"""Reproduce AMP/no-AMP LoRA mismatch on tiny CPU model and verify matched AMP."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import torch
    from peft import get_peft_model, PeftModel, LoraConfig
    from transformers import Qwen3Config, Qwen3ForCausalLM
    from train_ione_sft import probe_logits
    if args.output.exists(): raise ValueError('Output already exists')
    args.output.mkdir(parents=True)
    torch.manual_seed(42); torch.set_num_threads(2)
    config = Qwen3Config(vocab_size=128, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                         num_attention_heads=2, num_key_value_heads=1, head_dim=16, tie_word_embeddings=True)
    base = Qwen3ForCausalLM(config).to(torch.bfloat16)
    state = {n: p.clone() for n, p in base.state_dict().items()}
    model = get_peft_model(base, LoraConfig(r=8, lora_alpha=16, target_modules=['q_proj', 'v_proj'], task_type='CAUSAL_LM'))
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if 'lora_' in name: parameter.normal_(mean=0, std=0.1)
    model.eval()
    batch = {'input_ids': torch.tensor([[1, 2, 3, 4]])}
    reference = probe_logits(model, batch, 3)
    model.save_pretrained(args.output / 'adapter')
    new_base = Qwen3ForCausalLM(config).to(torch.bfloat16); new_base.load_state_dict(state)
    reloaded = PeftModel.from_pretrained(new_base, args.output / 'adapter'); reloaded.eval()
    with torch.no_grad(): unmatched = reloaded(**batch, use_cache=False).logits[:, 3].float().cpu()
    matched = probe_logits(reloaded, batch, 3)
    mismatch = float((reference - unmatched).abs().max())
    assert mismatch > 0, 'Test must exercise different mixed-precision arithmetic'
    torch.testing.assert_close(reference, matched, atol=0, rtol=0)
    result = {'scope': 'tiny random CPU bf16 LoRA arithmetic reproduction; not Colab rerun',
              'unmatched_amp_max_delta': mismatch, 'matched_amp_max_delta': float((reference - matched).abs().max()),
              'assertion_tolerance_unchanged': True}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
