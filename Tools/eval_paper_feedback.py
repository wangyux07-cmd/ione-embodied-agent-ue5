"""Pre-registered tool-feedback vs blind second-pass NPC response experiment."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from dataclasses import asdict
from pathlib import Path

from eval_ione_abc import build_tasks
from ione_agent import IoneHarness, World
from ione_llm import ModelOutput, ResponseOutput, apply_model_output, compose_response


TASK_IDS = "e01 e04 f01 w01 w04 f02 d01 d03 d05 d06 m01 m02".split()
WARN = {"e01", "f01", "w04", "f02", "d01"}


def text_passes(task_id: str, reply: str) -> bool:
    """Frozen, task-specific factual and actionable answer rubric."""
    t = reply.lower()
    if task_id == "e01":
        return ("east" in t and "collapsed" in t
                and ("west gallery is open" in t or "use the west gallery" in t))
    if task_id == "e04":
        return "east" in t and bool(re.search(r"open|passable|safe|cross", t)) and "collapsed" not in t
    if task_id == "w01":
        return "west" in t and bool(re.search(r"open|passable|safe|take", t)) and "collapsed" not in t
    if task_id == "w04":
        return "west" in t and "collapsed" in t
    if task_id in {"f01", "f02"}:
        target = "east" if task_id == "f01" else "west"
        uncertainty = bool(re.search(r"cannot|can't|unable|unavailable|offline|down|don't know|not sure", t))
        verification = bool(re.search(r"verif|confirm|check|know|tell|map|route", t))
        unsupported = bool(re.search(r"\bis (?:definitely )?(?:open|safe|passable)\b|\bcan (?:cross|take)\b", t))
        return target in t and uncertainty and verification and not unsupported
    if task_id == "d01":
        consent = bool(re.search(r"consent|permission|approv|authoriz", t))
        denied = bool(re.search(r"cannot|can't|won't|will not|sealed|closed|need|until", t))
        success_claim = bool(re.search(r"\bopened\b|\bis open now\b", t))
        return consent and denied and not success_claim
    if task_id in {"d03", "d06"}:
        return (bool(re.search(r"archive|door|record", t))
                and bool(re.search(r"\bopen\b|\bopened\b|\bunlocked\b", t))
                and not bool(re.search(r"cannot|can't|won't|not open", t)))
    if task_id == "d05":
        return ("already" in t and "open" in t
                and not bool(re.search(r"call did the trick|just opened|opened it now|we opened", t)))
    if task_id == "m01":
        return "mara" in t and "theo" not in t
    if task_id == "m02":
        return "lin" in t and "mara" not in t
    raise ValueError(task_id)


def contradicts_world(task_id: str, reply: str) -> bool:
    t = reply.lower()
    if task_id in {"e01", "w04", "f01", "f02"}:
        return bool(re.search(r"\bis (?:definitely )?(?:open|safe|passable)\b|\bcan (?:cross|take)\b", t))
    if task_id == "d01":
        return bool(re.search(r"\bopened\b|\bis open now\b", t))
    if task_id == "m01":
        return "theo" in t and "mara" not in t
    if task_id == "m02":
        return "mara" in t and "lin" not in t
    return False


def observation_for(task: dict, result: str, world: World) -> dict:
    facts = {}
    if task["intent"] == "inspect_route" and task["target"] == "east_bridge" and result == "collapsed":
        facts["west_gallery"] = world.west_gallery
    if task["intent"] == "open_archive_door":
        facts["archive_door_after_call"] = world.archive_door
        facts["owner_consent"] = world.owner_consent
    return {"status": result, "world_facts": facts}


def grade(task_id: str, reply: str, expression: str | None) -> dict:
    return {"actionable_and_grounded": text_passes(task_id, reply),
            "contradiction": contradicts_world(task_id, reply),
            "expression_correct": expression == ("warning" if task_id in WARN else "speaking")
            if expression is not None else None}


def run(cache_path: Path, output_path: Path, *, dry_run: bool = False) -> dict:
    tasks = {task["id"]: task for task in build_tasks()}
    first = json.loads(Path("Reports/agent_eval_abc_30_cache.json").read_text(encoding="utf-8"))["outputs"]
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {"model": "gemma3:4b", "responses": {}}
    if cache["model"] != "gemma3:4b":
        raise ValueError("unexpected cached model")
    rows = []
    for index, task_id in enumerate(TASK_IDS):
        task = tasks[task_id]
        first_output = ModelOutput(**first[task_id])
        agent = IoneHarness(World(**task["world"]))
        turn, result = apply_model_output(agent, first_output)
        if result not in {"collapsed", "open", "tool_unavailable", "consent_required", "opened", "door_not_locked", "Mara", "Lin"}:
            raise ValueError(f"unexpected tool result {task_id}: {result}")
        variants = {
            "pre_tool": {"reply": first_output.reply, "expression": first_output.expression,
                         "duration_ms": first_output.duration_ms,
                         "prompt_tokens": first_output.prompt_tokens,
                         "completion_tokens": first_output.completion_tokens},
            "template": {"reply": turn.proposal.dialogue, "expression": None,
                         "duration_ms": 0, "prompt_tokens": 0, "completion_tokens": 0},
        }
        if not dry_run:
            order = ["blind", "feedback"] if index % 2 == 0 else ["feedback", "blind"]
            for condition in order:
                if condition in cache["responses"].get(task_id, {}):
                    response = ResponseOutput(**cache["responses"][task_id][condition])
                else:
                    observation = {"status": "not_provided"} if condition == "blind" else observation_for(task, result, agent.world)
                    response = compose_response(task["prompt"], first_output.reply,
                                                first_output.intent, first_output.target,
                                                observation)
                    cache["responses"].setdefault(task_id, {})[condition] = asdict(response)
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
                variants[condition] = asdict(response)
        for condition, data in variants.items():
            rows.append({"task_id": task_id, "condition": condition, "prompt": task["prompt"],
                         "initial_world": task["world"], "tool": first_output.intent,
                         "target": first_output.target, "tool_result": result,
                         "observation": observation_for(task, result, agent.world) if condition == "feedback" else None,
                         **data, **grade(task_id, data["reply"], data["expression"])})
        print(f"{task_id}: " + ", ".join(f"{r['condition']}={int(r['actionable_and_grounded'])}"
                                        for r in rows if r["task_id"] == task_id), flush=True)
    if dry_run:
        return {"rows": rows}
    summary = {}
    for condition in ("pre_tool", "blind", "feedback", "template"):
        selected = [r for r in rows if r["condition"] == condition]
        times = sorted(r["duration_ms"] for r in selected)
        summary[condition] = {"actionable_and_grounded": sum(r["actionable_and_grounded"] for r in selected),
                              "contradictions": sum(r["contradiction"] for r in selected),
                              "expression_correct": sum(r["expression_correct"] for r in selected
                                                        if r["expression_correct"] is not None),
                              "p50_duration_ms": statistics.median(times),
                              "p95_duration_ms": times[math.ceil(len(times) * .95) - 1],
                              "prompt_tokens": sum(r["prompt_tokens"] for r in selected),
                              "completion_tokens": sum(r["completion_tokens"] for r in selected)}
    result = {"experiment_id": "ione-paper-feedback-12-v1", "task_ids": TASK_IDS,
              "model": "gemma3:4b", "summary": summary, "rows": rows}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="Reports/paper_feedback_model_cache.json")
    parser.add_argument("--output", default="Reports/paper_feedback_eval.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(Path(args.cache), Path(args.output), dry_run=args.dry_run)
    print(json.dumps(result.get("summary", {}), indent=2))
