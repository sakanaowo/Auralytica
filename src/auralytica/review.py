"""Shared review operations for CLI and local web."""

import json

from .storage import get_setting, set_video_group, transaction, assert_review_unlocked


def _active_rows(db):
    active = get_setting(db, 'active_import')
    if active is None:
        raise ValueError('Chưa có lịch sử; hãy import Takeout trước.')
    rows = db.execute(
        'SELECT v.*, COUNT(*) AS watch_count, '
        '(SELECT status FROM download_items d WHERE d.video_id=v.id ORDER BY batch_id DESC LIMIT 1) AS download_status '
        'FROM videos v JOIN watch_events e ON e.video_id=v.id WHERE e.import_id=? GROUP BY v.id',
        (active,),
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item['group'] = item['user_group'] or item['auto_group']
        item['decision_source'] = 'user' if item['user_group'] else 'automatic'
        item['reason'] = 'manual' if item['user_group'] else item['auto_reason']
        item['url'] = 'https://www.youtube.com/watch?v=' + item['id']
        item['evidence'] = json.loads(item.pop('evidence_json'))
        item.pop('metadata_json')
        items.append(item)
    return items


def _totals(items):
    return {group: sum(row['group'] == group for row in items) for group in ('music', 'rest')}


def list_videos(db, *, group='music', search='', channel=None, reason=None,
                page=1, page_size=50, sort='watch_count'):
    if group not in {'music', 'rest'}:
        raise ValueError('group phải là music hoặc rest.')
    if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 1000:
        raise ValueError('page >= 1 và page_size trong khoảng 1–1000.')
    if sort not in {'watch_count', 'title', 'channel'}:
        raise ValueError('sort phải là watch_count, title hoặc channel.')
    items = _active_rows(db)
    totals = _totals(items)
    query = search.casefold().strip()
    filtered = [row for row in items if row['group'] == group
                and (not query or query in (row['title'] + ' ' + (row['channel_name'] or '')).casefold())
                and (channel is None or row['channel_key'] == channel)
                and (reason is None or row['reason'] == reason)]
    if sort == 'watch_count':
        filtered.sort(key=lambda row: (-row['watch_count'], row['id']))
    else:
        field = 'title' if sort == 'title' else 'channel_name'
        filtered.sort(key=lambda row: ((row[field] or '').casefold(), row['id']))
    start = (page - 1) * page_size
    return dict(items=filtered[start:start + page_size], filtered_count=len(filtered),
                group_totals=totals, page=page, page_size=page_size)


def move_videos(db, video_ids, to_group):
    if to_group not in {'music', 'rest'}:
        raise ValueError('to_group phải là music hoặc rest.')
    if not isinstance(video_ids, (list, tuple)) or not video_ids or len(video_ids) > 1000:
        raise ValueError('Chọn từ 1 đến 1000 video mỗi lần chuyển.')
    if not all(isinstance(value, str) for value in video_ids):
        raise ValueError('Video ID phải là chuỗi.')
    ids = set(video_ids)
    with transaction(db):
        assert_review_unlocked(db)
        items = _active_rows(db)
        available = {row['id'] for row in items}
        if not ids <= available:
            raise ValueError('Có video ID không thuộc lịch sử đang xem; chưa chuyển video nào.')
        for video_id in ids:
            set_video_group(db, video_id, to_group)
        for row in items:
            if row['id'] in ids:
                row['group'] = to_group
        return dict(moved=len(ids), to_group=to_group, group_totals=_totals(items))
