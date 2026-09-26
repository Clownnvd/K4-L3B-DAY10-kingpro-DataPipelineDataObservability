from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json, first_sentence


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Write ten baseline questions with DOI provenance from clean metadata.

    Sort newest first (DOI breaks ties), then take ten evenly spaced ranks,
    including both endpoints. The fixed type cycle yields 3 summary, 3 author,
    2 date and 2 category questions. This samples chronology without consulting
    corruption results. Use this same saved set for all three experiment states;
    never rebuild ground truth from corrupted or healed input.

    A missing source field stays missing: the explicit fallback answer and
    ``missing_metadata`` distinguish missing metadata from a factual category.
    """
    if len(df) < 10 or df.paper_id.nunique() != len(df):
        raise ValueError("Test set requires at least 10 clean rows with unique paper IDs.")
    ordered = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    types = ["summary", "authors", "date", "categories"] * 2 + ["summary", "authors"]
    fields = {"summary": "summary", "authors": "authors_joined", "date": "published", "categories": "categories_joined"}
    templates = {
        "summary": 'What does the source abstract say about the paper "{title}"?',
        "authors": 'Who are the authors of the paper "{title}"?',
        "date": 'What is the publication date of the paper "{title}"?',
        "categories": 'What subject categories are provided in the source metadata for the paper "{title}"?',
    }
    questions = []
    for index, question_type in enumerate(types):
        row = ordered.iloc[round(index * (len(ordered) - 1) / 9)]
        value = row[fields[question_type]]
        if question_type == "summary" and pd.notna(value):
            value = first_sentence(str(value))
        missing = pd.isna(value) or not str(value).strip()
        questions.append({
            "id": f"q{index + 1:02d}", "question_type": question_type,
            "question": templates[question_type].format(title=row["title"]),
            "ground_truth": "Not provided in source metadata." if missing else str(value).strip(),
            "ground_truth_doc_ids": [row["paper_id"]],
            "missing_metadata": bool(missing),
        })
    write_json(Path(output_path), questions)
    return questions
