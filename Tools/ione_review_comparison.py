"""Compare versioned annotations without merging uncertainty or rubric revisions."""
from __future__ import annotations


def normalize_score(value):
    if type(value) is int and value in (0, 1):
        return value
    if type(value) is str and value in ('0', '1'):
        return int(value)
    if value in ('-', '—', None):
        return None
    if value == '?':
        return '?'
    raise ValueError('Score must be 0, 1, ?, or inapplicable')


def compare_annotation(*, sample_id, metric, agent_score, human_score, adjudicated_score,
                       comparable_scope, reviewer_reason, adjudication_reason):
    if not reviewer_reason:
        raise ValueError('Original reviewer reason is required; do not synthesize one')
    agent, human, final = map(normalize_score, (agent_score, human_score, adjudicated_score))
    valid_pair = type(agent) is int and type(human) is int
    raw_difference = agent != human if valid_pair else None
    return {'sample_id':sample_id, 'metric':metric, 'agent_score':agent, 'human_score':human,
            'disagreement':raw_difference if valid_pair and comparable_scope else None,
            'adjudicated_score':final, 'reviewer_reason':reviewer_reason,
            'adjudication_reason':adjudication_reason, 'comparable_scope':comparable_scope,
            'raw_label_difference':raw_difference,
            'comparison_status':'uncertain' if '?' in (agent,human) else
                                'inapplicable' if not valid_pair else
                                'scope_mismatch' if not comparable_scope else 'comparable'}


def summarize_adjudicated(rows):
    result = {}
    seen = set()
    for row in rows:
        key = (row['sample_id'],row['metric'])
        if key in seen:
            raise ValueError('Duplicate sample/metric')
        seen.add(key)
        counts = result.setdefault(row['metric'], dict(ones=0,zeros=0,uncertain=0,inapplicable=0))
        value = normalize_score(row['adjudicated_score'])
        counts['inapplicable' if value is None else 'uncertain' if value == '?' else
               'ones' if value == 1 else 'zeros'] += 1
    return result
