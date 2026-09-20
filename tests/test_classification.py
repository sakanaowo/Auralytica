import json
from pathlib import Path
import tempfile
import unittest

from auralytica import classification, importer, storage


class ClassificationTests(unittest.TestCase):
    def test_decisions_are_append_only_and_manual_correction_links_to_decision(self):
        from auralytica.review import move_videos
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'watch-history.json').write_text(json.dumps([
                {'titleUrl':'https://youtu.be/abcdefghijk','title':'Song'}]))
            db = storage.open_database(root/'db.sqlite3')
            self.addCleanup(db.close)
            importer.import_folder(db, root)
            first = db.execute("SELECT * FROM audit_events WHERE kind='classification_decided'").fetchone()
            self.assertIsNotNone(first, 'Import must preserve its original decision in the audit')
            move_videos(db, ['abcdefghijk'], 'music')
            correction = db.execute("SELECT payload_json FROM audit_events WHERE kind='review_changed'").fetchone()
            payload = json.loads(correction[0])
            self.assertEqual(payload['decision_id'], first['id'])
            self.assertEqual((payload['before_group'], payload['after_group']), ('rest','music'))
            run = classification.classify_active(db)
            self.assertEqual(run['counts'], {'music':1,'rest':0})
            decisions = db.execute("SELECT * FROM audit_events WHERE kind='classification_decided' ORDER BY id").fetchall()
            self.assertEqual(len(decisions), 2)
            self.assertEqual(decisions[0]['payload_json'], first['payload_json'])
            latest = json.loads(decisions[1]['payload_json'])
            self.assertEqual(latest['features']['watch_count'], 1)
            self.assertEqual(latest['effective_group'], 'music')
            self.assertEqual(latest['user_group'], 'music')

    def test_evidence_rules_and_conflicts(self):
        cases = [
            ({'channel_name':'Artist - Topic'}, 'music', 'topic_channel'),
            ({'metadata':{'music_library':True}}, 'music', 'music_library'),
            ({'channel_name':'Topic discussions'}, 'rest', 'unknown'),
            ({'title':'Podcast episode', 'watch_count':40}, 'rest', 'talk_context'),
            ({'title':'AMV OST remix', 'channel_name':'ArtistVEVO', 'watch_count':40}, 'rest', 'music_hint'),
            ({'title':'#shorts #fyp', 'metadata':{'duration':15}}, 'rest', 'unknown'),
            ({'title':'Song', 'metadata':{'category':'Entertainment','music_library':True}}, 'music', 'music_library'),
            ({'channel_name':'Artist - Topic','metadata':{'takeout_shorts_url':True}}, 'rest', 'shorts_url'),
            ({'channel_name':'Artist - Topic','title':'Podcast interview'}, 'rest', 'conflicting_evidence'),
            ({'channel_name':'Artist - Topic','channel_decision':{'group_name':'rest','reason':'podcast','source':'user'}}, 'rest', 'channel_decision'),
            ({'title':'未知の歌'}, 'rest', 'unknown'),
        ]
        for values, group, reason in cases:
            with self.subTest(values=values):
                result = classification.suggest(**values)
                self.assertEqual((result['group'], result['reason']), (group, reason))
                self.assertTrue(all('source' in e and 'code' in e for e in result['evidence']))

    def test_import_classifies_active_history_and_preserves_manual_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            history=root/'watch-history.json'
            history.write_text(json.dumps([{'title':'Watched Song', 'titleUrl':'https://youtube.com/watch?v=abcdefghijk',
                'subtitles':[{'name':'Artist - Topic','url':'https://youtube.com/channel/artist'}]}]))
            db=storage.open_database(root/'state.sqlite3')
            try:
                importer.import_folder(db,root)
                self.assertEqual(storage.get_video(db,'abcdefghijk')['effective_group'],'music')
                storage.set_video_group(db,'abcdefghijk','rest')
                importer.import_folder(db,root)
                self.assertEqual(storage.get_video(db,'abcdefghijk')['effective_group'],'rest')
                self.assertEqual(storage.get_video(db,'abcdefghijk')['auto_group'],'music')
                db.execute("INSERT INTO channel_decisions (channel_key,group_name,reason) VALUES ('https://youtube.com/channel/artist','rest','podcast')")
                storage.set_video_group(db,'abcdefghijk','music')
                classification.classify_active(db)
                self.assertEqual(storage.get_video(db,'abcdefghijk')['auto_reason'],'channel_decision')
                self.assertEqual(storage.get_video(db,'abcdefghijk')['effective_group'],'music')
                db.execute("INSERT INTO videos (id,auto_reason) VALUES ('outside0001','untouched')")
                classification.classify_active(db)
                self.assertEqual(storage.get_video(db,'outside0001')['auto_reason'],'untouched')
            finally:
                db.close()

    def test_shorts_url_is_preserved_even_when_video_also_has_watch_url(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'watch-history.json').write_text(json.dumps([
                {'titleUrl':'https://youtube.com/shorts/abcdefghijk','title':'Song'},
                {'titleUrl':'https://youtube.com/watch?v=abcdefghijk','subtitles':[{'name':'Artist - Topic'}]}
            ]))
            db=storage.open_database(root/'state.sqlite3')
            try:
                importer.import_folder(db,root)
                row=storage.get_video(db,'abcdefghijk')
                self.assertEqual(row['auto_reason'],'shorts_url')
                self.assertTrue(json.loads(row['metadata_json'])['takeout_shorts_url'])
            finally:
                db.close()
