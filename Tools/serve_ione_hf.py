"""Loopback-only FP32 Base/SFT/DPO inference worker, isolated from the game service."""
import argparse
from contextlib import nullcontext,contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

VARIANTS=('base','sft','dpo')


@contextmanager
def inference_slot(lock):
    if not lock.acquire(timeout=1):raise TimeoutError('Inference worker busy')
    try:yield
    finally:lock.release()


def validate_request(data):
    if not isinstance(data,dict) or set(data)!={'variant','messages'} or data['variant'] not in VARIANTS:
        raise ValueError('Invalid variant/request fields')
    messages=data['messages']
    if not isinstance(messages,list) or not 2<=len(messages)<=16:
        raise ValueError('Invalid messages')
    for message in messages:
        if (not isinstance(message,dict) or set(message)!={'role','content'}
            or message['role'] not in ['system','user','assistant']
            or not isinstance(message['content'],str) or not message['content']):
            raise ValueError('Invalid message')
    if messages[0]['role']!='system' or messages[-1]['role']!='user' or any(m['role']=='system' for m in messages[1:]):
        raise ValueError('Invalid system/user boundary')
    if sum(len(m['content']) for m in messages)>16000:raise ValueError('Context text too long')
    return data['variant'],messages


class RuntimeEngine:
    def __init__(self,model,tokenizer,identity,max_new_tokens=128):
        self.model,self.tokenizer,self.identity=model,tokenizer,identity
        self.max_new_tokens=max_new_tokens
        self.lock=threading.Lock()

    def generate(self,variant,messages):
        import torch
        from transformers import GenerationConfig,StoppingCriteria
        if variant not in VARIANTS:raise ValueError('Unknown model variant')
        queued=time.perf_counter()
        with inference_slot(self.lock):
            entered=time.perf_counter();model=self.model;tokenizer=self.tokenizer
            prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            inputs=tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to(model.device)
            prompt_tokens=inputs['input_ids'].shape[1]
            if prompt_tokens+self.max_new_tokens>4096:raise ValueError('Context limit; no silent truncation')
            if variant!='base':model.set_adapter(variant)
            model.eval();device=model.device.type
            def sync():
                if device=='cuda':torch.cuda.synchronize()
            options=GenerationConfig(max_new_tokens=self.max_new_tokens,do_sample=False,
                eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id)
            first=[]
            deadline=[]
            class FirstToken(StoppingCriteria):
                def __call__(self,input_ids,scores,**kwargs):
                    if not first:
                        sync();first.append(time.perf_counter())
                    if time.perf_counter()-started>6:
                        deadline.append(True);return True
                    return False
            sync();started=time.perf_counter()
            # Same greedy override as the frozen evaluations; no sampling defaults leak through.
            with model.disable_adapter() if variant=='base' else nullcontext(),torch.inference_mode():
                generated=model.generate(**inputs,generation_config=options,do_sample=False,
                    use_model_defaults=False,use_cache=True,stopping_criteria=[FirstToken()])
            sync();finished=time.perf_counter()
            tokens=generated[0,prompt_tokens:].cpu().tolist()
            text=tokenizer.decode(tokens,skip_special_tokens=True)
            return {'variant':variant,'text':text,'metadata':{**self.identity,'training_steps':0,
                    'queue_ms':(entered-queued)*1000,'context_ms':(started-entered)*1000,
                    'generation_ms':(finished-started)*1000,
                    'first_token_generation_ms':(first[0]-started)*1000 if first else None,
                    'prompt_tokens':prompt_tokens,'generated_tokens':len(tokens),
                    'generation_deadline_reached':bool(deadline),
                    'truncated':bool(deadline) or (len(tokens)==self.max_new_tokens and tokens[-1]!=tokenizer.eos_token_id),
                    'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                    'do_sample':False,'enable_thinking':False,'use_model_defaults':False}}


def load_engine(sft_result,dpo_result,sft_adapter,dpo_adapter,device='cuda',allow_download=False):
    import torch
    import transformers,peft
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel
    from eval_ione_dpo import validate_training_identity
    from train_ione_sft import MODELS
    sft=json.loads(Path(sft_result).read_text(encoding='utf-8'))
    dpo=json.loads(Path(dpo_result).read_text(encoding='utf-8'))
    model_id,revision=MODELS['pilot']
    if (sft['model'],sft['revision'])!=(model_id,revision) or not sft['checkpoint_reload_passed']:
        raise ValueError('Expected verified pinned SFT checkpoint')
    if sft['dtype']!='torch.float32' or dpo['precision']!='fp32':raise ValueError('Expected verified FP32 checkpoints')
    validate_training_identity(dpo,sft,Path(sft_adapter)/'adapter_model.safetensors',
                                Path(dpo_adapter)/'adapter_model.safetensors')
    if device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no paid or CPU fallback')
    kwargs={'revision':revision,'local_files_only':not allow_download,'trust_remote_code':False}
    tokenizer=AutoTokenizer.from_pretrained(model_id,**kwargs)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()!=sft['chat_template_sha256']:
        raise ValueError('Tokenizer template changed')
    base=AutoModelForCausalLM.from_pretrained(model_id,dtype=torch.float32,device_map={'':device},
               low_cpu_mem_usage=True,attn_implementation='sdpa',**kwargs)
    model=PeftModel.from_pretrained(base,sft_adapter,adapter_name='sft',is_trainable=False)
    model.load_adapter(dpo_adapter,adapter_name='dpo',is_trainable=False)
    identity={'model':model_id,'revision':revision,'precision':'fp32','device':device,
              'SFT_sha256':dpo['source_SFT_adapter_sha256'],'DPO_sha256':dpo['policy_adapter_sha256'],
              'torch':torch.__version__,'transformers':transformers.__version__,'peft':peft.__version__,
              'hardware':torch.cuda.get_device_name() if device=='cuda' else 'CPU',
              'scope':'real pretrained runtime inference; not frozen evaluation scores'}
    return RuntimeEngine(model,tokenizer,identity)


def make_server(engine,port=8770):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,payload):
            blob=json.dumps(payload).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(blob)));self.end_headers();self.wfile.write(blob)
        def do_GET(self):
            self.respond(200,{'status':'ready','variants':VARIANTS,'identity':engine.identity}) if self.path=='/health' else self.respond(404,{'error':'not_found'})
        def do_POST(self):
            if self.path!='/generate':self.respond(404,{'error':'not_found'});return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536:raise ValueError('Invalid length')
                variant,messages=validate_request(json.loads(self.rfile.read(length)))
            except (ValueError,TypeError,KeyError):self.respond(400,{'error':'invalid_request'});return
            try:result=engine.generate(variant,messages)
            except ValueError:self.respond(422,{'error':'context_or_generation_invalid'});return
            except (RuntimeError,OSError) as exc:
                self.respond(503,{'error':'inference_unavailable','type':type(exc).__name__});return
            self.respond(200,result)
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['sft-result','dpo-result','sft-adapter','dpo-adapter']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    parser.add_argument('--allow-download',action='store_true',help='Explicitly allow downloading the pinned public base weights')
    args=parser.parse_args()
    engine=load_engine(args.sft_result,args.dpo_result,args.sft_adapter,args.dpo_adapter,args.device,args.allow_download)
    print('Ione HF runtime: http://127.0.0.1:8770; Base/SFT/DPO; FP32; no training',flush=True)
    make_server(engine).serve_forever()
