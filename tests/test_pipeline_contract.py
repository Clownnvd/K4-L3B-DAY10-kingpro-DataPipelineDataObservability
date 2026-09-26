from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest
from core.config import load_settings, normalized_provider
from core.utils import read_json, write_json
from pipelines.phase1 import run_phase1_pipeline, evaluation_config
from pipelines.corruption_flow import repair_from_raw_snapshot, run_corruption_flow_pipeline


def test_invalid_baseline_is_blocked_before_indexing(tmp_path):
    settings = replace(load_settings(tmp_path), llm_provider="mock")
    with patch("pipelines.phase1.fetch_source_records", return_value=[]), \
         patch("pipelines.phase1.LocalEmbeddingIndex.build") as build:
        with pytest.raises(RuntimeError, match="quality gate"):
            run_phase1_pipeline(settings)
        build.assert_not_called()


def test_repair_reads_raw_and_is_repeatable(tmp_path):
    settings = load_settings(tmp_path)
    source = Path(__file__).resolve().parents[1] / "data/raw/crossref_records.json"
    raw = read_json(source)
    write_json(settings.paths.raw_records_json, raw)
    first = repair_from_raw_snapshot(settings, datetime(2026, 9, 26))
    second = repair_from_raw_snapshot(settings, datetime(2026, 9, 26))
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 24
    assert read_json(settings.paths.raw_records_json) == raw


def test_changed_baseline_artifact_rejects_comparison(tmp_path):
    settings = load_settings(tmp_path)
    write_json(settings.paths.baseline_metrics.with_name("run_manifest.json"), {"raw_response_sha256": "not-the-current-hash", "evaluation_config": evaluation_config(settings)})
    write_json(settings.paths.raw_api_response, {})
    with pytest.raises(RuntimeError, match="artifact changed"):
        run_corruption_flow_pipeline(settings)


@pytest.mark.parametrize("provider, expected", [("mock", "mock"), ("google", "gemini"), ("openai", "openai"), ("anthropic", "anthropic")])
def test_provider_aliases(provider, expected, tmp_path):
    assert normalized_provider(replace(load_settings(tmp_path), llm_provider=provider)) == expected


def test_changed_search_config_rejects_comparison(tmp_path):
    settings = load_settings(tmp_path)
    write_json(settings.paths.baseline_metrics.with_name("run_manifest.json"), {"evaluation_config": evaluation_config(settings)})
    with pytest.raises(RuntimeError, match="configuration changed"):
        run_corruption_flow_pipeline(replace(settings, top_k=settings.top_k + 1))


def test_index_rejects_wrong_query_embedding_model(tmp_path):
    from retrieval.index import LocalEmbeddingIndex
    settings = load_settings(tmp_path)
    write_json(settings.paths.embeddings_json, {"embedding_model": "other-model"})
    with pytest.raises(ValueError, match="Embedding model differs"):
        LocalEmbeddingIndex.load(settings)
