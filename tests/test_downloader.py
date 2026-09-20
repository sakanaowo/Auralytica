from pathlib import Path
import errno
import multiprocessing
import os
import signal
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from auralytica import batches, downloader, importer, storage


def child_with_worker_lock(database,batch_id,directory):
    db=storage.open_database(database)
    try:
        with batches.worker_session(db,batch_id) as batch:
            code="import os,sys,time; from pathlib import Path; (Path(sys.argv[-1])/'child.pid').write_text(str(os.getpid())); time.sleep(30)"
            downloader.YtDlpAdapter([sys.executable,'-c',code])(
                '00000000000',Path(directory),lambda a,b:None,lambda:False,batch['worker_lock_fd'])
    finally:
        db.close()


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=storage.open_database(self.root/'state.sqlite3')
        self.addCleanup(self.db.close)
        (self.root/'watch-history.json').write_text(json.dumps([
            {'titleUrl':f'https://youtu.be/{i:011d}','title':'Watched Song / dangerous: name',
             'subtitles':[{'name':'Artist - Topic'}]} for i in range(3)]))
        importer.import_folder(self.db,self.root)
        self.batch=batches.create_batch(self.db,self.root/'audio')['batch_id']

    @staticmethod
    def success(video_id, directory, progress, stopped, lock_fd):
        path=directory/'audio.webm'
        path.write_bytes(b'fixture audio')
        progress(13,13)
        return {'path':str(path),'id':video_id,'acodec':'opus','vcodec':'none'}

    def test_failure_continues_and_retry_skips_successful_files(self):
        calls=[]
        def flaky(video_id,*args):
            calls.append(video_id)
            if video_id.endswith('1'): raise downloader.DownloadFailure('unavailable','Video unavailable')
            return self.success(video_id,*args)
        result=downloader.run_batch(self.db,self.batch,adapter=flaky)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['counts'],{'completed':2,'failed':1})
        self.assertEqual(len(calls),3)
        batches.resume_batch(self.db,self.batch)
        calls.clear()
        def retry(video_id,*args):
            calls.append(video_id); return self.success(video_id,*args)
        result=downloader.run_batch(self.db,self.batch,adapter=retry)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(calls,['00000000001'])
        self.assertEqual(len(list((self.root/'audio').glob('*.webm'))),3)

    def test_stop_keeps_partial_path_and_resume_uses_it(self):
        folders=[]
        def cancelled(video_id,directory,progress,stopped,lock_fd):
            folders.append(directory)
            (directory/'audio.webm.part').write_bytes(b'partial')
            progress(7,None)
            downloader.request_stop(self.db,self.batch)
            self.assertTrue(stopped())
            raise downloader.DownloadStopped()
        result=downloader.run_batch(self.db,self.batch,adapter=cancelled)
        self.assertEqual(result['status'],'paused')
        self.assertTrue((folders[0]/'audio.webm.part').exists())
        batches.resume_batch(self.db,self.batch)
        def continued(video_id,directory,*args):
            if video_id=='00000000000': self.assertEqual(directory,folders[0])
            return self.success(video_id,directory,*args)
        self.assertEqual(downloader.run_batch(self.db,self.batch,adapter=continued)['status'],'completed')

    def test_filesystem_error_pauses_without_losing_completed_items(self):
        def full(video_id,*args):
            if video_id.endswith('1'): raise OSError(errno.ENOSPC,'No space left on device')
            return self.success(video_id,*args)
        result=downloader.run_batch(self.db,self.batch,adapter=full)
        self.assertEqual(result['status'],'paused')
        self.assertEqual(result['counts'],{'completed':1,'failed':1,'queued':1})

    def test_unrelated_filename_is_not_overwritten_and_bad_result_not_completed(self):
        existing=self.root/'audio'/'Song dangerous name [00000000000].webm'
        existing.write_bytes(b'keep')
        def wrong(video_id,*args):
            result=self.success(video_id,*args)
            if video_id.endswith('1'): result['id']='wrong000000'
            if video_id.endswith('2'): result['vcodec']='h264'
            return result
        result=downloader.run_batch(self.db,self.batch,adapter=wrong)
        self.assertEqual(result['counts'],{'completed':1,'failed':2})
        self.assertEqual(existing.read_bytes(),b'keep')

    def test_missing_successful_file_downloads_again_in_new_batch(self):
        downloader.run_batch(self.db,self.batch,adapter=self.success)
        file=self.db.execute("SELECT file_path FROM download_items WHERE video_id='00000000000'").fetchone()[0]
        Path(file).unlink()
        batch=batches.create_batch(self.db,self.root/'audio')
        self.assertEqual(batch['queued'],1)
        self.assertEqual(downloader.run_batch(self.db,batch['batch_id'],adapter=self.success)['status'],'completed')

    def test_adapter_reads_progress_and_result_from_subprocess(self):
        directory=self.root/'child'; directory.mkdir()
        code="""import json,sys; from pathlib import Path
p=Path(sys.argv[-1])/'audio.webm'; p.write_bytes(b'audio')
print(json.dumps({'type':'progress','downloaded_bytes':5,'total_bytes':5}),flush=True)
print(json.dumps({'type':'result','path':str(p),'id':sys.argv[-2],'acodec':'opus','vcodec':'none'}),flush=True)
"""
        adapter=downloader.YtDlpAdapter(command=[sys.executable,'-c',code])
        progress=[]
        result=adapter('00000000000',directory,lambda a,b:progress.append((a,b)),lambda:False,None)
        self.assertEqual(progress,[(5,5)])
        self.assertTrue(Path(result['path']).is_file())

    def test_adapter_stops_child_even_without_progress(self):
        code="import time; time.sleep(30)"
        adapter=downloader.YtDlpAdapter(command=[sys.executable,'-c',code])
        started=time.monotonic()
        with self.assertRaises(downloader.DownloadStopped):
            adapter('00000000000',self.root,lambda a,b:None,lambda:time.monotonic()-started>.2,None)
        self.assertLess(time.monotonic()-started,5)

    def test_crash_after_publish_reuses_same_final_file(self):
        original=downloader._publish
        def interrupted(*args):
            original(*args)
            raise KeyboardInterrupt()
        with patch('auralytica.downloader._publish',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                downloader.run_batch(self.db,self.batch,adapter=self.success)
        first=list((self.root/'audio').glob('*.webm'))
        self.assertEqual(len(first),1)
        batches.resume_batch(self.db,self.batch)
        def resume(video_id,directory,progress,stopped,lock_fd):
            path=directory/'audio.webm'
            if path.exists():
                return {'path':str(path),'id':video_id,'acodec':'opus','vcodec':'none'}
            return self.success(video_id,directory,progress,stopped,lock_fd)
        self.assertEqual(downloader.run_batch(self.db,self.batch,adapter=resume)['status'],'completed')
        self.assertEqual(len(list((self.root/'audio').glob('*.webm'))),3)

    def test_cleanup_failure_does_not_mark_published_file_failed(self):
        original=Path.unlink
        def deny_staging(path,*args,**kwargs):
            if '.auralytica' in path.parts and path.suffix=='.webm':
                raise PermissionError('Cannot clean staging')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',deny_staging):
            result=downloader.run_batch(self.db,self.batch,adapter=self.success)
        self.assertEqual(result['status'],'completed')

    def test_last_item_filesystem_failure_is_paused(self):
        def full(video_id,*args):
            if video_id.endswith('2'): raise OSError(errno.ENOSPC,'No space left on device')
            return self.success(video_id,*args)
        self.assertEqual(downloader.run_batch(self.db,self.batch,adapter=full)['status'],'paused')

    def test_orphan_downloader_keeps_worker_lock_until_child_exits(self):
        context=multiprocessing.get_context('spawn')
        parent=context.Process(target=child_with_worker_lock,args=(self.root/'state.sqlite3',self.batch,self.root))
        parent.start(); child_pid=None
        try:
            for _ in range(100):
                if (self.root/'child.pid').exists():
                    child_pid=int((self.root/'child.pid').read_text());break
                time.sleep(.02)
            self.assertIsNotNone(child_pid)
            parent.terminate();parent.join(5)
            with self.assertRaisesRegex(storage.BatchBusyError,'Worker khác'):
                batches.recover_batch(self.db,self.batch)
            os.killpg(child_pid,signal.SIGTERM)
            for _ in range(100):
                try:
                    result=batches.recover_batch(self.db,self.batch)
                    break
                except storage.BatchBusyError: time.sleep(.02)
            else: self.fail('Child lock not released after exit')
            self.assertEqual(result['status'],'paused')
        finally:
            if parent.is_alive(): parent.terminate();parent.join(5)
            if child_pid:
                try: os.killpg(child_pid,signal.SIGKILL)
                except ProcessLookupError: pass

    def test_adapter_surfaces_protocol_errors_without_accepting_incomplete_output(self):
        # A noisy downloader must still preserve the structured error and must
        # never accept successful exit alone as a completed audio download.
        error = dict(type='error', code='unavailable', message='fixture unavailable', fatal=False)
        code = f"import json; print('not JSON'); print('[]'); print({json.dumps(json.dumps(error))})"
        adapter = downloader.YtDlpAdapter([sys.executable, '-c', code])
        with self.assertRaises(downloader.DownloadFailure) as failure:
            adapter('00000000000', self.root, lambda *args: None, lambda: False, None)
        self.assertEqual(failure.exception.code, 'unavailable')
        self.assertEqual(str(failure.exception), 'fixture unavailable')
        empty = downloader.YtDlpAdapter([sys.executable, '-c', 'pass'])
        with self.assertRaisesRegex(downloader.DownloadFailure, 'không trả file hoàn tất'):
            empty('00000000000', self.root, lambda *args: None, lambda: False, None)
        with self.assertRaises(downloader.DownloadFailure) as failure:
            empty('../bad-id', self.root, lambda *args: None, lambda: False, None)
        self.assertEqual(failure.exception.code, 'invalid_id')

    def test_ytdlp_error_summary_does_not_persist_urls_or_tokens(self):
        from auralytica import _ytdlp
        code, message, fatal = _ytdlp.summarize_error(
            RuntimeError('Private video https://signed.example/audio?token=SECRET'))
        self.assertEqual((code, fatal), ('unavailable', False))
        self.assertNotIn('SECRET', message)
        self.assertNotIn('https://', message)
        self.assertEqual(
            _ytdlp.summarize_error(OSError(errno.ENOSPC, 'No space left on device')),
            ('filesystem', 'Không thể ghi file tải; kiểm tra quyền và dung lượng.', True),
        )
