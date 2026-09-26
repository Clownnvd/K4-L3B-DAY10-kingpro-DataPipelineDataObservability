from __future__ import annotations

from pipelines.phase1 import main
from core.execution import run_recorded


if __name__ == "__main__":
    run_recorded("baseline", main)
