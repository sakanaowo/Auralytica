import csv
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from auralytica.storage import open_database
from auralytica.metadata import normalize


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('auralytica.classification_preview'), 'Offline classification preview is missing')
        from auralytica.classification_preview import build_preview
        self.preview = build_preview
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'db.sqlite3';self.db=open_database(self.path);self.addCleanup(self.db.close)
        self.db.execute("INSERT INTO imports(id,source_hash,source_name) VALUES(1,'hash','history')")
        self.db.execute("INSERT INTO settings VALUES('active_import','1')")
        for i,title in enumerate(['Unknown','Song','Piano Tutorial cover','Lyrics','Podcast','Song'],1):
            vid=f'{i:011d}'
            self.db.execute('INSERT INTO videos(id,title,user_group) VALUES(?,?,?)',(vid,title,'rest' if i==2 else None))
            for day in range(1,4):
                self.db.execute('INSERT INTO watch_events VALUES(?,?,?,?)',(1,i*10+day,vid,f'2026-09-0{day}T00:00:00Z'))
        self.labels=self.root/'labels.csv'
        self.labels.write_text('video_id,source_hash,manual_label,notes\n00000000001,hash,music,confirmed\n00000000002,hash,music,conflict\n')
        self.log=self.root/'log.jsonl'
        records=[{'kind':'run_manifest','run':{'id':'run','source_hash':'hash'}}]
        for i,typ in [(3,'MUSIC_VIDEO_TYPE_UGC'),(4,'MUSIC_VIDEO_TYPE_OMV'),(5,'MUSIC_VIDEO_TYPE_OMV'),(6,'MUSIC_VIDEO_TYPE_UGC')]:
            vid=f'{i:011d}';payload=normalize(vid,{'videoDetails':{'videoId':vid,'musicVideoType':typ}})
            payload['fetched_at']=1000
            records.append(dict(kind='metadata_observed',run_id='run',id=i,video_id=vid,payload=payload))
        self.log.write_text('\n'.join(json.dumps(r) for r in records))

    def test_labels_metadata_guards_and_override_without_mutation(self):
        before=list(self.db.iterdump())
        out=self.preview(self.db,self.labels,self.log)
        rows={r['video_id']:r for r in out['items']}
        self.assertEqual([r['proposed_group'] for r in out['items']],['music','rest','rest','music','rest','music'])
        self.assertTrue(rows['00000000002']['conflict'])
        self.assertEqual(rows['00000000003']['reason'],'ambiguous_tutorial')
        self.assertEqual(rows['00000000006']['reason'],'ytmusic_ugc_recurrence')
        self.assertEqual(rows['00000000004']['evidence']['observation_id'],4)
        self.assertEqual(before,list(self.db.iterdump()))

    def test_invalid_labels_or_snapshot_fail_without_partial_output(self):
        for content in ['00000000001,wrong,music', '99999999999,hash,music',
                        '00000000001,hash,yes','00000000001,hash,music\n00000000001,hash,non_music']:
            self.labels.write_text('video_id,source_hash,manual_label\n'+content+'\n')
            with self.assertRaises(ValueError):self.preview(self.db,self.labels,self.log)

    def test_missing_or_mismatched_metadata_never_promotes(self):
        records=[json.loads(l) for l in self.log.read_text().splitlines()]
        for r in records[1:]:r['payload']['returned_id']='xxxxxxxxxxx'
        self.log.write_text('\n'.join(json.dumps(r) for r in records))
        result=self.preview(self.db,self.labels,self.log)
        self.assertEqual(result['proposed_totals']['music'],1)
        records[0]['run']['source_hash']='wrong'
        self.log.write_text('\n'.join(json.dumps(r) for r in records))
        with self.assertRaises(ValueError):self.preview(self.db,self.labels,self.log)

    def test_repeat_is_distinct_days_and_unresolved_review_blocks_promotion(self):
        self.db.execute("UPDATE watch_events SET watched_at='2026-09-01T00:00:00Z' WHERE video_id='00000000006'")
        with self.labels.open('a') as f:f.write('00000000004,hash,uncertain,need review\n')
        out=self.preview(self.db,self.labels,self.log)
        rows={r['video_id']:r for r in out['items']}
        self.assertEqual(rows['00000000006']['watch_count'],3)
        self.assertEqual(rows['00000000006']['watch_days'],1)
        self.assertEqual(rows['00000000006']['proposed_group'],'rest')
        self.assertEqual(rows['00000000004']['reason'],'unresolved_review')
        self.assertEqual(rows['00000000004']['proposed_group'],'rest')

    def test_apply_changes_audits_and_survives_reclassification(self):
        from auralytica import classification_preview as module
        self.assertTrue(hasattr(module,'apply_preview'),'Preview cannot yet be applied')
        plan=self.preview(self.db,self.labels,self.log)
        result=module.apply_preview(self.db,plan,self.labels,self.log)
        self.assertEqual(result['changed'],3)
        self.assertEqual(self.db.execute("SELECT user_group FROM videos WHERE id='00000000002'").fetchone()[0],'rest')
        self.assertEqual(self.db.execute("SELECT user_group FROM videos WHERE id='00000000001'").fetchone()[0],'music')
        self.assertEqual(self.db.execute("SELECT count(*) FROM audit_events WHERE kind='preview_applied'").fetchone()[0],3)
        from auralytica.classification import classify_active
        classify_active(self.db)
        self.assertEqual(self.db.execute("SELECT auto_group FROM videos WHERE id='00000000004'").fetchone()[0],'music')
        self.assertEqual(self.db.execute("SELECT auto_group FROM videos WHERE id='00000000006'").fetchone()[0],'music')

    def test_apply_rejects_stale_tampered_or_busy_and_rolls_back_audit_failure(self):
        from auralytica import classification_preview as module
        from unittest.mock import patch
        self.assertTrue(hasattr(module,'apply_preview'),'Apply needs snapshot and batch guards')
        plan=self.preview(self.db,self.labels,self.log)
        self.db.execute("UPDATE videos SET user_group='rest' WHERE id='00000000001'")
        with self.assertRaises(ValueError):module.apply_preview(self.db,plan,self.labels,self.log)
        self.db.execute("UPDATE videos SET user_group=NULL WHERE id='00000000001'")
        bad=json.loads(json.dumps(plan));bad['items'][0]['proposed_group']='rest'
        with self.assertRaises(ValueError):module.apply_preview(self.db,bad,self.labels,self.log)
        self.db.execute("INSERT INTO download_batches(output_dir,status) VALUES('/tmp/audio','queued')")
        with self.assertRaises(ValueError):module.apply_preview(self.db,plan,self.labels,self.log)
        self.db.execute("UPDATE download_batches SET status='paused'")
        before=list(self.db.iterdump())
        with patch.object(module,'record_event',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):module.apply_preview(self.db,plan,self.labels,self.log)
        self.assertEqual(before,list(self.db.iterdump()))
