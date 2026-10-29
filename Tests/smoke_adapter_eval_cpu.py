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
    from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM
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
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
