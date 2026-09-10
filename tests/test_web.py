import json
from pathlib import Path
import subprocess
import sys
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
    def test_root_serves_local_ui_assets(self):
        response=self.client.get('/')
        self.assertIn('text/html',response.headers['content-type'])
        self.assertIn('Đã nhận dạng là nhạc',response.text)
        for path in ('/static/app.js','/static/style.css'):
            self.assertEqual(self.client.get(path).status_code,200)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'library.sqlite3'
        self.client=TestClient(web.create_app(self.database),base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def upload(self, content=HISTORY, filename='Takeout/history/watch-history.json'):
        return self.client.post('/api/imports',headers={'Origin':ORIGIN},
                                files=[('files',(filename,content,'application/json'))])

    def test_upload_list_and_move_share_cli_database(self):
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
        cli=subprocess.run([str(Path(sys.executable).parent/'auralytica'),'list','--group','rest',
                            '--database',str(self.database)],capture_output=True,text=True,timeout=10)
        self.assertEqual(cli.returncode,0,cli.stderr)
        self.assertEqual(json.loads(cli.stdout)['items'][0]['decision_source'],'user')
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
