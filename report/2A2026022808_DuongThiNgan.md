# Báo cáo cá nhân - Dương Thị Ngân

## 1. Thông tin

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Dương Thị Ngân |
| MSSV | `2A2026022808` |
| Khóa/Lớp | K4 - E403 - L3B |
| Nhóm | kingpro |
| Vai trò | Kiểm tra độc lập Quality Gate và Freshness SLA |
| Repository | <https://github.com/Clownnvd/K4-L3B-DAY10-kingpro-DataPipelineDataObservability> |
| Nhánh cá nhân | `ngan/quality-check` |
| Ngày hoàn thành | 26/09/2026 |

## 2. Phạm vi trực tiếp thực hiện

| Phần việc | File/artifact | Input | Output |
|---|---|---|---|
| Chạy lại quality experiment độc lập | `handoff/ngan-quality-check/run_checks.py` | Ba JSON baseline/corrupted/repaired | Báo cáo cho ba trạng thái |
| Phân tích quy tắc thất bại | `handoff/ngan-quality-check/outputs/corrupted_quality_report.json` | Kết quả Great Expectations | DOI trùng và summary rỗng được xác định theo dòng |
| Bổ sung test biên số dòng | `handoff/ngan-quality-check/tests/test_ngan_cases.py` | DataFrame hợp lệ 5 và 4 dòng | 5 dòng đạt, 4 dòng bị chặn |
| Ghi nhận kết quả và giải thích | `handoff/ngan-quality-check/NGAN_NOTES.md` | Output chạy thật | Nhật ký có lệnh, phiên bản, kết quả và giới hạn |

Tôi không nhận ownership cho phần cài đặt pipeline chính do Nguyễn Văn Duy tích hợp. Phần của tôi là chạy kiểm tra độc lập, đọc bằng chứng lỗi, bổ sung trường hợp test mới và xác nhận hành vi của Quality Gate.

## 3. Kết quả có thể đối chiếu

- Python 3.11.9 trên Windows 10 Home 64-bit.
- Kết quả ba trạng thái: `baseline=True`, `corrupted=False`, `repaired=True`.
- Bộ corrupted có 21 dòng; 4 dòng có `paper_id` bị trùng tại chỉ số 0, 1, 19, 20.
- Sáu dòng corrupted có `summary` rỗng tại chỉ số 0, 1, 2, 3, 19, 20.
- Freshness của corrupted vẫn đạt: 4/21 dòng cũ, tương đương 19,05%, chưa vượt 25%.
- Test cá nhân xác nhận ranh giới `min_value=5`: 5 dòng hợp lệ đạt, 4 dòng không đạt.
- Bộ test handoff sau thay đổi: **23 test đạt**.

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Pipeline RAG không nên index dữ liệu chỉ vì file đọc được. Dữ liệu có thể thiếu nội dung, trùng DOI hoặc quá cũ, khiến retrieval và câu trả lời suy giảm. Quality Gate cần chặn các lỗi cấu trúc/nội dung, còn Freshness SLA đo tỷ lệ bài quá cũ.

### Cách kiểm tra

`run_data_quality_checks` tạo bản sao DataFrame, chuẩn hóa các chuỗi bắt buộc bằng `strip()` và đổi chuỗi rỗng thành `None`. Great Expectations kiểm tra số dòng, not-null, DOI không trùng và độ dài summary. `evaluate_freshness_sla` xác thực `age_days`, đếm bài trên 180 ngày và chỉ đạt khi tỷ lệ không vượt 25%.

| Thành phần | Nội dung |
|---|---|
| Input | JSON baseline, corrupted và repaired được đóng băng từ cùng thí nghiệm |
| Output | `report.json`, `SUMMARY.md`, ba `*_quality_report.json` |
| Điều kiện chặn | Thiếu schema, ô bắt buộc rỗng, DOI trùng, summary ngắn, số dòng ngoài biên hoặc freshness không đạt |
| Module sử dụng output | Pipeline trước bước indexing và báo cáo observability |
| Nguyên tắc lỗi | Fail closed với tuổi thiếu, không phải số, vô hạn hoặc âm |

### Cách xác minh

```powershell
cd handoff/ngan-quality-check
python run_checks.py
python -m pytest -q
```

Kết quả mong đợi và thực tế đều là `baseline=True`, `corrupted=False`, `repaired=True`; toàn bộ 23 test đạt.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần test biên số dòng mà không làm nhiễu bởi các quy tắc khác.
- **Phương án cân nhắc:** lấy bớt dữ liệu thật hoặc tạo dữ liệu tối thiểu hợp lệ riêng cho test.
- **Phương án chọn:** tạo helper `_valid_papers(count)` với mọi trường còn lại hợp lệ, chỉ thay đổi số dòng từ 5 xuống 4.
- **Lý do:** lỗi test khi có 4 dòng chỉ có thể quy về expectation số dòng tối thiểu, giúp test dễ đọc và tái hiện ổn định.
- **Bằng chứng:** cùng schema/nội dung, 5 dòng có `gx_success=True` còn 4 dòng có `gx_success=False`.

## 6. Lỗi dữ liệu đã phân tích

- **Triệu chứng:** trạng thái corrupted có `success=False` dù Freshness SLA vẫn `is_fresh=True`.
- **Bước tái hiện:** chạy `python run_checks.py`, rồi mở `outputs/corrupted_quality_report.json`.
- **Nguyên nhân gốc:** hai DOI xuất hiện lặp lại làm 4 dòng vi phạm uniqueness; đồng thời 6 dòng có summary rỗng.
- **Xử lý trong thí nghiệm:** Quality Gate chặn trạng thái corrupted; dữ liệu được repair từ raw snapshot thay vì sửa tay báo cáo.
- **Xác minh:** repaired trở lại 24 dòng, gate đạt và hash dữ liệu khớp baseline.
- **Điều học được:** một SLA riêng lẻ đạt không đồng nghĩa bộ dữ liệu đủ chất lượng; kết quả tổng phải kết hợp nhiều tín hiệu.

## 7. Hiểu luồng end-to-end

1. Crossref response được giữ nguyên để truy vết; cleaning chuẩn hóa record và tạo `text_for_embedding`; MiniLM sinh vector để lưu vào ChromaDB.
2. Frozen evaluation set giữ nguyên 10 câu hỏi và ground-truth DOI. Retrieval hit rate đo khả năng lấy đúng tài liệu; Token F1 đo mức khớp câu trả lời.
3. Quality checks kiểm tra schema và giá trị trong một snapshot; freshness monitoring tập trung vào tuổi và tỷ lệ dữ liệu cũ.
4. Dùng cùng test set giúp chênh lệch metric phản ánh thay đổi dữ liệu, không phải thay đổi câu hỏi.
5. Repair thành công khi raw và test set không đổi, repaired data khớp baseline, gate đạt lại và các metric phục hồi.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
|---|---:|---:|---:|---|
| Retrieval hit rate | 1,0 | 0,7 | 1,0 | Dữ liệu hỏng làm mất đúng nguồn ở 3/10 câu |
| Mean Token F1 | 1,0 | 0,6125 | 1,0 | Nội dung lỗi làm câu trả lời suy giảm rõ rệt |
| Judge accuracy | 1,0 | 0,6 | 1,0 | Cùng xu hướng với retrieval và Token F1 |
| Mean judge score | 5,0 | 3,4 | 5,0 | Phục hồi hoàn toàn sau repair |
| Quality Gate | Đạt | Không đạt | Đạt | Bắt được DOI trùng và summary rỗng |
| Freshness | Đạt | Đạt | Đạt | 4/21 stale của corrupted vẫn dưới 25% |

Chuỗi bằng chứng: corruption tạo DOI trùng và summary rỗng → Quality Gate thất bại, hit rate giảm từ 1,0 xuống 0,7 và Token F1 giảm xuống 0,6125 → repair dựng lại từ raw snapshot → gate và metric trở lại baseline.

Điểm đáng chú ý là corrupted vẫn đạt freshness. Điều này không mâu thuẫn: freshness chỉ đo độ cũ, còn thất bại tổng thể đến từ uniqueness và nội dung bắt buộc.

## 9. Điều học được và hướng cải thiện

1. Quality Gate cần chạy trước indexing, không đợi đến khi agent trả lời sai.
2. Chuỗi chỉ chứa khoảng trắng phải được chuẩn hóa thành thiếu dữ liệu để expectation not-null có ý nghĩa.
3. Observability cần nhiều tín hiệu; freshness không thay thế kiểm tra uniqueness và completeness.

Nếu có thêm thời gian, tôi sẽ bổ sung test property-based cho các ngưỡng freshness và tự động xuất danh sách DOI lỗi ngắn gọn cho người vận hành.

## 10. Xác nhận cá nhân

- [x] Nội dung phản ánh đúng phạm vi kiểm tra độc lập và test đã bổ sung.
- [x] Có thể giải thích luồng end-to-end và sự khác nhau giữa quality với freshness.
- [x] Các kết luận đều có artifact hoặc test để đối chiếu.
- [x] Không nhận ownership cho phần pipeline chính của thành viên khác.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Dương Thị Ngân
**Ngày xác nhận:** 26/09/2026
