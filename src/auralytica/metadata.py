"""Resumable, observation-only enrichment of a frozen history selection."""

from contextlib import contextmanager
import fcntl
import json
import math
from pathlib import Path
import re
import time

from .audit import finish_run, record_event, start_run
from .storage import assert_review_unlocked, get_setting, transaction

VERSION = 'metadata-v1'


class MetadataFetchError(Exception):
    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class YTMusicProvider:
    """Unauthenticated player metadata only; construction does not access the network."""
    def __init__(self, *, client=None, language='en', location='VN'):
        from importlib.metadata import version
        self.key = f'ytmusicapi:{version("ytmusicapi")}:player-v1:{language}:{location}'
        self.language, self.location = language, location
        self._client = client
        self.last_http_status = None

    def fetch(self, video_id):
        import requests
        self.last_http_status = None
        try:
            if self._client is None:
                from ytmusicapi import YTMusic
                owner = self
                class Session(requests.Session):
                    def request(self, method, url, **kwargs):
                        owner.last_http_status = None
                        kwargs['timeout'] = (5, 15)
                        response = super().request(method, url, **kwargs)
                        owner.last_http_status = response.status_code
                        response.raise_for_status()
                        return response
                self._client = YTMusic(requests_session=Session(), language=self.language, location=self.location)
            return self._client.get_song(video_id)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else self.last_http_status
            self.last_http_status = status
            raise MetadataFetchError(f'http_{status}', status == 429 or (status is not None and status >= 500)) from None
        except (requests.Timeout, requests.ConnectionError):
            raise MetadataFetchError('network_error', True) from None


def create_run(db, *, provider_key, video_ids=None, limit=50, max_attempts=3,
               cache_ttl=7*86400, refresh=False):
    if type(limit) is not int or not 1 <= limit <= 100000:
        raise ValueError('limit phải trong khoảng 1–100000.')
    if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
        raise ValueError('max_attempts phải trong khoảng 1–5.')
    if not isinstance(cache_ttl, (int, float)) or not math.isfinite(cache_ttl) or cache_ttl < 0:
        raise ValueError('cache_ttl phải hữu hạn và không âm.')
    if video_ids is not None and (not isinstance(video_ids, (list, tuple)) or not video_ids or
            not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', v) for v in video_ids)):
        raise ValueError('Cần danh sách video ID hợp lệ.')
    with transaction(db):
        assert_review_unlocked(db)
        active = get_setting(db, 'active_import')
        if active is None:
            raise ValueError('Hãy import Takeout trước.')
        available = [r[0] for r in db.execute(
            'SELECT video_id FROM watch_events WHERE import_id=? AND video_id IS NOT NULL '
            'GROUP BY video_id ORDER BY COUNT(*) DESC,video_id', (active,))]
        ids = list(dict.fromkeys(video_ids)) if video_ids is not None else available[:limit]
        if not ids or not set(ids) <= set(available):
            raise ValueError('Chỉ lấy metadata cho ID thuộc lịch sử đang xem; danh sách không được trống.')
        config = dict(provider_key=provider_key, max_attempts=max_attempts, cache_ttl=cache_ttl,
                      refresh=bool(refresh), request_interval=0.25)
        run_id = start_run(db, 'metadata', int(active), VERSION, config)
        db.executemany('INSERT INTO metadata_items(run_id,video_id,position) VALUES(?,?,?)',
                       [(run_id, video_id, index) for index, video_id in enumerate(ids)])
        record_event(db, 'metadata_selected', {'video_ids':ids}, run_id=run_id)
    return run_id


def get_run(db, run_id):
    row = db.execute("SELECT * FROM audit_runs WHERE id=? AND kind='metadata'", (run_id,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy lượt lấy metadata.')
    counts = dict(db.execute('SELECT status,COUNT(*) FROM metadata_items WHERE run_id=? GROUP BY status', (run_id,)))
    return dict(run_id=run_id, status=row['status'], import_id=row['import_id'], source_hash=row['source_hash'],
                config=json.loads(row['config_json']), total=sum(counts.values()), counts=counts)


def list_runs(db, limit=20):
    rows = db.execute("SELECT id FROM audit_runs WHERE kind='metadata' ORDER BY created_at DESC,id DESC LIMIT ?",
                      (limit,)).fetchall()
    return [get_run(db, row['id']) for row in rows]


def request_stop(db, run_id):
    with transaction(db):
        run = get_run(db, run_id)
        if run['status'] in {'pending', 'running'}:
            db.execute("UPDATE audit_runs SET status='stop_requested' WHERE id=?", (run_id,))
            record_event(db, 'run_stop_requested', {}, run_id=run_id)
    return get_run(db, run_id)


def recover_interrupted(db):
    """A newly created web app has no collector threads from the previous process."""
    with transaction(db):
        rows = db.execute("SELECT id,status FROM audit_runs WHERE kind='metadata' "
                          "AND status IN ('pending','running','stop_requested')").fetchall()
        for row in rows:
            db.execute("UPDATE audit_runs SET status='paused',finished_at=CURRENT_TIMESTAMP WHERE id=?",
                       (row['id'],))
            record_event(db, 'run_recovered', {'previous_status': row['status']}, run_id=row['id'])
    return len(rows)


def normalize(video_id, response):
    """Allowlist player fields. Queue UGC is deliberately not a fallback source."""
    response = response if isinstance(response, dict) else {}
    def obj(parent, key):
        value = parent.get(key)
        return value if isinstance(value, dict) else {}
    details = obj(response, 'videoDetails')
    micro = obj(obj(response, 'microformat'), 'microformatDataRenderer')
    play = obj(response, 'playabilityStatus')
    returned = details.get('videoId')
    returned = returned if isinstance(returned, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', returned) else None
    values = [
        ('music_video_type', details.get('musicVideoType'), 'videoDetails.musicVideoType'),
        ('category', micro.get('category'), 'microformat.microformatDataRenderer.category'),
        ('playability', play.get('status'), 'playabilityStatus.status'),
        ('title', details.get('title'), 'videoDetails.title'),
        ('author', details.get('author'), 'videoDetails.author'),
        ('channel_id', details.get('channelId'), 'videoDetails.channelId'),
        ('duration_seconds', details.get('lengthSeconds'), 'videoDetails.lengthSeconds'),
        ('is_live_content', details.get('isLiveContent'), 'videoDetails.isLiveContent'),
    ]
    evidence = {}
    for name, value, source in values:
        if name == 'is_live_content':
            value = value if type(value) is bool else None
        elif name == 'duration_seconds':
            value = int(value) if str(value).isdigit() and len(str(value)) <= 9 else None
        else:
            value = value[:1024] if isinstance(value, str) and value else None
        evidence[name] = dict(value=value, source='get_song.'+source)
    return dict(requested_id=video_id, returned_id=returned, exact_match=returned == video_id,
                status='observed' if returned == video_id else ('id_mismatch' if returned else 'missing'),
                evidence=evidence, missing_fields=[k for k, v in evidence.items() if v['value'] is None])


@contextmanager
def collector_lock(db):
    filename = next(r[2] for r in db.execute('PRAGMA database_list') if r[1] == 'main')
    if not filename:
        raise ValueError('Collector cần database trên đĩa.')
    # Separate from the audio worker: enrichment never changes video groups.
    with Path(str(Path(filename).resolve())+'.metadata.lock').open('a+b') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Đang có collector metadata chạy cho database này.') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def collect_run(db, run_id, provider, *, sleep=time.sleep):
    with collector_lock(db):
        run = get_run(db, run_id)
        config = run['config']
        if config['provider_key'] != provider.key:
            raise ValueError('Provider/version/config khác lượt gốc; tạo lượt mới để giữ nguồn cache chính xác.')
        if run['status'] == 'completed':
            return run
        if run['status'] == 'stop_requested':
            with transaction(db):
                finish_run(db, run_id, 'paused', counts=run['counts'])
            return get_run(db, run_id)
        with transaction(db):
            db.execute("UPDATE audit_runs SET status='running',finished_at=NULL WHERE id=?", (run_id,))
            record_event(db, 'run_resumed', {'previous_status':run['status']}, run_id=run_id)
        try:
            items = db.execute("SELECT video_id FROM metadata_items WHERE run_id=? AND status!='done' ORDER BY position", (run_id,)).fetchall()
            for item in items:
                if db.execute('SELECT status FROM audit_runs WHERE id=?', (run_id,)).fetchone()[0] == 'stop_requested':
                    with transaction(db):
                        finish_run(db, run_id, 'paused', counts=get_run(db, run_id)['counts'])
                    return get_run(db, run_id)
                video_id = item['video_id']
                cached = db.execute('SELECT * FROM metadata_cache WHERE provider_key=? AND video_id=?',
                                    (provider.key, video_id)).fetchone()
                age = time.time() - cached['fetched_at'] if cached else None
                if cached and not config['refresh'] and 0 <= age < config['cache_ttl']:
                    with transaction(db):
                        record_event(db, 'metadata_cache_hit', dict(observation_id=cached['observation_id'],
                                     provider_key=provider.key, age_seconds=age), run_id=run_id, video_id=video_id)
                        db.execute("UPDATE metadata_items SET status='done',observation_id=? WHERE run_id=? AND video_id=?",
                                   (cached['observation_id'], run_id, video_id))
                    continue
                attempts = db.execute("SELECT COUNT(*) FROM audit_events WHERE run_id=? AND video_id=? AND kind='metadata_observed'",
                                      (run_id, video_id)).fetchone()[0]
                for retry in range(config['max_attempts']):
                    start = time.monotonic()
                    retryable = False
                    try:
                        observation = normalize(video_id, provider.fetch(video_id))
                    except Exception as exc:
                        # Never save str(exc): it can contain headers, cookies or signed URLs.
                        retryable = isinstance(exc, (TimeoutError, ConnectionError)) or getattr(exc, 'retryable', False)
                        observation = dict(requested_id=video_id, returned_id=None, exact_match=False,
                                           status='error', error_code=getattr(exc, 'code', type(exc).__name__))
                    now = time.time()
                    observation.update(provider_key=provider.key, method='get_song', attempt=attempts+retry+1,
                                       fetched_at=now, elapsed_ms=round((time.monotonic()-start)*1000),
                                       http_status=getattr(provider, 'last_http_status', None), cache_hit=False,
                                       retryable=retryable)
                    with transaction(db):
                        event_id = record_event(db, 'metadata_observed', observation, run_id=run_id, video_id=video_id)
                        success = observation['status'] == 'observed'
                        db.execute('UPDATE metadata_items SET status=?,observation_id=? WHERE run_id=? AND video_id=?',
                                   ('done' if success else 'failed', event_id, run_id, video_id))
                        if success:
                            db.execute('INSERT INTO metadata_cache(provider_key,video_id,observation_id,fetched_at) VALUES(?,?,?,?) '
                                       'ON CONFLICT(provider_key,video_id) DO UPDATE SET observation_id=excluded.observation_id,fetched_at=excluded.fetched_at',
                                       (provider.key, video_id, event_id, now))
                    sleep(max(config['request_interval'], min(2**retry, 8) if retryable else 0))
                    if success or not retryable:
                        break
            with transaction(db):
                counts = get_run(db, run_id)['counts']
                finish_run(db, run_id, 'partial' if counts.get('failed') else 'completed', counts=counts)
        except BaseException:
            with transaction(db):
                finish_run(db, run_id, 'paused', counts=get_run(db, run_id)['counts'])
            raise
    return get_run(db, run_id)
