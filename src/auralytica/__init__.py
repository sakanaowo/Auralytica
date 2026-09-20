"""Auralytica command-line entry point."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

from . import download_controls as downloads
from .importer import import_folder
from .storage import open_database
from .classification import classify_active
from .review import list_videos, move_videos
from . import metadata, audit


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
    meta = commands.add_parser('metadata', help='Lấy metadata YouTube Music có cache và log, không đổi nhóm')
    meta_commands = meta.add_subparsers(dest='metadata_command', required=True)
    for name in ('collect', 'status'):
        sub = meta_commands.add_parser(name, help='Thu thập/tiếp tục metadata' if name == 'collect' else 'Xem tiến độ metadata')
        sub.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
        if name == 'status':
            sub.add_argument('run_id')
        else:
            sub.add_argument('--video-id', action='append', dest='video_ids', help='ID trong lịch sử; có thể lặp tùy chọn này')
            sub.add_argument('--limit', type=int, default=50, help='Số video khi không chỉ định ID (mặc định 50, xem nhiều nhất)')
            sub.add_argument('--resume', metavar='RUN_ID', help='Tiếp tục snapshot cũ, dùng cấu hình cũ')
            sub.add_argument('--refresh', action='store_true', help='Bỏ qua cache cho lượt mới')
            sub.add_argument('--cache-days', type=float, default=7)
    audit_cli = commands.add_parser('audit', help='Xuất log JSONL local; không ghi đè file có sẵn')
    audit_cli.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    audit_cli.add_argument('--run-id')
    audit_cli.add_argument('--video-id')
    audit_cli.add_argument('--output', type=Path, required=True)
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
    preview = commands.add_parser('classification-preview', help='Xem trước nhóm theo nhãn/metadata local; không sửa DB')
    preview.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    preview.add_argument('--labels', type=Path, required=True)
    preview.add_argument('--metadata-log', type=Path, required=True)
    preview.add_argument('--output', type=Path, required=True)
    apply = commands.add_parser('classification-apply', help='Áp dụng preview còn khớp, giữ sửa tay và ghi audit')
    apply.add_argument('--database', type=Path, default=Path.home()/'.local/share/auralytica/library.sqlite3')
    apply.add_argument('--preview', type=Path, required=True)
    apply.add_argument('--labels', type=Path, required=True)
    apply.add_argument('--metadata-log', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'classification-preview':
        from .classification_preview import build_preview
        try:
            with closing(sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro', uri=True)) as db:
                db.row_factory = sqlite3.Row
                db.execute('BEGIN')
                result = build_preview(db, args.labels, args.metadata_log)
            with args.output.open('x', encoding='utf-8') as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            print(json.dumps({k:v for k,v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
        except (OSError, ValueError, sqlite3.Error) as exc:
            parser.error(str(exc))
        return
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
                if args.command == 'classification-apply':
                    from .classification_preview import apply_preview
                    result = apply_preview(db, json.loads(args.preview.read_text()), args.labels, args.metadata_log)
                elif args.command == 'import':
                    result = import_folder(db, args.folder, history=args.history)
                elif args.command == 'metadata':
                    if args.metadata_command == 'status':
                        result = metadata.get_run(db, args.run_id)
                    else:
                        if args.resume and (args.video_ids or args.refresh):
                            raise ValueError('resume giữ snapshot/cấu hình cũ; không dùng cùng video-id hoặc refresh.')
                        provider = metadata.YTMusicProvider()
                        run_id = args.resume or metadata.create_run(db, provider_key=provider.key,
                            video_ids=args.video_ids, limit=args.limit, cache_ttl=args.cache_days*86400, refresh=args.refresh)
                        print(f'Metadata run: {run_id}', file=sys.stderr, flush=True)
                        try:
                            result = metadata.collect_run(db, run_id, provider)
                        except KeyboardInterrupt:
                            print(f'Đã dừng. Tiếp tục: auralytica metadata collect --resume {run_id} --database {args.database}', file=sys.stderr)
                            raise SystemExit(130)
                elif args.command == 'audit':
                    result = audit.export_events(db, args.output, run_id=args.run_id, video_id=args.video_id)
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
