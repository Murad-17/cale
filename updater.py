"""ORION background updater: trusted HTTPS manifest + SHA-256 source packages.

No fabricated releases, progress, executable downloads, dependency installation,
or edits to .env, virtual environments, SQLite, uploads or browser profiles.
"""
import copy
import http.client
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import config
from update_installer import MAX_PACKAGE, atomic_json, inspect_package, sha256

CHECK_INTERVAL = 6 * 60 * 60
BUSY = {"checking", "downloading", "verifying", "installing"}


def version_key(value):
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?", str(value))
    if not match:
        raise ValueError("Versiya major.minor.patch formatında olmalıdır.")
    pre = match[4]
    identifiers = []
    if pre is not None:
        for item in pre.split("."):
            if not item or (item.isdigit() and len(item) > 1 and item.startswith("0")):
                raise ValueError("Versiyanın ilkin buraxılış işarəsi etibarsızdır.")
            identifiers.append((0, int(item)) if item.isdigit() else (1, item))
    return tuple(map(int, match.group(1, 2, 3))) + (pre is None, tuple(identifiers))


def current_version(root=None):
    return json.loads((Path(root or config.ROOT) / "version.json").read_text(encoding="utf-8"))["version"]


def current_name(root=None):
    metadata = json.loads((Path(root or config.ROOT) / "version.json").read_text(encoding="utf-8"))
    name = metadata.get("name", "")
    return name if isinstance(name, str) else ""


def https_url(url):
    parsed = urlsplit(str(url))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Yeniləmə mənbəyi etibarlı HTTPS ünvanı olmalıdır.")
    return str(url)


class SecureRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            redirected.remove_header("Authorization")
        return redirected


class Updater:
    def __init__(self, engine, root=None):
        self.engine, self.store = engine, engine.store
        self.root = Path(root or config.ROOT).resolve()
        self.directory = (self.store.directory / "updates").resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.directory / "operation.lock"
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.sessions = {}
        self.top_panel_until = 0
        self.worker = None
        self.restart = None
        self.shutdown = None
        self.prefs = {"consent": None, "auto": False, "notified": [], "snooze_until": 0,
                      "last_check": None, "success_pending": None, **self.store.get("software_updates", {})}
        self.release = None
        self.package = None
        self.state = {"phase": "idle", "current_version": current_version(self.root), "current_name": current_name(self.root),
                      "latest_version": None, "downloaded": 0, "total": None,
                      "percent": None, "error": "", "error_action": ""}
        self._consume_install_result()

    def _consume_install_result(self):
        result = self.directory / "install-result.json"
        if not result.exists():
            return
        try:
            data = json.loads(result.read_text(encoding="utf-8"))
            if data.get("ok") and data.get("version") == self.state["current_version"]:
                self.prefs["success_pending"] = data["version"]
                self.state["phase"] = "current"
                self._save()
            elif not data.get("ok"):
                self.prefs["success_pending"] = None
                self._save()
                self.state.update(phase="error", error=data.get("error", "Quraşdırma alınmadı."), error_action="check")
            result.unlink()
        except (OSError, ValueError):
            self.state.update(phase="error", error="Əvvəlki quraşdırmanın nəticəsi oxunmadı.", error_action="check")

    def _save(self):
        self.store.put("software_updates", self.prefs)

    def source(self):
        url = os.environ.get("ORION_UPDATE_MANIFEST_URL", "").strip()
        if not url:
            try:
                url = json.loads((self.root / "update_source.json").read_text(encoding="utf-8")).get("manifest_url", "").strip()
            except (OSError, ValueError, AttributeError):
                pass
        return https_url(url) if url else ""

    def status(self, surface="dashboard"):
        with self.lock:
            try:
                configured = bool(self.source())
            except ValueError:
                configured = False
            event = None
            owner = "top" if time.time() < self.top_panel_until else "dashboard"
            if self.prefs["success_pending"]:
                event = "success:" + self.prefs["success_pending"]
            elif self.prefs["consent"] is None:
                event = "permission"
            elif (self.state["phase"] == "available" and self.release and
                  self.release["version"] not in self.prefs["notified"] and time.time() >= self.prefs["snooze_until"]):
                event = "release:" + self.release["version"]
            return {**copy.deepcopy(self.state), "configured": configured,
                    "automatic": self.prefs["auto"], "consent": self.prefs["consent"],
                    "last_check": self.prefs["last_check"], "notification": event if owner == surface else None,
                    "notification_owner": owner,
                    "notes": self.release["notes"] if self.release else self._local_notes(),
                    "native": True, "can_restart": callable(self.shutdown) and bool(self.restart),
                    "busy": self.state["phase"] in BUSY}

    def _local_notes(self):
        try:
            return (self.root / "RELEASE_NOTES_AZ.md").read_text(encoding="utf-8")[:20000]
        except OSError:
            return "Bu versiya üçün buraxılış qeydləri əlavə edilməyib."

    def preferences(self, consent=None, automatic=None):
        with self.lock:
            if consent is not None:
                if type(consent) is not bool:
                    raise ValueError("İcazə seçimi düzgün deyil.")
                self.prefs.update(consent=consent, auto=consent)
            if automatic is not None:
                if type(automatic) is not bool:
                    raise ValueError("Avtomatik yoxlama seçimi düzgün deyil.")
                self.prefs.update(auto=automatic, consent=automatic)
            self._save()
        if self.prefs["auto"]:
            self.check()
        return self.status()

    def notice(self, event, later=False):
        with self.lock:
            if event == "success":
                self.prefs["success_pending"] = None
            elif self.release and event == self.release["version"]:
                self.prefs["notified"] = (self.prefs["notified"] + [event])[-30:]
                if later:
                    self.prefs["snooze_until"] = time.time() + 24 * 60 * 60
            self._save()
        return self.status()

    def start(self):
        def background():
            if self.prefs["auto"]:
                self.check()
            while not self.stop.wait(60):
                if self.prefs["auto"] and time.time() - (self.prefs["last_check"] or 0) >= CHECK_INTERVAL:
                    self.check()
        threading.Thread(target=background, daemon=True, name="orion-update-checks").start()

    def _claim(self):
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                pid = int(self.lock_path.read_text())
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes
                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                    kernel.OpenProcess.restype = wintypes.HANDLE
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    handle = kernel.OpenProcess(0x1000, False, pid)
                    alive = bool(handle) or ctypes.get_last_error() == 5
                    if handle:
                        kernel.CloseHandle(handle)
                else:
                    try:
                        os.kill(pid, 0)
                        alive = True
                    except ProcessLookupError:
                        alive = False
                if not alive:
                    self.lock_path.unlink(missing_ok=True)
                    return self._claim()
            except (OSError, ValueError):
                pass
            raise ValueError("Başqa yeniləmə prosesi işləyir. Onun bitməsini gözlə.") from None
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))

    def _release_lock(self):
        try:
            if self.lock_path.read_text() == str(os.getpid()):
                self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _launch(self, phase, action, fn):
        with self.lock:
            if self.state["phase"] in BUSY:
                return self.status()
            self._claim()
            self.state.update(phase=phase, error="", error_action="")
            def work():
                try:
                    fn()
                except ValueError as error:
                    with self.lock:
                        self.state.update(phase="error", error=str(error)[:300], error_action=action)
                except (OSError, urllib.error.URLError, http.client.HTTPException, zipfile.BadZipFile):
                    with self.lock:
                        self.state.update(phase="error", error="Bağlantı kəsildi və ya yeniləmə faylı oxunmadı. Yenidən sına.", error_action=action)
                except Exception:
                    with self.lock:
                        self.state.update(phase="error", error="Yeniləmə tamamlanmadı. Yenidən sına.", error_action=action)
                finally:
                    self._release_lock()
            self.worker = threading.Thread(target=work, daemon=True, name="orion-update-" + action)
            self.worker.start()
            return self.status()

    def _open(self, url):
        https_url(url)
        headers = {"User-Agent": "ORION/" + self.state["current_version"], "Accept-Encoding": "identity"}
        token = os.environ.get("ORION_UPDATE_TOKEN", "")
        if token and urlsplit(url).netloc == urlsplit(self.source()).netloc:
            headers["Authorization"] = "Bearer " + token
        response = urllib.request.build_opener(SecureRedirect()).open(urllib.request.Request(url, headers=headers), timeout=25)
        https_url(response.geturl())
        return response

    def check(self):
        with self.lock:
            if self.state["phase"] in BUSY or self.state["phase"] == "ready":
                return self.status()
            try:
                source = self.source()
            except ValueError as error:
                self.state.update(phase="unconfigured", error=str(error))
                return self.status()
            if not source:
                self.state.update(phase="unconfigured", error="Rəsmi yeniləmə mənbəyi hələ qoşulmayıb.")
                return self.status()
        def perform():
            with self.lock:
                self.prefs["last_check"] = time.time()
                self._save()
            with self._open(source) as response:
                raw = response.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise ValueError("Buraxılış məlumatı həddən artıq böyükdür.")
            try:
                release = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ValueError("Buraxılış məlumatı düzgün JSON deyil.") from None
            if not isinstance(release, dict):
                raise ValueError("Buraxılış məlumatı düzgün deyil.")
            latest = release.get("version", "")
            newer = version_key(latest) > version_key(self.state["current_version"])
            notes = release.get("notes", "Bu buraxılış üçün əlavə qeyd yoxdur.")
            if not isinstance(notes, str) or len(notes) > 20000:
                raise ValueError("Buraxılış qeydləri düzgün deyil.")
            if newer:
                url = https_url(release.get("url", ""))
                digest = str(release.get("sha256", "")).lower()
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError("Buraxılış üçün SHA-256 yoxlaması göstərilməyib.")
                size = release.get("size")
                if type(size) is not int or not 0 < size <= MAX_PACKAGE:
                    raise ValueError("Buraxılış faylının ölçüsü düzgün deyil.")
                verified = dict(version=latest, notes=notes, url=url, sha256=digest, size=size)
            else:
                verified = dict(version=latest, notes=notes)
            with self.lock:
                self.release = verified
                self.package = None
                self.state.update(phase="available" if newer else "current", latest_version=latest,
                                  percent=None, downloaded=0, total=None)
        return self._launch("checking", "check", perform)

    def download(self):
        with self.lock:
            if self.state["phase"] in BUSY or self.state["phase"] == "ready":
                return self.status()
            if not self.release or "url" not in self.release:
                raise ValueError("Əvvəlcə yeni versiyanı yoxla.")
            release = dict(self.release)
            self.state.update(downloaded=0, total=release["size"], percent=0)
        def perform():
            partial = self.directory / (uuid.uuid4().hex + ".part")
            try:
                with self._open(release["url"]) as response, partial.open("wb") as out:
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) != release["size"]:
                        raise ValueError("Endirmə ölçüsü buraxılış məlumatına uyğun deyil.")
                    downloaded = 0
                    while True:
                        if self.stop.is_set():
                            raise ValueError("Endirmə dayandırıldı. Yenidən sına.")
                        block = response.read(64 * 1024)
                        if not block:
                            break
                        downloaded += len(block)
                        if downloaded > release["size"]:
                            raise ValueError("Endirilən fayl gözləniləndən böyükdür.")
                        out.write(block)
                        with self.lock:
                            self.state.update(downloaded=downloaded, percent=round(downloaded / release["size"] * 100, 1))
                if downloaded != release["size"]:
                    raise ValueError("Endirmə yarımçıq qaldı. Yenidən sına.")
                with self.lock:
                    self.state["phase"] = "verifying"
                if sha256(partial) != release["sha256"]:
                    raise ValueError("SHA-256 yoxlaması uğursuz oldu. Fayl quraşdırılmadı.")
                inspect_package(partial, release["version"])
                package = partial.with_suffix(".zip")
                os.replace(partial, package)
                with self.lock:
                    self.package = package
                    self.state.update(phase="ready", percent=100)
            finally:
                partial.unlink(missing_ok=True)
        return self._launch("downloading", "download", perform)

    def expect_top_panel(self):
        self.top_panel_until = time.time() + 15

    def heartbeat(self, session, dirty, surface="dashboard"):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", str(session)) or type(dirty) is not bool:
            raise ValueError("İş sessiyası düzgün deyil.")
        with self.lock:
            self.sessions = {k: v for k, v in self.sessions.items() if time.time() - v[0] < 30}
            self.sessions[session] = (time.time(), dirty)
            if surface == "top":
                self.top_panel_until = time.time() + 12
        return {"ok": True}

    def close_session(self, session):
        with self.lock:
            self.sessions.pop(str(session), None)
            if str(session).startswith("top-"):
                self.top_panel_until = 0
        return {"ok": True}

    def install(self, session, confirmed=False, snapshot=None):
        with self.engine.work_gate, self.lock:
            if self.state["phase"] == "installing":
                return self.status()
            if self.state["phase"] != "ready" or not self.package:
                raise ValueError("Yeniləmə hələ quraşdırmaya hazır deyil.")
            if not confirmed or not callable(self.shutdown) or not self.restart:
                raise ValueError("Quraşdırmaq üçün ORION-u START.bat ilə aç və yenidən başlatmanı təsdiqlə.")
            caller = self.sessions.get(session)
            if not caller or time.time() - caller[0] > 10:
                raise ValueError("İş sahəsinin vəziyyəti yenilənməyib. Yenidən sına.")
            if any(dirty for seen, dirty in self.sessions.values() if time.time() - seen < 30):
                raise ValueError("Açıq pəncərədə saxlanılmamış iş var. Əvvəlcə onu saxla və ya göndər.")
            if getattr(self.engine, "panel", None) and self.engine.panel.has_draft():
                raise ValueError("Üst chatbot panelində göndərilməmiş mesaj və ya fayl var. Əvvəlcə onu göndər və ya təmizlə.")
            companion_draft = self.store.directory / "companion-draft.json"
            if companion_draft.exists():
                try:
                    if json.loads(companion_draft.read_text(encoding="utf-8")).get("text", "").strip():
                        raise ValueError("Kiçik ORION çatında göndərilməmiş komanda var. Əvvəlcə onu göndər və ya təmizlə.")
                except (OSError, json.JSONDecodeError):
                    raise ValueError("Kiçik çatın qaralaması yoxlanmadı. Əvvəlcə onu bağla və yenidən aç.") from None
            if any(j["status"] in ("queued", "running", "waiting") for j in self.store.jobs()):
                raise ValueError("Aktiv AI tapşırığı var. Onun tamamlanmasını gözlə.")
            if getattr(self.engine, 'companion', None) and self.engine.companion.running_actions():
                raise ValueError('Kiçik botda təsdiqlənmiş əməliyyat icra olunur. Tamamlanmasını gözlə.')
            if self.engine.voice:
                voice = self.engine.voice.status()
                if voice.get("busy") or voice.get("state") in ("recording", "transcribing", "thinking", "speaking", "processing"):
                    raise ValueError("Səsli əməliyyatın tamamlanmasını gözlə.")
            if snapshot is not None:
                if not isinstance(snapshot, dict) or len(json.dumps(snapshot)) > 12 * 1024 * 1024:
                    raise ValueError("İş sahəsinin ehtiyat nüsxəsi düzgün deyil.")
                allowed = {k: v for k, v in snapshot.items() if k in (
                    "orion.workspace.v2", "orion.settings.v1", "orion.runtime.v1", "orion.timeline.workspace.v1") and isinstance(v, str)}
                self.store.put("pre_update_workspace", allowed)
            self._claim()
            try:
                # A second integrity check closes the gap between download and install.
                if sha256(self.package) != self.release["sha256"]:
                    self.package = None
                    self.state.update(phase="error", error="Yoxlanılmış paket dəyişib. Yeniləməni yenidən endir.", error_action="download")
                    raise ValueError("Yoxlanılmış paket dəyişib. Yeniləməni yenidən endir.")
                self.directory.mkdir(exist_ok=True)
                backup = self.directory / ("backup-" + uuid.uuid4().hex)
                with self.store.connection() as db, sqlite3.connect(self.directory / "pre-update.sqlite3") as dest:
                    db.backup(dest)
                helper = self.directory / "installer-runner.py"
                shutil.copy2(self.root / "update_installer.py", helper)
                job_path = self.directory / "install-job.json"
                atomic_json(job_path, {"package": str(self.package), "target": str(self.root),
                                      "backup": str(backup), "version": self.release["version"],
                                      "sha256": self.release["sha256"], "restart": self.restart,
                                      "pid": os.getpid(), "lock": str(self.lock_path)})
                options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
                process = subprocess.Popen([sys.executable, str(helper), str(job_path)],
                    cwd=str(self.directory), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, close_fds=True,
                    env={**os.environ, "ORION_DATA_DIR": str(self.store.directory.resolve())}, **options)
                # Keep the inter-process lock owned by the detached installer.
                self.lock_path.write_text(str(process.pid), encoding="utf-8")
                self.state.update(phase="installing", error="")
                timer = threading.Timer(1.2, self.shutdown)
                timer.daemon = True
                timer.start()
            except Exception:
                self._release_lock()
                raise
            return self.status()

    def close(self):
        self.stop.set()
