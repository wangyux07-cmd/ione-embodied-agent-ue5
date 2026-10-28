"""Paired twenty-case player-visible NPC quality/latency comparison."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path

from ione_agent import IoneHarness, World
from ione_fast_agent import (execute_fast, infer_fast_plan, preplan_domain_action,
                             preplan_explicit_negative, repair_route_intent, needs_large_router, FastPlan)
from ione_llm import apply_model_output, compose_anchored_response, infer
from ione_response import make_fact_card, publish_response


def tasks() -> list[dict]:
    rows = []

    def add(task_id, prompt, intent, required=(), *, forbidden=(), tool=True, **world):
        rows.append({"id": task_id, "prompt": prompt, "intent": intent,
                     "required": list(required), "forbidden": list(forbidden),
                     "tool": tool, "world": asdict(World(**world))})

    add("R01", "Can we cross the east bridge, or is the west gallery safer?", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("R02", "Is the west gallery passable right now?", "route", ["west gallery is open"])
    add("R03", "Which route is usable, the east bridge or the west gallery?", "route",
        ["east bridge has collapsed", "west gallery has collapsed"], west_gallery="collapsed")
    add("R04", "Compare both passages for me after the repairs.", "route",
        ["east bridge is open", "west gallery has collapsed"], east_bridge="open", west_gallery="collapsed")
    add("R05", "If the west gallery caved in, can we use the east bridge instead?", "route",
        ["west gallery has collapsed", "east bridge is open"], east_bridge="open", west_gallery="collapsed")
    add("R06", "Check the east bridge, even though the map service is offline.", "route",
        ["cannot verify the east bridge"], route_service_available=False)
    add("R07", "Please verify the west gallery while the map service is down.", "route",
        ["cannot verify the west gallery"], route_service_available=False)
    add("R08", "Is the eastern crossing usable after rebuilding?", "route", ["east bridge is open"], east_bridge="open")
    add("R09", "Find any passage that is still open; check the east and west routes.", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("R10", "Show me a viable path, east or west, if either remains.", "route",
        ["east bridge has collapsed", "west gallery has collapsed"], west_gallery="collapsed")
    add("D01", "Please open the archive door.", "door", ["door remains locked", "consent"])
    add("D02", "The owner has approved. Open the archive door.", "door", ["door is open"], owner_consent=True)
    add("D03", "I say the owner gave consent, so unlock the archive door.", "door",
        ["door remains locked", "consent"], owner_consent=False)
    add("D04", "Open the archive door again, please.", "door", ["door was already open"],
        owner_consent=True, archive_door="open")
    add("D05", "Do not open the archive door. Tell me its history instead.", "chat", tool=False)
    add("M01", "My old note names Theo. Who owns the red ledger now?", "record",
        ["ledger belongs to mara"], forbidden=["theo"])
    add("M02", "I thought Mara owned the red ledger; has that changed?", "record",
        ["ledger belongs to lin"], forbidden=["mara"], record_owner="Lin")
    add("M03", "Check the current owner of the red ledger.", "record",
        ["ledger belongs to quinn"], record_owner="Quinn")
    add("C01", "Do not check the bridge. Just talk to me first.", "chat", tool=False)
    add("C02", "Please do not unlock anything. I'm thinking.", "chat", tool=False, owner_consent=True)
    assert len(rows) == 20 and len({r["id"] for r in rows}) == 20
    return rows


def run_baseline(task: dict) -> dict:
    started = time.perf_counter()
    world = World(**task["world"])
    agent = IoneHarness(world)
    first = infer(task["prompt"], model="gemma3:4b")
    turn, result = apply_model_output(agent, first)
    trace = [{"tool": first.intent, "target": first.target, "result": result}] if first.intent != "chat" else []
    dialogue, pose, publish_reason = turn.proposal.dialogue, first.expression, "no_second_pass"
    if result in {"collapsed", "open", "tool_unavailable", "consent_required", "opened", "door_not_locked",
                  world.record_owner} and first.intent != "chat":
        card = make_fact_card(first.intent, first.target, result, world)
        second = compose_anchored_response(task["prompt"], card.sentence, card.expression)
        dialogue, pose, publish_reason = publish_response(second, card)
        second_data = asdict(second)
    else:
        second_data = None
    return {"mode": "B0_gemma_twopass", "id": task["id"], "prompt": task["prompt"],
            "intent": {"inspect_route": "route", "open_archive_door": "door", "lookup_record": "record"}.get(first.intent, "chat"),
            "targets": [first.target] if first.intent == "inspect_route" else [],
            "dialogue": dialogue, "pose": pose, "trace": trace, "world": asdict(world),
            "duration_ms": (time.perf_counter() - started) * 1000,
            "first_model": asdict(first), "second_model": second_data, "publish_reason": publish_reason}


def run_fast(task: dict, model: str, *, repair: bool = False, domain_action: bool = False,
             mode_name: str | None = None) -> dict:
    started = time.perf_counter()
    world = World(**task["world"])
    plan = preplan_explicit_negative(task["prompt"])
    route_source = "explicit_negative_policy" if plan else "small_model"
    if plan is None and domain_action:
        plan = preplan_domain_action(task["prompt"])
        if plan is not None:
            route_source = "domain_action_policy"
    if plan is None:
        plan = infer_fast_plan(task["prompt"], model=model)
    repair_reason = "not_applied"
    if repair and route_source == "small_model":
        plan, repair_reason = repair_route_intent(task["prompt"], plan)
    large_router = None
    if domain_action and route_source == "small_model" and needs_large_router(task["prompt"], plan):
        large_router = infer(task["prompt"], model="gemma3:4b")
        intent = {"inspect_route": "route", "open_archive_door": "door",
                  "lookup_record": "record", "chat": "chat"}.get(large_router.intent, "chat")
        targets = ([large_router.target] if intent == "route" and
                   large_router.target in {"east_bridge", "west_gallery"} else [])
        plan = FastPlan(intent, targets, plan.duration_ms + large_router.duration_ms,
                        plan.prompt_tokens + large_router.prompt_tokens,
                        plan.completion_tokens + large_router.completion_tokens,
                        plan.raw)
        route_source = "small_model_then_large_router"
    turn = execute_fast(task["prompt"], world, plan)
    return {"mode": mode_name or (f"B3_tiered_repair_{model}" if repair else f"B2_tiered_{model}"),
            "id": task["id"], "prompt": task["prompt"],
            "intent": plan.intent, "targets": plan.targets, "dialogue": turn.dialogue,
            "pose": turn.pose, "trace": turn.tool_trace, "world": turn.world,
            "duration_ms": (time.perf_counter() - started) * 1000,
            "router": asdict(plan), "route_source": route_source,
            "repair_reason": repair_reason,
            "large_router": asdict(large_router) if large_router else None,
            "execution_ms": turn.duration_ms}


def grade(task: dict, row: dict) -> dict:
    dialogue = row["dialogue"].lower().replace("has also collapsed", "has collapsed")
    required = all(fragment in dialogue for fragment in task["required"])
    forbidden = not any(fragment in dialogue for fragment in task["forbidden"])
    initial = task["world"]
    expected_door = "open" if task["id"] == "D02" else initial["archive_door"]
    world_ok = row["world"]["archive_door"] == expected_door
    tool_calls = [event for event in row["trace"] if "tool" in event]
    tool_ok = bool(tool_calls) == task["tool"]
    if task["id"] in {"D01", "D03"}:
        tool_ok = tool_ok and tool_calls[-1].get("result") == "consent_required"
    if task["id"] == "D04":
        tool_ok = tool_ok and tool_calls[-1].get("result") == "door_not_locked"
    if task["id"] == "D02":
        tool_ok = tool_ok and tool_calls[-1].get("result") == "opened"
    return {"intent_correct": row["intent"] == task["intent"], "required_facts": required,
            "no_forbidden_claim": forbidden, "world_correct": world_ok, "tool_correct": tool_ok,
            "success": (row["intent"] == task["intent"] and required and forbidden and world_ok and tool_ok)}


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for mode in sorted({r["mode"] for r in rows}):
        selected = [r for r in rows if r["mode"] == mode]
        times = sorted(r["duration_ms"] for r in selected if r.get("error") is None)
        summary[mode] = {"n": len(selected), "success": sum(r["grade"]["success"] for r in selected),
                         "errors": sum(r.get("error") is not None for r in selected),
                         "intent_correct": sum(r["grade"]["intent_correct"] for r in selected),
                         "world_correct": sum(r["grade"]["world_correct"] for r in selected),
                         "tool_correct": sum(r["grade"]["tool_correct"] for r in selected),
                         "latency_n": len(times),
                         "p50_wall_ms": statistics.median(times) if times else None,
                         "p95_wall_ms": times[math.ceil(len(times) * .95) - 1] if times else None,
                         "max_wall_ms": max(times) if times else None}
    return summary


def run(path: Path, model: str) -> dict:
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"experiment_id": "ione-fast-agent-20-v1", "rows": []}
    by_key = {(r["id"], r["mode"]): r for r in saved["rows"]}
    all_tasks = tasks()
    for mode in ("B0_gemma_twopass", f"B2_tiered_{model}", f"B3_tiered_repair_{model}",
                 f"B4_tiered_consistency_{model}"):
        for task in all_tasks:
            key = task["id"], mode
            if key in by_key:
                continue
            try:
                row = (run_baseline(task) if mode == "B0_gemma_twopass" else
                       run_fast(task, model, repair=mode.startswith(("B3", "B4")), mode_name=mode))
                row["error"] = None
            except Exception as exc:
                row = {"mode": mode, "id": task["id"], "prompt": task["prompt"],
                       "intent": "error", "targets": [], "dialogue": "", "pose": "listening",
                       "trace": [], "world": task["world"], "duration_ms": 0.0,
                       "error": f"{type(exc).__name__}: {exc}"}
            row["grade"] = grade(task, row)
            saved["rows"].append(row)
            saved["summary"] = summarize(saved["rows"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{mode} {task['id']}: {int(row['grade']['success'])} {row['duration_ms']:.0f}ms {row['error'] or ''}", flush=True)
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="Reports/fast_agent_20.json")
    parser.add_argument("--model", default="qwen3:0.6b")
    args = parser.parse_args()
    result = run(Path(args.output), args.model)
    print(json.dumps(result["summary"], indent=2))
