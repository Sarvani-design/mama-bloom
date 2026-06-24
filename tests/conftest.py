import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect mcp_server's session/baby-book storage to a temp dir
    so tests never write into the real data/ directory."""
    sessions_dir = tmp_path / "sessions"
    baby_book_dir = tmp_path / "baby_book"
    sessions_dir.mkdir()
    baby_book_dir.mkdir()

    import app.mcp_server as mcp_server

    monkeypatch.setattr(mcp_server, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(mcp_server, "BABY_BOOK_DIR", baby_book_dir)
    return tmp_path


@pytest.fixture
def mechanical_scenarios():
    path = (
        Path(__file__).parent
        / "eval"
        / "datasets"
        / "mama-bloom-mechanical-cases.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
