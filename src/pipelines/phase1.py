from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from core.config import load_settings, normalized_provider
from core.utils import read_json, write_csv, write_json
from ingestion.crossref import fetch_source_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluation_config(settings):
    return {"embedding_model": settings.embedding_model, "top_k": settings.top_k,
            "provider": normalized_provider(settings), "model_name": settings.model_name,
            "llm_judge": os.getenv("RUN_LLM_JUDGE", "").lower() in {"1", "true", "yes"},
            "ragas": os.getenv("RUN_RAGAS", "").lower() in {"1", "true", "yes"},
            "answer_mode": "extractive_metadata", "retrieval_mode": "exact_title_assisted_semantic_search"}


def run_phase1_pipeline(settings):
    run_date = datetime.fromisoformat(os.environ["RUN_DATE"]) if os.getenv("RUN_DATE") else datetime.now(UTC)
    records = fetch_source_records(settings)
    df = build_clean_dataframe(records, run_date)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    write_json(settings.paths.clean_json.with_name("cleaning_report.json"), df.attrs["cleaning_report"])
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline failed the quality gate; indexing blocked. See data/quality/.")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)
    questions = read_json(settings.paths.eval_testset)
    if len(questions) != 10 or {q["question_type"] for q in questions} != {"summary", "authors", "date", "categories"}:
        raise ValueError("Expected 10 frozen questions covering four types")
    ids = set(df.paper_id)
    if any(not set(q["ground_truth_doc_ids"]).issubset(ids) for q in questions):
        raise ValueError("Frozen test set belongs to another corpus; explicitly refresh it")
    index = LocalEmbeddingIndex.build(df, settings)
    bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset,
                               settings.paths.baseline_metrics, settings.paths.baseline_answers)
    agent = build_agent(settings, index)
    demo = [{"question": questions[0]["question"], "answer": run_agent_question(agent, questions[0]["question"]),
             "provider": normalized_provider(settings)}]
    write_json(settings.paths.demo_answers, demo)
    manifest = {
        "run_date": df.attrs["cleaning_report"]["run_date_utc"], "rows": len(df),
        "raw_response_sha256": file_hash(settings.paths.raw_api_response),
        "raw_records_sha256": file_hash(settings.paths.raw_records_json),
        "clean_sha256": file_hash(settings.paths.clean_json),
        "test_set_sha256": file_hash(settings.paths.eval_testset),
        "baseline_metrics_sha256": file_hash(settings.paths.baseline_metrics),
        "embedding_model": settings.embedding_model, "provider": normalized_provider(settings),
        "evaluation_config": evaluation_config(settings),
    }
    write_json(settings.paths.baseline_metrics.with_name("run_manifest.json"), manifest)
    generate_phase1_report(settings.paths.baseline_report, manifest, bundle.summary, quality, freshness)
    print(json.dumps({"stage": "baseline", "rows": len(df), "quality": quality["success"], **bundle.summary}, indent=2))
    return {"metrics": bundle.summary, "quality": quality, "manifest": manifest}


def main():
    run_phase1_pipeline(load_settings())


if __name__ == "__main__":
    main()
