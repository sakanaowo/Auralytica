"""Offline installed-package quickstart smoke through the web-only launcher."""

import importlib.metadata
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
import auralytica


def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    takeout = root/'Takeout'/'history'; takeout.mkdir(parents=True)
    history = json.dumps([
        {'title': 'Watched Nhạc thử nghiệm', 'titleUrl': 'https://youtu.be/00000000000',
         'subtitles': [{'name': 'Artist - Topic'}]},
        {'title': 'Watched Podcast', 'titleUrl': 'https://youtu.be/00000000001'},
    ]).encode()
    (takeout/'watch-history.json').write_bytes(history)
    executable = str(Path(sys.executable).parent/'auralytica')
    database = root/'library.sqlite3'
    subprocess.run([executable, '--help'], capture_output=True, check=True, timeout=10)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'

    def json_request(path, *, method='GET', data=None, content_type=None):
        headers = {'Origin': origin}
        if content_type:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(origin+path, method=method, headers=headers, data=data)
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def upload():
        boundary = 'auralytica-' + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
                'filename="Takeout/history/watch-history.json"\r\n'
                'Content-Type: application/json\r\n\r\n').encode()
        body += history + f'\r\n--{boundary}--\r\n'.encode()
        return json_request('/api/imports', method='POST', data=body,
                            content_type=f'multipart/form-data; boundary={boundary}')

    with (root/'server.log').open('w') as log:
        server = subprocess.Popen(
            [executable, '--no-browser', '--port', str(port), '--database', str(database)],
            stdout=log, stderr=log,
        )
        try:
            for _ in range(80):
                try:
                    health = json_request('/api/health')
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Server did not start')
            assert health['database_id'] == auralytica.database_identity(database)
            first = upload()
            assert first['statistics']['unique_videos'] == 2
            assert json_request('/api/videos?group=music')['group_totals'] == {'music': 1, 'rest': 1}
            json_request('/api/videos/move', method='POST', content_type='application/json',
                         data=json.dumps({'video_ids': ['00000000001'], 'to_group': 'music'}).encode())
            assert json_request('/api/videos?group=music')['filtered_count'] == 2
            assert upload()['reused']
            assert json_request('/api/videos?group=music')['filtered_count'] == 2
            reused = subprocess.run(
                [executable, '--no-browser', '--port', str(port), '--database', str(database)],
                capture_output=True, text=True, timeout=5,
            )
            assert reused.returncode == 0
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()
    packages = sorted(dist.metadata['Name'].lower() for dist in importlib.metadata.distributions())
    assert not {'playwright', 'httpx', 'jupyterlab', 'pandas'} & set(packages)
    assert Path(auralytica.__file__).is_relative_to(Path(sys.prefix))
    report = dict(python=sys.version.split()[0], sqlite=sqlite3.sqlite_version,
                  installed_package=True, runtime_packages=len(packages), notebook_or_test_dependencies=False,
                  web_import=True, web_move=True, reimport_preserved=True, launcher_reused=True)
    (root/'validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
