# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""frames.py receives video frames posted from a browser page and lays them out on contact sheets.

    uv run frames.py receive OUT_DIR [--port 8765]
    uv run frames.py sheet FRAMES_DIR SHEET_DIR

receive
    Serves http://127.0.0.1:PORT/ until stopped. Each form POST holds one field per frame. The field
    name is `<folder>__<name>` and the value is a JPEG data URL. Each frame is written to
    OUT_DIR/<folder>/<name>.jpg, with both parts cut to lowercase letters, digits and hyphens. A page
    on YouTube can't send data to the computer with fetch(), because the site's security policy
    blocks it, but it can submit a form, so frames leave the page that way. Submitting the form
    moves the tab to the receiver, so a page collects every frame first and submits once.
sheet
    Reads every c<seconds>.jpg in FRAMES_DIR, such as c0186.jpg for 3:06, and writes contact sheets
    of 20 frames each to SHEET_DIR/sheetNN.jpg, with each frame labelled m:ss.

Exit 2 prints `frames:` and the reason.
"""
import argparse
import base64
import http.server
import re
import sys
import urllib.parse
from pathlib import Path


def clean(part: str) -> str:
    return re.sub(r'[^a-z0-9-]', '', part.lower())


def receive(out: Path, port: int) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers['Content-Length'])).decode()
            saved = 0
            for key, value in urllib.parse.parse_qsl(body):
                folder, _, name = key.partition('__')
                folder, name = clean(folder), clean(name)
                if not folder or not name or ',' not in value:
                    continue
                (out / folder).mkdir(parents=True, exist_ok=True)
                (out / folder / f'{name}.jpg').write_bytes(base64.b64decode(value.split(',', 1)[1]))
                saved += 1
            print(f'frames: saved {saved}', flush=True)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'saved {saved}'.encode())

        def log_message(self, *args):
            pass

    out.mkdir(parents=True, exist_ok=True)
    print(f'frames: receiving on http://127.0.0.1:{port}/ into {out}', flush=True)
    http.server.HTTPServer(('127.0.0.1', port), Handler).serve_forever()


def sheet(frames: Path, sheets: Path) -> None:
    from PIL import Image, ImageDraw
    files = sorted(frames.glob('c*.jpg'))
    if not files:
        sys.exit(f'frames: no c<seconds>.jpg files in {frames}')
    sheets.mkdir(parents=True, exist_ok=True)
    per, cols, w, h, label = 20, 4, 400, 225, 18
    for start in range(0, len(files), per):
        chunk = files[start:start + per]
        rows = (len(chunk) + cols - 1) // cols
        page = Image.new('RGB', (cols * w, rows * (h + label)), 'white')
        draw = ImageDraw.Draw(page)
        for i, f in enumerate(chunk):
            t = int(re.sub(r'\D', '', f.stem) or 0)
            x, y = (i % cols) * w, (i // cols) * (h + label)
            page.paste(Image.open(f).resize((w, h)), (x, y + label))
            draw.text((x + 4, y + 3), f'{t // 60}:{t % 60:02d}', fill='black')
        page.save(sheets / f'sheet{start // per:02d}.jpg', quality=80)
    print(f'frames: {len(files)} frames on {(len(files) + per - 1) // per} sheets in {sheets}')


def main() -> None:
    ap = argparse.ArgumentParser(prog='frames.py')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('receive')
    r.add_argument('out', type=Path)
    r.add_argument('--port', type=int, default=8765)
    s = sub.add_parser('sheet')
    s.add_argument('frames', type=Path)
    s.add_argument('sheets', type=Path)
    a = ap.parse_args()
    try:
        receive(a.out, a.port) if a.cmd == 'receive' else sheet(a.frames, a.sheets)
    except OSError as e:
        print(f'frames: {e}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
