from __future__ import annotations

from pipelines.corruption_flow import main
from core.execution import run_recorded


if __name__ == "__main__":
    run_recorded("corruption_repair", main)
