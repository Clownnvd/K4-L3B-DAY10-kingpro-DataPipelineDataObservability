from __future__ import annotations

from datetime import datetime
import json
import pandas as pd
from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
from pipelines.phase1 import file_hash, evaluation_config


def repair_from_raw_snapshot(settings, run_date):
    """Reconstruct clean data using the immutable source and original clock."""
    return build_clean_dataframe(load_raw_records(settings.paths.raw_records_json), run_date)


def run_corruption_flow_pipeline(settings):
    p = settings.paths
    manifest = read_json(p.baseline_metrics.with_name("run_manifest.json"))
    if manifest.get("evaluation_config") != evaluation_config(settings):
        raise RuntimeError("Evaluation configuration changed; rerun baseline before comparison")
    for path, key in [(p.raw_api_response, "raw_response_sha256"), (p.raw_records_json, "raw_records_sha256"),
                      (p.clean_json, "clean_sha256"), (p.eval_testset, "test_set_sha256"),
                      (p.baseline_metrics, "baseline_metrics_sha256")]:
        if file_hash(path) != manifest[key]:
            raise RuntimeError(f"Baseline artifact changed: {path.name}. Rerun Phase 1.")
    baseline = read_json(p.baseline_metrics)
    clean = pd.DataFrame(read_json(p.clean_json))
    corrupted = corrupt_clean_dataframe(clean, p.corruption_log)
    write_csv(corrupted, p.corrupted_clean_csv)
    write_json(p.corrupted_clean_json, corrupted.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted, settings, p.quality_dir / "corrupted_freshness_report.json")
    # Invalid data is isolated solely for this controlled lab experiment.
    bad_index = LocalEmbeddingIndex.build(corrupted, settings, p.corrupted_embeddings_json)
    damaged = evaluate_pipeline(settings, bad_index, p.eval_testset, p.corrupted_metrics, p.corrupted_answers)
    if corrupted_quality["success"]:
        raise RuntimeError("Corruption did not trigger the gate; inspect experiment")
    repaired = repair_from_raw_snapshot(settings, datetime.fromisoformat(manifest["run_date"]))
    repeated = repair_from_raw_snapshot(settings, datetime.fromisoformat(manifest["run_date"]))
    pd.testing.assert_frame_equal(repaired, repeated)
    if repaired.to_dict(orient="records") != clean.to_dict(orient="records"):
        raise RuntimeError("Repair differs from frozen baseline records")
    repaired_quality = run_data_quality_checks(repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired, settings, p.quality_dir / "repaired_freshness_report.json")
    if not repaired_quality["success"]:
        raise RuntimeError("Repaired data failed validation; promotion blocked")
    write_csv(repaired, p.repaired_clean_csv)
    write_json(p.repaired_clean_json, repaired.to_dict(orient="records"))
    good_index = LocalEmbeddingIndex.build(repaired, settings, p.repaired_embeddings_json)
    recovered = evaluate_pipeline(settings, good_index, p.eval_testset, p.repaired_metrics, p.repaired_answers)
    generate_corruption_report(p.comparison_report, baseline, damaged.summary, recovered.summary,
                               corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness)
    verification = {"raw_unchanged": file_hash(p.raw_records_json) == manifest["raw_records_sha256"],
                    "raw_response_unchanged": file_hash(p.raw_api_response) == manifest["raw_response_sha256"],
                    "test_set_unchanged": file_hash(p.eval_testset) == manifest["test_set_sha256"],
                    "repair_identical_to_baseline": True, "repair_idempotent": True,
                    "auto_repair_trigger": "failed_quality_gate", "quality_after_repair": repaired_quality["success"]}
    if not all(v for v in verification.values() if isinstance(v, bool)):
        raise RuntimeError("Experiment invariant failed")
    write_json(p.repaired_metrics.with_name("repair_verification.json"), verification)
    result = {"baseline": baseline, "corrupted": damaged.summary, "repaired": recovered.summary,
              "verification": verification}
    print(json.dumps(result, indent=2))
    return result


def main():
    run_corruption_flow_pipeline(load_settings())


if __name__ == "__main__":
    main()
