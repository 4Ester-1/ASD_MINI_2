"""Walidacja pól modelu domenowego (reguły ASD1-M2-14).

Zawiera klasę ``ValidationError`` oraz funkcje ``validate_work``,
``validate_material`` i ``validate_work_list``. Reguły:

  * ``work.id``  — niepusty, zgodny z ``^[A-Z0-9-]+$`` (wielkie litery, cyfry, myślnik);
  * ``work.year`` — liczba całkowita w przedziale 2000–2100;
  * ``work.work_type`` — jedna z dopuszczonych wartości ``WORK_TYPES``;
  * pola tekstowe/tagi/autorzy — poprawne typy i niepuste wartości.

Każda operacja zmieniająca stan (w repozytoriach ``InMemory`` / ``SQLite``)
wywołuje te funkcje **przed** zapisem, dzięki czemu nie ma częściowych zapisów.
"""

from __future__ import annotations

import re
from dataclasses import is_dataclass
from typing import List

from .models import WORK_TYPES

__all__ = [
    "ValidationError",
    "validate_work",
    "validate_material",
    "validate_work_list",
]

_ID_PATTERN = re.compile(r"^[A-Z0-9-]+$")


class ValidationError(Exception):
    """Raised when a value does not satisfy a domain rule."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _non_empty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _list_of_str(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_material(material: "Material") -> None:
    if not is_dataclass(material):
        raise ValidationError("material must be a Material instance")
    if not _non_empty_str(material.name):
        raise ValidationError("material.name must be a non-empty string")
    if not _non_empty_str(material.path_or_url):
        raise ValidationError("material.path_or_url must be a non-empty string")

    url = material.path_or_url
    # Relative path (no scheme) or http(s) URL.
    if not (url.startswith(("https://", "http://")) or "://" not in url):
        raise ValidationError(
            "material.path_or_url must be a relative path or an http(s) URL"
        )


def validate_work_list(works: List["Work"]) -> None:
    if not isinstance(works, list):
        raise ValidationError("works must be a list of Work instances")
    for index, work in enumerate(works):
        try:
            validate_work(work)
        except ValidationError as exc:
            raise ValidationError(f"works[{index}]: {exc.reason}") from exc


def validate_work(work: "Work") -> None:
    if not is_dataclass(work):
        raise ValidationError("work must be a Work instance")

    if not _non_empty_str(work.id):
        raise ValidationError("work.id must be a non-empty string")
    if not _ID_PATTERN.fullmatch(work.id):
        raise ValidationError("work.id may only contain A-Z, digits and hyphen")

    if not _non_empty_str(work.title):
        raise ValidationError("work.title must be a non-empty string")

    if not _list_of_str(work.authors):
        raise ValidationError("work.authors must be a list of strings")
    for index, author in enumerate(work.authors):
        if not _non_empty_str(author):
            raise ValidationError(f"work.authors[{index}] must be a non-empty string")

    if not isinstance(work.year, int) or isinstance(work.year, bool):
        raise ValidationError("work.year must be an integer")
    if not (2000 <= work.year <= 2100):
        raise ValidationError("work.year must be in range 2000-2100")

    if not _non_empty_str(work.subject):
        raise ValidationError("work.subject must be a non-empty string")

    if work.work_type not in WORK_TYPES:
        raise ValidationError(
            "work.work_type must be one of: " + ", ".join(sorted(WORK_TYPES))
        )

    if not _non_empty_str(work.description):
        raise ValidationError("work.description must be a non-empty string")

    if not _list_of_str(work.tags):
        raise ValidationError("work.tags must be a list of strings")
    for index, tag in enumerate(work.tags):
        if not _non_empty_str(tag):
            raise ValidationError(f"work.tags[{index}] must be a non-empty string")

    if not _non_empty_str(work.repo_url):
        raise ValidationError("work.repo_url must be a non-empty string")

    if not isinstance(work.materials, list):
        raise ValidationError("work.materials must be a list of Material instances")
    for index, material in enumerate(work.materials):
        if not is_dataclass(material):
            raise ValidationError(f"work.materials[{index}] must be a Material instance")
        validate_material(material)
