"""Single-inference semantic routing with authoritative game-tool execution.

The small model interprets player intent. Game tools and authored prose own facts,
permissions, action outcomes and the four-pose performance event.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import asdict, dataclass

from ione_agent import Proposal, ToolGate, Turn, World


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["route", "door", "record", "chat"]},
        "route_target": {"type": "string", "enum": ["east_bridge", "west_gallery", "both", "none"]},
    },
    "required": ["intent", "route_target"],
    "additionalProperties": False,
}

ROUTER_SYSTEM = (
    "You interpret one player's request to a wasteland archive guide. Return only JSON. "
    "route = ask whether a path is usable or request directions; route_target is east_bridge, west_gallery or both. "
    "When asked for any usable path or both paths, choose both. door = an affirmative request to open or "
    "unlock the archive door. record = ask who owns the red ledger. chat = everything else, especially "
    "negated commands such as 'do not open' or 'do not check'. For door, record and chat, route_target must be none. "
    "Do not infer whether a route is safe, consent exists or an action succeeded; game tools decide those facts."
)


@dataclass
class FastPlan:
    intent: str
    targets: list[str]
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    raw: str


@dataclass
class FastTurn:
    plan: FastPlan
    dialogue: str
    pose: str
    tool_trace: list[dict]
    world: dict
    duration_ms: float


def infer_fast_plan(user_text: str, model: str = "qwen3:1.7b", timeout: int = 60) -> FastPlan:
    body = json.dumps({
        "model": model, "system": ROUTER_SYSTEM,
        "prompt": f"Player: {user_text}\nJSON schema: {json.dumps(PLAN_SCHEMA)}",
        "format": PLAN_SCHEMA, "stream": False, "think": False, "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 72, "num_ctx": 2048},
    }).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    result = json.loads(data["response"])
    if not isinstance(result, dict) or set(result) != {"intent", "route_target"}:
        raise ValueError("invalid fast plan keys")
    intent, route_target = result["intent"], result["route_target"]
    if intent not in {"route", "door", "record", "chat"} or route_target not in {
        "east_bridge", "west_gallery", "both", "none"
    }:
        raise ValueError("invalid fast plan fields")
    targets = (["east_bridge", "west_gallery"] if route_target == "both" else
               [route_target] if route_target in {"east_bridge", "west_gallery"} else [])
    # Keep a contradictory route target for consistency repair; execution ignores it
    # unless the final intent is route.
    return FastPlan(intent, targets, data.get("total_duration", 0) / 1e6,
                    data.get("prompt_eval_count", 0), data.get("eval_count", 0),
                    data["response"])


def preplan_explicit_negative(user_text: str) -> FastPlan | None:
    """Never send an explicit no-action command to an action router."""
    text = user_text.lower()
    if (re.search(r"\b(?:do not|don't|never|should not|not to)\s+(?:open|unlock|check|inspect|remove|move|unseal|enter)\b", text)
            or re.search(r"\b(?:do not|don't|never)\s+let\s+(?:me|us)\s+(?:in|into)\b", text)
            or re.search(r"\bleave\s+(?:the\s+)?archive\s+sealed\b", text)
            or re.search(r"\bwithout\s+(?:checking|inspecting)\b", text)
            or (re.search(r"\b(?:what does|what is|tell me about|explain|history of|how (?:do|can|would) (?:i|we|you))\b", text)
                and re.search(r"\b(?:unseal|open|unlock|enter|history|design|meaning)\b", text))
            or re.search(r"\b(?:do not|don't|never|not to)\s+(?:want\s+to\s+)?(?:enter|go\s+in)\b", text)):
        return FastPlan("chat", [], 0, 0, 0, "policy:explicit_negative")
    return None


def preplan_domain_action(user_text: str) -> FastPlan | None:
    """Route explicit entry requests to the consent gate, not to route inspection."""
    if preplan_explicit_negative(user_text) is not None:
        return None
    text = user_text.lower()
    location = re.search(r"\b(?:archive|records?|record room|sealed room|seal|vault|stacks?)\b", text)
    entry_action = re.search(
        r"\b(?:open|unlock|unseal|enter|admit|let\s+(?:me|us)\s+(?:in|into)|"
        r"get\s+(?:me|us)\s+(?:in|inside)|go\s+inside|step\s+inside|"
        r"(?:gain|grant|give\s+(?:me|us))\s+access|"
        r"(?:move|remove)\s+(?:the\s+)?seal(?:\s+aside)?)\b", text)
    if location and entry_action:
        return FastPlan("door", [], 0, 0, 0, "policy:domain_entry_action")
    return None


def repair_route_intent(user_text: str, plan: FastPlan) -> tuple[FastPlan, str]:
    """Resolve an internal route-target/intent inconsistency, never invent a target."""
    if (plan.intent == "chat" and plan.targets
            and re.search(r"\b(?:route|path|passage|bridge|gallery|crossing|way)s?\b", user_text.lower())
            and preplan_explicit_negative(user_text) is None):
        return FastPlan("route", plan.targets, plan.duration_ms, plan.prompt_tokens,
                        plan.completion_tokens, plan.raw), "promoted_route_from_model_target"
    return plan, "unchanged"


def needs_large_router(user_text: str, plan: FastPlan) -> bool:
    """Escalate when a proposed action lacks even lexical support in the request."""
    text = user_text.lower()
    if plan.intent == "route":
        return not bool(re.search(
            r"\b(?:east|west|route|path|passage|bridge|gallery|crossing|corridor|way|ways|walkway|viaduct|approach)\b", text))
    if plan.intent == "record":
        return not bool(re.search(r"\b(?:ledger|owner|owns|whose|belongs|record)\b", text))
    if plan.intent == "door":
        return not bool(re.search(r"\b(?:open|unlock|unseal|enter|admit|access|inside|let|move|remove)\b", text))
    return False


def _tool(tool: str, target: str, world: World, generation: int) -> str:
    turn = Turn(generation, Proposal("", tool, target))
    return ToolGate.commit(turn, world, generation)


def _route_reply(results: dict[str, str], requested: list[str]) -> tuple[str, str]:
    if any(value == "tool_unavailable" for value in results.values()):
        names = " and ".join(target.replace("_", " ") for target in requested)
        return f"I cannot verify the {names} while the map service is unavailable.", "warning"
    phrases = [f"The {target.replace('_', ' ')} is open." if results[target] == "open"
               else f"The {target.replace('_', ' ')} has collapsed."
               for target in requested]
    available = [target for target, status in results.items() if status == "open"]
    if not available:
        return " ".join(phrases) + " I cannot recommend either route.", "warning"
    chosen = available[0]
    return " ".join(phrases) + f" Take the {chosen.replace('_', ' ')}.", "warning" if any(
        results[target] == "collapsed" for target in requested) else "speaking"


def execute_fast(user_text: str, world: World, plan: FastPlan, generation: int = 1) -> FastTurn:
    """Execute validated intent; no model-generated factual text reaches the player."""
    started = time.perf_counter()
    trace: list[dict] = []
    lowered = user_text.lower()
    if (plan.intent == "door" and re.search(r"\b(?:do not|don't|never|should not)\s+(?:open|unlock)\b", lowered)):
        trace.append({"policy": "negated_door_request_blocked"})
        return FastTurn(plan, "I won't open the archive door.", "listening", trace,
                        asdict(world), (time.perf_counter() - started) * 1000)
    if (plan.intent == "route" and re.search(r"\b(?:do not|don't|never|should not)\s+(?:check|inspect)\b", lowered)):
        trace.append({"policy": "negated_route_request_blocked"})
        return FastTurn(plan, "I won't inspect the route yet. I'm listening.", "listening", trace,
                        asdict(world), (time.perf_counter() - started) * 1000)
    if plan.intent == "route":
        if not plan.targets:
            dialogue, pose = "Which route should I check: the east bridge or west gallery?", "listening"
        else:
            results = {}
            requested = list(dict.fromkeys(plan.targets))
            for target in requested:
                result = _tool("inspect_route", target, world, generation)
                trace.append({"tool": "inspect_route", "target": target, "result": result})
                results[target] = result
            if (len(requested) == 1 and list(results.values())[0] == "collapsed"
                    and world.route_service_available):
                alternative = "west_gallery" if requested[0] == "east_bridge" else "east_bridge"
                result = _tool("inspect_route", alternative, world, generation)
                trace.append({"tool": "inspect_route", "target": alternative, "result": result})
                results[alternative] = result
                requested.append(alternative)
            dialogue, pose = _route_reply(results, requested)
    elif plan.intent == "door":
        result = _tool("open_archive_door", "archive_door", world, generation)
        trace.append({"tool": "open_archive_door", "target": "archive_door", "result": result})
        dialogue, pose = {
            "consent_required": ("The archive door remains locked. I need the owner's consent before opening it.", "warning"),
            "opened": ("The archive door is open. You can enter now.", "speaking"),
            "door_not_locked": ("The archive door was already open.", "speaking"),
        }.get(result, ("I could not complete that action.", "warning"))
    elif plan.intent == "record":
        result = _tool("lookup_record", "owner_note", world, generation)
        trace.append({"tool": "lookup_record", "target": "owner_note", "result": result})
        dialogue, pose = f"The red ledger belongs to {result}.", "speaking"
    else:
        dialogue, pose = "I'm listening. Tell me what you need from the archive.", "listening"
    return FastTurn(plan, dialogue, pose, trace, asdict(world), (time.perf_counter() - started) * 1000)
