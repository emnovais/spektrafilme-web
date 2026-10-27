"""Loopback-only web application. Run with python -m spektrafilm_web.server."""
from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import tempfile
import threading
import uuid
from time import perf_counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from spektrafilm_web.timing import RenderTimer, TimingHistory, render_signature

STATIC = Path(__file__).with_name('static')
PROFILES = Path(__file__).parents[1] / 'spektrafilm' / 'data' / 'profiles'
LIMIT = 256 * 1024 * 1024
API_VERSION = 1
LOGGER = logging.getLogger('spektrafilm.web')
LOGGER.addHandler(logging.NullHandler())
RENDER_STAGES = {
    'preprocess': 'Preparando imagem',
    'filming.expose': 'Expondo o filme',
    'filming.develop': 'Revelando o filme e aplicando textura',
    'printing.expose': 'Expondo o papel',
    'printing.develop': 'Revelando o papel',
    'scanning.scan_print': 'Digitalizando a impressão',
    'scanning.scan_film': 'Digitalizando o filme',
}


def configure_logging(log_file, *, debug=False):
    path = Path(log_file).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    for handler in LOGGER.handlers[:]:
        LOGGER.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    console_handler = logging.StreamHandler()
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if debug else logging.INFO)
    LOGGER.propagate = False
    return path


def profiles():
    return [dict(json.loads(p.read_text())['info'], id=p.stem)
            for p in sorted(PROFILES.glob('*.json'))]


def number(data, key, default, low, high):
    value = float(data.get(key, default))
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Invalid {key}: expected {low}–{high}')
    return value


class LocalServer(ThreadingHTTPServer):
    def __init__(self, address, directory):
        super().__init__(address, Handler)
        self.directory = Path(directory)
        self.images = {}
        self.jobs = {}
        self.job_started = {}
        self.render_timers = {}
        self.timing_keys = {}
        self.timing_history = TimingHistory()
        self.session = uuid.uuid4().hex
        self.lock = threading.Lock()

    def update_job(self, job_id, **changes):
        # Replace snapshots so polling never sees a partially updated record.
        with self.lock:
            previous = self.jobs.get(job_id, {})
            current = {**previous, **changes}
            self.jobs[job_id] = current
            started = self.job_started.setdefault(job_id, perf_counter())
            timer = self.render_timers.get(job_id)
            if current.get('status') in {'done', 'error'}:
                current['elapsed_seconds'] = round(perf_counter() - started, 1)
                if timer and timer.status == 'running':
                    timer.finish(current['status'])
                    if current['status'] == 'done':
                        self.timing_history.remember(self.timing_keys[job_id], timer.durations)
            elif timer and current.get('stage'):
                timer.enter(current['stage'])
        if (current.get('stage'), current.get('status')) != (previous.get('stage'), previous.get('status')):
            LOGGER.info('job=%s kind=%s status=%s progress=%s stage=%s elapsed=%.3fs',
                        job_id, current.get('kind'), current.get('status'), current.get('progress'),
                        current.get('stage'), perf_counter() - started)

    def report(self, job_id, progress, stage):
        self.update_job(job_id, progress=progress, stage=stage)

    def track_render(self, job_id, key):
        with self.lock:
            self.timing_keys[job_id] = key
            self.render_timers[job_id] = RenderTimer(self.timing_history.estimate(key))

    def job_snapshot(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            snapshot = dict(job)
            if job.get('status') == 'running':
                snapshot['elapsed_seconds'] = round(perf_counter() - self.job_started.get(job_id, perf_counter()), 1)
            if job.get('kind') == 'render':
                timer = self.render_timers.get(job_id)
                if timer:
                    remaining, state = timer.remaining()
                else:
                    remaining = 0 if job.get('status') == 'done' else None
                    state = {'done': 'done', 'error': 'error'}.get(job.get('status'), 'learning')
                snapshot.update(remaining_seconds=remaining, eta_state=state)
            return snapshot

    def handle_error(self, request, client_address):
        LOGGER.exception('Unhandled HTTP request failure client=%s', client_address[0])


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        path = urlparse(self.path).path
        level = logging.DEBUG if path.startswith('/api/jobs/') and str(code) in {'200', '404'} else logging.INFO
        LOGGER.log(level, 'HTTP %s %s -> %s', self.command, path, code)

    def reply(self, data, status=200, mime='application/json'):
        body = json.dumps(data).encode() if mime == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self.reply({'api_version': API_VERSION, 'session': self.server.session})
        if path == '/api/profiles':
            return self.reply(profiles())
        if path.startswith('/api/jobs/'):
            job = self.server.job_snapshot(path.rsplit('/', 1)[-1])
            return self.reply(job or {'error': 'Job not found'}, 200 if job else 404)
        if path.startswith('/media/'):
            name = path.removeprefix('/media/')
            if Path(name).name != name:
                return self.reply({'error': 'Invalid path'}, 400)
            target = self.server.directory / name
            if target.is_file():
                mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.tif': 'image/tiff'}.get(target.suffix)
                if mime:
                    return self.reply(target.read_bytes(), mime=mime)
        name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}.get(path)
        if name:
            mime = {'html': 'text/html; charset=utf-8', 'js': 'text/javascript', 'css': 'text/css'}[name.rsplit('.', 1)[-1]]
            return self.reply((STATIC / name).read_bytes(), mime=mime)
        self.reply({'error': 'Not found'}, 404)

    def do_POST(self):
        # Only same-origin browser requests can mutate the local application.
        if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.reply({'error': 'Origin rejected'}, 403)
        job_id = None
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= LIMIT:
                return self.reply({'error': 'Maximum upload size is 256 MB'}, 413)
            path = urlparse(self.path).path
            if path == '/api/client-error' and length > 16 * 1024:
                return self.reply({'error': 'Diagnostic message too large'}, 413)
            if path == '/api/upload' and self.headers.get('X-Upload-ID'):
                upload_id = uuid.UUID(self.headers['X-Upload-ID']).hex
                with self.server.lock:
                    if upload_id in self.server.jobs:
                        raise ValueError('Upload ID already exists')
                    job_id = upload_id
                    self.server.jobs[job_id] = {
                        'kind': 'upload', 'status': 'running', 'progress': 0,
                        'stage': 'Recebendo arquivo',
                    }
                    self.server.job_started[job_id] = perf_counter()
                LOGGER.info('job=%s kind=upload started bytes=%s', job_id, length)
            report = (lambda value, stage: self.server.report(job_id, value, stage)) if job_id else (lambda *_: None)
            body = bytearray()
            while len(body) < length:
                chunk = self.rfile.read(min(256 * 1024, length - len(body)))
                if not chunk:
                    raise ValueError('Upload interrupted')
                body.extend(chunk)
                report(round(40 * len(body) / length), 'Recebendo arquivo')
            if path == '/api/client-error':
                data = json.loads(body)
                LOGGER.error('browser context=%s message=%s stack=%s',
                             str(data.get('context', ''))[:200], str(data.get('message', ''))[:2000],
                             str(data.get('stack', ''))[:8000])
                return self.reply({'ok': True})
            if path == '/api/upload':
                image = self.upload(body, report)
                if job_id:
                    self.server.update_job(job_id, status='done', progress=100, stage='Imagem pronta')
                return self.reply(image)
            if path == '/api/render':
                data = json.loads(body)
                if data.get('image') not in self.server.images:
                    raise ValueError('Open an image first')
                with self.server.lock:
                    if any(j['status'] == 'running' and j.get('kind') == 'render' for j in self.server.jobs.values()):
                        return self.reply({'error': 'A simulation is already running'}, 409)
                    job_id = uuid.uuid4().hex
                    self.server.jobs[job_id] = {
                        'kind': 'render', 'status': 'running', 'progress': 0,
                        'stage': 'Carregando o motor de simulação',
                    }
                    self.server.job_started[job_id] = perf_counter()
                LOGGER.info('job=%s kind=render started mode=%s', job_id, data.get('mode'))
                threading.Thread(target=self.render, args=(job_id, data), daemon=True).start()
                return self.reply({'job': job_id}, 202)
            self.reply({'error': 'Not found'}, 404)
        except ImportError as exc:
            LOGGER.exception('Request failed path=%s job=%s', urlparse(self.path).path, job_id)
            if job_id:
                self.server.update_job(job_id, status='error', error=str(exc), stage='Falha no processamento')
            self.reply({'error': f'Missing dependency: {exc}. Install this project with Python 3.13: pip install -e .'}, 503)
        except Exception as exc:
            LOGGER.exception('Request failed path=%s job=%s', urlparse(self.path).path, job_id)
            if job_id:
                self.server.update_job(job_id, status='error', error=str(exc), stage='Falha no processamento')
            self.reply({'error': str(exc)}, 400)

    def upload(self, body, report=lambda *_: None):
        report(40, 'Carregando os leitores de imagem')
        import numpy as np
        from PIL import Image, ImageOps
        from spektrafilm.utils.io import load_image_oiio
        name = Path(self.headers.get('X-Filename', 'image.png')).name
        suffix = Path(name).suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.nef', '.cr2', '.cr3', '.arw', '.dng', '.raf', '.rw2', '.orf'}:
            raise ValueError('Unsupported image format')
        key = uuid.uuid4().hex
        report(45, 'Lendo e decodificando a imagem')
        source = self.server.directory / (key + suffix)
        source.write_bytes(body)
        space, encoded = 'sRGB', True
        try:
            if suffix in {'.png', '.jpg', '.jpeg'}:
                image = np.asarray(ImageOps.exif_transpose(Image.open(source)).convert('RGB'), dtype=np.float64) / 255
            elif suffix in {'.tif', '.tiff', '.exr'}:
                image = load_image_oiio(str(source))[..., :3]
                space, encoded = 'ProPhoto RGB', False
            else:
                import rawpy
                with rawpy.imread(str(source)) as raw:
                    image = raw.postprocess(output_color=rawpy.ColorSpace.sRGB, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True, output_bps=16).astype(np.float64) / 65535
                encoded = False
            if image.ndim != 3 or image.shape[2] != 3:
                raise ValueError('An RGB image is required')
            report(70, 'Convertendo as cores para exibição')
            from colour import cctf_encoding
            display = image if encoded else cctf_encoding(image, function='sRGB') if space == 'sRGB' else self.display(image, space)
            preview = Image.fromarray((np.clip(display, 0, 1) * 255).astype('uint8'))
            report(85, 'Criando a miniatura')
            preview.thumbnail((1600, 1600))
            preview.save(self.server.directory / f'{key}-original.png')
            self.server.images[key] = (image, space, encoded)
            return {'id': key, 'name': name, 'width': image.shape[1], 'height': image.shape[0], 'url': f'/media/{key}-original.png', 'space': space, 'encoded': encoded}
        finally:
            source.unlink(missing_ok=True)

    @staticmethod
    def display(image, space):
        import colour
        return colour.RGB_to_RGB(image, space, 'sRGB', apply_cctf_encoding=True)

    def render(self, job_id, data):
        report = lambda value, stage: self.server.report(job_id, value, stage)
        try:
            import numpy as np
            from spektrafilm import init_params, simulate, simulate_preview
            from spektrafilm.utils.io import save_image_oiio
            available = {p['id']: p for p in profiles()}
            film, paper = data.get('film'), data.get('paper')
            if film not in available or available[film]['support'] != 'film':
                raise ValueError('Select a valid film')
            if paper not in available or available[paper]['support'] != 'paper':
                raise ValueError('Select a valid print paper')
            report(3, 'Carregando os perfis de filme e papel')
            params = init_params(film_profile=film, print_profile=paper)
            image, space, encoded = self.server.images[data['image']]
            params.io.input_color_space = data.get('space', space)
            if params.io.input_color_space not in {'sRGB', 'ProPhoto RGB', 'Adobe RGB (1998)', 'Display P3', 'ACES2065-1'}:
                raise ValueError('Invalid input color space')
            params.io.input_cctf_decoding = bool(data.get('encoded', encoded))
            params.io.output_color_space = 'sRGB'
            params.io.output_cctf_encoding = True
            params.camera.exposure_compensation_ev = number(data, 'exposure', 0, -3, 3)
            params.enlarger.y_filter_shift = number(data, 'yellow', 0, -50, 50)
            params.enlarger.m_filter_shift = number(data, 'magenta', 0, -50, 50)
            params.film_render.grain.active = bool(data.get('grain', True))
            params.film_render.grain.agx_particle_area_um2 = number(data, 'grain_size', .2, .01, 2)
            params.film_render.grain.blur = number(data, 'grain_blur', .65, 0, 2)
            params.film_render.halation.halation_amount = number(data, 'halation', 1, 0, 3)
            params.film_render.halation.scatter_amount = number(data, 'scatter', 1, 0, 3)
            preview = data.get('mode') != 'full'
            params.settings.preview_mode = preview
            params.settings.preview_max_size = 1000
            self.server.track_render(job_id, render_signature(params, image.shape, preview))
            report(8, 'Preparando a simulação e os modelos de cor')

            def on_progress(label, completed, total):
                report(round(10 + 75 * completed / total), RENDER_STAGES.get(label, label))

            result = (simulate_preview if preview else simulate)(image, params, on_progress=on_progress)
            report(86, 'Preparando o resultado para exportação')
            result = np.nan_to_num(result)
            report(88, 'Gravando PNG')
            save_image_oiio(str(self.server.directory / f'{job_id}.png'), result, color_space='sRGB')
            urls = {'png': f'/media/{job_id}.png'}
            if not preview:
                for ext in ('jpg', 'tif'):
                    report(92 if ext == 'jpg' else 96, 'Gravando JPEG' if ext == 'jpg' else 'Gravando TIFF de 16 bits')
                    save_image_oiio(str(self.server.directory / f'{job_id}.{ext}'), result, color_space='sRGB')
                    urls[ext] = f'/media/{job_id}.{ext}'
            self.server.update_job(job_id, status='done', progress=100, stage='Processamento concluído', url=urls['png'], exports=urls, preview=preview)
        except Exception as exc:
            LOGGER.exception('Render failed job=%s', job_id)
            self.server.update_job(job_id, status='error', stage='Falha na simulação', error=str(exc))


def main():
    parser = argparse.ArgumentParser(description='Spektrafilm local web interface')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--log-file', default='logs/spektrafilm-web.log')
    parser.add_argument('--debug', action='store_true', help='Include individual progress polling requests in logs')
    args = parser.parse_args()
    log_file = configure_logging(args.log_file, debug=args.debug)
    with tempfile.TemporaryDirectory(prefix='spektrafilm-web-') as directory:
        server = LocalServer(('127.0.0.1', args.port), directory)
        print(f'Spektrafilm Web: http://127.0.0.1:{args.port}', flush=True)
        print(f'Log: {log_file}', flush=True)
        LOGGER.info('Server started port=%s api_version=%s session=%s', args.port, API_VERSION, server.session)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            LOGGER.info('Server stopping session=%s', server.session)
            server.server_close()


if __name__ == '__main__':
    main()
