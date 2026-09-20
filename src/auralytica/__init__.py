"""Auralytica local web launcher."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import webbrowser


DEFAULT_DATABASE = Path.home()/'.local/share/auralytica/library.sqlite3'


class LauncherError(ValueError):
    """The requested local server cannot be started or safely reused."""


def database_identity(database):
    """Identify a database without exposing its local path over HTTP."""
    value = str(Path(database).expanduser().resolve()).encode()
    return hashlib.sha256(value).hexdigest()[:16]


def _port_in_use(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.2):
            return True
    except OSError:
        return False


def _probe_instance(url):
    try:
        with urlopen(url + '/api/health', timeout=.5) as response:
            value = json.load(response)
            return value if isinstance(value, dict) else None
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def _is_expected(identity, database):
    return identity == {
        'app': 'auralytica',
        'api': 1,
        'database_id': database_identity(database),
    }


def _open_when_ready(url, database, browser_open):
    for _ in range(100):
        if _is_expected(_probe_instance(url), database):
            browser_open(url)
            return
        time.sleep(.05)


def launch(database=DEFAULT_DATABASE, *, port=8765, open_browser=True,
           run_server=None, browser_open=None):
    """Start one loopback instance or reopen the verified matching instance."""
    if not 1 <= port <= 65535:
        raise LauncherError('port phải trong khoảng 1–65535.')
    database = Path(database).expanduser()
    url = f'http://127.0.0.1:{port}'
    browser_open = browser_open or webbrowser.open
    if _port_in_use(port):
        if not _is_expected(_probe_instance(url), database):
            raise LauncherError(
                f'Cổng {port} đang được process khác hoặc thư viện Auralytica khác sử dụng. '
                'Ứng dụng không dừng hoặc tái dùng process đó; hãy đóng nó hoặc chọn --port khác.'
            )
        if open_browser:
            browser_open(url)
        return 'reused'

    if run_server is None:
        import uvicorn
        run_server = uvicorn.run
    from .web import create_app
    if open_browser:
        threading.Thread(target=_open_when_ready, args=(url, database, browser_open), daemon=True).start()
    run_server(create_app(database, port=port), host='127.0.0.1', port=port,
               proxy_headers=False, access_log=False)
    return 'started'


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='auralytica',
        description='Mở giao diện web local để nhập Takeout, khám phá, deduplicate và tải nhạc.',
    )
    parser.add_argument('--port', type=int, default=8765, help='Cổng loopback (mặc định: 8765)')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE,
                        help='Database local (mặc định: %(default)s)')
    parser.add_argument('--no-browser', action='store_true', help='Không tự mở trình duyệt')
    args = parser.parse_args()
    try:
        launch(args.database, port=args.port, open_browser=not args.no_browser)
    except LauncherError as exc:
        parser.error(str(exc))
