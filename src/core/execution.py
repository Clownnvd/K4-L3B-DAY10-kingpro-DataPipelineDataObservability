"""Append run receipts for successful and failed CLI executions."""
from datetime import UTC, datetime
import json
from pathlib import Path
import time


def run_recorded(stage, action):
    start = time.monotonic()
    receipt = {"stage": stage, "started_at": datetime.now(UTC).isoformat()}
    try:
        result = action()
    except Exception as exc:
        receipt.update(status="failed", error_type=type(exc).__name__)
        raise
    else:
        receipt["status"] = "passed"
        return result
    finally:
        receipt["elapsed_seconds"] = round(time.monotonic() - start, 3)
        path = Path(__file__).resolve().parents[2] / "data" / "results" / "execution_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt) + "\n")
