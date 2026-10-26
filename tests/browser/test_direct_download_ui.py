"""Playwright browser test for the quick-download (Tải nhanh) workspace.

Runs against download_server.py: real HTTP, database and worker, with a fixture
adapter instead of yt-dlp, so nothing reaches YouTube or the user's ~/Music.
"""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from playwright.sync_api import sync_playwright, expect


@unittest.skipUnless(shutil.which('ffmpeg'), 'quick download transcodes with ffmpeg')
class DirectDownloadBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'real-audio').touch()
        self.music = self.root / 'Music'

        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'
        self.log = (self.root / 'server.log').open('w')
        self.addCleanup(self.log.close)

        command = [sys.executable, str(Path(__file__).with_name('download_server.py')), str(self.root), str(port)]
        self.server = subprocess.Popen(command, stdout=self.log, stderr=self.log)
        self.addCleanup(self.server.wait)
        self.addCleanup(self.server.terminate)

        for _ in range(60):
            try:
                urllib.request.urlopen(self.url, timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)

        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch()
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={'width': 1440, 'height': 900})
        self.page.route('https://i.ytimg.com/**', lambda route: route.abort())
        self.page.goto(self.url)

    def test_resolve_edit_download_and_open_player(self):
        page = self.page

        # 1. Quick download is reachable without any Takeout import.
        page.locator('#mode-quick-download').click()
        urls_input = page.locator('#direct-urls-input')
        expect(urls_input).to_be_visible()
        analyze_btn = page.locator('#analyze-urls-btn')
        expect(analyze_btn).to_be_disabled()

        # 2. Resolution is mocked: deterministic and offline.
        page.route('**/api/download/direct/resolve', lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps({
                'videos': [{
                    'video_id': 'dQw4w9WgXcQ',
                    'title': 'Never Gonna Give You Up',
                    'artist': 'Rick Astley',
                    'channel': 'Rick Astley',
                    'duration': 213,
                }],
                'invalid_urls': ['not-a-link'],
                'unavailable': [{'video_id': 'privateVid1', 'url': 'https://youtu.be/privateVid1',
                                 'code': 'unavailable', 'message': 'Video không khả dụng.'}],
                'truncated': False,
            })))
        urls_input.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://youtu.be/privateVid1\nnot-a-link')
        expect(analyze_btn).to_be_enabled()
        analyze_btn.click()

        # 3. Only the downloadable video is listed; the rest is reported.
        title_input = page.locator('input[value="Never Gonna Give You Up"]')
        expect(title_input).to_be_visible(timeout=5000)
        expect(page.locator('input[value="Rick Astley"]')).to_be_visible()
        report = page.locator('#direct-resolve-report')
        expect(report).to_contain_text('1 video không tải được')
        expect(report).to_contain_text('privateVid1')
        expect(report).to_contain_text('1 liên kết không nhận dạng được')

        # 4. Inline edit updates the planned file name.
        title_input.fill('Never Gonna Give You Up (Remastered)')
        page.locator('button:has-text("MP3 320kbps")').click()
        expect(page.locator('text=Rick Astley - Never Gonna Give You Up (Remastered).mp3')).to_be_visible()
        page.locator('#output-dir').fill(str(self.music))

        # 5. Start; the fixture worker holds the item until released.
        start_btn = page.locator('#start-direct-download-btn')
        expect(start_btn).to_contain_text('(1)')
        start_btn.click()
        expect(page.locator('text=Tiến trình #1')).to_be_visible(timeout=5000)

        # 6. While the worker is busy, a second batch cannot be started.
        expect(start_btn).to_be_disabled(timeout=10000)
        expect(start_btn).to_contain_text('Đang có lượt tải chạy')

        # 7. Release the worker; the edited tags name the transcoded file.
        (self.root / 'release').touch()
        expect(page.locator('text=Hoàn tất').first).to_be_visible(timeout=20000)
        expected = self.music / 'Rick Astley - Never Gonna Give You Up (Remastered).mp3'
        for _ in range(50):
            if expected.exists():
                break
            time.sleep(0.1)
        self.assertTrue(expected.is_file(), sorted(p.name for p in self.music.glob('*')))

        # 8. Quick download never touches Takeout review state.
        workflow = json.loads(urllib.request.urlopen(self.url + '/api/workflow').read())
        self.assertFalse(workflow['batch_locked'])

        # 9. The player opens from the batch monitor.
        page.locator('button:has-text("Mở Player")').click()
        expect(page.locator('text=Thư viện của bạn')).to_be_visible(timeout=5000)


if __name__ == '__main__':
    unittest.main()
