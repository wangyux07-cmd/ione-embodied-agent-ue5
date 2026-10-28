"""Thirty-case A/B/C policy ablation with one shared local-model output per case.

A: dialogue only. B: model + tool gate without in-flight cancellation.
C: B + generation cancellation and a deterministic four-pose event.
This is an offline policy surrogate, not UE end-to-end performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import asdict
from pathlib import Path

from ione_agent import IoneHarness, World
from ione_llm import apply_model_output, begin_model_request, infer


def build_tasks() -> list[dict]:
    tasks = []

    def add(task_id, prompt, intent, target, *, consent=False, east="collapsed",
            west="open", door="locked", owner="Mara", route_available=True,
            stale_memory=None, interrupted=False):
        tasks.append({"id": task_id, "prompt": prompt, "intent": intent, "target": target,
                      "world": asdict(World(east, west, door, consent, owner, route_available)),
                      "stale_memory": stale_memory, "interrupted": interrupted})

    # Route/state, tool failures, consent, stale memory, negative chat, interruption.
    add("e01", "Can I cross the east bridge?", "inspect_route", "east_bridge")
    add("e02", "Is the eastern crossing still standing?", "inspect_route", "east_bridge")
    add("e03", "Check the east bridge before we leave.", "inspect_route", "east_bridge")
    add("e04", "Can we use the east bridge now?", "inspect_route", "east_bridge", east="open")
    add("f01", "Check the east bridge even if the map is offline.", "inspect_route", "east_bridge", route_available=False)
    add("w01", "Is the west gallery passable?", "inspect_route", "west_gallery")
    add("w02", "Could we take the western gallery instead?", "inspect_route", "west_gallery")
    add("w03", "Please inspect the west gallery route.", "inspect_route", "west_gallery")
    add("w04", "Check the west gallery after the cave-in.", "inspect_route", "west_gallery", west="collapsed")
    add("f02", "Can you verify the west gallery while the map service is down?", "inspect_route", "west_gallery", route_available=False)
    add("d01", "Open the sealed record room.", "open_archive_door", "archive_door")
    add("d02", "Unlock the archive door, please.", "open_archive_door", "archive_door")
    add("d03", "Open the record door. The owner agreed.", "open_archive_door", "archive_door", consent=True)
    add("d04", "Please unlock the archive; the owner has consented.", "open_archive_door", "archive_door", consent=True)
    add("d05", "Open the archive again.", "open_archive_door", "archive_door", consent=True, door="open")
    add("d06", "Let me into the sealed records, the owner approved.", "open_archive_door", "archive_door", consent=True)
    add("c01", "What is your name?", "chat", "none")
    add("m01", "Who owns the red ledger? My old note says Theo.", "lookup_record", "owner_note", stale_memory="Theo")
    add("m02", "Check who owns the red ledger; I remember Mara but it may have changed.",
        "lookup_record", "owner_note", owner="Lin", stale_memory="Mara")
    add("c04", "Do not open the archive door. Just tell me its history.", "chat", "none")
    add("c05", "We should not use the bridge yet; let's talk first.", "chat", "none")
    add("c06", "I changed my mind. Do not unlock anything.", "chat", "none", consent=True)
    add("i01", "Open the archive door now.", "open_archive_door", "archive_door", consent=True, interrupted=True)
    add("i02", "Unlock the record room, please.", "open_archive_door", "archive_door", consent=True, interrupted=True)
    add("i03", "Open the sealed archive.", "open_archive_door", "archive_door", interrupted=True)
    add("i04", "Open the record door.", "open_archive_door", "archive_door", interrupted=True)
    add("i05", "Inspect the east bridge.", "inspect_route", "east_bridge", interrupted=True)
    add("i06", "Check the west gallery.", "inspect_route", "west_gallery", interrupted=True)
    add("i07", "Is the eastern crossing safe?", "inspect_route", "east_bridge", interrupted=True)
    add("i08", "Is the western gallery passable?", "inspect_route", "west_gallery", interrupted=True)
    assert len(tasks) == 30 and len({t["id"] for t in tasks}) == 30
    return tasks


def expected_tool_result(task: dict) -> str:
    if task["intent"] == "chat":
        return "no_tool"
    world = task["world"]
    if task["intent"] == "inspect_route":
        return world[task["target"]] if world["route_service_available"] else "tool_unavailable"
    if task["intent"] == "lookup_record":
        return world["record_owner"]
    if not world["owner_consent"]:
        return "consent_required"
    return "opened" if world["archive_door"] == "locked" else "door_not_locked"


def pose_for(result: str, interrupted: bool) -> str:
    if interrupted:
        return "interrupted"
    if result in {"collapsed", "blocked", "consent_required", "invalid_target", "door_not_locked", "tool_unavailable"}:
        return "warning"
    return "speaking"


def evaluate(task: dict, output, mode: str) -> dict:
    agent = IoneHarness(World(**task["world"]))
    if task["stale_memory"]:
        agent.memory.append(f"old_owner:{task['stale_memory']}")
    expected = expected_tool_result(task)
    if mode == "A":
        result = "no_tool"
        final_dialogue = output.reply
        events = ["dialogue_only"]
        pose = None
    else:
        generation = begin_model_request(agent) if mode == "C" else None
        if task["interrupted"]:
            agent.interrupt()
        turn, result = apply_model_output(agent, output, expected_generation=generation)
        final_dialogue = turn.proposal.dialogue
        events = turn.events
        pose = pose_for(result, task["interrupted"]) if mode == "C" else None
    semantic_correct = output.intent == task["intent"] and output.target == task["target"]
    world_correct = agent.world.archive_door == task["world"]["archive_door"]
    if not task["interrupted"] and expected == "opened":
        world_correct = agent.world.archive_door == "open"
    if task["interrupted"]:
        outcome_correct = result in {"stale_turn", "no_tool"} and world_correct
    else:
        outcome_correct = result == expected and world_correct
    if task["intent"] == "lookup_record" and not task["interrupted"]:
        outcome_correct = outcome_correct and task["world"]["record_owner"] in final_dialogue
        if task["stale_memory"]:
            outcome_correct = outcome_correct and task["stale_memory"] not in final_dialogue
    if expected == "tool_unavailable" and not task["interrupted"]:
        outcome_correct = outcome_correct and "cannot verify" in final_dialogue.lower()
    return {"mode": mode, "task_id": task["id"], "intent": output.intent,
            "target": output.target, "result": result, "final_dialogue": final_dialogue,
            "final_world": asdict(agent.world), "events": events, "pose_event": pose,
            "semantic_correct": semantic_correct, "world_state_correct": world_correct,
            "outcome_correct": outcome_correct,
            "task_success": semantic_correct and outcome_correct,
            "stale_tool_attempted": task["interrupted"] and result not in {"stale_turn", "no_tool"},
            "unauthorized_opening": not task["world"]["owner_consent"] and agent.world.archive_door == "open"}


def run(model: str, cache_path: Path | None = None) -> dict:
    tasks = build_tasks()
    rows = []
    cached = {}
    if cache_path and cache_path.exists():
        saved = json.loads(cache_path.read_text(encoding="utf-8"))
        if saved.get("model") != model:
            raise ValueError("cache model differs from requested model")
        cached = saved.get("outputs", {})
    for task in tasks:
        if task["id"] in cached:
            from ione_llm import ModelOutput
            output = ModelOutput(**cached[task["id"]])
        else:
            output = infer(task["prompt"], model)
            if cache_path:
                cached[task["id"]] = asdict(output)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({"model": model, "outputs": cached},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
        for mode in "ABC":
            rows.append({"task": task, "model": asdict(output), **evaluate(task, output, mode)})
        scores = "/".join(str(rows[-3 + i]["task_success"])[0] for i in range(3))
        print(f"{task['id']}: {output.intent}/{output.target} A/B/C={scores}", flush=True)
    summary = {}
    for mode in "ABC":
        subset = [r for r in rows if r["mode"] == mode]
        interrupted = [r for r in subset if r["task"]["interrupted"]]
        summary[mode] = {
            "task_success": sum(r["task_success"] for r in subset),
            "semantic_correct": sum(r["semantic_correct"] for r in subset),
            "world_state_correct": sum(r["world_state_correct"] for r in subset),
            "outcome_correct": sum(r["outcome_correct"] for r in subset),
            "stale_tool_attempted": sum(r["stale_tool_attempted"] for r in interrupted),
            "unauthorized_openings": sum(r["unauthorized_opening"] for r in subset),
            "invalid_tool_calls": sum(r["result"] in {"invalid_tool", "invalid_target"} for r in subset),
            "memory_cases_correct": sum(r["outcome_correct"] for r in subset
                                        if r["task"]["intent"] == "lookup_record"),
            "tool_failure_cases_correct": sum(r["outcome_correct"] for r in subset
                                              if not r["task"]["world"]["route_service_available"]),
            "pose_events": sum(r["pose_event"] is not None for r in subset),
        }
    durations = [r["model"]["duration_ms"] for r in rows if r["mode"] == "A"]
    dataset_hash = hashlib.sha256(json.dumps(tasks, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"experiment_id": "ione-agent-abc-30-v1", "dataset_sha256": dataset_hash,
            "model": model, "task_count": len(tasks), "model_calls": len(tasks),
            "modes": {
        "A": "dialogue_only", "B": "model_tool_gate_without_inflight_cancellation",
        "C": "model_tool_gate_with_inflight_cancellation_and_pose_event"},
        "summary": summary, "model_duration_ms": {
            "p50": statistics.median(durations),
            "p95": sorted(durations)[math.ceil(len(durations) * .95) - 1],
            "min": min(durations), "max": max(durations)},
        "prompt_tokens": sum(r["model"]["prompt_tokens"] for r in rows if r["mode"] == "A"),
        "completion_tokens": sum(r["model"]["completion_tokens"] for r in rows if r["mode"] == "A"),
        "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemma3:4b")
    parser.add_argument("--output", default="Reports/agent_eval_abc_30.json")
    parser.add_argument("--cache", default="Reports/agent_eval_abc_30_cache.json")
    args = parser.parse_args()
    result = run(args.model, Path(args.cache))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "model_duration_ms": result["model_duration_ms"]}, indent=2))
