"""Fetching from the Rwanda Law Reform Commission's open API (amategeko.gov.rw), with an on-disk cache.

    https://apis.amategeko.gov.rw/v1/site/documents-files/<file id>  -> JSON with a signed `file_url` (expires in 1 h)
    the signed URL                                                     -> the PDF bytes (Official Gazette, trilingual)

The PDF is cached under its FILE id (cache/file-<id>.pdf), the metadata as cache/meta-<id>.json with the signed URL
removed, so an --offline rebuild is byte-identical. robots.txt (2026-10-28): "User-agent: * / Disallow:" (open).
Standard library + curl fallback.
"""
import datetime as dt
import gzip
import json
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / 'cache'
API = 'https://apis.amategeko.gov.rw/v1/site'
SITE = 'https://www.amategeko.gov.rw'
UA = 'LexifinaLawHistory/1.0 (law@lexifina.com)'


def _get(url: str) -> bytes:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = r.read()
                if r.headers.get('Content-Encoding') == 'gzip':
                    d = gzip.decompress(d)
            return d
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503):
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except Exception:
            out = subprocess.run(['curl', '-sS', '-f', '--compressed', '-A', UA, url], capture_output=True)
            if out.returncode == 0:
                return out.stdout
            time.sleep(2)
    raise SystemExit('cannot fetch ' + url)


def _stamp():
    s = CACHE / 'retrieved.txt'
    if not s.exists():
        s.write_text(dt.date.today().isoformat() + '\n', encoding='utf-8', newline='\n')


def meta(file_id: int, offline: bool = False) -> dict:
    CACHE.mkdir(exist_ok=True)
    (CACHE / '.gitignore').write_text('*\n', encoding='utf-8', newline='\n')
    f = CACHE / f'meta-{file_id}.json'
    if f.exists():
        return json.loads(f.read_text(encoding='utf-8'))
    if offline:
        raise SystemExit(f'--offline: metadata of file {file_id} is not in the cache')
    d = json.loads(_get(f'{API}/documents-files/{file_id}'))['data']
    url = d.pop('file_url')
    pdf = CACHE / f'file-{file_id}.pdf'
    if not pdf.exists():
        b = _get(url)
        if not b.startswith(b'%PDF'):
            raise SystemExit(f'file {file_id}: not a PDF')
        pdf.write_bytes(b)
    d['file_url_path'] = url.split('?', 1)[0]
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    _stamp()
    time.sleep(0.25)
    return d


def pdf_path(file_id: int, offline: bool = False) -> Path:
    meta(file_id, offline)
    return CACHE / f'file-{file_id}.pdf'


def retrieved() -> str:
    p = CACHE / 'retrieved.txt'
    return p.read_text(encoding='utf-8').strip() if p.exists() else dt.date.today().isoformat()
