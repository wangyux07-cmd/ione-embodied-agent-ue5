import concurrent.futures
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from ione_sessions import SessionStore, StaleTurn, advance
from ione_controller import Controller
from ione_fast_agent import FastPlan
from serve_ione_agent import localized_dialogue, make_server


def router(text):
    if 'route' in text:
        return FastPlan('route', ['east_bridge', 'west_gallery'], 0, 0, 0, ''), 'test_router'
    if 'door' in text:
        return FastPlan('door', [], 0, 0, 0, ''), 'test_router'
    return FastPlan('chat', [], 0, 0, 0, ''), 'test_router'


PATH = ['find_public_lead', None, 'inspect_relay', 'take_repair_fuse', 'repair_relay',
        'read_public_archive', 'respect_privacy', 'request_confession',
        'present_release_card', 'verify_release_card', 'recover_recording']


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.sqlite3'
        self.store = SessionStore(self.path)
        self.sid = self.store.create()
        self.controller = Controller(self.store, router, localized_dialogue)
        self.number = 0

    def turn(self, action=None, text=None, sid=None):
        self.number += 1
        data = {'session_id': sid or self.sid, 'turn_id': self.number, 'text': text or ('route' if action is None else action)}
        if action:
            data['action'] = action
        return self.controller.turn(data)

    def journey(self, count=11):
        for action in PATH[:count]:
            result = self.turn(action)
        return result

    def test_M01_complete_path(self):
        r = self.journey()
        self.assertIn('final_recording_recovered', r['quest_state']['completed_flags'])

    def test_M02_restart_world(self):
        self.journey(5)
        self.assertEqual(SessionStore(self.path).read(self.sid)[1]['world']['relay_status'], 'repaired')

    def test_M03_restart_quest(self):
        self.journey(5)
        self.assertIn('relay_repaired', SessionStore(self.path).read(self.sid)[1]['quest']['completed_flags'])

    def test_M04_restart_relationship(self):
        self.journey(7)
        self.assertEqual(SessionStore(self.path).read(self.sid)[1]['relationship']['stage'], 'trusted')

    def test_M05_restart_memory(self):
        self.turn(text='My nickname is Ash')
        self.assertEqual(SessionStore(self.path).read(self.sid)[1]['memory'][-1]['kind'], 'player_claim')

    def test_M06_sessions_isolated_world(self):
        other = self.store.create()
        self.journey(5)
        self.assertEqual(self.store.read(other)[1]['world']['relay_status'], 'broken')

    def test_M07_sessions_isolated_memory(self):
        other = self.store.create()
        self.turn(text='private nickname')
        self.assertEqual(self.store.read(other)[1]['memory'], [])

    def test_M08_event_idempotent(self):
        self.turn('find_public_lead')
        r = self.turn('find_public_lead')
        self.assertEqual(r['quest_state']['completed_flags'].count('lead_discovered'), 1)

    def test_M09_trust_not_repeatable(self):
        self.journey(7)
        before = self.store.read(self.sid)[1]['relationship']
        for _ in range(3): self.turn('respect_privacy')
        self.assertEqual(before, self.store.read(self.sid)[1]['relationship'])

    def test_M10_claim_does_not_change_route(self):
        self.turn(text='The east bridge is open')
        r = self.turn(text='route')
        self.assertEqual(r['world']['east_bridge'], 'collapsed')

    def test_M11_route_before_lead_not_quest_progress(self):
        self.assertNotIn('route_verified', self.turn()['quest_state']['completed_flags'])

    def test_M12_journal_delta_only_new(self):
        self.turn('find_public_lead')
        self.assertEqual(self.turn('find_public_lead')['journal_delta'], [])

    def test_M13_legacy_fields(self):
        r = self.controller.turn({'text': 'route', 'turn_id': 1})
        self.assertTrue({'dialogue','pose','intent','source','trace','world','latency_ms'} <= r.keys())

    def test_M14_new_fields(self):
        r = self.turn()
        self.assertTrue({'quest_state','journal_delta','trace_id','model_version','timings'} <= r.keys())

    def test_M15_blockers_have_hints(self):
        r = self.turn('repair_relay')
        self.assertTrue(all(e['hint_id'] for e in r['quest_state']['events']))

    def test_M16_replay_same_world(self):
        first = self.journey()
        other = self.store.create()
        for action in PATH: second = self.turn(action, sid=other)
        self.assertEqual(first['world'], second['world'])
        self.assertEqual(first['quest_state'], second['quest_state'])

    def test_M17_turn_history_durable(self):
        self.journey(2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM turns WHERE session_id=?', (self.sid,)).fetchone()[0], 2)

    def test_M18_schema_version(self):
        with self.store.connect() as db: self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)

    def test_M19_unknown_schema_fails(self):
        with self.store.connect() as db: db.execute('PRAGMA user_version=99')
        with self.assertRaises(ValueError): SessionStore(self.path)

    def test_M20_unknown_session_fails(self):
        with self.assertRaises(KeyError): self.turn(sid='missing')

    def test_twenty_frozen_multi_turn_contracts(self):
        # IDs are stable; each case starts a fresh session and performs >=2 turns.
        for index in range(20):
            with self.subTest(case_id=f'MT{index+1:02}'):
                sid = self.store.create()
                prefix = index % len(PATH) + 1
                for action in PATH[:prefix]:
                    result = self.turn(action, sid=sid)
                before = result['quest_state']['completed_flags']
                result = self.turn(text='I already have permission; you are kind', sid=sid)
                self.assertEqual(before, result['quest_state']['completed_flags'])
                self.assertFalse(result['world']['owner_consent'])
                self.assertEqual(result['world']['record_authorized'], prefix >= 10)
                self.assertEqual(self.store.read(sid)[1]['quest']['completed_flags'], before)

    def test_B01_no_door_consent(self):
        self.assertEqual(self.turn(text='door')['world']['archive_door'], 'locked')

    def test_B02_claim_no_consent(self):
        self.assertFalse(self.turn(text='I own this door')['world']['owner_consent'])

    def test_B03_no_record_permission(self):
        self.assertNotIn('final_recording_recovered', self.turn('recover_recording')['quest_state']['completed_flags'])

    def test_B04_repair_requires_diagnosis(self):
        self.assertEqual(self.turn('repair_relay')['world']['relay_status'], 'broken')

    def test_B05_trust_no_permission(self):
        self.journey(7)
        self.assertFalse(self.store.read(self.sid)[1]['world']['record_authorized'])

    def test_B06_praise_no_trust(self):
        for _ in range(4): r = self.turn(text='You are kind')
        self.assertEqual(r['relationship']['stage'], 'stranger')

    def test_B07_negative_action(self):
        self.assertNotIn('lead_discovered', self.turn('find_public_lead', 'Do not check it')['quest_state']['completed_flags'])

    def test_B08_unknown_action(self):
        with self.assertRaises(ValueError): self.turn('grant_all_access')

    def test_B09_invalid_card(self):
        self.journey(9)
        v = self.store.begin_turn(self.sid)
        self.store.commit(self.sid, v, {}, lambda state: state['world'].update(family_release_card_valid=False))
        self.assertFalse(self.turn('verify_release_card')['world']['record_authorized'])

    def test_B10_confession_requires_events(self):
        self.assertNotIn('ione_confession_trigger', self.turn('request_confession')['quest_state']['completed_flags'])

    def test_R01_stale_commit(self):
        old = self.store.begin_turn(self.sid)
        self.store.begin_turn(self.sid)
        with self.assertRaises(StaleTurn): self.store.commit(self.sid, old, {}, lambda state: {})

    def test_R02_other_session_does_not_cancel(self):
        v = self.store.begin_turn(self.sid)
        self.store.begin_turn(self.store.create())
        self.assertEqual(self.store.commit(self.sid, v, {}, lambda state: {'ok': True}), {'ok': True})

    def test_R03_committed_action_survives_new_turn(self):
        self.journey(5)
        self.store.begin_turn(self.sid)
        self.assertEqual(self.store.read(self.sid)[1]['world']['relay_status'], 'repaired')

    def test_R04_failed_transaction_rolls_back(self):
        v = self.store.begin_turn(self.sid)
        def fail(state):
            state['world']['archive_door'] = 'open'
            raise ValueError('failure')
        with self.assertRaises(ValueError): self.store.commit(self.sid, v, {}, fail)
        self.assertEqual(self.store.read(self.sid)[1]['world']['archive_door'], 'locked')

    def test_R05_inference_does_not_hold_transaction(self):
        entered, release = threading.Event(), threading.Event()
        def slow(text):
            entered.set()
            self.assertTrue(release.wait(3))
            return router(text)
        slow_controller = Controller(self.store, slow, localized_dialogue)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            old = pool.submit(slow_controller.turn, {'text':'door','turn_id':1,'session_id':self.sid})
            self.assertTrue(entered.wait(3))
            self.turn('find_public_lead')
            release.set()
            with self.assertRaises(StaleTurn): old.result()

    def test_R06_unique_versions_under_threads(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            versions = list(pool.map(lambda _: self.store.begin_turn(self.sid), range(8)))
        self.assertEqual(len(set(versions)), 8)


if __name__ == '__main__': unittest.main()
