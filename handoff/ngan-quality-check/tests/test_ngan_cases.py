"""Kiểm thử biên số dòng do Ngân bổ sung cho phần Quality Check."""

import pandas as pd

from core.config import load_settings
from observability.quality import run_data_quality_checks


def _valid_papers(count: int) -> pd.DataFrame:
    """Tạo dữ liệu hợp lệ để chỉ thay đổi điều kiện số lượng bản ghi."""
    return pd.DataFrame(
        {
            "paper_id": [f"10.2026/ngan-{index}" for index in range(count)],
            "title": ["Bài báo kiểm thử chất lượng"] * count,
            "summary": [
                "Tóm tắt đủ dài để vượt qua quy tắc tối thiểu ba mươi ký tự."
            ]
            * count,
            "text_for_embedding": ["Nội dung hợp lệ dùng cho bước embedding."] * count,
            "age_days": [10] * count,
            "published": ["2026-09-16"] * count,
        }
    )


def test_ngan_minimum_row_count_boundary(tmp_path):
    """Đúng 5 dòng phải đạt, còn 4 dòng phải bị Quality Gate chặn."""
    settings = load_settings(tmp_path)

    five_rows = run_data_quality_checks(_valid_papers(5), settings, "ngan_five_rows")
    four_rows = run_data_quality_checks(_valid_papers(4), settings, "ngan_four_rows")

    assert five_rows["success"] is True
    assert five_rows["gx_success"] is True
    assert four_rows["success"] is False
    assert four_rows["gx_success"] is False
