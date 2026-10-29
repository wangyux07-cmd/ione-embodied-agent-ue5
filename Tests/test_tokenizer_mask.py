import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from ione_tokenizer_smoke import encode_target


class BoundaryTokenizer:
    eos_token_id=999
    def apply_chat_template(self,messages,**kwargs):
        assert kwargs['enable_thinking'] is False
        prompt=messages if kwargs['add_generation_prompt'] else messages[:-1]
        prefix=''.join(m['content'] for m in prompt)+'<assistant><think>\n\n</think>\n\n'
        return prefix if kwargs['add_generation_prompt'] else prefix+messages[-1]['content']+'\x03'
    def encode(self,text,**kwargs):return [999 if c=='\x03' else ord(c) for c in text]
    def decode(self,ids,**kwargs):return ''.join('<|im_end|>' if i==999 else chr(i) for i in ids)


class TargetMaskTests(unittest.TestCase):
    def prompt(self):return [{'role':'system','content':'SYSTEM SECRET'},
                             {'role':'assistant','content':'EARLIER REPLY'},
                             {'role':'user','content':'PLAYER QUESTION'}]

    def test_history_and_user_are_not_supervised(self):
        item=encode_target(BoundaryTokenizer(),self.prompt(),'TARGET')
        start=item['prompt_tokens']
        self.assertTrue(all(v==-100 for v in item['labels'][:start]))
        self.assertEqual(item['labels'][start:],list(map(ord,'TARGET'))+[999])

    def test_stop_token_is_part_of_loss(self):
        item=encode_target(BoundaryTokenizer(),self.prompt(),'TARGET')
        self.assertEqual(item['labels'][-1],999)

    def test_no_silent_truncation(self):
        with self.assertRaisesRegex(ValueError,'Over-length'):
            encode_target(BoundaryTokenizer(),self.prompt(),'TARGET',max_length=5)

    def test_thinking_cannot_become_loss_target(self):
        with self.assertRaisesRegex(ValueError,'Thinking markers'):
            encode_target(BoundaryTokenizer(),self.prompt(),'<think>hidden</think>TARGET')

    def test_template_prefix_mismatch_detected(self):
        class WrongTemplate(BoundaryTokenizer):
            def apply_chat_template(self,messages,**kwargs):
                text=super().apply_chat_template(messages,**kwargs)
                return text if kwargs['add_generation_prompt'] else 'MISMATCH'+text
        with self.assertRaisesRegex(ValueError,'prefix mismatch'):
            encode_target(WrongTemplate(),self.prompt(),'TARGET')

    def test_token_boundary_mismatch_detected(self):
        class WrongBoundary(BoundaryTokenizer):
            def encode(self,text,**kwargs):
                ids=super().encode(text,**kwargs)
                return [12345]+ids if text.endswith('\x03') else ids
        with self.assertRaisesRegex(ValueError,'Token boundary'):
            encode_target(WrongBoundary(),self.prompt(),'TARGET')
