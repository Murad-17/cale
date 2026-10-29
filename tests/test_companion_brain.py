"""Functional companion tests with actual SQLite/HTTP and fake upstream only."""
import concurrent.futures
import io
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch, Mock
from engine import Engine
from storage import Store
from dashboard_bridge import start
from orion_http import APIError, AnthropicClient
from provider_connections import Connections
from voice_service import VoiceService
import orion_agent_hook


class BrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'fixture-not-a-real-secret', 'ANTHROPIC_MODEL': 'claude-fixture', 'OPENAI_API_KEY': '', 'ANTHROPIC_WORKSPACE_ID': ''})
        self.environment.start()
        self.engine = Engine(self.temp.name)
        self.brain = self.engine.companion
        self.thread = self.brain.active_thread()
        self.settings = {**self.engine.settings, '_source': 'companion', '_thread_id': self.thread}

    def tearDown(self):
        self.engine.close()
        self.environment.stop()
        self.temp.cleanup()

    def wait(self, predicate):
        for _ in range(300):
            value = predicate()
            if value:
                return value
            time.sleep(.01)
        self.fail('Operation did not complete')

    def test_additive_schema_preserves_old_messages_and_settings(self):
        self.engine.close()
        old = Path(self.temp.name) / 'old'
        old.mkdir()
        with sqlite3.connect(old / 'orion.sqlite3') as db:
            db.executescript('CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender TEXT,text TEXT,extras TEXT,created REAL); INSERT INTO messages VALUES (1,\'user\',\'Mövcud məlumat\',\'{}\',1); CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT); INSERT INTO settings VALUES (\'kept\',\'42\');')
        migrated = Store(old)
        self.assertEqual(migrated.messages()[0]['text'], 'Mövcud məlumat')
        self.assertEqual(migrated.get('kept'), 42)
        self.assertEqual(migrated.message('user', 'Yeni'), 2)

    def test_threads_isolate_actual_model_context_from_each_other_and_dashboard(self):
        store = self.engine.store
        store.message('user', 'Dashboard məlumatı')
        first = store.message('user', 'Birinci layihə', thread_id=self.thread)
        store.message('orion', 'Birinci cavab', thread_id=self.thread, reply_to=first)
        other = self.brain.thread({'action': 'new'})['id']
        second = store.message('user', 'İkinci layihə', thread_id=other)
        self.assertEqual([m['text'] for m in store.history(before=second)], ['İkinci layihə'])
        self.assertEqual([m['text'] for m in store.history(before=first)], ['Birinci layihə'])
        self.assertEqual([m['text'] for m in store.history()], ['Dashboard məlumatı'])
        with patch('orion_http.request', return_value={'content': [{'type': 'text', 'text': 'Yalnız ikinci.'}], 'usage': {}}) as request:
            self.engine.answer(second, {**self.settings, '_thread_id': other})
        self.assertEqual([m['content'][0]['text'] for m in request.call_args.args[2]['messages']], ['İkinci layihə'])

    def test_thread_archive_retains_data_but_removes_it_from_active_navigation(self):
        self.engine.store.message('user', 'Qorunsun', thread_id=self.thread)
        result = self.brain.thread({'action': 'archive', 'id': self.thread})
        self.assertNotEqual(result['active_thread'], self.thread)
        self.assertEqual(len(self.engine.store.messages(thread_id=self.thread)), 1)
        with self.assertRaises(ValueError):
            self.brain.require_thread(self.thread)

    def test_memory_is_explicit_editable_bounded_and_respects_opt_out(self):
        rows = self.brain.memory({'label': 'İş tərzi', 'text': 'Misallar Python dilində olsun.', 'pinned': True})
        self.assertIn('Python', self.engine.instructions(self.settings))
        self.brain.preferences({'useMemory': False})
        self.assertNotIn('Python', self.engine.instructions(self.settings))
        self.brain.preferences({'useMemory': True, 'detail': 'detailed', 'tone': 'precise'})
        self.assertIn('Ətraflı', self.engine.instructions(self.settings))
        self.brain.memory({'id': rows[0]['id'], 'label': 'İş tərzi', 'text': 'Rust ilə işlə.'})
        self.assertNotIn('Python', self.engine.instructions(self.settings))
        self.assertIn('Rust', self.engine.instructions(self.settings))
        with self.assertRaises(ValueError):
            self.brain.memory({'label': 'Secret', 'text': 'sk-ant-' + 'a'*30})
        self.brain.memory({'action': 'delete', 'id': rows[0]['id']})
        self.assertEqual(self.brain.memory(), [])

    def test_workspace_context_requires_explicit_share(self):
        settings = {**self.settings, 'workspaceContext': {'private_project': 'WORKSPACE_PRIVATE_MARKER'}}
        self.assertNotIn('WORKSPACE_PRIVATE_MARKER', self.engine.instructions(settings))
        self.assertEqual(self.engine.tool('workspace_statistics', {}, settings)['dashboard'], {})
        self.brain.preferences({'useWorkspace': True})
        self.assertIn('WORKSPACE_PRIVATE_MARKER', self.engine.instructions(settings))
        self.assertIn('private_project', self.engine.tool('workspace_statistics', {}, settings)['dashboard'])

    def test_memory_tool_waits_for_approval_and_runs_once(self):
        proposed = self.engine.tool('remember_fact', {'label': 'Ad', 'text': 'Adım Muraddır.'}, self.settings)
        self.assertEqual(proposed['status'], 'awaiting_confirmation')
        self.assertEqual(self.brain.memory(), [])
        self.brain.decide(proposed['approval_id'], True)
        self.wait(lambda: self.brain.memory())
        with self.assertRaises(ValueError):
            self.brain.decide(proposed['approval_id'], True)
        self.assertEqual(len(self.brain.memory()), 1)
        self.wait(lambda: not self.brain.running_actions())
        self.assertTrue(any('tamamlandı' in m['text'] for m in self.engine.store.messages(thread_id=self.thread)))

    def test_denied_or_expired_approval_never_launches_application(self):
        with patch('subprocess.Popen') as launch:
            a = self.engine.tool('open_application', {'name': 'notepad'}, self.settings)
            self.brain.decide(a['approval_id'], False)
            b = self.engine.tool('open_application', {'name': 'notepad'}, self.settings)
            with self.engine.store.connection() as db:
                db.execute('UPDATE companion_approvals SET created=0 WHERE id=?', (b['approval_id'],))
            with self.assertRaises(ValueError):
                self.brain.decide(b['approval_id'], True)
            launch.assert_not_called()

    def test_concurrent_allow_clicks_cannot_execute_twice(self):
        a = self.engine.tool('add_reminder', {'title': 'Bir dəfə', 'due': 0}, self.settings)
        def decide():
            try:
                self.brain.decide(a['approval_id'], True)
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(lambda _: decide(), range(2))), 1)
        self.wait(lambda: not self.brain.running_actions())
        self.assertEqual([t['title'] for t in self.brain.tasks()], ['Bir dəfə'])

    def test_paid_media_is_not_requested_until_approved(self):
        with patch.object(self.engine.media, 'image', return_value={'file': 'image.png'}) as create:
            a = self.engine.tool('generate_image', {'prompt': 'Gözəl mənzərə'}, self.settings)
            create.assert_not_called()
            self.brain.decide(a['approval_id'], True)
            self.wait(lambda: not self.brain.running_actions())
            create.assert_called_once()

    def test_async_video_keeps_pollable_kind_and_reports_completion_once(self):
        self.brain.preferences({'confirmActions': False})
        def create(prompt, job_id):
            self.engine.store.update(job_id, 'waiting', result={'kind': 'video', 'remote_id': 'fixture'})
            return {'job_id': job_id, 'status': 'waiting'}
        with patch.object(self.engine.media, 'video', side_effect=create):
            result = self.engine.tool('generate_video', {'prompt': 'İşıqlı planet'}, self.settings)
        job = next(j for j in self.engine.store.jobs() if j['id'] == result['job_id'])
        self.assertEqual(job['kind'], 'video')
        self.assertEqual(job['status'], 'waiting')
        output = {'kind': 'video', 'file': job['id']+'.mp4'}
        self.engine.store.update(job['id'], 'completed', result=output)
        self.brain.tick(); self.brain.tick()
        messages = self.engine.store.messages(thread_id=self.thread)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['action_result']['file'], output['file'])

    def test_long_running_job_ownership_survives_activity_retention(self):
        job = self.engine.store.job('video', 'Uzun video')
        self.engine.store.update(job, 'waiting')
        self.brain.activity(self.thread, 'generate_video', 'Hazırlanır', 'waiting', job)
        with self.engine.store.connection() as db:
            db.executemany('INSERT INTO companion_activity(thread_id,kind,label,state,job_id,created) VALUES (NULL,\'agent\',\'event\',\'completed\',\'\',1)', [() for _ in range(1010)])
        self.brain.activity(None, 'agent', 'Timeline trim', 'completed')
        with self.engine.store.connection() as db:
            self.assertIsNone(db.execute('SELECT id FROM companion_activity WHERE job_id=?', (job,)).fetchone())
        self.assertEqual(self.brain.snapshot()['active_jobs'][0]['id'], job)
        self.engine.store.update(job, 'completed', result={'file': job+'.mp4'})
        self.brain.tick(); self.brain.tick()
        self.assertEqual(len(self.engine.store.messages(thread_id=self.thread)), 1)

    def test_active_thread_rejects_a_second_simultaneous_chat(self):
        gate = threading.Event()
        def answer(*_):
            gate.wait(3)
            return 'Tamamlandı'
        with patch.object(self.engine, 'answer', side_effect=answer):
            accepted = self.engine.submit('Birinci', source='companion', thread_id=self.thread)
            try:
                with self.assertRaisesRegex(ValueError, 'cari cavab'):
                    self.engine.submit('İkinci', source='companion', thread_id=self.thread)
            finally:
                gate.set()
                self.wait(lambda: any(j['id']==accepted['job_id'] and j['status']=='completed' for j in self.engine.store.jobs()))
        self.assertEqual([m['text'] for m in self.engine.store.messages(thread_id=self.thread) if m['sender']=='user'], ['Birinci'])

    def test_task_due_snooze_acknowledge_and_restart_are_real_persistent_states(self):
        rows = self.brain.tasks({'title': 'Faylı göndər', 'due': time.time()+30})
        task = rows[0]['id']
        with self.engine.store.connection() as db:
            db.execute('UPDATE companion_tasks SET due=? WHERE id=?', (time.time()-1, task))
        self.assertEqual(self.brain.snapshot()['tasks'][0]['state'], 'due')
        self.brain.tasks({'action': 'acknowledge', 'id': task})
        self.assertEqual(self.brain.snapshot()['tasks'][0]['notified'], 1)
        self.brain.tasks({'action': 'snooze', 'id': task})
        self.assertGreater(self.brain.tasks()[0]['due'], time.time()+590)
        self.brain.tasks({'action': 'done', 'id': task})
        self.engine.close()
        self.engine = Engine(self.temp.name)
        self.brain = self.engine.companion
        self.assertEqual(self.brain.tasks()[0]['state'], 'done')
        for value in (True, float('nan'), float('inf'), time.time()-300):
            with self.assertRaises(ValueError):
                self.brain.tasks({'title': 'Düzgün olmayan vaxt', 'due': value})

    def test_connection_workspace_header_private_storage_and_reload(self):
        key = 'fixture-ui-key-do-not-use'
        with patch('orion_http.request', return_value={'data': [{'id':'claude-fixture','display_name':'Fixture'}]}) as request:
            self.engine.connections.update({'provider':'anthropic','key':key,'workspace_id':'wrkspc_fixture','action':'save'})
        self.assertEqual(request.call_args.kwargs['headers']['anthropic-workspace-id'], 'wrkspc_fixture')
        self.assertNotIn(key, json.dumps(self.brain.snapshot()))
        self.assertNotIn(key.encode(), self.engine.store.path.read_bytes())
        self.assertEqual(self.engine.connections.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(Connections(self.engine.store).key('anthropic'), key)
        with patch('orion_http.request', return_value={'content':[{'type':'text','text':'Salam'}]}) as request:
            message = self.engine.store.message('user','Salam',thread_id=self.thread)
            self.engine.answer(message,self.settings)
        self.assertEqual(request.call_args.args[3]['anthropic-workspace-id'], 'wrkspc_fixture')
        with patch('orion_http.request', return_value={'content': []}) as request:
            AnthropicClient(key).create(model='claude-fixture',max_tokens=128,messages=[])
        self.assertEqual(request.call_args.args[3]['anthropic-workspace-id'], 'wrkspc_fixture')

    def test_failed_connection_test_keeps_existing_credentials(self):
        old_key = self.engine.connections.key('anthropic')
        with patch('orion_http.request', side_effect=APIError('Rədd edildi',401)):
            with self.assertRaises(APIError):
                self.engine.connections.update({'provider':'anthropic','key':'invalid-fixture-key','action':'save'})
        self.assertEqual(self.engine.connections.key('anthropic'),old_key)
        self.assertFalse(self.engine.connections.path.exists())

    def test_misplaced_secrets_in_model_or_workspace_never_reach_public_state(self):
        secret = 'sk-ant-api03-' + 'a' * 40
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': secret, 'ANTHROPIC_WORKSPACE_ID': secret}):
            self.assertNotIn(secret, json.dumps(self.brain.snapshot()))
            self.assertNotIn(secret, json.dumps(self.engine.models()))

    def test_agent_hook_requires_revocable_secret_and_has_no_command_execution(self):
        self.brain.port=8765
        self.brain.hook_control(True)
        token=self.brain.hook_token
        data={'agent':'Codex','session':'project','state':'working','label':'Faylları oxuyur'}
        with self.assertRaises(PermissionError):
            self.brain.agent_event(data,'wrong')
        self.brain.agent_event(data,token)
        self.brain.agent_event({**data,'state':'completed'},token)
        snapshot=self.brain.snapshot()
        self.assertEqual(len(snapshot['agents']),1)
        self.assertEqual(snapshot['agents'][0]['state'],'completed')
        self.assertNotIn(token,json.dumps(snapshot))
        self.brain.hook_control(False)
        self.assertFalse(self.brain.hook_path.exists())
        with self.assertRaises(PermissionError):
            self.brain.agent_event(data,token)

    def test_agent_cli_delivers_a_real_authenticated_loopback_event(self):
        server=start(0,self.engine)
        self.brain.hook_control(True)
        try:
            args=['orion_agent_hook.py','--agent','Codex','--session','test-project','--state','completed','--label','CLI işi tamamlandı']
            with patch('sys.argv',args),patch('config.load_env'),patch('config.data_directory',return_value=Path(self.temp.name)),patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(orion_agent_hook.main(),0)
            agent=self.brain.snapshot()['agents'][0]
            self.assertEqual((agent['agent'],agent['state'],agent['label']),('Codex','completed','CLI işi tamamlandı'))
        finally:
            server.shutdown();server.server_close()

    def test_live_http_routes_isolate_bot_messages_and_block_untrusted_writes(self):
        server=start(0,self.engine)
        base=f'http://127.0.0.1:{server.server_address[1]}'
        def get(path):
            with urllib.request.urlopen(base+path) as response:return json.load(response)
        def post(path,data,origin=None,token=None):
            headers={'Content-Type':'application/json'}
            if origin:headers['Origin']=origin
            if token:headers['Authorization']='Bearer '+token
            with urllib.request.urlopen(urllib.request.Request(base+path,json.dumps(data).encode(),headers)) as response:return json.load(response)
        try:
            self.engine.store.message('user','Bota aid',thread_id=self.thread)
            self.assertEqual(get('/api/messages')['messages'],[])
            self.assertEqual(get('/api/companion/messages?thread='+self.thread)['messages'][0]['text'],'Bota aid')
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/companion/memory',{'label':'Test','text':'Text'},origin='https://example.com')
            self.assertEqual(error.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/companion/agent-event',{'agent':'test'})
            self.assertEqual(error.exception.code,403)
            post('/api/companion/memory',{'label':'Real HTTP','text':'Yaddaş işləyir'})
            self.assertEqual(get('/api/companion/state')['memory'][0]['label'],'Real HTTP')
            with patch('orion_http.request',return_value={'content':[{'type':'text','text':'HTTP cavabı'}]}) as request:
                accepted=post('/api/companion/send',{'thread_id':self.thread,'text':'Salam'})
                self.wait(lambda:any(j['id']==accepted['job_id'] and j['status']=='completed' for j in self.engine.store.jobs()))
            self.assertEqual(get('/api/companion/messages?thread='+self.thread)['messages'][-1]['text'],'HTTP cavabı')
            self.assertEqual(get('/api/messages')['messages'],[])
        finally:
            server.shutdown();server.server_close()

    def test_real_conversation_tool_loop_proposes_memory_without_silent_write(self):
        responses=[{'content':[{'type':'tool_use','id':'memory1','name':'remember_fact','input':{'label':'Dil','text':'Azərbaycan dilində danış.'}}]},
                   {'content':[{'type':'text','text':'Yaddaş qeydi üçün təsdiqini gözləyirəm.'}]}]
        with patch('orion_http.request',side_effect=responses):
            accepted=self.engine.submit('Yadda saxla: Azərbaycan dilində danış.',source='companion',thread_id=self.thread)
            self.wait(lambda:any(j['id']==accepted['job_id'] and j['status']=='completed' for j in self.engine.store.jobs()))
        self.assertEqual(self.brain.memory(),[])
        self.assertEqual(len(self.brain.snapshot()['approvals']),1)
        self.assertEqual(self.engine.store.messages(thread_id=self.thread)[-1]['source'],'companion')

    def test_voice_command_and_reply_stay_in_selected_companion_conversation(self):
        self.engine.voice = Mock()
        voice = VoiceService(self.engine)
        with patch('orion_http.request', return_value={'content':[{'type':'text','text':'Səsli cavab'}]}):
            accepted = voice.submit_transcript('Səsli sual', self.thread)
            self.wait(lambda: any(j['id']==accepted['job_id'] and j['status']=='completed' for j in self.engine.store.jobs()))
            self.wait(lambda: self.engine.voice.finish.called)
        self.assertEqual([m['text'] for m in self.engine.store.messages(thread_id=self.thread)], ['Səsli sual','Səsli cavab'])
        self.assertEqual(self.engine.store.history(), [])
        self.engine.voice.speak.assert_called_once_with('Səsli cavab')
        self.engine.voice.finish.assert_called_once()


if __name__=='__main__':unittest.main()
