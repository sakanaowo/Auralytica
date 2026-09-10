"""Browser fixture: real HTTP/database/worker, synthetic audio and controlled errors."""
from contextlib import closing
from pathlib import Path
import sys
import threading
import time
import uvicorn
from auralytica import download_controls
from auralytica.downloader import DownloadFailure, DownloadStopped, run_batch
from auralytica.storage import open_database
from auralytica.web import create_app
root, port = Path(sys.argv[1]), int(sys.argv[2])

def launch(database, batch_id):
    def work():
        def adapter(video_id, directory, progress, stopped, lock_fd):
            while not (root/'release').exists():
                progress(100, 200)
                if stopped(): raise DownloadStopped()
                time.sleep(.05)
            marker = root/'failed-once'
            if video_id == '00000000001' and not marker.exists():
                marker.touch()
                raise DownloadFailure('unavailable', 'fixture unavailable')
            path = directory/'audio.webm'; path.write_bytes(b'fixture audio')
            return dict(id=video_id, path=str(path), acodec='opus', vcodec='none')
        with closing(open_database(database)) as db:
            run_batch(db, batch_id, adapter=adapter)
    threading.Thread(target=work, daemon=True).start()
app = create_app(root/'state.sqlite3', port=port)
app.state.launch_worker = launch
uvicorn.run(app, host='127.0.0.1', port=port, access_log=False)
