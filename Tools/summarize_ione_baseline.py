"""Finalize a complete frozen raw run; quality ratings remain explicitly pending."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from eval_ione_dialogue import read_cases


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered)-1)*quantile
    low = int(index)
    high = min(low+1, len(ordered)-1)
    return ordered[low]+(ordered[high]-ordered[low])*(index-low)


def summarize(trace_path: Path, dataset_path: Path, manifest_path: Path) -> dict:
    cases, digest = read_cases(dataset_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    raw = trace_path.read_bytes()
    rows = [json.loads(x) for x in raw.decode('utf-8').splitlines()]
    metadata, records = rows[0], rows[1:]
    if (metadata.get('kind') != 'run' or manifest.get('status') != 'approved_frozen'
            or digest != metadata.get('eval_set_sha256') or digest != manifest.get('eval_set_sha256')):
        raise ValueError('Dataset/manifest/trace identity mismatch')
    if metadata.get('options') != manifest['generation_options'] or metadata.get('think') != manifest['think']:
        raise ValueError('Generation policy differs from frozen contract')
    if metadata.get('persona_sha256') != manifest['persona_sha256']:
        raise ValueError('Persona differs from frozen contract')
    if len(records) != len(cases) or metadata['count'] != len(cases):
        raise ValueError('Run is incomplete; do not finalize a partial baseline')
    for order, (record, case) in enumerate(zip(records, cases)):
        if record.get('kind') != 'case' or record['case'] != case or record['order'] != order:
            raise ValueError('Reordered, duplicated or changed case trace')
    latency = {}
    for label, subset in [('all_attempts', records), ('subsequent_requests', records[1:])]:
        values = [r['wall_seconds'] for r in subset]
        latency[label] = {'n':len(values), 'p50_seconds':percentile(values,.5),
                          'p95_seconds':percentile(values,.95), 'max_seconds':max(values, default=None)}
    status = Counter(r['status'] for r in records)
    metric_denominators = Counter(metric for case in cases for metric, yes in case['eligible'].items() if yes)
    return {'run_metadata':metadata, 'status':'raw_baseline_complete_quality_review_pending',
            'trace_sha256':hashlib.sha256(raw).hexdigest(), 'trace_path':str(trace_path),
            'eval_set_sha256':digest, 'attempted':len(records), 'generation_status':dict(status),
            'latency_scope':'offline local HTTP+generation wall time; no UE input/render or ToolGate execution',
            'cold_warm_status':'first/subsequent request only; cold/warm not certified',
            'latency':latency,
            'output_tokens':sum(r.get('response',{}).get('eval_count',0) for r in records),
            'prompt_tokens':sum(r.get('response',{}).get('prompt_eval_count',0) for r in records),
            'thinking_content_nonempty':sum(bool(r.get('response',{}).get('message',{}).get('thinking')) for r in records),
            'quality_metrics':{metric:{'planned_denominator':n,'reviewed':0,'value':None,
                                      'status':'pending_semantic_review'} for metric,n in metric_denominators.items()},
            'fallback_rate':None, 'fallback_status':'validator_not_applied_in_raw_eval',
            'illegal_executions':None, 'execution_status':'no_world_executor_in_this_offline_run',
            'records':records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.trace,args.cases,args.manifest)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','run_metadata')},indent=2))
