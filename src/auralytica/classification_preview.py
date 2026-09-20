"""Offline, read-only proposals. No production classifier or review state changes."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

from .classification import TALK
from .storage import get_setting, transaction, assert_review_unlocked, set_video_group
from .audit import start_run, finish_run, record_event

VERSION = 'metadata-preview-v2'
STRONG = {'MUSIC_VIDEO_TYPE_ATV', 'MUSIC_VIDEO_TYPE_OMV', 'MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC'}
EXTRA = re.compile(r'\blyrics?\b|\bkaraoke\b|(?<!\w)m/?v(?!\w)|\bofficial audio\b|\bvisualizer\b', re.I)
TUTORIAL = re.compile(r'\btutorial\b|\bhow to\b|\blesson\b|hướng dẫn', re.I)
SHORT = re.compile(r'#shorts?\b', re.I)


def build_preview(db, labels_path, metadata_path):
    """Caller supplies a read transaction for a consistent snapshot."""
    active = get_setting(db, 'active_import')
    source = db.execute('SELECT source_hash FROM imports WHERE id=?', (active,)).fetchone()
    if source is None:
        raise ValueError('Chưa có lịch sử đang xem.')
    source_hash = source[0]
    videos = db.execute('SELECT v.*, COUNT(*) AS watch_count, '
        'COUNT(DISTINCT date(e.watched_at)) AS watch_days FROM videos v '
        'JOIN watch_events e ON e.video_id=v.id WHERE e.import_id=? GROUP BY v.id ORDER BY v.id', (active,)).fetchall()
    ids = {r['id'] for r in videos}
    labels_bytes, metadata_bytes = Path(labels_path).read_bytes(), Path(metadata_path).read_bytes()
    reader = csv.DictReader(io.StringIO(labels_bytes.decode('utf-8-sig')))
    if not {'video_id','source_hash','manual_label'} <= set(reader.fieldnames or []):
        raise ValueError('CSV cần video_id, source_hash, manual_label.')
    labels = {}
    for row in reader:
        vid = row['video_id']
        if vid not in ids or vid in labels or row['source_hash'] != source_hash:
            raise ValueError('CSV sai snapshot, ID ngoài lịch sử hoặc ID trùng.')
        if row['manual_label'] not in {'','music','non_music','uncertain','unavailable'}:
            raise ValueError('Nhãn CSV không hợp lệ.')
        labels[vid] = row
    records = [json.loads(line) for line in metadata_bytes.decode().splitlines() if line.strip()]
    runs = {r['run']['id']:r['run'] for r in records if r.get('kind') == 'run_manifest'}
    observations = {}
    for record in records:
        if record.get('kind') != 'metadata_observed':
            continue
        vid = record['video_id']; payload = record['payload']
        if vid not in ids or runs.get(record.get('run_id'), {}).get('source_hash') != source_hash:
            raise ValueError('Metadata sai snapshot hoặc ID ngoài lịch sử.')
        if vid not in observations or payload['fetched_at'] > observations[vid]['payload']['fetched_at']:
            observations[vid] = record
    channels = {r['channel_key']:r['group_name'] for r in db.execute('SELECT * FROM channel_decisions')}
    items = []
    for row in videos:
        vid = row['id']; label = labels.get(vid, {})
        observation = observations.get(vid, {}); payload = observation.get('payload', {})
        field = payload.get('evidence', {}).get('music_video_type', {})
        exact = (payload.get('status') == 'observed' and payload.get('exact_match') is True
                 and payload.get('requested_id') == vid and payload.get('returned_id') == vid
                 and field.get('source') == 'get_song.videoDetails.musicVideoType')
        typ = field.get('value') if exact else None
        current = row['user_group'] or row['auto_group']
        proposed, reason = current, row['auto_reason']
        target = {'music':'music','non_music':'rest'}.get(label.get('manual_label'))
        conflict = bool(row['user_group'] and target and row['user_group'] != target)
        meta = json.loads(row['metadata_json'])
        if row['user_group']:
            reason = 'manual_conflict' if conflict else 'manual_preserved'
        elif target:
            proposed, reason = target, 'confirmed_review'
        elif label.get('manual_label') in {'uncertain','unavailable'}:
            reason = 'unresolved_review'
        elif row['channel_key'] in channels:
            reason = 'channel_decision_preserved'
        elif meta.get('takeout_shorts_url') is True or SHORT.search(row['title']):
            reason = 'shorts_review'
        elif TUTORIAL.search(row['title']):
            reason = 'ambiguous_tutorial'
        elif TALK.search(row['title']):
            reason = 'talk_review'
        elif typ in STRONG:
            proposed, reason = 'music', 'ytmusic_strong'
        elif typ == 'MUSIC_VIDEO_TYPE_UGC' and row['watch_days'] >= 3:
            proposed, reason = 'music', 'ytmusic_ugc_recurrence'
        elif EXTRA.search(row['title']):
            reason = 'additional_title_hint'
        items.append(dict(video_id=vid,title=row['title'],channel=row['channel_name'],
            current_group=current,proposed_group=proposed,changed=current != proposed,conflict=conflict,
            reason=reason,watch_count=row['watch_count'],watch_days=row['watch_days'],
            evidence=dict(manual_group=row['user_group'],label=label.get('manual_label',''),
                label_notes=label.get('notes',''),metadata_exact=exact,music_video_type=typ,
                observation_id=observation.get('id'),run_id=observation.get('run_id'),
                fetched_at=payload.get('fetched_at'),metadata_status=payload.get('status','not_fetched'),
                additional_title_hint=bool(EXTRA.search(row['title'])))))
    state = dict(videos=[dict(r) for r in videos], channels=channels, events=[list(r) for r in db.execute('SELECT * FROM watch_events WHERE import_id=? ORDER BY source_row',(active,))])
    state_hash = hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return dict(state_sha256=state_hash,version=VERSION,created_at=datetime.now(timezone.utc).isoformat(),source_hash=source_hash,
        import_id=active,min_watch_days=3,mode='preview_only',
        inputs_sha256=dict(labels=hashlib.sha256(labels_bytes).hexdigest(),metadata=hashlib.sha256(metadata_bytes).hexdigest()),
        current_totals={g:sum(r['current_group']==g for r in items) for g in ('music','rest')},
        proposed_totals={g:sum(r['proposed_group']==g for r in items) for g in ('music','rest')},
        changed=sum(r['changed'] for r in items),conflicts=sum(r['conflict'] for r in items),items=items)



def apply_preview(db, plan, labels_path, metadata_path):
    """Recompute under a write lock; never trust editable proposal rows as commands."""
    with transaction(db):
        assert_review_unlocked(db)
        fresh = build_preview(db, labels_path, metadata_path)
        stable = lambda value: {k:v for k,v in value.items() if k != 'created_at'}
        if stable(plan) != stable(fresh):
            raise ValueError('Preview đã cũ hoặc bị sửa; tạo preview mới trước khi áp dụng.')
        run_id = start_run(db,'classification_apply',fresh['import_id'],VERSION,
            dict(state_sha256=fresh['state_sha256'],inputs_sha256=fresh['inputs_sha256']))
        for item in fresh['items']:
            if not item['changed']:
                continue
            vid = item['video_id']
            if item['reason'] == 'confirmed_review':
                set_video_group(db,vid,item['proposed_group'])
            else:
                row = db.execute('SELECT metadata_json FROM videos WHERE id=?',(vid,)).fetchone()
                metadata = json.loads(row[0])
                metadata['applied_music_evidence'] = dict(item['evidence'],source_hash=fresh['source_hash'])
                evidence = [dict(code=item['reason'],source='approved_local_preview',**item['evidence'])]
                db.execute('UPDATE videos SET auto_group=?,auto_reason=?,metadata_json=?,evidence_json=? WHERE id=?',
                    (item['proposed_group'],item['reason'],json.dumps(metadata,ensure_ascii=False),json.dumps(evidence,ensure_ascii=False),vid))
            record_event(db,'preview_applied',dict(before_group=item['current_group'],after_group=item['proposed_group'],
                reason=item['reason'],evidence=item['evidence'],inputs_sha256=fresh['inputs_sha256']),run_id=run_id,video_id=vid)
        finish_run(db,run_id,'completed',changed=fresh['changed'],conflicts=fresh['conflicts'])
        return dict(run_id=run_id,changed=fresh['changed'],conflicts=fresh['conflicts'],totals=fresh['proposed_totals'])
