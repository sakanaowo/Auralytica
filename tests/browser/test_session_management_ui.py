"""Playwright browser tests for Takeout Session Management."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from playwright.sync_api import sync_playwright, expect


class SessionManagementBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        # Folder 1: 4 videos
        self.takeout_1 = self.root / 'Takeout_1'
        (self.takeout_1 / 'history').mkdir(parents=True)
        rows_1 = [
            {
                'titleUrl': f'https://youtu.be/sess1vid00{i}',
                'title': f'Session 1 Track {i}',
                'subtitles': [{'name': 'Artist - Topic' if i < 2 else 'Channel 1'}],
            }
            for i in range(4)
        ]
        (self.takeout_1 / 'history' / 'watch-history.json').write_text(json.dumps(rows_1))

        # Folder 2: 2 videos
        self.takeout_2 = self.root / 'Takeout_2'
        (self.takeout_2 / 'history').mkdir(parents=True)
        rows_2 = [
            {
                'titleUrl': f'https://youtu.be/sess2vid00{i}',
                'title': f'Session 2 Track {i}',
                'subtitles': [{'name': 'Artist 2 - Topic'}],
            }
            for i in range(2)
        ]
        (self.takeout_2 / 'history' / 'watch-history.json').write_text(json.dumps(rows_2))

        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'
        self.log = (self.root / 'server.log').open('w')
        self.addCleanup(self.log.close)

        command = [
            str(Path(sys.executable).parent / 'auralytica'),
            '--no-browser',
            '--port',
            str(port),
            '--database',
            str(self.root / 'state.sqlite3'),
        ]
        self.server = subprocess.Popen(command, stdout=self.log, stderr=self.log)
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
        self.page.goto(self.url)

    def test_session_management_flow(self):
        page = self.page

        # 1. Initial page: Step 01 Import should display dropzone
        expect(page.locator('text=01 · Nhập')).to_be_visible()
        expect(page.locator('#folder-input')).to_be_attached()

        # 2. Upload first takeout folder
        page.locator('#folder-input').set_input_files(self.takeout_1)

        # After import success, it navigates to explore (Step 02)
        expect(page.locator('text=Nhạc đã nhận diện')).to_be_visible(timeout=10000)

        # 3. Navigate back to Step 01 · Import
        page.locator('#nav-step-import').click()
        expect(page.locator('text=Đang hoạt động')).to_be_visible()
        expect(page.locator('text=Phiên #1')).to_be_visible()
        expect(page.locator('text=Tiếp tục xem dữ liệu')).to_be_visible()

        # 4. Open "Nạp phiên mới"
        page.locator('button:has-text("Nạp phiên mới")').click()
        expect(page.locator('text=Nạp phiên Takeout mới')).to_be_visible()
        expect(page.locator('#folder-input')).to_be_attached()

        # 5. Upload second takeout folder
        page.locator('#folder-input').set_input_files(self.takeout_2)
        expect(page.locator('text=Nhạc đã nhận diện')).to_be_visible(timeout=10000)

        # 6. Return to Step 01 · Import
        page.locator('#nav-step-import').click()

        # Session #2 should now be Active
        expect(page.locator('text=Phiên #2')).to_be_visible()
        expect(page.locator('text=Các phiên lưu trữ khác (1)')).to_be_visible()
        expect(page.locator('text=Phiên #1')).to_be_visible()

        # 7. Switch back to Session #1
        page.locator('button:has-text("Kích hoạt phiên này")').click()
        expect(page.locator('text=Đã chuyển thành công sang phiên #1')).to_be_visible()

        # Now Session #1 is active again!
        # And Session #2 is in other sessions
        expect(page.locator('text=Các phiên lưu trữ khác (1)')).to_be_visible()

        # 8. Delete Session #2
        # Click trash icon on Session #2
        trash_btn = page.locator('button[title*="Xóa vĩnh viễn"]')
        expect(trash_btn).to_be_visible()
        trash_btn.click()

        # Confirmation modal appears
        expect(page.locator('text=Xác nhận xóa phiên #2?')).to_be_visible()
        page.locator('button:has-text("Xác nhận xóa")').click()

        # Success message
        expect(page.locator('text=Đã xóa thành công phiên #2')).to_be_visible()

        # Other sessions count should now be 0
        expect(page.locator('text=Các phiên lưu trữ khác')).to_be_hidden()

        # Take screenshot for evidence
        screenshot_dir = Path('artifacts/browser-runs')
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / 'session-management-verified.png'
        page.screenshot(path=str(screenshot_path), full_page=True)
        self.assertTrue(screenshot_path.exists())
