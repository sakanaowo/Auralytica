"""Playwright browser tests for Takeout Studio Direct YouTube Download."""
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


class DirectDownloadBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

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

    def test_direct_download_navigation_and_submission(self):
        page = self.page

        # 1. Clicking Tải nhanh mode button switches to Quick YouTube Downloader
        quick_mode_btn = page.locator('#mode-quick-download')
        expect(quick_mode_btn).to_be_visible()
        quick_mode_btn.click()

        # Header should be visible
        expect(page.locator('text=Quick YouTube Downloader')).to_be_visible()
        expect(page.locator('text=Tải nhanh trực tiếp từ YouTube')).to_be_visible()

        # 2. Check input controls
        urls_input = page.locator('#direct-urls-input')
        expect(urls_input).to_be_visible()
        analyze_btn = page.locator('#analyze-urls-btn')
        expect(analyze_btn).to_be_disabled()

        # 3. Fill YouTube URL
        urls_input.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        expect(analyze_btn).to_be_enabled()

        # 4. Mock the resolution endpoint so test is deterministic and offline-capable
        def handle_resolve(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "videos": [
                        {
                            "video_id": "dQw4w9WgXcQ",
                            "title": "Never Gonna Give You Up",
                            "artist": "Rick Astley",
                            "channel": "Rick Astley",
                            "duration": 213,
                            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
                        }
                    ],
                    "invalid_urls": []
                })
            )
        page.route("**/api/download/direct/resolve", handle_resolve)

        analyze_btn.click()

        # 5. Verify resolved item appears in metadata editor list
        expect(page.locator('text=Danh sách bài hát tìm thấy (1)')).to_be_visible(timeout=5000)
        title_input = page.locator('input[value="Never Gonna Give You Up"]')
        expect(title_input).to_be_visible()
        artist_input = page.locator('input[value="Rick Astley"]')
        expect(artist_input).to_be_visible()

        # Test editing metadata inline
        title_input.fill("Never Gonna Give You Up (Remastered)")
        expect(page.locator('text=Rick Astley - Never Gonna Give You Up (Remastered)')).to_be_visible()

        # 6. Verify start download button is enabled with 1 item
        start_btn = page.locator('#start-direct-download-btn')
        expect(start_btn).to_be_enabled()
        expect(start_btn).to_contain_text('(1 bài)')

        # 7. Click Start Download (this reaches real /api/download/direct on backend)
        start_btn.click()

        # 8. Verify active batch progress monitor displays batch information
        expect(page.locator('text=Tiến trình tải lượt #1')).to_be_visible(timeout=5000)
        expect(page.locator('text=Đã tạo lượt tải #1 gồm 1 bài hát.')).to_be_visible()

        screenshot_dir = Path('artifacts/browser-runs')
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        view_screenshot = screenshot_dir / 'direct-download-view-verified.png'
        page.screenshot(path=str(view_screenshot), full_page=True)
        self.assertTrue(view_screenshot.exists())

        # 9. Verify navigation button to Player
        player_nav_btn = page.locator('button:has-text("Mở Music Player")')
        expect(player_nav_btn).to_be_visible()
        player_nav_btn.click()

        # 10. Verify we switched to Music Player workspace
        expect(page.locator('text=Trình phát nhạc')).to_be_visible(timeout=5000)

        # 11. Capture evidence screenshot
        screenshot_path = screenshot_dir / 'direct-download-verified.png'
        page.screenshot(path=str(screenshot_path), full_page=True)
        self.assertTrue(screenshot_path.exists())
