"""Playwright browser tests for Player Spotify-style resizable UI and Shortcuts modal."""
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from playwright.sync_api import sync_playwright, expect


class PlayerUIBrowserTests(unittest.TestCase):
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
        self.process = subprocess.Popen(command, stdout=self.log, stderr=subprocess.STDOUT)
        self.addCleanup(self._stop_server)

        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f'{self.url}/api/health', timeout=0.2) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.05)
        else:
            self.fail('Server did not become ready within 10s')

    def _stop_server(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def test_player_spotify_layout_and_shortcuts_modal(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})

            # Navigate to /player
            page.goto(f'{self.url}/player')

            # Verify Player Workspace elements
            expect(page.locator('text=Thư viện của bạn')).to_be_visible(timeout=5000)
            expect(page.locator('text=Tất cả bài hát')).to_be_visible()

            # Verify Resizer handle for left sidebar
            left_resizer = page.locator('div[title*="Kéo để chỉnh độ rộng thư viện"]')
            expect(left_resizer).to_be_visible()

            # Verify PersistentPlayerBar at bottom
            footer = page.locator('footer')
            expect(footer).to_be_visible()

            # Verify Shortcuts button in Header or Footer
            shortcuts_btn = footer.locator('button[title*="Phím tắt điều khiển"]')
            expect(shortcuts_btn).to_be_visible()

            # Click shortcuts button -> Modal should open
            shortcuts_btn.click()
            expect(page.locator('text=Phím tắt điều khiển')).to_be_visible()
            expect(page.locator('text=Phát / Tạm dừng')).to_be_visible()
            expect(page.locator('text=Bài tiếp theo')).to_be_visible()
            expect(page.locator('text=Bài trước đó')).to_be_visible()

            # Close modal with Escape
            page.keyboard.press('Escape')
            expect(page.locator('text=Phím tắt điều khiển')).not_to_be_visible()

            # Press '?' key -> Modal should open again
            page.keyboard.press('?')
            expect(page.locator('text=Phím tắt điều khiển')).to_be_visible()

            # Close modal with close button
            close_btn = page.locator('button:has-text("Đóng")')
            close_btn.click()
            expect(page.locator('text=Phím tắt điều khiển')).not_to_be_visible()

            # Test toggling right sidebar via Queue button
            queue_toggle = footer.locator('button[title*="Mở danh sách hàng đợi"]')
            queue_toggle.click()

            # Right sidebar should appear with right resizer handle
            expect(page.locator('aside button:has-text("Hàng đợi")')).to_be_visible()
            expect(page.locator('text=Hàng đợi đang trống')).to_be_visible()
            right_resizer = page.locator('div[title*="Kéo để chỉnh độ rộng thông tin"]')
            expect(right_resizer).to_be_visible()

            # Switch to Now Playing tab in Right Sidebar
            now_playing_tab = page.locator('aside button:has-text("Đang phát")')
            now_playing_tab.click()
            expect(page.locator('text=Chưa có bài hát nào đang phát')).to_be_visible()

            # Test shortcut 'i' to toggle (collapse) Now Playing right sidebar
            page.keyboard.press('i')
            expect(page.locator('text=Chưa có bài hát nào đang phát')).not_to_be_visible()

            # Test shortcut 'i' again to open Now Playing right sidebar
            page.keyboard.press('i')
            expect(page.locator('text=Chưa có bài hát nào đang phát')).to_be_visible()

            # Test shortcut 'q' to switch to Queue tab
            page.keyboard.press('q')
            expect(page.locator('text=Hàng đợi đang trống')).to_be_visible()

            # Test shortcut 'q' again to collapse right sidebar
            page.keyboard.press('q')
            expect(page.locator('text=Hàng đợi đang trống')).not_to_be_visible()

            # Test Input Guard: typing in search input should not trigger shortcuts
            search_input = page.locator('input[placeholder*="Tìm theo bài"]')
            search_input.click()
            search_input.fill('')
            page.keyboard.type('hello world q i ?')
            expect(search_input).to_have_value('hello world q i ?')
            # Verify shortcuts modal was not opened by typing '?'
            expect(page.locator('text=Phím tắt điều khiển')).not_to_be_visible()

            browser.close()
