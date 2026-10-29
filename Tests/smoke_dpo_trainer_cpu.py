"""Opt-in actual DPOTrainer test on a tiny random model; no pretrained quality claim."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import torch
    from transformers import AutoTokenizer,Qwen3Config,Qwen3ForCausalLM,set_seed
    from peft import LoraConfig,get_peft_model
    from train_ione_dpo import run_training,reload_check
    if args.output.exists(): raise ValueError('Preserve prior runs')
    args.output.mkdir(parents=True)
    set_seed(42); torch.set_num_threads(2)
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    config=Qwen3Config(vocab_size=len(tok),hidden_size=32,intermediate_size=64,num_hidden_layers=1,
                        num_attention_heads=2,num_key_value_heads=1,head_dim=16,
                        eos_token_id=tok.eos_token_id,tie_word_embeddings=True)
    base=Qwen3ForCausalLM(config)
    state={n:p.detach().clone() for n,p in base.state_dict().items()}
    adapter=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    # Nonzero stand-in adapter proves reference is the adapter, not the unadapted base.
    with torch.no_grad():
        for n,p in adapter.named_parameters():
            if 'lora_B' in n: p.normal_(0,.02)
    adapter.save_pretrained(args.output/'initial_adapter')
    fresh=Qwen3ForCausalLM(config);fresh.load_state_dict(state)
    rows=[{'prompt':[{'role':'system','content':'Read the test dial.'},
                     {'role':'user','content':f'Test-only dial shows {i+61}.'}],
           'chosen':f'The dial shows {i+61}.','rejected':f'The dial shows {i+91}.'} for i in range(3)]
    result=run_training(fresh,tok,args.output/'initial_adapter',rows,args.output/'run',cpu=True,max_steps=2)
    reload_base=Qwen3ForCausalLM(config);reload_base.load_state_dict(state)
    result['reload_max_logit_delta']=reload_check(reload_base,args.output/'run')
    assert result['optimizer_steps']['successful']==2
    # Run the real adapter-selection loop; one generated token per call keeps CPU QA short.
    from peft import PeftModel
    import eval_ione_dpo
    from eval_ione_dialogue import read_cases
    compare_base=Qwen3ForCausalLM(config);compare_base.load_state_dict(state)
    compare=PeftModel.from_pretrained(compare_base,args.output/'initial_adapter',adapter_name='reference')
    compare.load_adapter(args.output/'run/adapters/policy',adapter_name='policy')
    actual_generate=eval_ione_dpo.generate_one
    def short_generate(model,tokenizer,messages,**kwargs):
        return actual_generate(model,tokenizer,messages,warmup=True)
    eval_ione_dpo.generate_one=short_generate
    root=Path(__file__).resolve().parents[1]
    cases,_=read_cases(root/'Reports/posttraining/eval_set_v1.jsonl')
    bible=json.loads((root/'Narrative/character_bible.json').read_text(encoding='utf-8'))
    versions={n:p._version for n,p in compare.named_parameters()}
    eval_ione_dpo.paired_frozen(compare,tok,cases[:2],bible,args.output/'comparison')
    raw=[json.loads(s) for s in (args.output/'comparison/frozen_raw.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [r['variant'] for r in raw]==['SFT','DPO','DPO','SFT']
    assert all(p._version==versions[n] for n,p in compare.named_parameters())
    result['named_adapter_comparison_smoke']='4 real one-token generations; alternating order; weights unchanged'
    result.update(scope='tiny random CPU mechanics only',GPU=False,pretrained_weights_loaded=False,reload_check='passed')
    (args.output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
