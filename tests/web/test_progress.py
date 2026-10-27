"""Progress contracts, including polling while an upload is still running."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest
import uuid
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from spektrafilm_web.server import Handler
from test_server import HTTPTestCase

# Load the pure dispatcher without importing the scientific runtime package.
module_name = '_web_test_topology'
spec = importlib.util.spec_from_file_location(module_name, Path(__file__).parents[2] / 'src/spektrafilm/runtime/topology.py')
topology = importlib.util.module_from_spec(spec)
sys.modules[module_name] = topology
spec.loader.exec_module(topology)


class TopologyProgressTests(unittest.TestCase):
    def chain(self):
        return [topology.Node(('a',), ('b',), lambda x: x + 1, 'first'),
                topology.Node(('b',), ('c',), lambda x: x * 2, 'second')]

    def test_progress_surrounds_real_work_and_preserves_timings(self):
        events, timings = [], []
        nodes = self.chain()
        nodes[0] = topology.Node(('a',), ('b',), lambda x: (events.append('working') or x + 1), 'first')
        result = topology.run_topology(nodes, 'a', 'c', 3,
            on_progress=lambda *args: events.append(args),
            on_fire=lambda node, elapsed: timings.append((node.label, elapsed)))
        self.assertEqual(result, 8)
        self.assertEqual(events, [('first', 0, 2), 'working', ('first', 1, 2), ('second', 1, 2), ('second', 2, 2)])
        self.assertEqual([name for name, _ in timings], ['first', 'second'])
        self.assertTrue(all(elapsed >= 0 for _, elapsed in timings))

    def test_counts_only_executed_stages(self):
        for inject, collect, expected in [('a', 'b', 'first'), ('b', 'c', 'second')]:
            with self.subTest(inject=inject, collect=collect):
                events = []
                topology.run_topology(self.chain(), inject, collect, 3, on_progress=lambda *args: events.append(args))
                self.assertEqual(events, [(expected, 0, 1), (expected, 1, 1)])

    def test_failed_stage_is_not_reported_complete(self):
        events = []
        nodes = [topology.Node(('a',), ('b',), lambda _: 1 / 0, 'broken')]
        with self.assertRaises(ZeroDivisionError):
            topology.run_topology(nodes, 'a', 'b', 0, on_progress=lambda *args: events.append(args))
        self.assertEqual(events, [('broken', 0, 1)])


class UploadProgressTests(HTTPTestCase):
    def request_upload(self, job):
        request = Request(self.url + '/api/upload', data=b'image', headers={'X-Upload-ID': job})
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def state(self, job):
        with urlopen(self.url + '/api/jobs/' + job, timeout=5) as response:
            return json.load(response)

    def test_polling_exposes_running_and_completed_upload(self):
        job = uuid.uuid4().hex
        started, release = threading.Event(), threading.Event()
        result, errors = [], []

        def decode(handler, body, report):
            self.assertEqual(body, b'image')
            report(70, 'Convertendo as cores para exibição')
            started.set()
            if not release.wait(5):
                raise RuntimeError('Test timed out')
            return {'id': 'imported'}

        def post():
            try:
                result.append(self.request_upload(job))
            except Exception as exc:
                errors.append(exc)

        with patch.object(Handler, 'upload', decode):
            thread = threading.Thread(target=post)
            thread.start()
            try:
                self.assertTrue(started.wait(5))
                state = self.state(job)
                self.assertEqual(state['status'], 'running')
                self.assertEqual(state['progress'], 70)
                self.assertIn('cores', state['stage'])
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(errors)
        self.assertEqual(result, [{'id': 'imported'}])
        self.assertEqual(self.state(job)['progress'], 100)
        self.assertEqual(self.state(job)['status'], 'done')

    def test_failed_upload_preserves_progress_and_releases_request(self):
        job = uuid.uuid4().hex

        def decode(handler, body, report):
            report(45, 'Lendo imagem')
            raise ValueError('Invalid image')

        with patch.object(Handler, 'upload', decode), self.assertRaises(HTTPError):
            self.request_upload(job)
        state = self.state(job)
        self.assertEqual((state['status'], state['progress']), ('error', 45))
        self.assertEqual(state['error'], 'Invalid image')

    def test_duplicate_upload_id_does_not_overwrite_existing_job(self):
        job = uuid.uuid4().hex
        self.server.update_job(job, status='running', kind='render', progress=50, stage='Revelando')
        with self.assertRaises(HTTPError):
            self.request_upload(job)
        self.assertEqual(self.state(job)['status'], 'running')
        self.assertEqual(self.state(job)['progress'], 50)
        self.server.update_job(job, status='done')
