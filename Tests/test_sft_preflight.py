import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from preflight_ione_sft import verify_bundle


class FrozenBundleTests(unittest.TestCase):
    def make_bundle(self, root):
        hashes = {}
        for split in ('train', 'dev'):
            row = dict(sample_id=split, family_id=split, template_id=split, split=split, kind='sft',
                       prompt=[{'role': 'system', 'content': 'Reply from verified facts.'},
                               {'role': 'user', 'content': 'How many?'}], completion='Three.',
                       context={'facts': {'count': 3}}, target_claims=[{'key': 'facts.count', 'value': 3}],
                       evidence={'source': 'synthetic fixture', 'snapshot_id': split}, tags=['fact'],
                       review_status='approved_human', review_source={'type': 'human', 'reference': 'test review'})
            payload = {'prompt': row['prompt'], 'completion': [{'role': 'assistant', 'content': 'Three.'}]}
            for name, value in ((f'sft_{split}_canonical.jsonl', row), (f'sft_{split}.jsonl', payload)):
                path = root / name
                path.write_text(json.dumps(value) + '\n', encoding='utf-8')
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {'status': 'approved_frozen', 'counts': {'SFT_train': 1, 'SFT_dev': 1}, 'files_sha256': hashes}
        self.save_manifest(root, manifest)
        return manifest

    def save_manifest(self, root, manifest):
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_valid_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.make_bundle(root)
            self.assertEqual(len(verify_bundle(root)[1]), 2)

    def test_payload_changed_after_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.make_bundle(root)
            (root / 'sft_train.jsonl').write_text('{}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_bundle(root)

    def test_export_disagrees_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = self.make_bundle(root)
            path = root / 'sft_train.jsonl'; path.write_text('{}\n', encoding='utf-8')
            manifest['files_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.save_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, 'differs'):
                verify_bundle(root)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = self.make_bundle(root)
            manifest['files_sha256']['../escape.json'] = 'invalid'
            self.save_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                verify_bundle(root)

    def test_pending_bundle_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = self.make_bundle(root)
            manifest['status'] = 'pending'; self.save_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, 'not approved'):
                verify_bundle(root)

    def test_missing_hash_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = self.make_bundle(root)
            del manifest['files_sha256']['sft_train.jsonl']; self.save_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, 'omits'):
                verify_bundle(root)
