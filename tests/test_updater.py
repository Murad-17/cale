"""Offline release, installation, persistence and API tests; no real user data."""
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import Store
from updater import Updater, SecureRedirect, https_url, version_key
from update_installer import apply_package, inspect_package, sha256, run_job
from dashboard_bridge import start
from release_tools import build


class Response(io.BytesIO):
    def __init__(self, value, size=None):
        super().__init__(value)
        self.headers = {"Content-Length": str(len(value) if size is None else size)}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "app"
        self.root.mkdir()
        for name, content in {
            "version.json": '{"version":"0.5.3"}',
            "main.py": "print('old')",
            "updater.py": "# updater",
            "update_installer.py": Path(__file__).parents[1].joinpath("update_installer.py").read_text(),
            "orion_dashboard.html": "old dashboard",
            "update_source.json": '{"manifest_url":"https://releases.example.test/latest.json"}',
            ".env": "PRIVATE_TEST_VALUE=keep-me",
        }.items():
            (self.root / name).write_text(content)
        self.engine = SimpleNamespace(store=Store(self.base / "data"), voice=None, work_gate=threading.RLock())
        self.up = Updater(self.engine, self.root)
        self.engine.updater = self.up
        self.env = patch.dict(os.environ, {"ORION_UPDATE_MANIFEST_URL": "", "ORION_UPDATE_TOKEN": ""})
        self.env.start()

    def tearDown(self):
        self.up.close()
        if self.up.worker:
            self.up.worker.join(3)
        self.env.stop()
        self.temp.cleanup()

    def release(self, version="0.5.4"):
        package, manifest = build(self.root, self.base / "release", version,
                                  "https://releases.example.test/ORION.zip", "Yeni funksiyalar <script>plain text</script>")
        return package, json.loads(manifest.read_text())

    def finish(self):
        self.up.worker.join(3)
        self.assertFalse(self.up.worker.is_alive())
        return self.up.status()

    def prepare(self):
        package, manifest = self.release()
        with patch.object(self.up, "_open", return_value=Response(json.dumps(manifest).encode())):
            self.up.check()
            self.assertEqual(self.finish()["phase"], "available")
        with patch.object(self.up, "_open", return_value=Response(package.read_bytes())):
            self.up.download()
            self.assertEqual(self.finish()["phase"], "ready")
        return package, manifest

    def test_release_preserves_name_only_for_matching_source_version(self):
        (self.root / "version.json").write_text('{"version":"0.5.3","name":"Premium UI"}')
        package, _ = self.release("0.5.3")
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(json.loads(archive.read("ORION/version.json")),
                             {"version": "0.5.3", "name": "Premium UI"})
        package, _ = self.release("0.5.4")
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(json.loads(archive.read("ORION/version.json")), {"version": "0.5.4"})

    def test_release_contains_bundled_font_support_and_rejects_private_files(self):
        root = Path(__file__).resolve().parents[1]
        package, _ = build(root, self.base / "bundled", "0.6.0",
                           "https://releases.example.test/ORION.zip", "Premium UI")
        with zipfile.ZipFile(package) as archive:
            names = set(archive.namelist())
            metadata = json.loads(archive.read("ORION/version.json"))
        self.assertEqual(metadata, {"version": "0.6.0", "name": "Premium UI"})
        for filename in ("orion_fonts.css", "password_meter.css", "password_meter.js",
                         "panel_assets/fonts/EuclidCircularA-Regular.woff",
                         "panel_assets/fonts/JetBrainsMono-Latin-Regular.woff",
                         "panel_assets/fonts/JetBrainsMono-OFL.txt"):
            self.assertIn("ORION/" + filename, names)
        self.assertFalse(any(".env" in name or "__pycache__" in name for name in names))
        self.assertEqual(len(inspect_package(package, "0.6.0")), len(names))

    def test_version_order_uses_semver_and_rejects_invalid(self):
        versions = ["0.5.3-alpha.1", "0.5.3-alpha.2", "0.5.3-alpha.10", "0.5.3-beta", "0.5.3", "0.5.10", "0.6.0", "1.0.0"]
        self.assertEqual(sorted(versions, key=version_key), versions)
        self.assertEqual(version_key("1.0.0+build.1"), version_key("1.0.0+build.2"))
        for value in ["", "0.5", "v0.5.4", "0.05.3", "1.0.0-a..b", "1.0.0-01"]:
            with self.assertRaises(ValueError):
                version_key(value)

    def test_source_missing_never_claims_latest_or_starts_a_download(self):
        (self.root / "update_source.json").write_text('{"manifest_url":""}')
        with patch.object(self.up, "_open") as remote:
            state = self.up.check()
        self.assertEqual(state["phase"], "unconfigured")
        self.assertIsNone(state["latest_version"])
        remote.assert_not_called()
        with self.assertRaises(ValueError):
            self.up.download()

    def test_consent_and_notification_deduplication_survive_restarts(self):
        self.assertEqual(self.up.status()["notification"], "permission")
        self.up.preferences(consent=False)
        self.assertIsNone(Updater(self.engine, self.root).status()["notification"])
        package, manifest = self.release()
        with patch.object(self.up, "_open", return_value=Response(json.dumps(manifest).encode())):
            self.up.check(); self.finish()
        self.assertEqual(self.up.status()["notification"], "release:0.5.4")
        self.up.notice("0.5.4", later=True)
        self.assertIsNone(self.up.status()["notification"])
        again = Updater(self.engine, self.root)
        self.assertIn("0.5.4", again.prefs["notified"])
        self.assertGreater(again.prefs["snooze_until"], time.time())

    def test_new_version_download_real_bytes_and_integrity(self):
        package, manifest = self.prepare()
        state = self.up.status()
        self.assertEqual(state["downloaded"], package.stat().st_size)
        self.assertEqual(state["total"], package.stat().st_size)
        self.assertEqual(state["percent"], 100)
        self.assertEqual(sha256(self.up.package), manifest["sha256"])
        self.assertNotIn("url", state)

    def test_same_or_older_release_is_current_without_fake_download(self):
        for version in ["0.5.3", "0.5.2"]:
            with patch.object(self.up, "_open", return_value=Response(json.dumps({"version": version}).encode())):
                self.up.check()
                self.assertEqual(self.finish()["phase"], "current")

    def test_invalid_manifest_and_missing_hash_are_visible_errors(self):
        for data in [b"not-json", b"[]", b'{"version":"0.5.4","url":"https://example.test/file"}']:
            with patch.object(self.up, "_open", return_value=Response(data)):
                self.up.check()
                state = self.finish()
                self.assertEqual(state["phase"], "error")
                self.assertTrue(state["error"])
                self.assertEqual(state["error_action"], "check")

    def test_failed_connection_is_retryable(self):
        with patch.object(self.up, "_open", side_effect=urllib.error.URLError("offline")):
            self.up.check()
            self.assertEqual(self.finish()["phase"], "error")
        with patch.object(self.up, "_open", return_value=Response(b'{"version":"0.5.3"}')):
            self.up.check()
            self.assertEqual(self.finish()["phase"], "current")

    def test_truncated_and_tampered_downloads_are_not_installable(self):
        package, manifest = self.release()
        with patch.object(self.up, "_open", return_value=Response(json.dumps(manifest).encode())):
            self.up.check(); self.finish()
        for raw in [package.read_bytes()[:-10], b"x" * package.stat().st_size]:
            with patch.object(self.up, "_open", return_value=Response(raw, manifest["size"])):
                self.up.download()
                state = self.finish()
                self.assertEqual(state["phase"], "error")
                self.assertEqual(state["error_action"], "download")
                self.assertIsNone(self.up.package)
        self.assertFalse(list(self.up.directory.glob("*.part")))
        self.assertEqual((self.root / "version.json").read_text(), '{"version":"0.5.3"}')

    def test_simultaneous_operations_are_coalesced(self):
        gate, entered = threading.Event(), threading.Event()
        def remote(_):
            entered.set(); gate.wait(2)
            return Response(b'{"version":"0.5.3"}')
        with patch.object(self.up, "_open", side_effect=remote) as request:
            self.up.check(); entered.wait(1)
            self.assertEqual(self.up.check()["phase"], "checking")
            self.assertEqual(self.up.download()["phase"], "checking")
            gate.set(); self.finish()
            self.assertEqual(request.call_count, 1)

    def test_https_redirects_cannot_downgrade_or_leak_token(self):
        for url in ["http://a.test/file", "file:///tmp/a", "https://name:secret@a.test/x", "https:///empty"]:
            with self.assertRaises(ValueError):
                https_url(url)
        redirect = SecureRedirect()
        req = urllib.request.Request("https://a.test/manifest", headers={"Authorization": "Bearer private"})
        with self.assertRaises(ValueError):
            redirect.redirect_request(req, None, 302, "", {}, "http://a.test/file")
        other = redirect.redirect_request(req, None, 302, "", {}, "https://b.test/file")
        self.assertIsNone(other.get_header("Authorization"))
        same = redirect.redirect_request(req, None, 302, "", {}, "https://a.test/file")
        self.assertEqual(same.get_header("Authorization"), "Bearer private")

    def test_release_builder_excludes_secrets_and_updates_preserve_data(self):
        (self.root / ".venv").mkdir(); (self.root / ".venv/python.exe").write_bytes(b"runtime")
        (self.root / "orion.sqlite3").write_bytes(b"user-data")
        package, manifest = self.release()
        with zipfile.ZipFile(package) as archive:
            self.assertNotIn("ORION/.env", archive.namelist())
            self.assertNotIn("ORION/update_source.json", archive.namelist())
        self.engine.store.put("personal", {"keep": True})
        apply_package(package, self.root, self.base / "backup", "0.5.4", manifest["sha256"])
        self.assertEqual(json.loads((self.root / "version.json").read_text())["version"], "0.5.4")
        self.assertEqual((self.root / ".env").read_text(), "PRIVATE_TEST_VALUE=keep-me")
        self.assertEqual((self.root / "orion.sqlite3").read_bytes(), b"user-data")
        self.assertEqual((self.root / ".venv/python.exe").read_bytes(), b"runtime")
        self.assertEqual(self.engine.store.get("personal"), {"keep": True})

    def test_unsafe_archives_rejected_before_writing(self):
        for name in ["ORION/.env", "../escape.py", "ORION/.venv/python.exe", "ORION/C:/bad", "ORION\\main.py", "/tmp/absolute.py"]:
            path = self.base / "bad.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(name, "bad")
            with self.assertRaises(ValueError):
                inspect_package(path, "0.5.4")
        self.assertFalse((self.base / "escape.py").exists())

    def test_copy_failure_rolls_back_prior_application_files(self):
        package, manifest = self.release()
        original = os.replace
        calls = []
        def fail_second(source, dest):
            if str(dest).startswith(str(self.root)):
                calls.append(dest)
                if len(calls) == 2:
                    raise PermissionError("fixture file locked")
            return original(source, dest)
        with patch("update_installer.os.replace", side_effect=fail_second):
            with self.assertRaises(PermissionError):
                apply_package(package, self.root, self.base / "rollback", "0.5.4", manifest["sha256"])
        self.assertEqual((self.root / "version.json").read_text(), '{"version":"0.5.3"}')
        self.assertEqual((self.root / "main.py").read_text(), "print('old')")

    def test_install_requires_confirmation_clean_sessions_and_no_active_jobs(self):
        self.prepare()
        self.up.restart = [sys.executable, str(self.root / "main.py"), "--desktop", "--port", "8765"]
        self.up.shutdown = Mock()
        self.up.heartbeat("test-session", True)
        with self.assertRaises(ValueError):
            self.up.install("test-session", True)
        self.up.heartbeat("test-session", False)
        with self.assertRaises(ValueError):
            self.up.install("test-session", False)
        job = self.engine.store.job("chat", "still running")
        with self.assertRaises(ValueError):
            self.up.install("test-session", True)
        self.engine.store.update(job, "completed")
        from panel_service import PanelService
        self.engine.panel = PanelService(self.engine.store)
        self.engine.panel.save({"text": "", "files": [{"name": "saved.txt", "id": "one", "size": 1, "type": "text/plain", "data": "eA=="}]})
        with self.assertRaisesRegex(ValueError, "Üst chatbot"):
            self.up.install("test-session", True)
        self.engine.panel.save({"text": "", "files": []})
        (self.engine.store.directory / "companion-draft.json").write_text('{"text":"unsent draft"}')
        with self.assertRaises(ValueError):
            self.up.install("test-session", True)
        (self.engine.store.directory / "companion-draft.json").write_text('{"text":""}')
        with patch("updater.subprocess.Popen", return_value=SimpleNamespace(pid=987654)), patch("updater.threading.Timer"):
            state = self.up.install("test-session", True, {"orion.workspace.v2": "saved"})
        self.assertEqual(state["phase"], "installing")
        self.assertTrue((self.up.directory / "pre-update.sqlite3").exists())
        self.assertEqual(self.engine.store.get("pre_update_workspace"), {"orion.workspace.v2": "saved"})
        self.assertEqual(json.loads((self.up.directory / "install-job.json").read_text())["restart"], self.up.restart)

    def test_success_is_reported_only_after_matching_installed_version(self):
        path = self.up.directory / "install-result.json"
        path.write_text('{"ok":true,"version":"0.5.3"}')
        again = Updater(self.engine, self.root)
        self.assertEqual(again.status()["notification"], "success:0.5.3")
        again.notice("success")
        self.assertNotEqual(again.status()["notification"], "success:0.5.3")
        path.write_text('{"ok":false,"error":"rolled back"}')
        self.assertEqual(Updater(self.engine, self.root).status()["phase"], "error")

    def test_detached_installer_replaces_then_relaunches_a_real_fixture_process(self):
        marker = self.base / "restarted.txt"
        (self.root / "main.py").write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('restarted')\n")
        package, manifest = self.release()
        parent = subprocess.Popen([sys.executable, "-c", "pass"])
        parent.wait(timeout=5)
        # Use a PID that has already exited; the helper must never kill a process.
        lock = self.base / "fixture.lock"
        lock.write_text("fixture")
        job = self.base / "install-job.json"
        job.write_text(json.dumps({"pid": parent.pid, "package": str(package),
            "target": str(self.root), "backup": str(self.base / "native-backup"),
            "version": "0.5.4", "sha256": manifest["sha256"], "lock": str(lock),
            "restart": [sys.executable, str(self.root / "main.py")]}))
        subprocess.run([sys.executable, str(Path(__file__).parents[1] / "update_installer.py"), str(job)], check=True, timeout=10)
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(.02)
        self.assertEqual(marker.read_text(), "restarted")
        self.assertEqual(json.loads((self.base / "install-result.json").read_text())["version"], "0.5.4")
        self.assertFalse(lock.exists())
        self.assertEqual((self.root / ".env").read_text(), "PRIVATE_TEST_VALUE=keep-me")

    def test_update_routes_enforce_existing_local_origin_boundary(self):
        server = start(0, self.engine)
        port = server.server_address[1]
        base = f"http://127.0.0.1:{port}"
        try:
            self.assertTrue(json.load(urllib.request.urlopen(base + "/api/updates"))["native"])
            body = json.dumps({"consent": False}).encode()
            req = urllib.request.Request(base + "/api/updates/preferences", data=body, headers={"Content-Type": "application/json"})
            self.assertFalse(json.load(urllib.request.urlopen(req))["automatic"])
            req = urllib.request.Request(base + "/api/updates/download", data=b"{}", headers={"Content-Type": "application/json", "Origin": "https://evil.test"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
