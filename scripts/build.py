"""Verified upstream release assembler. Python standard library only; never executes archives."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from html.parser import HTMLParser
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE = 500 * 1024 * 1024
MAX_SITE = 900 * 1024 * 1024
STABLE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')


def request(url, limit=MAX_ARCHIVE):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'api.github.com', 'github.com', 'raw.githubusercontent.com'}:
        raise ValueError('Untrusted download URL: ' + url)
    headers = {'User-Agent': 'Craft-Suite-Web-builder', 'Accept': 'application/vnd.github+json'}
    if parsed.hostname == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=90) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError('Download exceeds size limit')
            return data
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (TimeoutError, ConnectionError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def api(path):
    return json.loads(request('https://api.github.com/' + path, 20 * 1024 * 1024))


def choose_release(releases):
    valid = [r for r in releases if not r.get('draft') and not r.get('prerelease') and STABLE.fullmatch(r['tag_name'])]
    if not valid:
        raise ValueError('No stable semantic-version release found')
    return max(valid, key=lambda r: tuple(map(int, STABLE.fullmatch(r['tag_name']).groups())))


def checksum_for(text, filename):
    matches = []
    for line in text.splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)', line.strip())
        if match and match[2].removeprefix('./') == filename:
            matches.append(match[1].lower())
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous checksum for ' + filename)
    return matches[0]


def resolve(app):
    app_id = app['id']
    if not re.fullmatch(r'[a-z]+', app_id):
        raise ValueError('Invalid app ID')
    repo = 'storytold/' + app_id
    pin = app.get('pin')
    if pin:
        if not STABLE.fullmatch(pin):
            raise ValueError('Pins must be exact stable tags, e.g. v0.10.1')
        release = api(f'repos/{repo}/releases/tags/{quote(pin, safe="")}')
        if release.get('draft') or release.get('prerelease'):
            raise ValueError('Pinned release is not stable')
    else:
        release = choose_release(api(f'repos/{repo}/releases?per_page=100'))
    tag = release['tag_name']
    version = tag.removeprefix('v')
    assets = {asset['name']: asset for asset in release['assets']}
    filename = f'{app_id}-web-{version}.zip'
    if filename not in assets or 'SHA256SUMS.txt' not in assets:
        raise ValueError(f'{repo} {tag} missing Web ZIP/checksums; pin a complete release')
    archive = assets[filename]
    expected = checksum_for(request(assets['SHA256SUMS.txt']['browser_download_url'], 2 * 1024 * 1024).decode(), filename)
    digest = archive.get('digest')
    if digest and digest != 'sha256:' + expected:
        raise ValueError(f'{repo}: release digest disagrees with SHA256SUMS.txt')
    if archive['size'] > MAX_ARCHIVE:
        raise ValueError('Archive too large: ' + repo)
    return dict(app, repository=repo, version=version, tag=tag,
                publishedAt=release['published_at'], sha256=expected,
                archive=archive['browser_download_url'], archiveBytes=archive['size'],
                assetId=archive['id'], path=f'apps/{app_id}/{tag}/')


def safe_extract(archive_path, target):
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(info.file_size for info in infos) > MAX_SITE:
            raise ValueError('Archive expansion limit exceeded')
        seen = set()
        for info in infos:
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename or stat.S_ISLNK(mode):
                raise ValueError('Unsafe archive path: ' + info.filename)
            if info.filename in seen:
                raise ValueError('Duplicate archive entry')
            seen.add(info.filename)
        # Extract to a fresh temporary tree; zip entries cannot escape this root.
        archive.extractall(target)
    entries = list(target.iterdir())
    base = entries[0] if len(entries) == 1 and entries[0].is_dir() else target
    if not (base / 'index.html').is_file():
        raise ValueError('Web archive has no top-level index.html')
    return base


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base' and attrs.get('href', '').startswith('/'):
            raise ValueError('Root-absolute base URL is incompatible with project Pages')
        if tag in {'script', 'img', 'link'}:
            value = attrs.get('src' if tag != 'link' else 'href')
            if value:
                self.urls.append(value)


def verify_web(base):
    parser = References()
    parser.feed((base / 'index.html').read_text())
    for value in parser.urls:
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc or value.startswith('#'):
            continue
        if parsed.path.startswith('/'):
            raise ValueError('Root-absolute asset URL: ' + value)
        asset = (base / unquote(parsed.path)).resolve()
        if not asset.is_relative_to(base.resolve()) or not asset.exists():
            raise ValueError('Missing/escaping local asset: ' + value)
    if not list(base.rglob('*.wasm')) or not list(base.rglob('*.js')):
        raise ValueError('WebAssembly/JavaScript files missing')
    for path in base.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:
                magic = stream.read(4)
            if magic == b'\x7fELF' or magic[:2] == b'MZ' or path.suffix in {'.exe', '.dll', '.so', '.rlib', '.dylib'}:
                raise ValueError('Unexpected native binary: ' + str(path))


def install(app, dist):
    cache = ROOT / '.cache' / (app['sha256'] + '.zip')
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists() or hashlib.sha256(cache.read_bytes()).hexdigest() != app['sha256']:
        data = request(app['archive'])
        if hashlib.sha256(data).hexdigest() != app['sha256']:
            raise ValueError('Checksum mismatch: ' + app['id'])
        cache.write_bytes(data)
    target = dist / app['path']
    with tempfile.TemporaryDirectory() as temp:
        base = safe_extract(cache, Path(temp))
        # Some LightCraft releases accidentally include unused Cargo output.
        # This is a narrowly documented exclusion; never run anything from it.
        if app['id'] == 'lightcraft':
            for name in ['target', 'build', 'deps', '.fingerprint', 'examples', 'incremental']:
                extra = base / name
                if extra.is_dir():
                    shutil.rmtree(extra)
        verify_web(base)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(base, target)
    # Stable entry redirects to a versioned directory. Do not change upstream HTML.
    stable = target.parent / 'index.html'
    stable.write_text(f'<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=./{app["tag"]}/"><title>{app["name"]}</title><a href="./{app["tag"]}/">開啟 {app["name"]}</a></html>')
    # Include the pinned upstream license and notices, failing closed if missing.
    for name in ['LICENSE-MIT', 'LICENSE-APACHE']:
        content = request(f'https://raw.githubusercontent.com/{app["repository"]}/{app["tag"]}/{name}', 2 * 1024 * 1024)
        (target / name).write_bytes(content)
    for name in ['NOTICE', 'ATTRIBUTION.md']:
        try:
            content = request(f'https://raw.githubusercontent.com/{app["repository"]}/{app["tag"]}/{name}', 2 * 1024 * 1024)
            (target / name).write_bytes(content)
        except HTTPError as error:
            if error.code != 404:
                raise
    app['deployedBytes'] = sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
    print(f'{app["name"]} {app["tag"]}: verified, {app["deployedBytes"] / 1024**2:.1f} MiB', flush=True)
    return app


def fingerprint(apps):
    content = [{k: app.get(k) for k in ('id', 'tag', 'sha256', 'assetId')} for app in apps]
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='UI-only preview; no fake working launch links')
    parser.add_argument('--resolve-only', action='store_true')
    parser.add_argument('--locked', action='store_true', help='Build exact versions from release-lock.json')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/apps.json').read_text())
    if len(config) != 13 or len({a['id'] for a in config}) != 13:
        raise ValueError('Expected 13 distinct apps')
    if args.preview:
        apps = config
    elif args.locked:
        apps = json.loads((ROOT / 'release-lock.json').read_text())['apps']
        if [a['id'] for a in apps] != [a['id'] for a in config]:
            raise ValueError('Lock/config mismatch')
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            apps = list(pool.map(resolve, config))
        (ROOT / 'release-lock.json').write_text(json.dumps({'fingerprint': fingerprint(apps), 'apps': apps}, ensure_ascii=False, indent=2) + '\n')
    if args.resolve_only:
        return
    dist = ROOT / 'dist'
    if dist.exists():
        shutil.rmtree(dist)  # Fixed generated directory, never user data.
    shutil.copytree(ROOT / 'web', dist)
    (dist / '.nojekyll').touch()
    shutil.copyfile(ROOT / 'ATTRIBUTION.md', dist / 'ATTRIBUTION.md')
    if not args.preview:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            apps = list(pool.map(lambda app: install(app, dist), apps))
    total = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if total > MAX_SITE:
        raise ValueError('Site exceeds conservative 900 MiB Pages budget')
    output = {'hubVersion': '1.0.0', 'builtAt': None if args.preview else datetime.now(timezone.utc).isoformat(),
              'fingerprint': None if args.preview else fingerprint(apps), 'totalBytes': total, 'apps': apps}
    (dist / 'versions.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(f'Site: {total / 1024**2:.1f} MiB; {len(apps)} apps')


if __name__ == '__main__':
    main()
