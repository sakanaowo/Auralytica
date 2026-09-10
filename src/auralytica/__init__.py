"""Auralytica command-line entry point."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from . import download_controls as downloads
from .importer import import_folder
from .storage import open_database
from .classification import classify_active
from .review import list_videos, move_videos


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="auralytica",
        description="Tải audio nhạc từ lịch sử YouTube trong Google Takeout.",
        epilog="Dùng serve để mở giao diện local. Dùng download để tải toàn bộ nhóm nhạc.",
    )
    commands = parser.add_subparsers(dest='command')
    ingest = commands.add_parser('import', help='Nhập folder Google Takeout (JSON)')
    ingest.add_argument('folder')
    ingest.add_argument('--history', help='Đường dẫn tương đối đến watch-history.json khi có nhiều nguồn')
    ingest.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    classify = commands.add_parser('classify', help='Chạy lại gợi ý cho lịch sử đang xem, giữ sửa tay')
    classify.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    listing = commands.add_parser('list', help='Xem và lọc hai nhóm video')
    listing.add_argument('--group', choices=['music', 'rest'], default='music')
    listing.add_argument('--search', default='')
    listing.add_argument('--channel', help='Channel ID/URL chính xác đã lưu')
    listing.add_argument('--reason')
    listing.add_argument('--sort', choices=['watch_count', 'title', 'channel'], default='watch_count')
    listing.add_argument('--page', type=int, default=1)
    listing.add_argument('--page-size', type=int, default=50)
    listing.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    move = commands.add_parser('move', help='Chuyển video qua lại giữa music/rest')
    move.add_argument('video_ids', nargs='+')
    move.add_argument('--to', choices=['music', 'rest'], required=True)
    move.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    serve = commands.add_parser('serve', help='Chạy giao diện hai bảng và API local')
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    for name in ('download', 'status', 'stop', 'resume'):
        command = commands.add_parser(name, help={'download':'Tải toàn bộ nhóm nhạc', 'status':'Xem tiến độ tải', 'stop':'Dừng lượt tải', 'resume':'Tiếp tục snapshot cũ'}[name])
        command.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
        if name == 'download':
            command.add_argument('--output', required=True)
        elif name == 'status':
            command.add_argument('batch_id', nargs='?', type=int)
            command.add_argument('--page', type=int, default=1)
            command.add_argument('--page-size', type=int, default=50)
        else:
            command.add_argument('batch_id', type=int)
    args = parser.parse_args()
    if args.command == 'serve':
        if not 1 <= args.port <= 65535:
            parser.error('port phải trong khoảng 1–65535.')
        import uvicorn
        from .web import create_app
        uvicorn.run(create_app(args.database, port=args.port), host='127.0.0.1', port=args.port,
                    proxy_headers=False, access_log=False)
        return
    if args.command:
        try:
            with closing(open_database(args.database)) as db:
                if args.command == 'import':
                    result = import_folder(db, args.folder, history=args.history)
                elif args.command == 'classify':
                    result = classify_active(db)
                elif args.command == 'list':
                    result = list_videos(db, group=args.group, search=args.search, channel=args.channel,
                                         reason=args.reason, sort=args.sort, page=args.page, page_size=args.page_size)
                elif args.command == 'download':
                    result = downloads.start_download(db, args.database, output_dir=args.output)
                elif args.command == 'status':
                    result = downloads.batch_status(db, args.batch_id, page=args.page, page_size=args.page_size)
                elif args.command == 'stop':
                    result = downloads.stop_download(db, args.batch_id)
                elif args.command == 'resume':
                    result = downloads.start_download(db, args.database, batch_id=args.batch_id)
                else:
                    result = move_videos(db, args.video_ids, args.to)
        except (OSError, ValueError, sqlite3.Error) as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
