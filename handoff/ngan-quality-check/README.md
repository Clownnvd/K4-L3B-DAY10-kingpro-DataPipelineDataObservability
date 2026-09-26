# Phần thực hành của Ngân: kiểm tra chất lượng dữ liệu

Gói này chạy độc lập để kiểm tra ba bộ dữ liệu của Lab Day 10: ban đầu (`baseline`), đã gây lỗi (`corrupted`) và đã phục hồi (`repaired`). Ngân nhận phần **chạy lại, đọc lỗi, bổ sung một kiểm thử và giải thích kết quả**. Việc Ngân thực hành trên máy cá nhân hiện vẫn đang chờ thực hiện.

## Đầu vào và kết quả

Trong thư mục `data` cần có `baseline.json`, `corrupted.json` và `repaired.json`. Mỗi file chứa danh sách bản ghi được lấy từ lần chạy thực tế của bài lab. Chương trình chỉ đọc các file này và ghi báo cáo vào `outputs`.

| File | Nội dung |
|---|---|
| `src/observability/quality.py` | Bản sao nguyên vẹn của phần kiểm tra chất lượng trong bài lab chính |
| `src/core/config.py` | Cấu hình tối thiểu: nơi ghi báo cáo và ngưỡng tuổi bài 180 ngày |
| `run_checks.py` | Chạy cả ba bộ dữ liệu, lưu kết quả và kiểm tra kỳ vọng |
| `tests/test_quality.py` | Các tình huống kiểm thử quy tắc chất lượng |
| `tests/test_runner.py` | Kiểm thử luồng chạy và lưu báo cáo |
| `NGAN_NOTES.md` | Mẫu để Ngân tự ghi việc đã làm và kết quả quan sát được |

Gói dùng Python 3.11, 3.12 hoặc 3.13. Thư viện chính đã chốt phiên bản: Great Expectations 1.18.0, pandas 3.0.3 và python-dotenv 1.2.2. Lần cài đầu cần mạng để tải thư viện; các lệnh kiểm tra sau đó dùng dữ liệu tại máy. Không cần khóa dịch vụ hay mô hình ngôn ngữ. Gói không đọc file `.env`.

## Chạy bằng uv trên Windows, macOS hoặc Linux

`uv` là công cụ tạo môi trường Python riêng và cài thư viện cho dự án. Ví dụ một lệnh `uv sync` cài các thư viện của gói vào `.venv`, giúp tách chúng khỏi Python của dự án khác.

Sau khi giải nén, mở terminal tại thư mục có `pyproject.toml`. Nếu máy đã có `uv`, chạy:

```sh
uv sync --extra dev
uv run python run_checks.py --help
uv run python run_checks.py
uv run python -m pytest -q
```

Nếu máy chưa có `uv`, dùng cách `pip` bên dưới với Python đã cài. Hai cách đều chạy cùng mã nguồn và cùng bộ kiểm thử.

## Chạy bằng pip trên Windows

`pip` cài thư viện vào môi trường Python được gọi. Các lệnh sau chỉ định rõ Python trong `.venv`, nên không cần bật môi trường bằng PowerShell.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe run_checks.py
.\.venv\Scripts\python.exe -m pytest -q
```

Có thể thay `-3.11` bằng `-3.12` hoặc `-3.13` nếu máy đang dùng phiên bản đó.

## Chạy bằng pip trên macOS hoặc Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python run_checks.py
.venv/bin/python -m pytest -q
```

Kiểm tra `python3 --version` trước khi chạy; phiên bản phải nằm trong khoảng 3.11-3.13. Nếu hệ điều hành báo thiếu mô-đun `venv`, cài thành phần tạo môi trường Python của hệ điều hành rồi chạy lại lệnh đầu.

## Đọc kết quả

Kết quả mong đợi là `baseline=True`, `corrupted=False`, `repaired=True`. Nghĩa là bộ dữ liệu ban đầu và đã phục hồi đạt yêu cầu; bộ đã gây lỗi phải bị phát hiện. Chương trình trả mã kết thúc 0 khi cả ba kết quả khớp kỳ vọng, trả 1 khi có kết quả khác kỳ vọng.

Mở `outputs/SUMMARY.md` để xem bảng tổng hợp. `outputs/report.json` ghi thời điểm chạy, phiên bản thư viện, số dòng và dấu kiểm tra SHA-256 của từng đầu vào. SHA-256 là chuỗi 64 ký tự dùng để đối chiếu file; hai lần chạy có cùng chuỗi cho cùng file cho thấy đang dùng cùng nội dung. Báo cáo không tự xác nhận danh tính người chạy.

Ba file `*_quality_report.json` chứa kết quả chi tiết từ Great Expectations (GX), thư viện kiểm tra dữ liệu theo quy tắc. Ví dụ mã bài báo phải duy nhất: nếu 2 dòng dùng cùng mã, quy tắc này không đạt. Dựa vào đó, nhóm biết bộ dữ liệu chưa nên đưa sang bước sử dụng tiếp theo.

Các quy tắc hiện có:

- Số dòng từ 5 đến 5.000.
- Mã bài báo, tiêu đề, tóm tắt và nội dung phục vụ tìm kiếm không được rỗng.
- Mã bài báo không được trùng.
- Mỗi tóm tắt dài ít nhất 30 ký tự.
- Tuổi bài phải hợp lệ; tỷ lệ bài cũ không vượt quá 25%.

Tuổi bài (`age_days`) là số ngày từ ngày xuất bản đến ngày chụp dữ liệu của thí nghiệm. Một bài được tính là cũ khi tuổi **lớn hơn 180 ngày**. Tỷ lệ bài cũ bằng số bài cũ chia tổng số bài: với 24 bài, 6/24 = 25% vẫn đạt; 7/24 = 29,17% không đạt. Kiểm tra này giúp phát hiện dữ liệu quá cũ trước khi đưa sang bước trả lời câu hỏi. Gói giữ nguyên tuổi đã lưu để lần chạy trên máy Ngân tái hiện đúng thí nghiệm, không tính lại theo ngày hiện tại.

**Giới hạn về thông tin lĩnh vực:** dữ liệu nguồn không cung cấp lĩnh vực cho các bài báo. Cột lĩnh vực được giữ trống. Trong bộ câu hỏi của bài lab chính, `missing_metadata=true` đánh dấu thiếu thông tin và câu trả lời là `Not provided in source metadata.`. Kiểm tra chất lượng đạt không có nghĩa thông tin nguồn đã đầy đủ; gói này không suy đoán lĩnh vực để lấp chỗ trống.

## Ngân cần làm gì

1. Chạy chương trình và bộ kiểm thử trên máy cá nhân. Điền ngày chạy, phiên bản Python và kết quả thật vào `NGAN_NOTES.md`.
2. Mở báo cáo của bộ `corrupted`, tìm ít nhất một quy tắc không đạt. Ghi tên quy tắc, số dòng liên quan và giải thích bằng dữ liệu nhìn thấy.
3. Đọc `src/observability/quality.py`, đối chiếu với `tests/test_quality.py`. Giải thích vì sao chuỗi chỉ có dấu cách phải được tính là thiếu dữ liệu.
4. Thêm một kiểm thử do Ngân tự viết: chẳng hạn bộ 5 dòng hợp lệ phải đạt giới hạn số dòng, còn 4 dòng phải không đạt. Đặt kiểm thử trong `tests/test_ngan_cases.py`, rồi chạy lại `python -m pytest -q` bằng môi trường đã chọn.
5. Hoàn thiện ghi chép về phần đã sửa và kết quả chạy lại. Giữ bộ dữ liệu gốc để còn đối chiếu; nếu muốn thử sửa dữ liệu, sao chép sang thư mục mới và truyền `--data-dir` trỏ tới bản thử.

Gói chuẩn bị sẵn không được tính là phần Ngân đã thực hiện. Chỉ cập nhật trạng thái đóng góp sau khi Ngân chạy, sửa và ghi lại bằng chứng thực tế.
