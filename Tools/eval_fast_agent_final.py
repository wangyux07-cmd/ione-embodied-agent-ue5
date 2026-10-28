"""Fresh final-wording validation for the tiered NPC agent."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from eval_fast_agent import run_baseline, run_fast, summarize
from eval_fast_agent_holdout import grade
from ione_agent import World


def tasks() -> list[dict]:
    rows = []

    def add(task_id, prompt, intent, required=(), *, forbidden=(), tool=True,
            result=None, **world):
        rows.append({"id": task_id, "prompt": prompt, "intent": intent,
                     "required": list(required), "forbidden": list(forbidden),
                     "tool": tool, "result": result, "world": asdict(World(**world))})

    add("V01", "Can we take the shattered eastern viaduct or the western walkway?", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("V02", "The west wing corridor survived. Is it usable?", "route",
        ["west gallery is open"])
    add("V03", "The map is dead. Tell me whether the east approach works.", "route",
        ["cannot verify the east bridge"], route_service_available=False)
    add("V04", "The owner approved it. Unseal the records for me.", "door",
        ["door is open"], result="opened", owner_consent=True)
    add("V05", "I'd like to go inside the archive now.", "door",
        ["door remains locked", "consent"], result="consent_required")
    add("V06", "Don't let me into the archive even though I have permission.", "chat",
        tool=False, owner_consent=True)
    add("V07", "Who has the ledger after its transfer? Hazel's old tag is still on it.", "record",
        ["ledger belongs to nia"], forbidden=["hazel"], record_owner="Nia")
    add("V08", "Could you tell me about the archive's design?", "chat", tool=False)
    add("V09", "Can we enter the record room? The door is already open.", "door",
        ["door was already open"], result="door_not_locked", owner_consent=True,
        archive_door="open")
    add("V10", "Which way remains: east or west? Both look broken.", "route",
        ["east bridge has collapsed", "west gallery has collapsed"], west_gallery="collapsed")
    add("V11", "Unlock the archive only if you can confirm its owner approved.", "door",
        ["door remains locked", "consent"], result="consent_required")
    add("V12", "I'm not asking you to open it; just check the west route.", "route",
        ["west gallery is open"])
    assert len(rows) == 12
    return rows


def run(path: Path, model: str) -> dict:
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "experiment_id": "ione-fast-agent-final-12", "rows": []}
    by_key = {(row["id"], row["mode"]) for row in saved["rows"]}
    for mode in ("B0_gemma_twopass", f"B5_tiered_domain_action_{model}"):
        for task in tasks():
            if (task["id"], mode) in by_key:
                continue
            try:
                row = run_baseline(task) if mode == "B0_gemma_twopass" else run_fast(
                    task, model, repair=True, domain_action=True, mode_name=mode)
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
    parser.add_argument("--output", default="Reports/fast_agent_final_12.json")
    parser.add_argument("--model", default="qwen3:1.7b")
    args = parser.parse_args()
    result = run(Path(args.output), args.model)
    print(json.dumps(result["summary"], indent=2))
