"""Verification of the UI redesign fixes (bugs 1, 2, 3).

Runs against the live server.py handler and the static files on disk.
"""
import re
import subprocess
import sys
import urllib.request

import pytest

ROOT = "/d/PRoj_mini2/ASD1-M2-14"
SERVER_URL = "http://127.0.0.1:8000"


def _get(path):
    with urllib.request.urlopen(SERVER_URL + path, timeout=5) as r:
        return r.status, r.read(), dict(r.headers)


def test_root_returns_200_and_has_uwb_logo_and_css_js():
    status, body, headers = _get("/")
    assert status == 200
    html = body.decode("utf-8", errors="replace")

    # UwB logo (official, no old purple square icon)
    assert 'src="/static/img/uwb_logo.png"' in html
    # Old purple square SVG must NOT be in the header (bug #3 fixed)
    assert "logo-emblem" not in html
    assert 'viewBox="0 0 128 128"' not in html  # no inline emblem

    # Links to CSS + JS
    assert 'href="/static/style.css?v=2"' in html
    assert 'src="/static/app.js?v=2"' in html

    # ROOT CAUSE: the script MUST be deferred so it runs after the DOM is
    # parsed. Without defer, the top-level `$("#btn-search").onclick = …`
    # wiring runs before <body> exists and throws
    # `TypeError: Cannot set properties of null`, killing every section.
    assert 'src="/static/app.js?v=2" defer' in html


def test_sort_select_has_min_width_rule():
    css = _get("/static/style.css?v=2")[1].decode("utf-8", errors="replace")
    assert "min-width: 240px" in css


def test_static_style_css_returns_200_with_text_css_and_large():
    status, body, headers = _get("/static/style.css?v=2")
    ctype = str(headers.get("Content-Type", ""))
    assert status == 200
    assert "text/css" in ctype
    assert len(body) > 2000
    # Font family and UwB palette present
    assert "Segoe UI" in body.decode("utf-8", errors="replace")
    assert "4B236E" in body.decode("utf-8", errors="replace")


def test_static_app_js_returns_200_javascript():
    status, body, headers = _get("/static/app.js?v=2")
    ctype = str(headers.get("Content-Type", ""))
    assert status == 200
    assert "javascript" in ctype
    # Must include the fixed #sort-select handler
    assert "#sort-select" in body.decode("utf-8", errors="replace")
    # Must include the scenario renderer
    assert "renderScenarios" in body.decode("utf-8", errors="replace")


def test_dom_ids_in_js_are_all_present_in_html():
    html = _get("/")[1].decode("utf-8", errors="replace")
    js = _get("/static/app.js?v=2")[1].decode("utf-8", errors="replace")

    html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_-]+)["\']', html))
    js_refs = set(re.findall(r'\$\(\s*["\']([^"\']+)["\']\s*\)', js))
    js_refs |= set(re.findall(r'getElementById\(\s*["\']([^"\']+)["\']\s*\)', js))
    js_refs = {i.lstrip("#") for i in js_refs}

    missing = js_refs - html_ids
    assert not missing, f"JS references IDs missing from HTML: {missing}"


def test_page_loads_without_null_dom_errors():
    """Fetch the page; confirm every ID JS references exists and section
    containers are present so the renderer can populate them without a
    null reference at runtime (bug #2)."""
    status, body, _ = _get("/")
    assert status == 200
    html = body.decode("utf-8", errors="replace")

    # Section containers present on initial render
    for selector, label in [
        ("scenario-buttons", "Scenariusze container"),
        ("q-type", "work_type filter select"),
        ("sort-select", "Sort dropdown (bug #2)"),
        ("metrics", "live metrics container"),
        ("trace-wrap", "trace container"),
        ("trace-table", "trace table"),
        ("work-list", "works list container"),
        ("list-count", "works count badge"),
    ]:
        assert selector in html, f"missing {label} in HTML: #{selector}"

    # No stray old purple square emblem SVG in header
    assert "logo-emblem" not in html

    # All IDs JS references exist in the HTML
    js = _get("/static/app.js?v=2")[1].decode("utf-8", errors="replace")
    js_refs = set(re.findall(r'\$\(\s*["\']([^"\']+)["\']\s*\)', js))
    js_refs |= set(re.findall(r'getElementById\(\s*["\']([^"\']+)["\']\s*\)', js))
    js_refs = {i.lstrip("#") for i in js_refs}
    html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_-]+)["\']', html))
    missing = js_refs - html_ids
    assert not missing, f"JS references IDs missing from HTML: {missing}"


def _get_json(path):
    status, body, _ = _get(path)
    assert status == 200, status
    return body.decode("utf-8", errors="replace")


def test_scenarios_render_on_page_load():
    # The JS renderer reads scenarios from the API and paints 4 buttons into
    # #scenario-buttons. Confirm the container + renderer both exist, and the
    # API returns exactly the 4 expected scenarios.
    status, body, _ = _get("/")
    assert status == 200, status
    html = body.decode("utf-8", errors="replace")
    assert "scenario-buttons" in html
    assert "renderScenarios" in _get("/static/app.js?v=2")[1].decode()

    scenarios = _get_json("/api/scenarios")
    import json as _json
    scenarios = _json.loads(scenarios)
    assert len(scenarios["scenarios"]) == 4
    assert set(scenarios["scenarios"].keys()) == {"control", "typical", "edge", "larger"}


def test_page_includes_uwb_breadcrumb_and_footer():
    status, body, _ = _get("/")
    assert status == 200
    html = body.decode("utf-8", errors="replace")
    assert "Uniwersytet w Białymstoku" in html
    assert "Dorobek Filii" in html
    assert "Strona główna" in html
    assert "Tryb lokalny offline" in html


def test_server_serves_all_static_mime_types():
    cases = {
        "/static/style.css?v=2": "text/css",
        "/static/app.js?v=2": "javascript",
        "/static/img/uwb_logo.png": "image/png",
    }
    for path, expect in cases.items():
        status, body, headers = _get(path)
        ctype = str(headers.get("Content-Type", ""))
        assert status == 200, f"{path} not 200: {status}"
        assert expect in ctype, f"{path}: {ctype}"


def test_escalation_that_original_page_rendering_history_was_purple_buttons():
    # Regression guard: no leftover plain-gray default buttons in the new CSS.
    status, body, _ = _get("/static/style.css?v=2")
    css = body.decode("utf-8", errors="replace")
    # New palette: deep purple #4B236E on #F8F7FA bg
    assert "#4B236E" in css
    assert "#F8F7FA" in css
    # Old default gray button (#eef2f7) removed
    assert "#eef2f7" not in css
