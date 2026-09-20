from contextlib import closing
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from auralytica import batches, classification, dedup, importer, review, storage


def create_concurrently(database, output, start, results):
    with closing(storage.open_database(database)) as db:
        start.wait(10)
        try:
            results.put(batches.create_batch(db, output)['batch_id'])
        except Exception as exc:
            results.put(str(exc))


def hold_worker(database, batch_id, ready, release):
    with closing(storage.open_database(database)) as db:
        with batches.worker_session(db, batch_id):
            ready.set()
            release.wait(20)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/'state.sqlite3'
        self.output=self.root/'audio'
        self.db=storage.open_database(self.path)
        self.addCleanup(self.db.close)
        rows=[{'titleUrl':f'https://youtu.be/{i:011d}', 'title':f'Watched Song {i}',
               'subtitles':[{'name':'Artist - Topic' if i<3 else 'Other'}]} for i in range(4)]
        (self.root/'watch-history.json').write_text(json.dumps(rows))
        importer.import_folder(self.db,self.root)

    def test_snapshot_includes_all_music_and_reuses_active_batch(self):
        self.assertEqual(review.list_videos(self.db,search='Song 0',page_size=1)['filtered_count'],1)
        first=batches.create_batch(self.db,self.output)
        self.assertEqual((first['total'],first['queued'],first['skipped']),(3,3,0))
        self.assertEqual(batches.create_batch(self.db,self.root/'different')['batch_id'],first['batch_id'])
        self.assertFalse((self.root/'different').exists())
        ids={row[0] for row in self.db.execute('SELECT video_id FROM download_items')}
        self.assertEqual(ids,{'00000000000','00000000001','00000000002'})

    def test_eligible_snapshot_excludes_only_explicit_selection_and_rejects_stale_token(self):
        initial = batches.eligible_snapshot(self.db, self.output)
        self.assertEqual(
            {key: initial[key] for key in ('music', 'excluded', 'kept', 'skipped', 'queued', 'needed')},
            {'music': 3, 'excluded': 0, 'kept': 3, 'skipped': 0, 'queued': 3, 'needed': 3},
        )
        dedup.update_selections(self.db, ['00000000001'], False, 0)
        current = batches.eligible_snapshot(self.db, self.output)
        self.assertEqual((current['music'], current['excluded'], current['kept']), (3, 1, 2))
        with self.assertRaises(storage.RevisionConflict):
            batches.create_batch(self.db, self.output, expected_token=initial['token'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM download_batches').fetchone()[0], 0)

        batch = batches.create_batch(self.db, self.output, expected_token=current['token'])
        self.assertEqual((batch['total'], batch['excluded'], batch['kept']), (2, 1, 2))
        self.assertEqual(
            {row[0] for row in self.db.execute('SELECT video_id FROM download_items WHERE batch_id=?', (batch['batch_id'],))},
            {'00000000000', '00000000002'},
        )
        batches.pause_batch(self.db, batch['batch_id'])
        dedup.update_selections(self.db, ['00000000001'], True, 1)
        self.assertEqual(batches.resume_batch(self.db, batch['batch_id'])['total'], 2)

    def test_preview_token_is_bound_to_output_and_valid_file_state(self):
        self.output.mkdir()
        path = self.output/'existing.webm'
        path.write_bytes(b'audio')
        self.db.execute("INSERT INTO download_batches(id,output_dir,status) VALUES(1,?,'completed')", (str(self.output),))
        self.db.execute(
            "INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) "
            "VALUES(1,'00000000000','completed',?,5)",
            (str(path),),
        )
        preview = batches.eligible_snapshot(self.db, self.output)
        self.assertEqual((preview['skipped'], preview['needed']), (1, 2))
        with self.assertRaises(storage.RevisionConflict):
            batches.create_batch(self.db, self.root/'other', expected_token=preview['token'])
        path.unlink()
        with self.assertRaises(storage.RevisionConflict):
            batches.create_batch(self.db, self.output, expected_token=preview['token'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM download_batches').fetchone()[0], 1)

    def test_completed_files_skip_only_at_valid_destination(self):
        self.output.mkdir()
        source=self.output/'Song.webm'
        source.write_bytes(b'audio')
        self.db.execute("INSERT INTO download_batches(id,output_dir,status) VALUES(1,?,'completed')",(str(self.output),))
        self.db.execute("INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) VALUES(1,'00000000000','completed',?,5)",(str(source),))
        first=batches.create_batch(self.db,self.output)
        self.assertEqual(first['skipped'],1)
        batches.pause_batch(self.db,first['batch_id'])
        source.write_bytes(b'changed')
        second=batches.create_batch(self.db,self.output)
        self.assertEqual(second['skipped'],0)
        batches.pause_batch(self.db,second['batch_id'])
        source.write_bytes(b'audio')
        other=batches.create_batch(self.db,self.root/'other')
        self.assertEqual(other['skipped'],0)

    def test_mutations_are_locked_until_paused_and_resume_keeps_snapshot(self):
        first=batches.create_batch(self.db,self.output)
        for action in (lambda:review.move_videos(self.db,['00000000000'],'rest'),
                       lambda:importer.import_folder(self.db,self.root),
                       lambda:classification.classify_active(self.db)):
            with self.assertRaises(storage.BatchBusyError): action()
        self.assertEqual(review.list_videos(self.db)['filtered_count'],3)
        batches.pause_batch(self.db,first['batch_id'])
        review.move_videos(self.db,['00000000000'],'rest')
        resumed=batches.resume_batch(self.db,first['batch_id'])
        self.assertEqual(resumed['total'],3)
        self.assertEqual(storage.get_video(self.db,'00000000000')['effective_group'],'rest')

    def test_invalid_output_and_empty_selection_create_no_batch(self):
        path=self.root/'file'
        path.write_text('keep')
        with self.assertRaises(OSError): batches.create_batch(self.db,path)
        review.move_videos(self.db,['00000000000','00000000001','00000000002'],'rest')
        with self.assertRaises(ValueError): batches.create_batch(self.db,self.output)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM download_batches').fetchone()[0],0)

    def test_all_completed_batch_does_not_lock_review_and_missing_file_is_queued_again(self):
        self.output.mkdir()
        self.db.execute("INSERT INTO download_batches(id,output_dir,status) VALUES(1,?,'completed')",(str(self.output),))
        for i in range(3):
            path=self.output/f'{i}.webm'
            path.write_bytes(b'audio')
            self.db.execute("INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) VALUES(1,?,'completed',?,5)",
                            (f'{i:011d}',str(path)))
        batch=batches.create_batch(self.db,self.output)
        self.assertEqual(batch['status'],'completed')
        self.assertEqual(batch['skipped'],3)
        review.move_videos(self.db,['00000000000'],'music')
        (self.output/'0.webm').unlink()
        batch=batches.create_batch(self.db,self.output)
        self.assertEqual((batch['queued'],batch['skipped']),(1,2))
        batches.pause_batch(self.db,batch['batch_id'])
        (self.output/'1.webm').unlink()
        resumed=batches.resume_batch(self.db,batch['batch_id'])
        self.assertEqual((resumed['queued'],resumed['skipped']),(2,1))

    def test_two_processes_create_only_one_batch(self):
        context=multiprocessing.get_context('spawn')
        start=context.Event(); results=context.Queue()
        workers=[context.Process(target=create_concurrently,args=(self.path,self.output,start,results)) for _ in range(2)]
        try:
            for worker in workers: worker.start()
            start.set()
            ids=[results.get(timeout=15) for _ in workers]
            self.assertEqual(ids,[1,1])
            for worker in workers:
                worker.join(5); self.assertEqual(worker.exitcode,0)
        finally:
            for worker in workers:
                if worker.is_alive(): worker.terminate(); worker.join(5)
            results.close(); results.join_thread()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM download_batches').fetchone()[0],1)

    def test_process_lock_and_crash_recovery(self):
        batch=batches.create_batch(self.db,self.output)
        context=multiprocessing.get_context('spawn')
        ready=context.Event(); release=context.Event()
        worker=context.Process(target=hold_worker,args=(self.path,batch['batch_id'],ready,release))
        worker.start()
        try:
            self.assertTrue(ready.wait(10))
            with self.assertRaises(storage.BatchBusyError):
                with batches.worker_session(self.db,batch['batch_id']): pass
            with self.assertRaises(storage.BatchBusyError): batches.recover_batch(self.db,batch['batch_id'])
            worker.terminate(); worker.join(5)
            result=batches.recover_batch(self.db,batch['batch_id'])
            self.assertEqual(result['status'],'paused')
            batches.resume_batch(self.db,batch['batch_id'])
            with batches.worker_session(self.db,batch['batch_id']):
                self.assertEqual(batches.get_batch(self.db,batch['batch_id'])['status'],'running')
            self.assertEqual(batches.get_batch(self.db,batch['batch_id'])['status'],'paused')
        finally:
            if worker.is_alive(): worker.terminate(); worker.join(5)
