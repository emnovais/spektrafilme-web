"""Loopback-only web application. Run with python -m spektrafilm_web.server."""
from __future__ import annotations

import argparse
import json
import math
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

STATIC = Path(__file__).with_name('static')
PROFILES = Path(__file__).parents[1] / 'spektrafilm' / 'data' / 'profiles'
LIMIT = 256 * 1024 * 1024


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
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
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
        if path == '/api/profiles':
            return self.reply(profiles())
        if path.startswith('/api/jobs/'):
            job = self.server.jobs.get(path.rsplit('/', 1)[-1])
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
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= LIMIT:
                return self.reply({'error': 'Maximum upload size is 256 MB'}, 413)
            body = self.rfile.read(length)
            path = urlparse(self.path).path
            if path == '/api/upload':
                return self.upload(body)
            if path == '/api/render':
                data = json.loads(body)
                if data.get('image') not in self.server.images:
                    raise ValueError('Open an image first')
                with self.server.lock:
                    if any(j['status'] == 'running' for j in self.server.jobs.values()):
                        return self.reply({'error': 'A simulation is already running'}, 409)
                    job_id = uuid.uuid4().hex
                    self.server.jobs[job_id] = {'status': 'running'}
                threading.Thread(target=self.render, args=(job_id, data), daemon=True).start()
                return self.reply({'job': job_id}, 202)
            self.reply({'error': 'Not found'}, 404)
        except ImportError as exc:
            self.reply({'error': f'Missing dependency: {exc}. Install this project with Python 3.13: pip install -e .'}, 503)
        except Exception as exc:
            self.reply({'error': str(exc)}, 400)

    def upload(self, body):
        import numpy as np
        from PIL import Image, ImageOps
        from spektrafilm.utils.io import load_image_oiio
        name = Path(self.headers.get('X-Filename', 'image.png')).name
        suffix = Path(name).suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.nef', '.cr2', '.cr3', '.arw', '.dng', '.raf', '.rw2', '.orf'}:
            raise ValueError('Unsupported image format')
        key = uuid.uuid4().hex
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
            from colour import cctf_encoding
            display = image if encoded else cctf_encoding(image, function='sRGB') if space == 'sRGB' else self.display(image, space)
            preview = Image.fromarray((np.clip(display, 0, 1) * 255).astype('uint8'))
            preview.thumbnail((1600, 1600))
            preview.save(self.server.directory / f'{key}-original.png')
            self.server.images[key] = (image, space, encoded)
            return self.reply({'id': key, 'name': name, 'width': image.shape[1], 'height': image.shape[0], 'url': f'/media/{key}-original.png', 'space': space, 'encoded': encoded})
        finally:
            source.unlink(missing_ok=True)

    @staticmethod
    def display(image, space):
        import colour
        return colour.RGB_to_RGB(image, space, 'sRGB', apply_cctf_encoding=True)

    def render(self, job_id, data):
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
            result = (simulate_preview if preview else simulate)(image, params)
            result = np.nan_to_num(result)
            save_image_oiio(str(self.server.directory / f'{job_id}.png'), result, color_space='sRGB')
            urls = {'png': f'/media/{job_id}.png'}
            if not preview:
                for ext in ('jpg', 'tif'):
                    save_image_oiio(str(self.server.directory / f'{job_id}.{ext}'), result, color_space='sRGB')
                    urls[ext] = f'/media/{job_id}.{ext}'
            self.server.jobs[job_id] = {'status': 'done', 'url': urls['png'], 'exports': urls, 'preview': preview}
        except Exception as exc:
            self.server.jobs[job_id] = {'status': 'error', 'error': str(exc)}


def main():
    parser = argparse.ArgumentParser(description='Spektrafilm local web interface')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='spektrafilm-web-') as directory:
        server = LocalServer(('127.0.0.1', args.port), directory)
        print(f'Spektrafilm Web: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
