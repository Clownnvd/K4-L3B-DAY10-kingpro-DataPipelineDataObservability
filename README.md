# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Hình thức:** Teamwork | **Thời lượng:** 240 phút  
> **Lịch học (Lớp B - Ca Sáng):** Thứ 7 (26/09/2026) 09:00 – 13:00  
> ⏰ **Hạn nộp LMS:** 23:59:59 cùng ngày

---

## 🧭 Đọc gì, theo thứ tự nào?

| # | Tài liệu | Mô tả |
|:---:|---|---|
| 1️⃣ | **Codelab trên VLearn LMS** | Hướng dẫn từng bước + nộp bài (mở trên trình duyệt) |
| 2️⃣ | [CHECKPOINTS.md](docs/CHECKPOINTS.md) | Phân bổ thời gian 240 phút & deliverables từng mốc |
| 3️⃣ | [RUBRIC.md](docs/RUBRIC.md) | Tiêu chí chấm điểm (100 chuẩn + 10 bonus) |
| 4️⃣ | [SUBMISSION.md](docs/SUBMISSION.md) | Nội quy, deadline, bảo mật & checklist nộp bài |
| 5️⃣ | [TEAM.md](docs/TEAM.md) | Điền thông tin nhóm & báo cáo cá nhân |

---

## Repo có sẵn gì? (Scaffolded Baseline)

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Khung pipeline thu thập, embedding MiniLM, đánh giá metrics (có `TODO(student)`)
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Học viên cần làm gì?

1. Hoàn thiện **Data Quality Gate** (Great Expectations 1.x) trong `src/observability/quality.py`
2. Tích hợp **Freshness Check** (`age_days`) vào Quality Gate
3. Chạy **Baseline → Corruption → Repair** → xuất bảng đối chiếu 3 trạng thái
4. **Live Demo** trên bảng & nộp link repo lên VLearn LMS


## Run the completed local implementation

Python 3.11?3.13; install the locked environment from the project root:

```powershell
uv sync --extra dev --locked
Copy-Item .env.example .env
```

Do not overwrite an existing `.env`. Default `LLM_PROVIDER=mock` runs a local,
deterministic metadata-answering agent without a paid API. ChromaDB and the
`sentence-transformers/all-MiniLM-L6-v2` embeddings are real. First use may download
the public model; subsequent runs reuse its local cache.

Reproduce the lab at its original date, keeping the provided Crossref snapshot:

```powershell
$env:RUN_DATE = '2026-09-26'
$env:LLM_PROVIDER = 'mock'
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python -m pytest tests -q
```

On macOS/Linux use `RUN_DATE=2026-09-26 LLM_PROVIDER=mock uv run ...`, or put these
non-secret values in `.env`. From an activated `.venv`, replace `uv run python`
with `python`. Package installation exposes `src/` correctly without absolute paths.

Read `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, and
`data/results/repair_verification.json`. Per-question answers are in
`data/results/*_answers.json`; check these before drawing conclusions from averages.
Both successful and failed command executions append to
`data/results/execution_log.jsonl`.

### Experiment contract

- The baseline validates data before indexing. Phase 2 deliberately indexes invalid
  rows into an isolated corrupted collection to measure the damage.
- Ten questions and their answers are frozen from the clean source and shared by
  all three states. Corruption is chosen by chronology, not by the answer key.
- Repair rebuilds from raw records with the original evaluation date. Repeating
  repair must produce the same rows. Hashes reject modified experiment inputs.
- Source categories are missing for all 24 fetched papers. No categories are
  invented: two questions explicitly test missing-metadata handling.
- Standard metrics use deterministic field extraction and a token-overlap judge.
  This is an experiment about data quality, not a claim about an LLM's reasoning.
- The helper uses exact-title lookup together with semantic retrieval. Reported hit
  rate measures this combined path; it is not a pure semantic-search benchmark.
- Real providers are available via `LLM_PROVIDER=gemini` (alias `google`), `openai`,
  `anthropic`, `openrouter`, `ollama` or `custom`. Set the corresponding private key
  and model in `.env`. Never commit it. The optional demo calls the selected provider;
  standard evaluation remains extractive so comparisons stay reproducible.
- `RUN_LLM_JUDGE=1` opts into external judging. `RUN_RAGAS=1` enables the optional
  external Ragas pass. Those modes can consume API credits and are not required.

### Delivery status

`TASKS.md` tracks actual completion. Team identity and individual contribution
statements must be confirmed by the participants. The browser demo, team publication
and each person's VLearn submission are separate actions; generated reports do not
prove that those actions occurred. Chroma storage is generated locally and excluded
from Git; regenerate all three collections using the commands above.
