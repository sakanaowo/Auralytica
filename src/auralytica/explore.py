"""Descriptive statistics of active music; never a classifier or accuracy estimate."""
import json
import time

from .classification import MUSIC, TALK
from .storage import get_setting


def summary(db):
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Chưa có lịch sử; hãy import Takeout trước.')
    rows = db.execute(
        "SELECT v.*, COUNT(*) AS watches, COUNT(DISTINCT substr(e.watched_at,1,10)) AS days, "
        "SUM(e.watched_at IS NULL) AS undated FROM videos v JOIN watch_events e ON e.video_id=v.id "
        "WHERE e.import_id=? AND COALESCE(v.user_group,v.auto_group)='music' GROUP BY v.id", (active,)
    ).fetchall()
    cached = {r[0]: r[1] for r in db.execute('SELECT video_id,MAX(fetched_at) FROM metadata_cache GROUP BY video_id')}
    decisions = {'user': 0, 'automatic': 0}
    repeats = dict.fromkeys(('1', '2', '3–9', '10+'), 0)
    days = dict.fromkeys(('0', '1', '2', '3+'), 0)
    signals = {'music_terms': 0, 'talk_terms': 0}
    metadata = {'available': 0, 'missing': 0, 'applied': 0, 'cached': 0, 'fresh': 0, 'stale': 0}
    channels = {}
    for row in rows:
        decisions['user' if row['user_group'] else 'automatic'] += 1
        n = row['watches']
        repeats[str(n) if n < 3 else ('3–9' if n < 10 else '10+')] += 1
        days[str(row['days']) if row['days'] < 3 else '3+'] += 1
        signals['music_terms'] += bool(MUSIC.search(row['title']))
        signals['talk_terms'] += bool(TALK.search(row['title']))
        applied = bool(json.loads(row['metadata_json']).get('applied_music_evidence'))
        has_cache = row['id'] in cached
        metadata['applied'] += applied
        metadata['cached'] += has_cache
        metadata['fresh'] += has_cache and time.time() - cached[row['id']] <= 7 * 86400
        metadata['stale'] += has_cache and time.time() - cached[row['id']] > 7 * 86400
        metadata['available' if applied or has_cache else 'missing'] += 1
        key = row['channel_key'] or row['channel_name'] or ''
        channel = channels.setdefault(key, dict(key=key, name=row['channel_name'] or 'Chưa biết kênh', videos=0, watch_events=0))
        channel['videos'] += 1
        channel['watch_events'] += n
    dates = db.execute(
        "SELECT substr(e.watched_at,1,10) AS day, COUNT(*) AS events FROM watch_events e "
        "JOIN videos v ON v.id=e.video_id WHERE e.import_id=? AND e.watched_at IS NOT NULL "
        "AND COALESCE(v.user_group,v.auto_group)='music' GROUP BY day ORDER BY day", (active,)
    ).fetchall()
    source = db.execute('SELECT statistics_json FROM imports WHERE id=?', (active,)).fetchone()
    return dict(scope='active_import_music', import_id=int(active), videos=len(rows),
                watch_events=sum(r['watches'] for r in rows), watch_days_utc=len(dates),
                undated_events=sum(r['undated'] for r in rows), decisions=decisions,
                repeat_distribution=repeats, day_distribution=days, title_signals=signals,
                metadata=metadata, channel_count=len(channels),
                channels=sorted(channels.values(), key=lambda c: (-c['videos'], -c['watch_events'], c['key']))[:20],
                recent_days=[dict(r) for r in dates[-30:]],
                import_statistics=json.loads(source['statistics_json']))
