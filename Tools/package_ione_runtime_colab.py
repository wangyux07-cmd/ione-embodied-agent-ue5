"""Package a private free-Colab runtime comparison using existing verified adapters."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from eval_ione_dpo import validate_training_identity
from package_ione_colab import upload_cell_source


def build(sft_result,dpo_result,sft_adapter,dpo_adapter,output):
    root=Path(__file__).resolve().parents[1];output=Path(output)
    if output.exists():raise ValueError('Output exists; preserve earlier packets')
    sft=json.loads(Path(sft_result).read_text(encoding='utf-8'))
    dpo=json.loads(Path(dpo_result).read_text(encoding='utf-8'))
    validate_training_identity(dpo,sft,Path(sft_adapter)/'adapter_model.safetensors',Path(dpo_adapter)/'adapter_model.safetensors')
    if not sft['checkpoint_reload_passed']:raise ValueError('SFT reload gate failed')
    names=['serve_ione_hf.py','ione_model_backend.py','benchmark_ione_runtime.py','ione_controller.py',
           'ione_sessions.py','ione_agent.py','ione_fast_agent.py','ione_llm.py','ione_response.py',
           'serve_ione_agent.py','ione_story_router.py','eval_ione_dpo.py','eval_ione_frozen_hf.py',
           'eval_ione_adapter.py','eval_ione_dialogue.py','train_ione_sft.py','preflight_ione_sft.py',
           'ione_tokenizer_smoke.py','ione_data_pipeline.py']
    files={'Tools/'+name:(root/'Tools'/name).read_bytes() for name in names}
    for name in ['character_bible.json','quests.json','strings_en.json']:files['Narrative/'+name]=(root/'Narrative'/name).read_bytes()
    files['requirements-m6-colab.txt']=(root/'requirements-m6-colab.txt').read_bytes()
    files['packet/sft_result.json']=Path(sft_result).read_bytes();files['packet/dpo_result.json']=Path(dpo_result).read_bytes()
    for folder,source in [('sft',sft_adapter),('dpo',dpo_adapter)]:
        for name in ['adapter_config.json','adapter_model.safetensors']:files[f'packet/{folder}/{name}']=(Path(source)/name).read_bytes()
    run='''import json, os, sys, threading, time
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'Tools'))
from serve_ione_hf import load_engine,make_server
from benchmark_ione_runtime import benchmark
started=time.perf_counter()
engine=load_engine(root/'packet/sft_result.json',root/'packet/dpo_result.json',
                   root/'packet/sft',root/'packet/dpo',device='cuda',allow_download=True)
(root/'results/model_load.json').write_text(json.dumps({'load_wall_seconds':time.perf_counter()-started,
    'includes_public_weight_download_if_not_cached':True,'scope':'shared base loading, not model TTFT'}))
server=make_server(engine,port=0)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    result=benchmark('http://127.0.0.1:'+str(server.server_port),root/'results/runtime',repeats=3,timeout=15)
    (root/'results/runtime/model_identity.json').write_text(json.dumps(engine.identity,indent=2))
finally:server.shutdown();server.server_close()
print('Runtime inference comparison complete; no optimizer or training steps.')
'''
    compile(run,'run_runtime.py','exec');files['run_runtime.py']=run.encode()
    manifest={'scope':'matched runtime dialogue inference, 3 variants x 36 requests; no UE draw or retraining',
              'files_sha256':{name:hashlib.sha256(blob).hexdigest() for name,blob in files.items()}}
    files['manifest.json']=json.dumps(manifest,indent=2).encode()
    output.mkdir(parents=True)
    archive=output/'ione_runtime_bundle.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,blob in files.items():z.writestr(name,blob)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    def md(s):return {'cell_type':'markdown','metadata':{},'source':s.splitlines(True)}
    def code(s):return {'cell_type':'code','metadata':{},'source':s.splitlines(True),'outputs':[],'execution_count':None}
    cells=[md('''# Ione · M8 三模型运行链路检查

这轮只加载现有Base/SFT/DPO并做推理，训练步数0。免费GPU，预算$0，不购买套餐、不挂载Drive、不公开模型或端点。
选择免费GPU → 全部运行 → 上传ione_runtime_bundle.zip → 收取ione_runtime_results.zip。
每模型3次12步结构化游戏旅程，共36次测量；模型路由不在该GPU批次重测。结果是Python/模型服务测时，不含UE绘制。
此时仍使用严格事实锚点发布门禁，原始输出和回退独立保存，不能把门禁成功当作模型事实能力提升。
'''),code("import subprocess\nsubprocess.run(['nvidia-smi'],check=True)\n"),
        code(upload_cell_source(digest)),
        code("import sys,os\nos.environ['HF_HUB_DISABLE_TELEMETRY']='1'\nos.environ['WANDB_DISABLED']='true'\nsubprocess.run([sys.executable,'-m','pip','install','-q','-r',str(root/'requirements-m6-colab.txt')],check=True)\n"),
        code('''import shutil,json,hashlib
results=root/'results';results.mkdir(exist_ok=False)
try:
    manifest=json.loads((root/'manifest.json').read_text())
    for name,expected in manifest['files_sha256'].items():
        path=(root/name).resolve()
        assert root.resolve() in path.parents and hashlib.sha256(path.read_bytes()).hexdigest()==expected
    with (results/'runtime.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-u',str(root/'run_runtime.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:
            print(line,end='');log.write(line);log.flush()
        if process.wait():raise RuntimeError('运行失败，请保留结果包日志；不自动重试或租GPU。')
finally:
    subprocess.run([sys.executable,'-m','pip','freeze'],stdout=(results/'environment.txt').open('w'),check=False)
    shutil.copy2(root/'manifest.json',results/'packet_manifest.json')
    shutil.make_archive('/content/ione_runtime_results','zip',results)
    files.download('/content/ione_runtime_results.zip')
''')]
    for i,cell in enumerate(cells):
        if cell['cell_type']=='code':compile(''.join(cell['source']),f'cell{i}','exec')
    book={'nbformat':4,'nbformat_minor':5,'metadata':{'accelerator':'GPU',
            'colab':{'name':'Ione_M8_Runtime.ipynb'},'kernelspec':{'name':'python3','display_name':'Python 3'}},'cells':cells}
    (output/'Ione_M8_Runtime.ipynb').write_text(json.dumps(book,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'package_manifest.json').write_text(json.dumps({'archive_sha256':digest,**manifest},indent=2),encoding='utf-8')
    return {'archive_sha256':digest,'bytes':archive.stat().st_size,'files':len(files),'training_steps':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['sft-result','dpo-result','sft-adapter','dpo-adapter','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.sft_result,args.dpo_result,args.sft_adapter,args.dpo_adapter,args.output),indent=2))
