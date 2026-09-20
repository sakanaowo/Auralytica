import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from auralytica import storage, web


ORIGIN = 'http://127.0.0.1:8765'


class DedupWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'state.sqlite3'
        self.client = TestClient(web.create_app(self.database), base_url=ORIGIN)
        self.addCleanup(self.client.close)
        self.rows = [self.row('aaaaaaaaaaa', 'Shoujo A', 'Artist'),
                     self.row('bbbbbbbbbbb', '少女A', 'Artist')]
        self.upload(self.rows)
        for video_id in ('aaaaaaaaaaa', 'bbbbbbbbbbb'):
            self.post('/api/videos/move', {'video_ids': [video_id], 'to_group': 'music'})

    @staticmethod
    def row(video_id, title, channel):
        return {'titleUrl': f'https://youtu.be/{video_id}', 'title': f'Watched {title}',
                'subtitles': [{'name': channel}]}

    def upload(self, rows):
        response = self.client.post('/api/imports', headers={'Origin': ORIGIN}, files=[
            ('files', ('Takeout/history/watch-history.json', json.dumps(rows).encode(), 'application/json'))])
        self.assertEqual(response.status_code, 200, response.text)

    def post(self, path, payload=None):
        return self.client.post(path, headers={'Origin': ORIGIN}, json=payload or {})

    def test_alias_run_selection_revision_reload_and_new_member_default_keep(self):
        result = self.post('/api/dedup/aliases', {
            'video_ids': ['aaaaaaaaaaa', 'bbbbbbbbbbb'], 'artist_scope': 'Artist'})
        self.assertEqual(result.status_code, 200, result.text)
        run_id = result.json()['run']['run_id']
        groups = self.client.get(f'/api/dedup/runs/{run_id}/groups').json()
        self.assertEqual(groups['selection_revision'], 0)
        self.assertEqual([member['raw_title'] for member in groups['items'][0]['members']],
                         ['Shoujo A', '少女A'])

        changed = self.post('/api/dedup/selections', {
            'video_ids': ['bbbbbbbbbbb'], 'keep': False, 'expected_revision': 0})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['revision'], 1)
        again = self.client.get(f'/api/dedup/runs/{run_id}/groups').json()
        self.assertEqual({m['video_id']: m['keep'] for m in again['items'][0]['members']},
                         {'aaaaaaaaaaa': True, 'bbbbbbbbbbb': False})
        stale = self.post('/api/dedup/selections', {
            'video_ids': ['aaaaaaaaaaa'], 'keep': False, 'expected_revision': 0})
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'], 2)

        third = self.row('ccccccccccc', '少女A (Official Audio)', 'Artist')
        self.upload(self.rows + [third])
        self.post('/api/videos/move', {'video_ids': ['ccccccccccc'], 'to_group': 'music'})
        rerun = self.post('/api/dedup/runs').json()
        members = self.client.get(f"/api/dedup/runs/{rerun['run_id']}/groups").json()['items'][0]['members']
        states = {member['video_id']: member['keep'] for member in members}
        self.assertFalse(states['bbbbbbbbbbb'])
        self.assertTrue(states['ccccccccccc'])

    def test_reject_and_undo_group_without_changing_music_label(self):
        run = self.post('/api/dedup/aliases', {
            'video_ids': ['aaaaaaaaaaa', 'bbbbbbbbbbb']}).json()['run']
        group = self.client.get(f"/api/dedup/runs/{run['run_id']}/groups").json()['items'][0]
        rejected = self.post(f"/api/dedup/groups/{group['group_id']}/rejection",
                             {'rejected': True, 'expected_revision': 0})
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(self.post('/api/dedup/runs').json()['groups'], 0)
        restored = self.post(f"/api/dedup/groups/{group['group_id']}/rejection",
                             {'rejected': False, 'expected_revision': 1})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(self.post('/api/dedup/runs').json()['groups'], 1)
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'], 2)

    def test_batch_locks_selection_atomically(self):
        run = self.post('/api/dedup/aliases', {
            'video_ids': ['aaaaaaaaaaa', 'bbbbbbbbbbb']}).json()['run']
        with storage.open_database(self.database) as db:
            from auralytica.batches import create_batch
            create_batch(db, Path(self.temp.name) / 'audio')
        response = self.post('/api/dedup/selections', {
            'video_ids': ['aaaaaaaaaaa', 'bbbbbbbbbbb'], 'keep': False, 'expected_revision': 0})
        self.assertEqual(response.status_code, 409, response.text)
        members = self.client.get(f"/api/dedup/runs/{run['run_id']}/groups").json()['items'][0]['members']
        self.assertTrue(all(member['keep'] for member in members))

    def test_large_group_members_are_paginated_and_group_selection_is_complete(self):
        rows = [self.row(f'{index:011d}', 'Shared Song', 'Artist - Topic') for index in range(120)]
        self.upload(rows)
        run = self.post('/api/dedup/runs').json()
        page = self.client.get(f"/api/dedup/runs/{run['run_id']}/groups").json()
        group = page['items'][0]
        self.assertEqual(group['member_count'], 120)
        self.assertEqual(len(group['members']), 50)
        last = self.client.get(f"/api/dedup/groups/{group['group_id']}/members",
                               params={'page': 3, 'page_size': 50}).json()
        self.assertEqual(len(last['items']), 20)
        changed = self.post(f"/api/dedup/groups/{group['group_id']}/selection",
                            {'keep': False, 'expected_revision': 0})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['updated'], 120)
        first = self.client.get(f"/api/dedup/groups/{group['group_id']}/members").json()
        self.assertTrue(all(not member['keep'] for member in first['items']))


if __name__ == '__main__':
    unittest.main()
