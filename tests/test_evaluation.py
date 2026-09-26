import pytest
from evaluation.metrics import _token_f1
from retrieval.qa import _extract_answer
from retrieval.qa import answer_question
from retrieval.index import SearchResult
from core.config import load_settings
from unittest.mock import Mock


def test_token_f1_counts_repeated_tokens():
    assert _token_f1('a a b', 'a b b') == pytest.approx(2 / 3)
    assert _token_f1('a b', '') == 0
    assert _token_f1('A B', 'a b') == 1


def test_missing_categories_are_explicit_not_invented():
    result = SearchResult('doi', 'Title', 1, 'context', {'categories_joined': ''})
    assert _extract_answer('What categories does this paper belong to?', result) == 'Not provided in source metadata.'


def test_generated_templates_reach_correct_field(tmp_path):
    metadata = {"authors_joined": "A Nguyen", "published": "2026-09-01", "categories_joined": "", "summary": "First sentence. Second."}
    doc = {"paper_id": "doi", "title": "A paper's title", "content": "context", "metadata": metadata}
    index = Mock()
    index.lookup.return_value = doc
    index.search.return_value = []
    settings = load_settings(tmp_path)
    for question, expected in [
        ('Who are the authors of the paper "A paper\'s title"?', "A Nguyen"),
        ('What subject categories are provided in the source metadata for the paper "A paper\'s title"?', "Not provided in source metadata."),
        ('What is the publication date of the paper "A paper\'s title"?', "2026-09-01"),
        ('What does the source abstract say about the paper "A paper\'s title"?', "First sentence."),
    ]:
        result = answer_question(question, settings, index)
        assert result.answer == expected
        assert result.retrieved_doc_ids == ["doi"]
        index.lookup.assert_called_with("A paper's title")
