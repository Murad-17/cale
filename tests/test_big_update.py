"""Offline integration coverage for ORION Big Update."""
import base64
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
from engine import Engine
from dashboard_bridge import start
from orion_companion import LocalClient
from orion_http import APIError
from workspace_service import WorkspaceService
from update_installer import allowed_file


class Event:
    def __init__(self): self.callbacks = []
    def __iadd__(self, fn): self.callbacks.append(fn); return self


class BigUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-anthropic', 'OPENAI_API_KEY': 'test-openai', 'RUNWAYML_API_SECRET': 'test-runway'})
        self.env.start(); self.engine = Engine(self.temp.name)

    def tearDown(self):
        self.engine.close(); self.env.stop(); self.temp.cleanup()

    def reference(self):
        data = io.BytesIO(); Image.new('RGB', (120, 80), '#43bb88').save(data, 'PNG')
        return self.engine.media.video_service.reference({'data': base64.b64encode(data.getvalue()).decode()})

    def test_device_profile_hash_session_and_restart_preserve_workspace(self):
        service = self.engine.workspace
        self.engine.store.put('unrelated_user_data', {'keep': 17})
        data = {'email': 'Murad@example.test', 'name': 'Murad', 'password': 'a-long-local-pass'}
        result, cookie = service.authenticate('register', data)
        self.assertEqual(result['name'], 'Murad'); self.assertIn('HttpOnly; SameSite=Strict', cookie)
        self.assertTrue(service.profile_status(cookie)['authenticated'])
        self.assertNotIn(data['password'], json.dumps(self.engine.store.get('device_profile')))
        restarted = WorkspaceService(self.engine.store)
        self.assertTrue(restarted.profile_status()['registered']); self.assertFalse(restarted.profile_status()['authenticated'])
        _, login_cookie = restarted.authenticate('login', {**data, 'email': 'murad@EXAMPLE.TEST'})
        self.assertTrue(restarted.profile_status(login_cookie)['authenticated'])
        restarted.authenticate('logout', {})
        self.assertFalse(restarted.profile_status(login_cookie)['authenticated'])
        self.assertEqual(self.engine.store.get('unrelated_user_data'), {'keep': 17})
        with self.assertRaises(ValueError): service.authenticate('register', data)
        with self.assertRaises(ValueError): service.authenticate('login', {**data, 'password': 'incorrect-pass'})

    def test_device_login_attempts_are_bounded(self):
        service = self.engine.workspace
        service.authenticate('register', {'email': 'x@example.test', 'name': 'X', 'password': 'long-password'})
        with patch('workspace_service.time.time', return_value=100000):
            for _ in range(8):
                with self.assertRaises(ValueError): service.authenticate('login', {'email': 'x@example.test', 'password': 'wrong-password'})
            with self.assertRaisesRegex(ValueError, 'Çox cəhd'):
                service.authenticate('login', {'email': 'x@example.test', 'password': 'long-password'})

    def test_detached_windows_deduplicate_and_reopen_after_close(self):
        service = self.engine.workspace
        self.assertFalse(service.open_widget('note-test')['native'])
        window = SimpleNamespace(show=Mock(), restore=Mock(), destroy=Mock(), events=SimpleNamespace(closed=Event()))
        service.opener = Mock(return_value=window)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: service.open_widget('note-test'), range(4)))
        self.assertTrue(all(r['native'] for r in results)); service.opener.assert_called_once_with('note-test', '/?widget=note-test')
        window.events.closed.callbacks[0](); service.open_widget('note-test')
        self.assertEqual(service.opener.call_count, 2); service.close_all(); window.destroy.assert_called_once()
        for key in ('../../.env', 'https://external.test', 'bad?key', None):
            with self.assertRaises(ValueError): service.open_widget(key)

    def test_reference_validation_and_image_to_video_payload(self):
        reference = self.reference()
        self.assertTrue((self.engine.media.directory/reference['id']).is_file())
        payload = self.engine.media.video_service.prepare('Slow camera movement', {'reference_id': reference['id'], 'size': '720x1280', 'seconds': 10})
        self.assertEqual(payload['model'], 'gen4.5'); self.assertEqual(payload['ratio'], '720:1280'); self.assertEqual(payload['duration'], 10)
        with Image.open(io.BytesIO(base64.b64decode(payload['promptImage'].split(',')[1]))) as image:
            self.assertEqual(image.size, (720, 1280))
        for options in ({'seconds': 4}, {'size': 'arbitrary'}, {'reference_id': '../.env'}, {'reference_id': 'a'*32+'.png'}):
            with self.assertRaises(ValueError): self.engine.media.video_service.prepare('Scene', options)
        for raw in ('not-base64', base64.b64encode(b'not an image').decode()):
            with self.assertRaises(ValueError): self.engine.media.video_service.reference({'data': raw})

    def test_runway_poll_resumes_without_duplicate_paid_create_or_cdn_secret(self):
        with patch('orion_http.request', return_value={'id': 'task_fixture'}) as create:
            result = self.engine.media.video('Scene')
        self.assertEqual(create.call_args.args[0], 'https://api.dev.runwayml.com/v1/image_to_video')
        self.assertEqual(create.call_args.args[2]['promptText'], 'Scene')
        self.assertEqual(create.call_args.args[3]['X-Runway-Version'], '2024-11-06')
        with patch('orion_http.request', side_effect=APIError('offline')): self.engine.media.poll_videos()
        self.assertEqual(self.engine.store.jobs()[0]['status'], 'waiting')
        with patch('orion_http.request', side_effect=[{'status': 'SUCCEEDED', 'output': ['https://cdn.runway.test/result.mp4']}, b'video-fixture']) as poll:
            self.engine.media.poll_videos()
        self.assertNotIn('headers', poll.call_args_list[1].kwargs)
        job = next(j for j in self.engine.store.jobs() if j['id']==result['job_id'])
        self.assertEqual(job['status'], 'completed'); self.assertEqual((self.engine.media.directory/job['result']['file']).read_bytes(), b'video-fixture')
        self.assertEqual(create.call_count, 1)

    def test_retired_video_jobs_never_claim_completion(self):
        job = self.engine.store.job('video', 'Old Sora task')
        self.engine.store.update(job, 'waiting', result={'remote_id': 'old_sora_id'})
        with patch('orion_http.request') as network: self.engine.media.poll_videos()
        network.assert_not_called()
        saved = next(j for j in self.engine.store.jobs() if j['id']==job)
        self.assertEqual(saved['status'], 'failed'); self.assertIn('bağlanıb', saved['result']['error'])

    def test_modes_change_behavior_and_preserve_user_instructions(self):
        self.engine.save_settings({'assistantMode': 'code', 'assistantMood': 'focused', 'persona': 'Keep my preference'})
        prompt = self.engine.instructions(self.engine.settings)
        self.assertIn('Kod və texniki iş', prompt); self.assertIn('Keep my preference', prompt)
        with self.assertRaises(ValueError): self.engine.save_settings({'assistantMode': 'fake-model'})
        self.assertEqual(self.engine.settings['assistantMode'], 'code')
        with patch.object(self.engine.pool, 'submit') as submit: self.engine.submit('Research this', settings={'assistantMode': 'research'})
        self.assertEqual(submit.call_args.args[3]['researchMode'], 'deep'); self.assertEqual(self.engine.settings['researchMode'], 'auto')

    def test_http_routes_protect_origins_and_never_return_secrets(self):
        server=start(0,self.engine); url=f'http://127.0.0.1:{server.server_address[1]}'; client=LocalClient(url)
        try:
            self.assertEqual(client.request('/api/video/settings')['provider'], 'Runway')
            self.assertNotIn('test-runway', json.dumps(client.request('/api/settings')))
            self.assertIn('registered', client.request('/api/workspace/profile'))
            for route in ('/api/widgets/open','/api/workspace/register','/api/video/settings'):
                req=urllib.request.Request(url+route,data=b'{}',headers={'Content-Type':'application/json','Origin':'https://external.test'})
                with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(req)
                self.assertEqual(error.exception.code,403)
            for path,mime in (('/orion-big.js','application/javascript'),('/orion-big.css','text/css'),('/orion-modes.js','application/javascript')):
                with urllib.request.urlopen(url+path) as response:
                    self.assertEqual(response.headers.get_content_type(),mime); self.assertGreater(len(response.read()),100)
        finally: server.shutdown(); server.server_close()

    def test_release_allowlist_covers_update_and_excludes_credentials(self):
        for name in ('workspace_service.py','assistant_modes.py','video_service.py','orion_big.js','orion_big.css','orion_modes.js','panel_assets/orion-entry.png'):
            self.assertTrue(allowed_file(name),name)
        for name in ('device_profile.json','runway_api_secret','.env','panel_assets/../../.env'):
            self.assertFalse(allowed_file(name),name)

if __name__=='__main__': unittest.main()
