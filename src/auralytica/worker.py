"""Detached worker entry point, using the same persistent lock as every caller."""
from contextlib import closing
import sqlite3
import sys

from .downloader import DownloadFailure, run_batch
from .storage import BatchBusyError, open_database, set_setting


def main():
    database, batch_id = sys.argv[1], int(sys.argv[2])
    with closing(open_database(database)) as db:
        try:
            run_batch(db, batch_id)
        except (BatchBusyError, ValueError):
            # Another launch already claimed/finished/stopped this queued batch.
            return
        except (DownloadFailure, OSError, sqlite3.Error) as exc:
            set_setting(db, f'batch_error:{batch_id}', str(exc)[:1500])


if __name__ == '__main__':
    main()
