"""HTTP contract tests; deliberately independent of scientific dependencies."""
import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from spektrafilm_web.server import LocalServer, number


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = LocalServer(('127.0.0.1', 0), cls.temp.name)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def test_static_and_profiles(self):
        for path in ('/', '/app.js', '/style.css'):
            with urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 100)
        with urlopen(self.url + '/api/profiles') as response:
            rows = json.load(response)
        ids = {p['id']: p for p in rows}
        self.assertEqual(ids['kodak_portra_400']['support'], 'film')
        self.assertEqual(ids['kodak_portra_endura']['support'], 'paper')

    def test_render_requires_uploaded_image(self):
        request = Request(self.url + '/api/render', data=b'{"image":"missing"}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        self.assertIn('Open an image', json.load(raised.exception)['error'])

    def test_cross_origin_is_rejected(self):
        request = Request(self.url + '/api/render', data=b'{}', headers={'Origin': 'https://example.com'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 403)

    def test_private_files_are_not_served(self):
        for path in ('/server.py', '/media/../server.py', '/api/jobs/unknown'):
            with self.assertRaises(HTTPError):
                urlopen(self.url + path)

    def test_parameter_ranges(self):
        for value in (float('nan'), float('inf'), -4, 4):
            with self.assertRaises(ValueError):
                number({'exposure': value}, 'exposure', 0, -3, 3)
        self.assertEqual(number({}, 'exposure', 0, -3, 3), 0)


if __name__ == '__main__':
    unittest.main()
