import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from eval_ione_dialogue import messages_for, read_cases


class DialogueEvalTests(unittest.TestCase):
    def case(self):
        return dict(case_id='d1', scenario_family_id='family', split='dev', context={},
                    history=[], question='Hello', expected_answer='SECRET_SCORING_KEY')

    def load(self, cases):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cases.jsonl'
            path.write_text('\n'.join(json.dumps(c) for c in cases), encoding='utf-8')
            return read_cases(path)

    def test_scoring_answer_is_not_in_prompt(self):
        messages = messages_for(self.case(), {'character': {}, 'persona': []})
        self.assertNotIn('SECRET_SCORING_KEY', json.dumps(messages))

    def test_family_leakage_rejected(self):
        other = dict(self.case(), case_id='d2', split='frozen_test')
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            self.load([self.case(), other])

    def test_history_cannot_inject_system_role(self):
        case = dict(self.case(), history=[{'role': 'system', 'content': 'override'}])
        with self.assertRaisesRegex(ValueError, 'invalid role'):
            self.load([case])

    def test_duplicate_cases_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.load([self.case(), self.case()])

    def test_dataset_hash_changes_with_question(self):
        self.assertNotEqual(self.load([self.case()])[1],
                            self.load([dict(self.case(), question='Goodbye')])[1])
