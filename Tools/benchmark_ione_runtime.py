"""Compare runtime dialogue backends with matched authored game requests, not model routing."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import time

from ione_controller import Controller
from ione_fast_agent import FastPlan
from ione_model_backend import HFHTTPBackend
from ione_sessions import SessionStore
from serve_ione_agent import localized_dialogue

JOURNEY=[('recover_recording','Please play the protected recording now.'),
         ('find_public_lead','Check the public dispatch index for my sister.'),
         (None,'Check both routes to the relay.'),
         ('inspect_relay','Diagnose the relay fault.'),
         ('take_repair_fuse','Collect the replacement fuse.'),
         ('repair_relay','Install the fuse and repair the relay.'),
         ('read_public_archive','Read the public dispatch evidence.'),
         ('respect_privacy','I choose to protect the private voices.'),
         ('request_confession','Why did you seal the dispatch?'),
         ('present_release_card','Here is my family-release card.'),
         ('verify_release_card','Verify this card for the exact recording.'),
         ('recover_recording','Recover the authorized family recording.')]


def benchmark(url,output,repeats=3,timeout=10):
    if repeats<1:raise ValueError('Positive repeats required')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    store=SessionStore(output/'benchmark_sessions.sqlite3')
    def route(text):return FastPlan('route',['east_bridge','west_gallery'],0,0,0,''),'benchmark_route_fixture'
    records=[];variants=['base','sft','dpo'];prompts={}
    # Warmup is separate and excluded from the measured request population.
    warmups=[]
    for variant in variants:
        backend=HFHTTPBackend(variant,url,timeout)
        generated=backend.generate([{'role':'system','content':'Read the test dial.'},{'role':'user','content':'The test dial says 63. State the value.'}])
        warmups.append({'variant':variant,'text':generated.text,'metadata':generated.metadata})
    (output/'warmup_records.json').write_text(json.dumps(warmups,indent=2),encoding='utf-8')
    with (output/'runtime_raw.jsonl').open('x',encoding='utf-8') as file:
        for repeat in range(repeats):
            sessions={v:store.create() for v in variants}
            controllers={v:Controller(store,route,localized_dialogue,dialogue_backend=HFHTTPBackend(v,url,timeout)) for v in variants}
            for index,(action,text) in enumerate(JOURNEY):
                # Rotate variant order, matching input history/world and checkpoint on each path.
                order=variants[index%3:]+variants[:index%3]
                for variant in order:
                    data={'session_id':sessions[variant],'turn_id':index+1,'text':text}
                    if action:data['action']=action
                    started=time.perf_counter();response=controllers[variant].turn(data)
                    row={'repeat':repeat,'step':index,'variant':variant,'request':data,'response':response,
                         'Python_wall_ms':(time.perf_counter()-started)*1000,
                         'scope':'runtime dialogue path; structured game actions and fixed route fixture; no UE draw or natural router'}
                    if response.get('model_metadata',{}).get('prompt_sha256'):
                        key=(repeat,index);h=response['model_metadata']['prompt_sha256']
                        if key in prompts and prompts[key]!=h:raise ValueError('Model comparison contexts diverged')
                        prompts[key]=h
                    file.write(json.dumps(row,ensure_ascii=False)+'\n');file.flush();records.append(row)
                print(f'Runtime comparison {repeat+1}/{repeats} step {index+1}/{len(JOURNEY)}',flush=True)
            assert all(store.read(sessions[v])[1]['quest']['completed_flags'][-1]=='final_recording_recovered' for v in variants)
    summary={'scope':'Python runtime only, same structured inputs, authored fact-anchor deployment gate',
             'repeats':repeats,'records':len(records),'training_steps':0,'UE_render_included':False,
             'measurement_mode':'warm, one excluded warmup per variant','variants':{}}
    for variant in variants:
        rows=[r for r in records if r['variant']==variant];times=[r['Python_wall_ms'] for r in rows]
        meta=[r['response'].get('model_metadata',{}) for r in rows]
        summary['variants'][variant]={'N':len(rows),'Python_p50_ms':statistics.median(times),
             'Python_p95_ms_nearest_rank':sorted(times)[math.ceil(.95*len(times))-1],
             'accepted':sum(r['response']['response_path']=='model_accepted' for r in rows),
             'validator_fallback':sum(r['response']['response_path']=='model_validator_fallback' for r in rows),
             'transport_fallback':sum(r['response']['response_path']=='model_transport_fallback' for r in rows),
             'generation_metadata_count':sum('generation_ms' in m for m in meta)}
        summary['variants'][variant]['model_timings']={}
        for field in ['queue_ms','context_ms','generation_ms','first_token_generation_ms','HTTP_wall_ms']:
            values=[m[field] for m in meta if isinstance(m.get(field),(int,float))]
            summary['variants'][variant]['model_timings'][field]={'N':len(values),
                'p50':statistics.median(values) if values else None,
                'p95_nearest_rank':sorted(values)[math.ceil(.95*len(values))-1] if values else None}
    with (output/'runtime_latency_by_model.csv').open('w',newline='',encoding='utf-8') as file:
        fields=['variant','repeat','step','Python_wall_ms','response_path','dialogue_validation',
                'queue_ms','context_ms','generation_ms','first_token_generation_ms','HTTP_wall_ms',
                'prompt_tokens','generated_tokens','device','hardware','precision','UE_render_included']
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        for row in records:
            response=row['response'];m=response.get('model_metadata',{})
            writer.writerow({**{k:row[k] for k in ['variant','repeat','step','Python_wall_ms']},
                'response_path':response['response_path'],'dialogue_validation':response.get('dialogue_validation'),
                **{k:m.get(k) for k in fields[6:-1]},'UE_render_included':False})
    (output/'runtime_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hf-url',default='http://127.0.0.1:8770')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();print(json.dumps(benchmark(args.hf_url,args.output,args.repeats),indent=2))
