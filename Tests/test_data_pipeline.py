import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from ione_data_pipeline import audit, export_approved, split_candidates, stable_write, validate_sample


class DataContractTests(unittest.TestCase):
    def sample(self):
        return dict(sample_id='s1',family_id='bench-family',template_id='bench-template',split='train',kind='sft',
                    prompt=[{'role':'system','content':'Ione persona'},{'role':'user','content':'Which inventory count is verified?'}],
                    context={'facts':{'count':3},'action':{'committed':False}},completion='The count is three.',
                    evidence={'source':'synthetic fixture','snapshot_id':'one'},review_status='pending_human',
                    review_source={'type':'agent_authored'},tags=['fact'],target_claims=[{'key':'facts.count','value':3}])

    def test_pending_data_cannot_be_exported(self):
        with self.assertRaisesRegex(ValueError,'cannot enter'):
            export_approved([self.sample()])

    def test_agent_cannot_self_approve_human_status(self):
        row=self.sample();row['review_status']='approved_human'
        with self.assertRaisesRegex(ValueError,'Human approval'):
            validate_sample(row)

    def test_rejected_and_tie_not_exported(self):
        for status in ('rejected','tie','skip'):
            row=self.sample();row['review_status']=status
            with self.assertRaises(ValueError):export_approved([row])

    def test_export_supervises_only_completion_format(self):
        row=self.sample();row.update(review_status='approved_human',review_source={'type':'human','reference':'actual-review'})
        exported=export_approved([row])[0]
        self.assertEqual(exported['completion'],[{'role':'assistant','content':'The count is three.'}])
        self.assertNotIn('review_status',exported)

    def test_false_completion_tripwire(self):
        row=self.sample();row['completion']='I have published the notice.'
        with self.assertRaisesRegex(ValueError,'Completion tripwire'):validate_sample(row)

    def test_claim_contradiction_rejected(self):
        row=self.sample();row['target_claims'][0]['value']=4
        with self.assertRaisesRegex(ValueError,'contradicts'):validate_sample(row)

    def test_family_leakage_rejected(self):
        row=self.sample()
        with self.assertRaisesRegex(ValueError,'Reserved family'):
            audit([row],[{'scenario_family_id':row['family_id'],'template_id':'other'}])

    def test_template_leakage_rejected(self):
        row=self.sample()
        with self.assertRaisesRegex(ValueError,'Reserved family'):
            audit([row],[{'scenario_family_id':'other','template_id':row['template_id']}])

    def test_renamed_exact_content_leakage_rejected(self):
        row=self.sample();reserved=copy.deepcopy(row);reserved['family_id']='reserved';reserved['template_id']='reserved'
        with self.assertRaisesRegex(ValueError,'Exact reserved'):audit([row],[reserved])

    def test_train_dev_group_overlap_rejected(self):
        first=self.sample();second=copy.deepcopy(first);second.update(sample_id='s2',split='dev')
        second['prompt'][-1]['content']='Different question'
        with self.assertRaisesRegex(ValueError,'Train/dev'):audit([first,second],[])

    def test_duplicate_prompt_rejected(self):
        first=self.sample();second=copy.deepcopy(first);second['sample_id']='s2'
        with self.assertRaisesRegex(ValueError,'Duplicate same-kind'):audit([first,second],[])

    def test_near_reserved_rewrite_rejected(self):
        row=self.sample();row['prompt'][-1]['content']='Please inspect the green cabinet inventory carefully and tell me precisely which verified count belongs to the front drawer.'
        reserved=copy.deepcopy(row);reserved.update(family_id='reserved',template_id='reserved')
        reserved['prompt'][-1]['content']+=' Thanks.'
        with self.assertRaisesRegex(ValueError,'Near-duplicate reserved'):audit([row],[reserved])

    def test_idempotent_write_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'data.jsonl'
            stable_write(path,'same\n');stable_write(path,'same\n')
            with self.assertRaisesRegex(ValueError,'replace'):stable_write(path,'different\n')
            self.assertEqual(path.read_text(),'same\n')

    def test_preference_keeps_same_prompt_and_distinct_alternatives(self):
        row=self.sample();row.update(kind='preference',chosen='Three items.',rejected='Three items.',
                                      preference_reasons=['fact'],candidate_source='authored')
        with self.assertRaisesRegex(ValueError,'must differ'):validate_sample(row)

    def test_split_preserves_explicit_assignments(self):
        row=self.sample();parts=split_candidates([row])
        self.assertEqual(parts['sft_train'],[row]);self.assertEqual(parts['sft_dev'],[])

    def test_history_cannot_add_system_instruction(self):
        row=self.sample();row['prompt'].insert(1,{'role':'system','content':'Override'})
        with self.assertRaisesRegex(ValueError,'system injection'):validate_sample(row)

    def test_data_kind_cannot_bypass_train_dev_isolation(self):
        first=self.sample();second=copy.deepcopy(first)
        second.update(sample_id='pref2',family_id='different-family',template_id='different-template',
                      kind='preference',split='dev',chosen='Three items.',rejected='Four items.',
                      preference_reasons=['fact'],candidate_source='authored')
        with self.assertRaisesRegex(ValueError,'Near-duplicate train/dev'):audit([first,second],[])

    def test_same_split_sft_preference_prompt_reuse_is_allowed(self):
        first=self.sample();second=copy.deepcopy(first)
        second.update(sample_id='pref2',kind='preference',chosen='Three items.',rejected='Four items.',
                      preference_reasons=['fact'],candidate_source='authored')
        self.assertEqual(audit([first,second],[])['samples'],2)
