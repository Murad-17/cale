"""Native window contract, persistent drafts and shared top-panel API tests."""
import base64
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Engine
from dashboard_bridge import start
from panel_service import DEFAULT_APPEARANCE, GREETING_INTERVAL, PanelService
from top_panel import PanelAPI, geometry, round_windows_window, run
from orion_companion import CompanionProcess, LocalClient
import main


class Event:
    def __init__(self):
        self.callbacks = []

    def __iadd__(self, callback):
        self.callbacks.append(callback)
        return self


class TopPanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root)
        self.panel = self.engine.panel

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def test_old_companion_draft_migrates_without_resetting_it(self):
        (self.root / "companion-draft.json").write_text(json.dumps({"text": "Əvvəlki qaralamam"}))
        self.assertEqual(self.panel.draft()["text"], "Əvvəlki qaralamam")
        self.panel.save({"text": "Yeni qaralama"})
        self.assertEqual(PanelService(self.engine.store).draft()["text"], "Yeni qaralama")
        self.assertEqual(json.loads((self.root / "companion-draft.json").read_text())["text"], "Yeni qaralama")

    def test_files_and_text_persist_independently_and_failed_save_is_atomic(self):
        file = {"id": "f1", "name": "plan.txt", "type": "text/plain", "size": 4,
                "data": base64.b64encode(b"plan").decode()}
        self.panel.save({"text": "Bunu oxu", "files": [file]})
        self.panel.save({"text": "Bunu izah et"})
        self.assertEqual(self.panel.draft()["files"], [file])
        for invalid in [[{**file, "data": "bad!"}], [{**file, "size": 9}], [file] * 6]:
            with self.assertRaises(ValueError):
                self.panel.save({"text": "should not replace", "files": invalid})
            self.assertEqual(self.panel.draft()["text"], "Bunu izah et")
        self.assertTrue(self.panel.has_draft())
        self.panel.save({"text": "", "files": []})
        self.assertFalse(self.panel.has_draft())

    def test_native_notification_has_priority_and_dashboard_recovers_on_close(self):
        up = self.engine.updater
        self.assertEqual(up.status()["notification"], "permission")
        up.heartbeat("top-panel-session", False, "top")
        self.assertIsNone(up.status()["notification"])
        self.assertEqual(up.status("top")["notification"], "permission")
        up.close_session("top-panel-session")
        self.assertEqual(up.status()["notification"], "permission")
        up.preferences(consent=False)
        self.assertIsNone(up.status("top")["notification"])

    def test_geometry_is_top_centered_and_clamps_saved_positions(self):
        self.assertEqual(geometry("home", (0, 0, 1920, 1080)), (680, 212, 620, 14))
        self.assertEqual(geometry("chat", (0, 0, 1920, 1080)), (560, 920, 1336, 20))
        for mode in ("home", "chat", "peek", "settings", "update", "notes", "greeting"):
            w, h, x, y = geometry(mode, (0, 0, 360, 640), 9000, 9000)
            self.assertGreaterEqual(x, 0); self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, 360); self.assertLessEqual(y + h, 640)
        with self.assertRaises(ValueError):
            geometry("arbitrary", (0, 0, 1920, 1080))

    def test_chat_opens_on_right_and_restores_compact_position_without_moving_its_anchor(self):
        state = self.root / "companion-ui.json"
        window = SimpleNamespace(x=620, y=14, width=680, height=212)
        def resize(w, h):
            window.width, window.height = w, h
        def move(x, y):
            window.x, window.y = x, y
        window.resize, window.move, window.destroy = resize, move, Mock()
        api = PanelAPI("http://127.0.0.1:8765", state, (0, 0, 1920, 1080))
        api._attach(window)
        api.layout("chat", True)
        self.assertEqual((window.x, window.y, window.width, window.height), (1336, 20, 560, 920))
        self.assertEqual(json.loads(state.read_text())["center"], 960)
        api.layout("home", True)
        self.assertEqual((window.x, window.y, window.width, window.height), (620, 14, 680, 212))
        api.layout("chat", True)
        api.layout("peek", True)
        self.assertEqual(window.width, 284)
        self.assertEqual(window.y, 0)
        self.assertEqual(window.x + window.width / 2, 960)
        self.assertEqual(json.loads(state.read_text())["version"], 3)
        self.assertTrue(json.loads(state.read_text())["collapsed"])
        api.layout("chat", True)
        self.assertEqual(window.y, 20)
        with self.assertRaises(ValueError):
            api.layout("../../bad")
        api.layout("update", True, 212)
        self.assertEqual(window.height, 212)
        with self.assertRaises(ValueError):
            api.layout("update", True, "arbitrary")
        api.close_panel()
        window.destroy.assert_called_once()

    def test_native_drag_snaps_at_top_and_pulling_the_tab_down_expands_it(self):
        window = SimpleNamespace(x=650, y=14, width=620, height=158, evaluate_js=Mock())
        api = PanelAPI("http://127.0.0.1:8765", self.root / "position.json", (0, 0, 1920, 1080))
        api._attach(window)
        api._settle_position()
        window.evaluate_js.assert_not_called()
        window.y = 4
        api._settle_position()
        self.assertIn("dockTop()", window.evaluate_js.call_args.args[0])
        api._mode = "peek"
        window.y = 60
        api._settle_position()
        self.assertIn("expandDock()", window.evaluate_js.call_args.args[0])

    def test_theme_changes_persist_and_invalid_css_does_not_replace_the_palette(self):
        theme = {**DEFAULT_APPEARANCE, "theme": "purple", "light": False,
                 "accent": "#6d4cff", "background": "#07050f", "text": "#f3eeff"}
        self.panel.save_appearance(theme)
        self.assertEqual(PanelService(self.engine.store).appearance(), theme)
        with self.assertRaises(ValueError):
            self.panel.save_appearance({**theme, "accent": "url(https://external.test)"})
        self.assertEqual(self.panel.appearance(), theme)

    def test_dashboard_can_reenable_and_reopen_a_closed_panel_without_losing_its_draft(self):
        server = start(0, self.engine)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        client = LocalClient(url)
        controller = CompanionProcess(url, self.root, enabled=False)
        self.panel.controller = controller
        child = Mock(); child.poll.return_value = None
        try:
            self.panel.save({"text": "Bağlayanda da qalsın", "files": []})
            with patch("orion_companion.importlib.util.find_spec", return_value=object()), patch("orion_companion.subprocess.Popen", return_value=child) as launch:
                self.assertTrue(client.request("/api/panel/control", {"action": "show"})["ok"])
                self.assertTrue(controller.enabled)
                self.assertTrue(client.request("/api/panel/status")["running"])
                client.request("/api/panel/control", {"action": "show"})
                self.assertEqual(launch.call_count, 1)
                client.request("/api/panel/control", {"action": "close"})
                child.poll.return_value = 0
                self.assertFalse(client.request("/api/panel/status")["running"])
                client.request("/api/panel/control", {"action": "show"})
                self.assertEqual(launch.call_count, 2)
                self.assertFalse(self.panel.close_requested)
                self.assertEqual(client.request("/api/panel/draft")["text"], "Bağlayanda da qalsın")
        finally:
            server.shutdown(); server.server_close()

    def test_runner_creates_a_real_separate_always_on_top_frameless_window(self):
        window = Mock()
        window.events = SimpleNamespace(before_show=Event(), shown=Event(), loaded=Event(), resized=Event(), moved=Event(), closed=Event())
        webview = SimpleNamespace(screens=[SimpleNamespace(x=0, y=0, width=1920, height=1080)],
                                  create_window=Mock(return_value=window), start=Mock())
        with patch.dict("sys.modules", {"webview": webview}):
            run("http://127.0.0.1:8765", self.root / "companion-ui.json")
        kwargs = webview.create_window.call_args.kwargs
        self.assertEqual(webview.create_window.call_args.args[1], "http://127.0.0.1:8765/panel")
        self.assertTrue(kwargs["on_top"])
        self.assertTrue(kwargs["frameless"])
        self.assertEqual(kwargs['transparent'], os.name != 'nt')
        self.assertFalse(kwargs["easy_drag"])
        self.assertEqual(kwargs["y"], 14)
        self.assertEqual(kwargs["x"], 620)
        self.assertFalse(webview.start.call_args.kwargs["private_mode"])
        self.assertIn("top-panel-webview", webview.start.call_args.kwargs["storage_path"])

    def test_panel_only_launch_keeps_the_main_dashboard_hidden(self):
        window = Mock()
        window.events = SimpleNamespace(closing=Event())
        webview = SimpleNamespace(create_window=Mock(return_value=window), start=Mock())
        tray = SimpleNamespace(Icon=Mock(return_value=Mock()), Menu=lambda *args: args,
                               MenuItem=lambda *args, **kwargs: args)
        self.engine.panel_only = True
        with patch.dict("sys.modules", {"webview": webview, "pystray": tray}):
            main.desktop(self.engine, Mock(), "http://127.0.0.1:8765", Mock())
        self.assertTrue(webview.create_window.call_args.kwargs["hidden"])

    def test_windows_surface_is_applied_only_on_windows(self):
        window=SimpleNamespace(native=None)
        with patch('panel_window.apply_surface',return_value=True) as shape:
            with patch('top_panel.os.name','nt'):
                self.assertTrue(round_windows_window(window,'home'))
                shape.assert_called_once_with(window,'home')
            shape.reset_mock()
            with patch('top_panel.os.name','posix'):
                self.assertFalse(round_windows_window(window,'peek'))
                shape.assert_not_called()

    def test_greeting_cooldown_and_disabled_choice_survive_panel_restart(self):
        with patch("panel_service.time.time", return_value=100000):
            self.assertTrue(self.panel.greeting({"action": "claim"})["show"])
            restarted = PanelService(self.engine.store)
            self.assertFalse(restarted.greeting({"action": "claim"})["show"])
        with patch("panel_service.time.time", return_value=100000 + GREETING_INTERVAL):
            self.assertTrue(restarted.greeting({"action": "claim"})["show"])
        restarted.greeting({"action": "preferences", "enabled": False})
        self.assertFalse(PanelService(self.engine.store).greeting_preferences()["enabled"])
        with patch("panel_service.time.time", return_value=200000):
            self.assertFalse(restarted.greeting({"action": "claim"})["show"])
            self.assertTrue(restarted.greeting({"action": "preview"})["show"])
        for bad in ({"action": "unknown"}, {"action": "preferences", "enabled": "true"}):
            with self.assertRaises(ValueError):
                restarted.greeting(bad)

    def test_simultaneous_greeting_checks_only_show_once(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.panel.greeting({"action": "claim"}), range(8)))
        self.assertEqual(sum(result["show"] for result in results), 1)

    def test_panel_routes_persist_drafts_and_reject_external_origins(self):
        server = start(0, self.engine)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        client = LocalClient(url)
        try:
            self.assertIn(b"ORIONPanel", urllib.request.urlopen(url + "/panel").read())
            self.assertTrue(client.request("/api/panel/draft", {"text": "Qoru", "files": []})["ok"])
            self.assertEqual(client.request("/api/panel/draft")["text"], "Qoru")
            self.assertTrue(client.request("/api/panel/greeting", {"action": "claim"})["show"])
            self.assertFalse(client.request("/api/panel/greeting", {"action": "claim"})["show"])
            self.assertTrue(client.request("/api/panel/greeting", {"action": "preferences", "enabled": False})["ok"])
            self.assertFalse(client.request("/api/panel/status")["greetings"]["enabled"])
            self.assertTrue(urllib.request.urlopen(url + "/panel-assets/orion-idle.png").read().startswith(b"\x89PNG"))
            for path in ["/panel-assets/../../.env", "/panel-assets/missing.png"]:
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(url + path)
            req = urllib.request.Request(url + "/api/panel/control", data=b'{"action":"close"}',
                headers={"Content-Type": "application/json", "Origin": "https://external.test"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)
            req = urllib.request.Request(url + "/api/panel/greeting", data=b'{"action":"preview"}',
                headers={"Content-Type": "application/json", "Origin": "https://external.test"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown(); server.server_close()

    def test_parent_waits_for_graceful_panel_exit_before_forcing_termination(self):
        server = start(0, self.engine)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        child = Mock();child.poll.return_value = None
        controller = CompanionProcess(url, self.root)
        controller.process = child
        try:
            controller.stop()
            self.assertTrue(self.panel.close_requested)
            child.wait.assert_called_once_with(timeout=3)
            child.terminate.assert_not_called()
        finally:
            server.shutdown(); server.server_close()

    def test_offline_font_and_animation_assets_are_served_without_opening_static_access(self):
        server = start(0, self.engine)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urllib.request.urlopen(url + "/panel-assets/fonts/Poppins-Regular.woff") as response:
                self.assertEqual(response.headers.get_content_type(), "font/woff")
                self.assertTrue(response.read().startswith(b"wOFF"))
            with urllib.request.urlopen(url + "/robot-animator.js") as response:
                self.assertEqual(response.headers.get_content_type(), "application/javascript")
                self.assertIn(b"window.ORIONRobot", response.read())
            with urllib.request.urlopen(url + "/panel-assets/orion-shell.png") as response:
                self.assertTrue(response.read().startswith(b"\x89PNG"))
            for path in ["/panel-assets/fonts/../../.env", "/panel-assets/fonts/missing.woff", "/robot-animator.js/../.env"]:
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(url + path)
        finally:
            server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
