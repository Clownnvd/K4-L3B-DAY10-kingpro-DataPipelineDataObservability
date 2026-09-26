"""Run the portable quality experiment without credentials or model downloads."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import pandas as pd

from core.config import Paths, Settings
from observability.quality import run_data_quality_checks


EXPECTED = {"baseline": True, "corrupted": False, "repaired": True}


def run_experiment(data_dir: Path, output_dir: Path) -> dict:
    data_dir, output_dir = Path(data_dir).resolve(), Path(output_dir).resolve()
    datasets = {}
    for state in EXPECTED:
        path = data_dir / f"{state}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing dataset: {path}. Copy all three supplied JSON datasets into --data-dir.")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload or any(not isinstance(row, dict) for row in payload):
            raise ValueError(f"Expected a nonempty JSON list of records: {path}")
        datasets[state] = (pd.DataFrame(payload), hashlib.sha256(path.read_bytes()).hexdigest())
    settings = Settings(paths=Paths(quality_dir=output_dir))
    states = {}
    for state, (frame, digest) in datasets.items():
        result = run_data_quality_checks(frame, settings, state)
        categories = frame.get("categories_joined", pd.Series("", index=frame.index))
        missing_categories = int(categories.fillna("").astype(str).str.strip().eq("").sum())
        states[state] = {
            "rows": len(frame), "input_sha256": digest,
            "expected_success": EXPECTED[state], "success": result["success"],
            "gx_success": result["gx_success"], "freshness": result["freshness"],
            "missing_category_rows": missing_categories,
            "quality_report": f"{state}_quality_report.json",
        }
    report = {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "dependencies": {name: version(name) for name in ("great-expectations", "pandas", "python-dotenv")},
        "states": states,
        "expectations_met": all(value["success"] == value["expected_success"] for value in states.values()),
        "scope": "Local quality checks only; this report does not identify or attest the person who ran it.",
        "age_policy": "Use frozen age_days from the original experiment; do not recompute against today's date.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Kết quả kiểm tra chất lượng", "", f"Thời điểm chạy UTC: `{report['executed_at_utc']}`.", "",
             "Bảng ghi kết quả của lần chạy này; người thực hiện tự bổ sung vào `NGAN_NOTES.md`.", "",
             "| Bộ dữ liệu | Số dòng | Đạt GX | Đạt độ mới | Đạt tổng | Kỳ vọng |", "|---|---:|---|---|---|---|"]
    for state, item in states.items():
        label = lambda value: "Đạt" if value else "Không đạt"
        lines.append(f"| {state} | {item['rows']} | {label(item['gx_success'])} | {label(item['freshness']['is_fresh'])} | {label(item['success'])} | {label(item['expected_success'])} |")
    lines.extend(["", "GX là Great Expectations, thư viện đối chiếu từng quy tắc với dữ liệu: số dòng, ô bắt buộc, mã bài báo duy nhất và độ dài tóm tắt.",
                  "", "Độ mới được tính bằng số bài có tuổi trên 180 ngày chia tổng số bài. Ví dụ 6/24 = 25% vẫn đạt; 7/24 = 29,17% không đạt. Tuổi âm hoặc thiếu cũng làm kiểm tra không đạt.",
                  "", "Tuổi bài được giữ theo ngày chụp dữ liệu của bài lab để có thể so sánh lại thí nghiệm.",
                  "", "Trường lĩnh vực còn thiếu trong dữ liệu nguồn; đạt kiểm tra không có nghĩa nguồn đã đủ mọi thông tin.",
                  "", f"Kết quả khớp cả ba kỳ vọng: {'Có' if report['expectations_met'] else 'Không'}.", ""])
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    if not report["expectations_met"]:
        raise RuntimeError("Quality results differ from expected baseline=True, corrupted=False, repaired=True; inspect the written reports.")
    return report


def main(argv=None) -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Check baseline, corrupted and repaired local JSON datasets using real Great Expectations.")
    parser.add_argument("--data-dir", type=Path, default=root / "data", help="Folder containing baseline.json, corrupted.json and repaired.json")
    parser.add_argument("--output-dir", type=Path, default=root / "outputs", help="Destination for reports (default: outputs beside this script)")
    args = parser.parse_args(argv)
    try:
        report = run_experiment(args.data_dir, args.output_dir)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"PASS: all {len(report['states'])} dataset outcomes match expectations. Reports: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
