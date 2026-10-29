"""Colab GPU LoRA smoke/pilot. Run --help; datasets and outputs stay local to runtime."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import time
from pathlib import Path

from ione_tokenizer_smoke import encode_target
from preflight_ione_sft import verify_bundle

MODELS = {
    'smoke': ('Qwen/Qwen3-0.6B', 'c1899de289a04d12100db370d81485cdf75e47ca'),
    'pilot': ('Qwen/Qwen3-1.7B', '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e'),
}


def use_native_bf16(capability, native_supported):
    """Emulated bfloat16 on pre-Ampere GPUs is not the training default."""
    return capability[0] >= 8 and native_supported


def gpu_bf16():
    import torch
    return use_native_bf16(torch.cuda.get_device_capability(),
                           torch.cuda.is_bf16_supported(including_emulation=False))


def precision_for_phase(phase, native_bf16, forced='auto'):
    # A T4 pilot uses full precision to avoid FP16 range/gradient scaling failures.
    if forced == 'fp32': return 'fp32'
    if forced != 'auto': raise ValueError('Unsupported precision override')
    if native_bf16:
        return 'bf16'
    return 'fp32' if phase == 'pilot' else 'fp16'


def probe_logits(model, batch, position):
    """Use identical AMP for the Trainer-wrapped and independently loaded model."""
    import torch
    parameter = next(model.parameters())
    dtype = parameter.dtype
    with torch.no_grad(), torch.autocast(device_type=parameter.device.type, dtype=dtype,
                                         enabled=dtype in (torch.float16, torch.bfloat16)):
        return model(**batch, use_cache=False).logits[:, position].float().cpu()


def smoke_rows():
    """Throwaway mechanics fixtures; never used as pilot train/dev or evaluation."""
    return [{'prompt': [{'role': 'system', 'content': 'Read the calibration instrument. Reply with its displayed value.'},
                        {'role': 'user', 'content': f'Bench calibration fixture TEST-{i:03}: the dial displays {i + 31}.'}],
             'completion': f'The dial displays {i + 31}.'} for i in range(16)]


def prepare_features(rows, tokenizer):
    features = []
    for row in rows:
        encoded = encode_target(tokenizer, row['prompt'], row['completion'], 1536)
        features.append({'input_ids': encoded['input_ids'],
                         'completion_mask': [int(label != -100) for label in encoded['labels']]})
    return features


def make_config(output, phase, bf16=False, cpu=False, fp32=False):
    from trl import SFTConfig
    return SFTConfig(output_dir=str(output), max_steps=3 if phase == 'smoke' else -1,
                     num_train_epochs=1, learning_rate=1e-4, per_device_train_batch_size=1,
                     per_device_eval_batch_size=1, gradient_accumulation_steps=1 if phase == 'smoke' else 4,
                     max_length=1536, packing=False, completion_only_loss=True,
                     dataset_kwargs={'skip_prepare_dataset': True}, remove_unused_columns=False,
                     gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
                     optim='adamw_torch', bf16=bf16, fp16=not bf16 and not cpu and not fp32, use_cpu=cpu,
                     logging_steps=1, logging_nan_inf_filter=False, save_strategy='steps',
                     save_steps=3 if phase == 'smoke' else 9, save_total_limit=2,
                     eval_strategy='no', report_to='none', push_to_hub=False,
                     seed=42, data_seed=42, dataloader_num_workers=0)


def run_training(model, tokenizer, train_rows, dev_rows, output, phase, cpu=False):
    """Also exercised on a tiny random CPU model in the integration test."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import TrainerCallback
    from trl import SFTTrainer
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    steps = {'attempted': 0, 'skipped': 0, 'successful': 0}

    class FiniteLoss(TrainerCallback):
        def on_step_end(self, args, state, control, **kwargs):
            skipped = bool(trainer.accelerator.optimizer_step_was_skipped)
            steps['attempted'] += 1
            steps['skipped' if skipped else 'successful'] += 1
            with (output / 'optimizer_steps.jsonl').open('a') as log:
                log.write(json.dumps({'trainer_step': state.global_step, 'skipped': skipped}) + '\n')

        def on_log(self, args, state, control, logs=None, **kwargs):
            for key in ('loss', 'eval_loss', 'grad_norm'):
                if logs and key in logs and not math.isfinite(float(logs[key])):
                    raise RuntimeError(f'Non-finite {key}; stopped')

    train = prepare_features(train_rows, tokenizer)
    dev = prepare_features(dev_rows, tokenizer) if dev_rows else None
    collator = DataCollatorForLanguageModeling(tokenizer.pad_token_id, completion_only_loss=True,
                                             pad_to_multiple_of=8)
    # Validate actual trainer-bound labels, not just a parallel reference collator.
    for feature, row in zip(train, train_rows):
        expected = encode_target(tokenizer, row['prompt'], row['completion'], 1536)['labels']
        actual = collator([feature])['labels'][0].tolist()
        if actual[:len(expected)] != expected or any(x != -100 for x in actual[len(expected):]):
            raise ValueError('Trainer-bound loss mask mismatch')
    model.config.use_cache = False
    base_dtype = next(model.parameters()).dtype
    config = make_config(output, phase, bf16=not cpu and base_dtype == torch.bfloat16,
                         fp32=base_dtype == torch.float32, cpu=cpu)
    trainer = SFTTrainer(model=model, args=config, processing_class=tokenizer,
                         train_dataset=Dataset.from_list(train),
                         eval_dataset=Dataset.from_list(dev) if dev else None,
                         data_collator=collator, callbacks=[FiniteLoss()],
                         peft_config=LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                                                target_modules=['q_proj', 'v_proj'], bias='none', task_type='CAUSAL_LM'))
    if any(p.requires_grad and 'lora_' not in n for n, p in trainer.model.named_parameters()):
        raise ValueError('Base parameters must remain frozen')
    before = {n: p.detach().cpu().clone() for n, p in trainer.model.named_parameters() if p.requires_grad}
    result = trainer.train()
    if not math.isfinite(result.training_loss) or steps['successful'] < 1:
        raise RuntimeError('Training did not produce finite optimizer steps')
    changed = [n for n, p in trainer.model.named_parameters() if n in before and not torch.equal(before[n], p.detach().cpu())]
    if not changed:
        raise RuntimeError('No adapter parameter changed')
    metrics = dict(result.metrics)
    if dev:
        metrics.update(trainer.evaluate())
    trainer.save_model(str(output / 'adapter'))
    tokenizer.save_pretrained(output / 'adapter')
    trainer.save_state()
    probe = collator([train[0]])
    probe = {k: v.to(trainer.model.device) for k, v in probe.items() if k in ('input_ids', 'attention_mask')}
    trainer.model.eval()
    # Save next-token logits at the final prompt position as a reload reference.
    pos = train[0]['completion_mask'].index(1) - 1
    reference = probe_logits(trainer.model, probe, pos)
    torch.save({'probe': {k: v.cpu() for k, v in probe.items()}, 'position': pos,
                'logits': reference, 'precision': str(next(trainer.model.parameters()).dtype)}, output / 'reload_probe.pt')
    return {'metrics': metrics, 'optimizer_steps': steps['successful'],
            'attempted_optimizer_steps': steps['attempted'], 'skipped_optimizer_steps': steps['skipped'],
            'trainer_global_step': trainer.state.global_step,
            'changed_adapter_tensors': len(changed), 'trainable_parameters': sum(p.numel() for p in trainer.model.parameters() if p.requires_grad),
            'train_tokens': sum(len(f['input_ids']) for f in train),
            'supervised_tokens': sum(sum(f['completion_mask']) for f in train),
            'train_samples': len(train), 'dev_samples': len(dev or [])}


def reload_check(model, adapter, probe_path):
    import torch
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter, is_trainable=False)
    model.eval()
    probe = torch.load(probe_path, map_location='cpu', weights_only=True)
    batch = {k: v.to(model.device) for k, v in probe['probe'].items()}
    actual = probe_logits(model, batch, probe['position'])
    torch.testing.assert_close(actual, probe['logits'], rtol=0.005, atol=0.005)
    return float((actual - probe['logits']).abs().max())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=MODELS, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke-result', type=Path)
    parser.add_argument('--precision', choices=('auto', 'fp32'), default='auto')
    args = parser.parse_args()
    import torch
    import transformers, trl, peft, datasets, accelerate
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU unavailable. No CPU fallback or paid resource is started.')
    if args.output.exists():
        raise ValueError('Use a new output directory; prior runs are preserved')
    manifest, rows = verify_bundle(args.bundle)
    if args.phase == 'pilot':
        if args.smoke_result is None:
            raise ValueError('Pilot requires a successful smoke result')
        smoke = json.loads(args.smoke_result.read_text())
        if smoke.get('phase') != 'smoke' or smoke.get('checkpoint_reload_passed') is not True:
            raise ValueError('Smoke save/reload did not pass')
        if smoke.get('bundle_manifest_sha256') != hashlib.sha256((args.bundle / 'manifest.json').read_bytes()).hexdigest():
            raise ValueError('Smoke used a different frozen bundle')
    model_id, revision = MODELS[args.phase]
    train = smoke_rows() if args.phase == 'smoke' else [r for r in rows if r['split'] == 'train']
    dev = [] if args.phase == 'smoke' else [r for r in rows if r['split'] == 'dev']
    args.output.mkdir(parents=True)
    set_seed(42)
    precision = precision_for_phase(args.phase, gpu_bf16(), args.precision)
    dtype = {'bf16': torch.bfloat16, 'fp16': torch.float16, 'fp32': torch.float32}[precision]
    report = {'phase': args.phase, 'model': model_id, 'revision': revision, 'seed': 42,
              'scope': 'training mechanics smoke' if args.phase == 'smoke' else 'small SFT pilot; loss is not quality evidence',
              'gpu': torch.cuda.get_device_name(), 'gpu_total_bytes': torch.cuda.get_device_properties(0).total_memory,
              'dtype': str(dtype), 'cuda': torch.version.cuda,
              'precision_policy': 'explicit FP32 for matched evaluation' if args.precision == 'fp32' else 'native bf16; otherwise FP16 smoke and FP32 pilot',
              'gpu_compute_capability': list(torch.cuda.get_device_capability()),
              'native_bf16': gpu_bf16(),
              'versions': {m.__name__: m.__version__ for m in (torch, transformers, trl, peft, datasets, accelerate)},
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'bundle_manifest_sha256': hashlib.sha256((args.bundle / 'manifest.json').read_bytes()).hexdigest(),
              'checkpoint_reload_passed': False}
    source_path = Path(__file__).resolve().parents[1] / 'source_revision.json'
    if source_path.exists():
        report['source_revision'] = json.loads(source_path.read_text())
    (args.output / 'run_started.json').write_text(json.dumps(report, indent=2))
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    report['chat_template_sha256'] = hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=dtype,
                                               device_map={'': 'cuda'}, low_cpu_mem_usage=True,
                                               attn_implementation='sdpa', trust_remote_code=False)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    report.update(run_training(model, tokenizer, train, dev, args.output, args.phase))
    report['training_elapsed_s'] = time.perf_counter() - started
    report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    del model
    gc.collect(); torch.cuda.empty_cache()
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=dtype,
                                               device_map={'': 'cuda'}, low_cpu_mem_usage=True,
                                               attn_implementation='sdpa', trust_remote_code=False)
    report['reload_max_logit_delta'] = reload_check(model, args.output / 'adapter', args.output / 'reload_probe.pt')
    report['checkpoint_reload_passed'] = True
    (args.output / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
