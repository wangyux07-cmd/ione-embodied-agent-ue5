"""CPU-only Qwen3 target-only masking checks; does not load model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ione_data_pipeline import read_jsonl, stable_write, validate_sample


def encode_target(tokenizer,prompt,target,max_length=4096):
    prefix=tokenizer.apply_chat_template(prompt,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    full=tokenizer.apply_chat_template(prompt+[{'role':'assistant','content':target}],tokenize=False,
                                        add_generation_prompt=False,enable_thinking=False)
    if not full.startswith(prefix):raise ValueError('Chat template target prefix mismatch')
    prefix_ids=tokenizer.encode(prefix,add_special_tokens=False)
    ids=tokenizer.encode(full,add_special_tokens=False)
    if ids[:len(prefix_ids)]!=prefix_ids:raise ValueError('Token boundary changed at completion start')
    if len(ids)>max_length:raise ValueError('Over-length sample; no silent truncation')
    if len(ids)<=len(prefix_ids):raise ValueError('Empty supervised span')
    labels=[-100]*len(prefix_ids)+ids[len(prefix_ids):]
    if tokenizer.eos_token_id not in labels[len(prefix_ids):]:raise ValueError('Assistant end token is not supervised')
    visible=tokenizer.decode(ids[len(prefix_ids):],skip_special_tokens=False)
    if target not in visible:raise ValueError('Decoded supervised span lost target text')
    if '<think>' in visible or '</think>' in visible:raise ValueError('Thinking markers leaked into supervised target')
    return {'input_ids':ids,'labels':labels,'attention_mask':[1]*len(ids),
            'prompt_tokens':len(prefix_ids),'target_tokens':len(ids)-len(prefix_ids)}


def collate_cpu(rows,pad_id):
    import torch
    width=max(len(r['input_ids']) for r in rows)
    batch={key:[] for key in ('input_ids','labels','attention_mask')}
    for row in rows:
        n=width-len(row['input_ids'])
        batch['input_ids'].append(row['input_ids']+[pad_id]*n)
        batch['labels'].append(row['labels']+[-100]*n)
        batch['attention_mask'].append(row['attention_mask']+[0]*n)
    return {key:torch.tensor(values,dtype=torch.long,device='cpu') for key,values in batch.items()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import torch
    import transformers
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,trust_remote_code=False)
    encoded=[];checks=[]
    for row in read_jsonl(args.input):
        validate_sample(row)
        targets=[row['completion']] if row['kind']=='sft' else [row['chosen'],row['rejected']]
        for index,target in enumerate(targets):
            item=encode_target(tokenizer,row['prompt'],target)
            assert all(x==-100 for x in item['labels'][:item['prompt_tokens']])
            encoded.append(item)
            checks.append(dict(sample_id=row['sample_id'],candidate=index,prompt_tokens=item['prompt_tokens'],target_tokens=item['target_tokens']))
    batch=collate_cpu(encoded[:3],tokenizer.pad_token_id)
    assert batch['labels'].device.type=='cpu'
    assert bool(torch.any(batch['attention_mask']==0)), 'Use unequal-length rows to exercise padding'
    assert bool(torch.all(batch['labels'][batch['attention_mask']==0]==-100))
    assert bool(torch.any(batch['labels']!=-100))
    report={'model_weights_loaded':False,'training_run':False,'device':'cpu',
            'transformers':transformers.__version__,'torch':torch.__version__,
            'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
            'template_sha256':hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
            'encoded_sequences':len(encoded),'batch_shape':list(batch['input_ids'].shape),
            'padded_positions':int((batch['attention_mask']==0).sum()),
            'system_history_user_and_non_thinking_prefix_masked':True,'padding_masked':True,
            'assistant_stop_supervised':True,'silent_truncation':False,'samples':checks,
            'scope':'candidate-data mechanics smoke, not training approval or actual TRL trainer execution'}
    stable_write(args.output,json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
