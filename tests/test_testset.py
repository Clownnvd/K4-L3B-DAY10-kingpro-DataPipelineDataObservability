from collections import Counter
import json

import pandas as pd
import pytest

from evaluation.testset import build_test_set


def papers(count=24):
    return pd.DataFrame([dict(paper_id=f"10.1234/{i:02d}", title=f"Research title {i}",
                              summary=f"Summary for paper {i}. Additional detail.",
                              authors_joined=f"Author {i}", categories_joined="",
                              published=f"2026-09-{26-i:02d}") for i in range(count)])


def test_ten_frozen_grounded_questions_across_four_types(tmp_path):
    frame = papers()
    snapshot = frame.copy(deep=True)
    result = build_test_set(frame, tmp_path / "testset.json")
    assert len(result) == 10
    assert Counter(item["question_type"] for item in result) == {"summary": 3, "authors": 3, "date": 2, "categories": 2}
    assert len({item["id"] for item in result}) == 10
    assert len({item["ground_truth_doc_ids"][0] for item in result}) == 10
    lookup = frame.set_index("paper_id")
    for item in result:
        doi = item["ground_truth_doc_ids"][0]
        row = lookup.loc[doi]
        assert row.title in item["question"]
        if item["question_type"] == "categories":
            assert item["ground_truth"] == "Not provided in source metadata."
            assert item["missing_metadata"] is True
        else:
            key = {"summary": "summary", "authors": "authors_joined", "date": "published"}[item["question_type"]]
            expected = f"Summary for paper {int(doi.rsplit('/', 1)[1])}." if item["question_type"] == "summary" else row[key]
            assert item["ground_truth"] == expected
            assert item["missing_metadata"] is False
    assert json.loads((tmp_path / "testset.json").read_text()) == result
    pd.testing.assert_frame_equal(frame, snapshot)
    assert build_test_set(frame.sample(frac=1, random_state=12), tmp_path / "again.json") == result
    assert (tmp_path / "testset.json").read_bytes() == (tmp_path / "again.json").read_bytes()


def test_existing_categories_are_preserved(tmp_path):
    frame = papers()
    frame["categories_joined"] = "AI, Information retrieval"
    result = build_test_set(frame, tmp_path / "testset.json")
    for item in result:
        if item["question_type"] == "categories":
            assert item["ground_truth"] == "AI, Information retrieval"
            assert item["missing_metadata"] is False


def test_insufficient_or_duplicate_dois_rejected(tmp_path):
    for frame in (papers(9), pd.concat([papers(9), papers(1)])):
        with pytest.raises(ValueError, match="unique"):
            build_test_set(frame, tmp_path / "testset.json")
    assert not (tmp_path / "testset.json").exists()
