import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from auralytica import importer, storage


class Provider:
    key = 'fixture-v1:en:VN'
    last_http_status = 200

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def fetch(self, video_id):
        self.calls.append(video_id)
        response = self.responses.get(video_id, {
            'videoDetails': {'videoId': video_id, 'musicVideoType':'MUSIC_VIDEO_TYPE_UGC'},
            'microformat': {'microformatDataRenderer': {'category':'Gaming'}},
        })
        if isinstance(response, BaseException):
            raise response
        return response


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = storage.open_database(self.root/'db.sqlite3')
        self.addCleanup(self.db.close)
        (self.root/'watch-history.json').write_text(json.dumps([
            {'titleUrl':'https://youtu.be/aaaaaaaaaaa','title':'Unknown'},
            {'titleUrl':'https://youtu.be/bbbbbbbbbbb','title':'Podcast'}]))
        importer.import_folder(self.db, self.root)
        self.assertIsNotNone(importlib.util.find_spec('auralytica.metadata'),
                             'The planned metadata collector is not implemented')
        self.m = importlib.import_module('auralytica.metadata')

    def create(self, provider, **kwargs):
        return self.m.create_run(self.db, provider_key=provider.key, **kwargs)

    def events(self, kind):
        return [json.loads(r[0]) for r in self.db.execute(
            'SELECT payload_json FROM audit_events WHERE kind=? ORDER BY id', (kind,))]

    def test_collect_exact_ids_cache_reuse_and_manual_groups_unchanged(self):
        storage.set_video_group(self.db, 'aaaaaaaaaaa', 'music')
        before = [tuple(r) for r in self.db.execute('SELECT * FROM videos ORDER BY id')]
        p = Provider()
        first = self.create(p)
        result = self.m.collect_run(self.db, first, p, sleep=lambda _:None)
        self.assertEqual(result['counts'], {'done':2})
        second = self.create(p)
        self.m.collect_run(self.db, second, p, sleep=lambda _:None)
        self.assertEqual(p.calls, ['aaaaaaaaaaa','bbbbbbbbbbb'])
        self.assertEqual(len(self.events('metadata_cache_hit')), 2)
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM videos ORDER BY id')], before)
        self.assertEqual(self.events('metadata_observed')[0]['evidence']['category']['value'], 'Gaming')
        self.assertEqual(self.events('metadata_observed')[0]['evidence']['music_video_type']['source'], 'get_song.videoDetails.musicVideoType')

    def test_mismatch_missing_and_errors_do_not_cache_or_become_non_music(self):
        for response, status in [
            ({'videoDetails':{'videoId':'ccccccccccc'}}, 'id_mismatch'),
            ({'playabilityStatus':{'status':'LOGIN_REQUIRED'}}, 'missing'),
            (TimeoutError('Authorization: SECRET'), 'error'),
        ]:
            with self.subTest(status=status):
                p = Provider({'aaaaaaaaaaa':response})
                run = self.create(p, video_ids=['aaaaaaaaaaa'], max_attempts=1)
                result = self.m.collect_run(self.db, run, p, sleep=lambda _:None)
                self.assertEqual(result['status'], 'partial')
                self.assertEqual(self.events('metadata_observed')[-1]['status'], status)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM metadata_cache').fetchone()[0], 0)
        all_logs = '\n'.join(r[0] for r in self.db.execute('SELECT payload_json FROM audit_events'))
        self.assertNotIn('SECRET', all_logs)
        self.assertEqual(storage.get_video(self.db, 'aaaaaaaaaaa')['auto_reason'], 'unknown')

    def test_missing_type_and_unplayable_are_observations_not_negative_labels(self):
        p = Provider({'aaaaaaaaaaa':{'videoDetails':{'videoId':'aaaaaaaaaaa'},
                                    'playabilityStatus':{'status':'UNPLAYABLE'},
                                    'streamingData':{'url':'SECRET'},'playbackTracking':{'token':'SECRET'}}})
        run = self.create(p, video_ids=['aaaaaaaaaaa'])
        self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        observation = self.events('metadata_observed')[-1]
        self.assertEqual(observation['status'], 'observed')
        self.assertIn('music_video_type', observation['missing_fields'])
        self.assertEqual(observation['evidence']['playability']['value'], 'UNPLAYABLE')
        self.assertNotIn('SECRET', json.dumps(observation))

    def test_interrupt_resume_and_changed_active_import_keep_original_snapshot(self):
        p = Provider({'bbbbbbbbbbb':KeyboardInterrupt()})
        run = self.create(p)
        with self.assertRaises(KeyboardInterrupt):
            self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        self.assertEqual(self.m.get_run(self.db, run)['status'], 'paused')
        (self.root/'watch-history.json').write_text(json.dumps([{'titleUrl':'https://youtu.be/ccccccccccc'}]))
        importer.import_folder(self.db, self.root)
        p.responses.clear()
        self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        self.assertEqual(p.calls, ['aaaaaaaaaaa','bbbbbbbbbbb','bbbbbbbbbbb'])
        self.assertEqual(self.m.get_run(self.db, run)['counts'], {'done':2})

    def test_retry_is_bounded_and_logs_each_attempt(self):
        p = Provider({'aaaaaaaaaaa':TimeoutError('sensitive URL')})
        run = self.create(p, video_ids=['aaaaaaaaaaa'], max_attempts=2)
        self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        self.assertEqual(len(p.calls), 2)
        self.assertEqual([e['attempt'] for e in self.events('metadata_observed')], [1,2])
        p.responses.clear()
        self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        self.assertEqual(self.m.get_run(self.db, run)['status'], 'completed')
        self.assertEqual(self.events('metadata_observed')[-1]['attempt'], 3)

    def test_cache_ttl_refresh_and_provider_version_are_respected(self):
        p = Provider()
        for options in ({}, {'refresh':True}, {}, {}):
            if len(p.calls) == 2:
                self.db.execute('UPDATE metadata_cache SET fetched_at=0')
            run = self.create(p, video_ids=['aaaaaaaaaaa'], **options)
            self.m.collect_run(self.db, run, p, sleep=lambda _:None)
            if len(p.calls) == 3:
                p.key = 'fixture-v2:en:VN'
        self.assertEqual(len(p.calls), 4)

    def test_invalid_selection_and_provider_mismatch_fail_before_network(self):
        p = Provider()
        for kwargs in ({'video_ids':['ccccccccccc']}, {'limit':0}, {'max_attempts':0}, {'cache_ttl':-1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.create(p, **kwargs)
        run = self.create(p, video_ids=['aaaaaaaaaaa'])
        p.key = 'different-version'
        with self.assertRaises(ValueError):
            self.m.collect_run(self.db, run, p)
        self.assertEqual(p.calls, [])

    def test_process_lock_prevents_double_collection_and_recovers_after_kill(self):
        import select
        import subprocess
        import sys
        p = Provider()
        run = self.create(p, video_ids=['aaaaaaaaaaa'])
        script = '''
import sys,time
from auralytica.storage import open_database
from auralytica.metadata import collector_lock
db=open_database(sys.argv[1])
with collector_lock(db):
    db.execute("UPDATE audit_runs SET status='running' WHERE id=?",(sys.argv[2],))
    print('locked',flush=True)
    time.sleep(30)
'''
        child = subprocess.Popen([sys.executable,'-c',script,str(self.root/'db.sqlite3'),run],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 5)[0])
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(ValueError, 'collector'):
                self.m.collect_run(self.db, run, p, sleep=lambda _:None)
            self.assertEqual(p.calls, [])
        finally:
            child.kill()
            child.communicate(timeout=5)
        self.assertEqual(self.m.collect_run(self.db, run, p, sleep=lambda _:None)['status'], 'completed')

    def test_invalid_override_and_review_audit_roll_back_together(self):
        from auralytica.review import move_videos
        before = self.db.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
        with self.assertRaises(ValueError):
            move_videos(self.db, ['aaaaaaaaaaa','ccccccccccc'], 'music')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0], before)
        self.assertIsNone(storage.get_video(self.db, 'aaaaaaaaaaa')['user_group'])

    def test_unknown_type_and_malformed_nested_fields_keep_evidence_without_crashing(self):
        p = Provider({'aaaaaaaaaaa':{'videoDetails':{'videoId':'aaaaaaaaaaa','musicVideoType':'MUSIC_VIDEO_TYPE_FUTURE'},
                                    'microformat':{'microformatDataRenderer':[]}, 'playabilityStatus':None}})
        run = self.create(p, video_ids=['aaaaaaaaaaa'])
        self.m.collect_run(self.db, run, p, sleep=lambda _:None)
        value = self.events('metadata_observed')[-1]
        self.assertEqual(value['evidence']['music_video_type']['value'], 'MUSIC_VIDEO_TYPE_FUTURE')
        self.assertIn('category',value['missing_fields'])
        self.assertEqual(storage.get_video(self.db,'aaaaaaaaaaa')['auto_group'], 'rest')
