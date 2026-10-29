import json
import hashlib
import io
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from package_ione_colab import package, notebook_cells, upload_cell_source
from train_ione_sft import smoke_rows


class ColabPackageTests(unittest.TestCase):
    def test_renamed_upload_extracts_verified_bytes_and_preserves_previous_run(self):
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, 'w') as archive:
            archive.writestr('bundle/manifest.json', '{"verified": true}')
        data = blob.getvalue()
        fake_colab = types.ModuleType('google.colab')
        fake_colab.files = types.SimpleNamespace(upload=lambda: {'ione_colab_bundle (2).zip': data})
        source = upload_cell_source(hashlib.sha256(data).hexdigest())
        original_mkdtemp = tempfile.mkdtemp
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules, {'google.colab': fake_colab}), patch('tempfile.mkdtemp',
                    side_effect=lambda **kw: original_mkdtemp(prefix=kw['prefix'], dir=directory)):
                first = {}; exec(source, first)
                second = {}; exec(source, second)
            self.assertNotEqual(first['root'], second['root'])
            for state in (first, second):
                self.assertEqual((state['root'] / 'bundle/manifest.json').read_text(), '{"verified": true}')
        fake_colab.files.upload = lambda: {'ione_colab_bundle.zip': b'wrong content'}
        with patch.dict(sys.modules, {'google.colab': fake_colab}):
            with self.assertRaisesRegex(AssertionError, 'hash'):
                exec(source, {})

    def test_notebook_python_cells_compile(self):
        for index, cell in enumerate(notebook_cells('0' * 64)):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell{index}', 'exec')

    def test_mechanics_fixtures_are_separate(self):
        rows = smoke_rows()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({r['prompt'][-1]['content'] for r in rows}), 16)
        self.assertTrue(all('TEST-' in r['prompt'][-1]['content'] for r in rows))

    def test_package_allowlist_and_frozen_exports(self):
        from test_sft_preflight import FrozenBundleTests
        from preflight_ione_sft import verify_bundle
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'input'; bundle.mkdir()
            fixture = FrozenBundleTests()
            manifest = fixture.make_bundle(bundle)
            manifest['heldout_sha256'] = '0' * 64
            fixture.save_manifest(bundle, manifest)
            (bundle / 'PRIVATE_CV.txt').write_text('must not ship')
            output = root / 'output'; inventory = package(bundle, output)
            expected = {'Tools/train_ione_sft.py', 'Tools/ione_tokenizer_smoke.py', 'Tools/ione_data_pipeline.py',
                        'Tools/preflight_ione_sft.py', 'requirements-m6-colab.txt', 'source_revision.json', 'bundle/manifest.json',
                        'bundle/sft_train.jsonl', 'bundle/sft_dev.jsonl',
                        'bundle/sft_train_canonical.jsonl', 'bundle/sft_dev_canonical.jsonl'}
            self.assertEqual(set(inventory), expected)
            with zipfile.ZipFile(output / 'ione_colab_bundle.zip') as archive:
                self.assertEqual(set(archive.namelist()), expected)
                extracted = root / 'extracted'; archive.extractall(extracted)
            self.assertEqual(len(verify_bundle(extracted / 'bundle')[1]), 2)
            book = json.loads((output / 'Ione_Free_GPU_Trial.ipynb').read_text(encoding='utf-8'))
            self.assertTrue(all(not c.get('outputs') for c in book['cells']))
            with self.assertRaisesRegex(ValueError, 'new output'):
                package(bundle, output)
