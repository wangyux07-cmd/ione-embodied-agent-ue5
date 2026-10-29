"""Opt-in paired-generation integration on tiny random CPU model; no quality claim."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM, GenerationConfig
    from peft import LoraConfig, get_peft_model
    from eval_ione_adapter import paired_dev
    from test_data_pipeline import DataContractTests
    torch.manual_seed(42); torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    config = Qwen3Config(vocab_size=len(tokenizer), hidden_size=32, intermediate_size=64,
                        num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
                        head_dim=16, eos_token_id=tokenizer.eos_token_id, tie_word_embeddings=True)
    model = get_peft_model(Qwen3ForCausalLM(config), LoraConfig(r=8, lora_alpha=16,
                            target_modules=['q_proj', 'v_proj'], task_type='CAUSAL_LM'))
    base = model.get_base_model()
    base.generation_config = GenerationConfig(do_sample=True, temperature=0.6, top_k=20, top_p=0.95)
    base.generation_config.transformers_version = '4.57.6'
    observed_sampling = []
    original_prepare = base._prepare_generation_config
    legacy, _ = original_prepare(GenerationConfig(do_sample=False), use_model_defaults=None)
    assert legacy.do_sample is True, 'The adversarial model config must reproduce the override'
    import types
    def traced_prepare(self, *args, **kwargs):
        prepared, model_kwargs = original_prepare(*args, **kwargs)
        observed_sampling.append(prepared.do_sample)
        return prepared, model_kwargs
    base._prepare_generation_config = types.MethodType(traced_prepare, base)
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if 'lora_B' in name: parameter.normal_(std=0.02)
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    row = DataContractTests().sample()
    row.update(split='dev', review_status='approved_human', review_source={'type': 'human', 'reference': 'integration fixture'})
    second = copy.deepcopy(row); second['sample_id'] = 's2'; second['family_id'] = 'second'
    result = paired_dev(model, tokenizer, [row, second], args.output,
                        {'scope': 'tiny random CPU eval integration; no pretrained weights'}, max_new_tokens=3)
    records = [json.loads(line) for line in (args.output / 'paired_raw.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [r['variant'] for r in records] == ['Base', 'SFT', 'SFT', 'Base']
    assert records[0]['prompt_sha256'] == records[1]['prompt_sha256']
    assert records[2]['prompt_sha256'] == records[3]['prompt_sha256']
    assert all(torch.equal(before[n], p.detach()) for n, p in model.named_parameters())
    assert result['training_steps'] == 0 and result['raw_responses'] == 4
    assert len(observed_sampling) == 6 and not any(observed_sampling), observed_sampling
    assert all(r['generation_kwargs']['use_model_defaults'] is False for r in records)
    from eval_ione_frozen_hf import generate_one
    one = generate_one(model, tokenizer, row['prompt'], warmup=True)
    two = generate_one(model, tokenizer, row['prompt'], warmup=True)
    sampled = generate_one(model, tokenizer, row['prompt'], sample=True, seed=1000, warmup=True)
    assert one['new_token_ids'] == two['new_token_ids'] and not one['generation_kwargs']['do_sample']
    assert sampled['generation_kwargs']['do_sample'] and sampled['seed'] == 1000
    assert all(torch.equal(before[n], p.detach()) for n, p in model.named_parameters())
    (args.output / 'generation_policy_test.json').write_text(json.dumps({
        'legacy_model_default_overrides_false': legacy.do_sample,
        'actual_generate_prepared_do_sample': observed_sampling,
        'weight_changes': False, 'scope': 'tiny random CPU library integration'}))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
