from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import time
import warnings

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _text(value) -> str:
    parser = _PlainText()
    parser.feed(value if isinstance(value, str) else "")
    return normalize_whitespace(unescape(" ".join(parser.parts)))


def _publication_date(item: dict) -> str:
    for key in ("published", "published-online", "published-print", "issued"):
        try:
            parts = item[key]["date-parts"][0]
            return date(parts[0], parts[1] if len(parts) > 1 else 1,
                        parts[2] if len(parts) > 2 else 1).isoformat()
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Extract usable records without changing the original Crossref response."""
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise ValueError("Invalid Crossref message")
    items = payload["message"].get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref message.items must be a list")
    records = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = _text(item.get("DOI"))
        titles = item.get("title") or []
        title = _text(titles[0] if isinstance(titles, list) and titles else titles)
        published = _publication_date(item)
        if not paper_id or not title or not published:
            continue
        authors = []
        for author in item.get("author") or []:
            if isinstance(author, dict):
                name = _text(author.get("name")) or normalize_whitespace(
                    f"{_text(author.get('given'))} {_text(author.get('family'))}"
                )
                if name:
                    authors.append(name)
        categories = [_text(s) for s in item.get("subject", []) if _text(s)]
        url = item.get("URL") or f"https://doi.org/{paper_id}"
        pdf_url = next((link["URL"] for link in item.get("link", [])
                        if link.get("content-type") == "application/pdf" and link.get("URL")), url)
        updated = (item.get("deposited") or item.get("created") or {}).get("date-time", published)[:10]
        records.append(PaperRecord(
            paper_id=paper_id, title=title, summary=_text(item.get("abstract")),
            authors=authors, categories=categories,
            primary_category=categories[0] if categories else "",
            published=published, updated=updated, abs_url=url, pdf_url=pdf_url,
            comment=f"Crossref record {paper_id}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Reuse a snapshot by default; explicitly refresh it with bounded retries.

    A failed refresh never overwrites the last usable raw response. Successful
    responses are preserved byte-for-byte, separately from extracted records.
    """
    if settings.max_results < 1:
        raise ValueError("max_results must be positive")
    path = settings.paths.raw_api_response

    def validated_records(raw):
        records = parse_crossref_payload(json.loads(raw))[:settings.max_results]
        if len(records) != settings.max_results:
            raise ValueError(f"Expected {settings.max_results} valid records, got {len(records)}")
        return records

    if path.exists() and not settings.refresh_source:
        records = validated_records(path.read_bytes())
    else:
        error = None
        for attempt in range(3):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params={"query": settings.source_query, "filter": settings.source_filter,
                            "rows": settings.max_results},
                    headers={"User-Agent": "Day10-DataPipeline-Lab/0.1", "Accept": "application/json"},
                    timeout=(10, 30),
                )
                response.raise_for_status()
                records = validated_records(response.content)
            except (requests.RequestException, ValueError) as exc:
                error = exc
                retryable = isinstance(exc, (requests.ConnectionError, requests.Timeout)) or (
                    isinstance(exc, requests.HTTPError) and response.status_code in {429, 500, 502, 503, 504}
                )
                if retryable and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                break
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".json.tmp")
                temporary.write_bytes(response.content)
                temporary.replace(path)
                error = None
                break
        if error is not None:
            if not path.exists():
                raise RuntimeError("Crossref unavailable and no local snapshot exists") from error
            warnings.warn(f"Crossref refresh failed ({type(error).__name__}); using local snapshot", stacklevel=2)
            records = validated_records(path.read_bytes())
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the extracted snapshot used by cleaning and recovery."""
    return [PaperRecord(**record) for record in read_json(path)]
