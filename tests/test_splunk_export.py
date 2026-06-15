"""Tests for Splunk export helpers (no live Splunk connection)."""

import pytest

from attack_range.splunk_export import (
    get_splunk_connection_from_config,
    normalize_search,
)


def test_normalize_search_adds_search_prefix():
    assert normalize_search("index=*") == "search index=*"


def test_normalize_search_preserves_existing_prefix():
    assert normalize_search("search index=main") == "search index=main"


def test_normalize_search_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        normalize_search("   ")


def test_get_splunk_connection_from_config():
    config = {
        "general": {"attack_range_password": "fallback"},
        "attack_range": [
            {
                "name": "splunk",
                "ip_last_octet": 10,
                "roles": [
                    {
                        "role": "P4T12ICK.ludus_ar_splunk",
                        "vars": {"ludus_ar_splunk_password": "secret"},
                    }
                ],
            }
        ],
    }
    conn = get_splunk_connection_from_config(config)
    assert conn["host"] == "10.0.2.10"
    assert conn["port"] == 8089
    assert conn["username"] == "admin"
    assert conn["password"] == "secret"


def test_get_splunk_connection_missing_role():
    with pytest.raises(ValueError, match="No Splunk server"):
        get_splunk_connection_from_config({"attack_range": []})
