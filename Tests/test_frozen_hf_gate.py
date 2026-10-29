import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from eval_ione_frozen_hf import load_frozen


class FrozenHFGateTests(unittest.TestCase):
    def test_freeze_and_persona_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = {'case_id':'one', 'scenario_family_id':'family', 'split':'frozen_test', 'context':{}, 'history':[], 'question':'What is known?'}
            raw = (json.dumps(case)+'\n').encode(); bible = b'{"character":{},"persona":[]}'
            (root/'eval_set_v1.jsonl').write_bytes(raw); (root/'character_bible.json').write_bytes(bible)
            manifest = {'status':'approved_frozen','eval_set_sha256':hashlib.sha256(raw).hexdigest(),
                        'persona_sha256':hashlib.sha256(bible).hexdigest(),'approval_reference':'用户批准冻结','case_count':1}
            path = root/'freeze_manifest_v1.json'; path.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
            self.assertEqual(len(load_frozen(root)[0]), 1)
            (root/'character_bible.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'mismatch'): load_frozen(root)
            (root/'character_bible.json').write_bytes(bible)
            manifest['approval_reference']=''; path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'mismatch'): load_frozen(root)
