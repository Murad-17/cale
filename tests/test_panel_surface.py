"""Window input/measurement contracts; actual Win32 mask cases are separate."""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from top_panel import round_windows_window, set_window_bounds, PanelAPI, run


class SurfaceTests(unittest.TestCase):
    def test_atomic_bounds_runs_once_on_gui_thread_using_native_geometry_scale(self):
        class Func:
            def __class_getitem__(cls, item): return lambda callback: callback
        native = SimpleNamespace(InvokeRequired=True, IsDisposed=False, IsHandleCreated=True,
                                 _scale=1.5, DeviceDpi=96, SetBounds=Mock())
        native.Invoke = Mock(side_effect=lambda callback: callback())
        window = SimpleNamespace(native=native, resize=Mock(), move=Mock(), _orion_surface_scale=1.25)
        with patch('top_panel.os.name', 'nt'), patch.dict(sys.modules, {'System': SimpleNamespace(Boolean=bool, Func=Func)}):
            set_window_bounds(window, 680, 212, 620, 14)
        native.SetBounds.assert_called_once_with(930, 21, 1020, 318)
        native.Invoke.assert_called_once()
        window.resize.assert_not_called()
        window.move.assert_not_called()

    def test_slow_frames_skip_missed_deadlines_and_finish_at_exact_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            api = PanelAPI('http://127.0.0.1:8765', Path(folder)/'state.json', (0,0,1920,1080))
            window = SimpleNamespace(x=620, y=14, width=680, height=212)
            api._attach(window)
            clock = [0.0]
            def bounds(window, w, h, x, y):
                window.width, window.height, window.x, window.y = w, h, x, y
                clock[0] += .045  # Worse than 30fps: do not accumulate eleven sleeps.
            api._closed.wait = lambda seconds: clock.__setitem__(0, clock[0]+seconds)
            with patch('top_panel.time.perf_counter', side_effect=lambda: clock[0]), patch('top_panel.set_window_bounds', side_effect=bounds) as move, patch('top_panel.round_windows_window') as clip:
                self.assertTrue(api.layout('peek')['ok'])
            self.assertLessEqual(clock[0], .31)
            self.assertLessEqual(move.call_count, 7)
            self.assertEqual((window.width,window.height,window.x,window.y), (284,48,818,0))
            clip.assert_called_once_with(window, 'peek')
            self.assertFalse(api._animating)

    def test_animation_does_not_enqueue_observer_measurement_or_worker_clip(self):
        with tempfile.TemporaryDirectory() as folder:
            api = PanelAPI('http://127.0.0.1:8765', Path(folder)/'state.json', (0,0,1920,1080))
            api._attach(SimpleNamespace(_orion_surface_verified=True))
            api._animating = True
            with patch('top_panel.os.name', 'nt'), patch('top_panel.round_windows_window') as clip:
                self.assertTrue(api.surface(680,212,1)['pending'])
                api._resized()
            clip.assert_not_called()

    def test_css_viewport_measurement_overrides_wrong_form_device_dpi(self):
        class Func:
            def __class_getitem__(cls, item):return lambda callback:callback
        native=SimpleNamespace(InvokeRequired=False,ClientSize=SimpleNamespace(Width=1020,Height=318),DeviceDpi=96)
        window=SimpleNamespace(native=native)
        with tempfile.TemporaryDirectory() as folder:
            api=PanelAPI('http://127.0.0.1:8765',Path(folder)/'state.json',(0,0,1920,1080));api._attach(window)
            with patch('top_panel.os.name','nt'),patch.dict(sys.modules,{'System':SimpleNamespace(Boolean=bool,Func=Func)}),patch('top_panel.round_windows_window') as clip:
                api.surface(680,212,1.5)
            self.assertEqual(window._orion_surface_scale,1.5)
            clip.assert_called_once_with(window,'home')
            for args in ((float('nan'),212,1),(680,0,1),(680,212,99)):
                with self.assertRaises(ValueError):api.surface(*args)

    def test_windows_startup_uses_opaque_focusable_host_and_no_alpha_zero(self):
        class Event:
            def __init__(self):self.callbacks=[]
            def __iadd__(self, callback):self.callbacks.append(callback);return self
        window=SimpleNamespace(events=SimpleNamespace(before_show=Event(),shown=Event(),loaded=Event(),resized=Event(),moved=Event(),closed=Event()))
        webview=SimpleNamespace(screens=[SimpleNamespace(x=0,y=0,width=1920,height=1080)],create_window=Mock(return_value=window),start=Mock())
        windows_os=SimpleNamespace(name='nt',environ=os.environ,replace=os.replace)
        with tempfile.TemporaryDirectory() as folder,patch.dict(sys.modules,{'webview':webview}),patch('top_panel.LocalClient') as client,patch('top_panel.os',windows_os),patch.dict(os.environ,{'WEBVIEW2_DEFAULT_BACKGROUND_COLOR':'00000000'}),patch('top_panel.round_windows_window') as clip:
            client.return_value.request.return_value={'background':'#100d1c'}
            def start(**_):
                # The real backend raises this synchronously after creating
                # BrowserForm, before browser.Show() can expose its backdrop.
                for callback in window.events.before_show.callbacks:callback()
                clip.assert_called_once_with(window,'home')
            webview.start.side_effect=start
            run('http://127.0.0.1:8765',Path(folder)/'state.json')
            self.assertFalse(webview.create_window.call_args.kwargs['transparent'])
            self.assertTrue(webview.create_window.call_args.kwargs['focus'])
            self.assertEqual(os.environ['WEBVIEW2_DEFAULT_BACKGROUND_COLOR'],'FF100D1C')

    def test_invalid_outline_cannot_mask_buttons_or_inject_background_css(self):
        with tempfile.TemporaryDirectory() as folder:
            api=PanelAPI('http://127.0.0.1:8765',Path(folder)/'state.json',(0,0,1920,1080))
            shape={'left':0,'top':0,'right':0,'bottom':0,'radius':26,'background':'#100d1c'}
            for invalid in [[],{**shape,'radius':True},{**shape,'left':float('nan')},{**shape,'top':100,'bottom':120},{**shape,'background':'url(secret)'},{**shape,'background':None}]:
                with self.assertRaises(ValueError):api.surface(680,212,1,invalid)

    def test_docking_does_not_spawn_position_timers_during_animation(self):
        with tempfile.TemporaryDirectory() as folder:
            api=PanelAPI('http://127.0.0.1:8765',Path(folder)/'state.json',(0,0,1920,1080));api._animating=True
            with patch('top_panel.threading.Timer') as timer:api._moved()
            timer.assert_not_called()


if __name__=='__main__':unittest.main()
