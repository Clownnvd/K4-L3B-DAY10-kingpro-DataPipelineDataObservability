# Báo cáo nhóm kingpro - Day 10 Data Pipeline & Data Observability

## 1. Mục tiêu

Nhóm xây dựng một pipeline dữ liệu có thể tái hiện cho RAG: thu thập 24 bài báo Crossref, giữ raw lineage, làm sạch, kiểm tra chất lượng, tạo embedding MiniLM, index ChromaDB, đánh giá trên bộ 10 câu hỏi cố định, chủ động tiêm lỗi rồi phục hồi từ dữ liệu gốc.

## 2. Luồng thực thi

```text
Crossref API / local snapshot
→ raw response + normalized records
→ cleaning + age_days + text_for_embedding
→ Great Expectations + Freshness SLA
→ frozen benchmark 10 câu
→ MiniLM embeddings + ChromaDB
→ baseline evaluation
→ six corruption operations
→ corrupted evaluation
→ rebuild from raw snapshot
→ repaired evaluation + integrity verification
```

## 3. Dữ liệu và provenance

- Raw source: 24 records, 24 DOI riêng biệt.
- `crossref_response.json` giữ phản hồi nguồn; SHA-256: `84f0b4b240e016dc6adc52e2c471eb7641fb5fa5612752fd35260d822a7d5676`.
- Cleaning giữ 24/24 dòng, không loại bản ghi lỗi hoặc trùng.
- Cả 24 bản ghi thiếu category từ nguồn; pipeline giữ trạng thái thiếu thay vì tự tạo metadata.
- Ngày thí nghiệm được khóa tại `2026-09-26` để `age_days` có thể tái hiện.

## 4. Quality gate

Great Expectations 1.18.0 kiểm tra:

1. Số dòng từ 5 đến 5.000.
2. `paper_id` không rỗng và không trùng.
3. `title` không rỗng.
4. `summary` không rỗng và dài tối thiểu 30 ký tự.
5. `text_for_embedding` không rỗng.

Freshness SLA đánh dấu stale khi `age_days > 180`; ngưỡng cho phép tối đa 25% dòng stale.

## 5. Corruption suite

| Operation | Số ID bị tác động | Mục đích |
|---|---:|---|
| `drop_newest` | 5 | Mô phỏng mất các tài liệu mới nhất |
| `blank_summary` | 4 | Mô phỏng thiếu nội dung bắt buộc |
| `inject_noise` | 4 | Mô phỏng text bị nhiễu |
| `truncate_title` | 4 | Mô phỏng tiêu đề mất thông tin |
| `stale_date` | 4 | Mô phỏng dữ liệu cũ |
| `duplicate_rows` | 2 | Mô phỏng DOI bị trùng |

Corruption được chọn theo thứ tự thời gian và DOI, không đọc đáp án benchmark để chọn mục tiêu.

## 6. Kết quả ba trạng thái

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Số dòng | 24 | 21 | 24 |
| Quality gate | Đạt | Không đạt | Đạt |
| Retrieval hit rate | 1,0000 | 0,7000 | 1,0000 |
| Mean Token F1 | 1,0000 | 0,6125 | 1,0000 |
| Judge accuracy | 1,0000 | 0,6000 | 1,0000 |
| Mean judge score | 5,0 | 3,4 | 5,0 |

Quality gate của dữ liệu corrupted phát hiện DOI trùng và 6 summary rỗng. Freshness riêng vẫn đạt vì 4/21 dòng stale tương đương 19,05%, thấp hơn ngưỡng 25%; điều này cho thấy một tín hiệu riêng lẻ không thay thế quality gate tổng hợp.

## 7. Xác minh phục hồi

`repair_verification.json` xác nhận:

- Raw records không đổi.
- Raw response không đổi.
- Frozen test set không đổi.
- Repaired data giống baseline.
- Repair chạy lặp lại vẫn cho cùng kết quả.
- Cơ chế repair được kích hoạt bởi quality gate thất bại.

## 8. Giới hạn

- Chế độ chuẩn dùng `LLM_PROVIDER=mock`; câu trả lời được trích xuất từ metadata, không chứng minh năng lực suy luận của LLM thương mại.
- Retrieval có exact-title assistance bên cạnh semantic search nên hit rate không phải điểm của vector search thuần túy.
- Nguồn không có category cho 24/24 bài; hai câu hỏi category kiểm tra cách xử lý dữ liệu thiếu.
- Ragas và external LLM judge không chạy trong nghiệm thu chuẩn để giữ khả năng tái hiện và không phát sinh chi phí.
- ChromaDB được sinh lại local và không commit thư mục database.

## 9. Cách tái hiện

```powershell
uv sync --extra dev --locked
$env:RUN_DATE = "2026-09-26"
$env:LLM_PROVIDER = "mock"
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python -m pytest tests -q
```

Kết quả chạy lại trước khi nộp: hai pipeline exit code 0, `53 passed`.

## 10. Phân công và liêm chính

Phân công và trạng thái commit được ghi tại `docs/TEAM.md`. Báo cáo không nhận thay phần của thành viên chưa tự chạy hoặc chưa có commit. Không có API key, token hoặc `.env` trong bài nộp.
