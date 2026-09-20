import importlib.util
import unittest
import pandas as pd


class ResidualStudyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('notebooks.residual_study'), 'Residual comparison not implemented')
        from notebooks import residual_study
        self.study = residual_study

    def row(self, **kwargs):
        return dict(video_id='test0000001',title='Song',auto_group='rest',proxy_seed=False,
                    content_candidate=False,watch_count=16,watch_days=15,
                    player_status='observed',player_exact_match=True,player_type='MUSIC_VIDEO_TYPE_UGC',
                    category='Music',channel_excluded=False,shorts_explicit=False, **kwargs)

    def test_ugc_gaming_and_no_keyword_repeat_are_candidates_but_talk_is_not(self):
        rows=[]
        for changes in [{}, {'category':'Gaming','content_candidate':True},
                        {'title':'Podcast interview with music','content_candidate':True},
                        {'title':'Game #leaguegameplay OST','content_candidate':True},
                        {'title':'Piano #shorts','content_candidate':True},
                        {'channel_excluded':True}]:
            r=self.row();r.update(changes);rows.append(r)
        out=self.study.hypotheses(pd.DataFrame(rows), min_days=3)
        self.assertEqual(out['ugc_combined'].tolist(), [True,True,False,False,False,False])
        self.assertFalse(out['ugc_content'].iloc[0])

    def test_queue_or_mismatched_player_never_supply_music_type(self):
        rows=[]
        for status,exact in [('not_fetched',False),('id_mismatch',False),('error',False)]:
            r=self.row();r.update(player_status=status,player_exact_match=exact);rows.append(r)
        out=self.study.hypotheses(pd.DataFrame(rows))
        self.assertFalse(out['ugc_combined'].any())

    def test_recurrence_missing_days_and_unplayable_semantics(self):
        r=self.row();r.update(watch_days=None,playability='UNPLAYABLE')
        out=self.study.hypotheses(pd.DataFrame([r]))
        self.assertFalse(out['ugc_recurrence'].iloc[0])
        r.update(player_type='MUSIC_VIDEO_TYPE_ATV',duration_seconds=25)
        self.assertTrue(self.study.hypotheses(pd.DataFrame([r]))['metadata_strong'].iloc[0])

    def test_metrics_require_both_classes_and_report_label_coverage(self):
        labels=pd.Series(['music','','uncertain'])
        predictions=pd.DataFrame({'rule':[True,True,False]})
        out=self.study.evaluate(predictions,labels)
        self.assertFalse(out['can_evaluate'])
        self.assertEqual(out['unlabeled_or_unresolved'],2)
        labels=pd.Series(['music','non_music','music'])
        out=self.study.evaluate(predictions,labels)
        self.assertTrue(out['can_evaluate'])
        metric=out['metrics']['rule']
        self.assertEqual((metric['tp'],metric['fp'],metric['fn'],metric['tn']), (1,1,1,0))

    def test_review_labels_cannot_import_duplicates_unknown_ids_or_wrong_snapshot(self):
        base=pd.DataFrame({'video_id':['test0000001'], 'source_hash':['source'], 'manual_label':['']})
        for review in [pd.DataFrame({'video_id':['other000001'],'source_hash':['source'],'manual_label':['music']}),
                       pd.DataFrame({'video_id':['test0000001'],'source_hash':['wrong'],'manual_label':['music']}),
                       pd.DataFrame({'video_id':['test0000001']*2,'source_hash':['source']*2,'manual_label':['music']*2}),
                       pd.DataFrame({'video_id':['test0000001'],'source_hash':['source'],'manual_label':['yes']})]:
            with self.subTest(review=review.to_dict()),self.assertRaises(ValueError):
                self.study.merge_labels(base,review)

    def test_frozen_cohort_keeps_ids_and_labels_while_updating_metadata(self):
        self.assertTrue(hasattr(self.study,'restore_cohort'), 'Cohort must not change after enrichment')
        frame=pd.DataFrame({'video_id':['a','b','c'],'source_hash':['hash']*3,
                            'player_type':['ATV','UGC',None],'manual_label':['']*3})
        frozen=pd.DataFrame({'video_id':['b','a'],'source_hash':['hash']*2,
                             'sample_reason':['repeat','pilot'],'manual_label':['non_music','music'],
                             'label_source':['manual','user'],'notes':['keep','']})
        actual=self.study.restore_cohort(frame,frozen)
        self.assertEqual(actual.video_id.tolist(),['b','a'])
        self.assertEqual(actual.player_type.tolist(),['UGC','ATV'])
        self.assertEqual(actual.manual_label.tolist(),['non_music','music'])
        with self.assertRaises(ValueError):
            self.study.restore_cohort(frame,frozen.assign(source_hash='wrong'))

    def test_imported_review_notes_survive_reanalysis(self):
        base=pd.DataFrame({'video_id':['a'],'source_hash':['hash'],'manual_label':[''],'notes':['']})
        review=base.assign(manual_label='uncertain',notes='Need to check whether there is speech')
        actual=self.study.merge_labels(base,review)
        self.assertEqual(actual.loc[0,'notes'],review.loc[0,'notes'])
