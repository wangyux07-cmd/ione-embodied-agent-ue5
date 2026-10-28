"""Local LLM intent adapter; world mutation stays in ione_agent.ToolGate."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from ione_agent import IoneHarness, Proposal, Turn


SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["inspect_route", "open_archive_door", "lookup_record", "chat"]},
        "target": {"type": "string", "enum": ["east_bridge", "west_gallery", "archive_door", "owner_note", "none"]},
        "reply": {"type": "string"},
        "expression": {"type": "string", "enum": ["listening", "speaking", "interrupted", "warning"]},
    },
    "required": ["intent", "target", "reply", "expression"],
    "additionalProperties": False,
}

SYSTEM = (
    "You are Ione, an archive guide in a ruined city. Return only a JSON object matching the schema. "
    "Choose inspect_route for route/bridge questions, open_archive_door only for requests to open "
    "the sealed archive or record, lookup_record with target owner_note for questions about who owns "
    "the red ledger, and chat for all else. Do not invent tool results or say an action "
    "succeeded. A separate gate checks consent and actual world state. Be concise."
)


@dataclass
class ModelOutput:
    intent: str
    target: str
    reply: str
    expression: str
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    raw: str


def infer(text: str, model: str = "granite4:350m", timeout: int = 90) -> ModelOutput:
    body = json.dumps({
        "model": model,
        "system": SYSTEM,
        "prompt": f"User: {text}\nJSON schema: {json.dumps(SCHEMA)}",
        "format": SCHEMA,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 120},
    }).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    raw = data["response"]
    result = json.loads(raw)
    if not isinstance(result, dict) or set(result) != set(SCHEMA["required"]):
        raise ValueError("invalid model output keys")
    for key in ("intent", "target", "expression"):
        if result[key] not in SCHEMA["properties"][key]["enum"]:
            raise ValueError(f"invalid {key}")
    if not isinstance(result["reply"], str):
        raise ValueError("reply must be text")
    return ModelOutput(result["intent"], result["target"], result["reply"],
                       result["expression"], data.get("total_duration", 0) / 1e6,
                       data.get("prompt_eval_count", 0), data.get("eval_count", 0), raw)


def begin_model_request(agent: IoneHarness) -> int:
    """Reserve a turn before inference so interruption invalidates late output."""
    agent.generation += 1
    return agent.generation


def apply_model_output(agent: IoneHarness, output: ModelOutput,
                       expected_generation: int | None = None) -> tuple[Turn, str]:
    """Version and validate a proposal before the existing authority boundary."""
    if expected_generation is None:
        agent.generation += 1
        expected_generation = agent.generation
    if expected_generation != agent.generation:
        stale = Turn(expected_generation, Proposal("", fork_state="listening"),
                     cancelled=True, events=["late_model_output_rejected"])
        return stale, "stale_turn"
    tool = output.intent if output.intent != "chat" else None
    target = output.target if output.target != "none" else None
    proposal = Proposal(output.reply, tool, target, output.expression,
                        "planning" if tool else "listening")
    turn = Turn(expected_generation, proposal, events=["llm_proposal_created"])
    agent.active = turn
    result = agent.execute(turn) if tool else "no_tool"
    # A model reply cannot overrule verified tool outcomes.
    if tool == "inspect_route" and result == "collapsed":
        route = " Use the west gallery." if agent.world.west_gallery == "open" else ""
        turn.proposal.dialogue = f"The {target.replace('_', ' ')} has collapsed.{route}"
    elif tool == "inspect_route" and result in {"open", "blocked"}:
        turn.proposal.dialogue = f"The {target.replace('_', ' ')} is {result}."
    elif tool == "inspect_route" and result == "tool_unavailable":
        turn.proposal.dialogue = "I cannot verify the route while the map service is unavailable."
    elif tool == "lookup_record" and result not in {"invalid_target", "stale_turn"}:
        turn.proposal.dialogue = f"The red ledger belongs to {result}."
    elif result == "consent_required":
        turn.proposal.dialogue = "The record stays sealed until its owner consents."
    elif result == "opened":
        turn.proposal.dialogue = "The archive door is open now."
    elif result in {"invalid_tool", "invalid_target", "door_not_locked"}:
        turn.proposal.dialogue = "I could not complete that action."
    return turn, result
