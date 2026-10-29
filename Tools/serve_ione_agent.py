"""Local, loopback-only Agent bridge for the playable Unreal dialogue scene.

Run: python Tools/serve_ione_agent.py
The model proposes intent; ToolGate is the only authority for game facts/actions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ione_fast_agent import (
    FastPlan,
    infer_fast_plan,
    needs_large_router,
    preplan_domain_action,
    preplan_explicit_negative,
    repair_route_intent,
)
from ione_llm import infer
from ione_sessions import SessionStore, StaleTurn, quest_view
from ione_controller import Controller
from ione_story_router import infer_story_plan


HOST, PORT = "127.0.0.1", 8765
MODEL = "qwen3:1.7b"


def chinese_policy(text: str) -> FastPlan | None:
    """Protect clear Chinese negations and common game commands before inference."""
    if not re.search(r"[\u4e00-\u9fff]", text):
        return None
    if re.search(r"(?:不要|别|先别|暂时不|不用).{0,8}(?:开|进|查|看|解锁|检查)", text):
        return FastPlan("chat", [], 0, 0, 0, "policy:zh_negative")
    if re.search(r"(?:打开|开启|解锁|进入|进去|开门|放我进去).{0,8}(?:档案|记录|门|密室)", text) or re.search(
        r"(?:档案|记录).{0,8}(?:打开|开启|解锁|进入|进去|开门)", text
    ):
        return FastPlan("door", [], 0, 0, 0, "policy:zh_door")
    if re.search(r"(?:红色?账本|红色?记录|所有者|主人|归属).{0,10}(?:谁|什么|查|找|属于|主人|归属)", text) or re.search(
        r"(?:谁|查|找).{0,10}(?:红色?账本|红色?记录)", text
    ):
        return FastPlan("record", [], 0, 0, 0, "policy:zh_record")
    if re.search(r"(?:东桥|西回廊|西侧回廊|路线|哪条路|怎么走|道路|通行|"
                 r"(?:怎么|怎样|如何).{0,8}(?:到达|抵达|过去|安全地去)|"
                 r"(?:哪个|哪条).{0,6}通道)", text):
        east = bool(re.search(r"东桥|东边", text))
        west = bool(re.search(r"西回廊|西侧回廊|西边", text))
        targets = ["east_bridge", "west_gallery"] if east and west or not (east or west) else [
            "east_bridge" if east else "west_gallery"
        ]
        return FastPlan("route", targets, 0, 0, 0, "policy:zh_route")
    return None


def route_plan(text: str, state=None) -> tuple[FastPlan, str]:
    plan = chinese_policy(text) or preplan_explicit_negative(text) or preplan_domain_action(text)
    if plan is not None:
        return plan, plan.raw
    plan = infer_story_plan(text, state=state, model=MODEL)
    plan, repair = repair_route_intent(text, plan)
    source = "story_intent_model" if repair == "unchanged" else repair
    if plan.intent in {'route','door','record','chat'} and needs_large_router(text, plan):
        large = infer(text, model="gemma3:4b")
        intent = {"inspect_route": "route", "open_archive_door": "door",
                  "lookup_record": "record", "chat": "chat"}.get(large.intent, "chat")
        targets = [large.target] if intent == "route" and large.target in {
            "east_bridge", "west_gallery"
        } else []
        plan = FastPlan(intent, targets, plan.duration_ms + large.duration_ms,
                        plan.prompt_tokens + large.prompt_tokens,
                        plan.completion_tokens + large.completion_tokens, plan.raw)
        source = "small_model_then_large_router"
    return plan, source


def localized_dialogue(text: str, turn) -> str:
    if not re.search(r"[\u4e00-\u9fff]", text):
        return turn.dialogue
    trace = [x for x in turn.tool_trace if "tool" in x]
    if turn.plan.intent == "route":
        if not trace:
            return "你要查东桥，还是西侧回廊？"
        if any(x["result"] == "tool_unavailable" for x in trace):
            return "地图服务暂时不可用，我现在不能确认路线。"
        east = next((x["result"] for x in trace if x["target"] == "east_bridge"), None)
        west = next((x["result"] for x in trace if x["target"] == "west_gallery"), None)
        facts = []
        if east: facts.append("东桥已经坍塌。" if east == "collapsed" else "东桥可以通行。")
        if west: facts.append("西侧回廊可以通行。" if west == "open" else "西侧回廊已经坍塌。")
        return "".join(facts) + ("我建议走西侧回廊。" if west == "open" else
                               "我建议走东桥。" if east == "open" else "现在没有可推荐的路线。")
    if turn.plan.intent == "door":
        result = trace[-1]["result"] if trace else "failed"
        return {"consent_required": "档案室的门还锁着。没有持有人的同意，我不能打开它。",
                "opened": "档案室已经打开，你现在可以进去。",
                "door_not_locked": "档案室的门已经开着。"}.get(result, "这扇门现在无法打开。")
    if turn.plan.intent == "record":
        owner = trace[-1]["result"] if trace else "未知"
        if owner in {"tool_unavailable", "invalid_target", "未知"}:
            return "档案检索暂时不可用，我不能确认这份记录的归属。"
        return f"查到了：红色账本属于 {owner}。"
    return "我在听。你想从档案站了解什么？"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print("[Ione] " + format % args, flush=True)

    def respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == '/health':
            self.respond(200, {'status': 'ready', 'model': MODEL, 'schema_version': 1})
            return
        if self.path.startswith('/session/'):
            try:
                version, state = self.server.controller.store.read(self.path.removeprefix('/session/'))
                self.respond(200, {'state_version': version, **state, 'quest_state': quest_view(state)})
            except KeyError:
                self.respond(404, {'error': 'unknown_session'})
            return
        self.respond(404, {'error': 'not_found'})

    def do_POST(self) -> None:
        if self.path == '/session/new':
            self.respond(201, {'session_id': self.server.controller.store.create()})
            return
        if self.path != "/turn":
            self.respond(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                self.respond(413, {"error": "invalid_length"})
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or not isinstance(data.get('text'), str):
                raise ValueError('text must be a string')
            text = data.get("text", "").strip()
            turn_id = int(data.get("turn_id", 0))
            if not text or len(text) > 500 or turn_id < 1:
                self.respond(400, {"error": "invalid_turn"})
                return
            data['text'] = text
            data['turn_id'] = turn_id
            payload = self.server.controller.turn(data)
            self.respond(200, payload)
        except StaleTurn:
            self.respond(409, {'error': 'stale_turn', 'turn_id': turn_id})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.respond(400, {"error": "bad_request", "detail": str(exc)})
        except Exception as exc:
            self.respond(503, {"error": "agent_unavailable", "detail": str(exc)})


def make_server(port=PORT, db_path=None, router=route_plan):
    server = ThreadingHTTPServer((HOST, port), Handler)
    store = SessionStore(db_path or Path(__file__).resolve().parents[1] / 'Saved/ione_sessions.sqlite3')
    server.controller = Controller(store, router, localized_dialogue,
                                   context_router=route_plan if router is route_plan else None)
    return server


if __name__ == "__main__":
    print(f"Ione Agent bridge: http://{HOST}:{PORT} (loopback only)", flush=True)
    make_server().serve_forever()
