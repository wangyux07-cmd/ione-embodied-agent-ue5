"""Frozen HF Base/SFT comparison, followed by separate SFT preference sampling."""
import argparse
from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from eval_ione_dialogue import read_cases, messages_for
from eval_ione_adapter import greedy_generate


def load_frozen(packet):
    cases, digest = read_cases(packet / 'eval_set_v1.jsonl')
    freeze = json.loads((packet / 'freeze_manifest_v1.json').read_text(encoding='utf-8-sig'))
    bible_bytes = (packet / 'character_bible.json').read_bytes()
    if (freeze.get('status') != 'approved_frozen' or freeze.get('eval_set_sha256') != digest
            or not freeze.get('approval_reference') or len(cases) != freeze.get('case_count')
            or any(c['split'] != 'frozen_test' for c in cases)
            or hashlib.sha256(bible_bytes).hexdigest() != freeze.get('persona_sha256')):
        raise ValueError('Frozen evaluation/persona approval mismatch')
    return cases, json.loads(bible_bytes), digest


def generate_one(model, tokenizer, messages, *, sample=False, seed=42, warmup=False):
    import torch
    from transformers import GenerationConfig, set_seed
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer(text, return_tensors='pt', add_special_tokens=False).to(model.device)
    if inputs['input_ids'].shape[1] + 128 > 4096:
        raise ValueError('Context exceeds frozen 4096-token budget; no silent truncation')
    options = GenerationConfig(max_new_tokens=1 if warmup else 128, do_sample=sample,
                               eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id)
    set_seed(seed)
    if model.device.type == 'cuda': torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode():
        if sample:
            generated = model.generate(**inputs, generation_config=options, use_model_defaults=False,
                         do_sample=True, temperature=0.7, top_p=0.9, top_k=0, use_cache=True)
        else:
            generated = greedy_generate(model, inputs, options)
    if model.device.type == 'cuda': torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    tokens = generated[0, inputs['input_ids'].shape[1]:].cpu().tolist()
    return {'response': tokenizer.decode(tokens, skip_special_tokens=True), 'new_token_ids': tokens,
            'generated_tokens': len(tokens), 'prompt_tokens': inputs['input_ids'].shape[1],
            'prompt_sha256': hashlib.sha256(text.encode()).hexdigest(), 'wall_seconds': elapsed,
            'truncated': len(tokens) == options.max_new_tokens and tokens[-1] != tokenizer.eos_token_id,
            'generation_kwargs': {'do_sample': sample, 'use_model_defaults': False, 'max_new_tokens': options.max_new_tokens},
            'seed': seed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import torch, transformers, peft
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    if not torch.cuda.is_available(): raise RuntimeError('Free CUDA GPU unavailable; stop')
    packet_manifest = json.loads((args.packet / 'packet_manifest.json').read_text())
    for name, expected in packet_manifest['files_sha256'].items():
        path = (args.packet / name).resolve()
        if args.packet.resolve() not in path.parents or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Packet hash/path mismatch')
    cases, bible, digest = load_frozen(args.packet)
    if len(cases) != 240: raise ValueError('Expected unchanged 240-case benchmark')
    training = json.loads((args.packet / 'training_result.json').read_text())
    if not training['checkpoint_reload_passed'] or training['dtype'] != 'torch.float32':
        raise ValueError('Expected verified FP32 adapter')
    args.output.mkdir(parents=True, exist_ok=False)
    tokenizer = AutoTokenizer.from_pretrained(training['model'], revision=training['revision'], trust_remote_code=False)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != training['chat_template_sha256']:
        raise ValueError('Chat template changed')
    base = AutoModelForCausalLM.from_pretrained(training['model'], revision=training['revision'], dtype=torch.float32,
                device_map={'': 'cuda'}, low_cpu_mem_usage=True, attn_implementation='sdpa', trust_remote_code=False)
    model = PeftModel.from_pretrained(base, args.packet / 'adapter', is_trainable=False)
    model.eval()
    metadata = {'scope': 'frozen fixed-context HF comparison; not UE timing or model rollout',
                'eval_set_sha256': digest, 'model': training['model'], 'revision': training['revision'],
                'dtype': 'float32', 'gpu': torch.cuda.get_device_name(),
                'versions': {'torch': torch.__version__, 'transformers': transformers.__version__, 'peft': peft.__version__},
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'packet_manifest_sha256': hashlib.sha256((args.packet / 'packet_manifest.json').read_bytes()).hexdigest(),
                'training_steps': 0, 'quality_scores': 'pending review', 'case_count': len(cases),
                'generation': {'do_sample': False, 'use_model_defaults': False, 'max_new_tokens': 128, 'seed': 42}}
    (args.output / 'run_metadata.json').write_text(json.dumps(metadata, indent=2))
    times = {'Base': [], 'SFT': []}; truncated = {'Base': 0, 'SFT': 0}
    with (args.output / 'frozen_raw.jsonl').open('x', encoding='utf-8') as trace:
        for index, case in enumerate(cases):
            messages = messages_for(case, bible)
            for variant in (('Base', 'SFT') if index % 2 == 0 else ('SFT', 'Base')):
                with model.disable_adapter() if variant == 'Base' else nullcontext():
                    if index == 0: generate_one(model, tokenizer, messages, warmup=True)
                    reply = generate_one(model, tokenizer, messages)
                record = {'case_id': case['case_id'], 'variant': variant, 'case': case, 'messages': messages,
                          'order': index, 'world_actions': 'not_executed', 'scoring': 'pending_review', **reply}
                trace.write(json.dumps(record, ensure_ascii=False) + '\n'); trace.flush()
                times[variant].append(reply['wall_seconds']); truncated[variant] += reply['truncated']
            print(f"formal {index+1}/240 {case['case_id']}", flush=True)
    summary = {'metadata': metadata, 'responses': 480, 'variants': {v: {
        'p50_seconds': statistics.median(t), 'p95_seconds_nearest_rank': sorted(t)[math.ceil(.95*len(t))-1],
        'truncated': truncated[v]} for v,t in times.items()}}
    (args.output / 'formal_summary.json').write_text(json.dumps(summary, indent=2))
    # This is isolated from the benchmark and does not update the model.
    prompts = [json.loads(line) for line in (args.packet / 'preference_prompts.jsonl').read_text(encoding='utf-8').splitlines()]
    with (args.output / 'preference_candidates.jsonl').open('x', encoding='utf-8') as file:
        for index, row in enumerate(prompts):
            candidates = [generate_one(model, tokenizer, row['prompt'], sample=True, seed=1000+index*2+j) for j in range(2)]
            file.write(json.dumps({'sample_id': row['sample_id'], 'family_id': row['family_id'],
                'axis': row['axis'], 'prompt': row['prompt'], 'context': row['context'], 'candidates': candidates,
                'candidate_source': 'actual frozen SFT sampling', 'review_status': 'pending_human',
                'identical_text': candidates[0]['response'] == candidates[1]['response']}, ensure_ascii=False) + '\n')
            file.flush(); print(f'preference candidates {index+1}/{len(prompts)}', flush=True)
    print('Formal generation and preference sampling complete; quality/preference labels remain pending.', flush=True)


if __name__ == '__main__': main()
