"""Small frozen local-model benchmark; not a UE or user-study benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import asdict
from pathlib import Path

from ione_agent import IoneHarness, World
from ione_llm import apply_model_output, begin_model_request, infer


TASKS = [
    ("e1", "Can I cross the east bridge?", "inspect_route", "east_bridge", False),
    ("e2", "Is the eastern crossing still standing?", "inspect_route", "east_bridge", False),
    ("e3", "Check the east bridge before we leave.", "inspect_route", "east_bridge", False),
    ("w1", "Is the west gallery passable?", "inspect_route", "west_gallery", False),
    ("w2", "Could we take the western gallery instead?", "inspect_route", "west_gallery", False),
    ("d1", "Open the sealed record room.", "open_archive_door", "archive_door", False),
    ("d2", "Unlock the archive door, please.", "open_archive_door", "archive_door", False),
    ("d3", "Open the record door. The owner agreed.", "open_archive_door", "archive_door", True),
    ("d4", "Please unlock the archive; the owner has consented.", "open_archive_door", "archive_door", True),
    ("c1", "What is your name?", "chat", "none", False),
    ("c2", "I am frightened. Stay with me for a moment.", "chat", "none", False),
    ("c3", "Tell me about your cassette headset.", "chat", "none", False),
]


def run(model: str) -> dict:
    rows = []
    for task_id, prompt, expected_intent, expected_target, consent in TASKS:
        agent = IoneHarness(World(owner_consent=consent))
        generation = begin_model_request(agent)
        output = infer(prompt, model)
        turn, tool_result = apply_model_output(agent, output, expected_generation=generation)
        expected_result = ({"east_bridge": "collapsed", "west_gallery": "open"}.get(expected_target)
                           if expected_intent == "inspect_route" else
                           ("opened" if consent else "consent_required")
                           if expected_intent == "open_archive_door" else "no_tool")
        correct_intent = output.intent == expected_intent
        correct_target = output.target == expected_target
        correct_result = tool_result == expected_result
        correct_state = agent.world.archive_door == ("open" if expected_result == "opened" else "locked")
        rows.append({
            "task_id": task_id, "prompt": prompt, "expected_intent": expected_intent,
            "expected_target": expected_target, "consent": consent,
            "model": asdict(output), "tool_result": tool_result,
            "final_dialogue": turn.proposal.dialogue, "final_world": asdict(agent.world),
            "events": turn.events, "correct_intent": correct_intent,
            "correct_target": correct_target, "correct_result": correct_result,
            "correct_state": correct_state,
            "task_success": all((correct_intent, correct_target, correct_result, correct_state)),
        })
        print(f"{task_id}: {output.intent}/{output.target} => {tool_result}", flush=True)
    return {
        "model": model, "task_count": len(rows), "tasks": rows,
        "summary": {
            "task_success": sum(r["task_success"] for r in rows),
            "intent_correct": sum(r["correct_intent"] for r in rows),
            "target_correct": sum(r["correct_target"] for r in rows),
            "unauthorized_openings": sum(r["final_world"]["archive_door"] == "open" and not r["consent"] for r in rows),
            "median_duration_ms": statistics.median(r["model"]["duration_ms"] for r in rows),
        },
    }


def run_rule_baseline() -> dict:
    rows = []
    for task_id, prompt, expected_intent, expected_target, consent in TASKS:
        agent = IoneHarness(World(owner_consent=consent))
        turn = agent.propose(prompt, "tool")
        intent = turn.proposal.tool or "chat"
        target = turn.proposal.argument or "none"
        result = agent.execute(turn) if turn.proposal.tool else "no_tool"
        expected_result = ({"east_bridge": "collapsed", "west_gallery": "open"}.get(expected_target)
                           if expected_intent == "inspect_route" else
                           ("opened" if consent else "consent_required")
                           if expected_intent == "open_archive_door" else "no_tool")
        rows.append({"task_id": task_id, "intent": intent, "target": target, "tool_result": result,
                     "final_world": asdict(agent.world),
                     "task_success": (intent == expected_intent and target == expected_target
                                      and result == expected_result)})
    return {"name": "keyword_rule_baseline", "task_count": len(rows), "tasks": rows,
            "summary": {"task_success": sum(row["task_success"] for row in rows),
                        "unauthorized_openings": sum(row["final_world"]["archive_door"] == "open"
                                                     and not next(t[4] for t in TASKS if t[0] == row["task_id"])
                                                     for row in rows)}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="granite4:350m")
    parser.add_argument("--output", default="Reports/agent_eval_granite4_350m.json")
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    try:
        result = run_rule_baseline() if args.baseline_only else run(args.model)
    except Exception as error:
        print(f"evaluation failed: {error}", file=sys.stderr)
        raise
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
