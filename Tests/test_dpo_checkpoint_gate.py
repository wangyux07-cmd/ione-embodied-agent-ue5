"""A swapped reference invalidates a DPO increment even when the base model matches."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from eval_ione_dpo import validate_training_identity


class CheckpointGateTests(unittest.TestCase):
    def test_actual_saved_reference_and_policy_required(self):
        with tempfile.TemporaryDirectory() as temp:
            ref=Path(temp)/'reference';ref.write_bytes(b'SFT adapter A')
            policy=Path(temp)/'policy';policy.write_bytes(b'DPO adapter B')
            sft={'model':'model','revision':'pinned'}
            record={'model_id':'model','revision':'pinned','reload_check':'passed','reference_unchanged':True,
                    'source_SFT_adapter_sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),
                    'policy_adapter_sha256':hashlib.sha256(policy.read_bytes()).hexdigest()}
            validate_training_identity(record,sft,ref,policy)
            for path in (ref,policy):
                with self.subTest(path=path.name):
                    original=path.read_bytes();path.write_bytes(b'swapped checkpoint')
                    with self.assertRaises(ValueError):validate_training_identity(record,sft,ref,policy)
                    path.write_bytes(original)
            record['reload_check']='pending'
            with self.assertRaises(ValueError):validate_training_identity(record,sft,ref,policy)


if __name__=='__main__':unittest.main()
