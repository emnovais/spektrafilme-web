"""Session-local estimates based on completed, comparable render stages."""
from __future__ import annotations

from collections import OrderedDict, deque
from statistics import median
from time import perf_counter


class TimingHistory:
    """Bounded history; failed renders never contribute samples."""

    def __init__(self, max_configs=32, max_samples=5):
        self.max_configs = max_configs
        self.max_samples = max_samples
        self.samples = OrderedDict()

    def remember(self, key, durations):
        if not durations:
            return
        self.samples.setdefault(key, deque(maxlen=self.max_samples)).append(dict(durations))
        self.samples.move_to_end(key)
        while len(self.samples) > self.max_configs:
            self.samples.popitem(last=False)

    def estimate(self, key):
        samples = self.samples.get(key)
        if not samples:
            return None
        self.samples.move_to_end(key)
        stages = set.intersection(*(set(sample) for sample in samples))
        return {stage: median(sample[stage] for sample in samples) for stage in stages}


class RenderTimer:
    """Measure boundaries; predict remaining stages without using percentage."""

    def __init__(self, expected=None, *, clock=perf_counter):
        self.clock = clock
        self.expected = expected
        self.stage = None
        self.stage_started = clock()
        self.durations = {}
        self.status = 'running'

    def enter(self, stage):
        if stage == self.stage or self.status != 'running':
            return
        now = self.clock()
        self._close_stage(now)
        self.stage = stage
        self.stage_started = now

    def _close_stage(self, now):
        if self.stage is not None:
            self.durations[self.stage] = self.durations.get(self.stage, 0) + max(0, now - self.stage_started)

    def finish(self, status):
        if self.status != 'running':
            return
        self._close_stage(self.clock())
        self.status = status

    def remaining(self):
        if self.status == 'done':
            return 0, 'done'
        if self.status == 'error':
            return None, 'error'
        if not self.expected:
            return None, 'learning'
        if self.stage not in self.expected:
            return None, 'recalculating'
        stage_elapsed = max(0, self.clock() - self.stage_started)
        expected_stage = self.expected[self.stage]
        # Never leave a running job counting down at zero after an overrun.
        if stage_elapsed > max(expected_stage * 1.5, expected_stage + 2):
            return None, 'recalculating'
        future = sum(duration for stage, duration in self.expected.items()
                     if stage != self.stage and stage not in self.durations)
        remaining = max(0, expected_stage - stage_elapsed) + future
        if remaining <= 0:
            return None, 'recalculating'
        return max(0.1, round(remaining, 1)), 'estimated'


def render_signature(params, image_shape, preview):
    """Match dimensions, profiles and settings that affect spatial work.

    Exposure/filter shifts are intentionally excluded so color adjustments
    can reuse timings. No extrapolation from thumbnails to large originals.
    """
    grain = params.film_render.grain
    halation = params.film_render.halation
    return (
        bool(preview), tuple(image_shape[:2]),
        params.film.info.stock, params.print.info.stock,
        params.io.input_color_space, params.io.input_cctf_decoding,
        bool(grain.active) if not preview else False,
        grain.agx_particle_area_um2 if not preview and grain.active else None,
        grain.blur if not preview and grain.active else None,
        halation.halation_amount, halation.scatter_amount,
    )
