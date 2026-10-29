"""Opt-in TRL integration check on tiny RANDOM Qwen3; no pretrained quality claim.

python Tests/smoke_sft_trainer_cpu.py --tokenizer PATH --output NEW_DIRECTORY
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('smoke', 'pilot'), default='smoke')
    args = parser.parse_args()
    import torch
    from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM, set_seed
    from train_ione_sft import run_training, reload_check, smoke_rows
    if args.output.exists():
        raise ValueError('Output already exists')
    args.output.mkdir(parents=True)
    torch.set_num_threads(2); set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    config = Qwen3Config(vocab_size=len(tokenizer), hidden_size=32, intermediate_size=64,
                         num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
                         head_dim=16, eos_token_id=tokenizer.eos_token_id, tie_word_embeddings=True)
    model = Qwen3ForCausalLM(config)
    base_state = {n: p.detach().clone() for n, p in model.state_dict().items()}
    rows = smoke_rows()
    result = run_training(model, tokenizer, rows[:14], rows[14:], args.output, args.phase, cpu=True)
    expected_steps = 3 if args.phase == 'smoke' else 4
    assert result['optimizer_steps'] == expected_steps
    assert result['attempted_optimizer_steps'] == expected_steps
    assert result['skipped_optimizer_steps'] == 0
    base = Qwen3ForCausalLM(config); base.load_state_dict(base_state)
    result['reload_max_logit_delta'] = reload_check(base, args.output / 'adapter', args.output / 'reload_probe.pt')
    result.update(scope='tiny random CPU model integration only', pretrained_weights_loaded=False,
                  GPU_training=False, checkpoint_reload_passed=True)
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
