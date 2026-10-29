"""Opt-in real three-adapter HTTP/Controller integration on tiny RANDOM CPU weights."""
import argparse
import json
from pathlib import Path
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve previous runs')
    import torch
    from transformers import AutoTokenizer,Qwen3Config,Qwen3ForCausalLM,set_seed
    from peft import get_peft_model,LoraConfig
    from serve_ione_hf import RuntimeEngine,make_server
    from benchmark_ione_runtime import benchmark
    torch.set_num_threads(2);set_seed(42)
    tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    config=Qwen3Config(vocab_size=len(tokenizer),hidden_size=32,intermediate_size=64,
        num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=1,head_dim=16,
        eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,tie_word_embeddings=True)
    model=get_peft_model(Qwen3ForCausalLM(config),
        LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'),adapter_name='sft')
    model.add_adapter('dpo',LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    with torch.no_grad():
        for name,p in model.named_parameters():
            if 'lora_B' in name:p.normal_(std=.03)
    versions={name:p._version for name,p in model.named_parameters()}
    from peft.tuners.lora.layer import LoraLayer
    layers=[layer for layer in model.modules() if isinstance(layer,LoraLayer)]
    observed=[];original_generate=model.generate
    def traced_generate(*args,**kwargs):
        selected=['base' if layer.disable_adapters else ','.join(layer.active_adapters) for layer in layers]
        assert len(set(selected))==1
        assert kwargs['do_sample'] is False and kwargs['use_model_defaults'] is False
        observed.append(selected[0])
        return original_generate(*args,**kwargs)
    model.generate=traced_generate
    engine=RuntimeEngine(model,tokenizer,{'scope':'tiny random CPU; no pretrained weights or training',
                                        'precision':'fp32','device':'cpu'},max_new_tokens=2)
    server=make_server(engine,port=0)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:summary=benchmark('http://127.0.0.1:'+str(server.server_port),args.output,repeats=1,timeout=30)
    finally:server.shutdown();server.server_close()
    assert all(p._version==versions[name] for name,p in model.named_parameters())
    assert summary['records']==36
    assert all(s['generation_metadata_count']==12 for s in summary['variants'].values())
    assert observed[:3]==['base','sft','dpo']
    assert all(observed.count(v)==13 for v in ['base','sft','dpo'])
    summary.update(scope='tiny random CPU integration only; no pretrained quality or GPU result',
                   weight_writes=False,pretrained_weights_loaded=False,
                   actual_LoRA_dispatch_counts={v:observed.count(v) for v in ['base','sft','dpo']})
    (args.output/'integration_result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
