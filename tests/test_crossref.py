import json
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest
import requests

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def payload(count=24):
    return {"message": {"items": [
        {"DOI": f"10.1234/{i}", "title": ["  A &amp; B  "],
         "abstract": "<jats:p>A sufficiently long abstract about retrieval.</jats:p>",
         "author": [{"given": "An", "family": "Nguyen"}, {"name": "Research Group"}],
         "subject": ["AI"], "published": {"date-parts": [[2026, 9]]},
         "URL": f"https://doi.org/10.1234/{i}"}
        for i in range(count)]}}


def test_parse_normalizes_markup_and_partial_dates():
    data = payload(1)
    data["message"]["items"].append({"title": ["Missing DOI"]})
    record, = parse_crossref_payload(data)
    assert record.paper_id == "10.1234/0"
    assert record.title == "A & B"
    assert record.summary == "A sufficiently long abstract about retrieval."
    assert record.authors == ["An Nguyen", "Research Group"]
    assert record.categories == ["AI"]
    assert record.published == "2026-09-01"


def test_fetch_preserves_response_bytes_and_round_trips(tmp_path):
    settings = replace(load_settings(tmp_path), refresh_source=True)
    raw = json.dumps(payload(), indent=3).encode()
    response = Mock(content=raw, status_code=200)
    with patch("requests.get", return_value=response) as get:
        records = fetch_source_records(settings)
    assert len(records) == 24
    assert settings.paths.raw_api_response.read_bytes() == raw
    assert load_raw_records(settings.paths.raw_records_json) == records
    assert get.call_args.kwargs["params"]["rows"] == 24


def test_existing_snapshot_requires_no_network(tmp_path):
    settings = replace(load_settings(tmp_path), refresh_source=False)
    settings.paths.raw_api_response.parent.mkdir(parents=True)
    settings.paths.raw_api_response.write_text(json.dumps(payload()))
    with patch("requests.get") as get:
        assert len(fetch_source_records(settings)) == 24
        get.assert_not_called()


@pytest.mark.parametrize("failure", ["network", "invalid"])
def test_failed_refresh_preserves_snapshot(tmp_path, failure):
    settings = replace(load_settings(tmp_path), refresh_source=True)
    settings.paths.raw_api_response.parent.mkdir(parents=True)
    raw = json.dumps(payload()).encode()
    settings.paths.raw_api_response.write_bytes(raw)
    kwargs = ({"side_effect": requests.ConnectionError("offline")} if failure == "network"
              else {"return_value": Mock(content=b'{"message":{"items":[]}}', status_code=200)})
    with patch("requests.get", **kwargs), patch("time.sleep"):
        with pytest.warns(UserWarning, match="snapshot"):
            assert len(fetch_source_records(settings)) == 24
    assert settings.paths.raw_api_response.read_bytes() == raw


def test_no_network_and_no_snapshot_fails(tmp_path):
    settings = replace(load_settings(tmp_path), refresh_source=True)
    with patch("requests.get", side_effect=requests.Timeout("offline")), patch("time.sleep"):
        with pytest.raises(RuntimeError, match="snapshot"):
            fetch_source_records(settings)


def test_429_retries_then_succeeds(tmp_path):
    settings = replace(load_settings(tmp_path), refresh_source=True)
    busy = Mock(status_code=429)
    busy.raise_for_status.side_effect = requests.HTTPError("429")
    ok = Mock(status_code=200, content=json.dumps(payload()).encode())
    with patch("requests.get", side_effect=[busy, ok]) as get, patch("time.sleep"):
        assert len(fetch_source_records(settings)) == 24
        assert get.call_count == 2
