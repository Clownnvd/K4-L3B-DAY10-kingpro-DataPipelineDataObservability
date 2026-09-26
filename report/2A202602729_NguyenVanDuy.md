# Báo cáo cá nhân - Nguyễn Văn Duy

## 1. Thông tin

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Văn Duy |
| MSSV | `2A202602729` |
| Khóa/Lớp | K4 - E403 - L3B |
| Nhóm | kingpro |
| Vai trò | Tích hợp Data Pipeline, Observability, Evaluation và Repair |
| Repository | <https://github.com/Clownnvd/K4-L3B-DAY10-kingpro-DataPipelineDataObservability> |
| Ngày hoàn thành | 26/09/2026 |

## 2. Phạm vi trực tiếp thực hiện

| Phần việc | File/hàm chính | Input | Output |
|---|---|---|---|
| Crossref ingestion và lineage | `src/ingestion/crossref.py` | API hoặc snapshot | Hai raw JSON, 24 records |
| Cleaning và pre-embed model | `src/ingestion/cleaning.py` | Raw records | CSV/JSON sạch, cleaning report |
| Quality gate và freshness | `src/observability/quality.py` | DataFrame sạch/lỗi | GX report và freshness report |
| Frozen benchmark | `src/evaluation/testset.py` | 24 records sạch | 10 câu hỏi có ground-truth IDs |
| Retrieval và QA | `src/retrieval/` | Clean/corrupted/repaired data | Chroma collections và answer artifacts |
| Corruption và repair | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Baseline + frozen test set | Ba bộ metrics và integrity checks |
| Tích hợp, báo cáo và test | `script/`, `tests/`, `report/group_report.md` | Toàn pipeline | Lệnh chạy, test và báo cáo |

## 3. Kết quả có thể đối chiếu

- Raw response SHA-256: `84f0b4b240e016dc6adc52e2c471eb7641fb5fa5612752fd35260d822a7d5676`.
- Baseline: 24 dòng, gate đạt, hit rate 1,0, Token F1 1,0.
- Corrupted: 21 dòng, gate không đạt, hit rate 0,7, Token F1 0,6125.
- Repaired: 24 dòng, gate đạt, hit rate 1,0, Token F1 1,0.
- Năm integrity checks trong `repair_verification.json` đều đúng.
- Chạy lại trước khi nộp: `53 passed`.

## 4. Giải thích kỹ thuật

### Vấn đề

Một RAG agent có thể tiếp tục trả lời khi nguồn bị thiếu, trùng hoặc nhiễu, nhưng kết quả sẽ kém mà người vận hành không biết. Phần của tôi đặt quality gate trước indexing, tạo corruption có kiểm soát để đo hậu quả và dùng raw snapshot bất biến để phục hồi.

### Cách triển khai

Pipeline tải hoặc đọc snapshot Crossref, giữ raw bytes, chuẩn hóa 24 records, tính `age_days`, tạo `text_for_embedding`, chạy Great Expectations và Freshness SLA. Chỉ dữ liệu sạch đi vào baseline index. Pha corruption cố ý đưa dữ liệu lỗi vào collection tách biệt để đo suy giảm. Khi gate thất bại, repair dựng lại từ raw records với cùng run date và frozen test set.

### Contract

| Thành phần | Nội dung |
|---|---|
| Input | Raw Crossref response, `RUN_DATE`, cấu hình quality/freshness |
| Output | Clean data, quality reports, embeddings, answers, metrics, reports |
| Điều kiện chặn | ID rỗng/trùng, summary thiếu hoặc ngắn, schema thiếu, freshness vượt ngưỡng |
| Tính bất biến | Không sửa raw artifacts và không đổi test set giữa ba trạng thái |

## 5. Quyết định kỹ thuật quan trọng

- **Phương án cân nhắc:** gọi API live mỗi lần hoặc khóa snapshot; dùng câu hỏi mới cho mỗi trạng thái hoặc giữ cùng test set.
- **Phương án chọn:** giữ raw snapshot và frozen test set, đồng thời khóa ngày thí nghiệm.
- **Lý do:** ba trạng thái chỉ khác chất lượng dữ liệu; so sánh không bị nhiễu bởi nguồn, câu hỏi hoặc thời gian thay đổi.
- **Bằng chứng:** repaired data khớp baseline, test set giữ nguyên và metrics trở lại mức baseline.

## 6. Lỗi đã xử lý

- **Triệu chứng:** một test summary kỳ vọng toàn bộ abstract trong khi contract của bài yêu cầu câu đầu tiên.
- **Nguyên nhân:** test và implementation hiểu khác nhau về đáp án summary.
- **Xử lý:** sửa test theo contract được dùng chung trong pipeline, không sửa artifact metrics bằng tay.
- **Xác minh:** toàn bộ `53 passed`; Phase 1 và Corruption/Repair đều exit code 0.

## 7. Hiểu luồng end-to-end

1. Crossref được lưu thành raw response và records; cleaning tạo text năm phần rồi MiniLM sinh vector cho ChromaDB.
2. Frozen test set giữ câu hỏi, đáp án và ground-truth DOI; retrieval hit rate đo có DOI đúng trong kết quả, Token F1 đo mức trùng từ của câu trả lời.
3. Quality check kiểm tra schema/nội dung tại một lần chạy; freshness đo độ cũ theo `age_days` và SLA.
4. Cùng test set giúp thay đổi metric phản ánh thay đổi dữ liệu, không phải thay đổi câu hỏi.
5. Repair thành công khi dữ liệu khớp baseline, gate đạt lại, raw/test set không đổi và metrics phục hồi.

## 8. Phân tích số liệu

| Metric | Baseline | Corrupted | Repaired | Nhận xét |
|---|---:|---:|---:|---|
| Retrieval hit rate | 1,0 | 0,7 | 1,0 | Mất/noise metadata làm 3/10 câu không còn đúng nguồn |
| Mean Token F1 | 1,0 | 0,6125 | 1,0 | Summary/title lỗi làm câu trả lời thiếu hoặc sai từ |
| Judge accuracy | 1,0 | 0,6 | 1,0 | Heuristic judge phản ánh cùng xu hướng suy giảm |
| Quality gate | Đạt | Không đạt | Đạt | Gate bắt DOI trùng và summary rỗng |
| Freshness | Đạt | Đạt | Đạt | 4/21 stale chưa vượt ngưỡng 25% |

Chuỗi nguyên nhân: corruption làm mất 5 tài liệu, rỗng summary, nhiễu text, cắt title, làm cũ ngày và trùng DOI → quality gate thất bại và metrics giảm → repair từ raw snapshot → dữ liệu, gate và metrics trở lại baseline.

## 9. Điều học được

1. Raw lineage và frozen evaluation là điều kiện để so sánh có ý nghĩa.
2. Data quality không thể thay bằng một metric freshness đơn lẻ.
3. Agent vẫn có thể chạy khi dữ liệu lỗi, nên phải chặn trước indexing và đo ảnh hưởng sau retrieval.

Nếu có thêm thời gian, tôi sẽ bổ sung dashboard drift và CI coverage report, sau đó đo semantic retrieval riêng không dùng exact-title assistance.

## 10. Xác nhận cá nhân

- [x] Báo cáo phản ánh phần việc đã chạy và có artifact đối chiếu.
- [x] Có thể giải thích luồng end-to-end.
- [x] Không nhận ownership thay phần Ngân chưa tự thực hiện.
- [x] Không chứa `.env`, API key, token hoặc secret.
- [x] Không sao chép nguyên báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Duy  
**Ngày xác nhận:** 26/09/2026
