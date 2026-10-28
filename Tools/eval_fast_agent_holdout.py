"""New-wording holdout for the final tiered NPC architecture."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from eval_fast_agent import run_baseline, run_fast, summarize
from ione_agent import World


def tasks() -> list[dict]:
    rows = []

    def add(task_id, prompt, intent, required=(), *, forbidden=(), tool=True,
            result=None, **world):
        rows.append({"id": task_id, "prompt": prompt, "intent": intent,
                     "required": list(required), "forbidden": list(forbidden),
                     "tool": tool, "result": result, "world": asdict(World(**world))})

    add("H01", "Can we use the eastern span, or is the west gallery our way through?", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("H02", "Between the east and west sides, which one is still standing?", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("H03", "What about the corridor on the western side—is it passable?", "route",
        ["west gallery is open"])
    add("H04", "The map terminal froze. Can you confirm the eastern crossing?", "route",
        ["cannot verify the east bridge"], route_service_available=False)
    add("H05", "The owner signed off. Move the seal aside so I can enter.", "door",
        ["door is open"], result="opened", owner_consent=True)
    add("H06", "Please leave the archive sealed. I want to think first.", "chat", tool=False)
    add("H07", "The old label says Hazel owns the red ledger. Who owns it today?", "record",
        ["ledger belongs to quinn"], forbidden=["hazel"], record_owner="Quinn")
    add("H08", "Can we use the east crossing or the western hall?", "route",
        ["east bridge is open", "west gallery has collapsed"], east_bridge="open", west_gallery="collapsed")
    add("H09", "I told you not to unlock that door. We're only talking.", "chat", tool=False,
        owner_consent=True)
    add("H10", "What does that cassette at your ear do?", "chat", tool=False)
    add("H11", "Let us into the archive, please.", "door", ["door was already open"],
        result="door_not_locked", owner_consent=True, archive_door="open")
    add("H12", "Tell me the history of the east bridge, without checking its current state.",
        "chat", tool=False)
    assert len(rows) == 12
    return rows


def grade(task: dict, row: dict) -> dict:
    dialogue = row["dialogue"].lower().replace("has also collapsed", "has collapsed")
    tool_calls = [event for event in row["trace"] if "tool" in event]
    intent_ok = row["intent"] == task["intent"]
    facts_ok = all(fragment in dialogue for fragment in task["required"])
    forbidden_ok = not any(fragment in dialogue for fragment in task["forbidden"])
    tool_ok = bool(tool_calls) == task["tool"]
    if task["result"]:
        tool_ok = tool_ok and tool_calls[-1].get("result") == task["result"]
    expected_door = "open" if task["result"] == "opened" else task["world"]["archive_door"]
    world_ok = row["world"]["archive_door"] == expected_door
    return {"intent_correct": intent_ok, "required_facts": facts_ok,
            "no_forbidden_claim": forbidden_ok, "world_correct": world_ok,
            "tool_correct": tool_ok,
            "success": intent_ok and facts_ok and forbidden_ok and tool_ok and world_ok}


def run(path: Path, model: str) -> dict:
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "experiment_id": "ione-fast-agent-holdout-12", "rows": []}
    by_key = {(row["id"], row["mode"]) for row in saved["rows"]}
    for mode in ("B0_gemma_twopass", f"B4_tiered_consistency_{model}",
                 f"B5_tiered_domain_action_{model}"):
        for task in tasks():
            if (task["id"], mode) in by_key:
                continue
            try:
                row = run_baseline(task) if mode == "B0_gemma_twopass" else run_fast(
                    task, model, repair=True, domain_action=mode.startswith("B5"), mode_name=mode)
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
    parser.add_argument("--output", default="Reports/fast_agent_holdout_12.json")
    parser.add_argument("--model", default="qwen3:1.7b")
    args = parser.parse_args()
    result = run(Path(args.output), args.model)
    print(json.dumps(result["summary"], indent=2))
