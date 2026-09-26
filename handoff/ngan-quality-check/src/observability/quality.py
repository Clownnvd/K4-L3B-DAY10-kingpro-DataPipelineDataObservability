from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Missing, non-finite or future ages fail the freshness SLA explicitly."""
    ages = pd.to_numeric(df.get("age_days", pd.Series(index=df.index, dtype=float)), errors="coerce")
    valid = ages.map(lambda age: pd.notna(age) and math.isfinite(float(age)) and age >= 0).astype(bool)
    total = len(df)
    invalid = int((~valid).sum())
    stale = int((valid & ages.gt(settings.freshness_threshold_days)).sum())
    dates = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
    oldest, latest = dates.min(), dates.max()
    ratio = stale / total if total else 0.0
    return {
        "latest_published": latest.isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale,
        "total_rows": total,
        "stale_ratio": ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "invalid_age_rows": invalid,
        "is_fresh": bool(total and invalid == 0 and ratio <= 0.25),
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate an isolated DataFrame with a real GX 1.x suite and freshness SLA."""
    import great_expectations as gx

    required = ("paper_id", "title", "summary", "text_for_embedding", "age_days")
    missing = [column for column in required if column not in df.columns]
    # Normalize only the validation copy so blank strings do not pass not-null
    # expectations. Missing columns receive nulls and an explicit schema failure.
    checked = df.copy(deep=True)
    for column in required:
        if column not in checked:
            checked[column] = None
    for column in required[:-1]:
        checked[column] = checked[column].map(
            lambda value: None if not isinstance(value, str) or not value.strip() else value.strip()
        )
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name="papers_source")
    asset = source.add_dataframe_asset(name="papers_asset")
    definition = asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = definition.get_batch(batch_parameters={"dataframe": checked})
    suite = gx.ExpectationSuite(name="papers_quality")
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    for column in required[:-1]:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))
    validation = batch.validate(suite).to_json_dict()
    freshness = evaluate_freshness_sla(df, settings)
    gx_success = bool(validation["success"] and not missing)
    result = {
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "freshness": freshness,
        "validation": validation,
        "missing_columns": missing,
    }
    # GX may include numpy scalar values; its serializer produces plain JSON.
    result = json.loads(json.dumps(result, default=str))
    _write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Write the SLA result to the caller's explicitly selected artifact path."""
    result = evaluate_freshness_sla(df, settings)
    _write_json(Path(report_path), result)
    return result
