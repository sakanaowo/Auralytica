import itertools
import json
from pathlib import Path
import tempfile
import unittest

from auralytica import dedup, storage
from auralytica.importer import import_folder


FIXTURE = Path(__file__).parent / 'fixtures' / 'dedup_quality.json'


class DedupQualityTests(unittest.TestCase):
    def test_independent_labels_report_candidate_precision_and_recall(self):
        labels = json.loads(FIXTURE.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            history = root / 'Takeout' / 'history'
            history.mkdir(parents=True)
            rows = []
            for video in labels['videos']:
                row = {
                    'titleUrl': f"https://youtu.be/{video['id']}",
                    'title': f"Watched {video['title']}",
                }
                if video['channel']:
                    row['subtitles'] = [{'name': video['channel']}]
                rows.append(row)
            (history / 'watch-history.json').write_text(
                json.dumps(rows, ensure_ascii=False), encoding='utf-8')

            with storage.open_database(root / 'state.sqlite3') as db:
                import_folder(db, history.parent)
                for video in labels['videos']:
                    storage.set_video_group(db, video['id'], 'music')
                for aliases in labels['confirmed_aliases']:
                    dedup.confirm_aliases(db, aliases, source='quality_fixture_confirmed')

                run = dedup.create_run(db)
                groups = dedup.list_groups(db, run['run_id'], page_size=100)['items']
                predicted = set()
                for group in groups:
                    ids = sorted(member['video_id'] for member in group['members'])
                    predicted.update(itertools.combinations(ids, 2))
                expected = {tuple(sorted(pair)) for pair in labels['positive_pairs']}

                true_positive = predicted & expected
                false_positive = predicted - expected
                false_negative = expected - predicted
                precision = len(true_positive) / len(predicted)
                recall = len(true_positive) / len(expected)

                self.assertEqual(false_positive, {('qa000000007', 'qa000000008')})
                self.assertEqual(false_negative, {('qa000000009', 'qa000000010')})
                self.assertEqual((len(true_positive), len(predicted), len(expected)), (4, 5, 5))
                self.assertEqual((precision, recall), (0.8, 0.8))

                live_group = next(group for group in groups
                                  if {'qa000000005', 'qa000000006'} <=
                                  {member['video_id'] for member in group['members']})
                markers = {member['video_id']: member['version_marker']
                           for member in live_group['members']}
                self.assertEqual(markers['qa000000005'], 'live')
                self.assertIsNone(markers['qa000000006'])
                self.assertTrue(all(member['keep'] for member in live_group['members']))

                print(json.dumps({
                    'fixture': str(FIXTURE.relative_to(Path(__file__).parents[1])),
                    'scope': 'same-song review candidates; no automatic exclusion',
                    'videos': len(labels['videos']),
                    'expected_positive_pairs': len(expected),
                    'predicted_pairs': len(predicted),
                    'true_positive': len(true_positive),
                    'false_positive': len(false_positive),
                    'false_negative': len(false_negative),
                    'precision': precision,
                    'recall': recall,
                }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
