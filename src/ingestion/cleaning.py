from __future__ import annotations

from dataclasses import asdict, fields
from datetime import UTC, datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace


def _clean_text(value: str | None) -> str:
    return normalize_whitespace(value or "")


def _utc_date(value: str):
    try:
        parsed = datetime.fromisoformat(_clean_text(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).date()
    except (TypeError, ValueError):
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Build clean records without modifying source data or writing files.

    Dates use UTC calendar days; naive run_date is interpreted as UTC. Reject
    missing identifiers/titles and invalid publication dates. Preserve missing
    optional metadata, short summaries and future dates for quality checks.
    DOI comparison ignores case; retain the first valid occurrence and sort by
    publication date descending, then DOI ascending. Filtering is recorded in
    ``df.attrs['cleaning_report']`` so removed records remain explainable.
    """
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    run_day = run_date.astimezone(UTC).date()
    rows, rejected, duplicates = [], [], []
    seen = set()
    for index, record in enumerate(records):
        row = asdict(record)
        for key, value in row.items():
            if key not in {"authors", "categories"}:
                row[key] = _clean_text(value)
        row["paper_id"] = row["paper_id"].lower()
        published = _utc_date(row["published"])
        reason = ("missing_paper_id" if not row["paper_id"] else
                  "missing_title" if not row["title"] else
                  "invalid_published_date" if published is None else None)
        if reason:
            rejected.append({"input_index": index, "paper_id": row["paper_id"], "reason": reason})
            continue
        if row["paper_id"] in seen:
            duplicates.append({"input_index": index, "paper_id": row["paper_id"]})
            continue
        seen.add(row["paper_id"])
        for key in ("authors", "categories"):
            row[key] = [_clean_text(value) for value in (row[key] or []) if _clean_text(value)]
        row["primary_category"] = row["categories"][0] if row["categories"] else ""
        updated = _utc_date(row["updated"])
        row["published"] = published.isoformat()
        row["updated"] = updated.isoformat() if updated else ""
        row["age_days"] = (run_day - published).days
        row["authors_joined"] = ", ".join(row["authors"])
        row["categories_joined"] = ", ".join(row["categories"])
        row["summary_chars"] = len(row["summary"])
        row["text_for_embedding"] = "\n".join([
            f"Title: {row['title']}", f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}", f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ])
        rows.append(row)
    columns = [field.name for field in fields(PaperRecord)] + [
        "age_days", "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
    ]
    df = pd.DataFrame(rows, columns=columns).astype({"age_days": "int64", "summary_chars": "int64"})
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    df.attrs["cleaning_report"] = {
        "run_date_utc": run_day.isoformat(), "input_rows": len(records), "output_rows": len(df),
        "invalid_rows_removed": len(rejected), "duplicate_rows_removed": len(duplicates),
        "rejected_rows": rejected, "duplicate_rows": duplicates,
        "missing_categories": sum(not row["categories"] for row in rows),
        "missing_authors": sum(not row["authors"] for row in rows),
        "summaries_under_30_chars": sum(row["summary_chars"] < 30 for row in rows),
        "future_publication_dates": sum(row["age_days"] < 0 for row in rows),
    }
    return df
