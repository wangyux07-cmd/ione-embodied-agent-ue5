"""Durable per-session state. SQLite transactions own the turn commit boundary."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from contextlib import contextmanager

from ione_agent import World

ROOT = Path(__file__).resolve().parents[1]
QUEST = json.loads((ROOT / 'Narrative/quests.json').read_text(encoding='utf-8'))
STRINGS = json.loads((ROOT / 'Narrative/strings_en.json').read_text(encoding='utf-8'))


class StaleTurn(Exception):
    pass


def initial_state():
    return {'world': asdict(World()), 'quest': {'completed_flags': [], 'event_ids': []},
            'relationship': {'stage': 'stranger', 'trust_events': []}, 'memory': []}


def advance(state, event, source):
    flags = state['quest']['completed_flags']
    spec = next(x for x in QUEST['events'] if x['id'] == event)
    if event in flags or not set(spec['requires']) <= set(flags):
        return False
    flags.append(event)
    state['quest']['event_ids'].append(event)
    state['memory'].append({'id': event, 'actor': 'archive', 'kind': 'verified_event',
                            'source_event': source, 'timestamp': time.time(),
                            'confidence': 1, 'scope': 'session', 'text': event})
    trust = [x for x in flags if x in {'relay_repaired', 'privacy_respected', 'public_evidence_collected'}]
    state['relationship'] = {'stage': 'trusted' if len(trust) == 3 else
                             'familiar' if 'relay_repaired' in trust else 'stranger', 'trust_events': trust}
    return True


def quest_view(state):
    flags = set(state['quest']['completed_flags'])
    chapter = next((c for c in QUEST['chapters'] if not set(c['required_events']) <= flags), QUEST['chapters'][-1])
    return {**state['quest'], 'chapter': chapter['number'],
            'objective': STRINGS['objectives'][chapter['objective_id']],
            'events': [{'id': e['id'], 'completed': e['id'] in flags,
                        'available': set(e['requires']) <= flags,
                        'blocked_reason': e['blocked_reason'], 'hint_id': e['hint_id']}
                       for e in QUEST['events']]}


class SessionStore:
    SCHEMA_VERSION = 1

    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('unsupported database version; migrate a backup before opening')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, version INTEGER NOT NULL, state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS turns (session_id TEXT, version INTEGER, request TEXT, response TEXT, PRIMARY KEY(session_id,version))')
            db.execute('PRAGMA user_version=1')
        self.create('legacy')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, session_id=None):
        session_id = session_id or uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO sessions VALUES (?,0,?)', (session_id, json.dumps(initial_state())))
        return session_id

    def read(self, session_id):
        with self.connect() as db:
            row = db.execute('SELECT version,state FROM sessions WHERE id=?', (session_id,)).fetchone()
        if row is None:
            raise KeyError('unknown_session')
        return row[0], json.loads(row[1])

    def begin_turn(self, session_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor = db.execute('UPDATE sessions SET version=version+1 WHERE id=?', (session_id,))
            if not cursor.rowcount:
                raise KeyError('unknown_session')
            return db.execute('SELECT version FROM sessions WHERE id=?', (session_id,)).fetchone()[0]

    def commit(self, session_id, version, request, execute):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT version,state FROM sessions WHERE id=?', (session_id,)).fetchone()
            if row is None or row[0] != version:
                raise StaleTurn()
            state = json.loads(row[1])
            response = execute(state)
            db.execute('UPDATE sessions SET state=? WHERE id=?', (json.dumps(state), session_id))
            db.execute('INSERT INTO turns VALUES (?,?,?,?)',
                       (session_id, version, json.dumps(request), json.dumps(response)))
            return response
