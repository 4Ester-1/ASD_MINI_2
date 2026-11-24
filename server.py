"""server.py — lokalny, w pełni offline interfejs WWW dla ASD1-M2-14.

Zero zależności zewnętrznych: stdlib ``http.server`` + czysty HTML/CSS/JS.

Uruchomienie:
    python server.py
a następnie otwórz http://127.0.0.1:8000

Stan przechowywany jest w dwóch repozytoriach:
 - archive (SqliteWorkRepository, trwałe archiwum SQLite),
 - sandbox (InMemoryWorkRepository, RAM; domyślny tryb demo/scenariuszy).

Flagi konfiguracyjne (zmienne środowiskowe — flagi funkcjonalne):
 - APP_ENABLE_SANDBOX  (domyślnie "true"; "false" wyłącza tryb piaskownicy),
 - APP_READ_ONLY       (domyślnie "false"; "true" blokuje operacje zmieniające).

Strażnicy backendowi (backend-enforced):
 - gdy APP_ENABLE_SANDBOX="false": /api/mode i /api/load_scenario/* → 403,
 - gdy APP_READ_ONLY="true":           add / edit / delete / import → 403,
   natomiast odczyt / wyszukiwanie / sortowanie / eksport pozostają aktywne.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.algorithms import insertion_sort, linear_search
from src.duplicates import find_suspected_duplicates
from src.io_json import apply_import, export_to_json, parse_and_validate
from src.models import Material, Work, WORK_TYPES
from src.repository import InMemoryWorkRepository, OperationResult
from src.scenarios import load_scenario
from src.sqlite_repository import SqliteWorkRepository
from src.stats import summarize
from src.validation import ValidationError

HOST = "127.0.0.1"
PORT = 8000

ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT / "frontend" / "templates"
STATIC_DIR = ROOT / "frontend" / "static"
MATERIALY_DIR = ROOT / "materialy"


# --------------------------------------------------------------------------- #
# Feature flags (env)
# --------------------------------------------------------------------------- #
def _env_bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


SANDBOX_ENABLED = _env_bool("APP_ENABLE_SANDBOX", "true")
READ_ONLY = _env_bool("APP_READ_ONLY", "false")

# --------------------------------------------------------------------------- #
# Repositories
# --------------------------------------------------------------------------- #
archive_repo = SqliteWorkRepository(str(ROOT / "data" / "archive.db"))
sandbox_repo = InMemoryWorkRepository()

ACTIVE_MODE = "sandbox" if SANDBOX_ENABLED else "archive"


def active_repo():
    return sandbox_repo if ACTIVE_MODE == "sandbox" else archive_repo


def repo_label() -> str:
    if ACTIVE_MODE == "sandbox":
        return "Tryb: Piaskownica (RAM)"
    return "Tryb: Archiwum (SQLite)"


SCENARIOS = {
    "control": "Przykład kontrolny (A, B, C + D)",
    "typical": "Typowy (~8 prac)",
    "edge": "Graniczny (lata 2000/2100, braki, remisy)",
    "larger": "Większy (~27 prac)",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _work_from_payload(data: dict) -> Work:
    materials = []
    for m in data.get("materials", []):
        materials.append(Material(name=m["name"], path_or_url=m["path_or_url"]))
    return Work(
        id=data["id"],
        title=data["title"],
        authors=list(data.get("authors", [])),
        year=data["year"],
        subject=data.get("subject", ""),
        work_type=data.get("work_type", "projekt"),
        description=data.get("description", ""),
        tags=list(data.get("tags", [])),
        repo_url=data.get("repo_url", ""),
        materials=materials,
    )


def _work_to_dict(w: Work) -> dict:
    d = w.to_dict()
    d["material_status"] = w.material_status(str(MATERIALY_DIR))
    return d


def _sort_key_from(value: str) -> str:
    return "title" if value == "title" else "default"


# --------------------------------------------------------------------------- #
# Request handler
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    server_version = "ASD1-M2-14/1.0"

    def log_message(self, fmt, *args):
        pass

    # -- plumbing ----------------------------------------------------------- #
    def _send(self, status, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    # -- routing ------------------------------------------------------------ #
    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)

        if route in ("/", "/index.html"):
            return self._serve_template(TEMPLATES_DIR / "index.html")
        if route == "/style.css":
            return self._serve_static("style.css")
        if route.startswith("/static/"):
            return self._serve_static(route[len("/static/"):])

        if route == "/api/config":
            return self._respond_json({
                "sandbox_enabled": SANDBOX_ENABLED,
                "read_only": READ_ONLY,
                "active_mode": ACTIVE_MODE,
                "mode_label": repo_label(),
            })

        if route == "/api/works":
            sort_key = _sort_key_from(qs.get("sort", ["default"])[0])
            result = insertion_sort(active_repo().list_all(), key=sort_key)
            payload = {
                "works": [_work_to_dict(w) for w in result.sorted_works],
                "comparisons": result.comparisons,
            }
            return self._respond_json(payload)

        if route == "/api/search":
            res = linear_search(
                active_repo().list_all(),
                title=qs.get("title", [""])[0] or None,
                authors=qs.get("authors", [""])[0] or None,
                keywords=qs.get("keywords", [""])[0].split(",") if qs.get("keywords") else None,
                year=int(qs["year"][0]) if qs.get("year", [""])[0] else None,
                subject=qs.get("subject", [""])[0] or None,
                work_type=qs.get("work_type", [""])[0] or None,
            )
            return self._respond_json({
                "works": [_work_to_dict(w) for w in res.works],
                "checked": res.checked,
            })

        if route == "/api/trace":
            sort_key = _sort_key_from(qs.get("sort", ["default"])[0])
            result = insertion_sort(active_repo().list_all(), key=sort_key, trace=True)
            return self._respond_json({
                "comparisons": result.comparisons,
                "trace": [list(t) for t in result.trace],
                "sorted_ids": [w.id for w in result.sorted_works],
            })

        if route == "/api/stats":
            return self._respond_json(summarize(active_repo().list_all()).to_dict())

        if route == "/api/scenarios":
            if SANDBOX_ENABLED:
                return self._respond_json({"scenarios": SCENARIOS})
            return self._respond_json({"scenarios": {}})

        if route == "/api/export":
            export_to_json(active_repo().list_all(), str(ROOT / "data" / "export.json"))
            payload = {
                "format_version": "1.0",
                "works": [w.to_dict() for w in active_repo().list_all()],
            }
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            extra = {"Content-Disposition": 'attachment; filename="archiwum_export.json"'}
            return self._send(200, body, "application/json; charset=utf-8", extra)

        if route.startswith("/api/material/"):
            return self._serve_material(route[len("/api/material/"):])

        return self._send(404, b'{"error": "not found"}', "application/json")

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path
        data = self._read_body()

        if route == "/api/mode":
            if not SANDBOX_ENABLED:
                return self._respond_json(
                    {"ok": False, "error": "sandbox disabled by server policy"}, 403
                )
            mode = data.get("mode", "")
            if mode not in ("sandbox", "archive"):
                return self._respond_json(
                    {"ok": False, "error": "mode must be 'sandbox' or 'archive'"}, 400
                )
            global ACTIVE_MODE
            ACTIVE_MODE = mode
            return self._respond_json({"ok": True, "active_mode": ACTIVE_MODE,
                                       "mode_label": repo_label()})

        if route == "/api/add":
            return self._handle_add(data, None)
        if route.startswith("/api/edit/"):
            return self._handle_add(data, route[len("/api/edit/"):])
        if route.startswith("/api/load_scenario/"):
            return self._handle_load_scenario(route[len("/api/load_scenario/"):])
        if route == "/api/import":
            return self._handle_import(data)
        if route == "/api/import/apply":
            return self._handle_import_apply(data)

        return self._send(404, b'{"error": "not found"}', "application/json")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route.startswith("/api/delete/"):
            return self._handle_delete(route[len("/api/delete/"):])

        return self._send(404, b'{"error": "not found"}', "application/json")

    # -- specific handlers -------------------------------------------------- #
    def _respond_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _serve_template(self, path: Path):
        if not path.is_file():
            return self._respond_json({"error": "template not found"}, 404)
        self._send(200, path.read_bytes(), "text/html; charset=utf-8")

    def _serve_static(self, rel: str):
        # Serve under frontend/static/, never above it (path traversal guard).
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR)):
            return self._respond_json({"error": "forbidden"}, 403)
        if not target.is_file():
            return self._respond_json({"error": "not found", "missing": True}, 404)
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".ico": "image/x-icon",
            ".json": "application/json; charset=utf-8",
        }.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def _serve_material(self, rel: str):
        target = (MATERIALY_DIR / rel).resolve()
        if not str(target).startswith(str(MATERIALY_DIR.resolve())):
            return self._respond_json({"error": "forbidden"}, 403)
        if not target.is_file():
            return self._respond_json({"error": "Brak pliku materiału", "missing": True}, 404)
        self._send(200, target.read_bytes(), "text/plain; charset=utf-8")

    def _handle_add(self, data: dict, edit_id: str | None):
        if READ_ONLY:
            return self._respond_json({"ok": False, "error": "read-only mode"}, 403)

        try:
            if edit_id is not None:
                if "id" in data and data["id"] != edit_id:
                    data = dict(data)
                    data["id"] = edit_id
                work = _work_from_payload(data)
                work = Work(id=edit_id, title=work.title, authors=work.authors,
                            year=work.year, subject=work.subject,
                            work_type=work.work_type, description=work.description,
                            tags=work.tags, repo_url=work.repo_url,
                            materials=work.materials)
            else:
                work = _work_from_payload(data)
        except Exception as exc:
            return self._respond_json({"ok": False, "error": str(exc)}, 400)

        others = [w for w in active_repo().list_all() if w.id != work.id]
        warning = find_suspected_duplicates(work, others)

        confirmed = bool(data.get("confirmed", False))
        if warning.is_suspected and not confirmed:
            return self._respond_json({
                "ok": False,
                "duplicate": True,
                "matches": [w.id for w in warning.matches],
                "message": "Podejrzenie duplikatu — potwierdź, aby zapisać.",
            }, 409)

        if edit_id is not None:
            result = active_repo().update(edit_id, work)
        else:
            result = active_repo().add(work)
        if result.success:
            return self._respond_json({"ok": True, "work": _work_to_dict(work)})
        return self._respond_json({"ok": False, "error": result.reason}, 400)

    def _handle_delete(self, work_id: str):
        if READ_ONLY:
            return self._respond_json({"ok": False, "error": "read-only mode"}, 403)
        deleted = active_repo().delete(work_id)
        if deleted:
            return self._respond_json({"ok": True, "deleted": work_id})
        return self._respond_json({"ok": False, "error": "not found"}, 404)

    def _handle_load_scenario(self, name: str):
        # Scenarios always load into the sandbox to protect the archive.
        if not SANDBOX_ENABLED:
            return self._respond_json(
                {"ok": False, "error": "sandbox disabled by server policy"}, 403
            )
        if name not in SCENARIOS:
            return self._respond_json({"ok": False, "error": f"unknown scenario {name!r}"}, 404)
        works = load_scenario(name)
        result = sandbox_repo.replace_all(works)
        if not result.success:
            return self._respond_json({"ok": False, "error": result.reason}, 400)
        global ACTIVE_MODE
        ACTIVE_MODE = "sandbox"
        return self._respond_json({"ok": True, "count": len(works), "mode": "sandbox"})

    def _handle_import(self, data: dict):
        if READ_ONLY:
            return self._respond_json({"ok": False, "error": "read-only mode"}, 403)
        path = data.get("path")
        if not path:
            return self._respond_json({"ok": False, "error": "missing 'path'"}, 400)
        ok, records, reason = parse_and_validate(path)
        if not ok:
            return self._respond_json({"ok": False, "error": reason,
                                       "current_count": len(active_repo().list_all())}, 400)
        return self._respond_json({
            "ok": True,
            "summary": f"Poprawny plik: {len(records)} rekordów gotowych do importu.",
            "record_count": len(records),
            "stage": "confirm",
        })

    def _handle_import_apply(self, data: dict):
        if READ_ONLY:
            return self._respond_json({"ok": False, "error": "read-only mode"}, 403)
        path = data.get("path")
        confirmed = bool(data.get("confirmed", False))
        if not path:
            return self._respond_json({"ok": False, "error": "missing 'path'"}, 400)
        ok, records, reason = parse_and_validate(path)
        if not ok:
            return self._respond_json({"ok": False, "error": reason}, 400)
        ok2, reason2 = apply_import(active_repo(), records, confirmed=confirmed)
        if not ok2:
            return self._respond_json({"ok": False, "error": reason2}, 400)
        return self._respond_json({"ok": True, "count": len(active_repo().list_all())})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ASD1-M2-14 UI: http://{HOST}:{PORT}  (Ctrl+C to stop)")
    print(f"  sandbox: {'enabled' if SANDBOX_ENABLED else 'DISABLED'}  |  "
          f"read-only: {'yes' if READ_ONLY else 'no'}  |  active: {ACTIVE_MODE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
