"""Clean the preserved source snapshot without fetching data or calling an LLM."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json

from core.config import load_settings
from core.utils import write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="ISO date/time; default is current UTC time")
    args = parser.parse_args()
    run_date = datetime.fromisoformat(args.run_date) if args.run_date else datetime.now(UTC)
    settings = load_settings()
    records = load_raw_records(settings.paths.raw_records_json)
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError(f"No usable records; existing clean files were preserved: {df.attrs['cleaning_report']}")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    report = df.attrs["cleaning_report"]
    write_json(settings.paths.clean_json.with_name("cleaning_report.json"), report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
