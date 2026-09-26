# Ghi chép thực hành của Ngân

Trạng thái: **đã hoàn thành phần thực hành Quality Check trên máy cá nhân**.

- Ngày chạy và hệ điều hành: 26/09/2026, Microsoft Windows 10 Home 64-bit (10.0.19045).
- Phiên bản Python: 3.11.9.
- Thư mục chạy: `handoff/ngan-quality-check` trên nhánh `ngan/quality-check`.
- Lệnh đã chạy: `python run_checks.py` và `python -m pytest -q` bằng môi trường Python 3.11 đã cài đúng dependency khóa trong `pyproject.toml`.
- Kết quả trước khi thêm test cá nhân: **22 passed in 9.51s**.
- Kết quả ba bộ dữ liệu: `baseline=True`, `corrupted=False`, `repaired=True`; cả ba khớp kỳ vọng của bài.
- Quy tắc không đạt trong bộ dữ liệu hỏng: `expect_column_values_to_be_unique` tại cột `paper_id`. Có 4 dòng liên quan ở chỉ số 0, 1, 19 và 20. Hai DOI `10.28932/jutisi.v12i2.13099` và `10.20944/preprints202608.1849.v1` đều xuất hiện hai lần.
- Một lỗi khác quan sát được: `expect_column_values_to_not_be_null` tại cột `summary` không đạt ở 6 dòng có chỉ số 0, 1, 2, 3, 19 và 20 vì các giá trị này rỗng.
- Chuỗi chỉ có dấu cách phải được coi là thiếu: bản sao kiểm tra gọi `value.strip()`, rồi đổi chuỗi rỗng thành `None`. Nhờ vậy ô nhìn rỗng không thể vượt qua expectation không-null.
- Giải thích ngưỡng độ mới: bài chỉ bị tính là cũ khi `age_days > 180`; SLA cho phép `stale_ratio <= 0.25`. Vì vậy đúng 25% vẫn đạt, còn trên 25% không đạt. Bộ corrupted có 4/21 bài cũ (19,05%), nên freshness đạt dù Quality Gate tổng thể không đạt.
- Giới hạn do thiếu thông tin lĩnh vực: `categories_joined` trống ở baseline 24/24, corrupted 21/21 và repaired 24/24. Quality Check đạt không có nghĩa metadata nguồn đầy đủ; không tự suy đoán lĩnh vực để điền.
- Thay đổi đã thực hiện: thêm `tests/test_ngan_cases.py` để kiểm tra biên số dòng tối thiểu. Năm dòng hợp lệ phải đạt; bốn dòng phải bị chặn.
- Artifact được tạo trực tiếp khi chạy: `outputs/report.json`, `outputs/SUMMARY.md` và ba file `*_quality_report.json`. Dữ liệu đầu vào được giữ nguyên.
- Kết quả chạy lại sau thay đổi: **23 passed in 8.31s**.

## Kết luận ngắn

Quality Gate đã phát hiện đúng dữ liệu hỏng thay vì chỉ kiểm tra chương trình có chạy hay không. Bộ corrupted vẫn đạt SLA độ mới nhưng bị chặn vì DOI trùng và summary rỗng; kết quả tổng chỉ đạt khi cả Great Expectations và freshness cùng đạt.
