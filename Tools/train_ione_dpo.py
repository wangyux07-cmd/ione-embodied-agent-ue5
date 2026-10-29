"""DPO on an approved private packet; one frozen base, policy and reference SFT adapters."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def prepare_pairs(rows, tokenizer, max_length=1536):
    """Use explicit non-thinking strings; TRL adds one EOS to each completion."""
    from trl import DPOTrainer
    features = []
    for row in rows:
        def text(value):
            return value if isinstance(value, str) else value[0]['content']
        item = {'prompt': tokenizer.apply_chat_template(row['prompt'], tokenize=False,
                     add_generation_prompt=True, enable_thinking=False),
                'chosen': text(row['chosen']), 'rejected': text(row['rejected'])}
        if not item['chosen'].strip() or item['chosen'].strip() == item['rejected'].strip():
            raise ValueError('Empty or tied preference')
        for key in ('chosen','rejected'):
            if any(marker in item[key] for marker in ('<think>','</think>',tokenizer.eos_token)):
                raise ValueError('Completion contains thinking or pre-appended EOS')
        encoded = DPOTrainer.tokenize_row(item, tokenizer, add_special_tokens=False)
        for key in ('chosen_input_ids','rejected_input_ids'):
            if len(encoded['prompt_input_ids']) + len(encoded[key]) > max_length:
                raise ValueError('DPO sequence would be truncated')
            assert encoded[key][-1] == tokenizer.eos_token_id
        features.append(item)
    return features


def adapter_state(model, name):
    from peft import get_peft_model_state_dict
    return {n: p.detach().cpu().clone() for n,p in get_peft_model_state_dict(model, adapter_name=name).items()}


def run_training(base, tokenizer, adapter, rows, output, cpu=False, max_steps=-1):
    import torch
    from datasets import Dataset
    from peft import PeftModel
    from transformers import TrainerCallback
    from trl import DPOConfig, DPOTrainer
    from train_ione_sft import probe_logits

    output = Path(output)
    if output.exists(): raise ValueError('Output already exists; preserve prior evidence')
    output.mkdir(parents=True)
    model = PeftModel.from_pretrained(base, adapter, adapter_name='policy', is_trainable=True)
    model.load_adapter(adapter, adapter_name='reference', is_trainable=False)
    model.set_adapter('policy')
    before = adapter_state(model,'policy'); reference = adapter_state(model,'reference')
    assert before.keys() == reference.keys()
    assert all(torch.equal(before[n], reference[n]) for n in before)
    # Frozen tensor version counters detect accidental writes without copying a 1.7B base.
    base_versions = {n:p._version for n,p in model.named_parameters() if 'lora_' not in n}
    features = prepare_pairs(rows, tokenizer)
    config = DPOConfig(output_dir=str(output), num_train_epochs=1, max_steps=max_steps,
                       learning_rate=1e-5, beta=.1, loss_type=['sigmoid'],
                       model_adapter_name='policy', ref_adapter_name='reference',
                       precompute_ref_log_probs=True, precompute_ref_batch_size=1, use_logits_to_keep=True,
                       max_length=1536, max_prompt_length=None, max_completion_length=None,
                       per_device_train_batch_size=1, gradient_accumulation_steps=1 if cpu else 4,
                       bf16=False, fp16=False, use_cpu=cpu,
                       gradient_checkpointing=True,
                       gradient_checkpointing_kwargs={'use_reentrant':False},
                       optim='adamw_torch', report_to='none', push_to_hub=False,
                       save_strategy='no', logging_steps=1, logging_nan_inf_filter=False,
                       seed=42, data_seed=42, dataloader_num_workers=0)
    steps = {'attempted':0,'successful':0,'skipped':0}
    class Ledger(TrainerCallback):
        def on_pre_optimizer_step(self,args,state,control,**kwargs):
            grad=kwargs.get('model',model)
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in grad.parameters()):
                raise FloatingPointError('Non-finite DPO gradient')
        def on_step_end(self,args,state,control,**kwargs):
            steps['attempted'] += 1
            skipped = trainer.accelerator.optimizer_step_was_skipped
            steps['skipped' if skipped else 'successful'] += 1
            if skipped: raise FloatingPointError('Skipped DPO optimizer step')
        def on_log(self,args,state,control,logs=None,**kwargs):
            for key,value in (logs or {}).items():
                if isinstance(value,(int,float)) and not math.isfinite(value):
                    raise FloatingPointError('Non-finite DPO log: '+key)
    trainer = DPOTrainer(model=model, ref_model=None, args=config,
                         train_dataset=Dataset.from_list(features), processing_class=tokenizer,
                         callbacks=[Ledger()])
    trainer.create_optimizer()
    for index, feature in enumerate(features):
        expected = DPOTrainer.tokenize_row(feature, tokenizer, add_special_tokens=False)
        assert all(trainer.train_dataset[index][key] == value for key,value in expected.items())
    names = {id(p): n for n,p in model.named_parameters()}
    optimizer_names = [names[id(p)] for group in trainer.optimizer.param_groups for p in group['params']]
    assert optimizer_names and all('.policy.' in n and 'lora_' in n for n in optimizer_names)
    # Exercise TRL's actual reference context and ensure it restores policy.
    with trainer.null_ref_context():
        assert model.active_adapter == 'reference'
    assert model.active_adapter == 'policy'
    result = trainer.train()
    model.set_adapter('policy'); model.eval()
    after = adapter_state(model,'policy')
    changed = sum(not torch.equal(before[n],after[n]) for n in before)
    assert changed > 0
    reference_after=adapter_state(model,'reference')
    assert all(torch.equal(reference[n], reference_after[n]) for n in reference)
    assert all(p._version == base_versions[n] for n,p in model.named_parameters() if n in base_versions)
    assert steps['successful'] == trainer.state.global_step and steps['skipped']==0
    expected_steps=max_steps if max_steps>0 else math.ceil(len(rows)/config.gradient_accumulation_steps)
    assert steps['successful']==expected_steps
    model.save_pretrained(output/'adapters',selected_adapters=['policy'])
    tokenizer.save_pretrained(output/'tokenizer')
    trainer.save_state()
    torch.save({'optimizer':trainer.optimizer.state_dict(),'scheduler':trainer.lr_scheduler.state_dict()},
               output/'optimizer_scheduler.pt')
    (output/'dpo_config.json').write_text(config.to_json_string(),encoding='utf-8')
    batch = tokenizer(features[0]['prompt'],return_tensors='pt').to(next(model.parameters()).device)
    logits = probe_logits(model,batch,-1)
    torch.save({'batch':{k:v.cpu() for k,v in batch.items()},'logits':logits},output/'reload_probe.pt')
    summary = {'pairs':len(rows), 'optimizer_steps':steps, 'policy_changed_tensors':changed,
               'reference_unchanged':True,'base_unchanged':True,'optimizer_policy_only':True,
               'initial_policy_equals_SFT_reference':True,'precision':'fp32',
               'precompute_reference_log_probs':True,'use_logits_to_keep':True,
               'max_sequence_length':1536,'learning_rate':1e-5,'beta':.1,'epochs':1,
               'source_SFT_adapter_sha256':hashlib.sha256((Path(adapter)/'adapter_model.safetensors').read_bytes()).hexdigest(),
               'policy_adapter_sha256':hashlib.sha256((output/'adapters/policy/adapter_model.safetensors').read_bytes()).hexdigest(),
               'adapter_path':'adapters/policy','trainer_metrics':result.metrics,
               'log_history':trainer.state.log_history,'reload_check':'pending'}
    (output/'result_pending_reload.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def reload_check(base, output):
    import torch
    from peft import PeftModel
    from train_ione_sft import probe_logits
    output=Path(output)
    model=PeftModel.from_pretrained(base,output/'adapters/policy',adapter_name='policy')
    model.eval()
    probe=torch.load(output/'reload_probe.pt',map_location='cpu',weights_only=True)
    batch={k:v.to(next(model.parameters()).device) for k,v in probe['batch'].items()}
    delta=(probe_logits(model,batch,-1)-probe['logits']).abs().max().item()
    if delta > 1e-5: raise ValueError(f'DPO reload mismatch: {delta}')
    return delta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--sft-adapter',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from ione_data_pipeline import read_jsonl, export_approved
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    digest=hashlib.sha256(args.data.read_bytes()).hexdigest()
    if manifest['files'].get(args.data.name)!=digest: raise ValueError('Data hash mismatch')
    rows=read_jsonl(args.data); export_approved(rows)
    if len(rows)!=manifest['pairs'] or not manifest.get('approval_reference'): raise ValueError('Approval missing')
    import gc
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,set_seed
    from train_ione_sft import MODELS
    if not torch.cuda.is_available(): raise RuntimeError('Free CUDA GPU required; do not rent a GPU')
    set_seed(42)
    model_id,revision=MODELS['pilot']
    adapter_config=json.loads((args.sft_adapter/'adapter_config.json').read_text(encoding='utf-8'))
    if adapter_config.get('base_model_name_or_path')!=model_id:
        raise ValueError('Expected SFT adapter for the pinned Qwen3-1.7B model')
    tokenizer=AutoTokenizer.from_pretrained(model_id,revision=revision)
    def load():
        return AutoModelForCausalLM.from_pretrained(model_id,revision=revision,torch_dtype=torch.float32,
                                                   attn_implementation='sdpa').to('cuda')
    summary=run_training(load(),tokenizer,args.sft_adapter,rows,args.output)
    gc.collect(); torch.cuda.empty_cache()
    summary['reload_max_logit_delta']=reload_check(load(),args.output)
    summary.update(reload_check='passed',model_id=model_id,revision=revision,
                   data_sha256=digest,GPU=torch.cuda.get_device_name(),torch_version=torch.__version__)
    (args.output/'result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
