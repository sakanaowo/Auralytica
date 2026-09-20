"""Opt-in network acceptance for one Takeout video through backend services.

Usage: python tests/manual/smoke_download.py TAKEOUT_FOLDER NEW_WORK_DIRECTORY
Requires ffprobe and ffmpeg. Keeps local evidence/audio in the work directory.
"""

from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import time

from auralytica import batches, download_controls, downloader, importer, storage


def main():
    source, root = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    database = root/'state.sqlite3'
    output = root/'audio'
    with closing(storage.open_database(database)) as db:
        imported = importer.import_folder(db, source)
        if imported['statistics']['unique_videos'] != 1:
            raise ValueError('Smoke requires exactly one unique video; no download started.')
        started = time.monotonic()
        batch = batches.create_batch(db, output)
        downloader.run_batch(db, batch['batch_id'])
        status = download_controls.batch_status(db, batch['batch_id'])
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
        again = batches.create_batch(db, output)
        assert again['skipped'] == 1 and again['queued'] == 0
        report = dict(status='completed', bytes=path.stat().st_size, streams=streams,
                      decode_exit=0, second_batch_skipped=1, initial_response_status=batch['status'],
                      elapsed_seconds=round(time.monotonic()-started, 2))
        (root/'validation.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))


if __name__ == '__main__':
    main()
