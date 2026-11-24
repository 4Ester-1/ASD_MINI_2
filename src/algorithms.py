"""Własne algorytmy ASD I: wyszukiwanie liniowe i sortowanie przez wstawianie.

Moduł implementuje **własnoręcznie** (bez ``sorted`` / ``list.sort``) dwa
algorytmy wymagane w zadaniu:

1. ``linear_search`` — **wyszukiwanie liniowe + filtry AND**.
   Przechodzi po rekordach jeden po drugim (pętla ``for work in works``),
   zbiera **wszystkie** dopasowania (bez limitu „top-k”), a licznik
   ``checked`` inkrementuje przy każdej iteracji pętli — dlatego zawsze
   równa się liczbie przeglądniętych rekordów, niezależnie od liczby
   trafień. Złożoność: **O(n)** czas, **O(1)** pamięć (poza listą wyników).

2. ``insertion_sort`` — **sortowanie przez wstawianie**.
   Realizuje tzw. „przesuwanie w lewo” w pętli ``while``: każdy kolejny
   element jest wstawiany w odpowiednie miejsce wśród już posortowanych.
   Klucz domyślny: **rok malejąco, id rosnąco**; klucz ``title``: tytuł
   rosnąco (bez wielkości liter), id rosnąco — oba deterministyczne dzięki
   rozstrzyganiu remisów po ``id``. Licznik ``comparisons`` inkrementuje
   przy każdym porównaniu kluczy w pętli ``while``; ``trace=True`` zapisuje
   kroki „Przed → Decyzja → Po”. Złożoność: **O(n)** optymistyczna
   (dane posortowane), **O(n²)** pesymistyczna (dane odwrotne).

Obie funkcje są używane przez ``server.py`` (endpointy ``/api/search``,
``/api/works``, ``/api/trace``), testy oraz ``scripts/benchmark.py``.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .models import Work
from .validation import ValidationError, validate_work, WORK_TYPES

__all__ = [
    "SearchResult",
    "linear_search",
    "normalize_text",
    "SortKey",
    "InsertionSortResult",
    "insertion_sort",
]

TextFilter = Optional[str]


class SearchResult:
    """Result of a linear search."""

    def __init__(self, works: List[Work], checked: int) -> None:
        self.works = works
        self.checked = checked

    def __len__(self) -> int:
        return len(self.works)

    def __iter__(self):
        return iter(self.works)

    def to_dict(self) -> dict:
        return {"works": [w.id for w in self.works], "checked": self.checked, "matches": len(self.works)}


def normalize_text(value: str) -> str:
    """Normalize a string for comparison: strip + lower."""
    if not isinstance(value, str):
        raise ValidationError("expected str")
    return value.strip().lower()


def _text_contains(work: Work, field: str, query: str) -> bool:
    """Case-insensitive substring search inside one work field."""
    norm_query = normalize_text(query)
    if not norm_query:
        return True
    value = getattr(work, field)
    if field == "title":
        return norm_query in normalize_text(value)
    if field == "authors":
        # order-independent: any author contains the query
        return any(normalize_text(a).find(norm_query) != -1 for a in value)
    # tags / description
    return any(norm_query in normalize_text(item) for item in value)


def _match_text_fields(work: Work, title: TextFilter, authors: TextFilter,
                       keywords: Optional[List[str]]) -> bool:
    if title is not None and not _text_contains(work, "title", title):
        return False
    if authors is not None and not _text_contains(work, "authors", authors):
        return False
    if keywords:
        if not any(
            _text_contains(work, "tags", kw) or _text_contains(work, "description", kw)
            for kw in keywords
        ):
            return False
    return True


def _match_and_filter(work: Work, year: Optional[int], subject: Optional[str],
                      work_type: Optional[str]) -> bool:
    if year is not None and work.year != year:
        return False
    if subject is not None and normalize_text(subject) != normalize_text(work.subject):
        return False
    if work_type is not None and work_type != work.work_type:
        return False
    return True


def linear_search(
    works: Iterable[Work],
    *,
    title: TextFilter = None,
    authors: TextFilter = None,
    keywords: Optional[List[str]] = None,
    year: Optional[int] = None,
    subject: Optional[str] = None,
    work_type: Optional[str] = None,
) -> SearchResult:
    """Linearly scan `works` and return every record matching the criteria.

    - Text params (``title``, ``authors``, ``keywords``) are AND-ed together.
      ``keywords`` searches tags **and** description.
    - The provided filters (``year``, ``subject``, ``work_type``) are AND-ed
      onto the text match (subject/work_type case-insensitive).
    - Every record in `works` is examined exactly once; ``checked`` equals the
      number of loop iterations (== len(works) for a list/sequence).
    - Returns **all** matching records; no top-k / limit.
    """
    for name, value in (("year", year), ("subject", subject), ("work_type", work_type)):
        if value is None:
            continue
        if name == "year":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValidationError("year must be an integer")
            if not (2000 <= value <= 2100):
                raise ValidationError("year must be in range 2000-2100")
        elif name == "subject":
            if not isinstance(value, str):
                raise ValidationError("subject must be a string")
            if not value.strip():
                raise ValidationError("subject must not be empty")
        elif name == "work_type":
            if value not in WORK_TYPES:
                raise ValidationError(
                    f"work_type must be one of: {', '.join(sorted(WORK_TYPES))}"
                )

    keyword_list = list(keywords or [])
    results: List[Work] = []
    checked = 0

    for work in works:
        # --- RZECZYWISTA ITERACJA PĘTLI --------------------------------------
        # Licznik `checked` rośnie przy KAŻDYM przebiegu pętli, a nie przy
        # trafieniu — dlatego zawsze == len(works), nawet gdy dopasowanie jest
        # na samym początku (wyszukiwanie zbiera wszystkie trafienia, O(n)).
        checked += 1
        # Filtry tekstowe (title / authors / keywords) — warunki AND.
        if not _match_text_fields(work, title, authors, keyword_list):
            continue
        # Filtry strukturalne (year / subject / work_type) — również AND.
        if not _match_and_filter(work, year, subject, work_type):
            continue
        results.append(work)

    return SearchResult(results, checked)


SortKey = str  # "default" | "title"

# (field, is_ascending) where field is the work attribute to compare.
_KEY_SPEC: dict[SortKey, Tuple[str, bool]] = {
    "default": ("year", False),   # descending
    "title": ("title", True),     # ascending, case-insensitive
}

# Helper/flag for step-by-step trace entries (before -> decision -> after).
TraceEntry = Tuple[int, str, str, str, List[str]]


def _key(work: Work, key: SortKey) -> Tuple:
    """Building block used by the comparator; reflects the sort spec."""
    field, ascending = _KEY_SPEC[key]
    value = getattr(work, field)
    if field == "year":
        # year descending -> invert for a normal ascending tie-break
        return ((-value, work.id),)
    if field == "title":
        return ((normalize_text(value), work.id),)
    raise ValueError(f"unknown sort key {key!r}")


def _compare(a: Work, b: Work, key: SortKey) -> int:
    """Compare two works. Returns -1, 0, 1 per the sort spec."""
    ka = _key(a, key)
    kb = _key(b, key)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0


class InsertionSortResult:
    """Result of an insertion sort."""

    def __init__(
        self,
        sorted_works: List[Work],
        comparisons: int,
        trace: Optional[List[TraceEntry]] = None,
    ) -> None:
        self.sorted_works = sorted_works
        self.comparisons = comparisons
        self.trace = trace if trace is not None else []

    def __len__(self) -> int:
        return len(self.sorted_works)

    def to_dict(self) -> dict:
        return {
            "sorted_ids": [w.id for w in self.sorted_works],
            "comparisons": self.comparisons,
            "trace": [tuple(t) for t in self.trace],
        }


def insertion_sort(
    works: Iterable[Work],
    key: SortKey = "default",
    trace: bool = False,
) -> InsertionSortResult:
    """Insertion sort of `works` by the requested key.

    The main sorting path never calls ``sorted()`` or ``list.sort()``; it uses
    only swaps/assignments inside the while loop. Duplicates in the input are
    allowed and stay adjacent (deterministic).

    ``comparisons`` counts every key comparison performed in the loop body.
    ``trace`` (small datasets only) records entries of the form:
    (i, current_id, left_id, decision, array_after).
    """
    # Validate all works up front so a bad element cannot split the comparison
    # reference from the sorted copy (both see the same inputs).
    work_list = list(works)
    for w in work_list:
        validate_work(w)

    arr: List[Work] = list(work_list)
    comparisons = 0
    trace_entries: List[TraceEntry] = []

    for i in range(1, len(arr)):
        current = arr[i]
        j = i - 1
        current_id = current.id

        # Pętla „wstawiania”: przesuwamy element w lewo, dopóki jest większy
        # od sąsiada po lewej. KAŻDE porównanie kluczy liczy się do
        # `comparisons` (to jest licznik porównań, nie przesunięć).
        while j >= 0:
            left = arr[j]
            cmp = _compare(left, current, key)
            comparisons += 1

            if trace:
                # Migawka tablicy PRZED tym przesunięciem/zatrzymaniem —
                # tworzy wpis śladu „Przed → Decyzja → Po”.
                after = [w.id for w in arr]
                decision = "shift_left" if cmp > 0 else "stop"
                trace_entries.append((i, current_id, left.id, decision, after))

            if cmp > 0:
                arr[j + 1] = arr[j]
                j -= 1
            else:
                break

        arr[j + 1] = current

    return InsertionSortResult(arr, comparisons, trace_entries if trace else None)
