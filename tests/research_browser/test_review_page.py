"""Offline Chromium checks for the research label/export workflow."""
import json
from contextlib import closing
from pathlib import Path
import tempfile
import unittest

import pandas as pd
from playwright.sync_api import sync_playwright, expect
from notebooks import residual_study


class ReviewPageTests(unittest.TestCase):
    def test_labels_notes_reload_and_exports_round_trip_without_network(self):
        self.assertTrue(callable(getattr(residual_study, 'render_review', None)),
                        'Research review needs editable labels and CSV export')
        base = pd.DataFrame([
            dict(video_id='test0000001', title='</script><img src=x onerror="window.pwned=1">',
                 channel_name='Kênh thử', source_hash='snapshot', manual_label='', label_source='', notes=''),
            dict(video_id='test0000002', title='Known song', channel_name='Artist', source_hash='snapshot',
                 manual_label='music', label_source='user_confirmed_before_pilot', notes='keep'),
        ])
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw, closing(pw.chromium.launch()) as browser:
            path = Path(tmp) / 'review.html'
            path.write_text(residual_study.render_review(base, priority_count=1))
            page = browser.new_page(accept_downloads=True)
            requests, errors = [], []
            page.on('request', lambda r: requests.append(r.url) if r.url.startswith('http') else None)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(path.as_uri())
            expect(page.locator('tbody tr')).to_have_count(2)
            self.assertEqual(page.locator('tbody tr').first.locator('.title').inner_text(), base.iloc[0].title)
            self.assertIsNone(page.evaluate('window.pwned'))
            expect(page.locator('#export-csv')).to_be_disabled()
            label = page.locator('select').first
            label.select_option('music')
            label.select_option('non_music')
            note = 'Có lời nói, "hướng dẫn"\nkiểm tra lại'
            page.locator('textarea').first.fill(note)
            page.reload()
            expect(page.locator('select').first).to_have_value('non_music')
            expect(page.locator('textarea').first).to_have_value(note)
            with page.expect_download() as download:
                page.locator('#export-csv').click()
            reviewed = pd.read_csv(download.value.path(), keep_default_na=False)
            self.assertEqual(reviewed.video_id.tolist(), ['test0000001'])
            merged = residual_study.merge_labels(base, reviewed)
            self.assertEqual(merged.manual_label.tolist(), ['non_music', 'music'])
            self.assertEqual(merged.notes.tolist(), [note, 'keep'])
            with page.expect_download() as download:
                page.locator('#export-audit').click()
            audit = [json.loads(line) for line in Path(download.value.path()).read_text().splitlines()]
            self.assertEqual(len(audit), 3)
            self.assertEqual(audit[0]['before']['manual_label'], '')
            self.assertEqual(audit[1]['after']['manual_label'], 'non_music')
            self.assertEqual(audit[2]['after']['notes'], note)
            self.assertTrue(all(e['source_hash'] == 'snapshot' and e['at'] for e in audit))
            self.assertEqual(requests, [])
            self.assertEqual(errors, [])
            # A different initial review must not inherit stale drafts on the same origin.
            base.loc[0, 'notes'] = 'new snapshot of review'
            path.write_text(residual_study.render_review(base, priority_count=1))
            page.reload()
            expect(page.locator('select').first).to_have_value('')
            expect(page.locator('textarea').first).to_have_value('new snapshot of review')

    def test_storage_unavailable_still_allows_export_on_mobile(self):
        base = pd.DataFrame([dict(video_id='test0000001', title='Song', channel_name='Artist',
                                  source_hash='snapshot', manual_label='', label_source='', notes='')])
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw, closing(pw.chromium.launch()) as browser:
            path = Path(tmp) / 'review.html'
            path.write_text(residual_study.render_review(base))
            page = browser.new_page(viewport={'width':390, 'height':844}, accept_downloads=True)
            page.add_init_script("Storage.prototype.getItem=Storage.prototype.setItem=()=>{throw Error('Storage denied')}")
            page.goto(path.as_uri())
            expect(page.locator('#storage-status')).to_contain_text('Không lưu được')
            page.locator('select').select_option('unavailable')
            page.locator('textarea').fill('Không xem được')
            with page.expect_download() as download:
                page.locator('#export-csv').click()
            reviewed = pd.read_csv(download.value.path(), keep_default_na=False)
            self.assertEqual(reviewed.manual_label.tolist(), ['unavailable'])
            self.assertEqual(reviewed.notes.tolist(), ['Không xem được'])
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
