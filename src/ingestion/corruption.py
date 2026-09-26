from __future__ import annotations

from datetime import date, timedelta
import json
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six repeatable defects to a copy, keeping unaffected controls.

    Selection depends only on publication date and DOI, never evaluation answers.
    Drop ceil(20% of rows), divide survivors into five contiguous near-equal
    groups (blank, noise, short title, stale date, control), then duplicate two
    survivors. Earlier groups receive the remainder. Dates move back 365 days
    and ages increase by 365; derived text/length always reflect the defects.
    Require at least ten unique clean rows so all groups remain nonempty.
    The log records each operation independently; no cleaning is run afterward.
    """
    if len(df) < 10 or df.paper_id.nunique() != len(df):
        raise ValueError("Corruption requires at least 10 rows with unique paper IDs.")
    result = df.sort_values(["published", "paper_id"], ascending=[False, True]).copy(deep=True).reset_index(drop=True)
    operations = []

    def record(name, changes):
        operations.append({"operation": name, "affected_ids": [change["paper_id"] for change in changes], "changes": changes})

    drop_count = ceil(len(result) * 0.2)
    dropped = json.loads(result.head(drop_count).to_json(orient="records"))
    record("drop_newest", [{"paper_id": row["paper_id"], "before": row, "after": None} for row in dropped])
    result = result.iloc[drop_count:].reset_index(drop=True)
    group_size, remainder = divmod(len(result), 5)
    groups, start = [], 0
    for i in range(5):
        end = start + group_size + (i < remainder)
        groups.append(list(range(start, end)))
        start = end

    noise = " [CORRUPTED_NOISE] unrelated synthetic payload: zebra quasar waffle 987654321." * 12
    for name, indices in zip(("blank_summary", "inject_noise", "truncate_title", "stale_date"), groups[:4]):
        changes = []
        for index in indices:
            fields = ["published", "age_days"] if name == "stale_date" else ["title" if name == "truncate_title" else "summary"]
            before = json.loads(result.loc[[index], fields].to_json(orient="records"))[0]
            if name == "blank_summary":
                result.at[index, "summary"] = ""
            elif name == "inject_noise":
                result.at[index, "summary"] += noise
            elif name == "truncate_title":
                result.at[index, "title"] = result.at[index, "title"][:7]
            else:
                result.at[index, "published"] = (date.fromisoformat(result.at[index, "published"]) - timedelta(days=365)).isoformat()
                result.at[index, "age_days"] += 365
            after = json.loads(result.loc[[index], fields].to_json(orient="records"))[0]
            changes.append({"paper_id": result.at[index, "paper_id"], "before": before, "after": after})
        record(name, changes)

    result["summary_chars"] = result["summary"].str.len()
    result["text_for_embedding"] = result.apply(lambda row: "\n".join([
        f"Title: {row['title']}", f"Authors: {row['authors_joined']}",
        f"Published: {row['published']}", f"Categories: {row['categories_joined']}",
        f"Summary: {row['summary']}",
    ]), axis=1)
    controls = result.loc[groups[4], "paper_id"].tolist()
    duplicated = json.loads(result.head(2).to_json(orient="records"))
    record("duplicate_rows", [{"paper_id": row["paper_id"], "before": None, "after": row} for row in duplicated])
    result = pd.concat([result, result.head(2)], ignore_index=True)
    write_json(Path(output_log_path), {
        "schema_version": 1, "input_rows": len(df), "output_rows": len(result),
        "selection_policy": "published descending, DOI ascending; drop ceil(n*0.20); split survivors into five contiguous groups",
        "drop_fraction": 0.2, "drop_rounding": "ceiling", "operations": operations,
        "unaffected_control_ids": controls,
    })
    return result
