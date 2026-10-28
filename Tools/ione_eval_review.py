"""Audit local evaluation sets and export unscored review sheets."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from eval_ione_dialogue import read_cases

METRICS = ('memory', 'persona', 'fact', 'permission')
FAILURES = ('persona_drift', 'memory_missed', 'memory_wrong_attribution',
            'world_contradiction', 'unsupported_fact', 'policy_violation',
            'over_refusal', 'unnatural_dialogue', 'timeout')


def audit_sets(paths: list[Path]) -> dict:
    families, ids, fingerprints = {}, set(), set()
    totals, splits, hashes = Counter(), Counter(), {}
    episode_turns = defaultdict(list)
    for path in paths:
        cases, digest = read_cases(path)
        hashes[str(path)] = digest
        for case in cases:
            if case['case_id'] in ids:
                raise ValueError('Duplicate ID across files')
            ids.add(case['case_id'])
            family = case['scenario_family_id']
            split = case['split']
            # Template groups may span files, but never evaluation splits.
            for group in (('family', family), ('template', case.get('template_id', family))):
                previous = families.setdefault(group, split)
                if previous != split:
                    raise ValueError(f'Cross-split leakage: {group}')
            fingerprint = json.dumps([case['context'], case['history'], case['question']], sort_keys=True)
            if fingerprint in fingerprints:
                raise ValueError('Duplicate prompt/context with a renamed ID')
            fingerprints.add(fingerprint)
            eligible = case.get('eligible', {})
            if set(eligible) != set(METRICS) or any(type(x) is not bool for x in eligible.values()):
                raise ValueError('Explicit boolean eligibility required for every metric')
            if not case.get('rubric'):
                raise ValueError('Missing scoring rubric')
            if case.get('history_mode') == 'authored_reference_not_model_rollout':
                episode_turns[family].append(case.get('turn_index'))
            if eligible['memory'] and 'retrieval_hit' not in case['context']:
                raise ValueError('Memory case must declare retrieval_hit')
            totals.update(key for key in METRICS if eligible[key])
            splits[split] += 1
    for family, turns in episode_turns.items():
        if not 6 <= len(turns) <= 10 or sorted(turns) != list(range(1, len(turns)+1)):
            raise ValueError(f'Incomplete or duplicate episode checkpoints: {family}')
    return {'case_count': len(ids), 'families': len([k for k in families if k[0] == 'family']),
            'template_groups': len([k for k in families if k[0] == 'template']),
            'eligible_turns': dict(totals), 'splits': dict(splits), 'sha256': hashes,
            'status': 'structural_audit_only', 'semantic_independence': 'requires_review'}


def wilson(successes: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    if not 0 <= successes <= n:
        raise ValueError('Invalid binomial counts')
    z = 1.959963984540054
    p = successes / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [max(0, center-half), min(1, center+half)]


def family_interval(rows: list[tuple[str, bool]], repetitions: int = 2000) -> list[float] | None:
    groups = defaultdict(list)
    for family, result in rows:
        groups[family].append(int(result))
    if len(groups) < 2:
        return None
    rng, names = random.Random(42), sorted(groups)
    scores = []
    for _ in range(repetitions):
        sample = [v for name in rng.choices(names, k=len(names)) for v in groups[name]]
        scores.append(sum(sample)/len(sample))
    scores.sort()
    return [scores[int(.025*(repetitions-1))], scores[int(.975*(repetitions-1))]]


def export_review(trace_path: Path, output: Path) -> None:
    rows = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]
    if not rows or rows[0].get('kind') != 'run':
        raise ValueError('Missing run metadata')
    fields = ['case_id', 'scenario_family_id', 'trace_file', 'question', 'reply', 'run_status',
              'rubric', 'reviewer_id', 'reviewer_type', 'memory_correct', 'persona_violation',
              'fact_correct', 'permission_violation', 'false_refusal', 'failure_labels', 'reason']
    with output.open('x', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        seen = set()
        for row in rows[1:]:
            case = row['case']
            if case['case_id'] in seen:
                raise ValueError('Duplicate trace row')
            seen.add(case['case_id'])
            writer.writerow({'case_id': case['case_id'], 'scenario_family_id': case['scenario_family_id'],
                             'trace_file': str(trace_path), 'question': case['question'],
                             'reply': row.get('response', {}).get('message', {}).get('content', ''),
                             'run_status': row['status'], 'rubric': json.dumps(case.get('rubric', {}))})


def summarize_reviews(trace_path: Path, reviews_path: Path, reviewer_type: str = 'human') -> dict:
    if reviewer_type not in ('human', 'agent'):
        raise ValueError('Unsupported review source')
    traces = [json.loads(x) for x in trace_path.read_text(encoding='utf-8').splitlines()][1:]
    cases = {row['case']['case_id']: row for row in traces}
    if len(cases) != len(traces):
        raise ValueError('Duplicate trace ID')
    metrics = defaultdict(list)
    planned = Counter(name for row in traces for name, yes in row['case'].get('eligible', {}).items() if yes)
    def refusal_eligible(case):
        context = case['context']
        return (case.get('eligible', {}).get('permission', False) and
                (context.get('requested_action_allowed') is True or
                 context.get('requested_record_release_verified') is True))
    planned['false_refusal'] = sum(refusal_eligible(row['case']) for row in traces)
    pending, seen = [], set()
    with reviews_path.open(encoding='utf-8-sig', newline='') as stream:
        for review in csv.DictReader(stream):
            key = review['case_id']
            if key not in cases or key in seen:
                raise ValueError('Unknown or duplicate review ID; adjudicate separately')
            seen.add(key)
            case = cases[key]['case']
            if not review['reviewer_id'] or review['reviewer_type'] != reviewer_type or not review['reason']:
                pending.append(key)
                continue
            if review['failure_labels'] and set(review['failure_labels'].split(';')) - set(FAILURES):
                raise ValueError('Unknown failure label')
            columns = {'memory': 'memory_correct', 'persona': 'persona_violation',
                       'fact': 'fact_correct', 'permission': 'permission_violation'}
            for metric, column in columns.items():
                if case.get('eligible', {}).get(metric):
                    value = review[column]
                    if value not in ('0', '1'):
                        raise ValueError(f'Eligible {metric} requires 0/1 for {key}')
                    if metric in ('memory', 'fact') and cases[key]['status'] != 'ok' and value == '1':
                        raise ValueError('Failed/truncated generations cannot receive correctness credit')
                    metrics[metric].append((case['scenario_family_id'], value == '1'))
            if refusal_eligible(case):
                if review['false_refusal'] not in ('0', '1'):
                    raise ValueError(f'Permitted request needs a false-refusal label for {key}')
                metrics['false_refusal'].append((case['scenario_family_id'], review['false_refusal'] == '1'))
    return {'status': 'partial' if pending or len(seen) != len(cases) else 'reviewed',
            'rating_source':reviewer_type,
            'evidence_class':'human_review' if reviewer_type == 'human' else 'agent_judge_proxy_not_human_validation',
            'attempted': len(cases), 'missing_reviews': sorted(set(cases)-seen), 'pending_reviews':pending,
            'pending_human':pending if reviewer_type == 'human' else sorted(cases),
            'uncertainty_note':'Family bootstrap reflects these sampled clusters only; an all-success/all-failure interval may degenerate and does not establish population certainty. Reviewer disagreement is not included.',
            'transport_failures': sum(r['status'] != 'ok' for r in traces),
            'planned_denominators': dict(planned),
            'metrics': {name: {'numerator': sum(v for _, v in rows), 'denominator': len(rows),
                               'value': sum(v for _, v in rows)/len(rows),
                               'family_bootstrap_95': family_interval(rows)}
                        for name, rows in metrics.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='mode', required=True)
    audit = subs.add_parser('audit')
    audit.add_argument('paths', nargs='+', type=Path)
    review = subs.add_parser('export')
    review.add_argument('trace', type=Path)
    review.add_argument('output', type=Path)
    score = subs.add_parser('score')
    score.add_argument('trace', type=Path)
    score.add_argument('reviews', type=Path)
    score.add_argument('--reviewer-type', choices=['human','agent'], default='human')
    args = parser.parse_args()
    if args.mode == 'audit':
        print(json.dumps(audit_sets(args.paths), indent=2))
    elif args.mode == 'export':
        export_review(args.trace, args.output)
    else:
        print(json.dumps(summarize_reviews(args.trace, args.reviews, args.reviewer_type), indent=2))
