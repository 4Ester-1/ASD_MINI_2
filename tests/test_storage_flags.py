"""Automated tests for the SQLite repository, dual-mode storage, and the
backend-enforced feature flags (APP_ENABLE_SANDBOX / APP_READ_ONLY).

Run from the project root (or any cwd) with:

    python -m pytest tests/ -q
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import Work  # noqa: E402
from src.repository import InMemoryWorkRepository  # noqa: E402
from src.scenarios import (  # noqa: E402
    CONTROL_EXAMPLE_A,
    CONTROL_EXAMPLE_B,
    CONTROL_EXAMPLE_C,
)
from src.sqlite_repository import SqliteWorkRepository  # noqa: E402

import server  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _work(id_, title="T", year=2025, work_type="projekt") -> Work:
    return Work(
        id=id_,
        title=title,
        authors=["A. Kowalski"],
        year=year,
        subject="Algorytmy",
        work_type=work_type,
        description="Opis testowy.",
        tags=["test"],
        repo_url="https://github.com/example/" + id_,
        materials=[],
    )


class MockHandler(server.Handler):
    """Drive the handler without a real socket so flag logic is testable."""

    def __init__(self, path, method="GET", body=b"", content_type="application/json"):
        self.path = path
        self.command = method
        self._body = body
        self.headers = {} if not body else {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = 200
        self.sent_headers = {}

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass

    def log_message(self, *args):
        pass


def _do(handler):
    if handler.command == "GET":
        handler.do_GET()
    elif handler.command == "POST":
        handler.do_POST()
    elif handler.command == "DELETE":
        handler.do_DELETE()
    return handler.status, handler.wfile.getvalue().decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# 1. SqliteWorkRepository: CRUD + delete + persistence
# --------------------------------------------------------------------------- #
class TestSqliteRepository:
    def test_full_crud_and_delete(self, tmp_path):
        db = tmp_path / "archive.db"
        repo = SqliteWorkRepository(str(db))

        assert repo.add(_work("A")).success
        assert repo.add(_work("B")).success
        assert sorted(w.id for w in repo.list_all()) == ["A", "B"]

        # duplicate id rejected
        assert not repo.add(_work("A")).success

        # get_by_id
        assert repo.get_by_id("A").id == "A"
        assert repo.get_by_id("ZZZ") is None

        # update
        updated = _work("A", title="Nowy tytuł")
        assert repo.update("A", updated).success
        assert repo.get_by_id("A").title == "Nowy tytuł"
        # update missing -> failure
        assert not repo.update("ZZZ", _work("ZZZ")).success
        # id mismatch -> failure
        assert not repo.update("A", _work("B")).success

        # delete
        assert repo.delete("B") is True
        assert repo.delete("B") is False  # already gone
        assert repo.delete("NOPE") is False
        assert sorted(w.id for w in repo.list_all()) == ["A"]

    def test_persistence_across_instances(self, tmp_path):
        db = tmp_path / "archive.db"
        repo1 = SqliteWorkRepository(str(db))
        repo1.add(_work("A"))
        repo1.add(_work("B"))

        # A second instance over the same file sees the same data.
        repo2 = SqliteWorkRepository(str(db))
        assert sorted(w.id for w in repo2.list_all()) == ["A", "B"]

        # And a mutation via repo2 is visible to repo1.
        repo2.delete("A")
        assert sorted(w.id for w in repo1.list_all()) == ["B"]

    def test_replace_all(self, tmp_path):
        db = tmp_path / "archive.db"
        repo = SqliteWorkRepository(str(db))
        repo.add(_work("A"))
        repo.add(_work("B"))

        res = repo.replace_all([_work("X"), _work("Y")])
        assert res.success
        assert sorted(w.id for w in repo.list_all()) == ["X", "Y"]

        # invalid batch rejects atomically
        bad = repo.replace_all([_work("P"), _work("P")])
        assert not bad.success
        assert sorted(w.id for w in repo.list_all()) == ["X", "Y"]

    def test_roundtrip_materials_and_authors(self, tmp_path):
        db = tmp_path / "archive.db"
        repo = SqliteWorkRepository(str(db))
        from src.models import Material
        w = Work(
            id="M1",
            title="Z materiałem",
            authors=["Jan Kowalski", "Anna Nowak"],
            year=2024,
            subject="Algorytmy",
            work_type="projekt",
            description="Opis.",
            tags=["a", "b"],
            repo_url="https://github.com/example/m1",
            materials=[Material(name="instrukcja.txt", path_or_url="materialy/instrukcja.txt")],
        )
        repo.add(w)

        got = repo.get_by_id("M1")
        assert got.authors == ["Jan Kowalski", "Anna Nowak"]
        assert got.tags == ["a", "b"]
        assert [m.name for m in got.materials] == ["instrukcja.txt"]


# --------------------------------------------------------------------------- #
# 2. Sandbox isolation
# --------------------------------------------------------------------------- #
class TestSandboxIsolation:
    def test_scenario_in_sandbox_does_not_touch_archive(self, tmp_path):
        """Loading a scenario mutates only the sandbox; the SQLite archive is
        untouched."""
        db = tmp_path / "archive.db"
        archive = SqliteWorkRepository(str(db))
        archive.add(_work("PERSISTED"))

        sandbox = InMemoryWorkRepository()

        # Simulate the server loading a scenario into the sandbox.
        works = [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C]
        assert sandbox.replace_all(works).success

        # Sandbox has the scenario, archive still has only its own record.
        assert sorted(w.id for w in sandbox.list_all()) == ["A", "B", "C"]
        assert [w.id for w in archive.list_all()] == ["PERSISTED"]


# --------------------------------------------------------------------------- #
# 3. Feature flag enforcement (via the server handler)
# --------------------------------------------------------------------------- #
def _json_body(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


class TestFlagEnforcement:
    def test_default_flags_allow_everything(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", True)
        monkeypatch.setattr(server, "READ_ONLY", False)
        monkeypatch.setattr(server, "ACTIVE_MODE", "sandbox")

        status, _ = _do(MockHandler("/api/scenarios", "GET"))
        assert status == 200

        status, _ = _do(MockHandler("/api/works", "GET"))
        assert status == 200

    def test_sandbox_disabled_blocks_scenario_and_mode(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", False)
        monkeypatch.setattr(server, "READ_ONLY", False)
        monkeypatch.setattr(server, "ACTIVE_MODE", "archive")

        # Scenario list is empty (not 403) but scenario LOAD is forbidden.
        status, body = _do(MockHandler("/api/scenarios", "GET"))
        assert status == 200
        assert json.loads(body)["scenarios"] == {}

        status, _ = _do(MockHandler(
            "/api/load_scenario/control", "POST", _json_body({})
        ))
        assert status == 403

        # Mode switching is forbidden.
        status, _ = _do(MockHandler(
            "/api/mode", "POST", _json_body({"mode": "sandbox"})
        ))
        assert status == 403

    def test_read_only_blocks_mutations_allows_reads(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", True)
        monkeypatch.setattr(server, "READ_ONLY", True)
        monkeypatch.setattr(server, "ACTIVE_MODE", "sandbox")

        # Reads still work.
        for path in ["/api/works", "/api/search", "/api/trace", "/api/stats",
                     "/api/config"]:
            status, _ = _do(MockHandler(path, "GET"))
            assert status == 200, f"GET {path} should be allowed in read-only"

        # Mutations blocked with 403.
        payload = _json_body({
            "id": "NEW", "title": "X", "authors": ["A"], "year": 2025,
            "subject": "S", "work_type": "projekt", "description": "d",
        })
        status, _ = _do(MockHandler("/api/add", "POST", payload))
        assert status == 403

        status, _ = _do(MockHandler("/api/edit/NEW", "POST", payload))
        assert status == 403

        status, _ = _do(MockHandler("/api/delete/NEW", "DELETE"))
        assert status == 403

        status, _ = _do(MockHandler("/api/import", "POST", _json_body({"path": "x.json"})))
        assert status == 403

        status, _ = _do(MockHandler("/api/import/apply", "POST", _json_body({"path": "x.json"})))
        assert status == 403

    def test_config_endpoint_reports_flags(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", True)
        monkeypatch.setattr(server, "READ_ONLY", False)
        monkeypatch.setattr(server, "ACTIVE_MODE", "sandbox")

        status, body = _do(MockHandler("/api/config", "GET"))
        assert status == 200
        cfg = json.loads(body)
        assert cfg["sandbox_enabled"] is True
        assert cfg["read_only"] is False
        assert cfg["active_mode"] == "sandbox"


# --------------------------------------------------------------------------- #
# 4. Delete via handler (with confirmation semantics unchanged upstream)
# --------------------------------------------------------------------------- #
class TestDeleteEndpoint:
    def test_delete_endpoint_returns_ok_for_existing(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", True)
        monkeypatch.setattr(server, "READ_ONLY", False)
        monkeypatch.setattr(server, "ACTIVE_MODE", "sandbox")
        # Seed the sandbox with a record.
        assert server.sandbox_repo.replace_all([_work("DELME")]).success

        status, body = _do(MockHandler("/api/delete/DELME", "DELETE"))
        assert status == 200
        assert json.loads(body)["ok"] is True
        assert server.sandbox_repo.get_by_id("DELME") is None

    def test_delete_endpoint_404_for_missing(self, monkeypatch):
        monkeypatch.setattr(server, "SANDBOX_ENABLED", True)
        monkeypatch.setattr(server, "READ_ONLY", False)
        monkeypatch.setattr(server, "ACTIVE_MODE", "sandbox")

        status, _ = _do(MockHandler("/api/delete/GHOST", "DELETE"))
        assert status == 404
