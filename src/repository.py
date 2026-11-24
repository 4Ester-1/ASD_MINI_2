"""Abstrakcja repozytorium i implementacja w pamięci (krok 1).

``WorkRepository`` to abstrakcyjny interfejs (ABC) opisujący operacje na
hurtowni prac: ``list_all``, ``get_by_id``, ``add``, ``update``, ``delete``
i ``replace_all``. Dzięki temu warstwa logiki (algorytmy, serwer, statystyki)
nie zależy od konkretnego magazynu danych.

``InMemoryWorkRepository`` to deterministyczna implementacja trzymająca rekordy
w słowniku RAM (z limitem ``MAX_RECORDS_DEFAULT = 1000``). Druga implementacja
— ``SqliteWorkRepository`` — żyje w ``src/sqlite_repository.py`` i realizuje
ten sam interfejs na pliku SQLite.

Wszystkie operacje mutujące walidują pola **przed** zmianą stanu i zwracają
``OperationResult`` z czytelnym powodem niepowodzenia; nigdy nie ma
częściowych zapisów.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from .models import Work
from .validation import ValidationError, validate_work, validate_work_list

__all__ = [
    "WorkRepository",
    "InMemoryWorkRepository",
    "OperationResult",
    "RepositoryError",
]

MAX_RECORDS_DEFAULT = 1000


class RepositoryError(Exception):
    """A repository operation was rejected for a clear reason."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass
class OperationResult:
    """Success/failure result returned by mutating repository operations."""

    success: bool
    reason: str = ""
    value: object = None


class WorkRepository(ABC):
    """Abstract interface; a SQLite implementation can be plugged in later."""

    @abstractmethod
    def list_all(self) -> List[Work]:
        ...

    @abstractmethod
    def get_by_id(self, work_id: str) -> Optional[Work]:
        ...

    @abstractmethod
    def add(self, work: Work) -> OperationResult:
        ...

    @abstractmethod
    def update(self, work_id: str, work: Work) -> OperationResult:
        ...

    @abstractmethod
    def delete(self, work_id: str) -> bool:
        """Delete the work with ``work_id``.

        Returns ``True`` if a record was deleted, ``False`` if it did not
        exist. Never raises for a missing id.
        """

    @abstractmethod
    def replace_all(self, works: List[Work]) -> OperationResult:
        ...


class InMemoryWorkRepository(WorkRepository):
    """Deterministic in-memory store that keeps all invariants."""

    def __init__(self, max_records: int = MAX_RECORDS_DEFAULT) -> None:
        if not isinstance(max_records, int) or isinstance(max_records, bool) or max_records <= 0:
            raise ValueError("max_records must be a positive integer")
        self._max_records = max_records
        self._works: dict[str, Work] = {}

    def list_all(self) -> List[Work]:
        return list(self._works.values())

    def get_by_id(self, work_id: str) -> Optional[Work]:
        return self._works.get(work_id)

    def add(self, work: Work) -> OperationResult:
        # Validate fields BEFORE any state change.
        try:
            validate_work(work)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        if work.id in self._works:
            return OperationResult(success=False, reason=f"duplicate work id: {work.id!r}")
        if len(self._works) >= self._max_records:
            return OperationResult(
                success=False,
                reason=f"record limit of {self._max_records} reached",
            )

        self._works[work.id] = work
        return OperationResult(success=True, value=work)

    def update(self, work_id: str, work: Work) -> OperationResult:
        try:
            validate_work(work)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        if work.id != work_id:
            return OperationResult(
                success=False, reason="work.id does not match the updated work id"
            )
        if work_id not in self._works:
            return OperationResult(success=False, reason=f"work not found: {work_id!r}")

        self._works[work_id] = work
        return OperationResult(success=True, value=work)

    def delete(self, work_id: str) -> bool:
        if work_id not in self._works:
            return False
        del self._works[work_id]
        return True

    def replace_all(self, works: List[Work]) -> OperationResult:
        # Validate the whole batch (no partial replacement).
        try:
            validate_work_list(works)
        except ValidationError as exc:
            return OperationResult(success=False, reason=f"invalid work: {exc.reason}")

        ids = [work.id for work in works]
        if len(ids) != len(set(ids)):
            return OperationResult(success=False, reason="duplicate work ids within the batch")

        if len(works) > self._max_records:
            return OperationResult(
                success=False, reason=f"record limit of {self._max_records} reached"
            )

        self._works = {work.id: work for work in works}
        return OperationResult(success=True, value=len(works))
