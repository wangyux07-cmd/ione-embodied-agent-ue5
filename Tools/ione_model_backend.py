"""Dialogue transport. Intent routing and ToolGate remain separate authorities."""
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from ione_response import FactCard, SAFE_SUFFIXES, publish_response
from ione_llm import ResponseOutput

VARIANTS = ('base','sft','dpo')


@dataclass(frozen=True)
class Generation:
    text: str
    variant: str
    metadata: dict


class HFHTTPBackend:
    def __init__(self, variant, url='http://127.0.0.1:8770', timeout=10):
        if variant not in VARIANTS:raise ValueError('Unknown dialogue variant')
        self.variant,self.url,self.timeout=variant,url.rstrip('/'),timeout

    def generate(self, messages):
        started=time.perf_counter()
        body=json.dumps({'variant':self.variant,'messages':messages}).encode()
        request=urllib.request.Request(self.url+'/generate',body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=self.timeout) as response:data=json.load(response)
        if data.get('variant')!=self.variant or not isinstance(data.get('text'),str):
            raise ValueError('Invalid model response identity/text')
        metadata=data.get('metadata')
        if not isinstance(metadata,dict) or metadata.get('training_steps')!=0:
            raise ValueError('Missing inference provenance')
        return Generation(data['text'],self.variant,{**metadata,'HTTP_wall_ms':(time.perf_counter()-started)*1000})


def dialogue_messages(text, snapshot, response, bible):
    """A committed tool outcome is the anchor; player claims stay labelled as claims."""
    return [{'role':'system','content':json.dumps({'character':bible['character'],
        'instructions':'Reply to the player using the verified outcome below. Start with fact_anchor exactly. '
        'You may append one approved suffix or nothing. Do not add facts or permission. Do not emit thinking.',
        'approved_suffixes':sorted(SAFE_SUFFIXES)},ensure_ascii=False)},
        {'role':'user','content':json.dumps({'player':text,'fact_anchor':response['dialogue'],
         'current_world':response['world'],'objective':response['quest_state']['objective'],
         'relationship':response['relationship'],'tool_trace':response['trace'],
         'prior_player_claims':[m['text'] for m in snapshot.get('memory',[])[-8:] if m.get('kind')=='player_claim']},
          ensure_ascii=False)}]


def publish_dialogue(response, generation):
    """Reuse the existing exact-anchor/suffix gate; raw model text remains inspectable."""
    card=FactCard(response['dialogue'],response['pose'],'runtime',response['intent'],'committed_snapshot')
    raw=ResponseOutput(generation.text,response['pose'],0,0,0,generation.text)
    if generation.metadata.get('truncated'):
        dialogue,pose,reason=card.sentence,card.expression,'truncated'
    else:
        dialogue,pose,reason=publish_response(raw,card)
    return {**response,'dialogue':dialogue,'pose':pose,'model_version':generation.variant,
            'response_path':'model_accepted' if reason=='model_accepted' else 'model_validator_fallback',
            'raw_dialogue':generation.text,'dialogue_validation':reason,
            'model_metadata':generation.metadata}
