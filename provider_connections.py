"""Private desktop credentials and real, read-only provider connection checks.

Windows keys are protected with the current user's DPAPI. On other platforms
the fallback is an owner-only file in ORION's existing application data folder.
No key is ever returned to the WebView or put in conversation/settings SQLite.
"""
import ctypes
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
import orion_http as http

PROVIDERS = {'anthropic': ('ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL', 'claude-opus-5'),
             'openai': ('OPENAI_API_KEY', 'OPENAI_MODEL', 'gpt-5.5')}


def protect(data, decrypt=False):
    if os.name != 'nt':
        return data
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt.CryptUnprotectData.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt.CryptProtectData.restype = crypt.CryptUnprotectData.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    incoming, outgoing = Blob(len(data), buffer), Blob()
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    # CRYPTPROTECT_UI_FORBIDDEN; do not bind the key to another computer/user.
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ValueError('Açarı Windows istifadəçi hesabında saxlamaq/oxumaq alınmadı.')
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


def private_write(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Connections:
    def __init__(self, store):
        self.store = store
        self.path = store.directory / 'provider-credentials.bin'
        self.lock = threading.RLock()
        self.credentials = {}
        self.load_error = False
        self.original = {env: os.environ.get(env, '') for env in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_WORKSPACE_ID')}
        if self.path.exists():
            try:
                raw = self.path.read_bytes()
                if raw.startswith(b'ORION-DPAPI\0'):
                    if os.name != 'nt':
                        raise ValueError('Windows hesabı tələb olunur.')
                    raw = protect(raw[12:], decrypt=True)
                elif raw.startswith(b'ORION-LOCAL\0'):
                    raw = raw[12:]
                else:
                    raise ValueError('Naməlum açar formatı.')
                self.credentials = json.loads(raw)
                if not isinstance(self.credentials, dict):
                    raise ValueError('Düzgün olmayan açar faylı.')
                for provider in PROVIDERS:
                    if isinstance(self.credentials.get(provider), dict):
                        self.publish(provider)
            except (OSError, ValueError, json.JSONDecodeError):
                self.credentials = {}
                self.load_error = True

    def key(self, provider):
        return self.credentials.get(provider, {}).get('key') or os.environ.get(PROVIDERS[provider][0], '')

    def workspace(self):
        value = self.credentials.get('anthropic', {}).get('workspace_id', os.environ.get('ANTHROPIC_WORKSPACE_ID', ''))
        return value if isinstance(value, str) and (not value or re.fullmatch(r'wrkspc_[A-Za-z0-9_-]{2,100}', value)) else ''

    def headers(self, provider, key=None, workspace_id=None):
        key = key if key is not None else self.key(provider)
        if provider == 'openai':
            return {'Authorization': 'Bearer ' + key}
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
        workspace = self.workspace() if workspace_id is None else workspace_id
        if workspace:
            headers['anthropic-workspace-id'] = workspace
        return headers

    def publish(self, provider):
        env = PROVIDERS[provider][0]
        os.environ[env] = self.credentials.get(provider, {}).get('key') or self.original.get(env, '')
        if provider == 'anthropic':
            os.environ['ANTHROPIC_WORKSPACE_ID'] = self.credentials.get(provider, {}).get('workspace_id', self.original['ANTHROPIC_WORKSPACE_ID'])

    def persist(self, value):
        raw = json.dumps(value).encode()
        private_write(self.path, b'ORION-DPAPI\0' + protect(raw) if os.name == 'nt' else b'ORION-LOCAL\0' + raw)

    def status(self):
        result = []
        for provider, (_, model_env, default) in PROVIDERS.items():
            checked = self.store.get('connection_' + provider, {})
            model = os.environ.get(model_env, default)
            if http.credential_in_model(model):
                model = ''
            result.append({'id': provider, 'name': 'Claude' if provider == 'anthropic' else 'OpenAI',
                           'configured': bool(self.key(provider)), 'source': 'panel' if self.credentials.get(provider, {}).get('key') else 'environment',
                           'workspace_id': self.workspace() if provider == 'anthropic' else '',
                           'model': model, 'checked_at': checked.get('checked_at'),
                           'models': checked.get('models', []), 'verified': bool(checked.get('verified'))})
        return {'providers': result, 'storage': 'Windows DPAPI' if os.name == 'nt' else 'Yalnız bu istifadəçinin faylı', 'load_error': self.load_error}

    def catalog(self, provider, key, workspace):
        base = os.environ.get('ANTHROPIC_BASE_URL' if provider == 'anthropic' else 'OPENAI_BASE_URL',
                              'https://api.anthropic.com/v1' if provider == 'anthropic' else 'https://api.openai.com/v1').rstrip('/')
        data = http.request(base + '/models' + ('?limit=100' if provider == 'anthropic' else ''), headers=self.headers(provider, key, workspace), timeout=20)
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            raise http.APIError('Model siyahısı xidmətdən düzgün gəlmədi.')
        rows = []
        for item in data['data'][:1000]:
            model = str(item.get('id', '')) if isinstance(item, dict) else ''
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}', model) or http.credential_in_model(model):
                continue
            if provider == 'openai' and not re.match(r'^(gpt-|chatgpt-|o[1345](?:-|$))', model):
                continue  # Audio/embedding/image models are not chat selections.
            if provider == 'anthropic' and not model.startswith('claude-'):
                continue
            display = str(item.get('display_name') or model)[:160]
            rows.append({'id': provider + ':' + model, 'name': model if http.credential_in_model(display) else display})
        return rows[:200]

    def update(self, data):
        provider, action = data.get('provider'), data.get('action', 'save')
        if provider not in PROVIDERS or action not in ('save', 'test', 'disconnect'):
            raise ValueError('Bağlantı əməliyyatını düzgün seç.')
        with self.lock:
            if action == 'disconnect':
                updated = {k: v for k, v in self.credentials.items() if k != provider}
                self.persist(updated)
                self.credentials = updated
                self.publish(provider)
                self.store.put('connection_' + provider, {})
                return {'ok': True, **self.status()}
            key = data.get('key') or self.key(provider)
            if not isinstance(key, str) or len(key) < 8 or len(key) > 2000 or re.search(r'[\s\x00-\x1f]', key) or not key.isascii():
                raise ValueError('Etibarlı API açarını açar sahəsinə yaz.')
            workspace = data.get('workspace_id', self.workspace()) if provider == 'anthropic' else ''
            if not isinstance(workspace, str) or (workspace and not re.fullmatch(r'wrkspc_[A-Za-z0-9_-]{2,100}', workspace)):
                raise ValueError('Workspace ID boş və ya wrkspc_ ilə başlayan identifikator olmalıdır.')
            rows = self.catalog(provider, key, workspace)
            if action == 'save':
                updated = {**self.credentials, provider: {'key': key, 'workspace_id': workspace}}
                self.persist(updated)  # A failed test/write never replaces a working connection.
                self.credentials = updated
                self.publish(provider)
                self.load_error = False
            self.store.put('connection_' + provider, {'checked_at': time.time(), 'models': rows, 'verified': True})
            return {'ok': True, 'models': rows, **self.status()}
