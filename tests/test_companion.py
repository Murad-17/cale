"""Companion integration tests without a desktop, API key or external request."""
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import dashboard_bridge
import main
from orion_companion import CompanionApp, CompanionProcess, LocalClient
from storage import Store


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.show = Mock()

        def submit(text, files=None, settings=None):
            if text == "reject":
                raise ValueError("API açarı əlavə edilməyib.")
            message = self.store.message("user", text)
            job = self.store.job("chat", text)
            self.store.message("orion", "İcra edildi: " + text, reply_to=message)
            self.store.update(job, "completed", result={"reply": "İcra edildi: " + text})
            return {"ok": True, "message_id": message, "job_id": job}

        self.engine = SimpleNamespace(store=self.store, submit=submit, desktop_show=self.show)
        self.server = dashboard_bridge.start(0, self.engine)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.client = LocalClient(self.url)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_commands_and_replies_use_the_same_runtime_store(self):
        result = self.client.request("/api/send", {"text": "Planımı göstər"})
        self.assertTrue(result["ok"])
        messages = self.client.request("/api/messages?since=0")["messages"]
        self.assertEqual([m["sender"] for m in messages], ["user", "orion"])
        self.assertEqual(messages[1]["reply_to"], result["message_id"])
        self.assertEqual(self.client.request("/api/jobs")["jobs"][0]["status"], "completed")

    def test_restore_route_uses_only_the_desktop_callback(self):
        self.assertTrue(self.client.request("/api/desktop/show", {})["ok"])
        self.show.assert_called_once_with()
        self.engine.desktop_show = None
        with self.assertRaisesRegex(ValueError, "Əsas panel hazır deyil"):
            self.client.request("/api/desktop/show", {})

    def test_local_client_rejects_external_and_ambiguous_destinations(self):
        for url in ["https://example.com", "http://example.com:8765", "http://127.0.0.1:8765/x",
                    "http://user@127.0.0.1:8765", "http://localhost:8765/?x=1"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                LocalClient(url)

    def ui_without_a_display(self):
        app = CompanionApp.__new__(CompanionApp)
        app.root = Mock()
        app.entry = Mock()
        app.entry.get.return_value = "Planımı göstər"
        app.send_button, app.status, app.canvas, app.append = Mock(), Mock(), Mock(), Mock()
        app.client, app.events = self.client, queue.Queue()
        app.closed = app.sending = app.polling = False
        app.failures, app.cursor, app.pending_job = 0, None, None
        app.seen, app.images, app.figure = set(), (None, None, None), 1

        def immediate(kind, fn):
            try:
                app.events.put((kind, fn(), None))
            except Exception as error:
                app.events.put((kind, None, str(error)))
        app.background = immediate
        return app

    def test_chat_send_accept_poll_and_completion_without_duplicate_history(self):
        app = self.ui_without_a_display()
        app.send()
        app.drain()
        self.assertIsNone(app.pending_job)
        app.entry.delete.assert_called_once_with(0, "end")
        self.assertEqual(app.append.call_count, 2)
        app.poll(reschedule=False)
        app.drain()
        self.assertEqual(app.append.call_count, 2)
        # Only the UI pump is scheduled; an immediate send does not spawn another poll loop.
        self.assertTrue(all(call.args[0] == 100 for call in app.root.after.call_args_list))

    def test_rejected_command_preserves_the_draft(self):
        app = self.ui_without_a_display()
        app.entry.get.return_value = "reject"
        app.send()
        app.drain()
        app.entry.delete.assert_not_called()
        self.assertIsNone(app.pending_job)
        app.append.assert_called_with("notice", "API açarı əlavə edilməyib.")

    def test_closing_dashboard_keeps_companion_until_explicit_exit(self):
        class Event:
            def __iadd__(self, fn):
                self.callback = fn
                return self
        window = Mock()
        window.events = SimpleNamespace(closing=Event())
        companion, tray = Mock(), Mock()
        view = SimpleNamespace(create_window=Mock(return_value=window))
        items = []
        def menu_item(label, callback, **_):
            item = SimpleNamespace(label=label, callback=callback)
            items.append(item)
            return item
        tray_module = SimpleNamespace(Icon=Mock(return_value=tray), Menu=lambda *rows: rows,
                                      MenuItem=menu_item)
        def run_gui(**_):
            self.assertFalse(window.events.closing.callback())
            window.hide.assert_called_once()
            companion.stop.assert_not_called()
            next(item for item in items if item.label == "Tam çıxış").callback()
            window.destroy.assert_called_once()
        view.start = run_gui
        engine = SimpleNamespace(store=SimpleNamespace(directory=Path(self.temp.name)))
        with patch.dict("sys.modules", {"webview": view, "pystray": tray_module}):
            self.assertTrue(main.desktop(engine, Mock(), self.url, companion))
        companion.start.assert_called_once()
        self.assertTrue(companion.stop.called)
        self.assertTrue(callable(engine.desktop_show))

    def test_process_manager_does_not_spawn_duplicate_figures(self):
        child = Mock()
        child.poll.return_value = None
        controller = CompanionProcess(self.url, self.temp.name)
        with patch("orion_companion.importlib.util.find_spec", return_value=object()), patch("orion_companion.subprocess.Popen", return_value=child) as spawn:
            self.assertTrue(controller.start())
            self.assertTrue(controller.start())
            spawn.assert_called_once()
            controller.stop()
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=3)


if __name__ == "__main__":
    unittest.main()
