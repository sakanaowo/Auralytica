"""Explainable local candidate grouping; suggestions never exclude downloads."""
from collections import defaultdict
import hashlib
import json
import re
import unicodedata
import uuid

from .audit import record_event
from .storage import (RevisionConflict, assert_review_unlocked, get_setting,
                      set_setting, transaction)


VERSION = 'title-alias-v1'
MARKERS = ('cover', 'live', 'remix', 'slowed', 'instrumental', 'reverb', 'acoustic')
PRESENTATION = re.compile(
    r'\s*[\[(]?(?:official\s+(?:music\s+)?video|official\s+audio|lyrics?|lyric\s+video|visualizer|m/?v)[\])]?$'
    r'|\s*[-–—:]?\s*(?:' + '|'.join(MARKERS) + r')\s*$', re.I)


def normalize_title(title):
    raw = title if isinstance(title, str) else ''
    folded = unicodedata.normalize('NFKC', raw).casefold().strip()
    markers = sorted({marker for marker in MARKERS if re.search(rf'(?<!\w){marker}(?!\w)', folded)})
    base = folded
    while True:
        cleaned = PRESENTATION.sub('', base).strip()
        if cleaned == base:
            break
        base = cleaned
    key = re.sub(r'[^\w]+', ' ', base, flags=re.UNICODE).strip()
    key = re.sub(r'\s+', ' ', key)
    return dict(raw=raw, key=key, markers=markers)


def confirm_aliases(db, aliases, *, source='user', artist_scope=None):
    if not isinstance(aliases, (list, tuple)) or not 2 <= len(aliases) <= 20:
        raise ValueError('Cần từ 2 đến 20 alias.')
    normalized = [(alias, normalize_title(alias)['key']) for alias in aliases
                  if isinstance(alias, str) and normalize_title(alias)['key']]
    if len({key for _, key in normalized}) < 2:
        raise ValueError('Cần ít nhất hai alias khác nhau.')
    with transaction(db):
        assert_review_unlocked(db)
        requested = {key for _, key in normalized}
        existing = defaultdict(set)
        for row in db.execute('SELECT song_key,normalized_alias FROM song_aliases WHERE confirmed=1 '
                              'AND COALESCE(artist_scope,\'\')=COALESCE(?,\'\')', (artist_scope,)):
            existing[row['song_key']].add(row['normalized_alias'])
        reused = next((key for key, values in existing.items() if requested <= values), None)
        if reused:
            return dict(song_key=reused, aliases=[alias for alias, _ in normalized], source=source,
                        artist_scope=artist_scope, reused=True)
        song_key = uuid.uuid4().hex
        db.executemany('INSERT INTO song_aliases(song_key,alias,normalized_alias,artist_scope,source) '
                       'VALUES(?,?,?,?,?)',
                       [(song_key, alias[:1024], key, artist_scope, source) for alias, key in normalized])
    return dict(song_key=song_key, aliases=[alias for alias, _ in normalized], source=source,
                artist_scope=artist_scope, reused=False)


def confirm_video_aliases(db, video_ids, *, artist_scope=None):
    if not isinstance(video_ids, (list, tuple)) or not 2 <= len(video_ids) <= 20:
        raise ValueError('Cần từ 2 đến 20 video ID.')
    active, rows = _active_music(db)
    by_id = {row['id']: row for row in rows}
    if len(set(video_ids)) != len(video_ids) or not set(video_ids) <= set(by_id):
        raise ValueError('Video ghép alias phải là các video nhạc khác nhau trong lịch sử đang mở.')
    result = confirm_aliases(db, [by_id[video_id]['title'] for video_id in video_ids],
                             source='user_video_merge', artist_scope=artist_scope)
    result['video_ids'] = list(video_ids)
    result['import_id'] = active
    return result


def _active_music(db):
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Hãy import Takeout trước.')
    rows = db.execute(
        "SELECT v.* FROM videos v WHERE COALESCE(v.user_group,v.auto_group)='music' AND v.id IN "
        '(SELECT video_id FROM watch_events WHERE import_id=?) ORDER BY v.id', (active,)).fetchall()
    return int(active), rows


def _input(db):
    active, rows = _active_music(db)
    aliases = [tuple(row) for row in db.execute(
        'SELECT song_key,normalized_alias,COALESCE(artist_scope,\'\'),source,confirmed '
        'FROM song_aliases ORDER BY song_key,normalized_alias,id')]
    payload = dict(active=active, videos=[(row['id'], row['title'], row['channel_name']) for row in rows],
                   aliases=aliases)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return active, rows, aliases, digest


def create_run(db):
    with transaction(db):
        assert_review_unlocked(db)
        active, rows, aliases, input_hash = _input(db)
        alias_keys = defaultdict(list)
        for song_key, normalized, artist, source, confirmed in aliases:
            if confirmed:
                alias_keys[normalized].append((song_key, artist, source))
        buckets = defaultdict(list)
        for row in rows:
            normalized = normalize_title(row['title'])
            if len(normalized['key']) < 3:
                continue
            matches = alias_keys.get(normalized['key'], [])
            song_keys = {match[0] for match in matches}
            match = matches[0] if len(song_keys) == 1 else None
            anchor = ('alias', match[0]) if match else ('title', normalized['key'])
            buckets[anchor].append((row, normalized, match))
        run_id = uuid.uuid4().hex
        db.execute('INSERT INTO dedup_runs(id,import_id,input_hash,algorithm_version) VALUES(?,?,?,?)',
                   (run_id, active, input_hash, VERSION))
        for (kind, anchor), members in sorted(buckets.items()):
            if len(members) < 2:
                continue
            ids = sorted(row['id'] for row, _, _ in members)
            fingerprint = hashlib.sha256(json.dumps([kind, anchor, ids]).encode()).hexdigest()
            if db.execute('SELECT 1 FROM rejected_groups WHERE fingerprint=?', (fingerprint,)).fetchone():
                continue
            channels = {(row['channel_name'] or '').casefold() for row, _, _ in members if row['channel_name']}
            conflict = len(channels) > 1
            group_id = uuid.uuid4().hex
            title_key = (members[0][1]['key'] if kind == 'title' else
                         ' / '.join(dict.fromkeys(normalized['key'] for _, normalized, _ in members)))
            db.execute('INSERT INTO dedup_groups(id,run_id,fingerprint,title_key,evidence_type,artist_conflict) '
                       'VALUES(?,?,?,?,?,?)',
                       (group_id, run_id, fingerprint, title_key,
                        'confirmed_alias' if kind == 'alias' else 'normalized_title', conflict))
            for row, normalized, match in members:
                evidence = dict(normalized_title=normalized['key'], source='confirmed_alias' if match else 'title.normalized',
                                alias_source=match[2] if match else None, artist_scope=match[1] if match else None)
                db.execute('INSERT INTO dedup_members(group_id,video_id,evidence_json,version_marker) VALUES(?,?,?,?)',
                           (group_id, row['id'], json.dumps(evidence, ensure_ascii=False),
                            ','.join(normalized['markers']) or None))
        count = db.execute('SELECT COUNT(*) FROM dedup_groups WHERE run_id=?', (run_id,)).fetchone()[0]
        return dict(run_id=run_id, import_id=active, input_hash=input_hash, groups=count,
                    algorithm_version=VERSION, stale=False)


def get_run(db, run_id):
    row = db.execute('SELECT * FROM dedup_runs WHERE id=?', (run_id,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy lượt dedup.')
    _, _, _, current_hash = _input(db)
    return dict(run_id=row['id'], import_id=row['import_id'], input_hash=row['input_hash'],
                algorithm_version=row['algorithm_version'], status=row['status'],
                groups=db.execute('SELECT COUNT(*) FROM dedup_groups WHERE run_id=?', (run_id,)).fetchone()[0],
                stale=current_hash != row['input_hash'])


def latest_run(db):
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Hãy import Takeout trước.')
    row = db.execute('SELECT id FROM dedup_runs WHERE import_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1',
                     (active,)).fetchone()
    return get_run(db, row['id']) if row else None


def selection_revision(db):
    return int(get_setting(db, 'dedup_selection_revision') or 0)


def update_selections(db, video_ids, keep, expected_revision):
    if not isinstance(video_ids, (list, tuple)) or not video_ids or len(video_ids) > 1000:
        raise ValueError('Chọn từ 1 đến 1000 video.')
    if type(keep) is not bool or type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('Selection/revision không hợp lệ.')
    with transaction(db):
        assert_review_unlocked(db)
        current = selection_revision(db)
        if current != expected_revision:
            raise RevisionConflict('Lựa chọn đã đổi ở tab khác; tải lại trước khi lưu.')
        _, rows = _active_music(db)
        available = {row['id'] for row in rows}
        ids = set(video_ids)
        if len(ids) != len(video_ids) or not ids <= available:
            raise ValueError('Mọi video phải thuộc nhóm Nhạc hiện hành.')
        revision = current + 1
        for video_id in video_ids:
            db.execute('INSERT INTO download_selections(video_id,keep,revision) VALUES(?,?,?) '
                       'ON CONFLICT(video_id) DO UPDATE SET keep=excluded.keep,revision=excluded.revision,'
                       'updated_at=CURRENT_TIMESTAMP', (video_id, int(keep), revision))
            record_event(db, 'download_selection_changed',
                         {'keep': keep, 'revision': revision}, video_id=video_id)
        set_setting(db, 'dedup_selection_revision', str(revision))
        return dict(revision=revision, updated=len(video_ids), keep=keep)


def set_group_rejection(db, group_id, rejected, expected_revision):
    if type(rejected) is not bool or type(expected_revision) is not int:
        raise ValueError('Trạng thái từ chối/revision không hợp lệ.')
    with transaction(db):
        assert_review_unlocked(db)
        current = selection_revision(db)
        if current != expected_revision:
            raise RevisionConflict('Lựa chọn đã đổi ở tab khác; tải lại trước khi lưu.')
        group = db.execute('SELECT fingerprint FROM dedup_groups WHERE id=?', (group_id,)).fetchone()
        if group is None:
            raise ValueError('Không tìm thấy nhóm dedup.')
        if rejected:
            db.execute('INSERT OR IGNORE INTO rejected_groups(fingerprint) VALUES(?)', (group['fingerprint'],))
        else:
            db.execute('DELETE FROM rejected_groups WHERE fingerprint=?', (group['fingerprint'],))
        revision = current + 1
        set_setting(db, 'dedup_selection_revision', str(revision))
        record_event(db, 'dedup_group_rejection_changed',
                     {'group_id': group_id, 'fingerprint': group['fingerprint'],
                      'rejected': rejected, 'revision': revision})
        return dict(group_id=group_id, rejected=rejected, revision=revision)


def group_selection(db, group_id, keep, expected_revision):
    rows = db.execute('SELECT video_id FROM dedup_members WHERE group_id=? ORDER BY video_id',
                      (group_id,)).fetchall()
    if not rows:
        raise ValueError('Không tìm thấy nhóm dedup.')
    return update_selections(db, [row['video_id'] for row in rows], keep, expected_revision)


def _member_page(db, group_id, page, page_size):
    total = db.execute('SELECT COUNT(*) FROM dedup_members WHERE group_id=?', (group_id,)).fetchone()[0]
    rows = db.execute(
        'SELECT m.*,v.title,v.channel_name,COALESCE(s.keep,1) AS keep FROM dedup_members m '
        'JOIN videos v ON v.id=m.video_id LEFT JOIN download_selections s ON s.video_id=m.video_id '
        'WHERE m.group_id=? ORDER BY v.id LIMIT ? OFFSET ?',
        (group_id, page_size, (page - 1) * page_size)).fetchall()
    items = [dict(video_id=row['video_id'], raw_title=row['title'], channel=row['channel_name'],
                  version_marker=row['version_marker'], evidence=json.loads(row['evidence_json']),
                  keep=bool(row['keep'])) for row in rows]
    return total, items


def list_members(db, group_id, *, page=1, page_size=50):
    if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError('Phân trang thành viên không hợp lệ.')
    if db.execute('SELECT 1 FROM dedup_groups WHERE id=?', (group_id,)).fetchone() is None:
        raise ValueError('Không tìm thấy nhóm dedup.')
    total, items = _member_page(db, group_id, page, page_size)
    return dict(group_id=group_id, items=items, total=total, page=page,
                page_size=page_size, selection_revision=selection_revision(db))


def list_groups(db, run_id, *, page=1, page_size=20):
    run = get_run(db, run_id)
    if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError('Phân trang dedup không hợp lệ.')
    total = run['groups']
    groups = db.execute('SELECT * FROM dedup_groups WHERE run_id=? ORDER BY evidence_type,id LIMIT ? OFFSET ?',
                        (run_id, page_size, (page - 1) * page_size)).fetchall()
    items = []
    for group in groups:
        member_count, members = _member_page(db, group['id'], 1, 50)
        rejected = db.execute('SELECT 1 FROM rejected_groups WHERE fingerprint=?',
                              (group['fingerprint'],)).fetchone() is not None
        items.append(dict(group_id=group['id'], fingerprint=group['fingerprint'], title_key=group['title_key'],
                          evidence_type=group['evidence_type'], artist_conflict=bool(group['artist_conflict']),
                          rejected=rejected, member_count=member_count, member_page=1,
                          member_page_size=50, members=members))
    return dict(run=run, items=items, total=total, page=page, page_size=page_size,
                selection_revision=selection_revision(db))
