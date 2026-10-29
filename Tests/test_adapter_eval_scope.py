import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))


class DevEvaluationScopeTests(unittest.TestCase):
    def test_empty_set_rejected_before_model_access(self):
        from eval_ione_adapter import validate_dev_rows
        with self.assertRaisesRegex(ValueError, 'Only approved SFT dev'):
            validate_dev_rows([])

    def test_train_or_unapproved_data_cannot_enter_dev_diagnostic(self):
        from test_data_pipeline import DataContractTests
        from eval_ione_adapter import validate_dev_rows
        row = DataContractTests().sample()
        with self.assertRaisesRegex(ValueError, 'Only approved SFT dev'):
            validate_dev_rows([row])
        row['split'] = 'dev'
        with self.assertRaisesRegex(ValueError, 'Unapproved'):
            validate_dev_rows([row])
        row.update(review_status='approved_human', review_source={'type': 'human', 'reference': 'test'})
        validate_dev_rows([row])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_dev_rows([row, row])
