"""Explainable local music suggestions."""

import json
import re

from .storage import get_setting, transaction, assert_review_unlocked
from .audit import start_run, record_event, finish_run

RULE_VERSION = 'rules-v2-applied-metadata'
TOPIC = re.compile(r'\S.*\s[-–—]\s*topic\s*$', re.I)
MUSIC = re.compile(r'(?<!\w)(?:amv|ost|cover|remix|bgm|music|instrumental|piano|slowed|reverb)(?!\w)|nhạc|歌ってみた|カバー|노래', re.I)
TALK = re.compile(r'(?<!\w)(?:podcast|interview|gameplay|walkthrough|vlog|reaction|tutorial)(?!\w)|phỏng vấn|hướng dẫn', re.I)


def suggest(*, title='', channel_name='', metadata=None, watch_count=0, watch_days=0, channel_decision=None):
    metadata = metadata or {}
    evidence = []

    def add(code, source, **details):
        evidence.append(dict(code=code, source=source, **details))

    topic = bool(TOPIC.search(channel_name or ''))
    library = metadata.get('music_library') is True
    shorts = metadata.get('takeout_shorts_url') is True
    talk = bool(TALK.search(title))
    hint = bool(MUSIC.search(title))
    if topic:
        add('topic_channel', 'takeout.channel_name')
    if library:
        add('music_library', 'takeout.music_library')
    if shorts:
        add('shorts_url', 'takeout.history_url')
    if talk:
        add('talk_context', 'title.regex', strength='weak')
    if hint:
        add('music_hint', 'title.regex', strength='weak')
    if (channel_name or '').casefold().endswith('vevo'):
        add('vevo', 'takeout.channel_name', strength='weak')
    if watch_count >= 3:
        add('repeat_views', 'takeout.watch_count', count=watch_count, strength='weak')
    group, reason = 'rest', 'unknown'
    if channel_decision:
        add('channel_decision', channel_decision['source'], reason=channel_decision['reason'])
    if shorts:
        reason = 'shorts_url'
    elif channel_decision:
        group, reason = channel_decision['group_name'], 'channel_decision'
    elif talk and (topic or library or hint):
        reason = 'conflicting_evidence'
    elif talk:
        reason = 'talk_context'
    elif topic or library:
        group, reason = 'music', 'topic_channel' if topic else 'music_library'
    elif hint:
        reason = 'music_hint'
    applied = metadata.get('applied_music_evidence', {})
    if (group == 'rest' and reason in {'unknown','music_hint'} and not channel_decision
            and not re.search(r'#shorts?\b|\bhow to\b|\blesson\b',title,re.I)):
        typ = applied.get('music_video_type')
        if applied.get('metadata_exact') is True:
            if typ in {'MUSIC_VIDEO_TYPE_ATV','MUSIC_VIDEO_TYPE_OMV','MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC'}:
                group,reason = 'music','ytmusic_strong'
            elif typ == 'MUSIC_VIDEO_TYPE_UGC' and watch_days >= 3:
                group,reason = 'music','ytmusic_ugc_recurrence'
            if group == 'music':
                add(reason,'approved_local_preview',observation=applied)
    return dict(group=group, reason=reason, evidence=evidence)


def classify_import(db, import_id):
    """Update suggestions within the caller's transaction; never write user_group."""
    rows = db.execute(
        'SELECT v.*, COUNT(*) AS watch_count, COUNT(DISTINCT date(e.watched_at)) AS watch_days FROM videos v JOIN watch_events e ON e.video_id=v.id '
        'WHERE e.import_id=? GROUP BY v.id', (import_id,)
    ).fetchall()
    channels = {row['channel_key']: dict(row) for row in db.execute('SELECT * FROM channel_decisions')}
    run_id = start_run(db, 'classification', import_id, RULE_VERSION, {'feature_version':'rules-v1-inputs'})
    counts = {'music': 0, 'rest': 0}
    for row in rows:
        metadata = json.loads(row['metadata_json'])
        result = suggest(title=row['title'], channel_name=row['channel_name'],
                         metadata=metadata, watch_count=row['watch_count'], watch_days=row['watch_days'],
                         channel_decision=channels.get(row['channel_key']))
        record_event(db, 'classification_decided', dict(
            rule_version=RULE_VERSION,
            features=dict(title=row['title'], channel_name=row['channel_name'],
                          metadata=metadata, watch_count=row['watch_count'], watch_days=row['watch_days'],
                          channel_decision=channels.get(row['channel_key'])),
            before_group=row['auto_group'], before_reason=row['auto_reason'],
            after_group=result['group'], after_reason=result['reason'], evidence=result['evidence'],
            user_group=row['user_group'], effective_group=row['user_group'] or result['group'],
        ), run_id=run_id, video_id=row['id'])
        db.execute('UPDATE videos SET auto_group=?, auto_reason=?, evidence_json=? WHERE id=?',
                   (result['group'], result['reason'], json.dumps(result['evidence'], ensure_ascii=False), row['id']))
        counts[row['user_group'] or result['group']] += 1
    finish_run(db, run_id, 'completed', counts=counts)
    return dict(rule_version=RULE_VERSION, counts=counts, run_id=run_id)


def classify_active(db):
    with transaction(db):
        assert_review_unlocked(db)
        active = get_setting(db, 'active_import')
        if active is None:
            raise ValueError('Chưa có lịch sử; hãy import Takeout trước.')
        return classify_import(db, int(active))
