"""Diagnostics persist useful failures without filling logs with polling."""
import json
import logging
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

from spektrafilm_web.server import API_VERSION, LOGGER, configure_logging
from test_server import HTTPTestCase


class LoggingTests(HTTPTestCase):
    def test_health_reports_protocol_and_instance(self):
        with urlopen(self.url + '/api/health') as response:
            data = json.load(response)
        self.assertEqual(data['api_version'], API_VERSION)
        self.assertEqual(data['session'], self.server.session)

    def test_logs_record_stage_transitions_and_browser_errors(self):
        old_handlers, old_level, old_propagate = LOGGER.handlers[:], LOGGER.level, LOGGER.propagate
        with tempfile.TemporaryDirectory() as directory:
            try:
                path = configure_logging(Path(directory) / 'web.log')
                self.server.update_job('log-test', kind='upload', status='running', progress=10, stage='Receiving')
                self.server.report('log-test', 20, 'Receiving')
                with urlopen(self.url + '/api/jobs/log-test') as response:
                    self.assertEqual(response.status, 200)
                payload = json.dumps({'context':'render', 'message':'Broken image', 'stack':'Error at test.js:10'}).encode()
                with urlopen(Request(self.url + '/api/client-error', data=payload)) as response:
                    self.assertTrue(json.load(response)['ok'])
                try:
                    raise ValueError('Decoding failed')
                except ValueError:
                    LOGGER.exception('Diagnostic test failure')
                for handler in LOGGER.handlers:
                    handler.flush()
                text = path.read_text()
                self.assertEqual(text.count('stage=Receiving'), 1)
                self.assertIn('elapsed=', text)
                self.assertIn('browser context=render message=Broken image', text)
                self.assertIn('ValueError: Decoding failed', text)
                self.assertNotIn('HTTP GET /api/jobs/', text)
            finally:
                for handler in LOGGER.handlers[:]:
                    LOGGER.removeHandler(handler)
                    handler.close()
                LOGGER.handlers = old_handlers
                LOGGER.setLevel(old_level)
                LOGGER.propagate = old_propagate
