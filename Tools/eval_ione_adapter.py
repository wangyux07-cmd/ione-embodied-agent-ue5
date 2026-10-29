"""Paired Base/SFT development evaluation with one pinned HF model and no updates."""
import argparse
from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
import time

from ione_data_pipeline import read_jsonl, validate_sample
from ione_tokenizer_smoke import encode_target


def greedy_generate(model, prompt, options):
    # kwargs override model defaults, including Qwen's do_sample=True config.
    return model.generate(**prompt, generation_config=options, do_sample=False,
                          use_model_defaults=False, use_cache=True)


def validate_dev_rows(rows):
    if not rows or any(r['kind'] != 'sft' or r['split'] != 'dev' for r in rows):
        raise ValueError('Only approved SFT dev cases belong in this diagnostic')
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate dev sample IDs')
    for row in rows:
        validate_sample(row)
        if row['review_status'] != 'approved_human': raise ValueError('Unapproved dev payload')


def paired_dev(model, tokenizer, rows, output, metadata, max_new_tokens=128):
    validate_dev_rows(rows)
    import torch
    from transformers import GenerationConfig
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    device = next(model.parameters()).device
    def sync():
        if device.type == 'cuda': torch.cuda.synchronize()
    options = GenerationConfig(do_sample=False, max_new_tokens=max_new_tokens,
                               pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
    model.eval()
    trace = []
    for index, row in enumerate(rows):
        prefix = tokenizer.apply_chat_template(row['prompt'], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        prompt = tokenizer(prefix, return_tensors='pt', add_special_tokens=False).to(device)
        encoded = encode_target(tokenizer, row['prompt'], row['completion'], 1536)
        teacher = {k: torch.tensor([encoded[k]], device=device) for k in ('input_ids', 'attention_mask', 'labels')}
        variants = ('Base', 'SFT') if index % 2 == 0 else ('SFT', 'Base')
        for variant in variants:
            with model.disable_adapter() if variant == 'Base' else nullcontext():
                with torch.inference_mode():
                    if index == 0:
                        # Warm each path; exclude from measured generation wall time.
                        greedy_generate(model, prompt, GenerationConfig(do_sample=False, max_new_tokens=1,
                            pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id))
                    loss = float(model(**teacher, use_cache=False).loss)
                    if not math.isfinite(loss): raise RuntimeError('Non-finite dev loss')
                    sync(); started = time.perf_counter()
                    generated = greedy_generate(model, prompt, options)
                    sync(); elapsed = time.perf_counter() - started
            tokens = generated[0, prompt['input_ids'].shape[1]:].cpu().tolist()
            record = {'sample_id': row['sample_id'], 'family_id': row['family_id'], 'variant': variant,
                      'order_in_pair': variants.index(variant), 'prompt_sha256': hashlib.sha256(prefix.encode()).hexdigest(),
                      'prompt': row['prompt'], 'reference': row['completion'], 'context': row['context'],
                      'response': tokenizer.decode(tokens, skip_special_tokens=True),
                      'new_token_ids': tokens, 'generated_tokens': len(tokens), 'wall_seconds': elapsed,
                      'target_only_loss': loss, 'supervised_tokens': encoded['target_tokens'],
                      'truncated': len(tokens) >= max_new_tokens and tokens[-1] != tokenizer.eos_token_id,
                      'quality_labels': 'pending_review', 'world_actions': 'not_executed'}
            record['generation_kwargs'] = {'do_sample': False, 'use_model_defaults': False, 'use_cache': True}
            with (output / 'paired_raw.jsonl').open('a', encoding='utf-8') as file:
                file.write(json.dumps(record, ensure_ascii=False) + '\n')
            trace.append(record)
            print(row['sample_id'], variant, round(loss, 4), round(elapsed, 2), flush=True)
    summary = {'metadata': metadata, 'cases': len(rows), 'raw_responses': len(trace),
               'scope': 'development diagnostic; not frozen holdout, human scoring or UE latency',
               'do_sample': False, 'max_new_tokens': max_new_tokens, 'enable_thinking': False,
               'use_model_defaults': False,
               'training_steps': 0, 'variants': {}}
    for variant in ('Base', 'SFT'):
        records = [r for r in trace if r['variant'] == variant]
        times = sorted(r['wall_seconds'] for r in records)
        summary['variants'][variant] = {
            'mean_example_target_loss': sum(r['target_only_loss'] for r in records) / len(records),
            'token_weighted_target_loss': sum(r['target_only_loss'] * r['supervised_tokens'] for r in records) / sum(r['supervised_tokens'] for r in records),
            'p50_wall_seconds': __import__('statistics').median(times),
            'p95_wall_seconds_nearest_rank': times[math.ceil(0.95 * len(times)) - 1],
            'truncated': sum(r['truncated'] for r in records)}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import torch, transformers, peft
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    from peft import PeftModel
    if not torch.cuda.is_available(): raise RuntimeError('Free CUDA GPU unavailable; stop')
    manifest = json.loads((args.packet / 'eval_manifest.json').read_text())
    for name, digest in manifest['files_sha256'].items():
        path = (args.packet / name).resolve()
        if args.packet.resolve() not in path.parents: raise ValueError('Manifest path escape')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest: raise ValueError('Evaluation packet hash mismatch')
    result = json.loads((args.packet / 'training_result.json').read_text())
    if not result['checkpoint_reload_passed'] or result['dtype'] != 'torch.float32':
        raise ValueError('Expected verified FP32 pilot')
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(result['model'], revision=result['revision'], trust_remote_code=False)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != result['chat_template_sha256']:
        raise ValueError('Chat template changed')
    base = AutoModelForCausalLM.from_pretrained(result['model'], revision=result['revision'], dtype=torch.float32,
                device_map={'': 'cuda'}, low_cpu_mem_usage=True, attn_implementation='sdpa', trust_remote_code=False)
    model = PeftModel.from_pretrained(base, args.packet / 'adapter', is_trainable=False)
    rows = read_jsonl(args.packet / 'sft_dev_canonical.jsonl')
    metadata = {'model': result['model'], 'revision': result['revision'], 'dtype': 'float32', 'seed': 42,
                'gpu': torch.cuda.get_device_name(), 'torch': torch.__version__, 'transformers': transformers.__version__,
                'peft': peft.__version__, 'packet_manifest_sha256': hashlib.sha256((args.packet / 'eval_manifest.json').read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'base_path': 'same pinned model with adapter disabled', 'SFT_path': 'same model with adapter enabled'}
    print(json.dumps(paired_dev(model, tokenizer, rows, args.output, metadata), indent=2))


if __name__ == '__main__': main()
