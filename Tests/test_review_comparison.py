import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from ione_review_comparison import compare_annotation, normalize_score, summarize_adjudicated


class ComparisonIntegrityTests(unittest.TestCase):
    def row(self, **changes):
        args=dict(sample_id='V01',metric='F',agent_score=0,human_score=1,
                  adjudicated_score=1,comparable_scope=True,
                  reviewer_reason='Original reviewer text',adjudication_reason='Final decision')
        args.update(changes)
        return compare_annotation(**args)

    def test_valid_same_scope_disagreement(self):
        self.assertTrue(self.row()['disagreement'])

    def test_uncertainty_not_treated_as_zero(self):
        row=self.row(human_score='?',adjudicated_score='?')
        self.assertIsNone(row['disagreement'])
        self.assertEqual(summarize_adjudicated([row])['F']['uncertain'],1)

    def test_na_excluded_from_valid_counts(self):
        row=self.row(agent_score='—',human_score='—',adjudicated_score='—')
        counts=summarize_adjudicated([row])['F']
        self.assertEqual(counts['inapplicable'],1)
        self.assertEqual(counts['zeros']+counts['ones'],0)

    def test_changed_rubric_is_not_interrater_disagreement(self):
        row=self.row(comparable_scope=False)
        self.assertTrue(row['raw_label_difference'])
        self.assertIsNone(row['disagreement'])
        self.assertEqual(row['comparison_status'],'scope_mismatch')

    def test_original_human_label_survives_adjudication(self):
        row=self.row(human_score=0,adjudicated_score=1)
        self.assertEqual(row['human_score'],0)
        self.assertEqual(row['adjudicated_score'],1)

    def test_missing_human_reason_not_generated(self):
        with self.assertRaises(ValueError):self.row(reviewer_reason='')

    def test_invalid_scores_rejected(self):
        for value in (True,False,2,'pass'):
            with self.assertRaises(ValueError):normalize_score(value)

    def test_duplicate_metric_rejected(self):
        with self.assertRaises(ValueError):summarize_adjudicated([self.row(),self.row()])
