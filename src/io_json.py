"""Eksport JSON i konserwatywny dwufazowy import.

Eksport zapisuje ``{"format_version": "1.0", "works": [...]}``.

Import nigdy nie modyfikuje stanu repozytorium, dopóki **cały** plik nie
zostanie zwalidowany (``parse_and_validate``) **oraz** wywołujący jawnie nie
potwierdzi (``apply_import(..., confirmed=True)``). Błędny plik zawsze zwraca
jasny powód i nigdy nie nadpisuje istniejących rekordów. Warstwa ta jest
używana przez endpointy ``/api/export``, ``/api/import`` i ``/api/import/apply``
w ``server.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from .models import Work
from .repository import WorkRepository

__all__ = [
    "FORMAT_VERSION",
    "export_to_json",
    "validate_import_payload",
    "parse_and_validate",
    "apply_import",
]

FORMAT_VERSION = "1.0"
# Kept in sync with repository.MAX_RECORDS_DEFAULT.
MAX_RECORDS = 1000


def export_to_json(works, path) -> None:
    """Serialize ``works`` to ``path`` as JSON with a format version."""
    payload = {
        "format_version": FORMAT_VERSION,
        "works": [w.to_dict() for w in works],
    }
    p = Path(path)
    if p.parent != Path(""):
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def validate_import_payload(payload) -> Tuple[bool, str]:
    """Validate a decoded JSON payload IN FULL without touching any state.

    Returns ``(ok, reason)``; on any problem ``ok`` is ``False`` and ``reason``
    is a human-readable explanation."""
    if not isinstance(payload, dict):
        return False, "import payload must be a JSON object"

    version = payload.get("format_version")
    if version != FORMAT_VERSION:
        return False, f"unsupported format_version: {version!r} (expected '1.0')"

    works = payload.get("works")
    if not isinstance(works, list):
        return False, "'works' must be a list"

    if len(works) > MAX_RECORDS:
        return False, f"record count {len(works)} exceeds the limit of {MAX_RECORDS}"

    ids = []
    for i, item in enumerate(works):
        if not isinstance(item, dict):
            return False, f"works[{i}] must be a JSON object"
        if "id" not in item:
            return False, f"works[{i}] is missing its 'id' field"
        ids.append(item["id"])

    if len(ids) != len(set(ids)):
        return False, "duplicate work ids within the file"

    for i, item in enumerate(works):
        try:
            Work.from_dict(item)
        except Exception as exc:  # ValidationError and friends
            return False, f"works[{i}] invalid: {exc}"

    return True, ""


def parse_and_validate(file_path) -> Tuple[bool, List[Work], str]:
    """Read and validate the ENTIRE file before any mutation.

    Returns ``(success, records, error_reason)``. On failure ``success`` is
    ``False``, ``records`` is empty and ``error_reason`` explains why; the
    repository is never mutated."""
    try:
        raw = Path(file_path).read_text(encoding="utf-8")
        payload = json.loads(raw)
    except FileNotFoundError:
        return False, [], f"file not found: {file_path}"
    except json.JSONDecodeError as exc:
        return False, [], f"invalid JSON: {exc}"

    ok, reason = validate_import_payload(payload)
    if not ok:
        return False, [], reason

    records = [Work.from_dict(w) for w in payload["works"]]
    return True, records, ""


def apply_import(
    repository: WorkRepository, records: List[Work], confirmed: bool
) -> Tuple[bool, str]:
    """Replace the repository dataset ONLY with explicit confirmation.

    Without ``confirmed=True`` returns ``(False, reason)`` and nothing is
    overwritten."""
    if not confirmed:
        return False, "import rejected: no explicit confirmation given"

    result = repository.replace_all(records)
    if not result.success:
        return False, result.reason
    return True, ""
