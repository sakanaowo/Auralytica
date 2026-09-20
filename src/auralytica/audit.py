"""Local immutable observations and decision history; transactions belong to callers."""

import json
import uuid
from pathlib import Path


def record_event(db, kind, payload, *, run_id=None, video_id=None):
    return db.execute(
        'INSERT INTO audit_events(run_id,video_id,kind,payload_json) VALUES(?,?,?,?)',
        (run_id, video_id, kind, json.dumps(payload, ensure_ascii=False, allow_nan=False)),
    ).lastrowid


def start_run(db, kind, import_id, version, config):
    source = db.execute('SELECT source_hash FROM imports WHERE id=?', (import_id,)).fetchone()
    if source is None:
        raise ValueError('Không tìm thấy import.')
    run_id = uuid.uuid4().hex
    db.execute('INSERT INTO audit_runs(id,kind,import_id,source_hash,version,config_json,status) '
               'VALUES(?,?,?,?,?,?,?)', (run_id, kind, import_id, source[0], version,
                                        json.dumps(config, ensure_ascii=False), 'pending'))
    record_event(db, 'run_started', dict(kind=kind, import_id=import_id, source_hash=source[0],
                                       version=version, config=config), run_id=run_id)
    return run_id


def finish_run(db, run_id, status, **summary):
    db.execute('UPDATE audit_runs SET status=?,finished_at=CURRENT_TIMESTAMP WHERE id=?', (status, run_id))
    record_event(db, 'run_finished', dict(status=status, **summary), run_id=run_id)


def export_events(db, output, *, run_id=None, video_id=None):
    """Export a consistent snapshot, including cache dependencies; never overwrite a file."""
    if db.in_transaction:
        raise ValueError('Xuất audit cần transaction riêng.')
    db.execute('BEGIN')
    try:
        if run_id and db.execute('SELECT 1 FROM audit_runs WHERE id=?', (run_id,)).fetchone() is None:
            raise ValueError('Không tìm thấy run_id.')
        if video_id and db.execute('SELECT 1 FROM videos WHERE id=?', (video_id,)).fetchone() is None:
            raise ValueError('Không tìm thấy video_id.')
        clauses, params = [], []
        for key, value in [('run_id',run_id),('video_id',video_id)]:
            if value:
                clauses.append(key+'=?')
                params.append(value)
        rows = db.execute('SELECT * FROM audit_events'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY id', params).fetchall()
        events = {r['id']:dict(r) for r in rows}
        for row in rows:
            if row['kind'] == 'metadata_cache_hit':
                dependency_id = json.loads(row['payload_json'])['observation_id']
                if dependency_id not in events:
                    dependency = db.execute('SELECT * FROM audit_events WHERE id=?', (dependency_id,)).fetchone()
                    events[dependency_id] = dict(dependency, dependency=True)
        run_ids = {r['run_id'] for r in events.values() if r['run_id']}
        if run_id:
            run_ids.add(run_id)
        runs = [dict(db.execute('SELECT * FROM audit_runs WHERE id=?', (rid,)).fetchone()) for rid in sorted(run_ids)]
        db.commit()
    except BaseException:
        db.rollback()
        raise
    records = 0
    with Path(output).expanduser().open('x', encoding='utf-8') as handle:
        for run in runs:
            run['config'] = json.loads(run.pop('config_json'))
            handle.write(json.dumps(dict(kind='run_manifest', run=run), ensure_ascii=False)+'\n')
            records += 1
        for event_id in sorted(events):
            event = events[event_id]
            event['payload'] = json.loads(event.pop('payload_json'))
            handle.write(json.dumps(event, ensure_ascii=False)+'\n')
            records += 1
    return dict(output=str(Path(output).expanduser().resolve()), records=records)
