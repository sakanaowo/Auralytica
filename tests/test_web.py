import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from auralytica import storage, web
from auralytica.batches import create_batch, pause_batch


ORIGIN='http://127.0.0.1:8765'
HISTORY=json.dumps([{'titleUrl':'https://youtu.be/abcdefghijk',
                     'title':'Watched <script>alert(1)</script>',
                     'subtitles':[{'name':'Artist - Topic'}]}]).encode()


class WebTests(unittest.TestCase):
    def test_health_identifies_application_and_database_without_exposing_path(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['app'], response.json()['api']), ('auralytica', 1))
        self.assertEqual(len(response.json()['database_id']), 16)
        self.assertNotIn(str(self.database), response.text)

    def test_root_serves_local_ui_assets(self):
        response=self.client.get('/')
        self.assertIn('text/html',response.headers['content-type'])
        self.assertIn('Đã nhận dạng là nhạc',response.text)
        for path in ('/static/app.js','/static/style.css'):
            self.assertEqual(self.client.get(path).status_code,200)

    def test_explore_summary_uses_active_music_and_personal_watch_events(self):
        a = {'titleUrl': 'https://youtu.be/aaaaaaaaaaa', 'title': 'Watched Piano cover',
             'subtitles': [{'name': 'Artist - Topic'}], 'time': '2026-09-01T23:30:00Z'}
        b = {'titleUrl': 'https://youtu.be/bbbbbbbbbbb', 'title': 'Watched Song',
             'subtitles': [{'name': 'Other'}], 'time': '2026-09-02T00:30:00Z'}
        rest = {'titleUrl': 'https://youtu.be/ccccccccccc', 'title': 'Watched Podcast'}
        self.upload(json.dumps([a, dict(a, time='2026-09-02T00:30:00Z'),
                                dict(a, time='invalid'), b, rest]).encode())
        self.client.post('/api/videos/move', headers={'Origin': ORIGIN},
                         json={'video_ids': ['bbbbbbbbbbb'], 'to_group': 'music'})
        with storage.open_database(self.database) as db:
            db.execute("UPDATE videos SET metadata_json=? WHERE id='aaaaaaaaaaa'",
                       (json.dumps({'applied_music_evidence': {'metadata_exact': True}}),))
        response = self.client.get('/api/explore/summary')
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['scope'], 'active_import_music')
        self.assertEqual(data['videos'], 2)
        self.assertEqual(data['watch_events'], 4)
        self.assertEqual(data['watch_days_utc'], 2)
        self.assertEqual(data['undated_events'], 1)
        self.assertEqual(data['decisions'], {'user': 1, 'automatic': 1})
        self.assertEqual(data['repeat_distribution'], {'1': 1, '2': 0, '3–9': 1, '10+': 0})
        self.assertEqual(data['day_distribution'], {'0': 0, '1': 1, '2': 1, '3+': 0})
        self.assertEqual(data['title_signals'], {'music_terms': 1, 'talk_terms': 0})
        self.assertEqual(data['metadata'], {'available': 1, 'missing': 1, 'applied': 1,
                                            'cached': 0, 'fresh': 0, 'stale': 0})
        self.assertEqual(data['channels'][0]['watch_events'], 3)
        self.assertEqual(data['import_statistics']['video_events'], 5)
        self.assertEqual(self.client.get('/api/videos', params={'channel': 'Other'}).json()['filtered_count'], 1)
        self.upload(json.dumps([b]).encode())
        updated = self.client.get('/api/explore/summary').json()
        self.assertEqual(updated['videos'], 1)
        self.assertEqual(updated['watch_events'], 1)
        self.assertEqual(updated['decisions'], {'user': 1, 'automatic': 0})
        self.client.post('/api/videos/move', headers={'Origin': ORIGIN},
                         json={'video_ids': ['bbbbbbbbbbb'], 'to_group': 'rest'})
        empty = self.client.get('/api/explore/summary').json()
        self.assertEqual(empty['videos'], 0)
        self.assertEqual(empty['watch_events'], 0)
        self.assertEqual(empty['channels'], [])

    def test_workflow_routes_and_root_choose_active_import(self):
        self.assertEqual(self.client.get('/', follow_redirects=False).headers.get('location'), '/import')
        for route in ('import', 'explore', 'deduplicate', 'download'):
            response = self.client.get('/' + route)
            self.assertEqual(response.status_code, 200)
            self.assertIn('workflow-nav', response.text)
        self.upload()
        self.assertEqual(self.client.get('/', follow_redirects=False).headers.get('location'), '/explore')

    def test_workflow_reports_counts_locks_and_dedup_readiness(self):
        response = self.client.get('/api/workflow')
        self.assertEqual(response.status_code, 200)
        empty = response.json()
        self.assertIsNone(empty['active_import'])
        self.assertEqual(empty['steps']['explore'], 'needs_import')
        self.upload()
        ready = self.client.get('/api/workflow').json()
        self.assertEqual(ready['counts'], {'music': 1, 'rest': 0})
        self.assertEqual(ready['steps']['deduplicate'], 'ready')
        self.assertEqual(ready['steps']['download'], 'ready')
        self.assertNotEqual(empty['revision'], ready['revision'])
        self.assertEqual(ready, self.client.get('/api/workflow').json())
        with storage.open_database(self.database) as db:
            batch = create_batch(db, self.database.parent / 'audio')
        self.assertTrue(self.client.get('/api/workflow').json()['batch_locked'])
        with storage.open_database(self.database) as db:
            pause_batch(db, batch['batch_id'])
        self.client.post('/api/videos/move', headers={'Origin': ORIGIN},
                         json={'video_ids': ['abcdefghijk'], 'to_group': 'rest'})
        remaining = self.client.get('/api/workflow').json()
        self.assertFalse(remaining['batch_locked'])
        self.assertEqual(remaining['steps']['download'], 'no_music')
        self.assertEqual(len(self.client.get('/api/downloads').json()['batches']), 1)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'library.sqlite3'
        self.client=TestClient(web.create_app(self.database),base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def upload(self, content=HISTORY, filename='Takeout/history/watch-history.json'):
        return self.client.post('/api/imports',headers={'Origin':ORIGIN},
                                files=[('files',(filename,content,'application/json'))])

    def test_upload_list_and_move_share_persisted_database(self):
        response=self.upload()
        self.assertEqual(response.status_code,200,response.text)
        result=self.client.get('/api/videos?group=music')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['filtered_count'],1)
        self.assertEqual(result.headers['content-type'],'application/json')
        self.assertEqual(result.json()['items'][0]['title'],'<script>alert(1)</script>')
        moved=self.client.post('/api/videos/move',headers={'Origin':ORIGIN},
                               json={'video_ids':['abcdefghijk'],'to_group':'rest'})
        self.assertEqual(moved.status_code,200,moved.text)
        rest = self.client.get('/api/videos?group=rest')
        self.assertEqual(rest.status_code, 200, rest.text)
        self.assertEqual(rest.json()['items'][0]['decision_source'], 'user')
        db=storage.open_database(self.database)
        try:
            storage.set_video_group(db,'abcdefghijk','music')
        finally:
            db.close()
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'],1)

    def test_untrusted_host_origin_and_missing_origin_cannot_mutate(self):
        for headers in ({'Origin':'https://evil.example'},{}, {'Origin':ORIGIN,'Host':'evil.example:8765'},
                        {'Origin':'http://127.0.0.1:9999'},{'Origin':'null'}):
            with self.subTest(headers=headers):
                response=self.client.post('/api/imports',headers=headers,
                    files=[('files',('watch-history.json',HISTORY))])
                self.assertIn(response.status_code,(400,403))
        self.assertFalse(self.database.exists())
        self.assertEqual(self.client.get('/api/videos',headers={'Host':'evil.example'}).status_code,400)

    def test_invalid_import_preserves_existing_review_and_reports_ambiguity(self):
        self.assertEqual(self.upload().status_code,200)
        for content in (b'{',b'{}'):
            self.assertEqual(self.upload(content).status_code,400)
        duplicate=self.client.post('/api/imports',headers={'Origin':ORIGIN},files=[
            ('files',('a/watch-history.json',HISTORY)),('files',('b/watch-history.json',HISTORY))])
        self.assertEqual(duplicate.status_code,400)
        self.assertIn('chọn',duplicate.json()['detail'].lower())
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'],1)

    def test_library_upload_and_unrelated_files(self):
        response=self.client.post('/api/imports',headers={'Origin':ORIGIN},files=[
            ('files',('history/watch-history.json',HISTORY)),
            ('files',('music/music library songs.csv',b'Video ID\nabcdefghijk\n'))])
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['statistics']['library_matches'],1)
        for filename in ('../watch-history.json','/watch-history.json','watch-history.html','passwords.csv'):
            with self.subTest(filename=filename):
                self.assertEqual(self.upload(filename=filename).status_code,400)

    def test_request_limits_apply_to_content_length_and_chunked_bodies(self):
        client=TestClient(web.create_app(self.database,max_body_bytes=64),base_url=ORIGIN)
        with client:
            response=client.post('/api/imports',headers={'Origin':ORIGIN},content=b'x'*65)
            self.assertEqual(response.status_code,413)
            response=client.post('/api/imports',headers={'Origin':ORIGIN},content=iter([b'x'*32,b'y'*33]))
            self.assertEqual(response.status_code,413)
        self.assertFalse(self.database.exists())

    def test_query_and_move_validation(self):
        self.assertEqual(self.upload().status_code,200)
        for query in ('group=invalid','page=0','page_size=1001','sort=bad'):
            self.assertEqual(self.client.get('/api/videos?'+query).status_code,422)
        for payload in ({'video_ids':[],'to_group':'music'}, {'video_ids':['bad'],'to_group':'music'},
                        {'video_ids':['abcdefghijk'],'to_group':'invalid'}):
            self.assertEqual(self.client.post('/api/videos/move',headers={'Origin':ORIGIN},json=payload).status_code,422)
        missing=self.client.post('/api/videos/move',headers={'Origin':ORIGIN},
                                  json={'video_ids':['missing0000'],'to_group':'music'})
        self.assertEqual(missing.status_code,400)
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'],1)

    def test_queued_batch_returns_conflict_on_import_and_move_but_allows_browsing(self):
        self.assertEqual(self.upload().status_code,200)
        db=storage.open_database(self.database)
        try:
            batch=create_batch(db,self.database.parent/'audio')
            self.assertEqual(self.upload().status_code,409)
            response=self.client.post('/api/videos/move',headers={'Origin':ORIGIN},
                json={'video_ids':['abcdefghijk'],'to_group':'rest'})
            self.assertEqual(response.status_code,409)
            self.assertEqual(self.client.get('/api/videos?group=music').status_code,200)
            pause_batch(db,batch['batch_id'])
            self.assertEqual(self.upload().status_code,200)
        finally:
            db.close()
