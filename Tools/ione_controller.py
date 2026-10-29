"""Session orchestration; model routing runs outside the SQLite transaction."""
import re
import time
import uuid
import json
from pathlib import Path
from dataclasses import asdict

from ione_agent import World, Turn, Proposal, ToolGate
from ione_fast_agent import execute_fast
from ione_sessions import QUEST, STRINGS, advance, quest_view

ACTION = {
    'find_public_lead': ('inspect_public_lead', 'sister_final', 'lead_found', 'lead_discovered'),
    'inspect_relay': ('inspect_relay', 'archive_relay', 'fuse_fault', 'relay_diagnosed'),
    'take_repair_fuse': ('take_repair_fuse', 'archive_relay', 'fuse_taken', 'repair_part_found'),
    'repair_relay': ('repair_relay', 'archive_relay', 'repaired', 'relay_repaired'),
    'read_public_archive': ('read_public_archive', 'public_dispatch', 'public_entry', 'public_evidence_collected'),
    'verify_release_card': ('verify_release_card', 'sister_final', 'authorized', 'access_authorized'),
    'recover_recording': ('recover_final_recording', 'sister_final', 'recovered', 'final_recording_recovered'),
}
CHOICES = {'respect_privacy': 'privacy_respected', 'request_confession': 'ione_confession_trigger',
           'present_release_card': 'release_card_presented'}
REPLIES = {
    'lead_discovered': 'The public index links her recording to the archive relay. We should check the route there.',
    'relay_diagnosed': 'The relay diagnostic reports a failed fuse. Check the public maintenance locker.',
    'repair_part_found': 'The replacement fuse is in your inventory. We can repair the relay now.',
    'relay_repaired': 'The relay reports a stable signal. The public index is readable again.',
    'public_evidence_collected': STRINGS['clues']['public_seal'],
    'privacy_respected': 'Thank you. We can follow the public lead while keeping those voices protected.',
    'ione_confession_trigger': STRINGS['ending']['trusted_admission'],
    'release_card_presented': 'The family-release card is ready for the archive to check against this recording.',
    'access_authorized': 'The archive verified this card for your sister’s recording.',
    'final_recording_recovered': STRINGS['ending']['authorized_playback'],
}


class Controller:
    def __init__(self, store, router, localize, context_router=None, dialogue_backend=None):
        self.store, self.router, self.localize = store, router, localize
        self.context_router = context_router
        self.dialogue_backend = dialogue_backend
        self.bible = (json.loads((Path(__file__).resolve().parents[1]/'Narrative/character_bible.json').read_text(encoding='utf-8'))
                      if dialogue_backend else None)

    def turn(self, data):
        text, turn_id = data['text'], data['turn_id']
        sid = data.get('session_id', 'legacy')
        action = data.get('action')
        if action is not None and action not in ACTION and action not in CHOICES:
            raise ValueError('invalid_action')
        started = time.perf_counter()
        version = self.store.begin_turn(sid)
        if action is None:
            plan, source = (self.context_router(text, self.store.read(sid)[1])
                            if self.context_router else self.router(text))
            if plan.intent in ACTION or plan.intent in CHOICES:
                action = plan.intent
        else:
            plan, source = None, 'structured_game_action'
        routed = time.perf_counter()

        def execute(state):
            before = set(state['quest']['completed_flags'])
            advance(state, 'met_ione', 'dialogue_started')
            world = World(**state['world'])
            if action is None:
                turn = execute_fast(text, world, plan, generation=version)
                dialogue, pose, trace, intent = self.localize(text, turn), turn.pose, turn.tool_trace, plan.intent
                if any(t.get('tool') == 'inspect_route' and t.get('result') == 'open' for t in trace):
                    advance(state, 'route_verified', 'inspect_route')
            else:
                event = ACTION[action][3] if action in ACTION else CHOICES[action]
                spec = next(e for e in QUEST['events'] if e['id'] == event)
                flags = set(state['quest']['completed_flags'])
                denied = bool(re.search(r"\b(?:do not|don't|never)\b|不要|别", text.lower()))
                allowed = set(spec['requires']) <= flags and not denied
                result = 'negated_action' if denied else 'prerequisites_required'
                if event in flags and not denied:
                    result = 'already_completed'
                    trace = [{'event': event, 'result': result}]
                elif allowed and action in ACTION:
                    tool, target, success, _ = ACTION[action]
                    result = ToolGate.commit(Turn(version, Proposal('', tool, target)), world, version, flags)
                    if result == success:
                        advance(state, event, tool)
                    trace = [{'tool': tool, 'target': target, 'result': result}]
                elif allowed:
                    advance(state, event, 'explicit_player_choice' if action == 'respect_privacy' else 'authored_story_event')
                    result = 'accepted'
                    trace = [{'event': event, 'result': result}]
                else:
                    trace = [{'event': event, 'result': result}]
                completed = event in state['quest']['completed_flags']
                dialogue = REPLIES[event] if completed else (spec['blocked_reason'] or 'Please check the required step.')
                if result == 'negated_action':
                    dialogue = "I stopped that action. I'm listening."
                pose, intent = ('speaking' if completed else 'warning'), action
            advance(state, 'evidence_complete', 'quest_event_join')
            state['world'] = asdict(world)
            # Claims are labelled and never copied into authoritative world fields.
            state['memory'].append({'id': uuid.uuid4().hex, 'actor': 'player', 'kind': 'player_claim',
                                    'source_event': f'turn:{version}', 'timestamp': time.time(),
                                    'confidence': None, 'scope': 'session', 'text': text})
            delta = [x for x in state['quest']['completed_flags'] if x not in before]
            return {'turn_id': turn_id, 'session_id': sid, 'dialogue': dialogue, 'pose': pose,
                    'intent': intent, 'source': source, 'trace': trace, 'world': state['world'],
                    'quest_state': quest_view(state), 'journal_delta': delta,
                    'relationship': state['relationship'], 'trace_id': uuid.uuid4().hex,
                    'model_version': 'authored' if action else source, 'state_version': version,
                    'response_path': 'authored_tool_result',
                    'publication_status': 'pending_model' if self.dialogue_backend else 'published',
                    'timings': {'routing_ms': round((routed-started)*1000, 2)},
                    'latency_ms': round((time.perf_counter()-started)*1000, 2)}

        response=self.store.commit(sid, version, data, execute)
        committed=time.perf_counter()
        if self.dialogue_backend is None:return response
        # ToolGate has already committed a real outcome. Interruption may cancel its
        # later prose, never roll back the recorded action or repeat its side effect.
        from ione_model_backend import dialogue_messages, publish_dialogue
        current_version,snapshot=self.store.read(sid)
        if current_version!=version:
            return self.store.finalize_response(sid,version,response)
        messages=dialogue_messages(text,snapshot,response,self.bible)
        context_ready=time.perf_counter()
        try:
            generated=self.dialogue_backend.generate(messages)
        except (OSError,ValueError,TimeoutError) as exc:
            response={**response,'response_path':'model_transport_fallback',
                      'model_version':self.dialogue_backend.variant,
                      'dialogue_validation':type(exc).__name__,
                      'model_metadata':{'training_steps':0,'generation_succeeded':False}}
        else:
            response=publish_dialogue(response,generated)
        finished=time.perf_counter()
        response['timings'].update(commit_ms=round((committed-routed)*1000,2),
            context_ms=round((context_ready-committed)*1000,2),
            dialogue_and_validator_ms=round((finished-context_ready)*1000,2))
        response['latency_ms']=round((finished-started)*1000,2)
        return self.store.finalize_response(sid,version,response)
