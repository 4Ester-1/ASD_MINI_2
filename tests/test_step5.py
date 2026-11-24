"""Automated tests for Step 5 (reproducible benchmarks).

Run from the project root (or any cwd) with:

    python -m pytest tests/ -q
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Make the project root importable from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algorithms import insertion_sort, linear_search  # noqa: E402
from src.models import Work  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sample_dataset(n: int, seed: int = 42) -> list[Work]:
    """Build a deterministic, unsorted dataset of *n* works."""
    import random

    rng = random.Random(seed)
    return [
        Work(
            id=f"W{i:02d}",
            title="Test work",
            authors=["A. Kowalski"],
            year=2020 + (i % 6),
            subject="Algorytmy",
            work_type="projekt",
            description="D",
            tags=[],
            repo_url="https://github.com/example/x",
            materials=[],
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Insertion sort verification (10, 100, 1000)
# ---------------------------------------------------------------------------
class TestInsertionSortVerification:
    @pytest.mark.parametrize("n", (10, 100, 1000))
    def test_matches_built_in_sorted(self, n):
        data = _sample_dataset(n, seed=42)
        import random

        random.seed(42)
        random.shuffle(data)  # unsorted input

        expected = sorted(data, key=lambda w: (-w.year, w.id))
        result = insertion_sort(data, key="default")

        assert [w.id for w in result.sorted_works] == [w.id for w in expected]
        assert result.comparisons >= 0

    def test_best_case_has_fewer_comparisons_than_worst_case(self):
        """Best case (already sorted) is O(n); worst case (reverse sorted) is
        O(n^2). The best-case count must always be strictly smaller than the
        worst-case count for the same N."""
        for n in (10, 100, 1000):
            data = _sample_dataset(n, seed=42)
            best = insertion_sort(sorted(data, key=lambda w: (-w.year, w.id)),
                                  key="default", trace=False)
            worst = insertion_sort(list(reversed(sorted(data,
                                                             key=lambda w: (-w.year, w.id)))),
                                   key="default", trace=False)
            assert best.comparisons < worst.comparisons


# ---------------------------------------------------------------------------
# Linear search checked counter
# ---------------------------------------------------------------------------
class TestLinearSearchCheckedCounter:
    @pytest.mark.parametrize("n", (10, 100, 1000))
    def test_checked_equals_n_for_beginning_match(self, n):
        data = _sample_dataset(n, seed=42)
        result = linear_search(data, title="zzz_does_not_exist_fk87")
        assert result.checked == n

    @pytest.mark.parametrize("n", (10, 100, 1000))
    def test_checked_equals_n_for_end_match(self, n):
        data = _sample_dataset(n, seed=42)
        result = linear_search(list(reversed(data)), title="zzz_does_not_exist_fk87")
        assert result.checked == n

    @pytest.mark.parametrize("n", (10, 100, 1000))
    def test_checked_equals_n_for_no_match(self, n):
        data = _sample_dataset(n, seed=42)
        result = linear_search(data, title="_NO_MATCH_999999_")
        assert result.checked == n

    def test_returns_all_matches(self):
        """The function returns ALL matching records (no top-k / limit)."""
        data = _sample_dataset(100, seed=42)
        # Every record has the same title -> all 100 should match.
        result = linear_search(data, title="Test work")
        assert len(result.works) == 100
        assert result.checked == 100


# ---------------------------------------------------------------------------
# Benchmark script
# ---------------------------------------------------------------------------
class TestBenchmarkScript:
    def test_script_runs_and_writes_output(self):
        # Run the script from the project root.
        result = subprocess.run(
            [sys.executable, "scripts/benchmark.py"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, result.stderr
        assert "Table 1a." in result.stdout  # sanity: output contains tables

        out_path = PROJECT_ROOT / "docs" / "benchmarks.md"
        assert out_path.is_file(), "docs/benchmarks.md was not written"
        doc = out_path.read_text(encoding="utf-8")
        assert "| N | matches built-in sorted() |" in doc
        assert "| 1000 | YES |" in doc
        assert "| 1000 | 999 | 499500 |" in doc
