"""Persistent native top-panel drafts and graceful process control."""
import base64
import binascii
import json
import re
import threading
import time
from pathlib import Path

from update_installer import atomic_json

MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 25 * 1024 * 1024
GREETING_INTERVAL = 90 * 60
DEFAULT_APPEARANCE = {
    "theme": "coral", "name": "Açıq / Mərcan", "light": True,
    "accent": "#e76c46", "secondary": "#ad4328", "background": "#f5f3f6",
    "surface": "#ffffff", "raised": "#faf8fb", "muted": "#716978", "text": "#222126",
}


class PanelService:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.close_requested = False
        self.controller = None
        self.show_sequence = 0

    def appearance(self):
        with self.lock:
            return {**DEFAULT_APPEARANCE, **(self.store.get("top_panel_appearance") or {})}

    def save_appearance(self, data):
        if not isinstance(data, dict) or not isinstance(data.get("theme"), str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", data["theme"]):
            raise ValueError("Panel mövzusu düzgün deyil.")
        clean = {"theme": data["theme"], "name": str(data.get("name", "ORION"))[:80],
                 "light": data.get("light") is True}
        for key in ("accent", "secondary", "background", "surface", "raised", "muted", "text"):
            value = data.get(key)
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValueError("Panel rəngi düzgün deyil.")
            clean[key] = value.lower()
        with self.lock:
            self.store.put("top_panel_appearance", clean)
        return {"ok": True, "appearance": clean}

    def status(self):
        controller = self.controller
        return {"close_requested": self.close_requested, "show_sequence": self.show_sequence,
                "launch_available": controller is not None,
                "running": bool(controller and controller.is_running()), "appearance": self.appearance(),
                "greetings": self.greeting_preferences()}

    def greeting_preferences(self):
        with self.lock:
            saved = self.store.get("top_panel_greetings") or {}
            return {"enabled": saved.get("enabled", True) is True,
                    "last_shown": saved.get("last_shown", 0), "interval": GREETING_INTERVAL}

    def greeting(self, data):
        action = data.get("action")
        if action not in ("claim", "preview", "preferences"):
            raise ValueError("Salamlaşma əməliyyatı düzgün deyil.")
        with self.lock:
            prefs = self.greeting_preferences()
            if action == "preferences":
                if type(data.get("enabled")) is not bool:
                    raise ValueError("Salamlaşma seçimi düzgün deyil.")
                prefs["enabled"] = data["enabled"]
            else:
                now = time.time()
                if action == "claim" and (not prefs["enabled"] or now - prefs["last_shown"] < GREETING_INTERVAL):
                    return {"ok": True, "show": False, "greetings": prefs}
                prefs["last_shown"] = now
            self.store.put("top_panel_greetings", prefs)
            return {"ok": True, "show": action != "preferences", "greetings": prefs}

    def draft(self):
        with self.lock:
            saved = self.store.get("top_panel_draft")
            if not isinstance(saved, dict):
                text = ""
                try:
                    legacy = json.loads((self.store.directory / "companion-draft.json").read_text(encoding="utf-8"))
                    text = str(legacy.get("text", ""))[:20000]
                except (OSError, ValueError):
                    pass
                saved = {"text": text, "files": [], "revision": 0}
                self.store.put("top_panel_draft", saved)
            return saved

    def save(self, data):
        text = data.get("text")
        if not isinstance(text, str) or len(text) > 20000:
            raise ValueError("Qaralama 20 000 simvoldan uzun ola bilməz.")
        files = data.get("files")
        if files is not None:
            if not isinstance(files, list) or len(files) > 5:
                raise ValueError("Ən çox 5 fayl seç.")
            clean, total = [], 0
            for item in files:
                if not isinstance(item, dict) or not isinstance(item.get("data"), str) or len(item["data"]) > MAX_FILE * 4 // 3 + 8:
                    raise ValueError("Seçilmiş fayl ölçü limitini keçir.")
                try:
                    size = len(base64.b64decode(item["data"], validate=True))
                except (ValueError, binascii.Error):
                    raise ValueError("Fayl məzmunu düzgün deyil.") from None
                total += size
                if not 0 < size <= MAX_FILE or total > MAX_TOTAL or item.get("size") != size:
                    raise ValueError("Fayl limiti 20 MB, ümumi limit 25 MB-dır.")
                clean.append({"id": str(item.get("id", ""))[:100],
                              "name": str(item.get("name", "fayl")).replace("\\", "/").rsplit("/", 1)[-1][:180],
                              "type": str(item.get("type", "application/octet-stream"))[:100],
                              "size": size, "data": item["data"]})
            files = clean
        with self.lock:
            old = self.draft()
            saved = {"text": text, "files": old["files"] if files is None else files,
                     "revision": old.get("revision", 0) + 1}
            self.store.put("top_panel_draft", saved)
            # The original companion and the updater use this small marker too.
            atomic_json(self.store.directory / "companion-draft.json", {"text": text})
            return {"ok": True, "revision": saved["revision"]}

    def control(self, action):
        if action == "show":
            controller = self.controller
            if controller is None:
                raise ValueError("Üst chatbotu açmaq üçün ORION-u START.bat ilə başlat.")
            # Do not hold the service lock while the controller calls our local API.
            if not controller.show():
                raise ValueError("Üst chatbot açıla bilmədi. Masaüstü modulları üçün INSTALL.bat faylını aç.")
            with self.lock:
                self.close_requested = False
                self.show_sequence += 1
            return {"ok": True, "running": True}
        if action not in ("open", "close"):
            raise ValueError("Panel əməliyyatı düzgün deyil.")
        with self.lock:
            self.close_requested = action == "close"
        return {"ok": True}

    def has_draft(self):
        draft = self.draft()
        return bool(draft.get("text", "").strip() or draft.get("files"))
