# Baseline run

Generated from this run's artifacts.

## Source and provenance

```json
{
  "run_date": "2026-09-26",
  "rows": 24,
  "raw_response_sha256": "84f0b4b240e016dc6adc52e2c471eb7641fb5fa5612752fd35260d822a7d5676",
  "raw_records_sha256": "a466d924be97b0ba05829a5264fab18dc92fd5228f45827a646dfb76c4b0f80c",
  "clean_sha256": "0863384f3875ae704419bc0374a2bdc9d6633a9981e5cd8610b54301fe61dae4",
  "test_set_sha256": "d389216cdbc9262ad98587bd9decea8ab1b3bb02babf9a311448023aa749f73a",
  "baseline_metrics_sha256": "44fe2ed0183e2585a570526ae32c770b9ad0bee306d1b86021efd574618c8fa8",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "provider": "mock",
  "evaluation_config": {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "top_k": 4,
    "provider": "mock",
    "model_name": "gemini-2.5-flash",
    "llm_judge": false,
    "ragas": false,
    "answer_mode": "extractive_metadata",
    "retrieval_mode": "exact_title_assisted_semantic_search"
  }
}
```

## Measured results

| Metric | Value |
|---|---:|
| retrieval_hit_rate | 1.000000 |
| mean_token_f1 | 1.000000 |
| judge_accuracy | 1.000000 |
| mean_judge_score | 5.000000 |

Quality gate: **True**; GX suite: **True**.
Freshness: **True**; stale 0/24.

## Interpretation and limits

Retrieval hit rate = questions with at least one correct DOI retrieved / all questions.
Token F1 compares whitespace-separated, case-folded token counts; repeated words count.
QA evaluation extracts retrieved metadata. Exact-title lookup assists semantic search.
The default judge uses token overlap, not independent LLM reasoning.
These title-addressed questions do not establish general open-ended reasoning quality.
All 24 source records lack subject categories; category questions test explicit missing-data responses.
No category labels were fabricated.

Answer mode: `extractive_metadata`. Judge mode: `token_overlap_heuristic`.
Optional Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`.
