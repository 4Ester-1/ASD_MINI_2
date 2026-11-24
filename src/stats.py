"""Statystyki liczone jawną pętlą.

Funkcja ``summarize(works)`` zlicza **prace** (nie autorów), używając
jawnych pętli ``for`` z własnymi licznikami (nie ``collections.Counter`` /
``len`` na skróty):

  * liczba prac ogółem,
  * liczebność wg ``year``,
  * liczebność wg ``work_type``.

Praca z wieloma autorami liczy się **raz** (to praca, nie autor). Puste
wejście jest obsługiwane bezpiecznie — bez błędów, bez dzielenia przez zero;
lata i typy są sortowane deterministycznie dla stabilnego wyjścia.

Wynik jest używany przez ``/api/stats`` w ``server.py`` oraz przez UI
(karty KPI „Metryki algorytmów”).
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List

from .models import Work

__all__ = [
    "Stats",
    "summarize",
]

EmptyStats = Dict[str, object]


class Stats:
    """Loop-based aggregate statistics for an archive of works."""

    def __init__(
        self,
        total: int = 0,
        by_year: dict[int, int] = None,
        by_type: dict[str, int] = None,
    ) -> None:
        self.total = total
        self.by_year = dict(by_year) if by_year else {}
        self.by_type = dict(by_type) if by_type else {}

    def __len__(self) -> int:
        return self.total

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "by_year": dict(sorted(self.by_year.items())),
            "by_type": dict(sorted(self.by_type.items())),
        }

    @classmethod
    def empty(cls) -> "Stats":
        return cls()


def _loop_total(works: Iterable[Work]) -> int:
    total = 0
    for _ in works:
        total += 1
    return total


def _loop_by_year(works: Iterable[Work]) -> dict[int, int]:
    counter: dict[int, int] = {}
    for work in works:
        # Jawna pętla akumulująca licznik (wymóg zadania: bez Counter/len).
        # Każda PRACA liczy się raz — wieloautorska praca to nadal 1 rekord.
        year = work.year
        if year in counter:
            counter[year] += 1
        else:
            counter[year] = 1
    return counter


def _loop_by_type(works: Iterable[Work]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for work in works:
        work_type = work.work_type
        if work_type in counter:
            counter[work_type] += 1
        else:
            counter[work_type] = 1
    return counter


def summarize(works: Iterable[Work]) -> Stats:
    """Aggregate statistics using explicit loops. Returns an empty Stats for
    any empty/None input (never raises, never divides by zero)."""
    if works is None:
        return Stats.empty()
    try:
        items = list(works)
    except TypeError as exc:
        raise TypeError("summarize expects an iterable of Work instances") from exc

    total = _loop_total(items)
    by_year = _loop_by_year(items)
    by_type = _loop_by_type(items)

    return Stats(total=total, by_year=by_year, by_type=by_type)
