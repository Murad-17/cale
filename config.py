"""Load a local .env without third-party dependencies or printing its contents."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_env(path=None):
    path = Path(path or ROOT / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)
    if os.environ.get("BLENDER_EXE") and not os.environ.get("BLENDER_PATH"):
        os.environ["BLENDER_PATH"] = os.environ["BLENDER_EXE"]


def data_directory():
    default = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "ORION"
    return Path(os.environ.get("ORION_DATA_DIR", default))


def default_settings():
    return {"assistantMode": "companion", "assistantMood": "calm", "webEnabled": True, "researchMode": "auto", "researchTokens": 10000, "provider": "auto", "model": "server-default", "language": "az", "temperature": .7, "maxTokens": 4096, "systemPrompt": "", "persona": "", "memory": [], "profile": {}, "voiceMode": "cloud", "ttsProvider": "openai", "ttsModel": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "recognitionLanguage": "az-AZ", "wakeEnabled": False, "workspaceContext": {}}
