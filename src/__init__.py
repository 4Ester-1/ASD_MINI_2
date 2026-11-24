"""ASD1-M2-14 - Archiwum prac i projektów studenckich Filii.

Publiczny interfejs całego projektu: model domenowy, walidacja pól, abstrakcja
repozytorium (w pamięci + SQLite), własne algorytmy ASD I (wyszukiwanie liniowe
i sortowanie przez wstawianie), wykrywanie duplikatów, statystyki, eksport /
import JSON oraz gotowe scenariusze demonstracyjne.

Importowanie ``from src import ...`` daje dostęp do wszystkich publicznych
symboli z wyżej wymienionych modułów; ``server.py`` i testy korzystają
z tego pojedynczego punktu wejścia.
"""

from .models import Material, Work, WORK_TYPES
from .repository import (
    InMemoryWorkRepository,
    OperationResult,
    WorkRepository,
)
from .sqlite_repository import SqliteWorkRepository
from .validation import ValidationError
from .algorithms import (
    SearchResult,
    InsertionSortResult,
    linear_search,
    insertion_sort,
    normalize_text,
)
from .duplicates import (
    DuplicateWarning,
    find_suspected_duplicates,
)
from .stats import Stats, summarize
from .io_json import (
    FORMAT_VERSION,
    export_to_json,
    parse_and_validate,
    apply_import,
)

__all__ = [
    # models
    "Material",
    "Work",
    "WORK_TYPES",
    # validation
    "ValidationError",
    # repository
    "WorkRepository",
    "InMemoryWorkRepository",
    "SqliteWorkRepository",
    "OperationResult",
    # algorithms
    "SearchResult",
    "InsertionSortResult",
    "linear_search",
    "insertion_sort",
    "normalize_text",
    # duplicates
    "DuplicateWarning",
    "find_suspected_duplicates",
    # stats
    "Stats",
    "summarize",
    # io_json
    "FORMAT_VERSION",
    "export_to_json",
    "parse_and_validate",
    "apply_import",
]
