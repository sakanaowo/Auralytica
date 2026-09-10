"""Offline installed-package quickstart smoke using only the standard library.

Run with the clean environment's Python: quickstart.py NEW_WORK_DIRECTORY
"""
import importlib.metadata
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import auralytica


def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    takeout = root/'Takeout'/'history'; takeout.mkdir(parents=True)
    (takeout/'watch-history.json').write_text(json.dumps([
        {'title': 'Watched Nhạc thử nghiệm', 'titleUrl': 'https://youtu.be/00000000000',
         'subtitles': [{'name': 'Artist - Topic'}]},
        {'title': 'Watched Podcast', 'titleUrl': 'https://youtu.be/00000000001'}]))
    cli = str(Path(sys.executable).parent/'auralytica')
    database = root/'library.sqlite3'
    def command(*args):
        result = subprocess.run([cli, *args, '--database', str(database)],
                                capture_output=True, text=True, check=True, timeout=10)
        return json.loads(result.stdout)
    subprocess.run([cli, '--help'], capture_output=True, check=True, timeout=10)
    assert command('import', str(root/'Takeout'))['statistics']['unique_videos'] == 2
    assert command('list', '--group', 'music')['group_totals'] == {'music': 1, 'rest': 1}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    with (root/'server.log').open('w') as log:
        server = subprocess.Popen([cli, 'serve', '--port', str(port), '--database', str(database)],
                                  stdout=log, stderr=log)
        try:
            for _ in range(60):
                try:
                    with urllib.request.urlopen(origin, timeout=1) as response:
                        assert 'Tải toàn bộ' in response.read().decode()
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Server did not start')
            for asset in ('app.js', 'style.css'):
                with urllib.request.urlopen(origin+'/static/'+asset, timeout=5) as response:
                    assert response.status == 200 and response.read()
            request = urllib.request.Request(origin+'/api/videos/move', method='POST',
                headers={'Origin': origin, 'Content-Type': 'application/json'},
                data=json.dumps({'video_ids': ['00000000001'], 'to_group': 'music'}).encode())
            with urllib.request.urlopen(request, timeout=5) as response:
                assert response.status == 200
            assert command('list', '--group', 'music')['filtered_count'] == 2
            assert command('import', str(root/'Takeout'))['reused']
            assert command('list', '--group', 'music')['filtered_count'] == 2
        finally:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()
    packages = sorted(dist.metadata['Name'].lower() for dist in importlib.metadata.distributions())
    assert not {'playwright', 'httpx', 'jupyterlab', 'pandas'} & set(packages)
    assert Path(auralytica.__file__).is_relative_to(Path(sys.prefix))
    report = dict(python=sys.version.split()[0], sqlite=sqlite3.sqlite_version,
                  installed_package=True, runtime_packages=len(packages), notebook_or_test_dependencies=False,
                  cli_import=True, web_assets=True, web_move_visible_in_cli=True, reimport_preserved=True)
    (root/'validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
