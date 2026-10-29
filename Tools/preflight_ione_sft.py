"""Verify a frozen SFT bundle, actual TRL masks and storage-free LoRA architecture.

Example: python Tools/preflight_ione_sft.py --bundle PATH --tokenizer PATH --output PATH
Requires requirements-m6-preflight.txt. No pretrained tensors or optimizer are loaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ione_data_pipeline import read_jsonl, stable_write, validate_sample
from ione_tokenizer_smoke import encode_target


def verify_bundle(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['status'] != 'approved_frozen':
        raise ValueError('Bundle is not approved and frozen')
    required = {f'sft_{split}{suffix}.jsonl' for split in ('train', 'dev') for suffix in ('', '_canonical')}
    if not required <= manifest['files_sha256'].keys():
        raise ValueError('Manifest omits required SFT hashes')
    for name, expected in manifest['files_sha256'].items():
        path = (root / name).resolve()
        if path.parent != root.resolve():
            raise ValueError('Manifest path escapes bundle')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen hash mismatch: {name}')
    rows = []
    families = {}
    for split in ('train', 'dev'):
        canonical = read_jsonl(root / f'sft_{split}_canonical.jsonl')
        exported = read_jsonl(root / f'sft_{split}.jsonl')
        if not canonical or len(canonical) != manifest['counts'][f'SFT_{split}']:
            raise ValueError('SFT count mismatch')
        expected = []
        for row in canonical:
            validate_sample(row)
            if row['kind'] != 'sft' or row['split'] != split or row['review_status'] != 'approved_human':
                raise ValueError('Unapproved or misplaced SFT row')
            expected.append({'prompt': row['prompt'], 'completion': [{'role': 'assistant', 'content': row['completion']}]})
        if exported != expected:
            raise ValueError('Training export differs from approved payload')
        families[split] = {r['family_id'] for r in canonical}
        rows.extend(canonical)
    if families['train'] & families['dev']:
        raise ValueError('Train/dev family overlap')
    return manifest, rows


def check_collator(rows, tokenizer, max_length=1536):
    import torch
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    encoded = [encode_target(tokenizer, r['prompt'], r['completion'], max_length) for r in rows]
    features = [{'input_ids': r['input_ids'], 'completion_mask': [int(x != -100) for x in r['labels']]} for r in encoded]
    collator = DataCollatorForLanguageModeling(tokenizer.pad_token_id, completion_only_loss=True, pad_to_multiple_of=8)
    padded = 0
    for start in range(0, len(features), 3):
        batch = collator(features[start:start + 3])
        for index, row in enumerate(encoded[start:start + 3]):
            size = len(row['input_ids'])
            if batch['labels'][index, :size].tolist() != row['labels']:
                raise ValueError('TRL completion labels differ from reference')
        mask = batch['attention_mask'] == 0
        if not bool(torch.all(batch['labels'][mask] == -100)):
            raise ValueError('Padding participates in loss')
        padded += int(mask.sum())
    if not padded:
        raise ValueError('Padding was not exercised')
    return {'sequences': len(encoded), 'max_tokens': max(len(r['input_ids']) for r in encoded),
            'padded_positions': padded, 'completion_labels_match': True, 'max_length': max_length}


def check_lora(tokenizer_dir):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model
    config = AutoConfig.from_pretrained(tokenizer_dir, local_files_only=True, trust_remote_code=False)
    with torch.device('meta'):
        model = AutoModelForCausalLM.from_config(config, dtype=torch.float32)
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=['q_proj', 'v_proj'],
                                                lora_dropout=0.05, bias='none', task_type='CAUSAL_LM', init_lora_weights=False))
    parameters = list(model.named_parameters())
    if not all(p.is_meta for _, p in parameters):
        raise ValueError('Architecture check allocated real model tensors')
    trainable = [(n, p) for n, p in parameters if p.requires_grad]
    if not trainable or any('lora_' not in n for n, _ in trainable):
        raise ValueError('Base weights are trainable or adapter is missing')
    return {'device': 'meta', 'model_type': config.model_type, 'layers': config.num_hidden_layers,
            'trainable_parameters': sum(p.numel() for _, p in trainable),
            'total_parameters': sum(p.numel() for _, p in parameters),
            'adapter_tensors': len(trainable), 'rank': 8, 'alpha': 16, 'targets': ['q_proj', 'v_proj'],
            'all_base_parameters_frozen': True, 'pretrained_tensors_loaded': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import torch, transformers, trl, peft
    from transformers import AutoTokenizer
    manifest, rows = verify_bundle(args.bundle)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, trust_remote_code=False)
    report = {'scope': 'TRL collator and meta architecture preflight; no Trainer, forward, backward or checkpoint test',
              'training_started': False, 'cuda_available': torch.cuda.is_available(),
              'versions': dict(torch=torch.__version__, transformers=transformers.__version__, trl=trl.__version__, peft=peft.__version__),
              'bundle_manifest_sha256': hashlib.sha256((args.bundle / 'manifest.json').read_bytes()).hexdigest(),
              'collator': check_collator(rows, tokenizer), 'lora': check_lora(args.tokenizer),
              'counts': manifest['counts']}
    stable_write(args.output, json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
