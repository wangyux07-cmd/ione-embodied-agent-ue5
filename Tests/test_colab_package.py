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
    def run_combined_flow(self, fail_pilot):
        source = ''.join(notebook_cells('0' * 64, with_dev_eval=True)[5]['source'])
        commands = []; downloads = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bundle').mkdir()
            (root / 'bundle/sft_dev_canonical.jsonl').write_text('fixture')
            class Process:
                def __init__(self, command, **kwargs):
                    commands.append(command)
                    phase = command[command.index('--phase') + 1] if '--phase' in command else 'evaluation'
                    self.failed = fail_pilot and phase == 'pilot'
                    self.stdout = iter([phase + '\n'])
                    if not self.failed:
                        output = Path(command[command.index('--output') + 1])
                        output.mkdir(parents=True)
                        (output / 'result.json').write_text('{}')
                        if phase == 'pilot':
                            (output / 'adapter').mkdir()
                            for name in ('adapter_config.json', 'adapter_model.safetensors'):
                                (output / 'adapter' / name).write_text('fixture')
                def wait(self): return int(self.failed)
            namespace = {'root': root, 'sys': types.SimpleNamespace(executable='python'), 'json': json,
                         'subprocess': types.SimpleNamespace(Popen=Process, PIPE=-1, STDOUT=-2, run=lambda *a, **k: None),
                         'files': types.SimpleNamespace(download=downloads.append)}
            with patch('shutil.make_archive', return_value='fixture.zip'):
                if fail_pilot:
                    with self.assertRaisesRegex(RuntimeError, 'pilot'):
                        exec(source, namespace)
                else:
                    exec(source, namespace)
        return commands, downloads

    def test_combined_success_runs_eval_then_downloads(self):
        commands, downloads = self.run_combined_flow(False)
        self.assertEqual(len(commands), 3)
        self.assertTrue(commands[-1][2].endswith('eval_ione_adapter.py'))
        self.assertEqual(commands[1][-2:], ['--precision', 'fp32'])
        self.assertEqual(downloads, ['/content/ione_results.zip'])

    def test_combined_failed_pilot_stops_eval_and_still_downloads_logs(self):
        commands, downloads = self.run_combined_flow(True)
        self.assertEqual(len(commands), 2)
        self.assertFalse(any(c[2].endswith('eval_ione_adapter.py') for c in commands))
        self.assertEqual(downloads, ['/content/ione_results.zip'])

    def test_prior_smoke_requires_passed_matching_bundle(self):
        from test_sft_preflight import FrozenBundleTests
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'input'; bundle.mkdir()
            fixture = FrozenBundleTests(); manifest = fixture.make_bundle(bundle)
            manifest['heldout_sha256'] = '0' * 64; fixture.save_manifest(bundle, manifest)
            package(bundle, root / 'first')
            with zipfile.ZipFile(root / 'first/ione_colab_bundle.zip') as archive:
                manifest_hash = hashlib.sha256(archive.read('bundle/manifest.json')).hexdigest()
            proof = {'phase': 'smoke', 'model': 'Qwen/Qwen3-0.6B', 'checkpoint_reload_passed': True,
                     'optimizer_steps': 3, 'bundle_manifest_sha256': manifest_hash}
            proof_path = root / 'proof.json'; proof_path.write_text(json.dumps(proof))
            inventory = package(bundle, root / 'reused', proof_path)
            self.assertIn('prior_smoke_result.json', inventory)
            for key, value in [('checkpoint_reload_passed', False), ('bundle_manifest_sha256', 'wrong'), ('optimizer_steps', 0)]:
                changed = dict(proof); changed[key] = value
                proof_path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'smoke proof'):
                    package(bundle, root / ('bad_' + key), proof_path)

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
        for mode in (False, True):
            for index, cell in enumerate(notebook_cells('0' * 64, with_dev_eval=mode)):
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
            combined = root / 'combined'
            combined_files = package(bundle, combined, with_dev_eval=True)
            self.assertEqual(set(combined_files), expected | {'Tools/eval_ione_adapter.py'})
            book = json.loads((combined / 'Ione_Free_GPU_Trial.ipynb').read_text(encoding='utf-8'))
            source = ''.join(book['cells'][5]['source'])
            self.assertLess(source.index("run_phase('pilot'"), source.index('evaluation_command ='))
            self.assertLess(source.index('evaluation_command ='), source.index('files.download('))
