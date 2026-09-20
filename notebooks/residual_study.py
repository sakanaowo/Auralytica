"""Offline research hypotheses and label validation, not the app classifier."""

import re
import unicodedata
import pandas as pd

VERSION = 'residual-v1'
STRONG = {'MUSIC_VIDEO_TYPE_ATV', 'MUSIC_VIDEO_TYPE_OMV', 'MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC'}
TALK = re.compile(r'podcast|interview|gameplay|walkthrough|tutorial|reaction|talk\s?show|'
                  r'phỏng vấn|tâm sự|hướng dẫn|review phim|kể chuyện|#funny|#memes|#comment|#threads', re.I)
SHORT = re.compile(r'#shorts?\b|#gamingshorts\b|#lolshorts\b', re.I)


def restore_cohort(frame, frozen):
    """Update features on a fixed discovery cohort without selecting new subjects."""
    if not {'video_id','source_hash','sample_reason'} <= set(frozen.columns):
        raise ValueError('Frozen cohort needs ID, source hash and sampling reason')
    if frozen.video_id.duplicated().any() or frame.video_id.duplicated().any():
        raise ValueError('Duplicate cohort/feature IDs')
    if not set(frozen.video_id) <= set(frame.video_id):
        raise ValueError('Frozen cohort contains unknown IDs')
    selected = frame.set_index('video_id').loc[frozen.video_id].reset_index()
    if not selected.source_hash.reset_index(drop=True).equals(frozen.source_hash.reset_index(drop=True)):
        raise ValueError('Frozen cohort source snapshot mismatch')
    for column in ['sample_reason','manual_label','label_source','notes']:
        if column in frozen:
            selected[column] = frozen[column].fillna('').to_numpy()
    return selected


def hypotheses(frame, min_days=3):
    """Masks are candidate-selection experiments, never calibrated probabilities."""
    if type(min_days) is not int or min_days < 1:
        raise ValueError('min_days must be a positive integer')
    titles = frame['title'].fillna('').map(lambda x: unicodedata.normalize('NFKC', str(x)))
    def flag(name):
        return frame[name].fillna(False).eq(True)
    talk = titles.str.contains(TALK)
    short = flag('shorts_explicit') | titles.str.contains(SHORT)
    blocked = flag('channel_excluded') | talk | short
    exact = frame['player_status'].eq('observed') & flag('player_exact_match')
    ugc = exact & frame['player_type'].eq('MUSIC_VIDEO_TYPE_UGC')
    strong = (flag('proxy_seed') | (exact & frame['player_type'].isin(STRONG))) & ~blocked
    repeat = pd.to_numeric(frame['watch_days'], errors='coerce').ge(min_days) & pd.to_numeric(frame['watch_count'], errors='coerce').ge(min_days)
    content = flag('content_candidate')
    result = pd.DataFrame(index=frame.index)
    result['baseline'] = frame['auto_group'].eq('music')
    result['metadata_strong'] = strong
    result['ugc_content'] = strong | (ugc & content & ~blocked)
    result['ugc_recurrence'] = strong | (ugc & repeat & ~blocked)
    result['ugc_combined'] = strong | (ugc & (content | repeat) & ~blocked)
    result['repeat_alone_diagnostic'] = repeat
    result['talk_candidate'] = talk
    result['short_candidate'] = short
    result['guarded_for_review'] = blocked
    return result


def evaluate(predictions, labels):
    """Only labelled rows count. Discovery metrics must not be reported as population accuracy."""
    if not predictions.index.equals(labels.index):
        raise ValueError('Prediction/label index mismatch')
    resolved = labels.isin(['music', 'non_music'])
    classes = set(labels[resolved])
    result = dict(can_evaluate=classes == {'music','non_music'}, labelled=int(resolved.sum()),
                  unlabeled_or_unresolved=int((~resolved).sum()), metrics={})
    if not result['can_evaluate']:
        return result
    target = labels[resolved].eq('music')
    for name in predictions:
        predicted = predictions.loc[resolved, name].eq(True)
        tp, fp = int((predicted & target).sum()), int((predicted & ~target).sum())
        fn, tn = int((~predicted & target).sum()), int((~predicted & ~target).sum())
        result['metrics'][name] = dict(tp=tp, fp=fp, fn=fn, tn=tn,
            precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None)
    return result


def merge_labels(base, review):
    required = {'video_id','source_hash','manual_label'}
    if not required <= set(review.columns) or review['video_id'].duplicated().any():
        raise ValueError('Review must contain unique IDs, source_hash and manual_label')
    if not set(review['video_id']) <= set(base['video_id']):
        raise ValueError('Review contains IDs outside this discovery cohort')
    expected = base.set_index('video_id')['source_hash']
    if any(expected.loc[r.video_id] != r.source_hash for r in review.itertuples()):
        raise ValueError('Source snapshot mismatch')
    labels = review['manual_label'].fillna('')
    if not labels.isin(['','music','non_music','uncertain','unavailable']).all():
        raise ValueError('Unknown manual label')
    result = base.copy().set_index('video_id')
    for index, row in review.iterrows():
        label = labels.loc[index]
        if label:
            result.loc[row['video_id'], 'manual_label'] = label
            result.loc[row['video_id'], 'label_source'] = 'manual_review'
        if 'notes' in review:
            result.loc[row['video_id'], 'notes'] = row['notes'] if pd.notna(row['notes']) else ''
    return result.reset_index()


def render_review(review, priority_count=12):
    """Self-contained label editor; export only edited rows for merge_labels."""
    import hashlib
    import json
    from pathlib import Path

    columns = ['video_id', 'title', 'channel_name', 'source_hash',
               'manual_label', 'label_source', 'notes']
    data = review[columns].fillna('').to_dict(orient='records')
    # Escape HTML parser delimiters even though the payload is non-executable JSON.
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    key = hashlib.sha256(payload.encode()).hexdigest()
    template = Path(__file__).with_name('review_template.html').read_text()
    return (template.replace('__REVIEW_KEY__', key)
            .replace('__PRIORITY_COUNT__', str(min(priority_count, len(data))))
            .replace('__REVIEW_DATA__', payload))
