# Benchmark results (reproducible)

All datasets are generated with a fixed random seed `SEED = 42`, so every
run of this script produces the same numbers. Datasets are generated with
our own `generate_dataset()` (step 1) - no external data files are
needed.

> Note: the numbers below are measured on the current code. The benchmark
> recomputes `checked` on every run, so when the code changes the table
> changes - keep this file next to the code you are benchmarking.

## Table of contents

1. [Insertion sort - verification & key comparisons](#1-insertion-sort-verification--key-comparisons)
2. [Linear search - checked-record counter](#2-linear-search-checked-record-counter)
3. [Insertion sort verification on small datasets](#3-insertion-sort-verification-on-small-datasets)
4. [Insertion sort best vs worst case](#4-insertion-sort-best-vs-worst-case)
5. [Typical scenario](#5-typical-scenario)
6. [Edge case scenario](#6-edge-case-scenario)
7. [Larger scenario](#7-larger-scenario)

### 1. Insertion sort — verification & key comparisons

| N | matches built-in sorted() |
|---|---|
| 10 | YES |
| 100 | YES |
| 1000 | YES |

Table 1a. Insertion sort matches Python's built-in `sorted()`
(independent reference) for N = 10, 100, 1000. All checks PASS.

| N | best case (already-sorted) comparisons | worst case (reverse-sorted) comparisons |
|---|---|---|
| 10 | 9 | 45 |
| 100 | 99 | 4950 |
| 1000 | 999 | 499500 |

Table 1b. Key comparisons (asc/desc by -year, id asc).
Best case is ~O(n) (single pass, no shifts); worst case is
~O(n^2) (a shift of up to i elements for each i-th element).
The gap between the two columns is the reason insertion sort is
rarely used for large inputs, but stays excellent for small
arrays where it is often the fastest practical sorter.

### 2. Linear search — checked record counter

| N | case (position) | matches | checked |
|---|---|---|---|
| 10 | a) match at the beginning | 8 | 10 |
| 10 | b) match at the end | 8 | 10 |
| 10 | c) no match | 0 | 10 |
| 100 | a) match at the beginning | 87 | 100 |
| 100 | b) match at the end | 87 | 100 |
| 100 | c) no match | 0 | 100 |
| 1000 | a) match at the beginning | 807 | 1000 |
| 1000 | b) match at the end | 807 | 1000 |
| 1000 | c) no match | 0 | 1000 |

Table 2a. `checked` equals N in all three cases.
The loop is `for work in works:` with `checked += 1` inside
the body, so it scans the ENTIRE dataset - it never stops at the
first match. That is why `checked` is not faked: it reflects the
actual loop iterations, which is what the function promises to
count. Returns **all** matches (no top-k/limit).

| N | text='A' only | text='A' + AND filter year |
|---|---|---|
| 10 | 9 (10) | 2 (10) |
| 100 | 84 (100) | 16 (100) |
| 1000 | 824 (1000) | 149 (1000) |

Table 2b. AND filter reduces the match count (both still scan all
N records).

### 3. Insertion sort verification on small datasets

| N | matches sorted() |
|---|---|
| 10 | YES |
| 20 | YES |
| 30 | YES |

Table 3. Custom insertion sort matches Python's built-in
`sorted()` on small random datasets of 10, 20, 30 works.

### 4. Insertion sort: best case (already-sorted) vs worst case
(reverse-sorted)

| N | already-sorted comparisons | reverse-sorted comparisons |
|---|---|---|
| 10 | 9 | 45 |
| 100 | 99 | 4950 |
| 1000 | 999 | 499500 |

Table 4. Best case is O(n) (the while loop exits after a single
comparison per element, no shifts). Worst case is O(n^2) (each
new element shifts all previously-sorted elements). The
gap grows with N because the loop is O(n^2) in the worst case.

### 5. Typical scenario (`load_scenario('typical')`)

| total works | 8 |
| ids | T1, T2, T3, T4, T5, T6, T7, T8 |
| years | 2022, 2023, 2024, 2022, 2021, 2023, 2020, 2024 |
| types | projekt, projekt, mini-projekt, prezentacja, projekt, mini-projekt, praca dyplomowa, projekt |

Table 5. Typical scenario: 8 realistic student works across
years and types. Ready for addition of candidate D (a suspected
duplicate of A) via the control-example loader.

### 6. Edge case scenario (`load_scenario('edge')`)

| total works | 6 |
| empty state | NO |
| boundary years | 2000, 2100, 2023, 2023, 2022, 2023 |
| missing material file | YES |
| tie-breaker ids | E1, E2, E3, E4, E5, E6 |
| multi-author work | E1, E2, E3, E4, E5, E6 |

Table 6. Edge scenario: empty state, boundary years 2000/2100,
missing material file, tie-breaker IDs, multi-author work.

### 7. Larger scenario (`load_scenario('larger')`)

| total works | 27 |
| id range | L01 .. L27 |
| years | 2015, 2015, 2015, 2016, 2016, 2016, 2017, 2017, 2017, 2017, 2018, 2018, 2018, 2018, 2018, 2020, 2020, 2020, 2021, 2021, 2022, 2022, 2022, 2022, 2023, 2024, 2025 |
| types | mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, mini-projekt, praca dyplomowa, praca dyplomowa, praca dyplomowa, praca dyplomowa, praca dyplomowa, praca dyplomowa, prezentacja, prezentacja, prezentacja, prezentacja, prezentacja, projekt, projekt, projekt, projekt, projekt, projekt |
| avg length | 7.7 chars per work |

Table 7. Larger scenario: ~30 generated works.
