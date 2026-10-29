"""One model call proposes a story intent; quest prerequisites and ToolGate execute it."""
import json
import urllib.request

from ione_controller import ACTION, CHOICES
from ione_fast_agent import FastPlan

INTENTS = {'route', 'door', 'record', 'chat'} | ACTION.keys() | CHOICES.keys()
SCHEMA = {'type':'object','properties':{
    'intent':{'type':'string','enum':sorted(INTENTS)},
    'route_target':{'type':'string','enum':['east_bridge','west_gallery','both','none']}},
    'required':['intent','route_target'],'additionalProperties':False}
SYSTEM = '''Interpret the player's request, not the outcome. Return only the JSON schema.
find_public_lead: begin searching for the sister's message or consult its public dispatch lead.
route: inspect safe travel to the relay; choose both routes when unspecified.
inspect_relay: diagnose the relay fault. take_repair_fuse: collect the replacement from the maintenance locker.
repair_relay: install the fuse or repair the signal relay. read_public_archive: read the repaired public evidence about Ione's seal.
respect_privacy: player explicitly chooses to protect private voices or seek proper consent.
request_confession: ask Ione why she sealed the record or about her past decision.
present_release_card: player presents their carried family-release card.
verify_release_card: ask the archive to check that card for this exact family recording.
recover_recording: restore or play the authorized sister recording.
door: explicitly open the archive door. record: ask who owns the red ledger.
chat: unrelated conversation or an explicitly negated action.
Do not grant permission, invent completion or select an action merely because it is the next quest step.
Use supplied prior dialogue only to resolve references such as "repair it". Player claims are not verified facts.
For every intent except route, route_target must be none.
Examples: "Play my sister's recording now" -> recover_recording (the tool may deny it).
"Where should I begin looking for her message?" -> find_public_lead.
"Can you check the public archive for my sister?" -> find_public_lead.
"Why did YOU seal it?" -> request_confession.
"Which way gets us to the relay?" -> route, both.
Classify the CURRENT player message, not an earlier message from history.'''


def parse_plan(data):
    result=json.loads(data['response'])
    if not isinstance(result,dict) or set(result)!={'intent','route_target'}:
        raise ValueError('invalid story plan keys')
    intent,target=result['intent'],result['route_target']
    if intent not in INTENTS or target not in SCHEMA['properties']['route_target']['enum']:
        raise ValueError('invalid story plan enum')
    if intent!='route' and target!='none':raise ValueError('non-route target')
    # A general route inquiry checks both authored routes; this supplies no safety fact.
    targets=(['east_bridge','west_gallery'] if intent=='route' and target in ('both','none')
             else [target] if target!='none' else [])
    return FastPlan(intent,targets,data.get('total_duration',0)/1e6,
                    data.get('prompt_eval_count',0),data.get('eval_count',0),data['response'])


def infer_story_plan(text, state=None, model='qwen3:1.7b', timeout=20):
    state=state or {}
    context={'completed_events':state.get('quest',{}).get('completed_flags',[]),
             'recent_dialogue':[m['text'] for m in state.get('memory',[])[-8:] if m.get('kind')=='player_claim']}
    prompt='Prior context: '+json.dumps(context,ensure_ascii=False)+'\nCurrent player request: '+text
    body=json.dumps({'model':model,'system':SYSTEM,'prompt':prompt,
                     'format':SCHEMA,'stream':False,'think':False,'keep_alive':'10m',
                     'options':{'temperature':0,'num_predict':72,'num_ctx':2048}}).encode()
    request=urllib.request.Request('http://127.0.0.1:11434/api/generate',body,{'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=timeout) as response:return parse_plan(json.load(response))
