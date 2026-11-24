"""Model domenowy archiwum ASD1-M2-14.

Definiuje dwa obiekty wartościowe (immutable dataclasses z ``frozen=True``):
``Work`` (praca studencka) i ``Material`` (załączony plik/materiał) oraz zbiór
dopuszczalnych typów prac ``WORK_TYPES``.

Moduł ten jest fundamentem całego projektu — pozostałe moduły (walidacja,
repozytoria, algorytmy, statystyki, JSON, scenariusze) operują wyłącznie na
instancjach ``Work`` / ``Material``. Serializacja ``to_dict`` / ``from_dict``
jest używana przez warstwę eksportu/importu JSON (``src/io_json.py``), a
``Work.material_status`` informuje interfejs o braku pliku materiału.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ["Work", "Material", "WORK_TYPES"]

# Polish course terminology for the kind of work.
WORK_TYPES = frozenset(
    {
        "mini-projekt",
        "projekt",
        "prezentacja",
        "praca dyplomowa",
    }
)

# Id examples use uppercase letters, digits and hyphen.
_ID_PATTERN = re.compile(r"^[A-Z0-9-]+$")


@dataclass(frozen=True)
class Material:
    """A single attached material/file of a work."""

    name: str
    path_or_url: str

    def __post_init__(self) -> None:
        from .validation import validate_material

        validate_material(self)

    def to_dict(self) -> dict:
        """Serialize this material to a plain dict for JSON."""
        return {
            "name": self.name,
            "path_or_url": self.path_or_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        """Build a validated Material from a plain dict (used by JSON import)."""
        if not isinstance(data, dict):
            from .validation import ValidationError

            raise ValidationError("material must be a JSON object")
        return cls(
            name=data["name"],
            path_or_url=data["path_or_url"],
        )


@dataclass(frozen=True)
class Work:
    """A student work stored in the archive."""

    id: str
    title: str
    authors: List[str]
    year: int
    subject: str
    work_type: str
    description: str
    tags: List[str]
    repo_url: str
    materials: List[Material]

    def __post_init__(self) -> None:
        from .validation import validate_work

        validate_work(self)

    def to_dict(self) -> dict:
        """Serialize this work (and its materials) to a plain dict for JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "subject": self.subject,
            "work_type": self.work_type,
            "description": self.description,
            "tags": list(self.tags),
            "repo_url": self.repo_url,
            "materials": [m.to_dict() for m in self.materials],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Work":
        """Build a validated Work from a plain dict (used by JSON import)."""
        if not isinstance(data, dict):
            from .validation import ValidationError

            raise ValidationError("work must be a JSON object")

        def require(key: str) -> object:
            if key not in data:
                raise ValidationError(f"missing required field: {key}")
            return data[key]

        materials = data.get("materials", [])
        if not isinstance(materials, list):
            raise ValidationError("work.materials must be a list")

        material_objects = []
        for index, mat in enumerate(materials):
            if not isinstance(mat, dict):
                raise ValidationError(f"work.materials[{index}] must be an object")
            material_objects.append(Material.from_dict(mat))

        return cls(
            id=require("id"),
            title=require("title"),
            authors=require("authors"),
            year=require("year"),
            subject=require("subject"),
            work_type=require("work_type"),
            description=require("description"),
            tags=data.get("tags", []),
            repo_url=require("repo_url"),
            materials=material_objects,
        )

    def material_status(self, materialy_dir: str = "materialy") -> dict:
        """Per-material status.

        For each material, reports whether the local file exists under
        ``materialy_dir`` (relative to the given directory). Missing files
        produce a clear "missing" indicator so the work can still be read
        without raising an unhandled exception.
        """
        results = []
        for material in self.materials:
            path = os.path.join(materialy_dir, material.path_or_url)
            exists = os.path.isfile(path)
            results.append(
                {
                    "name": material.name,
                    "path_or_url": material.path_or_url,
                    "exists": exists,
                    "missing": not exists,
                    "status": "missing" if not exists else "present",
                    "message": (
                        f"Material '{material.name}' not found locally at {path!r}"
                        if not exists
                        else f"Material '{material.name}' found locally."
                    ),
                }
            )
        return results
