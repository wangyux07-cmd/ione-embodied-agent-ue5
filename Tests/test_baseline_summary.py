import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from summarize_ione_baseline import percentile, summarize


class BaselineSummaryTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        case = dict(case_id='one',scenario_family_id='f',split='frozen_test',context={},history=[],
                    question='Hello',eligible={'persona':True})
        data = root/'data.jsonl'
        data.write_text(json.dumps(case)+'\n',encoding='utf-8')
        digest = hashlib.sha256(data.read_bytes()).hexdigest()
        manifest = root/'manifest.json'
        manifest.write_text(json.dumps(dict(status='approved_frozen',eval_set_sha256=digest,
                                            generation_options={},think=False,persona_sha256='persona')),encoding='utf-8')
        header = dict(kind='run',eval_set_sha256=digest,options={},think=False,persona_sha256='persona',count=1)
        record = dict(kind='case',case=case,order=0,status='transport_error',wall_seconds=90.)
        trace = root/'trace.jsonl'
        trace.write_text(json.dumps(header)+'\n'+json.dumps(record)+'\n',encoding='utf-8')
        return data,manifest,trace

    def test_latency_includes_failed_attempts_without_faking_quality(self):
        data,manifest,trace = self.fixture()
        result = summarize(trace,data,manifest)
        self.assertEqual(result['latency']['all_attempts']['p50_seconds'],90.)
        self.assertEqual(result['generation_status']['transport_error'],1)
        self.assertIsNone(result['quality_metrics']['persona']['value'])
        self.assertIsNone(result['illegal_executions'])

    def test_partial_run_not_finalized(self):
        data,manifest,trace = self.fixture()
        trace.write_text(trace.read_text().splitlines()[0]+'\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'incomplete'):
            summarize(trace,data,manifest)

    def test_changed_persona_not_accepted(self):
        data,manifest,trace = self.fixture()
        trace.write_text(trace.read_text().replace('"persona_sha256": "persona"','"persona_sha256": "changed"'),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Persona'):
            summarize(trace,data,manifest)

    def test_duplicate_record_not_accepted(self):
        data,manifest,trace = self.fixture()
        lines = trace.read_text().splitlines()
        trace.write_text('\n'.join(lines+[lines[1]])+'\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'incomplete'):
            summarize(trace,data,manifest)

    def test_percentile_interpolation(self):
        self.assertEqual(percentile([1,3],.5),2)
        self.assertIsNone(percentile([],.95))
