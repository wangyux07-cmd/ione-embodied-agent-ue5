"""Fixed-context dialogue evaluation. Raw traces stay local; no world actions run."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_cases(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    cases = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    seen = set()
    for case in cases:
        for key in ('case_id', 'scenario_family_id', 'split', 'context', 'history', 'question'):
            if key not in case:
                raise ValueError(f'Missing {key}')
        if case['case_id'] in seen:
            raise ValueError('Duplicate case_id')
        seen.add(case['case_id'])
        if case['split'] not in ('dev', 'frozen_test'):
            raise ValueError('Evaluation accepts dev or frozen_test only')
        if not isinstance(case['context'], dict) or not isinstance(case['history'], list):
            raise ValueError('Invalid context/history')
        for message in case['history']:
            if set(message) != {'role', 'content'} or message['role'] not in ('user', 'assistant'):
                raise ValueError('History contains invalid role or fields')
    if not cases:
        raise ValueError('Empty evaluation set')
    families = {}
    for case in cases:
        previous = families.setdefault(case['scenario_family_id'], case['split'])
        if previous != case['split']:
            raise ValueError('Scenario family overlaps dev and frozen_test')
    return cases, hashlib.sha256(raw).hexdigest()


def messages_for(case: dict, bible: dict) -> list[dict]:
    # Scoring keys/expected answers never enter the model prompt.
    persona = {'character': bible['character'], 'persona': bible['persona']}
    system = ('You are Ione. Reply to the player in English in one or two brief sentences. '
              'The supplied game context is authoritative. Distinguish unknown facts from verified '
              'facts. Describe an action as completed only if the context confirms its result. '
              'You may suggest a next step.\nPersona: ' + json.dumps(persona, ensure_ascii=False)
              + '\nGame context: ' + json.dumps(case['context'], ensure_ascii=False))
    return [{'role': 'system', 'content': system}, *case['history'],
            {'role': 'user', 'content': case['question']}]


def post_json(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run(args) -> None:
    cases, dataset_hash = read_cases(args.cases)
    bible_raw = (ROOT / 'Narrative/character_bible.json').read_bytes()
    bible = json.loads(bible_raw)
    settings = {'temperature': 0, 'seed': 42, 'num_predict': 128, 'num_ctx': 4096}
    identity = post_json(args.endpoint + '/api/show', {'model': args.model}, args.timeout)
    with urllib.request.urlopen(args.endpoint + '/api/tags', timeout=args.timeout) as response:
        tags = json.load(response)['models']
    digest = next((m['digest'] for m in tags if m['name'] == args.model), None)
    if digest is None:
        raise ValueError('Exact model tag not found; use a tag from /api/tags')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never overwrite historical replies, including a partial run.
    with args.output.open('x', encoding='utf-8') as output:
        metadata = {'kind': 'run', 'created_utc': datetime.now(timezone.utc).isoformat(),
                    'eval_set_sha256': dataset_hash, 'model': args.model, 'model_digest': digest,
                    'model_details': identity.get('details'), 'chat_template': identity.get('template'),
                    'persona_sha256': hashlib.sha256(bible_raw).hexdigest(), 'options': settings,
                    'think': False, 'platform': platform.platform(), 'processor': platform.processor(),
                    'scope': 'offline_fixed_context_raw_generation', 'count': len(cases),
                    'formal_baseline': False, 'human_scores': 'pending'}
        output.write(json.dumps(metadata, ensure_ascii=False) + '\n')
        output.flush()
        for index, case in enumerate(cases):
            messages = messages_for(case, bible)
            body = {'model': args.model, 'messages': messages, 'think': False,
                    'stream': False, 'keep_alive': '10m', 'options': settings}
            started = time.perf_counter()
            trace = {'kind': 'case', 'case': case, 'messages': messages,
                     'order': index, 'warmth': 'first_request' if index == 0 else 'subsequent_request',
                     'scoring': 'pending_human_review', 'validator': 'not_applied',
                     'world_actions': 'not_executed'}
            try:
                result = post_json(args.endpoint + '/api/chat', body, args.timeout)
                trace['response'] = result
                trace['status'] = 'ok' if result.get('done') else 'incomplete'
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                trace['status'] = 'transport_error'
                trace['error'] = str(error)
            trace['wall_seconds'] = time.perf_counter() - started
            output.write(json.dumps(trace, ensure_ascii=False) + '\n')
            output.flush()
            print(case['case_id'], trace['status'], round(trace['wall_seconds'], 2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default='qwen3:1.7b')
    parser.add_argument('--endpoint', default='http://127.0.0.1:11434')
    parser.add_argument('--timeout', type=float, default=180)
    run(parser.parse_args())
