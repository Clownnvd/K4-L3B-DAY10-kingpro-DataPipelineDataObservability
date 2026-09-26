# Day 10 task checklist

Current execution scope: publish the verified group repository and submit Nguyễn Văn Duy's VLearn link. The earlier LOCAL ONLY restriction was explicitly replaced by the user's publication/submission request. Keep Dương Thị Ngân's contribution pending until she runs the handoff and commits her own evidence.

## Progress

- [x] 1. Fetch 24 Crossref records and preserve the source response.
  - Live API request succeeded; no offline fallback was used.
  - 24 records and 24 distinct DOI identifiers.
  - `data/raw/crossref_response.json`: 160215 bytes, original response bytes.
  - SHA-256: `84f0b4b240e016dc6adc52e2c471eb7641fb5fa5612752fd35260d822a7d5676`.
  - `data/raw/crossref_records.json`: extracted records, verified by loading them back.
- [x] 2. Clean records, remove duplicates, calculate age, prepare embedding text.
  - `data/clean/papers_clean.csv` and `papers_clean.json`: 24 rows, 16 columns.
  - `data/clean/cleaning_report.json`: no invalid or duplicate records removed.
  - Source category metadata is absent in all 24 rows; preserved as empty, not invented.
  - Publication ages: 11-178 days as of 2026-09-26 UTC.
  - Both raw file hashes remained unchanged; repeated cleaning produced identical files.
- [x] 3. Implement Great Expectations checks and freshness monitoring.
- [x] 4. Build 10 evaluation questions, index documents, run baseline evaluation.
- [x] 5. Implement six corruption cases and measure degraded performance.
- [x] 6. Repair from the preserved snapshot and compare baseline/corrupted/repaired results.
- [x] 7. Complete the technical report and prepare an independently runnable quality-check package for Ngân.
  - Team: Nguyễn Văn Duy and Dương Thị Ngân.
  - Duy's verified work is recorded; Ngân remains pending her own run and commit.

## Environment and handoff status

This directory is a local clone of the instructor starter, not a published team fork.
Team membership, collaborators and contributor configuration have not been changed.
The full locked .venv is installed and verified. Both phases ran with real MiniLM embeddings and ChromaDB.
Local mock/extractive QA requires no paid API key. Live provider calls and optional external judges were not exercised.

Deadline conflict: the VLearn technical guide states 13:00 morning / 18:00 afternoon;
the instructor repository README and checkpoint document state 23:59:59 on
2026-09-26. Verify the class announcement before choosing a submission deadline.

## Verification receipt

Command (PowerShell, from this directory):

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests/test_crossref.py -q --tb=short
```

Result: 7 passed. Covers parsing, exact response preservation, record round-trip,
cached reads without a network call, retry after HTTP 429, fallback after network
or unusable-response failures, and failure when neither network nor snapshot works.

Observed development checks: the initial test harness patched an import absent in
the starter; corrected mocks to patch requests/time directly. All 7 checks then
failed against the unimplemented student stubs before implementation and passed
after implementation.

To reuse the preserved snapshot (default unless REFRESH_SOURCE is enabled):

```powershell
$env:PYTHONPATH = 'src'
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; print(len(fetch_source_records(load_settings())))"
```

## Step 2 verification receipt

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests -q --tb=short
python script/run_cleaning.py --run-date 2026-09-26
```

Result: 16 tests passed (7 ingestion + 9 cleaning cases). The 9 new cases first
failed with the original cleaning stub's `NotImplementedError`, then passed after
implementation. They cover whitespace normalization and source immutability,
case-insensitive DOI deduplication, newest-first ordering, missing identifiers,
missing titles, impossible/empty publication dates, missing optional metadata,
empty input schema, UTC date handling and unclamped future publication ages.

Independent artifact checks passed: CSV and JSON contain the same 24 IDs and
embedding text; summary lengths match actual text; both source hashes remain
unchanged; two runs with the same date produce identical output hashes.

Cleaning treats missing summaries and categories as quality observations, leaving
their acceptance to step 3. It rejects missing IDs/titles and unparseable publication
dates with reasons in the report. For duplicate DOI values, the first valid source
occurrence wins. Short summaries and negative ages are not silently repaired.

Full pipeline validation subsequently passed; see the completion receipt below.

## Current full-lab run

- Environment: uv sync --extra dev succeeded after transient DNS failure; locked GX1.18.0, Chroma1.5.9, sentence-transformers5.5.1.
- Baseline command: .venv/Scripts/python.exe script/run_phase1.py exited 0; 24 rows, gate true, 10 questions, hit rate1.0, token F1 1.0.
- Initial full regression: 52 passed,1 failed; summary test expected entire abstract instead of first sentence required by VLearn. Correcting the test contract.

- Corruption and repair command exited0: hit rate1.0 ->0.7 ->1.0; token F1 1.0 ->0.6125 ->1.0; all raw/frozen-testset/repair invariants true.

## Local completion receipt

- `uv sync --extra dev`: PASS after transient registry DNS errors. A separate optional handoff-lock attempt failed offline and was stopped after slow online retries; the handoff pins tested direct dependency versions instead.
- `.venv/Scripts/python.exe -m pytest tests -q --tb=short`: 53 passed.
- `.venv/Scripts/python.exe script/run_phase1.py`: exit 0.
- `.venv/Scripts/python.exe script/run_corruption_flow.py`: exit 0.
- `.venv/Scripts/python.exe script/export_local_report.py`: exit 0.
- Baseline/corrupted/repaired: 24/21/24 rows; hit rate 1.0/0.7/1.0; token F1 1.0/0.6125/1.0; gates true/false/true.
- `data/results/repair_verification.json`: all five boolean integrity checks true.
- Handoff: `handoff/ngan-quality-check` with 22 standalone tests, exact quality module copy and all three real JSON datasets. Package copy in Downloads: `Day10-Ngan-Quality-Check.zip`.
- Generated reports accurately label extractive answers, exact-title assistance, heuristic judging and absent source categories.
- README includes uv/pip environment instructions and the exact two phase commands.
- No GitHub publication, collaborator invites, external messages or VLearn submission were performed.

Human follow-up outside the completed local preparation: Ng?n runs the package on her own machine and records actual results; participants confirm their own IDs and contribution reports; classroom demonstration and later submission remain human/course activities. Prepared files do not prove those activities occurred.

ZIP independently extracted and verified: portable imports, run_checks exit0, 22 tests passed; no environment/secrets/generated reports packaged.
