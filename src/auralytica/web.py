"""Local HTTP API for Takeout review."""

from contextlib import closing
from pathlib import Path, PurePosixPath
import hashlib
import json
import sqlite3
import tempfile
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, UploadFile

from . import download_controls as downloads
from . import dedup, enrichment, metadata
from .importer import import_folder
from .explore import summary as explore_summary
from .review import list_videos, move_videos
from .storage import open_database, BatchBusyError, RevisionConflict, get_setting
from . import database_identity


class LocalRequests:
    """Reject foreign hosts/origins and bound bodies before multipart parsing."""

    def __init__(self, app, *, port, max_body_bytes):
        self.app = app
        self.hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if port == 80:
            self.hosts.update({'127.0.0.1', 'localhost'})
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        host = headers.get('host', '')

        async def reject(status, detail):
            await JSONResponse({'detail': detail}, status_code=status)(scope, receive, send)

        if host not in self.hosts:
            await reject(400, 'Host không được phép.')
            return
        origin = headers.get('origin')
        mutating = scope['method'] not in {'GET', 'HEAD', 'OPTIONS'}
        if (mutating or origin is not None) and origin != f'http://{host}':
            await reject(403, 'Origin phải trùng địa chỉ ứng dụng local.')
            return
        try:
            length = int(headers.get('content-length', '0'))
            if length < 0:
                raise ValueError
        except ValueError:
            await reject(400, 'Content-Length không hợp lệ.')
            return
        if length > self.max_body_bytes:
            await reject(413, 'Upload vượt giới hạn kích thước.')
            return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > self.max_body_bytes:
                await reject(413, 'Upload vượt giới hạn kích thước.')
                return
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        delivered = False

        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        async def safe_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'x-content-type-options', b'nosniff'), (b'cache-control', b'no-store')]
            await send(message)

        await self.app(scope, limited_receive, safe_send)


VideoID = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9_-]{11}$')]


class MoveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    video_ids: list[VideoID] = Field(min_length=1, max_length=1000)
    to_group: Literal['music', 'rest']


class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    output_dir: str = Field(min_length=1, max_length=4096)
    preview_token: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')


class MetadataRunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    group: Literal['music', 'rest', 'all'] = 'rest'
    limit: int = Field(default=50, ge=1, le=1000)
    refresh: bool = False


class AliasRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    video_ids: list[VideoID] = Field(min_length=2, max_length=20)
    artist_scope: str | None = Field(default=None, max_length=500)


class SelectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    video_ids: list[VideoID] = Field(min_length=1, max_length=1000)
    keep: bool
    expected_revision: int = Field(ge=0)


class RejectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rejected: bool
    expected_revision: int = Field(ge=0)


class GroupSelectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    keep: bool
    expected_revision: int = Field(ge=0)


def _import_uploads(database, uploads):
    names = {}
    for upload in uploads:
        name = upload.filename or ''
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Đường dẫn upload không hợp lệ.')
        if path.name not in {'watch-history.json', 'music library songs.csv'}:
            raise ValueError('Chỉ nhận watch-history.json và music library songs.csv; HTML chưa hỗ trợ.')
        if path.name in names:
            raise ValueError('Có nhiều nguồn; chọn một lịch sử và library cùng export trước khi gửi.')
        names[path.name] = upload
    if 'watch-history.json' not in names:
        raise ValueError('Thiếu watch-history.json; chọn folder Takeout có lịch sử JSON.')
    with tempfile.TemporaryDirectory(prefix='auralytica-upload-') as folder:
        root = Path(folder)
        for name, upload in names.items():
            # Only the two fixed, validated basenames are used on disk.
            with (root / name).open('wb') as output:
                while chunk := upload.file.read(1024 * 1024):
                    output.write(chunk)
        with closing(open_database(database)) as db:
            return import_folder(db, root)


def create_app(database: str | Path, *, port=8765, max_body_bytes=64 * 1024 * 1024):
    if Path(database).expanduser().exists():
        with closing(open_database(database)) as startup_db:
            metadata.recover_interrupted(startup_db)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.launch_worker = downloads.launch_worker
    app.state.metadata_provider_factory = metadata.YTMusicProvider
    app.state.run_metadata_inline = lambda run_id: enrichment.run_inline(
        database, run_id, app.state.metadata_provider_factory)
    app.state.launch_metadata = lambda run_id: enrichment.launch_thread(
        database, run_id, app.state.metadata_provider_factory)
    app.add_middleware(LocalRequests, port=port, max_body_bytes=max_body_bytes)
    static = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=static), name='static')

    @app.exception_handler(BatchBusyError)
    async def batch_busy(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.exception_handler(RevisionConflict)
    async def revision_conflict(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid_input(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return JSONResponse({'detail': 'Không thể truy cập database local.'}, status_code=503)

    @app.exception_handler(OSError)
    async def filesystem_error(request, exc):
        return JSONResponse({'detail': 'Không thể đọc/ghi file local; kiểm tra quyền và dung lượng.'}, status_code=500)

    @app.get('/')
    def status():
        with closing(open_database(database)) as db:
            return RedirectResponse('/explore' if get_setting(db, 'active_import') else '/import', status_code=303)

    @app.get('/api/health')
    def health():
        return {'app': 'auralytica', 'api': 1, 'database_id': database_identity(database)}

    @app.get('/import')
    @app.get('/explore')
    @app.get('/deduplicate')
    @app.get('/download')
    def workflow_page():
        return FileResponse(static / 'index.html')

    @app.get('/api/workflow')
    def workflow():
        with closing(open_database(database)) as db:
            # One read snapshot: import, labels and batch locks must agree.
            db.execute('BEGIN')
            active = get_setting(db, 'active_import')
            rows = db.execute(
                "SELECT id, COALESCE(user_group, auto_group) AS selected_group FROM videos "
                "WHERE id IN (SELECT video_id FROM watch_events WHERE import_id=?) ORDER BY id",
                (active,),
            ).fetchall()
            counts = {group: sum(row['selected_group'] == group for row in rows)
                      for group in ('music', 'rest')}
            batches = [tuple(row) for row in db.execute('SELECT id, status FROM download_batches ORDER BY id')]
            locked = any(status in ('queued', 'running') for _, status in batches)
            result = dict(active_import=int(active) if active else None, counts=counts, batch_locked=locked,
                          steps=dict(import_='locked' if locked else 'ready',
                                     explore='ready' if active else 'needs_import',
                                     deduplicate=('ready' if counts['music'] else 'no_music') if active else 'needs_import',
                                     download='ready' if counts['music'] else ('no_music' if active else 'needs_import')))
            result['steps']['import'] = result['steps'].pop('import_')
            # Display-state fingerprint, not a mutation/selection concurrency token.
            result['revision'] = hashlib.sha256(json.dumps(
                [result, [tuple(row) for row in rows], batches], sort_keys=True).encode()).hexdigest()
            return result

    @app.get('/api/explore/summary')
    def music_summary():
        with closing(open_database(database)) as db:
            db.execute('BEGIN')
            return explore_summary(db)

    @app.get('/api/metadata/scope')
    def metadata_selection(group: Literal['music', 'rest', 'all'] = 'rest',
                           limit: Annotated[int, Query(ge=1, le=1000)] = 50):
        with closing(open_database(database)) as db:
            return enrichment.metadata_scope(db, group, limit)

    @app.get('/api/metadata/runs')
    def metadata_runs():
        with closing(open_database(database)) as db:
            return {'items': metadata.list_runs(db)}

    @app.post('/api/metadata/runs')
    def metadata_start(payload: MetadataRunRequest):
        provider = app.state.metadata_provider_factory()
        with closing(open_database(database)) as db:
            scope = enrichment.metadata_scope(db, payload.group, payload.limit)
            run_id = metadata.create_run(db, provider_key=provider.key,
                                         video_ids=scope['video_ids'], limit=payload.limit,
                                         refresh=payload.refresh)
        app.state.launch_metadata(run_id)
        with closing(open_database(database)) as db:
            return metadata.get_run(db, run_id)

    @app.get('/api/metadata/runs/{run_id}')
    def metadata_status(run_id: str):
        with closing(open_database(database)) as db:
            return metadata.get_run(db, run_id)

    @app.get('/api/metadata/runs/{run_id}/events')
    def metadata_events(run_id: str):
        with closing(open_database(database)) as db:
            return {'items': enrichment.run_events(db, run_id)}

    @app.post('/api/metadata/runs/{run_id}/stop')
    def metadata_stop(run_id: str):
        with closing(open_database(database)) as db:
            return metadata.request_stop(db, run_id)

    @app.post('/api/metadata/runs/{run_id}/resume')
    def metadata_resume(run_id: str):
        with closing(open_database(database)) as db:
            run = metadata.get_run(db, run_id)
            if run['status'] not in {'paused', 'partial', 'failed'}:
                raise ValueError('Chỉ tiếp tục lượt đã dừng hoặc có lỗi.')
        app.state.launch_metadata(run_id)
        with closing(open_database(database)) as db:
            return metadata.get_run(db, run_id)

    @app.post('/api/classification/previews')
    def classification_preview_create():
        with closing(open_database(database)) as db:
            return enrichment.create_preview(db)

    @app.get('/api/classification/previews/{preview_id}')
    def classification_preview_get(preview_id: str):
        with closing(open_database(database)) as db:
            return enrichment.get_preview(db, preview_id)

    @app.post('/api/classification/previews/{preview_id}/apply')
    def classification_preview_apply(preview_id: str):
        with closing(open_database(database)) as db:
            return enrichment.apply_preview(db, preview_id)

    @app.get('/api/dedup/runs/latest')
    def dedup_latest():
        with closing(open_database(database)) as db:
            return {'run': dedup.latest_run(db), 'selection_revision': dedup.selection_revision(db)}

    @app.post('/api/dedup/runs')
    def dedup_start():
        with closing(open_database(database)) as db:
            return dedup.create_run(db)

    @app.get('/api/dedup/runs/{run_id}/groups')
    def dedup_groups(run_id: str, page: Annotated[int, Query(ge=1)] = 1,
                     page_size: Annotated[int, Query(ge=1, le=100)] = 20):
        with closing(open_database(database)) as db:
            return dedup.list_groups(db, run_id, page=page, page_size=page_size)

    @app.post('/api/dedup/aliases')
    def dedup_alias(payload: AliasRequest):
        with closing(open_database(database)) as db:
            alias = dedup.confirm_video_aliases(db, payload.video_ids, artist_scope=payload.artist_scope)
            run = dedup.create_run(db)
            return {'alias': alias, 'run': run}

    @app.post('/api/dedup/selections')
    def dedup_selection(payload: SelectionRequest):
        with closing(open_database(database)) as db:
            return dedup.update_selections(db, payload.video_ids, payload.keep, payload.expected_revision)

    @app.post('/api/dedup/groups/{group_id}/rejection')
    def dedup_rejection(group_id: str, payload: RejectionRequest):
        with closing(open_database(database)) as db:
            return dedup.set_group_rejection(db, group_id, payload.rejected, payload.expected_revision)

    @app.get('/api/dedup/groups/{group_id}/members')
    def dedup_members(group_id: str, page: Annotated[int, Query(ge=1)] = 1,
                      page_size: Annotated[int, Query(ge=1, le=100)] = 50):
        with closing(open_database(database)) as db:
            return dedup.list_members(db, group_id, page=page, page_size=page_size)

    @app.post('/api/dedup/groups/{group_id}/selection')
    def dedup_group_selection(group_id: str, payload: GroupSelectionRequest):
        with closing(open_database(database)) as db:
            return dedup.group_selection(db, group_id, payload.keep, payload.expected_revision)

    @app.get('/api/videos')
    def videos(group: Literal['music', 'rest'] = 'music',
               search: Annotated[str, Query(max_length=500)] = '',
               channel: Annotated[str | None, Query(max_length=500)] = None,
               reason: Annotated[str | None, Query(max_length=100)] = None,
               page: Annotated[int, Query(ge=1)] = 1,
               page_size: Annotated[int, Query(ge=1, le=1000)] = 50,
               sort: Literal['watch_count', 'title', 'channel'] = 'watch_count'):
        with closing(open_database(database)) as db:
            return list_videos(db, group=group, search=search, channel=channel,
                               reason=reason, page=page, page_size=page_size, sort=sort)

    @app.post('/api/videos/move')
    def move(payload: MoveRequest):
        with closing(open_database(database)) as db:
            return move_videos(db, payload.video_ids, payload.to_group)

    @app.post('/api/imports')
    async def imports(request: Request):
        async with request.form(max_files=2, max_fields=0) as form:
            entries = form.multi_items()
            if any(key != 'files' or not isinstance(value, UploadFile) for key, value in entries):
                raise HTTPException(400, 'Gửi các file đã chọn bằng trường multipart files.')
            return await run_in_threadpool(_import_uploads, database, [value for _, value in entries])

    @app.get('/api/downloads/preview')
    def download_preview(output_dir: Annotated[str, Query(min_length=1, max_length=4096)]):
        with closing(open_database(database)) as db:
            return downloads.preview(db, output_dir)

    @app.get('/api/downloads')
    def download_list():
        with closing(open_database(database)) as db:
            return downloads.list_batches(db)

    @app.get('/api/downloads/{batch_id}')
    def download_status(batch_id: int,
                        status: Annotated[str | None, Query(pattern=r'^(all|queued|running|completed|failed|skipped)$')] = None,
                        page: Annotated[int, Query(ge=1)] = 1,
                        page_size: Annotated[int, Query(ge=1, le=1000)] = 50):
        with closing(open_database(database)) as db:
            return downloads.batch_status(db, batch_id, page=page, page_size=page_size, status=status)

    @app.post('/api/downloads/{batch_id}/retry-failed')
    def download_retry_failed(batch_id: int):
        with closing(open_database(database)) as db:
            return downloads.retry_failed(db, database, batch_id=batch_id, launcher=app.state.launch_worker)

    @app.post('/api/downloads/{batch_id}/items/{video_id}/retry')
    def download_retry_item(batch_id: int, video_id: VideoID):
        with closing(open_database(database)) as db:
            return downloads.retry_item(db, database, batch_id=batch_id, video_id=video_id, launcher=app.state.launch_worker)

    @app.post('/api/downloads')
    def download_start(payload: DownloadRequest):
        with closing(open_database(database)) as db:
            return downloads.start_download(db, database, output_dir=payload.output_dir,
                                            preview_token=payload.preview_token,
                                            launcher=app.state.launch_worker)

    @app.post('/api/downloads/{batch_id}/stop')
    def download_stop(batch_id: int):
        with closing(open_database(database)) as db:
            return downloads.stop_download(db, batch_id)

    @app.post('/api/downloads/{batch_id}/resume')
    def download_resume(batch_id: int):
        with closing(open_database(database)) as db:
            return downloads.start_download(db, database, batch_id=batch_id, launcher=app.state.launch_worker)

    return app
