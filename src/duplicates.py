"""Wykrywanie podejrzenia duplikatu z normalizacją.

Kandydat jest uznawany za *podejrzanie* duplikatowy tylko wtedy, gdy zachodzą
**wszystkie trzy** warunki jednocześnie:

  1. znormalizowany tytuł się zgadza (``.strip().lower()``),
  2. ``year`` się zgadza,
  3. zbiór znormalizowanych autorów się zgadza (niezależnie od kolejności).

Sam zgodny tytuł nigdy nie wystarcza. Wykrywanie to czysta operacja
tylko-do-odczytu: **nigdy** nie usuwa ani nie odrzuca rekordu automatycznie —
zwraca ``DuplicateWarning`` z listą pasujących rekordów i zostawia decyzję
(oraz jawne potwierdzenie) wywołującemu (``server.py`` / warstwa UI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, List, Tuple

from .models import Work

__all__ = [
    "DuplicateWarning",
    "normalize_text",
    "find_suspected_duplicates",
]


@lru_cache(maxsize=512)
def normalize_text(value: str) -> str:
    """Normalize a value for comparison: strip surrounding whitespace and
    lowercase. Non-string values normalize to the empty string so that a
    non-Work / non-str field never crashes the comparison."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _norm_authors(authors: Iterable[str]) -> Tuple[str, ...]:
    """Order-independent normalized author set (sorted tuple of normalized,
    non-empty authors)."""
    return tuple(
        sorted(
            a for a in (normalize_text(x) for x in authors) if a
        )
    )


@dataclass
class DuplicateWarning:
    """Result of a duplicate check. ``matches`` holds the existing works that
    look like duplicates of ``candidate`` (never auto-deleted)."""

    candidate: Work
    matches: List[Work] = field(default_factory=list)

    @property
    def is_suspected(self) -> bool:
        return bool(self.matches)

    def to_dict(self) -> dict:
        return {
            "candidate_id": getattr(self.candidate, "id", None),
            "suspected": self.is_suspected,
            "matches": [w.id for w in self.matches],
        }


def find_suspected_duplicates(
    candidate: Work, existing: Iterable[Work]
) -> DuplicateWarning:
    """Return a ``DuplicateWarning`` for ``candidate`` against ``existing``.

    A work is a suspected duplicate when title (normalized), year and the
    order-independent set of normalized authors all match. Non-``Work``
    candidates are handled gracefully and yield a warning with no matches.
    """
    if not isinstance(candidate, Work):
        return DuplicateWarning(candidate=candidate, matches=[])

    title_norm = normalize_text(candidate.title)
    year = candidate.year
    authors_norm = _norm_authors(candidate.authors)

    matches: List[Work] = []
    for work in existing:
        if not isinstance(work, Work):
            continue
        # Trzy warunki AND; autorzy porównywani jako zbiór (niezależnie od
        # kolejności), tytuł normalizowany (.strip().lower()).
        if normalize_text(work.title) != title_norm:
            continue
        if work.year != year:
            continue
        if _norm_authors(work.authors) != authors_norm:
            continue
        matches.append(work)

    # Zwracamy ostrzeżenie (DuplicateWarning), a NIE usuwamy rekordu —
    # automatyczne kasowanie byłoby niebezpieczne; decyzję podejmuje użytkownik.
    return DuplicateWarning(candidate=candidate, matches=matches)
