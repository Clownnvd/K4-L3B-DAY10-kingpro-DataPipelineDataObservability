from datetime import date, timedelta
import json

import pandas as pd
import pytest

from ingestion.corruption import corrupt_clean_dataframe


def clean_frame(count=24):
    rows = []
    for i in range(count):
        published = date(2026, 9, 26) - timedelta(days=i)
        rows.append(dict(paper_id=f"10.1234/{i:02d}", title=f"Research paper number {i}",
                         summary=f"An original summary explaining research result number {i}.",
                         authors_joined="A Nguyen", categories_joined="",
                         published=published.isoformat(), age_days=i,
                         summary_chars=0, text_for_embedding="stale derived value"))
    return pd.DataFrame(rows)


def test_six_visible_corruptions_leave_source_unchanged_and_log_every_change(tmp_path):
    original = clean_frame()
    snapshot = original.copy(deep=True)
    result = corrupt_clean_dataframe(original, tmp_path / "log.json")
    pd.testing.assert_frame_equal(original, snapshot)
    log = json.loads((tmp_path / "log.json").read_text())
    assert len(log["operations"]) == 6
    operations = {item["operation"]: item for item in log["operations"]}
    assert set(operations) == {"drop_newest", "blank_summary", "inject_noise", "truncate_title", "stale_date", "duplicate_rows"}
    assert operations["drop_newest"]["affected_ids"] == original.paper_id.head(5).tolist()
    assert len(result) == 21  # 24 - ceil(24 * .20) + 2 duplicates.
    assert result.paper_id.duplicated().sum() == 2
    for operation in operations.values():
        assert operation["affected_ids"]
        assert operation["changes"]
        for change in operation["changes"]:
            assert {"paper_id", "before", "after"} <= change.keys()
            assert change["before"] != change["after"]
    by_id = result.drop_duplicates("paper_id").set_index("paper_id")
    assert all(by_id.loc[doi, "summary"] == "" for doi in operations["blank_summary"]["affected_ids"])
    assert all("[CORRUPTED_NOISE]" in by_id.loc[doi, "summary"] for doi in operations["inject_noise"]["affected_ids"])
    assert all(len(by_id.loc[doi, "title"]) < 8 for doi in operations["truncate_title"]["affected_ids"])
    for change in operations["stale_date"]["changes"]:
        assert change["after"]["age_days"] - change["before"]["age_days"] == 365
        assert (date.fromisoformat(change["before"]["published"]) - date.fromisoformat(change["after"]["published"])).days == 365
    assert log["unaffected_control_ids"]
    for doi in log["unaffected_control_ids"]:
        assert by_id.loc[doi, "title"] == original.set_index("paper_id").loc[doi, "title"]
        assert by_id.loc[doi, "summary"] == original.set_index("paper_id").loc[doi, "summary"]
    for row in result.itertuples():
        assert row.summary_chars == len(row.summary)
        assert f"Title: {row.title}\n" in row.text_for_embedding
        assert f"Published: {row.published}\n" in row.text_for_embedding
        assert row.text_for_embedding.endswith(f"Summary: {row.summary}")
        assert (date(2026, 9, 26) - date.fromisoformat(row.published)).days == row.age_days


def test_corruption_deterministic_even_when_input_order_changes(tmp_path):
    first = corrupt_clean_dataframe(clean_frame(), tmp_path / "first.json")
    second = corrupt_clean_dataframe(clean_frame().sample(frac=1, random_state=8), tmp_path / "second.json")
    pd.testing.assert_frame_equal(first, second)
    assert (tmp_path / "first.json").read_bytes() == (tmp_path / "second.json").read_bytes()


def test_corruption_rejects_too_few_rows_before_writing(tmp_path):
    with pytest.raises(ValueError, match="at least"):
        corrupt_clean_dataframe(clean_frame(4), tmp_path / "log.json")
    assert not (tmp_path / "log.json").exists()
