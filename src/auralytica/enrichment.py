"""Server-side metadata scope and immutable classification previews."""
from contextlib import closing
import hashlib
import json
import threading
import time
import uuid

from . import metadata
from .audit import finish_run, record_event, start_run
from .classification import classify_import
from .classification_preview import STRONG
from .storage import (RevisionConflict, assert_review_unlocked, get_setting,
                      open_database, transaction)

DEFAULT_CACHE_TTL = 7 * 86400


def metadata_scope(db, group='rest', limit=50):
    if group not in {'music', 'rest', 'all'}:
        raise ValueError('group phải là music, rest hoặc all.')
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('limit phải trong khoảng 1–1000.')
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Hãy import Takeout trước.')
    clause = '' if group == 'all' else 'AND COALESCE(v.user_group,v.auto_group)=?'
    params = (active,) if group == 'all' else (active, group)
    rows = db.execute(
        'SELECT v.id,COUNT(*) AS watches FROM videos v JOIN watch_events e ON e.video_id=v.id '
        f'WHERE e.import_id=? {clause} GROUP BY v.id ORDER BY watches DESC,v.id', params).fetchall()
    ids = [row['id'] for row in rows[:limit]]
    cutoff = time.time() - DEFAULT_CACHE_TTL
    cached = stale = 0
    for video_id in ids:
        row = db.execute('SELECT MAX(fetched_at) FROM metadata_cache WHERE video_id=?', (video_id,)).fetchone()
        if row[0] is not None:
            cached += row[0] >= cutoff
            stale += row[0] < cutoff
    return dict(group=group, available=len(rows), selected=len(ids), cached=cached,
                stale=stale, video_ids=ids)


def run_inline(database, run_id, provider_factory):
    with closing(open_database(database)) as db:
        return metadata.collect_run(db, run_id, provider_factory())


def launch_thread(database, run_id, provider_factory):
    threading.Thread(target=run_inline, args=(database, run_id, provider_factory), daemon=True).start()


def run_events(db, run_id, limit=200):
    metadata.get_run(db, run_id)
    rows = db.execute('SELECT id,video_id,kind,payload_json,created_at FROM audit_events '
                      'WHERE run_id=? ORDER BY id DESC LIMIT ?', (run_id, limit)).fetchall()
    return [dict(id=row['id'], video_id=row['video_id'], kind=row['kind'],
                 payload=json.loads(row['payload_json']), created_at=row['created_at']) for row in rows]


def _snapshot(db):
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Hãy import Takeout trước.')
    rows = db.execute(
        'SELECT v.*,COUNT(*) AS watch_count,COUNT(DISTINCT date(e.watched_at)) AS watch_days '
        'FROM videos v JOIN watch_events e ON e.video_id=v.id WHERE e.import_id=? '
        'GROUP BY v.id ORDER BY v.id', (active,)).fetchall()
    observations = {}
    for row in db.execute(
            'SELECT c.video_id,c.provider_key,c.fetched_at,e.id,e.payload_json FROM metadata_cache c '
            'JOIN audit_events e ON e.id=c.observation_id ORDER BY c.video_id,c.fetched_at DESC'):
        observations.setdefault(row['video_id'], row)
    state = {
        'import_id': int(active),
        'videos': [(r['id'], r['auto_group'], r['user_group'], r['watch_count'], r['watch_days']) for r in rows],
        'observations': [(key, value['id'], value['fetched_at']) for key, value in sorted(observations.items())],
    }
    state_hash = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return int(active), rows, observations, state_hash


def create_preview(db):
    with transaction(db):
        assert_review_unlocked(db)
        active, rows, observations, state_hash = _snapshot(db)
        items = []
        for row in rows:
            observation = observations.get(row['id'])
            if observation is None:
                continue
            payload = json.loads(observation['payload_json'])
            stale = time.time() - observation['fetched_at'] > DEFAULT_CACHE_TTL
            field = payload.get('evidence', {}).get('music_video_type', {})
            exact = (payload.get('status') == 'observed' and payload.get('exact_match') is True
                     and payload.get('requested_id') == row['id'] and payload.get('returned_id') == row['id'])
            typ = field.get('value') if exact and not stale else None
            reason = ('ytmusic_strong' if typ in STRONG else
                      'ytmusic_ugc_recurrence' if typ == 'MUSIC_VIDEO_TYPE_UGC' and row['watch_days'] >= 3 else None)
            current = row['user_group'] or row['auto_group']
            proposed = current if row['user_group'] or reason is None else 'music'
            items.append(dict(video_id=row['id'], title=row['title'], current_group=current,
                              proposed_group=proposed, changed=current != proposed,
                              manual_preserved=bool(row['user_group']),
                              reason='metadata_stale' if stale else (reason or 'no_change'),
                              watch_count=row['watch_count'], watch_days=row['watch_days'],
                              evidence=dict(provider_key=observation['provider_key'], observation_id=observation['id'],
                                            fetched_at=observation['fetched_at'], metadata_exact=exact,
                                            stale=stale,
                                            music_video_type=typ)))
        preview_id = uuid.uuid4().hex
        plan = dict(preview_id=preview_id, import_id=active, state_hash=state_hash,
                    changed=sum(item['changed'] for item in items), items=items)
        db.execute('INSERT INTO classification_previews(id,import_id,state_hash,plan_json) VALUES(?,?,?,?)',
                   (preview_id, active, state_hash, json.dumps(plan, ensure_ascii=False)))
        return plan


def get_preview(db, preview_id):
    row = db.execute('SELECT * FROM classification_previews WHERE id=?', (preview_id,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy preview.')
    plan = json.loads(row['plan_json'])
    plan['status'] = row['status']
    return plan


def apply_preview(db, preview_id):
    conflict = None
    result = None
    with transaction(db):
        assert_review_unlocked(db)
        row = db.execute('SELECT * FROM classification_previews WHERE id=?', (preview_id,)).fetchone()
        if row is None:
            raise ValueError('Không tìm thấy preview.')
        plan = json.loads(row['plan_json'])
        active, _, _, state_hash = _snapshot(db)
        if row['status'] != 'ready' or active != row['import_id'] or state_hash != row['state_hash']:
            db.execute("UPDATE classification_previews SET status='stale' WHERE id=? AND status='ready'", (preview_id,))
            conflict = 'Preview đã cũ; tạo preview mới trước khi áp dụng.'
        else:
            run_id = start_run(db, 'classification_apply', active, 'server-preview-v1',
                               {'preview_id': preview_id, 'state_hash': state_hash})
            changed = 0
            for item in plan['items']:
                if not item['changed']:
                    continue
                video = db.execute('SELECT metadata_json FROM videos WHERE id=?', (item['video_id'],)).fetchone()
                values = json.loads(video['metadata_json'])
                values['applied_music_evidence'] = item['evidence']
                db.execute('UPDATE videos SET metadata_json=? WHERE id=?',
                           (json.dumps(values, ensure_ascii=False), item['video_id']))
                record_event(db, 'preview_applied', {'preview_id': preview_id, 'reason': item['reason'],
                             'evidence': item['evidence']}, run_id=run_id, video_id=item['video_id'])
                changed += 1
            classify_import(db, active)
            finish_run(db, run_id, 'completed', changed=changed)
            db.execute("UPDATE classification_previews SET status='applied',applied_at=CURRENT_TIMESTAMP WHERE id=?",
                       (preview_id,))
            result = dict(run_id=run_id, preview_id=preview_id, changed=changed)
    if conflict:
        raise RevisionConflict(conflict)
    return result
