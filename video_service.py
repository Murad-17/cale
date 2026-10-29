"""Runway image/text-to-video transport. Secrets never reach browser responses.
Protocol: https://docs.dev.runwayml.com/guides/using-the-api/
"""
import base64
import io
import math
import os
import re
import threading
import uuid
from urllib.parse import urlsplit
import orion_http as http

BASE = 'https://api.dev.runwayml.com/v1'


class VideoService:
    def __init__(self, media):
        self.media = media
        self.store = media.store
        self.poll_lock = threading.Lock()

    def key(self):
        value = os.environ.get('RUNWAYML_API_SECRET') or self.store.get('runway_api_secret', '')
        if not value:
            raise http.APIError('Video yaratmaq üçün studiyada Runway API açarını qoş.')
        return {'Authorization': 'Bearer ' + value, 'X-Runway-Version': '2024-11-06'}

    def available(self):
        return bool(os.environ.get('RUNWAYML_API_SECRET') or self.store.get('runway_api_secret', ''))

    def save_key(self, value):
        if not isinstance(value, str) or not re.fullmatch(r'key_[A-Za-z0-9_-]{20,500}', value.strip()):
            raise ValueError('Runway hesabındakı etibarlı API açarını daxil et.')
        self.store.put('runway_api_secret', value.strip())
        return {'ok': True, 'configured': True}

    def reference(self, item):
        if not isinstance(item, dict) or not isinstance(item.get('data'), str) or len(item['data']) > 28_000_000:
            raise ValueError('PNG, JPEG və ya WebP şəkli seç. Limit 20 MB-dır.')
        try:
            raw = base64.b64decode(item['data'], validate=True)
            if not raw or len(raw) > 20 * 1024 * 1024:
                raise ValueError()
            from PIL import Image, ImageOps
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP') or image.width * image.height > 25_000_000:
                    raise ValueError()
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1920, 1920))
                frame = image.convert('RGBA')
                output = io.BytesIO(); frame.save(output, 'PNG')
            name = uuid.uuid4().hex + '.png'
            (self.media.directory / name).write_bytes(output.getvalue())
            return {'ok': True, 'id': name, 'url': '/api/media/files/' + name,
                    'width': frame.width, 'height': frame.height}
        except Exception:
            # Pillow also rejects malformed/decompression-bomb inputs; do not expose parser internals.
            raise ValueError('Şəkil oxunmadı. 25 meqapikseldən və 20 MB-dan kiçik PNG, JPEG və ya WebP seç.') from None

    def prepare(self, prompt, options):
        self.key()
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1000:
            raise ValueError('Video təsvirini 1–1000 simvol arasında yaz.')
        options = options or {}
        duration = options.get('seconds', 5)
        size = options.get('size', '1280x720')
        if type(duration) is not int or duration not in (5, 10) or size not in ('1280x720', '720x1280'):
            raise ValueError('Video ölçüsü və müddəti düzgün deyil.')
        payload = {'model': 'gen4.5', 'promptText': prompt.strip(), 'ratio': size.replace('x', ':'), 'duration': duration}
        reference = options.get('reference_id')
        if reference:
            if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}\.png', reference):
                raise ValueError('İstinad şəkli düzgün deyil.')
            path = self.media.directory / reference
            if not path.is_file():
                raise ValueError('İstinad şəkli tapılmadı. Yenidən seç.')
            from PIL import Image, ImageOps
            with Image.open(path) as image:
                target = tuple(map(int, size.split('x')))
                image = ImageOps.contain(image.convert('RGB'), target)
                frame = Image.new('RGB', target, '#101014')
                frame.paste(image, ((target[0] - image.width)//2, (target[1] - image.height)//2))
                output = io.BytesIO(); frame.save(output, 'JPEG', quality=92)
            payload['promptImage'] = 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()
        return payload

    def create(self, prompt, job_id=None, options=None, payload=None):
        payload = payload or self.prepare(prompt, options)
        job_id = job_id or self.store.job('video', prompt)
        self.store.update(job_id, 'running')
        try:
            result = http.request(BASE + '/image_to_video', 'POST', payload, self.key(), timeout=120)
            remote = result.get('id', '')
            if not isinstance(remote, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', remote):
                raise ValueError('Video identifikatoru alınmadı.')
            output = {'provider': 'runway', 'remote_id': remote, 'prompt': prompt, 'kind': 'video',
                      'seconds': payload['duration'], 'size': payload['ratio'].replace(':', 'x')}
            self.store.update(job_id, 'waiting', result=output)
            return {'job_id': job_id, 'status': 'waiting', **output}
        except Exception:
            self.store.update(job_id, 'failed', result={'error': 'Video sorğusu qəbul edilmədi. Runway açarını, modelə çıxışı və balansı yoxla.'})
            raise

    def poll(self):
        if not self.poll_lock.acquire(blocking=False):
            return
        try:
            for job in self.store.jobs():
                if job['kind'] != 'video' or job['status'] != 'waiting':
                    continue
                if job['result'].get('provider') != 'runway':
                    self.store.update(job['id'], 'failed', result={**job['result'], 'error': 'Əvvəlki Sora video xidməti bağlanıb. Yeni videonu studiyada Runway ilə yarat.'})
                    continue
                try:
                    remote = job['result']['remote_id']
                    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', remote):
                        raise ValueError()
                    result = http.request(BASE + '/tasks/' + remote, headers=self.key(), timeout=30)
                    state = result.get('status')
                    if state == 'SUCCEEDED':
                        output = result.get('output') or []
                        address = output[0] if output else ''
                        parsed = urlsplit(address)
                        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.hostname in ('localhost', '127.0.0.1', '::1'):
                            raise ValueError('Video ünvanı etibarlı deyil.')
                        # The CDN never receives the Runway API secret.
                        data = http.request(address, timeout=180)
                        if not isinstance(data, bytes) or not data or len(data) > 100 * 1024 * 1024:
                            raise ValueError('Video faylı alınmadı.')
                        name = job['id'] + '.mp4'
                        path = self.media.directory / name
                        temporary = path.with_suffix('.part'); temporary.write_bytes(data); temporary.replace(path)
                        self.store.update(job['id'], 'completed', current=1, result={**job['result'], 'file': name, 'url': '/api/media/files/' + name})
                        self.store.message('orion', 'Video hazırdır. Yaradıcı studiyada baxa və endirə bilərsən.', read_aloud=False)
                    elif state in ('FAILED', 'CANCELED', 'CANCELLED'):
                        self.store.update(job['id'], 'failed', result={**job['result'], 'error': 'Video xidməti bu sorğunu tamamlaya bilmədi. Başqa təsvirlə yenidən yoxla.'})
                    elif isinstance(result.get('progress'), (int, float)) and math.isfinite(result['progress']):
                        self.store.update(job['id'], 'waiting', current=max(0, min(.99, result['progress'])), result=job['result'])
                except (http.APIError, ValueError, KeyError, OSError):
                    # Retain the remote ID and resume polling; never submit a second paid request.
                    continue
        finally:
            self.poll_lock.release()
