"""Local post-training data contracts, split/leakage audit and reviewed exports."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def stable_write(path, text):
    path=Path(path); raw=text.encode('utf-8')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Refusing to replace different existing data')
        return
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))


def get_fact(context,key):
    value=context
    for part in key.split('.'):
        value=value[part]
    return value


def validate_sample(row):
    required={'sample_id','family_id','template_id','split','kind','prompt','context','evidence',
              'review_status','review_source','tags','target_claims'}
    if required-set(row):raise ValueError('Missing data contract fields')
    if row['kind'] not in ('sft','preference'):raise ValueError('Unknown data kind')
    if row['split'] not in ('train','dev'):raise ValueError('Only explicit train/dev candidates allowed')
    if row['review_status'] not in ('pending_human','approved_human','rejected','tie','skip'):
        raise ValueError('Invalid review status')
    if row['review_status']=='approved_human' and (row['review_source'].get('type')!='human' or
           not row['review_source'].get('reference')):
        raise ValueError('Human approval requires human source and review reference')
    if not row['evidence'].get('source') or not row['evidence'].get('snapshot_id'):
        raise ValueError('Missing evidence provenance')
    prompt=row['prompt']
    if not prompt or prompt[0]['role']!='system' or prompt[-1]['role']!='user':
        raise ValueError('Prompt must start with system and end with user')
    for message in prompt:
        if set(message)!={'role','content'} or not isinstance(message['content'],str) or not message['content']:
            raise ValueError('Invalid message')
        if message['role'] not in ('system','user','assistant'):raise ValueError('Invalid role')
    if any(m['role']=='system' for m in prompt[1:]):raise ValueError('History system injection')
    target=row.get('completion') if row['kind']=='sft' else row.get('chosen')
    if not isinstance(target,str) or not target.strip():raise ValueError('Empty target')
    if '<think>' in target or '</think>' in target:raise ValueError('Thinking content in target')
    for claim in row['target_claims']:
        if set(claim)!={'key','value'}:raise ValueError('Invalid claim binding')
        if get_fact(row['context'],claim['key'])!=claim['value']:
            raise ValueError('Claim contradicts authoritative snapshot')
    # A conservative tripwire, not a semantic entailment score.
    if re.search(r'\bI (?:have )?(?:completed|sent|published)\b',target,re.I):
        if row['context'].get('action',{}).get('committed') is not True:
            raise ValueError('Completion tripwire without committed evidence')
    if row['kind']=='preference':
        if not row.get('rejected') or row['chosen'].strip()==row['rejected'].strip():
            raise ValueError('Preference alternatives must differ')
        if not row.get('preference_reasons') or not row.get('candidate_source'):
            raise ValueError('Preference provenance required')


def prompt_fingerprint(row):
    return hashlib.sha256(canonical(row['prompt']).encode()).hexdigest()


def similarity_text(row):
    # Shared persona text is intentionally excluded; world context and dialogue remain.
    context=row.get('context',{})
    messages=row.get('prompt') or row.get('history',[])+[{'role':'user','content':row.get('question','')}]
    return canonical(context)+' '+' '.join(m['content'] for m in messages if m['role']!='system')


def shingles(text,size=5):
    words=re.findall(r'[a-z0-9]+',text.lower())
    return {tuple(words[i:i+size]) for i in range(len(words)-size+1)}


def similarity(a,b):
    x,y=shingles(a),shingles(b)
    return len(x&y)/len(x|y) if x and y else 0.


def audit(rows, reserved, near_threshold=.75):
    ids=set();groups={};fingerprints={};near=[]
    reserved_groups={r.get('family_id',r.get('scenario_family_id')) for r in reserved}
    reserved_templates={r.get('template_id',r.get('scenario_family_id')) for r in reserved}
    reserved_text=[similarity_text(r) for r in reserved]
    for index,row in enumerate(rows):
        validate_sample(row)
        if row['sample_id'] in ids:raise ValueError('Duplicate sample ID')
        ids.add(row['sample_id'])
        if row['family_id'] in reserved_groups or row['template_id'] in reserved_templates:
            raise ValueError('Reserved family/template leakage')
        for group in (('family',row['family_id']),('template',row['template_id'])):
            split=groups.setdefault(group,row['split'])
            if split!=row['split']:raise ValueError('Train/dev family or template overlap')
        fingerprint=(row['kind'],prompt_fingerprint(row))
        if fingerprint in fingerprints:raise ValueError('Duplicate same-kind prompt')
        fingerprints[fingerprint]=index
        text=similarity_text(row)
        for other in reserved_text:
            if text==other:raise ValueError('Exact reserved content leakage')
            score=similarity(text,other)
            if score>=near_threshold:raise ValueError('Near-duplicate reserved content')
        for previous in rows[:index]:
            # The same training prompt may legitimately have SFT and preference
            # versions, but changing data kind must never bypass split isolation.
            if previous['kind']!=row['kind'] and previous['split']==row['split']:continue
            score=similarity(text,similarity_text(previous))
            if score>=near_threshold:
                near.append({'left':previous['sample_id'],'right':row['sample_id'],'similarity':score,
                             'cross_split':previous['split']!=row['split']})
    if any(item['cross_split'] for item in near):raise ValueError('Near-duplicate train/dev leakage')
    return {'samples':len(rows),'by_kind':dict(Counter(r['kind'] for r in rows)),
            'by_split':dict(Counter(r['split'] for r in rows)),
            'by_review_status':dict(Counter(r['review_status'] for r in rows)),
            'tag_counts':dict(Counter(tag for r in rows for tag in r['tags'])),
            'reserved_records_checked':len(reserved),'family_template_overlap':0,
            'near_threshold':near_threshold,'near_pairs_pending_review':near,
            'semantic_entailment':'not guaranteed by structural/lexical checks; author and human review required'}


def split_candidates(rows):
    return {f'{kind}_{split}':[r for r in rows if r['kind']==kind and r['split']==split]
            for kind in ('sft','preference') for split in ('train','dev')}


def export_approved(rows):
    exported=[]
    for row in rows:
        validate_sample(row)
        if row['review_status']!='approved_human':
            raise ValueError('Unreviewed/rejected/tie/skip data cannot enter training export')
        output={'prompt':row['prompt']}
        if row['kind']=='sft':output['completion']=[{'role':'assistant','content':row['completion']}]
        else:
            output.update(chosen=[{'role':'assistant','content':row['chosen']}],
                          rejected=[{'role':'assistant','content':row['rejected']}])
        exported.append(output)
    return exported


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['build','validate','split','export'])
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--reserved',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();rows=read_jsonl(args.input)
    reserved=[r for path in args.reserved for r in read_jsonl(path)]
    result=audit(rows,reserved)
    if args.mode=='validate':print(json.dumps(result,indent=2))
    elif args.mode=='build':
        if not args.output:parser.error('--output candidate file required')
        stable_write(args.output,''.join(canonical(row)+'\n' for row in rows))
    elif args.mode=='split':
        if not args.output:parser.error('--output directory required')
        for name,items in split_candidates(rows).items():
            stable_write(args.output/(name+'.jsonl'),''.join(canonical(r)+'\n' for r in items))
    else:
        if not args.output:parser.error('--output file required')
        stable_write(args.output,''.join(canonical(r)+'\n' for r in export_approved(rows)))
