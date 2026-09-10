"""Local HTTP API for Takeout review."""

from contextlib import closing
from pathlib import Path, PurePosixPath
import sqlite3
import tempfile
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, UploadFile

from . import download_controls as downloads
from .importer import import_folder
from .review import list_videos, move_videos
from .storage import open_database, BatchBusyError


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
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.launch_worker = downloads.launch_worker
    app.add_middleware(LocalRequests, port=port, max_body_bytes=max_body_bytes)
    static = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=static), name='static')

    @app.exception_handler(BatchBusyError)
    async def batch_busy(request, exc):
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
        return FileResponse(static / 'index.html')

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
    def download_status(batch_id: int, page: Annotated[int, Query(ge=1)] = 1,
                        page_size: Annotated[int, Query(ge=1, le=1000)] = 50):
        with closing(open_database(database)) as db:
            return downloads.batch_status(db, batch_id, page=page, page_size=page_size)

    @app.post('/api/downloads')
    def download_start(payload: DownloadRequest):
        with closing(open_database(database)) as db:
            return downloads.start_download(db, database, output_dir=payload.output_dir, launcher=app.state.launch_worker)

    @app.post('/api/downloads/{batch_id}/stop')
    def download_stop(batch_id: int):
        with closing(open_database(database)) as db:
            return downloads.stop_download(db, batch_id)

    @app.post('/api/downloads/{batch_id}/resume')
    def download_resume(batch_id: int):
        with closing(open_database(database)) as db:
            return downloads.start_download(db, database, batch_id=batch_id, launcher=app.state.launch_worker)

    return app
