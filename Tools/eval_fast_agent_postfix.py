"""Fresh action-routing validation after the V-set failures."""

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

    add("W01", "Is the eastern overpass usable, or should we take the western hallway?", "route",
        ["east bridge has collapsed", "west gallery is open"])
    add("W02", "The western passage collapsed. Is the eastern side still open?", "route",
        ["west gallery has collapsed", "east bridge is open"],
        west_gallery="collapsed", east_bridge="open")
    add("W03", "The local chart is offline; which of the two ways can we take?", "route",
        ["cannot verify the east bridge and west gallery"], route_service_available=False)
    add("W04", "The owner approved this. Grant access to the records vault.", "door",
        ["door is open"], result="opened", owner_consent=True)
    add("W05", "No permission yet, but unseal the vault anyway.", "door",
        ["door remains locked", "consent"], result="consent_required")
    add("W06", "Don't remove the seal from the archive. I only want to wait.", "chat",
        tool=False, owner_consent=True)
    add("W07", "My old note says Beatrice. Who now owns the red ledger?", "record",
        ["ledger belongs to quinn"], forbidden=["beatrice"], record_owner="Quinn")
    add("W08", "Take the eastern path after repairs; can we cross it?", "route",
        ["east bridge is open"], east_bridge="open")
    add("W09", "Get us inside the records room; it is already unlocked.", "door",
        ["door was already open"], result="door_not_locked", owner_consent=True,
        archive_door="open")
    add("W10", "Explain how the archive door was built. Do not open it.", "chat", tool=False)
    assert len(rows) == 10
    return rows


def run(path: Path, model: str) -> dict:
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "experiment_id": "ione-fast-agent-postfix-10", "rows": []}
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
    parser.add_argument("--output", default="Reports/fast_agent_postfix_10.json")
    parser.add_argument("--model", default="qwen3:1.7b")
    args = parser.parse_args()
    result = run(Path(args.output), args.model)
    print(json.dumps(result["summary"], indent=2))
