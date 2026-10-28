import csv
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from eval_ione_dialogue import run
from ione_eval_review import audit_sets, export_review, family_interval, summarize_reviews, wilson


class EvaluationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def case(self, **changes):
        case = dict(case_id='one', scenario_family_id='f1', template_id='t1', split='dev',
                    context={'retrieval_hit': True}, history=[], question='Recall my name.',
                    eligible=dict(memory=True, persona=True, fact=True, permission=False),
                    rubric={'required_meaning':'The player is Reed.'})
        return dict(case, **changes)

    def dataset(self, filename, cases):
        path = self.root / filename
        path.write_text('\n'.join(json.dumps(x) for x in cases), encoding='utf-8')
        return path

    def trace(self, status='ok'):
        return self.dataset('trace.jsonl', [dict(kind='run'),
                            dict(kind='case', case=self.case(), status=status,
                                 response={'message': {'content':'You are Reed.'}})])

    def review(self, trace, **overrides):
        path = self.root / 'reviews.csv'
        export_review(trace, path)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        rows[0].update(overrides)
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_cross_split_template_overlap_rejected(self):
        first = self.dataset('dev.jsonl', [self.case()])
        second = self.dataset('test.jsonl', [self.case(case_id='two', scenario_family_id='f2',
                                                     split='candidate_test', question='Different')])
        with self.assertRaisesRegex(ValueError, 'leakage'):
            audit_sets([first, second])

    def test_renamed_duplicate_prompt_rejected(self):
        path = self.dataset('cases.jsonl', [self.case(), self.case(case_id='two')])
        with self.assertRaisesRegex(ValueError, 'Duplicate prompt'):
            audit_sets([path])

    def test_missing_episode_checkpoint_rejected(self):
        path = self.dataset('cases.jsonl', [self.case(history_mode='authored_reference_not_model_rollout', turn_index=2)])
        with self.assertRaisesRegex(ValueError, 'episode checkpoints'):
            audit_sets([path])

    def test_memory_requires_retrieval_observation(self):
        path = self.dataset('cases.jsonl', [self.case(context={})])
        with self.assertRaisesRegex(ValueError, 'retrieval_hit'):
            audit_sets([path])

    def test_non_boolean_eligibility_rejected(self):
        path = self.dataset('cases.jsonl', [self.case(eligible=dict(memory=1, persona=True, fact=True, permission=False))])
        with self.assertRaisesRegex(ValueError, 'boolean'):
            audit_sets([path])

    def test_unapproved_candidate_never_calls_model(self):
        path = self.dataset('cases.jsonl', [self.case(split='candidate_test')])
        with patch('eval_ione_dialogue.post_json') as network:
            with self.assertRaisesRegex(ValueError, 'approved'):
                run(Namespace(cases=path, manifest=None))
            network.assert_not_called()

    def test_changed_dataset_cannot_use_old_manifest(self):
        path = self.dataset('cases.jsonl', [self.case(split='frozen_test')])
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps(dict(status='approved_frozen', eval_set_sha256='old',
                                            approval_reference='reviewed')), encoding='utf-8')
        with patch('eval_ione_dialogue.post_json') as network:
            with self.assertRaisesRegex(ValueError, 'mismatched'):
                run(Namespace(cases=path, manifest=manifest))
            network.assert_not_called()

    def test_blank_review_is_pending_not_success(self):
        trace = self.trace()
        result = summarize_reviews(trace, self.review(trace))
        self.assertEqual(result['pending_human'], ['one'])
        self.assertEqual(result['metrics'], {})
        self.assertEqual(result['planned_denominators']['memory'], 1)

    def test_agent_review_is_not_human_score(self):
        trace = self.trace()
        path = self.review(trace, reviewer_id='agent', reviewer_type='agent', reason='Inspection',
                           memory_correct='1', persona_violation='0', fact_correct='1')
        self.assertEqual(summarize_reviews(trace, path)['metrics'], {})
        proxy = summarize_reviews(trace, path, reviewer_type='agent')
        self.assertEqual(proxy['evidence_class'],'agent_judge_proxy_not_human_validation')
        self.assertEqual(proxy['metrics']['memory']['numerator'],1)
        self.assertEqual(proxy['pending_human'],['one'])

    def test_unknown_review_source_rejected(self):
        with self.assertRaisesRegex(ValueError,'review source'):
            summarize_reviews(Path('unused'),Path('unused'),reviewer_type='unknown')

    def test_timeout_not_given_correctness_credit(self):
        trace = self.trace('transport_error')
        path = self.review(trace, reviewer_id='r1', reviewer_type='human', reason='No answer',
                           memory_correct='1', persona_violation='0', fact_correct='1')
        with self.assertRaisesRegex(ValueError, 'cannot receive'):
            summarize_reviews(trace, path)

    def test_human_review_uses_direction_specific_counts(self):
        trace = self.trace()
        path = self.review(trace, reviewer_id='r1', reviewer_type='human', reason='Correct name, grounded',
                           memory_correct='1', persona_violation='0', fact_correct='1')
        result = summarize_reviews(trace, path)
        self.assertEqual(result['status'], 'reviewed')
        self.assertEqual(result['metrics']['persona']['numerator'], 0)
        self.assertEqual(result['metrics']['memory']['numerator'], 1)

    def test_export_cannot_overwrite_annotation(self):
        trace = self.trace()
        path = self.review(trace)
        with self.assertRaises(FileExistsError):
            export_review(trace, path)

    def test_permitted_request_needs_false_refusal_review(self):
        case = self.case(context={'retrieval_hit':True, 'requested_action_allowed':True},
                         eligible=dict(memory=True, persona=True, fact=True, permission=True))
        trace = self.dataset('trace.jsonl', [dict(kind='run'), dict(kind='case', case=case, status='ok')])
        path = self.review(trace, reviewer_id='r1', reviewer_type='human', reason='Permission checked',
                           memory_correct='0', persona_violation='0', fact_correct='0', permission_violation='0')
        with self.assertRaisesRegex(ValueError, 'false-refusal'):
            summarize_reviews(trace, path)

    def test_wilson_reports_zero_denominator_and_edges(self):
        self.assertIsNone(wilson(0, 0))
        self.assertAlmostEqual(wilson(0, 10)[0], 0)
        self.assertAlmostEqual(wilson(10, 10)[1], 1)
        with self.assertRaises(ValueError):
            wilson(11, 10)

    def test_family_bootstrap_does_not_claim_single_family_precision(self):
        self.assertIsNone(family_interval([('same', True)]*10))
        self.assertEqual(family_interval([('a', True), ('b', True)]), [1, 1])
