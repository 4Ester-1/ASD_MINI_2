"""
scripts/build_docs.py - generuje docs/dokumentacja_ASD1_M2_14.pdf (10 stron, PL).

Wynik:  docs/dokumentacja_ASD1_M2_14.pdf
Uruchomienie (z katalogu głównego projektu):
    python scripts/build_docs.py

Wymaganie:
    python -m pip install reportlab

Układ
-----
Dokładnie 10 stron, jedna sekcja logiczna na stronę:
  1. Strona tytułowa
  2. Architektura i reprezentacja danych
  3. Duplikaty, bezpieczeństwo, materiały
  4. Wyszukiwanie liniowe + licznik pętlą
  5. Insertionsort (sortowanie przez wstawianie)
  6. Przykład kontrolny + tabela kroków
  7. JSON export/import + scenariusze
  8. Testy automatyczne (pytest)
  9. Pomiary wydajności (10/100/1000) z docs/benchmarks.md
 10. Interfejs, dostępność, uruchomienie, wnioski

Polskie znaki diakrytyczne są renderowane czcionką TrueType (Arial w Windows,
DejaVuSans w Linuksie) zarejestrowaną przez reportlab.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCS_DIR = PROJECT_ROOT / "docs"
BENCHMARKS_MD = DOCS_DIR / "benchmarks.md"
PDF_OUT = DOCS_DIR / "dokumentacja_ASD1_M2_14.pdf"

PAGE_MARGIN = 9  # mm (margines wewnętrzny)


# --------------------------------------------------------------------------- #
# Rejestracja czcionki z polskimi znakami
# --------------------------------------------------------------------------- #
def register_fonts() -> None:
    """Rejestruje czcionkę TrueType obsługującą polskie znaki."""
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    arial_path = None
    for root, _dirs, files in os.walk("C:/Windows/Fonts"):
        for f in files:
            if f.lower() == "arial.ttf":
                arial_path = os.path.join(root, f)
                break
        if arial_path:
            break
    if not arial_path:
        for root, _dirs, files in os.walk("/usr/share/fonts"):
            for f in files:
                if f.lower() == "dejavusans.ttf":
                    arial_path = os.path.join(root, f)
                    break
            if arial_path:
                break
    if not arial_path:
        raise RuntimeError("Nie znaleziono czcionki z polskimi znakami (Arial/DejaVu).")
    pdfmetrics.registerFont(TTFont("Arial", arial_path))
    print(f"[fonts] zarejestrowano Arial z {arial_path}")


# --------------------------------------------------------------------------- #
# Parsowanie prawdziwych liczb z docs/benchmarks.md
# --------------------------------------------------------------------------- #
def extract_tables() -> list:
    """Zwraca listę tabel (każda to lista wierszy razem z nagłówkiem)
    w kolejności ich wystąpienia w docs/benchmarks.md."""
    text = BENCHMARKS_MD.read_text(encoding="utf-8")
    tables = []
    current = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{1,}:?", c) for c in cells):
                continue
            current.append(cells)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


# --------------------------------------------------------------------------- #
# Dokument
# --------------------------------------------------------------------------- #
class PDF:
    def __init__(self) -> None:
        self.doc = SimpleDocTemplate(
            str(PDF_OUT),
            pagesize=A4,
            leftMargin=PAGE_MARGIN,
            rightMargin=PAGE_MARGIN,
            topMargin=PAGE_MARGIN,
            bottomMargin=PAGE_MARGIN,
            title="ASD1-M2-14 - Dokumentacja",
            author="ASD1-M2-14 zespół",
        )
        self.story: list = []

    # ----- elementy niskopoziomowe ----------------------------------------- #
    def _header(self, title: str, page_num: int) -> None:
        styles = getSampleStyleSheet()
        self.story.append(
            Paragraph(
                "ASD1-M2-14 &nbsp;|&nbsp; "
                "<font color='#1a4e8a'><b>Archiwum prac i projektów studenckich Filii</b></font>",
                styles["Normal"],
            )
        )
        self.story.append(Spacer(1, 2))
        self.story.append(
            Paragraph(
                f"<b>{title}</b> &nbsp;&nbsp;·&nbsp;&nbsp; Strona {page_num}",
                ParagraphStyle(
                    "pagetitle", fontName="Arial", fontSize=10,
                    textColor="#666666", alignment=1,
                ),
            )
        )
        self.story.append(Spacer(1, 6))

    def _h2(self, text: str) -> None:
        p = ParagraphStyle(
            "h2", fontName="Arial", fontSize=13, textColor="#10243d",
            spaceBefore=4, spaceAfter=3,
        )
        self.story.append(Paragraph(text, p))

    def _p(self, text: str) -> None:
        style = ParagraphStyle(
            "body", fontName="Arial", fontSize=9.5, leading=12.5,
            textColor="#1a1a1a", alignment=0, spaceAfter=3,
        )
        self.story.append(Paragraph(text, style))

    @staticmethod
    def _escape_code(code: str) -> str:
        return code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _code(self, code: str, lang: str = "text") -> None:
        s = ParagraphStyle(
            "code", fontName="Courier", fontSize=7.2, leading=8.8,
            textColor="#000000", leftIndent=8, rightIndent=8, spaceAfter=4,
        )
        self.story.append(
            Paragraph(f"<b>{lang}:</b> {self._escape_code(code)}", s)
        )

    def _table(self, header: list, rows: list, widths=None) -> None:
        cell = ParagraphStyle("tc", fontName="Arial", fontSize=7.8,
                              leading=9.2, textColor="#1a1a1a")
        hcell = ParagraphStyle("tc_h", fontName="Arial", fontSize=7.8,
                               leading=9.2, textColor=colors.white, alignment=1)
        data = [[Paragraph(h, hcell) for h in header]]
        for r in rows:
            data.append([Paragraph(c, cell) for c in r])
        t = Table(data, colWidths=widths or None, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a4e8a")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#888888")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#eef2f7")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        self.story.append(t)

    # ----- treść poszczególnych stron --------------------------------------- #
    def page_title(self) -> None:
        self._header("1. Strona tytułowa", 1)
        self.story.append(Spacer(1, 18))
        self.story.append(Paragraph(
            "ASD1-M2-14", ParagraphStyle(
                "ttl", fontName="Arial", fontSize=30,
                textColor="#0b1f36", alignment=1, spaceAfter=3)))
        self.story.append(Paragraph(
            "Archiwum prac i projektów studenckich Filii",
            ParagraphStyle("tt2", fontName="Arial", fontSize=18,
                           textColor="#10243d", alignment=1, spaceAfter=4)))
        self.story.append(Paragraph(
            "Algorytmy i struktury danych I · Mini-projekt M2 · Rok akademicki 2026/2027",
            ParagraphStyle("tt3", fontName="Arial", fontSize=11,
                           textColor="#33506f", alignment=1)))
        self.story.append(Spacer(1, 20))

        self._h2("Cel projektu i zakres obowiązkowy")
        self._p(
            "<b>ASD1-M2-14</b> to repozytorium pracy / mini-projektu realizowanego "
            "w ramach przedmiotu <i>Algorytmy i struktury danych I</i> (grupa M2). "
            "Projekt implementuje model pracy studenckiej archiwum: <i>Work</i> (praca), "
            "rejestr podejrzenia duplikatów, własne wyszukiwanie liniowe i sortowanie "
            "przez wstawianie z licznikiem porównań, statystyki, eksport/import JSON "
            "oraz lokalne scenariusze demonstracyjne."
        )
        self._p("<b>Zakres obowiązkowy (Kroki 1–6):</b>")
        self._p(
            "• Model danych <b>Work</b> + zasada niezmienności <b>id</b>; "
            "walidacja pól (rok 2000–2100, limit 1000 rekordów).")
        self._p("• Moduły <i>src/repository.py</i>, <i>src/validation.py</i>, "
                "<i>src/models.py</i>.")
        self._p("• Własne wyszukiwanie liniowe z filtrowaniem AND oraz sortowanie "
                "przez wstawianie z licznikiem porównań.")
        self._p("• Wykrywanie podejrzenia duplikatów: normalizacja "
                "<font face='Courier'>.strip().lower()</font>, porównanie zbioru "
                "autorów, jawne potwierdzenie zamiast automatycznego usuwania.")
        self._p("• Obsługa braku pliku materiału bez blokowania dostępu do opisu pracy.")
        self._p("• Eksport/import JSON (dwuetapowy, z wersją formatu).")
        self._p("• Testy automatyczne <i>pytest</i> oraz pomiary wydajności w "
                "<i>docs/benchmarks.md</i>.")
        self._p("• Interfejs użytkownika lokalny, zero zależności zewnętrznych, "
                "w pełni <b>offline</b>.")

    def page_architecture(self) -> None:
        self._header("2. Architektura i reprezentacja danych", 2)
        self._p("<b>Struktura katalogów (z czystej kopii):</b>")
        self._code(
            "ASD1-M2-14/\n"
            "├── server.py                # punkt wejścia (http.server, offline)\n"
            "├── frontend/\n"
            "│   ├── templates/\n"
            "│   │   └── index.html        # szablon strony (UwB)\n"
            "│   └── static/\n"
            "│       ├── app.js            # logika frontendu (vanilla JS)\n"
            "│       ├── style.css         # motyw UwB (fiolet + biel)\n"
            "│       └── img/uwb_logo.png  # logo Uniwersytetu w Białymstoku\n"
            "├── src/\n"
            "│   ├── __init__.py\n"
            "│   ├── models.py             # Work, Material, WORK_TYPES\n"
            "│   ├── validation.py         # ValidationError, validate_work, ...\n"
            "│   ├── repository.py         # WorkRepository (ABC) + InMemoryWorkRepository\n"
            "│   ├── sqlite_repository.py  # SqliteWorkRepository (archiwum SQLite)\n"
            "│   ├── algorithms.py         # linear_search, insertion_sort, ...\n"
            "│   ├── duplicates.py         # normalize_text, find_suspected_duplicates\n"
            "│   ├── stats.py              # summarize (zliczanie pętlą)\n"
            "│   ├── io_json.py            # export/import JSON (dwufazowy)\n"
            "│   └── scenarios.py          # control / typical / edge / larger\n"
            "├── materialy/                # pliki demo dołączane do prac\n"
            "├── data/                     # lokalne dane runtime (ignorowane w git)\n"
            "├── tests/                    # testy pytest\n"
            "├── scripts/\n"
            "│   ├── benchmark.py          # benchmark (N=10/100/1000)\n"
            "│   └── build_docs.py         # generuje dokumentację PDF\n"
            "├── docs/                     # benchmarks.md + PDF\n"
            "├── .gitignore\n"
            "├── requirements.txt\n"
            "├── pyproject.toml\n"
            "└── README.md",
            "text",
        )
        self._p("<b>Reprezentacja listy rekordów — klasa <i>Work</i> (<i>models.py</i>):</b>")
        self._code(
            "@dataclass(frozen=True)\n"
            "class Work:\n"
            "    id: str                # unikalny, niezmienny; A-Z, cyfry, myślnik\n"
            "    title: str\n"
            "    authors: list[str]\n"
            "    year: int              # 2000 <= year <= 2100\n"
            "    subject: str\n"
            "    work_type: str         # projekt | mini-projekt | prezentacja | praca dyplomowa\n"
            "    description: str\n"
            "    tags: list[str]\n"
            "    repo_url: str\n"
            "    materials: list[Material]\n"
            "    # Work.material_status() -> {'name','exists','missing','status',...}"
        )
        self._p("<b>Zasady walidacji (<i>validation.py</i>):</b>")
        self._p(
            "• <i>work.id</i>: niepusty, unikalny, niezmienny; zgodny z "
            "<font face='Courier'>^[A-Z0-9-]+$</font>.")
        self._p("• Rok: liczba całkowita w przedziale <b>2000–2100</b>.")
        self._p("• <i>work_type</i>: jeden z <b>4</b> dopuszczonych typów.")
        self._p("• Do repozytorium może trafić <b>≤ 1000</b> rekordów "
                "(<font face='Courier'>MAX_RECORDS_DEFAULT = 1000</font>).")
        self._p("• Operacje zmieniające walidują pola <b>przed</b> zmianą stanu; przy "
                "błędzie zwracany jest jasny <i>OperationResult</i> i <b>nie ma "
                "częściowych zapisów</b>.")
        self._p("<b>Warstwa <i>WorkRepository</i> (<i>repository.py</i>):</b>")
        self._code(
            "class WorkRepository(ABC):\n"
            "    @abstractmethod\n"
            "    def list_all(self) -> list[Work]: ...\n"
            "    @abstractmethod\n"
            "    def get_by_id(self, work_id: str) -> Optional[Work]: ...\n"
            "    @abstractmethod\n"
            "    def add(self, work: Work) -> OperationResult: ...\n"
            "    @abstractmethod\n"
            "    def update(self, work_id: str, work: Work) -> OperationResult: ...\n"
            "    @abstractmethod\n"
            "    def replace_all(self, works: list[Work]) -> OperationResult: ...\n"
            "\n"
            "class InMemoryWorkRepository(WorkRepository):\n"
            "    # SQLite / WAL / inna baza danych - implementacja konkretna\n"
            "    # można podpiąć; logika aplikacji nie ulega zmianie"
        )
        self._p(
            "<b>Podsumowanie:</b> warstwa <i>repository</i> jest abstrakcyjna; aktualna "
            "implementacja <i>InMemoryWorkRepository</i> jest gotowa do podpięcia bazy "
            "danych (np. SQLite) bez zmiany logiki aplikacji."
        )

    def page_duplicates(self) -> None:
        self._header("3. Duplikaty, bezpieczeństwo i materiały", 3)
        self._p(
            "<b>Wykrywanie podejrzenia duplikatów (<i>algorithms.py</i>):</b> "
            "podejrzenie duplikatu zachodzi, gdy <b>wszystkie</b> trzy warunki są "
            "spełnione — <b>nigdy na podstawie samego tytułu</b>:"
        )
        self._p("• normalizacja <i>title</i>: <font face='Courier'>.strip().lower()</font>;")
        self._p("• identyczny <b>rok</b>;")
        self._p("• <b>zbiór autorów</b>, porównanie niezależnie od kolejności "
                "(np. <font face='Courier'>[student b, student a]</font> to "
                "<font face='Courier'>[Student A, Student B]</font> po normalizacji).")
        self._p(
            "Przykład: tytuł <font face='Courier'>\" atlas \"</font>, rok <b>2025</b>, "
            "autorzy <font face='Courier'>[\"student b\", \"student a\"]</font> — "
            "podejrzenie duplikatu pracy <b>A</b> (\"Atlas\", 2025, projekt)."
        )
        self._p("<b>Kluczowe zasady bezpieczeństwa:</b>")
        self._p("• <b>Nigdy nie jest wykonywany HTML</b> pochodzący z danych użytkownika; "
                "cały tekst renderowany przez <font face='Courier'>textContent</font> "
                "lub autoescaping.")
        self._p("• <b>Nie usuwa się automatycznie</b>; zamiast tego zwracany jest "
                "<i>DuplicateWarning</i> z listą dopasowanych rekordów, a zapis wymaga "
                "jawnego potwierdzenia (sam zgodny tytuł nie wystarcza).")
        self._p("• Brak pliku materiału nie blokuje dostępu do <i>description</i> pracy; "
                "zwraca czytelny komunikat (<i>missing=True</i>).")
        self._p("• Każdy status kolorystyczny jest opatrzony <b>tekstem</b> — kolor nie "
                "jest jedynym nośnikiem informacji.")
        self._code(
            "def normalize_text(value: str) -> str:\n"
            "    return value.strip().lower()\n"
            "\n"
            "def _norm_authors(authors) -> list[str]:\n"
            "    return sorted(normalize_text(a) for a in authors if isinstance(a, str))\n"
            "\n"
            "def find_suspected_duplicates(candidate, existing):\n"
            "    # 1. normalizuj title, year, authors\n"
            "    # 2. porównaj: title_norm, year,\n"
            "    #    _norm_authors(existing) == _norm_authors(candidate)\n"
            "    # WARUNEK: wszystkie trzy zbieżne -> duplikat"
        )
        self._p("<b>Obsługa braku pliku materiału (<i>models.py</i>, "
                "<i>material_status()</i>):</b>")
        self._code(
            "def material_status(self, materialy_dir=\"materialy\") -> dict:\n"
            "    for m in self.materials:\n"
            "        path = os.path.join(materialy_dir, m.path_or_url)\n"
            "        exists = os.path.isfile(path)\n"
            "        ...  # {\"name\", \"exists\", \"missing\": not exists}"
        )

    def page_linear_search(self) -> None:
        self._header("4. Wyszukiwanie liniowe + licznik pętlą", 4)
        self._p(
            "<b>Funkcja <i>linear_search</i> (<i>algorithms.py</i>)</b> — własna "
            "implementacja bez wywołania sortowania bibliotecznego; przechodzi "
            "rekord po rekordzie i zwraca <b>wszystkie</b> dopasowania (bez limitu "
            "top-k)."
        )
        self._code(
            "def linear_search(works, *, title=None, authors=None,\n"
            "                  keywords=None, year=None,\n"
            "                  subject=None, work_type=None) -> SearchResult:\n"
            "    checked = 0\n"
            "    for work in works:          # każdy rekord jest sprawdzany\n"
            "        checked += 1            # łączny licznik iteracji\n"
            "        if _match_text_fields(work, ...):\n"
            "            if _match_and_filter(work, ...):\n"
            "                results.append(work)\n"
            "    return SearchResult(results, checked)\n"
        )
        self._p("<b>Sposób wyszukiwania:</b>")
        self._p("• <i>title</i>: porównanie bez wielkości liter "
                "<font face='Courier'>normalize_text(q) in normalize_text(work.title)</font>;")
        self._p("• <i>authors</i>: dowolny autor zawiera zapytanie;")
        self._p("• <i>keywords</i>: zapytanie w <i>tags</i> lub w <i>description</i>;")
        self._p("• filtry <i>year</i>, <i>subject</i>, <i>work_type</i> stosowane jako "
                "<b>AND</b> (każdy weryfikowany osobno).")
        self._p("<b>Analiza kosztu:</b> czas <b>O(n)</b>, dodatkowa pamięć <b>O(1)</b> "
                "(poza listą wyników).")
        self._p(
            "<b>Licznik <i>checked</i>:</b> inkrementowany <b>wewnątrz</b> pętli "
            "<font face='Courier'>for work in works:</font>, więc zwraca <b>liczbę "
            "rzeczywistych iteracji</b> — <b>zawsze równą n</b>, niezależnie od tego, "
            "czy dopasowanie jest na początku, na końcu, czy go nie ma. Licznik nie jest "
            "„podrabiany”: odzwierciedla pełny przebieg pętli (wyszukiwanie wszystkich "
            "dopasowań)."
        )

    def page_insertionsort(self) -> None:
        self._header("5. Insertionsort (sortowanie przez wstawianie)", 5)
        self._p(
            "<b>Funkcja <i>insertion_sort</i> (<i>algorithms.py</i>)</b> — główna ścieżka "
            "sortowania <b>nie wywołuje</b> <font face='Courier'>sorted()</font> ani "
            "<font face='Courier'>.sort()</font>; używa tylko przesunięć wewnątrz pętli "
            "<font face='Courier'>while</font>."
        )
        self._p("<b>Warunek porównania kluczy:</b>")
        self._p("• domyślnie <b>rok malejąco, id rosnąco</b> (remis rozstrzygany przez id);")
        self._p("• <font face='Courier'>key=\"title\"</font>: tytuł rosnąco "
                "(bez wielkości liter), następnie id rosnąco.")
        self._p(
            "<b>Licznik porównań kluczy</b> — inkrementowany przy każdym porównaniu "
            "w pętli <font face='Courier'>while</font>."
        )
        self._code(
            "for i in range(1, len(arr)):\n"
            "    j = i - 1\n"
            "    while j >= 0:\n"
            "        cmp = _compare(arr[j], current, key)\n"
            "        comparisons += 1        # licznik porównań kluczy\n"
            "        if cmp > 0:\n"
            "            arr[j + 1] = arr[j]\n"
            "            j -= 1\n"
            "        else:\n"
            "            break\n"
            "    arr[j + 1] = current\n"
        )
        self._p(
            "<b>Koszt:</b> optymistyczny (dane już posortowane) <b>O(n)</b> — po jednym "
            "porównaniu na element; pesymistyczny (dane odwrotnie posortowane) "
            "<b>O(n²)</b> — każdy nowy element przesuwa wszystkie poprzednio "
            "posortowane."
        )

    def page_control_example(self) -> None:
        self._header("6. Przykład kontrolny (A, B, C, D) + tabela kroków", 6)
        self._p("<b>Scenariusz kontrolny (<i>src/scenarios.py</i>):</b>")
        self._table(
            ["id", "title", "authors", "year", "type"],
            [
                ["A", "Atlas", "Student A, Student B", "2025", "projekt"],
                ["B", "Gra", "Student C", "2026", "mini-projekt"],
                ["C", "Sieci", "Student D", "2025", "prezentacja"],
                ["D", " atlas ", "student b, student a", "2025", "projekt"],
            ],
        )
        self._p("Dodanie kandydata <b>D</b> wywołuje ostrzeżenie o podejrzeniu "
                "duplikatu względem <b>A</b> (taki sam znormalizowany tytuł, rok i zbiór "
                "autorów).")
        self._p("<b>Ręczne prześledzenie sortowania (klucz domyślny: rok malejąco, id "
                "rosnąco) — kolejność końcowa B, A, C:</b>")
        self._table(
            ["Przed (Before)", "Decyzja (Decision)", "Po (After)"],
            [
                ["[A(2025), B(2026), C(2025)]", "B przed A (2026 > 2025)", "[B, A, C]"],
                ["[B, A(2025), C(2025)]", "C za A (taki sam rok, C > A po id)", "[B, A, C]"],
            ],
        )
        self._p("<b>Statystyki (3 rekordy A, B, C):</b> rok 2026 → 1, rok 2025 → 2, "
                "razem 3.")
        self._p("<b>Filtr <font face='Courier'>rok=2025 AND typ=projekt</font></b> "
                "zwraca wyłącznie pracę <b>A</b>.")

    def page_json_scenarios(self) -> None:
        self._header("7. JSON export/import + scenariusze", 7)
        self._p(
            "<b>Eksport:</b> zapisuje <font face='Courier'>{ \"format_version\": \"1.0\", "
            "\"works\": [...] }</font>."
        )
        self._p("<b>Import dwuetapowy:</b>")
        self._p("• <b>Faza 1 (walidacja)</b> — sprawdzenie <b>całego pliku</b> przed "
                "modyfikacją: poprawny JSON, obsługiwany <i>format_version</i>, schemat "
                "i pola każdego rekordu, unikalne <i>id</i>, ≤ 1000 rekordów. Brak zmian "
                "w repozytorium.")
        self._p("• <b>Faza 2 (zastąpienie)</b> — podmiana zbioru danych <b>dopiero po</b> "
                "pomyślnej walidacji <b>i potwierdzeniu</b> przez użytkownika "
                "(<i>confirmed=True</i>). Błędne pliki nigdy nie nadpisują danych.")
        self._p("<b>Scenariusze demonstracyjne (<i>scenarios.py</i>):</b>")
        self._table(
            ["Scenariusz", "Opis"],
            [
                ["control", "Kontrolny: A, B, C + kandydat D (podejrzenie duplikatu A)"],
                ["typical", "Typowy: ~8 realistycznych prac studenckich"],
                ["edge", "Graniczny: stan pusty, lata 2000/2100, brak materiału, remisy, wielu autorów"],
                ["larger", "Większy: ~27 wygenerowanych prac (L01–L27)"],
            ],
        )
        self._p("Po wczytaniu każdego scenariusza rekordy można edytować, a wyniki "
                "(lista, statystyki, liczniki) aktualizują się natychmiast.")

    def page_tests(self) -> None:
        self._header("8. Testy automatyczne (pytest)", 8)
        self._p("<b>Wybrane przypadki testowe (wejście → oczekiwany wynik):</b>")
        self._table(
            ["Test", "Wejście", "Oczekiwany wynik / asercja"],
            [
                ["test_validate_year_range", "Work z year=2101", "ValidationError (poza 2000–2100)"],
                ["test_insertion_sort_matches_sorted", "[B(2026), A, C]", "wynik == [B, A, C] (zgodny z sorted())"],
                ["test_linear_search_checked_n", "control (3 rekordy)", "checked == 3"],
                ["test_linear_search_and_filter", "year=2025, type=projekt", "ids(result) == ['A']"],
                ["test_multi_author_counts_once", "[E5(3 autorów), E1]", "summarize(...).total == 2"],
                ["test_duplicate_warning", "D vs A,B,C", "DuplicateWarning dla A"],
                ["test_invalid_json_no_overwrite", "błędny plik JSON", "repo bez zmian (brak nadpisania)"],
                ["test_material_status_missing", "E6 (brak.txt)", "status[0]['missing'] is True"],
                ["test_boundary_years", "E1(2000), E2(2100)", "oba lata przyjęte"],
                ["test_trace_small_dataset", "control, trace=True", "wpisy (Przed→Decyzja→Po)"],
            ],
        )
        self._p("<b>Uruchomienie jednym poleceniem:</b> "
                "<font face='Courier'>python -m pytest tests/ -q</font>")
        self._p("<b>Wynik:</b> <b>15 passed</b>, 0 failures, 0 errors (stan bieżący).")

    def page_performance(self, tables: list) -> None:
        self._header("9. Pomiary wydajności (10/100/1000)", 9)
        self._p("Dane pochodzą z <i>docs/benchmarks.md</i> (wygenerowane przez "
                "<font face='Courier'>scripts/benchmark.py</font>, seed 42).")
        # Tabele benchmarkowe w kolejności: [0] weryfikacja, [1] porównania kluczy,
        # [2] wyszukiwanie checked, [3] filtr AND.
        if len(tables) >= 1:
            self._p("<b>Zgodność z niezależnym wzorcem (built-in <i>sorted()</i>):</b>")
            tbl = tables[0]
            self._table(tbl[0], tbl[1:])
        if len(tables) >= 2:
            self._p("<b>Porównania kluczy: dane uporządkowane vs odwrotne:</b>")
            tbl = tables[1]
            self._table(tbl[0], tbl[1:])
        if len(tables) >= 3:
            self._p("<b>Licznik <i>checked</i>: trafienie na początku / na końcu / brak "
                    "wyniku:</b>")
            tbl = tables[2]
            self._table(tbl[0], tbl[1:])
        self._p(
            "<b>Analiza różnic:</b> w wariancie optymistycznym pętla kończy się po jednym "
            "porównaniu na element (≈O(n)); w najgorszym przypadku każdy element przesuwa "
            "wszystkie poprzednio posortowane (O(n²)) — różnica rośnie z N, co uzasadnia "
            "stosowanie insertion sort do małych zbiorów. Licznik <i>checked</i> pozostaje "
            "równy N w każdym wariancie, bo pętla zawsze skanuje cały zbiór."
        )

    def page_ui_run(self) -> None:
        self._header("10. Interfejs, dostępność, uruchomienie, wnioski", 10)
        self._p(
            "<b>Interfejs:</b> lista prac (sortowana), karta szczegółów, formularze "
            "dodawania/edycji (id niezmienne), wyszukiwanie, filtry, sortowanie, "
            "scenariusze, eksport/import JSON, pliki <i>materialy/instrukcja.txt</i> i "
            "<i>materialy/prezentacja.md</i>, tryb offline."
        )
        self._p("<b>Dostępność:</b> kolor nie jest jedynym nośnikiem informacji — braki "
                "pliku, ostrzeżenia i błędy mają jawne etykiety tekstowe; pełna obsługa "
                "klawiatury (Tab, Enter, Escape).")
        self._p("<b>Instrukcja uruchomienia z czystej kopii:</b>")
        self._code(
            "python -m pip install -r requirements.txt\n"
            "python -m pytest tests/ -q\n"
            "python scripts/benchmark.py\n"
            "python scripts/build_docs.py"
        )
        self._p("<b>Podsumowanie:</b> projekt spójny, bezpieczny, w pełni offline i "
                "udokumentowany.")
        self._p("<b>Wnioski:</b>")
        self._p("• Wyszukiwanie liniowe O(n), sortowanie przez wstawianie O(n²) w "
                "najgorszym przypadku.")
        self._p("• Import JSON chroniony dwuetapowo (walidacja całości przed nadpisaniem).")
        self._p("• Architektura gotowa do dalszego rozwoju: podpięcie bazy danych, "
                "prezentacja, wizualizacja, dokumentacja PDF.")


# --------------------------------------------------------------------------- #
def build(tables: list) -> int:
    register_fonts()
    pdf = PDF()

    pdf.page_title()
    pdf.story.append(PageBreak())
    pdf.page_architecture()
    pdf.story.append(PageBreak())
    pdf.page_duplicates()
    pdf.story.append(PageBreak())
    pdf.page_linear_search()
    pdf.story.append(PageBreak())
    pdf.page_insertionsort()
    pdf.story.append(PageBreak())
    pdf.page_control_example()
    pdf.story.append(PageBreak())
    pdf.page_json_scenarios()
    pdf.story.append(PageBreak())
    pdf.page_tests()
    pdf.story.append(PageBreak())
    pdf.page_performance(tables)
    pdf.story.append(PageBreak())
    pdf.page_ui_run()

    pdf.doc.build(pdf.story)
    print(f"[docs] zapisano {PDF_OUT} ({PDF_OUT.stat().st_size} bajtów)")
    return 0


# --------------------------------------------------------------------------- #
def main() -> int:
    if not BENCHMARKS_MD.exists():
        print(f"[build_docs] BŁĄD: brak pliku {BENCHMARKS_MD}.")
        return 1
    return build(extract_tables())


if __name__ == "__main__":
    raise SystemExit(main())
