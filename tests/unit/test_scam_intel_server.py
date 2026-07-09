"""Unit tests for the scam-intel MCP server (mcp/scam_intel_server.py).

This is the shared knowledge base the agents read from and write to
(`query_tactics` / `add_tactic` / `get_stats`). It is pure SQLite, so it can be
tested deterministically.

The module lives in a `mcp/` directory that shadows the installed `mcp` PyPI
package and does its DB setup at import time, so it can't be imported by name.
We load it by file path (with the working directory pointed at a throwaway dir
so its import-time `data/` seed DB never touches the repo), then repoint its
module-global connection at a fresh in-memory database for each test.
"""

import importlib.util
import os
import sqlite3
from pathlib import Path

import pytest

SERVER_PATH = Path(__file__).resolve().parents[2] / "mcp" / "scam_intel_server.py"

# Same schema the server creates, including the (name, category) uniqueness that
# drives dedup on add_tactic.
SCHEMA = """
CREATE TABLE tactics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    lever TEXT NOT NULL,
    description TEXT NOT NULL,
    example_masked TEXT NOT NULL,
    UNIQUE(name, category)
)
"""

TACTIC = {
    "name": "deadline_pressure",
    "category": "phishing",
    "lever": "urgency",
    "description": "short fuse to stop you verifying",
    "example_masked": "account suspended in 24h - verify now",
}

EXPECTED_KEYS = {"id", "name", "category", "lever", "description", "example_masked"}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Load the server module by path, isolating its import-time DB writes."""
    load_dir = tmp_path_factory.mktemp("scam_intel_import")
    prev = Path.cwd()
    os.chdir(load_dir)
    try:
        spec = importlib.util.spec_from_file_location("scam_intel_server", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        os.chdir(prev)
    return module


@pytest.fixture
def db(server):
    """Repoint the module's connection at a fresh in-memory DB per test."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.commit()
    orig_conn, orig_cursor = server.conn, server.cursor
    server.conn = conn
    server.cursor = conn.cursor()
    yield server
    server.conn, server.cursor = orig_conn, orig_cursor
    conn.close()


def test_add_then_query_round_trip(db):
    result = db.add_tactic(**TACTIC)
    assert result["added"] is True

    rows = db.query_tactics("phishing")
    assert len(rows) == 1
    assert rows[0]["name"] == "deadline_pressure"
    assert rows[0]["lever"] == "urgency"
    assert set(rows[0]) == EXPECTED_KEYS


def test_query_unknown_category_returns_empty(db):
    db.add_tactic(**TACTIC)
    assert db.query_tactics("romance") == []


def test_duplicate_name_and_category_is_deduped(db):
    db.add_tactic(**TACTIC)
    result = db.add_tactic(**TACTIC)
    assert result["added"] is False
    assert "already exists" in result["reason"]
    # The duplicate must not create a second row.
    assert len(db.query_tactics("phishing")) == 1


def test_same_name_different_category_is_allowed(db):
    db.add_tactic(**TACTIC)
    result = db.add_tactic(**{**TACTIC, "category": "romance"})
    assert result["added"] is True
    assert len(db.query_tactics("phishing")) == 1
    assert len(db.query_tactics("romance")) == 1


def test_stats_on_empty_db(db):
    assert db.get_stats() == {"total": 0, "by_category": {}}


def test_stats_total_and_breakdown(db):
    db.add_tactic(**{**TACTIC, "name": "a", "category": "phishing"})
    db.add_tactic(**{**TACTIC, "name": "b", "category": "phishing"})
    db.add_tactic(**{**TACTIC, "name": "c", "category": "romance"})

    stats = db.get_stats()
    assert stats["total"] == 3
    assert stats["by_category"] == {"phishing": 2, "romance": 1}


def test_import_time_seed_is_loaded(server):
    """The module seeds its taxonomy at import; sanity-check that seed data."""
    stats = server.get_stats()
    assert stats["total"] == 12
    assert stats["by_category"]["romance"] == 3
    assert {t["name"] for t in server.query_tactics("phishing")} == {
        "deadline_pressure",
        "account_verify_link",
    }
