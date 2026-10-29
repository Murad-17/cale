"""Provider response contracts, compatibility and secret-safe error handling."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Engine
from storage import Store
from orion_http import APIError, request


class DiagnosticTests(unittest.TestCase):
    def provider_error(self, message, status=400, **detail):
        body = {"error": {"type": "invalid_request_error", "message": message, **detail}, "request_id": "req_fixture_diagnostic_123"}
        error = urllib.error.HTTPError("https://api.anthropic.com/v1/messages", status, "Bad request", {}, io.BytesIO(json.dumps(body).encode()))
        with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(APIError) as caught:
            request(error.url, "POST", {"model": "claude-sonnet-5", "messages": [{"role": "user", "content": "Private user prompt"}]}, {"x-api-key": "sk-ant-fixture-private"})
        return caught.exception

    def test_balance_reason_survives_the_conversation_and_is_not_blame_on_web(self):
        failure = self.provider_error("Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing.")
        self.assertEqual(failure.reason, "credit_balance")
        self.assertIn("Billing", str(failure))
        self.assertNotIn("internet", str(failure))
        self.assertEqual(failure.request_id, "req_fixture_diagnostic_123")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture", "ANTHROPIC_MODEL": "claude-sonnet-5"}):
            engine = Engine(directory)
            try:
                message = engine.store.message("user", "Salam")
                job = engine.store.job("chat", "Salam")
                with patch("orion_http.request", side_effect=failure):
                    engine._conversation_job(message, job, {**engine.settings, "provider": "anthropic", "webEnabled": True}, "ui")
                self.assertIn("Billing", engine.store.history()[-1]["text"])
                self.assertNotIn("internet", engine.store.history()[-1]["text"])
            finally:
                engine.close()

    def test_distinct_confirmed_reasons(self):
        fixtures = [
            ("model not found", "model"),
            ("temperature is not supported by this model", "temperature"),
            ("web_search is not supported by this model", "web_tool"),
            ("max_tokens: must be less than the model limit", "output_limit"),
            ("OAuth authentication is currently not supported", "credential_type"),
            ("workspace spend limit reached", "spend_limit"),
        ]
        for message, reason in fixtures:
            with self.subTest(reason=reason):
                self.assertEqual(self.provider_error(message).reason, reason)

    def test_unknown_errors_do_not_echo_the_prompt_key_or_arbitrary_error_type(self):
        failure = self.provider_error("Private user prompt; sk-ant-fixture-private", type="Private user prompt")
        self.assertNotIn("Private user prompt", str(failure))
        self.assertNotIn("sk-ant", str(failure))
        self.assertEqual(failure.status, 400)
        self.assertEqual(failure.reason, "")

    def test_known_reason_does_not_echo_secret_text_or_malformed_request_id(self):
        body = {"error": {"message": "model not found: sk-ant-private-credential Private user prompt", "type": "invalid_request_error"}, "request_id": "req_sk-ant-private-credential"}
        error = urllib.error.HTTPError("https://api.anthropic.com/v1/messages", 400, "bad", {}, io.BytesIO(json.dumps(body).encode()))
        with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(APIError) as caught:
            request(error.url)
        self.assertEqual(caught.exception.reason, "model")
        self.assertNotIn("sk-ant", str(caught.exception))
        self.assertNotIn("Private user prompt", str(caught.exception))
        self.assertEqual(caught.exception.request_id, "")

    def test_malformed_and_large_error_body_remains_bounded_and_generic(self):
        stream = io.BytesIO(b"<html>Private user prompt " + b"x" * 100000)
        error = urllib.error.HTTPError("https://api.anthropic.com/v1/messages", 400, "bad", {}, stream)
        with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(APIError) as caught:
            request(error.url)
        self.assertLessEqual(stream.tell(), 65537)
        self.assertNotIn("Private user prompt", str(caught.exception))

    def test_current_claude_omits_sampling_even_with_legacy_env_override(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture", "ANTHROPIC_MODEL": "claude-sonnet-5", "ORION_TEMPERATURE_SUPPORTED": "1"}):
            engine = Engine(directory)
            try:
                settings = {**engine.settings, "model": "anthropic:claude-sonnet-5", "webEnabled": False}
                message = engine.store.message("user", "Salam")
                with patch("orion_http.request", return_value={"content": [{"type": "text", "text": "Salam"}], "usage": {}}) as transport:
                    self.assertEqual(engine.answer(message, settings), "Salam")
                self.assertNotIn("temperature", transport.call_args.args[2])
                self.assertFalse(engine.capabilities()["temperature"])
                legacy = {**settings, "model": "anthropic:claude-sonnet-4-6"}
                with patch("orion_http.request", return_value={"content": [{"type": "text", "text": "Salam"}], "usage": {}}) as transport:
                    engine.answer(message, legacy)
                self.assertIn("temperature", transport.call_args.args[2])
            finally:
                engine.close()

    def test_empty_attachment_text_never_creates_an_empty_claude_text_block(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture"}):
            engine = Engine(directory)
            try:
                message = engine.store.message("user", "", attachments=[{"id": "fixture.png"}])
                image = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "fixture"}}
                with patch("attachments.content", return_value=[image]), patch("orion_http.request", return_value={"content": [{"type": "text", "text": "Şəkil"}], "usage": {}}) as transport:
                    engine.answer(message, {**engine.settings, "model": "anthropic:claude-sonnet-5", "webEnabled": False})
                self.assertEqual(transport.call_args.args[2]["messages"][0]["content"], [image])
            finally:
                engine.close()

    def test_credentials_in_model_are_not_exposed_persisted_or_sent(self):
        secret = "sk-ant-fixture-private-model"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture", "ANTHROPIC_MODEL": secret}):
            store = Store(directory)
            store.put("assistant", {"model": "anthropic:" + secret})
            engine = Engine(directory)
            try:
                self.assertNotIn(secret, json.dumps(engine.models()))
                self.assertEqual(engine.settings["model"], "server-default")
                self.assertEqual(engine.store.get("assistant")["model"], "server-default")
                with self.assertRaises(ValueError) as saved:
                    engine.save_settings({"model": "anthropic:" + secret})
                self.assertNotIn(secret, str(saved.exception))
                with self.assertRaises(APIError) as provider:
                    engine.provider(engine.settings)
                self.assertNotIn(secret, str(provider.exception))
            finally:
                engine.close()


if __name__ == "__main__":
    unittest.main()
