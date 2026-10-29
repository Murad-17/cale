"""Public update metadata and offline font delivery for ORION 0.6.0."""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from dashboard_bridge import start
from engine import Engine
from update_installer import allowed_file


class PracticalUpdateTests(unittest.TestCase):
    def test_current_release_and_every_bundled_font_are_served_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine(folder)
            server = start(0, engine)
            url = f'http://127.0.0.1:{server.server_address[1]}'
            try:
                with urllib.request.urlopen(url+'/api/updates') as response:
                    status = json.load(response)
                self.assertEqual(status['current_version'], '0.6.0')
                self.assertEqual(status['current_name'], 'Premium UI')
                self.assertIn('ORION 0.6.0 — Premium UI', status['notes'])
                with urllib.request.urlopen(url+'/orion-fonts.css') as response:
                    self.assertEqual(response.headers.get_content_type(), 'text/css')
                    self.assertEqual(response.read().count(b'@font-face'), 10)
                for weight in ('Light','Regular','Medium','SemiBold','Bold'):
                    for suffix in ('','Italic'):
                        name=f'EuclidCircularA-{weight}{suffix}.woff'
                        self.assertTrue(allowed_file('panel_assets/fonts/'+name))
                        with urllib.request.urlopen(url+'/panel-assets/fonts/'+name) as response:
                            self.assertEqual(response.headers.get_content_type(), 'font/woff')
                            self.assertEqual(response.read(4), b'wOFF')
                for path in ('/panel-assets/fonts/unknown.woff','/panel-assets/fonts/../../.env'):
                    with self.assertRaises(urllib.error.HTTPError):
                        urllib.request.urlopen(url+path)
                for path, mime in (('/password-meter.css','text/css'),('/password-meter.js','application/javascript')):
                    with urllib.request.urlopen(url+path) as response:
                        self.assertEqual(response.headers.get_content_type(), mime)
                        self.assertIn(b'vs-password-meter', response.read())
                for subset in ('Latin','LatinExt'):
                    for weight in ('Regular','Medium'):
                        name=f'JetBrainsMono-{subset}-{weight}.woff'
                        self.assertTrue(allowed_file('panel_assets/fonts/'+name))
                        with urllib.request.urlopen(url+'/panel-assets/fonts/'+name) as response:
                            self.assertEqual(response.read(4), b'wOFF')
            finally:
                server.shutdown()
                server.server_close()
                engine.close()

    def test_update_package_accepts_font_support_without_arbitrary_files(self):
        self.assertTrue(allowed_file('orion_fonts.css'))
        self.assertTrue(allowed_file('panel_window.py'))
        for name in ('password_meter.css','password_meter.js','panel_assets/fonts/JetBrainsMono-OFL.txt'):
            self.assertTrue(allowed_file(name))
        for path in ('panel_assets/fonts/key.txt','panel_assets/fonts/EuclidCircularA-Regular.exe','panel_assets/fonts/../.env'):
            self.assertFalse(allowed_file(path))


if __name__ == '__main__':
    unittest.main()
