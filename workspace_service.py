"""Local device profiles and bounded detachable workspace windows.

Profiles provide a local sign-in experience, not a cloud account or disk encryption.
The existing localhost API continues to rely on the operating-system user boundary.
"""
import hashlib
import hmac
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie
from urllib.parse import quote


class WorkspaceService:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.sessions = {}
        self.failures = []
        self.windows = {}
        self.opener = None

    def profile_status(self, cookie=''):
        saved = self.store.get('device_profile') or {}
        parsed = SimpleCookie()
        try:
            parsed.load(cookie)
            token = parsed.get('orion_device')
            expires = self.sessions.get(token.value, 0) if token else 0
        except Exception:
            expires = 0
        return {'registered': bool(saved), 'authenticated': expires > time.time(),
                'name': saved.get('name', ''), 'email': saved.get('email', '')}

    def authenticate(self, action, data):
        with self.lock:
            if action == 'logout':
                self.sessions.clear()
                return {'ok': True}, 'orion_device=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
            saved = self.store.get('device_profile') or {}
            email = str(data.get('email', '')).strip().casefold()
            password = data.get('password', '')
            if not isinstance(password, str) or not 8 <= len(password) <= 200 or not re.fullmatch(r'[^\s@]{1,100}@[^\s@]{1,150}\.[^\s@]{2,30}', email):
                raise ValueError('E-poçtu və ən azı 8 simvolluq şifrəni yoxla.')
            now = time.time()
            self.failures = [t for t in self.failures if now - t < 60]
            if len(self.failures) >= 8:
                raise ValueError('Çox cəhd edildi. Bir dəqiqə sonra yenidən yoxla.')
            if action == 'register':
                if saved:
                    raise ValueError('Bu cihazda artıq profil var. Daxil ol seçimini istifadə et.')
                name = str(data.get('name', '')).strip()[:60]
                if not name:
                    raise ValueError('Adını daxil et.')
                salt = secrets.token_bytes(24)
                digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000)
                saved = {'name': name, 'email': email, 'salt': salt.hex(), 'hash': digest.hex()}
                self.store.put('device_profile', saved)
            elif action == 'login':
                salt = bytes.fromhex(saved.get('salt', '00' * 24))
                digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000).hex()
                if not saved or email != saved.get('email') or not hmac.compare_digest(digest, saved.get('hash', '')):
                    self.failures.append(now)
                    raise ValueError('E-poçt və ya şifrə düzgün deyil.')
            else:
                raise ValueError('Giriş əməliyyatı düzgün deyil.')
            self.sessions = {t: expiry for t, expiry in self.sessions.items() if expiry > now}
            token = secrets.token_urlsafe(32)
            self.sessions[token] = now + 8 * 3600
            return {'ok': True, 'name': saved['name'], 'email': saved['email']}, (
                'orion_device=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')

    def open_widget(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', key):
            raise ValueError('Tab identifikatoru düzgün deyil.')
        url = '/?widget=' + quote(key)
        with self.lock:
            if not self.opener:
                return {'ok': True, 'native': False, 'url': url}
            previous = self.windows.get(key)
            if previous is not None:
                try:
                    previous.show(); previous.restore()
                    return {'ok': True, 'native': True, 'url': url}
                except Exception:
                    self.windows.pop(key, None)
            window = self.opener(key, url)
            self.windows[key] = window
            def closed(*_):
                with self.lock:
                    if self.windows.get(key) is window:
                        self.windows.pop(key, None)
            window.events.closed += closed
            return {'ok': True, 'native': True, 'url': url}

    def close_all(self):
        with self.lock:
            windows = list(self.windows.values())
            self.windows.clear()
        for window in windows:
            try:
                window.destroy()
            except Exception:
                pass
