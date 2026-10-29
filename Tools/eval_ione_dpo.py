"""Matched SFT/DPO frozen evaluation using two named adapters on one frozen base."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

from eval_ione_frozen_hf import load_frozen, generate_one
from eval_ione_dialogue import messages_for


def validate_training_identity(training, sft, reference_path, policy_path):
    if training['reload_check']!='passed' or not training['reference_unchanged']:
        raise ValueError('DPO checkpoint/reload gate failed')
    if training['model_id']!=sft['model'] or training['revision']!=sft['revision']:
        raise ValueError('SFT/DPO base identity mismatch')
    for key,path in [('source_SFT_adapter_sha256',reference_path),('policy_adapter_sha256',policy_path)]:
        if training[key]!=hashlib.sha256(Path(path).read_bytes()).hexdigest():
            raise ValueError('SFT reference or DPO policy checkpoint changed')


def paired_frozen(model, tokenizer, cases, bible, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    times={'SFT':[],'DPO':[]};truncated={'SFT':0,'DPO':0}
    with (output/'frozen_raw.jsonl').open('x',encoding='utf-8') as trace:
        for index,case in enumerate(cases):
            messages=messages_for(case,bible)
            hashes=[]
            for variant in (('SFT','DPO') if index%2==0 else ('DPO','SFT')):
                model.set_adapter('reference' if variant=='SFT' else 'policy')
                assert model.active_adapter == ('reference' if variant=='SFT' else 'policy')
                model.eval()
                if index==0:generate_one(model,tokenizer,messages,warmup=True)
                reply=generate_one(model,tokenizer,messages)
                hashes.append(reply['prompt_sha256'])
                trace.write(json.dumps(dict(case_id=case['case_id'],variant=variant,case=case,
                    messages=messages,order=index,world_actions='not_executed',scoring='pending_review',**reply),
                    ensure_ascii=False)+'\n');trace.flush()
                times[variant].append(reply['wall_seconds']);truncated[variant]+=reply['truncated']
            assert hashes[0]==hashes[1]
            print(f'SFT/DPO {index+1}/{len(cases)}',flush=True)
    summary={'responses':2*len(cases),'training_steps':0,'quality_scores':'pending review',
             'variants':{v:{'p50_seconds':statistics.median(t),
                            'p95_seconds_nearest_rank':sorted(t)[math.ceil(.95*len(t))-1],
                            'truncated':truncated[v]} for v,t in times.items()}}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--dpo-run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import torch,transformers,peft
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel
    if not torch.cuda.is_available():raise RuntimeError('Free CUDA GPU required')
    manifest=json.loads((args.packet/'packet_manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['files_sha256'].items():
        path=(args.packet/name).resolve()
        if args.packet.resolve() not in path.parents or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Packet hash/path mismatch')
    training=json.loads((args.dpo_run/'result.json').read_text(encoding='utf-8'))
    sft=json.loads((args.packet/'training_result.json').read_text(encoding='utf-8'))
    validate_training_identity(training,sft,args.packet/'adapter/adapter_model.safetensors',
                               args.dpo_run/'adapters/policy/adapter_model.safetensors')
    cases,bible,digest=load_frozen(args.packet)
    tokenizer=AutoTokenizer.from_pretrained(sft['model'],revision=sft['revision'],trust_remote_code=False)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()!=sft['chat_template_sha256']:
        raise ValueError('Chat template changed')
    base=AutoModelForCausalLM.from_pretrained(sft['model'],revision=sft['revision'],dtype=torch.float32,
             device_map={'':'cuda'},low_cpu_mem_usage=True,attn_implementation='sdpa',trust_remote_code=False)
    model=PeftModel.from_pretrained(base,args.packet/'adapter',adapter_name='reference',is_trainable=False)
    model.load_adapter(args.dpo_run/'adapters/policy',adapter_name='policy',is_trainable=False)
    summary=paired_frozen(model,tokenizer,cases,bible,args.output)
    metadata={'scope':'fixed-context SFT/DPO HF comparison; not UE timing or rollout',
              'eval_set_sha256':digest,'model':sft['model'],'revision':sft['revision'],'precision':'fp32',
              'gpu':torch.cuda.get_device_name(),'torch':torch.__version__,
              'transformers':transformers.__version__,'peft':peft.__version__,
              'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'reference_adapter_sha256':hashlib.sha256((args.packet/'adapter/adapter_model.safetensors').read_bytes()).hexdigest(),
              'policy_adapter_sha256':hashlib.sha256((args.dpo_run/'adapters/policy/adapter_model.safetensors').read_bytes()).hexdigest(),
              'responses':summary['responses'],'training_steps':0}
    (args.output/'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')


if __name__=='__main__':main()
