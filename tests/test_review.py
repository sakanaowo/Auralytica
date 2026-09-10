import json
from pathlib import Path
import tempfile
import unittest

from auralytica import importer, review, storage


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/'db.sqlite3'
        self.db=storage.open_database(self.path)
        self.addCleanup(self.db.close)
        rows=[{'titleUrl':f'https://youtu.be/{vid}', 'title':title,
               'subtitles':[{'name':channel,'url':f'https://youtube.com/channel/{key}'}]}
              for vid,title,channel,key in [
                  ('aaaaaaaaaaa','Watched NHẠC 100%','Artist - Topic','one'),
                  ('aaaaaaaaaaa','Watched NHẠC 100%','Artist - Topic','one'),
                  ('bbbbbbbbbbb','Watched Beta','Other','two'),
                  ('ccccccccccc','Watched Cover','Other','two')]]
        (self.root/'watch-history.json').write_text(json.dumps(rows))
        importer.import_folder(self.db,self.root)

    def test_groups_counts_filters_and_stable_pages(self):
        result=review.list_videos(self.db,group='music',search='nhạc 100%')
        self.assertEqual(result['group_totals'],{'music':1,'rest':2})
        self.assertEqual(result['filtered_count'],1)
        self.assertEqual(result['items'][0]['watch_count'],2)
        self.assertEqual(result['items'][0]['url'],'https://www.youtube.com/watch?v=aaaaaaaaaaa')
        self.assertEqual(result['items'][0]['decision_source'],'automatic')
        first=review.list_videos(self.db,group='rest',page_size=1,sort='title')
        second=review.list_videos(self.db,group='rest',page_size=1,page=2,sort='title')
        self.assertEqual([first['items'][0]['id'],second['items'][0]['id']],['bbbbbbbbbbb','ccccccccccc'])
        filtered=review.list_videos(self.db,group='rest',channel='https://youtube.com/channel/two',reason='music_hint')
        self.assertEqual([r['id'] for r in filtered['items']],['ccccccccccc'])
        self.assertEqual(review.list_videos(self.db,group='rest',page=99)['items'],[])

    def test_bulk_move_persists_both_directions_and_keeps_file(self):
        audio=self.root/'audio.webm'
        audio.write_bytes(b'fixture')
        self.db.execute("INSERT INTO download_batches(id,output_dir,status) VALUES (1,?,'completed')",(str(self.root),))
        self.db.execute("INSERT INTO download_items(batch_id,video_id,status,file_path) VALUES(1,'bbbbbbbbbbb','completed',?)",(str(audio),))
        result=review.move_videos(self.db,['bbbbbbbbbbb','ccccccccccc','bbbbbbbbbbb'],'music')
        self.assertEqual(result['moved'],2)
        self.assertEqual(result['group_totals'],{'music':3,'rest':0})
        reopened=storage.open_database(self.path)
        self.addCleanup(reopened.close)
        row=next(r for r in review.list_videos(reopened,group='music')['items'] if r['id']=='bbbbbbbbbbb')
        self.assertEqual(row['decision_source'],'user')
        self.assertEqual(row['reason'],'manual')
        self.assertEqual(row['download_status'],'completed')
        review.move_videos(reopened,['bbbbbbbbbbb'],'rest')
        self.assertEqual(audio.read_bytes(),b'fixture')
        self.assertEqual(review.list_videos(reopened,group='rest')['filtered_count'],1)

    def test_invalid_bulk_move_is_atomic_and_cannot_move_outside_history(self):
        self.db.execute("INSERT INTO videos(id) VALUES('ddddddddddd')")
        for ids in (['bbbbbbbbbbb','missing0000'],['bbbbbbbbbbb','ddddddddddd'],[]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):
                review.move_videos(self.db,ids,'music')
            self.assertIsNone(storage.get_video(self.db,'bbbbbbbbbbb')['user_group'])

    def test_validation_and_missing_import(self):
        for kwargs in ({'group':'bad'},{'page':0},{'page_size':1001},{'sort':'id; DROP TABLE videos'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                review.list_videos(self.db,**kwargs)
        with self.assertRaises(ValueError):
            review.move_videos(self.db,['aaaaaaaaaaa'],'bad')
        self.db.execute("DELETE FROM settings WHERE key='active_import'")
        with self.assertRaises(ValueError):
            review.list_videos(self.db)

    def test_only_active_import_counts_are_used(self):
        (self.root/'watch-history.json').write_text(json.dumps([{'titleUrl':'https://youtu.be/bbbbbbbbbbb'}]))
        importer.import_folder(self.db,self.root)
        result=review.list_videos(self.db,group='rest')
        self.assertEqual(result['group_totals'],{'music':0,'rest':1})
        self.assertEqual(result['items'][0]['watch_count'],1)
