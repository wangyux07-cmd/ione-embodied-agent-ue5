"""Exercise the private runtime packet contract with synthetic fixture artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from package_ione_runtime_colab import build


class RuntimePackageTests(unittest.TestCase):
    def test_package_imports_hashes_and_compiles_without_running_training(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sft=root/'sft';dpo=root/'dpo';sft.mkdir();dpo.mkdir()
            for path,value in [(sft,b'fixture SFT'),(dpo,b'fixture DPO')]:
                (path/'adapter_model.safetensors').write_bytes(value)
                (path/'adapter_config.json').write_text('{}')
            a={'model':'fixture','revision':'fixture','checkpoint_reload_passed':True}
            b={'model_id':'fixture','revision':'fixture','reload_check':'passed','reference_unchanged':True,
               'source_SFT_adapter_sha256':hashlib.sha256(b'fixture SFT').hexdigest(),
               'policy_adapter_sha256':hashlib.sha256(b'fixture DPO').hexdigest()}
            ar=root/'sft_result.json';br=root/'dpo_result.json'
            ar.write_text(json.dumps(a));br.write_text(json.dumps(b))
            build(ar,br,sft,dpo,root/'packet')
            with zipfile.ZipFile(root/'packet/ione_runtime_bundle.zip') as z:
                manifest=json.loads(z.read('manifest.json'))
                for name,expected in manifest['files_sha256'].items():
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),expected)
                self.assertFalse(any(n.startswith(('Reports/','Docs/','DevNotes/')) for n in z.namelist()))
                z.extractall(root/'extracted')
                compile(z.read('run_runtime.py'),'run_runtime.py','exec')
            book=json.loads((root/'packet/Ione_M8_Runtime.ipynb').read_text(encoding='utf-8'))
            for cell in book['cells']:
                if cell['cell_type']=='code':compile(''.join(cell['source']),'cell','exec')
            probe=subprocess.run([sys.executable,'-c',
                "import sys;sys.path.insert(0,'Tools');import serve_ione_hf,benchmark_ione_runtime;print('imports passed')"],
                cwd=root/'extracted',capture_output=True,text=True,timeout=15)
            self.assertEqual(probe.returncode,0,probe.stderr)
            self.assertIn('imports passed',probe.stdout)
            (dpo/'adapter_model.safetensors').write_bytes(b'swapped weights')
            with self.assertRaises(ValueError):build(ar,br,sft,dpo,root/'invalid')


if __name__=='__main__':unittest.main()
