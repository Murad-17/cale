"""Offline integration tests. No real API calls, keys, microphone or Blender needed."""
import base64
import importlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Engine
from storage import Store
from dashboard_bridge import start
from media_service import MediaService
from script_guard import validate_script
from attachments import intake, content
from orion_http import APIError, multipart
import config


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "OPENAI_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-test", "OPENAI_MODEL": "gpt-test"})
        self.environment.start()
        self.engine = Engine(self.temp.name)

    def tearDown(self):
        self.engine.close()
        self.environment.stop()
        self.temp.cleanup()

    def wait(self, job_id):
        for _ in range(200):
            job = next(j for j in self.engine.store.jobs() if j["id"] == job_id)
            if job["status"] in ("completed", "failed"):
                return job
            time.sleep(.01)
        self.fail("Job did not finish")

    def test_env_loader_preserves_keys_and_windows_paths(self):
        env = Path(self.temp.name) / "test.env"
        env.write_text('ORION_TEST_PATH=C:\\Program Files\\Blender\\blender.exe\nORION_TEST_EMPTY=\nORION_TEST_QUOTED="hello world"\n', encoding="utf-8")
        with patch.dict(os.environ):
            config.load_env(env)
            self.assertEqual(os.environ["ORION_TEST_PATH"], r"C:\Program Files\Blender\blender.exe")
            self.assertEqual(os.environ["ORION_TEST_QUOTED"], "hello world")

    def test_anthropic_tool_loop_persistence_and_real_usage(self):
        answers = [{"content": [{"type": "tool_use", "id": "call1", "name": "workspace_statistics", "input": {}}], "usage": {"input_tokens": 11, "output_tokens": 3}}, {"content": [{"type": "text", "text": "Salam, əvvəlki məlumatını xatırlayıram."}], "usage": {"input_tokens": 17, "output_tokens": 8}}]
        with patch("orion_http.request", side_effect=answers) as upstream:
            accepted = self.engine.submit("Statistikama bax", settings={"model": "server-default", "language": "az", "memory": [{"label": "Ad", "text": "Murad"}]})
            job = self.wait(accepted["job_id"])
        self.assertEqual(job["status"], "completed")
        self.assertEqual(len(self.engine.store.messages()), 2)
        self.assertIn("Murad", upstream.call_args_list[0].args[2]["system"])
        self.assertEqual(upstream.call_args_list[1].args[2]["messages"][-1]["content"][0]["type"], "tool_result")
        self.assertEqual(self.engine.store.statistics()["input_tokens"], 28)
        reopened = Store(self.temp.name)
        self.assertIn("xatırlayıram", reopened.messages()[-1]["text"])

    def test_openai_keeps_function_and_reasoning_outputs(self):
        outputs = [{"output": [{"type": "reasoning", "id": "reason1", "summary": []}, {"type": "function_call", "name": "workspace_statistics", "arguments": "{}", "call_id": "c1"}], "usage": {"input_tokens": 4, "output_tokens": 2}}, {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Your statistics are ready."}]}], "usage": {"input_tokens": 5, "output_tokens": 3}}]
        with patch("orion_http.request", side_effect=outputs) as upstream:
            result = self.engine.submit("Show my statistics", settings={"model": "openai:gpt-test", "language": "en", "maxTokens": 1024, "temperature": 1})
            job = self.wait(result["job_id"])
        self.assertEqual(job["status"], "completed")
        packet = upstream.call_args_list[1].args[2]
        self.assertEqual(packet["max_output_tokens"], 1024)
        self.assertTrue(any(x["type"] == "reasoning" for x in packet["input"] if "type" in x))
        self.assertIn("English", packet["instructions"])
        self.assertEqual(packet["input"][-1]["type"], "function_call_output")

    def test_history_orders_queued_turns_correctly(self):
        a = self.engine.store.message("user", "Birinci")
        b = self.engine.store.message("user", "İkinci")
        self.engine.store.message("orion", "Birinci cavab", reply_to=a)
        self.assertEqual([m["text"] for m in self.engine.store.history(before=b)], ["Birinci", "Birinci cavab", "İkinci"])

    def test_attachments_are_atomic_bounded_and_encoded(self):
        raw = b"hello"
        items = [{"name": "../plan.txt", "type": "text/plain", "size": 5, "data": base64.b64encode(raw).decode()}]
        saved = intake(self.engine.uploads, items)
        self.assertEqual(saved[0]["name"], "plan.txt")
        self.assertIn("hello", content(self.engine.uploads, saved, "openai")[0]["text"])
        with self.assertRaises(ValueError):
            intake(self.engine.uploads, items + [{"name": "bad.txt", "data": "!"}])
        self.assertEqual(len(list(self.engine.uploads.iterdir())), 1)
        with self.assertRaises(ValueError):
            intake(self.engine.uploads, [{"name": "x.txt", "size": 8, "data": base64.b64encode(raw).decode()}])
        with self.assertRaises(ValueError):
            intake(self.engine.uploads, [{"name": "x.pdf", "type": "application/pdf", "data": base64.b64encode(raw).decode()}])

    def test_media_jobs_image_and_video_are_real_state_transitions(self):
        png = b"\x89PNG\r\n\x1a\nexample"
        with patch("orion_http.request", return_value={"data": [{"b64_json": base64.b64encode(png).decode()}]}):
            image = self.engine.media.image("Test image")
        self.assertEqual((self.engine.media.directory / image["file"]).read_bytes(), png)
        with patch.dict(os.environ, {"RUNWAYML_API_SECRET": "runway-fixture"}), patch("orion_http.request", return_value={"id": "video_test"}):
            video = self.engine.media.video("Test video")
        self.assertEqual(video["status"], "waiting")
        with patch.dict(os.environ, {"RUNWAYML_API_SECRET": "runway-fixture"}), patch("orion_http.request", side_effect=[{"status": "SUCCEEDED", "output": ["https://cdn.runway.test/video.mp4"]}, b"MP4-fixture"]):
            self.engine.media.poll_videos()
        video_job = next(j for j in self.engine.store.jobs() if j["id"] == video["job_id"])
        self.assertEqual(video_job["status"], "completed")
        self.assertTrue((self.engine.media.directory / video_job["result"]["file"]).exists())
        with patch("orion_http.request", side_effect=APIError("Rate limit", 429)):
            with self.assertRaises(APIError):
                self.engine.media.image("Failure")
        self.assertEqual(self.engine.store.jobs()[0]["status"], "failed")

    def test_voice_endpoints_use_audio_bytes_and_language_hints(self):
        with patch("orion_http.request", return_value={"text": "Salam Orion"}) as upstream:
            self.assertEqual(self.engine.media.transcribe(b"audio", "audio/wav", "az"), "Salam Orion")
            self.assertIn(b'languages[]', upstream.call_args.kwargs["raw"])
            self.assertIn(b'az', upstream.call_args.kwargs["raw"])
        with patch("orion_http.request", return_value=b"WAV"):
            self.assertEqual(self.engine.media.speech("Salam"), b"WAV")

    def test_guard_and_sensitive_file_filter(self):
        self.assertTrue(validate_script("import bpy\nbpy.ops.mesh.primitive_cube_add()"))
        for code in ["import os", "open('file')", "bpy.ops.wm.open_mainfile(filepath='x')", "exec('x')"]:
            with self.assertRaises(ValueError):
                validate_script(code)
        import file_search
        self.assertTrue(file_search.is_sensitive(".env"))
        self.assertTrue(file_search.is_sensitive(".env(3)"))
        self.assertTrue(file_search.is_sensitive(".env.local"))

    def test_missing_key_does_not_queue_or_save_a_message(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""}):
            with self.assertRaises(APIError):
                self.engine.submit("hello")
        self.assertEqual(self.engine.store.messages(), [])

    def test_http_contract_origin_and_static_file_boundaries(self):
        server = start(0, self.engine)
        port = server.server_address[1]
        base = f"http://127.0.0.1:{port}"
        try:
            settings = json.loads(urllib.request.urlopen(base + "/api/settings").read())
            self.assertTrue(settings["capabilities"]["attachments"])
            self.assertNotIn("test-key", json.dumps(settings))
            html = urllib.request.urlopen(base).read().decode()
            self.assertIn('id="osKanban"', html)
            self.assertIn('id="assistantRuntimeSection"', html)
            for path in ["/.env", "/../engine.py", "/api/media/files/../../config.py"]:
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + path)
            bad = urllib.request.Request(base + "/api/send", data=b'{"text":"hi"}', headers={"Content-Type": "application/json", "Origin": "https://example.com"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(bad)
            self.assertEqual(error.exception.code, 403)
            packet = {"settings": {"language": "en", "maxTokens": 2048, "temperature": 1, "api_key": "should-not-store"}}
            req = urllib.request.Request(base + "/api/settings", data=json.dumps(packet).encode(), headers={"Content-Type": "application/json"})
            self.assertTrue(json.loads(urllib.request.urlopen(req).read())["saved"])
            self.assertEqual(self.engine.settings["language"], "en")
            self.assertEqual(self.engine.settings["temperature"], 1)
            self.assertNotIn("api_key", self.engine.settings)
        finally:
            server.shutdown(); server.server_close()

    def test_importing_entry_point_has_no_runtime_side_effect(self):
        module = importlib.import_module("main")
        self.assertTrue(callable(module.run))


if __name__ == "__main__":
    unittest.main()
