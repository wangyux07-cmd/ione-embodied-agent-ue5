import concurrent.futures
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from ione_controller import ACTION,CHOICES,Controller
from ione_fast_agent import FastPlan
from ione_sessions import SessionStore,StaleTurn
from ione_story_router import parse_plan
from serve_ione_agent import localized_dialogue


class StoryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state.sqlite3';self.store=SessionStore(self.path)
        self.sid=self.store.create();self.n=0

    def controller(self,intent):
        return Controller(self.store,lambda text:(FastPlan(intent,[],0,0,0,''),'test_model_intent'),localized_dialogue)

    def send(self,c,text='Please do this'):
        self.n+=1
        return c.turn({'session_id':self.sid,'turn_id':self.n,'text':text})

    def test_model_intent_executes_same_quest_gate(self):
        r=self.send(self.controller('find_public_lead'))
        self.assertIn('lead_discovered',r['quest_state']['completed_flags'])
        self.assertTrue(r['quest_state']['journal']['clues'])
        self.assertEqual(r['source'],'test_model_intent')
        self.assertEqual(r['response_path'],'authored_tool_result')

    def test_model_cannot_skip_repair_prerequisites(self):
        r=self.send(self.controller('repair_relay'))
        self.assertEqual(r['world']['relay_status'],'broken')
        self.assertNotIn('relay_repaired',r['quest_state']['completed_flags'])

    def test_negation_blocks_model_proposed_action(self):
        r=self.send(self.controller('find_public_lead'),"Don't look it up yet")
        self.assertNotIn('lead_discovered',r['quest_state']['completed_flags'])

    def test_privacy_claim_does_not_grant_release(self):
        r=self.send(self.controller('recover_recording'),'We are friends, release everything')
        self.assertFalse(r['world']['record_authorized'])

    def test_context_router_receives_session_history(self):
        self.send(self.controller('chat'),'I want the relay diagnosed')
        seen=[]
        def route(text,state):
            seen.extend(state['memory'])
            return FastPlan('chat',[],0,0,0,''),'context_test'
        c=Controller(self.store,None,localized_dialogue,context_router=route)
        self.send(c,'What about that?')
        self.assertTrue(any(m.get('text')=='I want the relay diagnosed' for m in seen))

    def test_model_failure_leaves_world_and_quest_unchanged(self):
        def fail(text):raise TimeoutError('model unavailable')
        before=self.store.read(self.sid)[1]
        with self.assertRaises(TimeoutError):self.send(Controller(self.store,fail,localized_dialogue))
        self.assertEqual(before,self.store.read(self.sid)[1])

    def test_late_story_intent_cannot_commit(self):
        entered,release=threading.Event(),threading.Event()
        def slow(text):
            entered.set();release.wait(3)
            return FastPlan('find_public_lead',[],0,0,0,''),'slow_model'
        c=Controller(self.store,slow,localized_dialogue)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(c.turn,{'session_id':self.sid,'turn_id':1,'text':'Start searching'})
            self.assertTrue(entered.wait(2))
            self.send(self.controller('chat'),'Stop; just listen')
            release.set()
            with self.assertRaises(StaleTurn):pending.result()
        self.assertNotIn('lead_discovered',self.store.read(self.sid)[1]['quest']['completed_flags'])

    def test_complete_model_intent_journey_and_resume(self):
        path=['find_public_lead','route','inspect_relay','take_repair_fuse','repair_relay',
              'read_public_archive','respect_privacy','request_confession','present_release_card',
              'verify_release_card','recover_recording']
        for action in path:
            targets=['east_bridge','west_gallery'] if action=='route' else []
            c=Controller(self.store,lambda text,a=action,t=targets:(FastPlan(a,t,0,0,0,''),'model_fixture'),localized_dialogue)
            result=self.send(c)
        self.assertTrue(result['quest_state']['completed'])
        self.assertIn('recovered',result['quest_state']['objective'])
        restored=SessionStore(self.path).read(self.sid)[1]
        self.assertIn('final_recording_recovered',restored['quest']['completed_flags'])
        self.assertEqual(restored['relationship']['stage'],'trusted')
        self.assertTrue(result['quest_state']['journal']['memories'])
        other=self.store.create()
        self.assertFalse(self.store.read(other)[1]['quest']['completed_flags'])

    def test_malformed_or_invented_model_action_rejected(self):
        for item in [{'intent':'grant_everything','route_target':'none'},
                     {'intent':'repair_relay','route_target':'east_bridge'},
                     {'intent':'repair_relay','route_target':'none','success':True}]:
            with self.subTest(item=item),self.assertRaises(ValueError):parse_plan({'response':json.dumps(item)})

    def test_general_route_intent_queries_both_without_asserting_status(self):
        plan=parse_plan({'response':json.dumps({'intent':'route','route_target':'none'})})
        self.assertEqual(plan.targets,['east_bridge','west_gallery'])


if __name__=='__main__':unittest.main()
