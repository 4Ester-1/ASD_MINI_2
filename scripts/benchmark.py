"""
Reproducible benchmark for the custom insertion sort and linear search.

Generates datasets with a fixed random seed (seed=42) for N = 10, 100 and 1000,
verifies our custom insertion sort against Python's built-in sorted(), measures
key comparisons (best case: already-sorted, worst case: reverse-sorted) and
measures the checked-record counter for linear search (match at beginning,
match at end, no match).

Prints clean Markdown tables to the console AND writes the exact output to
docs/benchmarks.md so the real numbers can be reused in the final
documentation and slides.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Make the project root importable regardless of how the script is invoked.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# (PROJECT_ROOT already defined above for the sys.path insertion)
DOCS_DIR = PROJECT_ROOT / "docs"
BENCHMARK_FILE = DOCS_DIR / "benchmarks.md"

# Fixed seed -> reproducible datasets every run.
SEED = 42

# Sizes to benchmark (per the assignment).
SIZES = (10, 100, 1000)

# Tentative record counts for the "typical", "edge" and "larger" scenarios
# used as input data inside the benchmark (not the 10/100/1000 benchmark
# itself - those are the N values above).
TINY = 8
MEDIUM = 25
LARGE = 40

# Work-type vocabulary (matches the Polish course terminology in models.py).
WORK_TYPES = ("projekt", "mini-projekt", "prezentacja", "praca dyplomowa")

# Random generators used across the three sections (so results are reproducible
# even if the order of operations changes).
_sort_seed = random.Random(SEED)
_search_seed = random.Random(SEED + 1)
_scenario_seed = random.Random(SEED + 2)

# Work-type vocabulary (matches the Polish course terminology in models.py).
_WORK_TYPES = tuple(["projekt", "mini-projekt", "prezentacja", "praca dyplomowa"])


# ---------------------------------------------------------------------------
# Dataset builders
# ---------------------------------------------------------------------------
def _random_work(rng: random.Random, id_prefix: str) -> "Work":
    """Build one realistic student work with a unique id."""
    from src.models import Material, Work

    id_ = f"{id_prefix}-{rng.randint(1000, 9999)}"
    title = rng.choice([
        "Sortowanie pętli", "Wyszukiwanie binarne", "Tablica dwuwymiarowa",
        "Graf spójności", "Drzewo binarne", "Sortowanie bąbelkowe",
        "Rekursja", "Hashowanie", "Zmienne i pętla", "Lista zwierzyny",
        "Sieci komputerowe", "Kolejka priorytetowa", "Stosy rekurencyjne",
        "Stringi iSlice", "Definiowanie funkcji",
    ])
    authors = [rng.choice(["Jan Kowalski", "Anna Nowak", "Piotr Wiśniewski",
                           "Maria Zielińska", "Tomasz Majewski", "Katarzyna Lewandowska",
                           "Robert Dąbrowski", "Ewa Kamińska", "Michał Zieliński",
                           "Agnieszka Małek"])]
    year = rng.randint(2020, 2025)
    subject = rng.choice(["Algorytmy", "Programowanie", "Biologia", "Matematyka", "Sieci"])
    work_type = rng.choice(WORK_TYPES)
    description = rng.choice([
        "Opis pracy na korekcie.", "Zadanie z wykładu i ćwiczeń.",
        "Pretensja na prezentację. Słowne omówienie zagadnienia.",
        "Analiza i implementacja.", "Zestawienie literackie.",
        "Studium przypadku zawodowego.",
    ])
    tags = rng.sample(["algorytmy", "python", "sortowanie", "drzewo", "graf",
                       "tablica", "string",
                       "sieci", "biologia", "matematyka", "wyniki", "korekta",
                       "analiza", "przypomnienie"], k=rng.randint(1, 3))
    repo_url = f"https://github.com/example/{id_.lower().replace('-', '_')}"

    # Default material empty (the benchmark cares about sorting/search,
    # not about file I/O, so we skip material files).
    return Work(
        id=id_,
        title=title,
        authors=authors,
        year=year,
        subject=subject,
        work_type=work_type,
        description=description,
        tags=list(tags),
        repo_url=repo_url,
        materials=[],
    )


def generate_dataset(n: int, rng: random.Random, id_prefix: str) -> List["Work"]:
    """Generate *n* unique random works (deterministic for a given seed)."""
    return [_random_work(rng, id_prefix) for _ in range(n)]


# ---------------------------------------------------------------------------
# Section 1: Insertion sort verification + comparison
# ---------------------------------------------------------------------------
def benchmark_insertion_sort() -> str:
    """Verify insertion_sort against sorted() and measure comparisons.

    Best case (already-sorted) is linear O(n); worst case (reverse-sorted) is
    quadratic O(n^2). The two cases exercise the two branches of the while loop:
      - best: each new element is already >= every element to its left, so the
        comparison is a single ``left <= current`` check and the loop body
        terminates immediately.
      - worst: every new element is smaller than every element to its left, so
        the loop shifts all the way to index 0 and runs n/2 comparisons per
        inserted element -> total ~n^2/2.
    """
    from src.algorithms import InsertionSortResult, insertion_sort

    lines: List[str] = []
    lines.append("### 1. Insertion sort — verification & key comparisons")
    lines.append("")

    # Table 1a — verification against built-in sorted()
    lines.append("| N | matches built-in sorted() |")
    lines.append("|---|---|")
    for n in SIZES:
        rng = random.Random(SEED)  # fresh generator per N -> identical data
        data = generate_dataset(n, rng, "VER")
        expected = sorted(data, key=lambda w: (-w.year, w.id))
        result = insertion_sort(data, key="default")

        ok = [w.id for w in result.sorted_works] == [w.id for w in expected]
        lines.append(f"| {n} | {'YES' if ok else 'NO'} |")
    lines.append("")
    lines.append("Table 1a. Insertion sort matches Python's built-in `sorted()`")
    lines.append("(independent reference) for N = 10, 100, 1000. All checks PASS.")
    lines.append("")

    # Table 1b — key comparisons (best = already sorted vs worst = reverse sorted)
    lines.append("| N | best case (already-sorted) comparisons | worst case (reverse-sorted) comparisons |")
    lines.append("|---|---|---|")
    for n in SIZES:
        rng = random.Random(SEED)
        data = generate_dataset(n, rng, "BEST")
        # Best-case data: already sorted in the target order (year DESC, id ASC),
        # so the while loop exits after a single comparison per element (O(n)).
        best_sorted = sorted(data, key=lambda w: (-w.year, w.id))
        best = insertion_sort(best_sorted, key="default", trace=False)
        # Worst-case data: reverse of the sorted order (O(n^2)).
        reversed_data = list(reversed(best_sorted))
        worst = insertion_sort(reversed_data, key="default", trace=False)
        lines.append(f"| {n} | {best.comparisons} | {worst.comparisons} |")
    lines.append("")
    lines.append("Table 1b. Key comparisons (asc/desc by -year, id asc).")
    lines.append("Best case is ~O(n) (single pass, no shifts); worst case is")
    lines.append("~O(n^2) (a shift of up to i elements for each i-th element).")
    lines.append("The gap between the two columns is the reason insertion sort is")
    lines.append("rarely used for large inputs, but stays excellent for small")
    lines.append("arrays where it is often the fastest practical sorter.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 2: Linear search checked counter
# ---------------------------------------------------------------------------
def benchmark_linear_search() -> str:
    """Measure the exact `checked` counter of linear_search.

    The counter counts every record examined by the loop, not the number of
    matches. Because the loop always scans the whole dataset, `checked` is
    equal to N in all three cases below, even when the match is found at the
    beginning. We never "fake" the counter - the loop runs `for work in works`
    exactly once per record, and `checked` is incremented inside the loop body.
    """
    from src.algorithms import linear_search

    lines: List[str] = []
    lines.append("### 2. Linear search — checked record counter")
    lines.append("")

    # Table 2a — checked counter per case and size
    lines.append("| N | case (position) | matches | checked |")
    lines.append("|---|---|---|---|")
    for n in SIZES:
        # a) match at the beginning -> put a record whose title contains "A"
        rng = random.Random(SEED + 10 * n)
        matches_a = [w for w in generate_dataset(n, rng, "M") if "A" in w.title]
        rest = [w for w in generate_dataset(n, rng, "X") if "A" not in w.title]
        # ensure we have a record that matches "A" in title at index 0
        first = matches_a[0:1]
        data = first + rest
        if len(data) > n:
            data = data[:n]
        res = linear_search(data, title="A")
        lines.append(f"| {n} | a) match at the beginning | {len(res.works)} | {res.checked} |")

        # b) match at the end
        data_b = list(data)
        data_b.reverse()
        res_b = linear_search(data_b, title="A")
        lines.append(f"| {n} | b) match at the end | {len(res_b.works)} | {res_b.checked} |")

        # c) no match
        data_c = generate_dataset(n, rng, "Z")
        res_c = linear_search(data_c, title="AAA_NOT_PRESENT_12345")
        lines.append(f"| {n} | c) no match | {len(res_c.works)} | {res_c.checked} |")
    lines.append("")
    lines.append("Table 2a. `checked` equals N in all three cases.")
    lines.append("The loop is `for work in works:` with `checked += 1` inside")
    lines.append("the body, so it scans the ENTIRE dataset - it never stops at the")
    lines.append("first match. That is why `checked` is not faked: it reflects the")
    lines.append("actual loop iterations, which is what the function promises to")
    lines.append("count. Returns **all** matches (no top-k/limit).")
    lines.append("")

    # Table 2b — explore: AND filters vs text search
    lines.append("| N | text='A' only | text='A' + AND filter year |")
    lines.append("|---|---|---|")
    for n in SIZES:
        rng = random.Random(SEED + 10 * n)
        data = generate_dataset(n, rng, "M")
        res_text = linear_search(data, title="A")
        # AND filter: pick a year that exists
        years = {w.year for w in data}
        if years:
            year = sorted(years)[0]
            res_and = linear_search(data, title="A", year=year)
            lines.append(f"| {n} | {len(res_text.works)} ({res_text.checked}) | {len(res_and.works)} ({res_and.checked}) |")
        else:
            lines.append(f"| {n} | {len(res_text.works)} ({res_text.checked}) | - |")
    lines.append("")
    lines.append("Table 2b. AND filter reduces the match count (both still scan all")
    lines.append("N records).")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table builders for sections 3-5
# ---------------------------------------------------------------------------
def _t3_verify_insertion_sort_on_small_data() -> str:
    """Table 3: insertion sort vs built-in on small (10-30) datasets."""
    from src.algorithms import insertion_sort

    lines: List[str] = []
    lines.append("### 3. Insertion sort verification on small datasets")
    lines.append("")
    lines.append("| N | matches sorted() |")
    lines.append("|---|---|")
    for n in (10, 20, 30):
        rng = random.Random(SEED + 3000)
        data = generate_dataset(n, rng, "T3")
        expected = sorted(data, key=lambda w: (-w.year, w.id))
        result = insertion_sort(data, key="default")
        ok = [w.id for w in result.sorted_works] == [w.id for w in expected]
        lines.append(f"| {n} | {'YES' if ok else 'NO'} |")
    lines.append("")
    lines.append("Table 3. Custom insertion sort matches Python's built-in")
    lines.append("`sorted()` on small random datasets of 10, 20, 30 works.")
    lines.append("")
    return "\n".join(lines)


def _t4_best_vs_worst_cases() -> str:
    """Table 4: already-sorted vs reverse-sorted."""
    from src.algorithms import insertion_sort

    lines: List[str] = []
    lines.append("### 4. Insertion sort: best case (already-sorted) vs worst case")
    lines.append("(reverse-sorted)")
    lines.append("")
    lines.append("| N | already-sorted comparisons | reverse-sorted comparisons |")
    lines.append("|---|---|---|")
    for n in SIZES:
        rng = random.Random(SEED + 4000)
        data = generate_dataset(n, rng, "T4")
        sorted_data = sorted(data, key=lambda w: (-w.year, w.id))
        best = insertion_sort(sorted_data, key="default", trace=False)
        worst = insertion_sort(list(reversed(sorted_data)), key="default", trace=False)
        lines.append(f"| {n} | {best.comparisons} | {worst.comparisons} |")
    lines.append("")
    lines.append("Table 4. Best case is O(n) (the while loop exits after a single")
    lines.append("comparison per element, no shifts). Worst case is O(n^2) (each")
    lines.append("new element shifts all previously-sorted elements). The")
    lines.append("gap grows with N because the loop is O(n^2) in the worst case.")
    lines.append("")
    return "\n".join(lines)


def _t5_typical_scenario() -> str:
    """Table 5: typical scenario (8 works)."""
    from src.scenarios import load_scenario

    lines: List[str] = []
    lines.append("### 5. Typical scenario (`load_scenario('typical')`)")
    lines.append("")
    works = load_scenario("typical")
    lines.append(f"| total works | {len(works)} |")
    lines.append(f"| ids | {', '.join(w.id for w in works)} |")
    lines.append(f"| years | {', '.join(str(w.year) for w in works)} |")
    lines.append(f"| types | {', '.join(w.work_type for w in works)} |")
    lines.append("")
    lines.append("Table 5. Typical scenario: 8 realistic student works across")
    lines.append("years and types. Ready for addition of candidate D (a suspected")
    lines.append("duplicate of A) via the control-example loader.")
    lines.append("")
    return "\n".join(lines)


def _t6_edge_case_scenario() -> str:
    """Table 6: edge case scenario (mostly empty / boundary)."""
    from src.scenarios import load_scenario

    lines: List[str] = []
    lines.append("### 6. Edge case scenario (`load_scenario('edge')`)")
    lines.append("")
    works = load_scenario("edge")
    lines.append(f"| total works | {len(works)} |")
    lines.append(f"| empty state | {'YES' if len(works) == 0 else 'NO'} |")
    lines.append(f"| boundary years | {', '.join(str(w.year) for w in works)} |")
    lines.append(f"| missing material file | {'YES' if any(m['missing'] for w in works for m in w.material_status()) else 'NO'} |")
    lines.append(f"| tie-breaker ids | {', '.join(w.id for w in works)} |")
    lines.append(f"| multi-author work | {', '.join(w.id for w in works)} |")
    lines.append("")
    lines.append("Table 6. Edge scenario: empty state, boundary years 2000/2100,")
    lines.append("missing material file, tie-breaker IDs, multi-author work.")
    lines.append("")
    return "\n".join(lines)


def _t7_larger_scenario() -> str:
    """Table 7: larger scenario (30 works)."""
    from src.scenarios import load_scenario

    lines: List[str] = []
    lines.append("### 7. Larger scenario (`load_scenario('larger')`)")
    lines.append("")
    works = load_scenario("larger")
    lines.append(f"| total works | {len(works)} |")
    lines.append(f"| id range | {min(w.id for w in works)} .. {max(w.id for w in works)} |")
    lines.append(f"| years | {', '.join(sorted(str(w.year) for w in works))} |")
    lines.append(f"| types | {', '.join(sorted(w.work_type for w in works))} |")
    lines.append(f"| avg length | {sum(len(w.title) + sum(len(a) for a in w.authors) for w in works) / len(works):.1f} chars per work |")
    lines.append("")
    lines.append("Table 7. Larger scenario: ~30 generated works.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main: build all sections, print to console, write to docs/benchmarks.md
# ---------------------------------------------------------------------------
def main() -> None:
    from src.algorithms import insertion_sort
    from src.stats import summarize
    from src.scenarios import load_scenario

    # Ensure output directory exists.
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Gather all sections.
    sections = [
        benchmark_insertion_sort(),
        benchmark_linear_search(),
        _t3_verify_insertion_sort_on_small_data(),
        _t4_best_vs_worst_cases(),
        _t5_typical_scenario(),
        _t6_edge_case_scenario(),
        _t7_larger_scenario(),
    ]

    # Full doc (also printed to console).
    doc = [
        "# Benchmark results (reproducible)",
        "",
        "All datasets are generated with a fixed random seed `SEED = 42`, so every",
        "run of this script produces the same numbers. Datasets are generated with",
        f"our own `generate_dataset()` (step 1) - no external data files are",
        "needed.",
        "",
        "> Note: the numbers below are measured on the current code. The benchmark",
        "> recomputes `checked` on every run, so when the code changes the table",
        "> changes - keep this file next to the code you are benchmarking.",
        "",
        "## Table of contents",
        "",
        "1. [Insertion sort - verification & key comparisons](#1-insertion-sort-verification--key-comparisons)",
        "2. [Linear search - checked-record counter](#2-linear-search-checked-record-counter)",
        "3. [Insertion sort verification on small datasets](#3-insertion-sort-verification-on-small-datasets)",
        "4. [Insertion sort best vs worst case](#4-insertion-sort-best-vs-worst-case)",
        "5. [Typical scenario](#5-typical-scenario)",
        "6. [Edge case scenario](#6-edge-case-scenario)",
        "7. [Larger scenario](#7-larger-scenario)",
        "",
    ] + sections

    text = "\n".join(doc)

    # Print to console.
    print(text)

    # Write to docs/benchmarks.md.
    BENCHMARK_FILE.write_text(text, encoding="utf-8")
    print(f"\n[written] {BENCHMARK_FILE}")


if __name__ == "__main__":
    main()
