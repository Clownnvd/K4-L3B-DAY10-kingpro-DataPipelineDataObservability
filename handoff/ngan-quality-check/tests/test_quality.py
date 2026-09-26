import json

import pandas as pd
import pytest

from core.config import load_settings
from observability.quality import build_freshness_report, run_data_quality_checks


def papers(count=8):
    return pd.DataFrame({
        "paper_id": [f"10.1234/{i}" for i in range(count)],
        "title": ["Research paper"] * count,
        "summary": ["A sufficiently detailed research summary for validation."] * count,
        "text_for_embedding": ["Research text with the complete abstract."] * count,
        "age_days": [10] * count,
        "published": ["2026-09-16"] * count,
    })


def test_valid_data_passes_real_gx_and_writes_json(tmp_path):
    settings = load_settings(tmp_path)
    frame = papers()
    original = frame.copy(deep=True)
    result = run_data_quality_checks(frame, settings, "baseline")
    assert result["success"] and result["gx_success"]
    assert result["validation"]["statistics"]["evaluated_expectations"] >= 4
    assert json.loads(settings.paths.baseline_quality_report.read_text()) == result
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("column,value", [
    ("paper_id", None), ("paper_id", "  "), ("title", None),
    ("title", "\n"), ("text_for_embedding", None),
    ("text_for_embedding", " "), ("summary", None), ("summary", "too short"),
])
def test_missing_blank_or_short_values_fail_quality(tmp_path, column, value):
    frame = papers()
    frame.loc[0, column] = value
    result = run_data_quality_checks(frame, load_settings(tmp_path), "bad")
    assert not result["success"]
    assert not result["gx_success"]


def test_duplicate_doi_and_insufficient_rows_fail(tmp_path):
    frame = papers(4)
    frame.loc[1, "paper_id"] = frame.loc[0, "paper_id"]
    result = run_data_quality_checks(frame, load_settings(tmp_path), "bad")
    assert not result["gx_success"]


def test_missing_schema_and_empty_data_fail_without_crashing(tmp_path):
    settings = load_settings(tmp_path)
    for frame in [pd.DataFrame(), papers().drop(columns=["summary", "age_days"])]:
        result = run_data_quality_checks(frame, settings, "bad")
        assert not result["success"]
        assert not result["freshness"]["is_fresh"]


def test_freshness_boundary_and_explicit_output_path(tmp_path):
    frame = papers()
    frame.loc[:1, "age_days"] = 181
    frame.loc[2, "age_days"] = 180
    path = tmp_path / "custom" / "freshness.json"
    report = build_freshness_report(frame, load_settings(tmp_path), path)
    assert report["stale_rows"] == 2
    assert report["stale_ratio"] == 0.25
    assert report["is_fresh"]
    assert json.loads(path.read_text()) == report
    frame.loc[2, "age_days"] = 181
    result = run_data_quality_checks(frame, load_settings(tmp_path), "stale")
    assert result["gx_success"]
    assert not result["success"]
    assert not result["freshness"]["is_fresh"]


@pytest.mark.parametrize("age", [None, "invalid", -1, float("inf"), float("nan")])
def test_invalid_age_fails_closed(tmp_path, age):
    frame = papers()
    frame["age_days"] = frame["age_days"].astype(object)
    frame.loc[0, "age_days"] = age
    report = build_freshness_report(frame, load_settings(tmp_path), tmp_path / "fresh.json")
    assert not report["is_fresh"]
    assert report["invalid_age_rows"] == 1
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("frame", [pd.DataFrame(), papers().drop(columns="age_days")])
def test_freshness_empty_or_missing_age_fails_closed(tmp_path, frame):
    report = build_freshness_report(frame, load_settings(tmp_path), tmp_path / "fresh.json")
    assert not report["is_fresh"]
    assert report["total_rows"] == len(frame)
    assert report["invalid_age_rows"] == len(frame)
