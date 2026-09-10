"""Opt-in network acceptance: one Takeout video through the installed CLI.

Usage: python tests/manual/smoke_download.py TAKEOUT_FOLDER NEW_WORK_DIRECTORY
Requires ffprobe and ffmpeg. Keeps local evidence/audio in the work directory.
"""
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    source, root = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    database = root/'state.sqlite3'
    cli = str(Path(sys.executable).parent/'auralytica')
    def call(*args):
        result = subprocess.run([cli, *args, '--database', str(database)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError(f'CLI {args[0]} failed; exit {result.returncode}')
        return json.loads(result.stdout)
    imported = call('import', str(source))
    if imported['statistics']['unique_videos'] != 1:
        raise ValueError('Smoke requires exactly one unique video; no download started.')
    started = time.monotonic()
    batch = call('download', '--output', str(root/'audio'))
    try:
        while time.monotonic() - started < 120:
            status = call('status', str(batch['batch_id']))
            if status['status'] not in {'queued', 'running'}:
                break
            time.sleep(.5)
        else:
            raise TimeoutError('Download exceeded smoke deadline.')
        (root/'status.local.json').write_text(json.dumps(status, ensure_ascii=False, indent=2))
        if status['status'] != 'completed':
            raise RuntimeError(f"Download ended {status['status']}; see local status file.")
        item = status['items'][0]
        path = Path(item['file_path'])
        assert item['video_id'] in path.name
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name',
                                '-of', 'json', str(path)], capture_output=True, text=True, check=True)
        streams = json.loads(probe.stdout)['streams']
        assert streams and all(stream['codec_type'] == 'audio' for stream in streams)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'],
                       capture_output=True, check=True, timeout=60)
        again = call('download', '--output', str(root/'audio'))
        assert again['skipped'] == 1 and again['queued'] == 0
        report = dict(status='completed', bytes=path.stat().st_size, streams=streams,
                      decode_exit=0, second_batch_skipped=1, initial_response_status=batch['status'],
                      elapsed_seconds=round(time.monotonic()-started, 2))
        (root/'validation.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
    finally:
        status = call('status', str(batch['batch_id']))
        if status['status'] in {'queued', 'running'}:
            call('stop', str(batch['batch_id']))


if __name__ == '__main__':
    main()
