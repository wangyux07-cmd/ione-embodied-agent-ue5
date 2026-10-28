"""Smoke-test the running Ione loopback bridge and retain raw responses."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Reports" / "ue5_ione_live" / "bridge_smoke.json"
CASES = [
    ("东桥还能走吗？", "route", "warning", "inspect_route"),
    ("我怎样才能安全到达那边？", "route", "warning", "inspect_route"),
    ("红账本是谁的？", "record", "speaking", "lookup_record"),
    ("打开档案室的门", "door", "warning", "open_archive_door"),
    ("不要打开档案室", "chat", "listening", None),
]


def main() -> None:
    with urlopen("http://127.0.0.1:8765/health", timeout=3) as response:
        health = json.load(response)
    assert health["status"] == "ready"
    observations = []
    for turn_id, (text, intent, pose, tool) in enumerate(CASES, 1):
        body = json.dumps({"text": text, "turn_id": turn_id}, ensure_ascii=False).encode("utf-8")
        request = Request("http://127.0.0.1:8765/turn", body,
                          {"Content-Type": "application/json; charset=utf-8"})
        with urlopen(request, timeout=40) as response:
            result = json.load(response)
        assert result["intent"] == intent, (text, result)
        assert result["pose"] == pose, (text, result)
        assert (result["trace"][0]["tool"] if result["trace"] else None) == tool, (text, result)
        assert result["world"]["archive_door"] == "locked", (text, result)
        if intent == "door":
            assert result["trace"][0]["result"] == "consent_required", result
        observations.append({"input": text, **result})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"health": health, "cases": observations},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(observations)}/{len(CASES)} live bridge cases passed → {OUTPUT}")


if __name__ == "__main__":
    main()
