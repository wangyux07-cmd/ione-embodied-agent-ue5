"""Check that a newer turn invalidates an in-flight model-routed turn."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


OUTPUT = Path(__file__).resolve().parents[1] / "Reports" / "ue5_ione_live" / "interrupt_smoke.json"


def request(text: str, turn_id: int) -> tuple[int, dict]:
    data = json.dumps({"text": text, "turn_id": turn_id}, ensure_ascii=False).encode("utf-8")
    req = Request("http://127.0.0.1:8765/turn", data,
                  {"Content-Type": "application/json; charset=utf-8"})
    try:
        with urlopen(req, timeout=45) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main() -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        old = pool.submit(request, "Could you check which path is safe to the archive?", 101)
        time.sleep(0.25)
        new_status, new_body = request("红账本是谁的？", 102)
        old_status, old_body = old.result()
    assert new_status == 200 and new_body["intent"] == "record", (new_status, new_body)
    assert old_status == 409 and old_body["error"] == "stale_turn", (old_status, old_body)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"older": {"status": old_status, "body": old_body},
                                  "newer": {"status": new_status, "body": new_body}},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"stale older turn {old_status}; newer record turn {new_status} → {OUTPUT}")


if __name__ == "__main__":
    main()
