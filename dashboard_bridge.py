"""One local HTTP server for the existing dashboard and ORION runtime.
No Flask, no permissive CORS, no arbitrary static directory serving.
"""
import json
import mimetypes
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit
import config
import orion_http

state = SimpleNamespace(on_user_message=None)
MAX_BODY = 38 * 1024 * 1024


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def engine(self):
        return self.server.engine

    def log_message(self, *_):
        pass

    def respond(self, value, status=200, mime="application/json; charset=utf-8", cookie=None):
        if not isinstance(value, bytes):
            value = json.dumps(value, ensure_ascii=False).encode() if mime.startswith("application/json") else str(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(value)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(value)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def valid_host(self):
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        return host in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self):
        if not self.valid_host():
            return self.respond({"error": "Host qəbul edilmir."}, 403)
        try:
            self.get_route()
        except (ValueError, KeyError, OSError):
            self.respond({"error": "Sorğu icra edilə bilmədi."}, 400)

    def get_route(self):
        url = urlsplit(self.path)
        path, query, engine = url.path, parse_qs(url.query), self.engine
        if path in ("/", "/dashboard", "/orion_dashboard.html"):
            return self.respond((config.ROOT / "orion_dashboard.html").read_bytes(), mime="text/html; charset=utf-8")
        if path in ("/panel", "/orion_panel.html"):
            return self.respond((config.ROOT / "orion_panel.html").read_bytes(), mime="text/html; charset=utf-8")
        if path == "/robot-animator.js":
            return self.respond((config.ROOT / "robot_animator.js").read_bytes(), mime="application/javascript; charset=utf-8")
        if path in ('/companion-hub.js', '/companion-hub.css'):
            name = 'companion_hub.js' if path.endswith('.js') else 'companion_hub.css'
            return self.respond((config.ROOT / name).read_bytes(), mime='application/javascript' if path.endswith('.js') else 'text/css')
        if path == '/api/companion/state':
            return self.respond(engine.companion.snapshot())
        if path == '/api/companion/statistics':
            from usage_stats import statistics
            return self.respond(statistics(engine.store, query.get('period', ['month'])[0]))
        if path == '/api/companion/messages':
            thread_id = engine.companion.require_thread(query.get('thread', [''])[0])
            return self.respond({'thread_id': thread_id, 'messages': engine.store.messages(max(0, int(query.get('since', [0])[0])), thread_id=thread_id)})
        if path in ('/orion-big.js', '/orion-big.css', '/orion-modes.js', '/orion-premium.css', '/orion-premium.js', '/orion-fonts.css', '/password-meter.css', '/password-meter.js'):
            names = {'/orion-big.js': 'orion_big.js', '/orion-big.css': 'orion_big.css', '/orion-modes.js': 'orion_modes.js',
                     '/orion-premium.css': 'orion_premium.css', '/orion-premium.js': 'orion_premium.js',
                     '/orion-fonts.css': 'orion_fonts.css', '/password-meter.css': 'password_meter.css', '/password-meter.js': 'password_meter.js'}
            return self.respond((config.ROOT / names[path]).read_bytes(), mime='text/css' if path.endswith('.css') else 'application/javascript')
        if path == '/api/workspace/profile':
            return self.respond(engine.workspace.profile_status(self.headers.get('Cookie', '')))
        if path == '/api/widgets':
            return self.respond({'native': callable(engine.workspace.opener), 'open': list(engine.workspace.windows)})
        if path == '/api/video/settings':
            return self.respond({'configured': engine.media.video_available(), 'provider': 'Runway', 'seconds': [5, 10], 'sizes': ['1280x720', '720x1280']})
        if path.startswith("/panel-assets/"):
            name = path.removeprefix("/panel-assets/")
            if re.fullmatch(r"fonts/(Poppins-(Regular|Medium|SemiBold|Bold)|EuclidCircularA-(Light|Regular|Medium|SemiBold|Bold)(Italic)?|JetBrainsMono-(Latin|LatinExt)-(Regular|Medium))\.woff", name):
                return self.respond((config.ROOT / "panel_assets" / name).read_bytes(), mime="font/woff")
            if name not in ("orion-idle.png", "orion-happy.png", "orion-wink.png", "orion-focus.png", "orion-shell.png", "orion-entry.png"):
                return self.respond({"error": "Şəkil tapılmadı."}, 404)
            return self.respond((config.ROOT / "panel_assets" / name).read_bytes(), mime="image/png")
        if path == "/api/panel/draft":
            return self.respond(engine.panel.draft())
        if path == "/api/panel/status":
            return self.respond(engine.panel.status())
        if path == "/api/panel/appearance":
            return self.respond(engine.panel.appearance())
        if path == "/api/messages/head":
            return self.respond({"next_id": engine.store.next_message_id()})
        if path == "/api/updates":
            return self.respond(engine.updater.status("top" if query.get("surface") == ["top"] else "dashboard"))
        if path == "/api/messages":
            since = max(0, int(query.get("since", [0])[0]))
            return self.respond({"messages": engine.store.messages(since, global_only=True)})
        if path == "/api/settings":
            return self.respond({"ok": True, "settings": engine.settings, "capabilities": engine.capabilities(), "key_status": {name: bool(os.environ.get(env)) for name, env in [("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY"), ("elevenlabs", "ELEVENLABS_API_KEY")]}})
        if path == "/api/models":
            return self.respond({"models": engine.models()})
        if path == "/api/status":
            try:
                from blender_bridge import find_blender
                find_blender()
                blender = "hazır"
            except Exception:
                blender = "qoşulmadı"
            roblox = bool(engine.roblox and time.time() - engine.roblox._last_seen < 8)
            return self.respond({"nodes": {"orion": {"status": "hazır"}, "blender": {"status": blender}, "roblox": {"status": "qoşuldu" if roblox else "qoşulmadı"}, "forge": {"status": "qoşuldu" if engine.last_provider_ok else "qoşulmadı"}}})
        if path in ("/api/tasks", "/api/jobs"):
            jobs = engine.store.jobs()
            if query.get('thread'):
                thread_id = engine.companion.require_thread(query['thread'][0])
                with engine.store.connection() as db:
                    owned = {r[0] for r in db.execute('SELECT job_id FROM companion_jobs WHERE thread_id=?', (thread_id,))}
                jobs = [j for j in jobs if j['id'] in owned]
            for job in jobs:
                if job["status"] in ("failed", "interrupted"):
                    job["label"] += " · " + ("xəta" if job["status"] == "failed" else "yarımçıq qalıb")
            return self.respond({"tasks" if path.endswith("tasks") else "jobs": jobs})
        if path == "/api/statistics":
            return self.respond(engine.store.statistics())
        if path == "/api/voice/status":
            return self.respond(engine.voice.status() if engine.voice else {"state": "unavailable", "note": "Səs modulu başlamayıb."})
        if path.startswith("/api/media/files/"):
            name = unquote(path.rsplit("/", 1)[-1])
            if not re.fullmatch(r"[0-9a-f]{32}\.(png|mp4)", name):
                return self.respond({"error": "Fayl tapılmadı."}, 404)
            file = engine.media.directory / name
            if not file.is_file():
                return self.respond({"error": "Fayl tapılmadı."}, 404)
            return self.respond(file.read_bytes(), mime=mimetypes.guess_type(name)[0] or "application/octet-stream")
        if path == "/manifest.json":
            return self.respond({"name": "ORION", "short_name": "ORION", "start_url": "/", "display": "standalone", "background_color": "#07050f", "theme_color": "#6d4cff"})
        if path == "/sw.js":
            # Retire old shell caches so an older HTML version cannot hide runtime updates.
            return self.respond(b"self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(n=>n.startsWith('orion-')).map(n=>caches.delete(n)))).then(()=>self.registration.unregister())));", mime="application/javascript")
        return self.respond({"error": "Tapılmadı."}, 404)

    def do_POST(self):
        port = self.server.server_address[1]
        origin = self.headers.get("Origin")
        if not self.valid_host() or (origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")):
            return self.respond({"error": "Bu mənbədən əmr qəbul edilmir."}, 403)
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size < 1 or size > MAX_BODY:
                return self.respond({"error": "Sorğu ölçüsü limitdən kənardır."}, 413)
            raw = self.rfile.read(size)
            if self.path == "/api/voice/transcribe":
                if size > 12 * 1024 * 1024:
                    return self.respond({"error": "Səs yazısı çox uzundur."}, 413)
                text = self.engine.media.transcribe(raw, self.headers.get("Content-Type", "audio/webm"), self.engine.settings["language"])
                return self.respond({"text": text})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self.respond({"error": "JSON tələb olunur."}, 415)
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON obyekt olmalıdır.")
            return self.post_route(data)
        except (ValueError, json.JSONDecodeError) as error:
            return self.respond({"error": str(error)[:400]}, 400)
        except orion_http.APIError as error:
            return self.respond({"error": str(error)}, 502)
        except PermissionError:
            return self.respond({'error': 'Bu əməliyyat üçün icazə yoxdur.'}, 403)
        except Exception:
            return self.respond({"error": "Server əməliyyatı tamamlaya bilmədi."}, 500)

    def post_route(self, data):
        engine = self.engine
        if self.path == '/api/companion/thread':
            return self.respond(engine.companion.thread(data))
        if self.path == '/api/companion/preferences':
            return self.respond({'ok': True, 'preferences': engine.companion.preferences(data)})
        if self.path == '/api/companion/memory':
            return self.respond({'ok': True, 'memory': engine.companion.memory(data)})
        if self.path == '/api/companion/tasks':
            return self.respond({'ok': True, 'tasks': engine.companion.tasks(data)})
        if self.path == '/api/companion/approval':
            return self.respond(engine.companion.decide(data.get('id'), data.get('allow')))
        if self.path == '/api/companion/connection':
            return self.respond(engine.connections.update(data))
        if self.path == '/api/companion/hooks':
            return self.respond(engine.companion.hook_control(data.get('enabled')))
        if self.path == '/api/companion/agent-event':
            token = self.headers.get('Authorization', '').removeprefix('Bearer ')
            return self.respond(engine.companion.agent_event(data, token))
        if self.path == '/api/companion/send':
            thread_id = engine.companion.require_thread(data.get('thread_id'))
            if engine.companion.busy(thread_id):
                raise ValueError('Bu söhbətin cari cavabını gözlə.')
            if sum(j['status'] in ('queued', 'running') for j in engine.store.jobs()) > 8:
                return self.respond({'error': 'Növbə doludur; cari işi gözlə.'}, 429)
            return self.respond(engine.submit(data.get('text'), data.get('attachments'), data.get('settings'), source='companion', thread_id=thread_id))
        if self.path in ('/api/workspace/register', '/api/workspace/login', '/api/workspace/logout'):
            result, cookie = engine.workspace.authenticate(self.path.rsplit('/', 1)[-1], data)
            return self.respond(result, cookie=cookie)
        if self.path == '/api/widgets/open':
            return self.respond(engine.workspace.open_widget(data.get('key')))
        if self.path == '/api/video/settings':
            return self.respond(engine.media.video_service.save_key(data.get('key')))
        if self.path == '/api/studio/reference':
            return self.respond(engine.media.video_service.reference(data.get('file')))
        if self.path == "/api/panel/draft":
            return self.respond(engine.panel.save(data))
        if self.path == "/api/panel/control":
            return self.respond(engine.panel.control(data.get("action")))
        if self.path == "/api/panel/appearance":
            return self.respond(engine.panel.save_appearance(data))
        if self.path == "/api/panel/greeting":
            return self.respond(engine.panel.greeting(data))
        if self.path == "/api/updates/preferences":
            return self.respond(engine.updater.preferences(data.get("consent"), data.get("automatic")))
        if self.path == "/api/updates/check":
            return self.respond(engine.updater.check())
        if self.path == "/api/updates/download":
            return self.respond(engine.updater.download())
        if self.path == "/api/updates/notice":
            return self.respond(engine.updater.notice(str(data.get("event", "")), data.get("later") is True))
        if self.path == "/api/updates/session":
            return self.respond(engine.updater.heartbeat(data.get("session"), data.get("dirty"), data.get("surface", "dashboard")))
        if self.path == "/api/updates/session/close":
            return self.respond(engine.updater.close_session(data.get("session")))
        if self.path == "/api/updates/install":
            return self.respond(engine.updater.install(data.get("session"), data.get("confirmed") is True, data.get("snapshot")))
        if self.path == "/api/desktop/show":
            show = getattr(engine, "desktop_show", None)
            if not callable(show):
                raise ValueError("Əsas panel hazır deyil. ORION-u START.bat ilə aç.")
            show()
            return self.respond({"ok": True})
        if self.path == "/api/send":
            if getattr(engine, "updater", None) and engine.updater.status()["phase"] == "installing":
                raise ValueError("ORION yenidən başladılır. Bir az sonra davam et.")
            if sum(j["status"] in ("queued", "running") for j in engine.store.jobs()) > 8:
                return self.respond({"error": "Növbə doludur; cari tapşırığı gözlə."}, 429)
            return self.respond(engine.submit(data.get("text"), data.get("attachments"), data.get("settings")))
        if self.path == "/api/settings":
            engine.save_settings(data.get("settings", {}))
            if engine.voice:
                engine.voice.configure(bool(engine.settings.get("wakeEnabled")))
            return self.respond({"ok": True, "saved": True, "capabilities": engine.capabilities()})
        if self.path == "/api/context":
            engine.save_settings({"workspaceContext": data.get("context", {}), **{key: data[key] for key in ("profile", "memory", "persona", "systemPrompt") if key in data}})
            return self.respond({"ok": True})
        if self.path == "/api/tts":
            text = str(data.get("text", "")).strip()
            if not text:
                raise ValueError("Səsləndirmək üçün mətn yoxdur.")
            audio = engine.media.speech(text, engine.settings["language"], data.get("provider", engine.settings.get("ttsProvider", "openai")))
            return self.respond(audio, mime="audio/wav")
        if self.path == "/api/media":
            with engine.work_gate:
                if getattr(engine, "updater", None) and engine.updater.status()["phase"] == "installing":
                    raise ValueError("ORION yenidən başladılır. Bir az sonra davam et.")
                kind, prompt = data.get("kind"), str(data.get("prompt", "")).strip()
                if kind not in ("image", "video") or not prompt or len(prompt) > 8000:
                    raise ValueError("Şəkil/video növünü və təsviri düzgün seç.")
                payload = None
                if kind == 'video':
                    payload = engine.media.video_service.prepare(prompt, data.get('options'))
                    if any(j['kind'] == 'video' and j['status'] in ('queued', 'running', 'waiting') for j in engine.store.jobs()):
                        raise ValueError('Cari videonun tamamlanmasını gözlə. Eyni anda bir video yaradılır.')
                else:
                    engine.media.key()
                job_id = engine.store.job(kind, prompt)
                def create():
                    try:
                        if kind == 'video':
                            engine.media.video(prompt, job_id, payload=payload)
                        else:
                            engine.media.image(prompt, job_id)
                    except Exception:
                        pass  # The media service persists a truthful failed state.
                engine.pool.submit(create)
                return self.respond({"ok": True, "job_id": job_id})
        if self.path == "/api/voice/listen":
            if not engine.voice:
                raise ValueError("Səs xidməti hazır deyil.")
            if data.get('thread_id'):
                engine.companion.require_thread(data['thread_id'])
                return self.respond(engine.voice.activate(thread_id=data['thread_id']))
            return self.respond(engine.voice.activate())
        if self.path == "/api/voice/wake":
            if not engine.voice:
                raise ValueError("Səs xidməti hazır deyil.")
            enabled = data.get("enabled") is True
            engine.save_settings({"wakeEnabled": enabled})
            engine.voice.configure(enabled)
            return self.respond(engine.voice.status())
        return self.respond({"error": "Tapılmadı."}, 404)


def start(port=8765, engine=None, background=True):
    if engine is None:
        from engine import Engine
        engine = Engine()
    server = LocalServer(("127.0.0.1", port), Handler)
    server.engine = engine
    if getattr(engine, 'companion', None):
        engine.companion.port = server.server_address[1]
        if engine.store.get('companion_hooks', False):
            engine.companion.hook_control(True)
    if background:
        threading.Thread(target=server.serve_forever, daemon=True, name="orion-http").start()
    else:
        server.serve_forever()
    return server
