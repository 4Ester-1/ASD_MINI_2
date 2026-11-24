"""Gotowe scenariusze demonstracyjne dla archiwum.

Każdy scenariusz zwraca listę instancji ``Work`` do przetestowania repozytorium,
algorytmów, wykrywania duplikatów i wyszukiwania. Ładowarka ``load_scenario``
zwraca listę obiektów ``Work`` używaną przez UI i skrypt benchmarkowy.

Scenariusze
-----------
- ``control`` — oficjalny przykład kontrolny (A, B, C) + kandydat D
- ``typical`` — ~6–8 realistycznych prac studenckich (różne lata i typy)
- ``edge``    — stan pusty, lata graniczne, plik materiału, remisy, wielu autorów
- ``larger``  — ~30 wygenerowanych prac

Wszystkie scenariusze są deterministyczne (stałe dane, nie losowe), więc
wczytanie jest identyczne w każdym środowisku. Uwaga na bezpieczeństwo:
w ``server.py`` scenariusze zawsze trafiają do **piaskownicy** (RAM), nigdy do
trwałego archiwum SQLite.
"""

from __future__ import annotations

from typing import List

from .models import Material, Work

__all__ = [
    "CONTROL_EXAMPLE_IDS",
    "CONTROL_EXAMPLE_A",
    "CONTROL_EXAMPLE_B",
    "CONTROL_EXAMPLE_C",
    "CONTROL_EXAMPLE_D",
    "load_scenario",
]


# ---------------------------------------------------------------------------
# Control example (the official case)
# ---------------------------------------------------------------------------
def _control_a() -> Work:
    return Work(
        id="A",
        title="Atlas",
        authors=["Student A", "Student B"],
        year=2025,
        subject="Algorytmy",
        work_type="projekt",
        description="Opis pracy A.",
        tags=["algorytmy", "atlas"],
        repo_url="https://github.com/example/atlas",
        materials=[],
    )


def _control_b() -> Work:
    return Work(
        id="B",
        title="Gra",
        authors=["Student C"],
        year=2026,
        subject="Gra w wolę",
        work_type="mini-projekt",
        description="Opis pracy B.",
        tags=["gra", "końce"],
        repo_url="https://github.com/example/gra",
        materials=[],
    )


def _control_c() -> Work:
    return Work(
        id="C",
        title="Sieci",
        authors=["Student D"],
        year=2025,
        subject="Sieci komputerowe",
        work_type="prezentacja",
        description="Opis pracy C.",
        tags=["sieci", "prezentacja"],
        repo_url="https://github.com/example/siec",
        materials=[],
    )


def _control_d() -> Work:
    """Candidate D: leading/trailing space in title, reversed + lowercased
    author names, same year and type as A -> suspected duplicate of A."""
    return Work(
        id="D",
        title=" atlas ",
        authors=["student b", "student a"],
        year=2025,
        subject="Algorytmy",
        work_type="projekt",
        description="Kandydat D - proląż kandydat do duplicate'a A.",
        tags=["atlas", "algorytmy"],
        repo_url="https://github.com/example/atlas-dup",
        materials=[],
    )


CONTROL_EXAMPLE_A = _control_a()
CONTROL_EXAMPLE_B = _control_b()
CONTROL_EXAMPLE_C = _control_c()
CONTROL_EXAMPLE_D = _control_d()
CONTROL_EXAMPLE_IDS = ("A", "B", "C", "D")


# ---------------------------------------------------------------------------
# Typical scenario (realistic student works across years and types)
# ---------------------------------------------------------------------------
def _typical() -> List[Work]:
    return [
        Work(
            id="T1", title="Lista zwierzyny", authors=["A. Nowak"], year=2022,
            subject="Biologia", work_type="projekt",
            description="Zwierzęta regionalne i ich siedliska.",
            tags=["biologia", "lista", "regionalne"],
            repo_url="https://github.com/example/t1",
            materials=[],
        ),
        Work(
            id="T2", title="Zmienne i pętla", authors=["B. Kowalski", "C. Wiśniewska"],
            year=2023, subject="Programowanie", work_type="projekt",
            description="Zadanie z wyrażeń warunkowych i pętli.",
            tags=["python", "pętla", "zmienna"],
            repo_url="https://github.com/example/t2",
            materials=[],
        ),
        Work(
            id="T3", title="Stosy rekurencyjne", authors=["D. Zieliński"],
            year=2024, subject="Algorytmy", work_type="mini-projekt",
            description="Zadanie o strukturze stosu.",
            tags=["stos", "rekurencja"],
            repo_url="https://github.com/example/t3",
            materials=[],
        ),
        Work(
            id="T4", title="Hashowanie", authors=["A. Nowak"], year=2022,
            subject="Algorytmy", work_type="prezentacja",
            description="Prezentacja o tabeli haszującej.",
            tags=["hash", "mapa"],
            repo_url="https://github.com/example/t4",
            materials=[],
        ),
        Work(
            id="T5", title="Drzewo binarne", authors=["E. Łaboda"], year=2021,
            subject="Algorytmy", work_type="projekt",
            description="Wstęp do drzew binarnych.",
            tags=["drzewo", "binarne"],
            repo_url="https://github.com/example/t5",
            materials=[],
        ),
        Work(
            id="T6", title="Rekurencyjne obliczenia", authors=["F. Szymańska"],
            year=2023, subject="Programowanie", work_type="mini-projekt",
            description="Odmiana i wykonywanie podobnych funkcji rekurencyjnie.",
            tags=["rekurencja", "funkcja"],
            repo_url="https://github.com/example/t6",
            materials=[],
        ),
        Work(
            id="T7", title="Wyszukiwanie w sortowanej liście",
            authors=["G. Mazur"], year=2020, subject="Algorytmy",
            work_type="praca dyplomowa",
            description="Bisection search in a sorted array.",
            tags=["wyszukiwanie", "sortowane", "binarne"],
            repo_url="https://github.com/example/t7",
            materials=[],
        ),
        Work(
            id="T8", title="Tablica dwuwymiarowa", authors=["H. Fiałek"],
            year=2024, subject="Programowanie", work_type="projekt",
            description="Operowanie na macierzy 2D: transponowanie i mnożenie.",
            tags=["tablica", "macierz"],
            repo_url="https://github.com/example/t8",
            materials=[],
        ),
    ]


# ---------------------------------------------------------------------------
# Edge case scenario (empty state, boundary years, missing material, ties,
# multi-author work)
# ---------------------------------------------------------------------------
def _edge() -> List[Work]:
    return [
        # boundary year 2000
        Work(
            id="E1", title="Granica 2000", authors=["I. Czerwona"], year=2000,
            subject="Algorytmy", work_type="projekt",
            description="Pierwsza możliwa data w regule.",
            tags=["granica", "2000"],
            repo_url="https://github.com/example/e1",
            materials=[],
        ),
        # boundary year 2100
        Work(
            id="E2", title="Granica 2100", authors=["J. Złotej"], year=2100,
            subject="Algorytmy", work_type="projekt",
            description="Ostatnia możliwa data w regule.",
            tags=["granica", "2100"],
            repo_url="https://github.com/example/e2",
            materials=[],
        ),
        # tie-breaker: two works with the SAME year and SAME id would collide;
        # here the tie is only in year, id differs.
        Work(
            id="E3", title="Tie-break", authors=["K. Czerwona", "L. Zielona"],
            year=2023, subject="Algorytmy", work_type="projekt",
            description="Ties in year, different ids.",
            tags=["tie", "brak"],
            repo_url="https://github.com/example/e3",
            materials=[],
        ),
        Work(
            id="E4", title="Tie-break2", authors=["M. Zielony"], year=2023,
            subject="Algorytmy", work_type="projekt",
            description="Different id, same year -> deterministic order by id.",
            tags=["tie"],
            repo_url="https://github.com/example/e4",
            materials=[],
        ),
        # multi-author work (counts as 1 in statistics)
        Work(
            id="E5", title="Wielu autorów", authors=["N. A", "O. B", "P. C"],
            year=2022, subject="S", work_type="projekt",
            description="3 authors count once.",
            tags=["multi"],
            repo_url="https://github.com/example/e5",
            materials=[],
        ),
        # missing material file: the material file does NOT exist, but the
        # description is still readable.
        Work(
            id="E6", title="Brak materialu", authors=["Q. R"], year=2023,
            subject="S", work_type="projekt",
            description="Missing material check.",
            tags=["brak", "material"],
            repo_url="https://github.com/example/e6",
            materials=[Material(name="brak.txt", path_or_url="materialy/brak.txt")],
        ),
        # empty state: this scenario returns fewer works than "larger"
        # (see the loader: "edge" has only these ~6 records).
    ]


# ---------------------------------------------------------------------------
# Larger scenario (generated works, ~30)
# ---------------------------------------------------------------------------
def _larger() -> List[Work]:
    from random import Random

    rng = Random(42)
    names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    subjects = ["Algorytmy", "Programowanie", "Biologia", "Matematyka", "Sieci"]
    types = ["projekt", "prezentacja", "mini-projekt", "praca dyplomowa"]
    # Generate ~27 works so the "larger" scenario is clearly in the
    # ~25-30 range required by the spec.
    works = []
    for i in range(1, 28):  # 27 works -> ids L01..L27
        works.append(Work(
            id=f"L{i:02d}",
            title=f"Work {i}",
            authors=[rng.choice(names)],
            year=rng.randint(2015, 2025),
            subject=rng.choice(subjects),
            work_type=rng.choice(types),
            description="Demo work for the larger scenario.",
            tags=["demo"],
            repo_url="https://github.com/example/larger",
            materials=[],
        ))
    return works


def load_scenario(name: str) -> List[Work]:
    """Return the requested scenario's list of works.

    Supported names: ``control``, ``typical``, ``edge``, ``larger``.
    """
    return {
        "control": [CONTROL_EXAMPLE_A, CONTROL_EXAMPLE_B, CONTROL_EXAMPLE_C],
        "typical": _typical(),
        "edge": _edge(),
        "larger": _larger(),
    }[name]
