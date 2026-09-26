import json

import pytest

from run_checks import run_experiment


def write_datasets(folder, *, break_baseline=False):
    folder.mkdir()
    clean = [dict(paper_id=f"10.1234/{i}", title="Research paper",
                  summary="A sufficiently long abstract explaining a concrete research result.",
                  text_for_embedding="A sufficiently long research text.",
                  published="2026-09-01", age_days=25, categories_joined="") for i in range(8)]
    corrupt = [dict(row) for row in clean]
    corrupt[0]["summary"] = ""
    for state, rows in {"baseline": corrupt if break_baseline else clean,
                        "corrupted": corrupt, "repaired": clean}.items():
        (folder / f"{state}.json").write_text(json.dumps(rows), encoding="utf-8")


def test_three_real_checks_write_report_with_expected_outcomes(tmp_path):
    write_datasets(tmp_path / "data")
    report = run_experiment(tmp_path / "data", tmp_path / "outputs")
    assert report["expectations_met"] is True
    assert {name: item["success"] for name, item in report["states"].items()} == {
        "baseline": True, "corrupted": False, "repaired": True}
    assert report["states"]["baseline"]["missing_category_rows"] == 8
    assert len(report["states"]["baseline"]["input_sha256"]) == 64
    assert json.loads((tmp_path / "outputs/report.json").read_text()) == report
    assert (tmp_path / "outputs/SUMMARY.md").exists()


def test_unexpected_gate_result_is_recorded_before_failure(tmp_path):
    write_datasets(tmp_path / "data", break_baseline=True)
    with pytest.raises(RuntimeError, match="expected"):
        run_experiment(tmp_path / "data", tmp_path / "outputs")
    assert json.loads((tmp_path / "outputs/report.json").read_text())["expectations_met"] is False


def test_missing_input_produces_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="baseline.json"):
        run_experiment(tmp_path / "missing", tmp_path / "outputs")
