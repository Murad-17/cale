"""Image/video jobs and speech transport. All generated results stay on disk."""
import base64
import os
import re
import time
import uuid
from pathlib import Path
from urllib.parse import quote
import orion_http as http


class MediaService:
    def __init__(self, store):
        self.store = store
        self.directory = store.directory / "media"
        self.directory.mkdir(exist_ok=True)
        from video_service import VideoService
        self.video_service = VideoService(self)

    @staticmethod
    def key():
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise http.APIError("Bu əməliyyat üçün .env daxilində OPENAI_API_KEY əlavə et.")
        return {"Authorization": "Bearer " + key}

    @staticmethod
    def url(path):
        return os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + path

    def image(self, prompt, job_id=None):
        job_id = job_id or self.store.job("image", prompt)
        self.store.update(job_id, "running")
        try:
            result = http.request(self.url("/images/generations"), "POST", {"model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst"), "prompt": prompt, "size": "1024x1024", "quality": "medium", "n": 1}, self.key(), timeout=240)
            raw = base64.b64decode(result["data"][0]["b64_json"], validate=True)
            if not raw or len(raw) > 40 * 1024 * 1024:
                raise ValueError("Şəkil nəticəsi alınmadı və ya çox böyükdür.")
            name = job_id + ".png"
            (self.directory / name).write_bytes(raw)
            output = {"file": name, "url": "/api/media/files/" + name, "prompt": prompt, "kind": "image"}
            self.store.update(job_id, "completed", result=output)
            return output
        except Exception:
            self.store.update(job_id, "failed", result={"error": "Şəkil yaradıla bilmədi. API açarını, modeli və balansı yoxla."})
            raise

    def video_available(self):
        return self.video_service.available()

    def video(self, prompt, job_id=None, options=None, payload=None):
        return self.video_service.create(prompt, job_id, options, payload)

    def poll_videos(self):
        self.video_service.poll()

    def transcribe(self, data, mime="audio/webm", language="az"):
        model = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe")
        fields = {"model": model, "response_format": "json"}
        if model == "gpt-transcribe":
            fields["languages[]"] = "en" if language == "en" else "az"
        else:
            fields["language"] = "en" if language == "en" else "az"
        ext = {"audio/wav": ".wav", "audio/mp4": ".m4a", "audio/ogg": ".ogg"}.get(mime.split(";")[0], ".webm")
        raw, content_type = http.multipart(fields, {"file": ("speech" + ext, data, mime)})
        result = http.request(self.url("/audio/transcriptions"), "POST", headers={**self.key(), "Content-Type": content_type}, raw=raw, timeout=90)
        return str(result.get("text", "")).strip()

    def speech(self, text, language="az", provider="openai"):
        text = text[:3500]
        if provider == "elevenlabs":
            key, voice = os.environ.get("ELEVENLABS_API_KEY", ""), os.environ.get("ELEVENLABS_VOICE_ID", "")
            if not key or not voice:
                raise http.APIError("ElevenLabs üçün API açarı və səs identifikatoru əlavə et.")
            data = http.request("https://api.elevenlabs.io/v1/text-to-speech/" + quote(voice) + "?output_format=pcm_24000", "POST", {"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_v3"), "language_code": language}, {"xi-api-key": key}, timeout=90)
            import io
            import wave
            out = io.BytesIO()
            with wave.open(out, "wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(data)
            return out.getvalue()
        return http.request(self.url("/audio/speech"), "POST", {"model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "input": text, "voice": os.environ.get("OPENAI_VOICE", "coral"), "response_format": "wav", "instructions": "Speak naturally in " + ("English." if language == "en" else "Azerbaijani. Pronounce ə, ğ, ş, ç, ö, ü, ı correctly.")}, self.key(), timeout=90)
