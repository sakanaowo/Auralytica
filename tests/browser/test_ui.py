"""Real Chromium acceptance checks. Run separately with the browser dependency group."""
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from playwright.sync_api import sync_playwright, expect


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.takeout=self.root/'Takeout'
        (self.takeout/'history').mkdir(parents=True)
        rows=[{'titleUrl':f'https://youtu.be/{i:011d}', 'title':f'Watched Video {i:03d}',
               'subtitles':[{'name':'Artist - Topic' if i < 2 else 'Other channel'}]} for i in range(54)]
        rows[2]['title']='Watched <img src=x onerror="window.pwned=1">'
        (self.takeout/'history'/'watch-history.json').write_text(json.dumps(rows))
        (self.takeout/'unrelated.txt').write_text('must not upload')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{port}'
        self.log=(self.root/'server.log').open('w')
        self.addCleanup(self.log.close)
        command = [str(Path(sys.executable).parent/'auralytica'),'--no-browser','--port',str(port),
                   '--database',str(self.root/'state.sqlite3')]
        if self._testMethodName in {'test_download_all_stop_resume_errors_and_reload',
                                    'test_acceptance_large_history_restart_and_reimport',
                                    'test_metadata_preview_apply_without_cli',
                                    'test_dedup_alias_select_reject_undo_and_reload'}:
            command = [sys.executable, str(Path(__file__).with_name('download_server.py')),
                       str(self.root), str(port)]
        self.server_command = command
        self.server=subprocess.Popen(command,stdout=self.log,stderr=self.log)
        self.addCleanup(self.stop_server)
        for _ in range(60):
            try:
                urllib.request.urlopen(self.url,timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        self.playwright=sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser=self.playwright.chromium.launch()
        self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1440,'height':1000})
        self.page.route('https://i.ytimg.com/**',lambda route:route.abort())
        self.page.goto(self.url)

    def test_explore_music_first_summary_and_page_sizes(self):
        page = self.page
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#music-total')).to_have_text('2')
        expect(page.locator('#rest')).to_be_hidden()
        expect(page.locator('#summary-videos')).to_have_text('2')
        expect(page.locator('#summary-watches')).to_have_text('2')
        expect(page.locator('#import-result')).to_contain_text('54')
        self.assertFalse(any('/api/videos?' in url and 'group=rest' in url for url in requests))
        page.locator('#rest-toggle').click()
        expect(page.locator('#rest tbody tr')).to_have_count(50)
        page.locator('#rest .page-size').select_option('25')
        expect(page.locator('#rest tbody tr')).to_have_count(25)
        page.locator('#rest .next').click()
        expect(page.locator('#rest .page-label')).to_have_text('2 / 3')
        page.reload()
        expect(page.locator('#rest .page-label')).to_have_text('2 / 3')
        page.locator('#rest .row-move').first.click()
        expect(page.locator('#summary-videos')).to_have_text('3')
        expect(page.locator('#summary-decisions')).to_contain_text('1 thủ công')
        page.locator('#music .channel').fill('Artist - Topic')
        expect(page.locator('#music tbody tr')).to_have_count(2)
        expect(page.locator('#summary-videos')).to_have_text('3')
        page.locator('#rest-toggle').click()
        page.reload()
        expect(page.locator('#rest')).to_be_hidden()
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
        Path('artifacts/browser-runs').mkdir(parents=True, exist_ok=True)
        page.screenshot(path='artifacts/browser-runs/wft03-explore.png', full_page=True)

    def test_metadata_preview_apply_without_cli(self):
        page = self.page
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#music-total')).to_have_text('2')
        expect(page.locator('#metadata-scope')).to_contain_text('52')
        page.locator('#metadata-limit').fill('2')
        page.locator('#metadata-start').click()
        expect(page.locator('#metadata-status')).to_contain_text('Hoàn tất')
        expect(page.locator('#metadata-events')).to_contain_text('metadata_observed')
        page.locator('#classification-preview').click()
        expect(page.locator('#preview-summary')).to_contain_text('2 thay đổi')
        expect(page.locator('#preview-items tr')).to_have_count(2)
        page.locator('#classification-apply').click()
        expect(page.locator('#music-total')).to_have_text('4')
        expect(page.locator('#preview-summary')).to_contain_text('Đã áp dụng')
        page.reload()
        expect(page.locator('#music-total')).to_have_text('4')

    def test_dedup_alias_select_reject_undo_and_reload(self):
        rows = [
            {'titleUrl': 'https://youtu.be/aaaaaaaaaaa', 'title': 'Watched Shoujo A',
             'subtitles': [{'name': 'Artist - Topic'}]},
            {'titleUrl': 'https://youtu.be/bbbbbbbbbbb', 'title': 'Watched 少女A',
             'subtitles': [{'name': 'Artist - Topic'}]},
        ]
        (self.takeout/'history'/'watch-history.json').write_text(json.dumps(rows))
        page = self.page
        page.locator('#folder-input').set_input_files(self.takeout)
        page.locator('nav a[href="/deduplicate"]').click()
        page.locator('#manual-video-ids').fill('aaaaaaaaaaa, bbbbbbbbbbb')
        page.locator('#manual-alias').click()
        expect(page.locator('.dedup-member')).to_have_count(2)
        expect(page.locator('#dedup-groups')).to_contain_text('Shoujo A')
        expect(page.locator('#dedup-groups')).to_contain_text('少女A')
        expect(page.locator('#dedup-groups')).to_contain_text('Alias đã xác nhận')
        second = page.locator('.dedup-member').nth(1).locator('input[type=checkbox]')
        second.uncheck()
        expect(page.locator('#dedup-status')).to_contain_text('Đã lưu')
        page.reload()
        expect(page.locator('.dedup-member').nth(1).locator('input[type=checkbox]')).not_to_be_checked()
        page.locator('.reject-group').click()
        expect(page.locator('.reject-group')).to_contain_text('Hoàn tác')
        page.locator('.reject-group').click()
        expect(page.locator('.reject-group')).to_contain_text('Không ghép')
        page.locator('nav a[href="/explore"]').click()
        expect(page.locator('#music-total')).to_have_text('2')
        page.goto(self.url + '/deduplicate')
        expect(page.locator('.dedup-member').nth(1).locator('input[type=checkbox]')).not_to_be_checked()
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
        Path('artifacts/browser-runs').mkdir(parents=True, exist_ok=True)
        page.screenshot(path='artifacts/browser-runs/wft06-dedup.png', full_page=True)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('nav a[href="/download"]').click()
        page.locator('#output-dir').fill(str(self.root/'audio'))
        expect(page.locator('#download-preview')).to_contain_text('2 video nhạc')
        expect(page.locator('#download-preview')).to_contain_text('1 loại bởi Deduplicate')
        expect(page.locator('#download-preview')).to_contain_text('1 giữ lại')
        (self.root/'release').touch()
        page.locator('#download-all').click()
        expect(page.locator('#batch-summary')).to_contain_text('1 video')
        expect(page.locator('#batch-summary')).to_contain_text('Hoàn tất')
        with sqlite3.connect(self.root/'state.sqlite3') as db:
            self.assertEqual(db.execute('SELECT video_id FROM download_items').fetchall(), [('aaaaaaaaaaa',)])
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
        page.screenshot(path='artifacts/browser-runs/wft07-download.png', full_page=True)

    def test_workflow_navigation_query_history_and_retry(self):
        page = self.page
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        expect(page).to_have_url(self.url + '/import')
        expect(page.locator('.workspace')).to_be_hidden()
        page.goto(self.url + '/explore')
        expect(page.locator('#workflow-empty')).to_contain_text('Import')
        page.goto(self.url + '/import')
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page).to_have_url(self.url + '/explore')
        page.locator('#rest-toggle').click()
        page.locator('#rest .next').click()
        expect(page.locator('#rest .page-label')).to_have_text('2 / 2')
        page.reload()
        expect(page.locator('#rest .page-label')).to_have_text('2 / 2')
        page.locator('#rest .search').fill('Video 010')
        expect(page.locator('#rest tbody tr')).to_have_count(1)
        page.go_back()
        expect(page.locator('#rest .page-label')).to_have_text('2 / 2')
        page.go_forward()
        expect(page.locator('#rest .search')).to_have_value('Video 010')
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.locator('nav a[href="/deduplicate"]').click()
        expect(page.locator('#dedup-placeholder')).to_contain_text('Chưa quét gợi ý')
        expect(page.locator('.workspace')).to_be_hidden()
        expect(page.locator('#dropzone')).to_be_hidden()
        page.reload()
        expect(page.locator('#workflow-status')).to_contain_text('2 nhạc')
        self.assertFalse(any('/api/videos' in url or '/api/downloads' in url for url in requests))
        expect(page.locator('nav a[aria-current="page"]')).to_contain_text('Deduplicate')
        page.locator('#skip-dedup').click()
        expect(page).to_have_url(self.url + '/download')
        expect(page.locator('#download-preview')).to_contain_text('2 video nhạc')
        page.route('**/api/workflow', lambda route: route.fulfill(status=503, json={'detail': 'fixture offline'}))
        page.goto(self.url + '/explore')
        expect(page.locator('#workflow-status')).to_contain_text('fixture offline')
        page.unroute('**/api/workflow')
        page.locator('#workflow-retry').click()
        expect(page.locator('#music-total')).to_have_text('2')
        page.route('**/api/videos?*', lambda route: route.fulfill(status=503, json={'detail': 'list offline'}))
        page.locator('#music .search').fill('Video 000')
        expect(page.locator('#music .empty')).to_contain_text('list offline')
        page.unroute('**/api/videos?*')
        page.locator('#music .list-retry').click()
        expect(page.locator('#music tbody tr')).to_have_count(1)
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
        self.assertEqual(errors, [])
        Path('artifacts/browser-runs').mkdir(parents=True, exist_ok=True)
        page.screenshot(path='artifacts/browser-runs/wft02-explore.png', full_page=True)


    def test_download_all_stop_resume_errors_and_reload(self):
        page = self.page
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#music-total')).to_have_text('2')
        page.locator('#music .search').fill('Video 000')
        expect(page.locator('#music tbody tr')).to_have_count(1)
        page.locator('#music .select-page').check()
        page.locator('nav a[href="/download"]').click()
        page.locator('#output-dir').fill(str(self.root/'audio'))
        expect(page.locator('#download-all')).to_be_enabled()
        page.locator('#download-all').click()
        expect(page.locator('#batch-summary')).to_contain_text('2 video')
        expect(page.locator('#stop-download')).to_be_enabled()
        page.goto(self.url + '/explore')
        expect(page.locator('#music .row-move').first).to_be_disabled()
        page.goto(self.url + '/download')
        page.locator('#stop-download').click()
        expect(page.locator('#batch-summary')).to_contain_text('Đã dừng')
        page.goto(self.url + '/explore')
        page.locator('#music .row-move').first.click()
        expect(page.locator('#music-total')).to_have_text('1')
        page.locator('#music .row-move').first.click()
        expect(page.locator('#music-total')).to_have_text('0')
        page.goto(self.url + '/download')
        expect(page.locator('#download-preview')).to_contain_text('0 video nhạc')
        expect(page.locator('#batch-summary')).to_contain_text('Đã dừng')
        (self.root/'release').touch()
        page.locator('#resume-download').click()
        expect(page.locator('#batch-summary')).to_contain_text('Có lỗi')
        expect(page.locator('#download-items')).to_contain_text('fixture unavailable')
        page.reload()
        expect(page.locator('#batch-summary')).to_contain_text('Có lỗi')
        page.locator('#resume-download').click()
        expect(page.locator('#batch-summary')).to_contain_text('Hoàn tất')
        expect(page.locator('#download-all')).to_be_disabled()
        self.assertEqual(len(list((self.root/'audio').glob('*.webm'))), 2)
        self.assertGreater(page.locator('#download-items td').first.bounding_box()['width'], 150)
        page.screenshot(path='artifacts/browser-runs/t10-download.png', full_page=True)

    def test_acceptance_large_history_restart_and_reimport(self):
        page = self.page
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        rows = [{'titleUrl': f'https://youtu.be/{i:011d}', 'title': f'Watched Video {i:04d}',
                 'subtitles': [{'name': 'Artist - Topic'}] if i < 255 else []} for i in range(6400)]
        rows.extend([rows[1], rows[1]])
        (self.takeout/'history'/'watch-history.json').write_text(json.dumps(rows))
        started = time.perf_counter()
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#music-total')).to_have_text('255', timeout=15000)
        page.locator('#music .search').fill('Video 0000')
        expect(page.locator('#music tbody tr')).to_have_count(1)
        page.locator('#music .row-move').click()
        page.locator('#rest-toggle').click()
        page.locator('#rest .search').fill('Video 6399')
        expect(page.locator('#rest tbody tr')).to_have_count(1)
        page.locator('#rest .row-move').click()
        expect(page.locator('#music-total')).to_have_text('255')
        review_seconds = time.perf_counter() - started
        page.locator('#music .search').fill('Video 6399')
        expect(page.locator('#music tbody tr')).to_have_count(1)
        page.locator('#music .select-page').check()
        page.goto(self.url + '/download')
        page.locator('#output-dir').fill(str(self.root/'audio'))
        (self.root/'release').touch()
        expect(page.locator('#download-all')).to_be_enabled()
        page.locator('#download-all').click()
        expect(page.locator('#batch-summary')).to_contain_text('Có lỗi', timeout=20000)
        expect(page.locator('#batch-summary')).to_contain_text('255 video')
        self.stop_server()
        self.server = subprocess.Popen(self.server_command, stdout=self.log, stderr=self.log)
        for _ in range(60):
            try:
                urllib.request.urlopen(self.url, timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        page.reload()
        expect(page.locator('#batch-summary')).to_contain_text('Có lỗi')
        def api(path):
            response = page.request.get(self.url + path)
            self.assertEqual(response.status, 200, response.text())
            return response.json()
        self.assertEqual(api('/api/downloads/1')['total'], 255)
        repeat = api('/api/videos?group=music&search=Video%200001')
        self.assertEqual(repeat['items'][0]['watch_count'], 3)
        page.locator('#resume-download').click()
        expect(page.locator('#batch-summary')).to_contain_text('Hoàn tất', timeout=15000)
        page.goto(self.url + '/import')
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page).to_have_url(self.url + '/explore')
        self.assertEqual(api('/api/workflow')['active_import'], 1)
        expect(page.locator('#music-total')).to_have_text('255')
        expect(page.locator('#rest-total')).to_have_text('6145')
        page.goto(self.url + '/download')
        expect(page.locator('#download-all')).to_be_disabled()
        files = list((self.root/'audio').glob('*.webm'))
        self.assertEqual(len(files), 255)
        self.assertFalse(any('[00000000000]' in path.name for path in files))
        self.assertTrue(any('[00000006399]' in path.name for path in files))
        retained = {path.name: path.stat().st_mtime_ns for path in files[1:]}
        files[0].unlink()
        expect(page.locator('#download-preview')).to_contain_text('1 file cần tải', timeout=10000)
        page.locator('#download-all').click()
        expect(page.locator('#batch-summary')).to_contain_text('Lượt #2')
        expect(page.locator('#batch-summary')).to_contain_text('Hoàn tất', timeout=15000)
        status = api('/api/downloads/2')
        self.assertEqual(status['skipped'], 254)
        self.assertEqual(status['counts']['completed'], 1)
        self.assertEqual({name: (self.root/'audio'/name).stat().st_mtime_ns for name in retained}, retained)
        self.assertEqual(errors, [])
        report = {'unique_videos': 6400, 'watch_events': 6402, 'music_snapshot': 255,
                  'first_batch_error_count': 1, 'restart_preserved': True, 'reimport_reused': True,
                  'replacement_completed': 1, 'replacement_skipped': 254,
                  'import_review_seconds': round(review_seconds, 3), 'total_seconds': round(time.perf_counter()-started, 3),
                  'page_errors': errors, 'audio': 'synthetic fixture; not playable evidence'}
        output = Path('artifacts/acceptance-runs'); output.mkdir(parents=True, exist_ok=True)
        (output/'t11-browser.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))

    def stop_server(self):
        self.server.terminate()
        try: self.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.server.kill(); self.server.wait()

    def test_folder_review_transfer_reload_filter_and_page(self):
        page=self.page
        expect(page.get_by_role('heading',name='Import · Nhập lịch sử',exact=True)).to_be_visible()
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#music-total')).to_have_text('2')
        expect(page.locator('#rest-total')).to_have_text('52')
        page.locator('#rest-toggle').click()
        expect(page.locator('#rest tbody tr')).to_have_count(50)
        self.assertIsNone(page.evaluate('window.pwned'))
        expect(page.locator('#rest tbody tr').first.locator('.thumbnail')).to_have_text('♪')
        page.locator('#rest .select-page').check()
        expect(page.locator('#rest .bulk-move')).to_contain_text('50')
        page.locator('#rest .next').click()
        expect(page.locator('#rest tbody tr')).to_have_count(2)
        expect(page.locator('#rest .bulk-move')).to_be_disabled()
        page.locator('#rest .select-page').check()
        page.locator('#rest .bulk-move').click()
        expect(page.locator('#music-total')).to_have_text('4')
        expect(page.locator('#rest-total')).to_have_text('50')
        page.reload()
        expect(page.locator('#music-total')).to_have_text('4')
        page.locator('#music .search').fill('Video 053')
        expect(page.locator('#music tbody tr')).to_have_count(1)
        page.locator('#music .row-move').click()
        expect(page.locator('#music-total')).to_have_text('3')
        expect(page.locator('#rest-total')).to_have_text('51')
        expect(page.locator('#music .empty')).to_be_visible()
        page.locator('#rest .select-page').check()
        page.locator('#rest .search').fill('Video 010')
        expect(page.locator('#rest .bulk-move')).to_be_disabled()
        expect(page.locator('#rest tbody tr')).to_have_count(1)
        page.locator('#rest .search').fill('')
        expect(page.locator('#rest tbody tr')).to_have_count(50)
        page.locator('#music .search').fill('')
        expect(page.locator('#music tbody tr')).to_have_count(3)
        page.locator('h1').click()
        Path('artifacts/browser-runs').mkdir(parents=True,exist_ok=True)
        page.screenshot(path='artifacts/browser-runs/t07-ui.png',full_page=True)


    def test_drop_folder_via_chromium_and_import_error(self):
        page=self.page
        session=page.context.new_cdp_session(page)
        box=page.locator('#dropzone').bounding_box()
        data={'items':[], 'files':[str(self.takeout)], 'dragOperationsMask':1}
        for event in ('dragEnter','drop'):
            session.send('Input.dispatchDragEvent',{'type':event,'x':box['x']+40,'y':box['y']+40,'data':data})
        expect(page.locator('#music-total')).to_have_text('2')
        (self.takeout/'history'/'watch-history.json').write_text('{')
        page.goto(self.url + '/import')
        page.locator('#folder-input').set_input_files(self.takeout)
        expect(page.locator('#notice')).to_contain_text('JSON')
        page.goto(self.url + '/explore')
        expect(page.locator('#music-total')).to_have_text('2')

    def test_multiple_histories_require_selection(self):
        other=self.root/'Other'/'history'
        other.mkdir(parents=True)
        (other/'watch-history.json').write_text('[]')
        self.page.locator('#folder-input').set_input_files(self.root)
        expect(self.page.locator('#source-dialog')).to_be_visible()
        choices=self.page.locator('#history-source option').all_text_contents()
        selected=next(text for text in choices if 'Takeout/history/' in text)
        self.page.locator('#history-source').select_option(label=selected)
        self.page.locator('#import-source').click()
        expect(self.page.locator('#music-total')).to_have_text('2')
        expect(self.page.locator('#rest-total')).to_have_text('52')

    def test_large_history_and_narrow_layout(self):
        rows=[{'titleUrl':f'https://youtu.be/{i:011d}', 'title':f'Watched Video {i:04d}',
               'subtitles':[{'name':'Artist - Topic' if i < 255 else 'Other'}]} for i in range(7500)]
        (self.takeout/'history'/'watch-history.json').write_text(json.dumps(rows))
        errors=[]
        self.page.on('pageerror',lambda error:errors.append(str(error)))
        started=time.perf_counter()
        self.page.locator('#folder-input').set_input_files(self.takeout)
        expect(self.page.locator('#music-total')).to_have_text('255',timeout=15000)
        expect(self.page.locator('#rest-total')).to_have_text('7245')
        self.page.locator('#rest-toggle').click()
        expect(self.page.locator('#rest tbody tr')).to_have_count(50)
        self.page.locator('#rest .search').fill('Video 7499')
        expect(self.page.locator('#rest tbody tr')).to_have_count(1)
        self.page.locator('#rest .row-move').click()
        expect(self.page.locator('#music-total')).to_have_text('256')
        elapsed = time.perf_counter()-started
        timings = {}
        for endpoint in ('/api/explore/summary', '/api/videos?group=music&page=1&page_size=50', '/api/videos?group=rest&search=Video%207499'):
            begin = time.perf_counter()
            response = self.page.request.get(self.url + endpoint)
            self.assertEqual(response.status, 200)
            timings[endpoint] = round(time.perf_counter()-begin, 4)
        report = {'videos': 7500, 'import_filter_move_seconds': round(elapsed, 3), 'api_seconds': timings,
                  'browser': self.browser.version, 'platform': sys.platform, 'fixture': 'synthetic', 'page_errors': errors}
        output = Path('artifacts/acceptance-runs'); output.mkdir(parents=True, exist_ok=True)
        (output/'wft03-7500.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
        self.page.set_viewport_size({'width':390,'height':844})
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.assertEqual(errors,[])


if __name__=='__main__':
    unittest.main()
