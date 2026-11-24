"""Repozytorium SQLite — trwały magazyn archiwum.

Implementuje dokładnie ten sam interfejs ``WorkRepository`` co
``InMemoryWorkRepository``, dzięki czemu oba magazyny są w pełni wymienne za
serwerem bez zmiany warstwy odczytu/wyszukiwania/sortowania/statystyk.

Układ danych
------------
Jedna tabela ``works``, której kolumny skalarne odwzorowują model ``Work``.
Pola listowe (``authors``, ``tags``) oraz lista materiałów są zapisywane jako
JSON, więc zapis/odczyt jest bezstratny, a schemat pozostaje mały. Plik bazy
jest tworzony automatycznie (wraz z tabelą) przy pierwszym użyciu, dzięki
czemu ``python server.py`` nie wymaga żadnej ręcznej konfiguracji.

Domyślna ścieżka to ``data/archive.db`` (względem katalogu roboczego procesu);
callerzy mogą podać ścieżkę absolutną (używane w testach przez ``tmp_path``).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from .models import Material, Work
from .repository import OperationResult, WorkRepository
from .validation import ValidationError, validate_work, validate_work_list

__all__ = ["SqliteWorkRepository", "DEFAULT_DB_PATH"]

DEFAULT_DB_PATH = "data/archive.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    authors     TEXT NOT NULL,
    year        INTEGER NOT NULL,
    subject     TEXT NOT NULL,
    work_type   TEXT NOT NULL,
    description TEXT NOT NULL,
    tags        TEXT NOT NULL,
    repo_url    TEXT NOT NULL,
    materials   TEXT NOT NULL
);
"""


def _row_to_work(row: sqlite3.Row) -> Work:
    materials = [
        Material(name=m["name"], path_or_url=m["path_or_url"])
        for m in json.loads(row["materials"])
    ]
    return Work(
        id=row["id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        year=row["year"],
        subject=row["subject"],
        work_type=row["work_type"],
        description=row["description"],
        tags=json.loads(row["tags"]),
        repo_url=row["repo_url"],
        materials=materials,
    )


def _work_to_row(work: Work) -> dict:
    return {
        "id": work.id,
        "title": work.title,
        "authors": json.dumps(list(work.authors), ensure_ascii=False),
        "year": work.year,
        "subject": work.subject,
        "work_type": work.work_type,
        "description": work.description,
        "tags": json.dumps(list(work.tags), ensure_ascii=False),
        "repo_url": work.repo_url,
        "materials": json.dumps(
            [m.to_dict() for m in work.materials], ensure_ascii=False
        ),
    }


class SqliteWorkRepository(WorkRepository):
    """Persistent archive store backed by a single SQLite database file.

    Thread-safe: every operation opens a short-lived connection (or uses a
    per-thread one guarded by a lock for multi-statement transactions) so the
    threaded ``http.server`` can share one instance.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._path = Path(db_path)
        # Auto-create the parent directory and the table on first use.
        if self._path.parent != Path(""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        # serialize writes (sqlite connections are not shared across threads)
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # -- read ---------------------------------------------------------------- #
    def list_all(self) -> List[Work]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM works ORDER BY id"
            ).fetchall()
            return [_row_to_work(r) for r in rows]
        finally:
            conn.close()

    def get_by_id(self, work_id: str) -> Optional[Work]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM works WHERE id = ?", (work_id,)
            ).fetchone()
            return _row_to_work(row) if row else None
        finally:
            conn.close()

    # -- mutation ----------------------------------------------------------- #
    def add(self, work: Work) -> OperationResult:
        try:
            validate_work(work)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        row = _work_to_row(work)
        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT 1 FROM works WHERE id = ?", (work.id,)
                ).fetchone()
                if existing:
                    return OperationResult(
                        success=False, reason=f"duplicate work id: {work.id!r}"
                    )
                conn.execute(
                    "INSERT INTO works (id, title, authors, year, subject, "
                    "work_type, description, tags, repo_url, materials) "
                    "VALUES (:id, :title, :authors, :year, :subject, "
                    ":work_type, :description, :tags, :repo_url, :materials)",
                    row,
                )
                conn.commit()
                return OperationResult(success=True, value=work)
            finally:
                conn.close()

    def update(self, work_id: str, work: Work) -> OperationResult:
        try:
            validate_work(work)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        if work.id != work_id:
            return OperationResult(
                success=False, reason="work.id does not match the updated work id"
            )

        row = _work_to_row(work)
        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT 1 FROM works WHERE id = ?", (work_id,)
                ).fetchone()
                if not existing:
                    return OperationResult(
                        success=False, reason=f"work not found: {work_id!r}"
                    )
                conn.execute(
                    "UPDATE works SET title=:title, authors=:authors, year=:year, "
                    "subject=:subject, work_type=:work_type, description=:description, "
                    "tags=:tags, repo_url=:repo_url, materials=:materials "
                    "WHERE id=:id",
                    row,
                )
                conn.commit()
                return OperationResult(success=True, value=work)
            finally:
                conn.close()

    def delete(self, work_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM works WHERE id = ?", (work_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def replace_all(self, works: List[Work]) -> OperationResult:
        try:
            validate_work_list(works)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        ids = [w.id for w in works]
        if len(ids) != len(set(ids)):
            return OperationResult(success=False, reason="duplicate work ids within the batch")

        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM works")
                conn.executemany(
                    "INSERT INTO works (id, title, authors, year, subject, "
                    "work_type, description, tags, repo_url, materials) "
                    "VALUES (:id, :title, :authors, :year, :subject, "
                    ":work_type, :description, :tags, :repo_url, :materials)",
                    [_work_to_row(w) for w in works],
                )
                conn.commit()
                return OperationResult(success=True, value=len(works))
            finally:
                conn.close()
