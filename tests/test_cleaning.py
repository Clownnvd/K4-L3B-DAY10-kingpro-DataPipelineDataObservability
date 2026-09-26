from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pandas as pd
import pytest

from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord


def paper(**changes):
    record = PaperRecord(
        paper_id="10.1234/ABC", title="  A\n research  paper ",
        summary="  First sentence.\n Second sentence. ",
        authors=[" An  Nguyen ", "", " Binh\tLe "], categories=[" AI ", ""],
        primary_category=" AI ", published="2026-09-01", updated="2026-09-02",
        abs_url="https://doi.org/10.1234/ABC", pdf_url="", comment="  Source  record ",
    )
    return replace(record, **changes)


def test_normalization_age_and_embedding_text_without_mutating_raw():
    records = [paper()]
    original = deepcopy(records)
    df = build_clean_dataframe(records, datetime(2026, 9, 26, tzinfo=UTC))
    row = df.iloc[0]
    assert row.paper_id == "10.1234/abc"
    assert row.title == "A research paper"
    assert row.summary == "First sentence. Second sentence."
    assert row.authors == ["An Nguyen", "Binh Le"]
    assert row.authors_joined == "An Nguyen, Binh Le"
    assert row.categories == ["AI"]
    assert row.summary_chars == len(row.summary)
    assert row.age_days == 25
    assert row.text_for_embedding == (
        "Title: A research paper\nAuthors: An Nguyen, Binh Le\n"
        "Published: 2026-09-01\nCategories: AI\nSummary: First sentence. Second sentence."
    )
    assert records == original
    pd.testing.assert_frame_equal(df, build_clean_dataframe(records, datetime(2026, 9, 26, tzinfo=UTC)))


def test_deduplicate_case_insensitive_doi_and_sort_newest_first():
    df = build_clean_dataframe([
        paper(), paper(paper_id=" 10.1234/abc ", title="Duplicate"),
        paper(paper_id="10.1234/new", published="2026-09-20"),
    ], datetime(2026, 9, 26))
    assert df.paper_id.tolist() == ["10.1234/new", "10.1234/abc"]
    assert df.iloc[1].title == "A research paper"
    assert df.attrs["cleaning_report"]["duplicate_rows_removed"] == 1


@pytest.mark.parametrize("changes", [
    {"paper_id": "  "}, {"title": "\n"}, {"published": "2026-02-30"}, {"published": ""},
])
def test_rejects_unusable_rows_with_reason(changes):
    df = build_clean_dataframe([paper(**changes)], datetime(2026, 9, 26))
    assert df.empty
    assert {"paper_id", "age_days", "text_for_embedding"}.issubset(df.columns)
    report = df.attrs["cleaning_report"]
    assert report["invalid_rows_removed"] == 1
    assert report["rejected_rows"][0]["reason"]


def test_missing_optional_fields_are_not_invented_or_filtered():
    df = build_clean_dataframe([paper(authors=[], categories=[], primary_category="", summary="", updated="invalid")],
                               datetime(2026, 9, 26))
    row = df.iloc[0]
    assert row.categories == []
    assert row.categories_joined == ""
    assert row.summary_chars == 0
    assert row.updated == ""
    assert df.attrs["cleaning_report"]["missing_categories"] == 1


def test_empty_input_has_stable_schema():
    df = build_clean_dataframe([], datetime(2026, 9, 26))
    assert df.empty
    assert df.attrs["cleaning_report"]["input_rows"] == 0
    assert df.age_days.dtype.kind in "iu"


def test_timezone_conversion_and_future_dates_are_not_clamped():
    local = timezone(timedelta(hours=7))
    # 01:00 on Sep 26 in UTC+7 is still Sep 25 UTC.
    df = build_clean_dataframe([paper(published="2026-09-26T01:00:00+07:00"),
                               paper(paper_id="future", published="2026-09-27")],
                              datetime(2026, 9, 26, 1, tzinfo=local))
    by_id = df.set_index("paper_id")
    assert by_id.loc["10.1234/abc", "published"] == "2026-09-25"
    assert by_id.loc["10.1234/abc", "age_days"] == 0
    assert by_id.loc["future", "age_days"] == -2
