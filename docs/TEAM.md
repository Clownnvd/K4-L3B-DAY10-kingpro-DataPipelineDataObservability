# Thông tin nhóm - Day 10 Data Pipeline & Data Observability

- **Tên nhóm:** kingpro
- **Lớp:** E403 - K4-L3B
- **Repository:** <https://github.com/Clownnvd/K4-L3B-DAY10-kingpro-DataPipelineDataObservability>
- **Ngày chạy nghiệm thu:** 26/09/2026

## Thành viên và phạm vi công việc

| Thành viên | MSSV | GitHub | Phạm vi | Trạng thái bằng chứng |
|---|---|---|---|---|
| Nguyễn Văn Duy | `2A202602729` | `Clownnvd` | Tích hợp ingestion, cleaning, quality gate, benchmark, corruption/repair, báo cáo và test end-to-end | Đã chạy và kiểm tra trên máy Duy; báo cáo cá nhân nằm trong `report/2A202602729_NguyenVanDuy.md` |
| Dương Thị Ngân | `2A2026022808` | `nganduong-123` | Kiểm tra độc lập quality gate trên baseline/corrupted/repaired; bổ sung test và ghi nhận phát hiện | Handoff đã chuẩn bị tại `handoff/ngan-quality-check`; đang chờ Ngân tự chạy và commit kết quả |

## Phân công theo checkpoint

| Checkpoint | Nội dung | Owner hiện tại | Bằng chứng |
|---|---|---|---|
| CP0 | Môi trường, Crossref ingestion và raw lineage | Nguyễn Văn Duy | `data/raw/`, `src/ingestion/crossref.py`, test ingestion |
| CP1 | Cleaning, Great Expectations và Freshness SLA | Nguyễn Văn Duy; Ngân kiểm tra độc lập | `src/ingestion/cleaning.py`, `src/observability/quality.py`, handoff Ngân |
| CP2 | Frozen test set, MiniLM và ChromaDB | Nguyễn Văn Duy | `data/eval/test_set.json`, `src/retrieval/` |
| CP3 | Baseline end-to-end | Nguyễn Văn Duy | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| CP4 | Sáu kịch bản corruption | Nguyễn Văn Duy | `src/ingestion/corruption.py`, `data/results/corruption_log.json` |
| CP5 | Idempotent repair và báo cáo ba trạng thái | Nguyễn Văn Duy | `repair_verification.json`, `corruption_report.md` |
| CP6 | Review nhóm và nộp cá nhân | Nguyễn Văn Duy nộp link; Ngân tự commit và tự nộp | Git history và VLearn của từng người |

## Tỷ lệ đóng góp có thể đối chiếu tại thời điểm hiện tại

| Thành viên | Tỷ lệ đã có bằng chứng commit | Ghi chú |
|---|---:|---|
| Nguyễn Văn Duy | 100% phần đang có trên nhánh `main` | Sẽ được ghi bằng commit tích hợp Day10 |
| Dương Thị Ngân | 0% - đang chờ commit cá nhân | Không nhận thay phần chưa do Ngân tự chạy và commit |

Tỷ lệ trên là trạng thái bằng chứng tại thời điểm nộp link của Duy, không phải phân bổ cuối cùng. Sau khi Ngân hoàn thành handoff, bảng phải được cập nhật theo commit thực tế.

## Lệnh nghiệm thu chung

```powershell
$env:RUN_DATE = "2026-09-26"
$env:LLM_PROVIDER = "mock"
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

Kết quả chạy lại ngày 26/09/2026: Phase 1 exit code 0, Corruption/Repair exit code 0 và `53 passed`.
