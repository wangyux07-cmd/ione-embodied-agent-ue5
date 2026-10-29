"""Build a private upload ZIP and Colab notebook from an approved SFT bundle.

python Tools/package_ione_colab.py --bundle PATH --output NEW_DIRECTORY
Only allowlisted source and four frozen SFT files enter the upload archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from preflight_ione_sft import verify_bundle


def upload_cell_source(archive_hash):
    return f'''from google.colab import files
from pathlib import Path
from io import BytesIO
import hashlib, zipfile, json, tempfile
uploaded = files.upload()
assert len(uploaded) == 1, '请只选择一个训练压缩包'
upload_name, blob = next(iter(uploaded.items()))
assert hashlib.sha256(blob).hexdigest() == '{archive_hash}', '压缩包 hash 不符'
root = Path(tempfile.mkdtemp(prefix='ione_trial_', dir='/content'))
with zipfile.ZipFile(BytesIO(blob)) as archive:
    for item in archive.infolist():
        target = (root / item.filename).resolve()
        assert root.resolve() in target.parents and not item.is_dir(), '非法归档路径'
    archive.extractall(root)
print('上传包校验通过:', upload_name, '→', root)
'''


def notebook_cells(archive_hash, with_dev_eval=False):
    def md(text): return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(True)}
    def code(text): return {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': text.splitlines(True)}
    cells = [md('# Ione · 免费 GPU 训练试跑\n\n1. 菜单「运行时 → 更改运行时类型」选择免费 GPU。\n2. 点击「运行时 → 全部运行」，上传同目录的 `ione_colab_bundle.zip`。\n3. 完成后下载结果；确认文件保存后断开运行时。\n\n预算 $0，不购买套餐。免费 GPU 不可用时停止。数据留在私有会话，不开启共享或发布模型。Notebook 不挂载 Drive。'),
            code("import subprocess\nsubprocess.run(['nvidia-smi'], check=True)\n"),
            code(upload_cell_source(archive_hash)),
            code("import sys\nsubprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(root / 'requirements-m6-colab.txt')], check=True)\n"),
            code('''import torch
assert torch.cuda.is_available(), '没有 CUDA GPU；本次停止，不购买算力'
print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name())
import os
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['WANDB_DISABLED'] = 'true'
print('检查已有 smoke 证明，随后启动 1.7B 一轮 pilot')
'''),
            code('''import shutil, time
results = root / 'results'
results.mkdir(exist_ok=True)
def run_phase(phase, extra=()):
    command = [sys.executable, '-u', str(root / 'Tools/train_ione_sft.py'), '--phase', phase,
               '--bundle', str(root / 'bundle'), '--output', str(results / phase), *extra]
    with (results / (phase + '.log')).open('w') as log:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end=''); log.write(line); log.flush()
        if process.wait():
            raise RuntimeError(phase + ' 失败，见下载包日志；不会自动改配置或租用 GPU')
try:
    prior_smoke = root / 'prior_smoke_result.json'
    if prior_smoke.exists():
        shutil.copy2(prior_smoke, results / 'smoke_result_reused.json')
        print('复用已通过的 0.6B smoke 结果，本次只运行 1.7B pilot')
        smoke_result = prior_smoke
    else:
        run_phase('smoke')
        smoke_result = results / 'smoke/result.json'
    run_phase('pilot', ['--smoke-result', str(smoke_result)])
    print('完成。检查点与日志已保存；模型质量对照尚待独立评估。')
finally:
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=(results / 'environment.txt').open('w'), check=False)
    shutil.make_archive('/content/ione_results', 'zip', results)
    print('下载 ione_results.zip，保留整个文件供复核。')
    files.download('/content/ione_results.zip')
'''),
            md('下载完成后，菜单「运行时 → 断开连接并删除运行时」。把 `ione_results.zip` 放回项目的 `Saved/m6_runs/`，供后续核验。\n\n训练 loss 与 dev loss 用于检查训练过程；角色、事实和权限收益需要后续 Base/SFT 同条件评估。')]
    if with_dev_eval:
        extra = '''    # Evaluate the same frozen dev payload after successful pilot reload.
    import hashlib
    evaluation_packet = root / 'dev_packet'
    (evaluation_packet / 'adapter').mkdir(parents=True)
    payloads = {
        'training_result.json': results / 'pilot/result.json',
        'sft_dev_canonical.jsonl': root / 'bundle/sft_dev_canonical.jsonl',
        'adapter/adapter_config.json': results / 'pilot/adapter/adapter_config.json',
        'adapter/adapter_model.safetensors': results / 'pilot/adapter/adapter_model.safetensors'}
    for name, path in payloads.items():
        shutil.copy2(path, evaluation_packet / name)
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in payloads.items()}
    (evaluation_packet / 'eval_manifest.json').write_text(json.dumps({'files_sha256': hashes}, indent=2))
    evaluation_command = [sys.executable, '-u', str(root / 'Tools/eval_ione_adapter.py'),
        '--packet', str(evaluation_packet), '--output', str(results / 'dev_comparison')]
    with (results / 'dev_evaluation.log').open('w') as log:
        process = subprocess.Popen(evaluation_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end=''); log.write(line); log.flush()
        if process.wait(): raise RuntimeError('dev evaluation failed; inspect downloaded logs')
'''
        source = ''.join(cells[5]['source'])
        source = source.replace("run_phase('pilot', ['--smoke-result', str(smoke_result)])",
                                "run_phase('pilot', ['--smoke-result', str(smoke_result), '--precision', 'fp32'])")
        source = source.replace("    print('完成。", extra + "    print('完成。")
        cells[5]['source'] = source.splitlines(True)
        cells[0]['source'] += ['\n本批次包含 smoke → SFT pilot → Base/SFT 开发集对照 → 统一下载。冻结测试集不参与本批次。']
    return cells


def package(bundle, output, smoke_result=None, with_dev_eval=False):
    manifest, _ = verify_bundle(bundle)
    output = Path(output)
    if output.exists(): raise ValueError('Use a new output directory')
    root = Path(__file__).resolve().parents[1]
    source_names = ['Tools/train_ione_sft.py', 'Tools/ione_tokenizer_smoke.py',
                    'Tools/ione_data_pipeline.py', 'Tools/preflight_ione_sft.py', 'requirements-m6-colab.txt']
    if with_dev_eval: source_names.append('Tools/eval_ione_adapter.py')
    files = {name: (root / name).read_bytes() for name in source_names}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    files['source_revision.json'] = json.dumps({'git_commit': commit,
        'source_sha256': {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}}, indent=2).encode()
    sft_names = [f'sft_{split}{suffix}.jsonl' for split in ('train', 'dev') for suffix in ('', '_canonical')]
    for name in sft_names: files['bundle/' + name] = (bundle / name).read_bytes()
    reduced = {'status': manifest['status'], 'counts': {k: manifest['counts'][k] for k in ('SFT_train', 'SFT_dev')},
               'files_sha256': {n: manifest['files_sha256'][n] for n in sft_names},
               'source_manifest_sha256': hashlib.sha256((bundle / 'manifest.json').read_bytes()).hexdigest(),
               'heldout_sha256': manifest['heldout_sha256']}
    files['bundle/manifest.json'] = json.dumps(reduced, indent=2).encode()
    if smoke_result is not None:
        raw = Path(smoke_result).read_bytes()
        proof = json.loads(raw)
        if (proof.get('phase') != 'smoke' or proof.get('checkpoint_reload_passed') is not True
                or proof.get('model') != 'Qwen/Qwen3-0.6B' or proof.get('optimizer_steps', 0) < 3
                or proof.get('bundle_manifest_sha256') != hashlib.sha256(files['bundle/manifest.json']).hexdigest()):
            raise ValueError('Prior smoke proof does not match this frozen bundle')
        files['prior_smoke_result.json'] = raw
    output.mkdir(parents=True)
    archive = output / 'ione_colab_bundle.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for name, data in files.items(): zip_file.writestr(name, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
                'metadata': {'kernelspec': {'display_name': 'Python 3', 'name': 'python3'},
                             'colab': {'name': 'Ione_Free_GPU_Trial.ipynb'}, 'accelerator': 'GPU'},
                'cells': notebook_cells(digest, with_dev_eval)}
    (output / 'Ione_Free_GPU_Trial.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
    inventory = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    (output / 'package_manifest.json').write_text(json.dumps({'zip_sha256': digest, 'files': inventory}, indent=2))
    return inventory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke-result', type=Path)
    parser.add_argument('--with-dev-eval', action='store_true')
    args = parser.parse_args()
    print(json.dumps(package(args.bundle, args.output, args.smoke_result, args.with_dev_eval), indent=2))
