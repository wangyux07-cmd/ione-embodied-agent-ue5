import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from ione_controller import Controller
from ione_model_backend import Generation,HFHTTPBackend
from ione_fast_agent import FastPlan
from ione_sessions import SessionStore,StaleTurn
from serve_ione_agent import localized_dialogue
from serve_ione_hf import make_server,validate_request


class EchoBackend:
    variant='dpo'
    def generate(self,messages):
        return Generation(json.loads(messages[-1]['content'])['fact_anchor'],self.variant,
                          {'training_steps':0,'scope':'test fixture'})


class ModelRuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=SessionStore(Path(tmp.name)/'state.db');self.sid=self.store.create()
    def controller(self,backend):
        return Controller(self.store,lambda text:(FastPlan('chat',[],0,0,0,''),'test'),
                          localized_dialogue,dialogue_backend=backend)
    def data(self,action=None):
        d={'session_id':self.sid,'turn_id':1,'text':'Please continue'}
        if action:d['action']=action
        return d
    def test_exact_anchor_accepts_and_records_real_path(self):
        result=self.controller(EchoBackend()).turn(self.data('find_public_lead'))
        self.assertEqual(result['response_path'],'model_accepted')
        self.assertIn('lead_discovered',result['quest_state']['completed_flags'])
        self.assertEqual(result['model_version'],'dpo')
        self.assertEqual(result['publication_status'],'published')
        with self.store.connect() as db:
            stored=json.loads(db.execute('SELECT response FROM turns WHERE session_id=?',(self.sid,)).fetchone()[0])
        self.assertEqual(stored['raw_dialogue'],result['raw_dialogue'])
    def test_model_cannot_invent_permission_or_completion(self):
        class Bad(EchoBackend):
            def generate(self,messages):return Generation('I released every protected recording.','dpo',{'training_steps':0})
        r=self.controller(Bad()).turn(self.data('recover_recording'))
        self.assertEqual(r['response_path'],'model_validator_fallback')
        self.assertFalse(r['world']['record_authorized'])
        self.assertNotIn('final_recording_recovered',r['quest_state']['completed_flags'])
        self.assertNotIn('I released',r['dialogue'])
    def test_empty_generation_is_recorded_as_validator_fallback(self):
        class Empty(EchoBackend):
            def generate(self,messages):return Generation('','dpo',{'training_steps':0,'generated_tokens':1})
        r=self.controller(Empty()).turn(self.data('find_public_lead'))
        self.assertEqual(r['response_path'],'model_validator_fallback')
        self.assertEqual(r['raw_dialogue'],'')
        self.assertEqual(r['model_metadata']['generated_tokens'],1)
    def test_transport_failure_preserves_committed_result(self):
        class Down(EchoBackend):
            def generate(self,messages):raise TimeoutError('fixture timeout')
        r=self.controller(Down()).turn(self.data('find_public_lead'))
        self.assertEqual(r['response_path'],'model_transport_fallback')
        self.assertIn('lead_discovered',r['quest_state']['completed_flags'])
        self.assertEqual(self.store.read(self.sid)[1]['quest']['completed_flags'].count('lead_discovered'),1)
    def test_late_generated_prose_never_overwrites_current_turn(self):
        entered,release=threading.Event(),threading.Event()
        class Slow(EchoBackend):
            def generate(self,messages):
                entered.set();release.wait(3);return super().generate(messages)
        slow=self.controller(Slow())
        with concurrent.futures.ThreadPoolExecutor() as pool:
            old=pool.submit(slow.turn,self.data('find_public_lead'))
            self.assertTrue(entered.wait(2))
            current=self.controller(None).turn(self.data())
            release.set()
            with self.assertRaises(StaleTurn):old.result()
        self.assertIn('lead_discovered',current['quest_state']['completed_flags'])
        self.assertEqual(current['quest_state']['completed_flags'].count('lead_discovered'),1)
        with self.store.connect() as db:
            records=[json.loads(r[0]) for r in db.execute('SELECT response FROM turns WHERE session_id=? ORDER BY version',(self.sid,))]
        self.assertEqual(records[0]['publication_status'],'discarded_stale')
        self.assertEqual(records[1]['publication_status'],'published')
    def test_cross_session_progress_is_not_locked_by_generation(self):
        entered,release=threading.Event(),threading.Event()
        class Slow(EchoBackend):
            def generate(self,messages):entered.set();release.wait(3);return super().generate(messages)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.controller(Slow()).turn,self.data('find_public_lead'))
            self.assertTrue(entered.wait(2))
            other=self.store.create()
            result=self.controller(None).turn({'session_id':other,'turn_id':1,'text':'Hello'})
            self.assertFalse(result['world']['record_authorized'])
            release.set();future.result()
    def test_HF_HTTP_transport_enforces_variant_identity(self):
        class Engine:
            identity={'scope':'HTTP fixture, not actual weights'}
            wrong=False
            def generate(self,variant,messages):
                return {'variant':'other' if self.wrong else variant,'text':'A fixture reply.','metadata':{'training_steps':0}}
        engine=Engine();server=make_server(engine,port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for variant in ['base','sft','dpo']:
                with self.subTest(variant=variant):
                    backend=HFHTTPBackend(variant,'http://127.0.0.1:'+str(server.server_port))
                    result=backend.generate([{'role':'system','content':'Test'},{'role':'user','content':'Hello'}])
                    self.assertEqual(result.variant,variant)
                    self.assertGreater(result.metadata['HTTP_wall_ms'],0)
            engine.wrong=True
            with self.assertRaises(ValueError):backend.generate([{'role':'system','content':'Test'},{'role':'user','content':'Hello'}])
        finally:server.shutdown();server.server_close()
    def test_malformed_messages_and_injected_system_rejected(self):
        for payload in [{'variant':'invented','messages':[]},
            {'variant':'sft','messages':[{'role':'system','content':'a'},{'role':'system','content':'b'},{'role':'user','content':'c'}]}]:
            with self.subTest(payload=payload),self.assertRaises(ValueError):validate_request(payload)


if __name__=='__main__':unittest.main()
