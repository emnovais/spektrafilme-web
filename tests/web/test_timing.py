"""ETA uses measured stage durations; percentages never imply time."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from spektrafilm_web.timing import RenderTimer, TimingHistory, render_signature
from test_server import HTTPTestCase


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = lambda: self.now

    def test_no_history_has_no_numeric_estimate(self):
        timer = RenderTimer(clock=self.clock)
        timer.enter('film')
        self.now = 20
        self.assertEqual(timer.remaining(), (None, 'learning'))

    def test_remaining_tracks_current_stage_and_unfinished_stages(self):
        timer = RenderTimer({'prepare':2, 'film':10, 'save':3}, clock=self.clock)
        timer.enter('prepare')
        self.now = 1
        self.assertEqual(timer.remaining(), (14, 'estimated'))
        self.now = 2
        timer.enter('film')
        self.now = 5
        self.assertEqual(timer.remaining(), (10, 'estimated'))
        timer.enter('film')  # Progress updates within a stage must not reset its clock.
        self.now = 12
        timer.enter('save')
        self.now = 13
        self.assertEqual(timer.remaining(), (2, 'estimated'))
        self.now = 15
        timer.finish('done')
        self.assertEqual(timer.remaining(), (0, 'done'))
        self.assertEqual(timer.durations, {'prepare':2, 'film':10, 'save':3})

    def test_overrun_and_unknown_stage_recalculate_instead_of_claiming_zero(self):
        timer = RenderTimer({'film':5}, clock=self.clock)
        timer.enter('film')
        self.now = 10
        self.assertEqual(timer.remaining(), (None, 'recalculating'))
        timer.enter('unexpected')
        self.assertEqual(timer.remaining(), (None, 'recalculating'))

    def test_failed_job_has_no_eta(self):
        timer = RenderTimer({'film':5}, clock=self.clock)
        timer.enter('film')
        self.now = 2
        timer.finish('error')
        self.assertEqual(timer.remaining(), (None, 'error'))

    def test_history_is_bounded_and_uses_median_of_completed_samples(self):
        history = TimingHistory(max_configs=2, max_samples=3)
        for duration in [100, 9, 10, 11]:
            history.remember('same', {'film':duration})
        self.assertEqual(history.estimate('same'), {'film':10})
        history.remember('other', {'film':20})
        history.remember('third', {'film':30})
        self.assertIsNone(history.estimate('same'))
        self.assertIsNone(history.estimate('unseen'))

    def test_config_matches_dimensions_mode_and_expensive_settings(self):
        params = NS(
            film=NS(info=NS(stock='film')), print=NS(info=NS(stock='paper')),
            io=NS(input_color_space='sRGB', input_cctf_decoding=True),
            film_render=NS(grain=NS(active=True, agx_particle_area_um2=.2, blur=.65),
                           halation=NS(halation_amount=1, scatter_amount=1)))
        original = render_signature(params, (4000,6000,3), False)
        self.assertNotEqual(original, render_signature(params, (2000,3000,3), False))
        self.assertNotEqual(original, render_signature(params, (4000,6000,3), True))
        params.film_render.grain.active = False
        self.assertNotEqual(original, render_signature(params, (4000,6000,3), False))


class JobTimingTests(HTTPTestCase):
    def test_snapshots_update_elapsed_eta_and_learn_only_successful_jobs(self):
        now = [0]
        clock = lambda: now[0]
        with patch('spektrafilm_web.server.perf_counter', clock):
            self.server.update_job('timed', kind='render', status='running', progress=0)
            self.server.track_render('timed', 'config')
            self.server.render_timers['timed'] = RenderTimer({'film':10, 'save':2}, clock=clock)
            self.server.report('timed', 10, 'film')
            now[0] = 4
            first = self.server.job_snapshot('timed')
            self.assertEqual(first['elapsed_seconds'], 4)
            self.assertEqual(first['remaining_seconds'], 8)
            now[0] = 10
            self.server.report('timed', 90, 'save')
            now[0] = 12
            self.server.update_job('timed', status='done', progress=100)
            final = self.server.job_snapshot('timed')
            self.assertEqual((final['elapsed_seconds'], final['remaining_seconds'], final['eta_state']), (12,0,'done'))
            now[0] = 50
            self.assertEqual(self.server.job_snapshot('timed')['elapsed_seconds'], 12)
            self.assertEqual(self.server.timing_history.estimate('config'), {'film':10,'save':2})
            self.server.update_job('failed-timing', kind='render', status='running')
            self.server.track_render('failed-timing', 'new-config')
            self.server.update_job('failed-timing', status='error')
            self.assertIsNone(self.server.timing_history.estimate('new-config'))
            self.assertIsNone(self.server.job_snapshot('failed-timing')['remaining_seconds'])
