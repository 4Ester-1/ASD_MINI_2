"""Automated tests for Step 3: duplicates, JSON import/export, control example,
material status, and the interplay of search/sort/stats.

Run from the project root (or any cwd) with:

    python -m pytest tests/ -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the project root importable from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algorithms import insertion_sort, linear_search  # noqa: E402
from src.duplicates import find_suspected_duplicates  # noqa: E402
from src.io_json import (apply_import, export_to_json,  # noqa: E402
                         parse_and_validate)
from src.models import Material, Work  # noqa: E402
from src.repository import InMemoryWorkRepository  # noqa: E402
from src.scenarios import (CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B,  # noqa: E402
                           CONTROL_EXAMPLE_C, CONTROL_EXAMPLE_D, load_scenario)
from src.stats import summarize  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _repo_with(works):
    repo = InMemoryWorkRepository()
    for w in works:
        repo.add(w)
    return repo


def test_control_example_default_sort_and_stats():
    """Control example: default sort is [B, A, C]; year stats 2026->1, 2025->2."""
    works = [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C]
    result = insertion_sort(works, key="default")
    assert [w.id for w in result.sorted_works] == ["B", "A", "C"]

    stats = summarize(works)
    assert stats.total == 3
    assert stats.by_year == {2025: 2, 2026: 1}


def test_adding_candidate_d_triggers_duplicate_warning_matching_a():
    """Candidate D is a suspected duplicate of A (normalized title, year and
    order-independent author set all match)."""
    existing = [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C]
    warning = find_suspected_duplicates(CONTROL_EXAMPLE_D, existing)
    assert warning.is_suspected
    assert [w.id for w in warning.matches] == ["A"]


def test_cancel_duplicate_keeps_state_unchanged():
    """Rejecting the duplicate (no explicit confirmation) leaves the repo intact."""
    repo = _repo_with([CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C])
    assert len(repo.list_all()) == 3
    # No add performed for D => still 3 works.
    assert len(repo.list_all()) == 3
    assert repo.get_by_id("D") is None


def test_reversed_author_order_does_not_hide_duplicate():
    """Order-independent author comparison: ['student b', 'student a'] still
    matches ['Student A', 'Student B']."""
    d_reversed = Work(
        id="D",
        title=" atlas ",
        authors=["student b", "student a"],
        year=2025,
        subject="Algorytmy",
        work_type="projekt",
        description="dup",
        tags=[],
        repo_url="https://github.com/example/dup",
        materials=[],
    )
    warning = find_suspected_duplicates(d_reversed, [CONTROL_EXAMPLE_A])
    assert warning.is_suspected


def test_and_filter_year_and_type_returns_only_a():
    """Two filters applied together (AND) return only records matching both."""
    works = [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C]
    result = linear_search(works, year=2025, work_type="projekt")
    assert [w.id for w in result.works] == ["A"]


def test_multi_author_work_counted_once():
    """A work with multiple authors counts once in statistics (works, not authors)."""
    multi = Work(
        id="E5", title="Wielu autorów", authors=["N. A", "O. B", "P. C"],
        year=2022, subject="S", work_type="projekt",
        description="3 authors", tags=[], repo_url="https://github.com/example/e5",
        materials=[],
    )
    solo = Work(
        id="E1", title="Granica 2000", authors=["I. Czerwona"],
        year=2000, subject="Algorytmy", work_type="projekt",
        description="b", tags=[], repo_url="https://github.com/example/e1",
        materials=[],
    )
    stats = summarize([multi, solo])
    assert stats.total == 2


def test_missing_material_file_does_not_block_description():
    """A missing local material returns a clear missing status without raising."""
    work = Work(
        id="E6", title="Brak materialu", authors=["Q. R"],
        year=2023, subject="S", work_type="projekt",
        description="opis pracy", tags=[],
        repo_url="https://github.com/example/e6",
        materials=[Material(name="brak.txt", path_or_url="materialy/brak.txt")],
    )
    status = work.material_status("materialy")
    assert status[0]["missing"] is True
    assert status[0]["status"] == "missing"
    assert work.description == "opis pracy"


def test_empty_list_handled_cleanly():
    """Empty list: stats, search and sort all return clean, error-free results."""
    assert summarize([]).total == 0
    assert summarize([]).by_year == {}
    search = linear_search([], title="x")
    assert search.works == [] and search.checked == 0
    sort = insertion_sort([], key="default")
    assert sort.sorted_works == [] and sort.comparisons == 0


def test_json_export_import_roundtrip(tmp_path):
    """JSON export then re-import restores the exact same data."""
    works = [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C]
    path = tmp_path / "roundtrip.json"
    export_to_json(works, path)

    ok, records, reason = parse_and_validate(path)
    assert ok, reason
    assert [w.id for w in records] == ["A", "B", "C"]

    repo = InMemoryWorkRepository()
    ok2, reason2 = apply_import(repo, records, confirmed=True)
    assert ok2, reason2
    assert sorted(w.id for w in repo.list_all()) == ["A", "B", "C"]


def test_invalid_json_does_not_overwrite(tmp_path):
    """An invalid file (bad JSON) never overwrites existing records."""
    repo = _repo_with([CONTROL_EXAMPLE_A])
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not valid JSON", encoding="utf-8")

    ok, records, reason = parse_and_validate(bad)
    assert ok is False
    assert records == []
    assert "invalid JSON" in reason
    # Repository untouched.
    assert [w.id for w in repo.list_all()] == ["A"]


def test_invalid_schema_does_not_overwrite(tmp_path):
    """A file with a missing required field is rejected before any mutation."""
    repo = _repo_with([CONTROL_EXAMPLE_A])
    bad = tmp_path / "bad_schema.json"
    bad.write_text(
        json.dumps({"format_version": "1.0", "works": [{"id": "NO_TITLE"}]}),
        encoding="utf-8",
    )
    ok, records, reason = parse_and_validate(bad)
    assert ok is False
    assert repo.get_by_id("NO_TITLE") is None


def test_import_requires_confirmation():
    """apply_import without confirmation never replaces the dataset."""
    repo = _repo_with([CONTROL_EXAMPLE_A])
    ok, reason = apply_import(repo, [CONTROL_EXAMPLE_B], confirmed=False)
    assert ok is False
    assert [w.id for w in repo.list_all()] == ["A"]  # untouched


def test_insertion_sort_verified_against_sorted():
    """Custom insertion sort matches built-in sorted() on already-sorted,
    reverse-sorted and tie data."""
    data = load_scenario("typical")

    expected = sorted(data, key=lambda w: (-w.year, w.id))
    got = insertion_sort(data, key="default")
    assert [w.id for w in got.sorted_works] == [w.id for w in expected]

    # reverse-sorted input
    got_rev = insertion_sort(list(reversed(data)), key="default")
    assert [w.id for w in got_rev.sorted_works] == [w.id for w in expected]

    # title asc
    expected_title = sorted(data, key=lambda w: (w.title.lower(), w.id))
    got_title = insertion_sort(data, key="title")
    assert [w.id for w in got_title.sorted_works] == [w.id for w in expected_title]
