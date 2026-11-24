"use strict";

/*
 * app.js — logika frontendu ASD1-M2-14 (czysty JS, offline, bez CDN).
 *
 * Odpowiada za: renderowanie listy prac, scenariuszy, śladu sortowania
 * (Przed → Decyzja → Po), metryk algorytmów, formularza dodawania/edycji
 * (z zachowaniem niezmienności id), okna potwierdzenia duplikatu ORAZ okna
 * potwierdzenia usunięcia, dwuetapowego importu JSON i przełącznika trybu
 * Archiwum (SQLite) / Piaskownica (RAM).
 *
 * Bezpieczeństwo: cały tekst użytkownika renderowany jest przez
 * ``textContent`` (nigdy ``innerHTML`` z danymi), więc żaden HTML z danych
 * nie jest wykonywany. Flagi z /api/config sterują ukrywaniem sekcji
 * (piaskownica wyłączona) oraz kontrolek mutacji (tryb tylko-do-odczytu).
 */

const $ = (sel) => document.querySelector(sel);

/* ------------------------------------------------------------------ */
/* State                                                              */
/* ------------------------------------------------------------------ */
let currentSort = "default";
let pendingForm = null;
let pendingEditId = null;
let importValidated = false;
let importPath = "";
let pendingDeleteId = null;
let config = { sandbox_enabled: true, read_only: false, active_mode: "sandbox" };
let readOnly = false;

/* ------------------------------------------------------------------ */
/* Plain-text rendering (safe: textContent, never innerHTML with data) */
/* ------------------------------------------------------------------ */
function textEl(tag, text) {
  const el = document.createElement(tag);
  el.textContent = text;
  return el;
}

/* ------------------------------------------------------------------ */
/* API helpers                                                        */
/* ------------------------------------------------------------------ */
async function apiGet(url) {
  const r = await fetch(url);
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await r.json().catch(() => ({}));
  return { status: r.status, data };
}

async function apiDelete(url) {
  const r = await fetch(url, { method: "DELETE" });
  const data = await r.json().catch(() => ({}));
  return { status: r.status, data };
}

/* ------------------------------------------------------------------ */
/* Rendering                                                          */
/* ------------------------------------------------------------------ */
function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }

function renderWorkList(works) {
  const ul = $("#work-list");
  clear(ul);
  $("#list-count").textContent = String(works.length) + " prac";
  for (const w of works) {
    const li = document.createElement("li");
    li.className = "work-item";
    li.tabIndex = 0;
    li.setAttribute("role", "button");

    const title = textEl("span", w.title);
    title.className = "work-title";

    const meta = textEl("span", [
      w.id, String(w.year), w.work_type, w.subject,
      w.authors.join(", "),
    ].filter(Boolean).join(" \u00b7 "));
    meta.className = "work-meta";

    const btn = document.createElement("button");
    btn.className = "btn btn-secondary btn-small";
    btn.textContent = "Poka\u017c szczeg\u00f3\u0142y";
    btn.setAttribute("aria-label", "Poka\u017c szczeg\u00f3\u0142y pracy " + w.title);
    btn.onclick = (e) => { e.stopPropagation(); showDetail(w); };

    li.onclick = () => showDetail(w);
    li.onkeydown = (e) => { if (e.key === "Enter") showDetail(w); };

    li.appendChild(title);
    li.appendChild(meta);
    li.appendChild(btn);
    if (!readOnly) {
      const delBtn = document.createElement("button");
      delBtn.className = "btn btn-danger btn-small";
      delBtn.textContent = "Usu\u0144";
      delBtn.setAttribute("aria-label", "Usu\u0144 prac\u0119 " + w.title);
      delBtn.onclick = (e) => { e.stopPropagation(); openDeleteDialog(w); };
      li.appendChild(delBtn);
    }
    ul.appendChild(li);
  }
}

function showDetail(w) {
  const panel = $("#detail-panel");
  const body = $("#detail-body");
  panel.hidden = false;
  clear(body);

  // --- Header: eyebrow label is the panel <h2>; here we add the prominent title ---
  const header = document.createElement("div");
  header.className = "detail-header";
  const title = textEl("h3", w.title);
  title.className = "detail-title";
  header.appendChild(title);
  body.appendChild(header);

  // --- Two-column detail table (CSS-grid <dl>, all via textContent = XSS-safe) ---
  const table = document.createElement("dl");
  table.className = "detail-table";

  const addRow = (label, valueNode) => {
    const dt = textEl("dt", label);
    const dd = document.createElement("dd");
    dd.appendChild(valueNode);
    table.appendChild(dt);
    table.appendChild(dd);
  };

  // Id — monospace pill.
  const idEl = textEl("span", w.id);
  idEl.className = "detail-id-pill";
  addRow("Id", idEl);

  addRow("Autorzy", textEl("span", w.authors.join(", ")));
  addRow("Rok", textEl("span", String(w.year)));
  addRow("Przedmiot", textEl("span", w.subject));

  // Typ — soft purple badge.
  const typeEl = textEl("span", w.work_type);
  typeEl.className = "badge badge-type";
  addRow("Typ", typeEl);

  addRow("Opis", textEl("span", w.description));

  // Tagi — individual lavender chips.
  const tagsWrap = document.createElement("div");
  tagsWrap.className = "tag-chips";
  for (const t of w.tags) {
    const chip = textEl("span", t);
    chip.className = "tag-chip";
    tagsWrap.appendChild(chip);
  }
  addRow("Tagi", tagsWrap);

  // URL — styled link if http(s), else plain text.
  let urlEl;
  if (/^https?:\/\//i.test(w.repo_url)) {
    urlEl = document.createElement("a");
    urlEl.href = w.repo_url;          // href set via property (not innerHTML)
    urlEl.textContent = w.repo_url;
    urlEl.target = "_blank";
    urlEl.rel = "noopener noreferrer";
    urlEl.className = "detail-link";
  } else {
    urlEl = textEl("span", w.repo_url);
  }
  addRow("URL", urlEl);

  body.appendChild(table);

  // --- Materials sub-card ---
  const matCard = document.createElement("div");
  matCard.className = "materials-card";
  matCard.appendChild(textEl("h4", "Materia\u0142y"));

  const mats = w.material_status || [];
  if (mats.length === 0) {
    const empty = textEl("p", "Brak zadeklarowanych materia\u0142\u00f3w.");
    empty.className = "materials-empty";
    matCard.appendChild(empty);
  } else {
    for (const m of mats) {
      const row = document.createElement("div");
      row.className = "material-row";
      const name = textEl("span", m.name);
      name.className = "material-name";
      row.appendChild(name);
      const badge = textEl("span", m.missing ? "Brak pliku materia\u0142u" : "Materia\u0142 dost\u0119pny");
      badge.className = m.missing ? "badge badge-missing" : "badge badge-ok";
      row.appendChild(badge);
      matCard.appendChild(row);
    }
  }
  body.appendChild(matCard);

  // --- Action buttons bar (respect read-only) ---
  if (!readOnly) {
    const actions = document.createElement("div");
    actions.className = "detail-actions";

    const editBtn = document.createElement("button");
    editBtn.className = "btn";
    editBtn.textContent = "Edytuj";
    editBtn.onclick = () => openForm(w);

    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-danger";
    delBtn.textContent = "Usu\u0144";
    delBtn.onclick = () => openDeleteDialog(w);

    actions.appendChild(editBtn);
    actions.appendChild(delBtn);
    body.appendChild(actions);
  }
}

async function refreshWorks() {
  const data = await apiGet("/api/works?sort=" + currentSort);
  renderWorkList(data.works);
  $("#metrics").textContent =
    "Liczba por\u00f3wna\u0144 kluczy (insertion sort): " + data.comparisons;
  if (data.works.length <= 15) {
    await renderTrace();
  } else {
    $("#trace-wrap").hidden = true;
  }
}

async function renderTrace() {
  const data = await apiGet("/api/trace?sort=" + currentSort);
  $("#trace-wrap").hidden = false;
  const table = $("#trace-table");
  clear(table);

  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  for (const h of ["Przed", "Decyzja", "Po"]) {
    hr.appendChild(textEl("th", h));
  }
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const trace = data.trace || [];
  if (trace.length === 0) {
    const tr = document.createElement("tr");
    const td = textEl("td", "Brak krok\u00f3w (zbi\u00f3r pusty).");
    td.colSpan = 3;
    tr.appendChild(td);
    tbody.appendChild(tr);
  }
  for (const entry of trace) {
    const current = entry[1], left = entry[2],
          decision = entry[3], after = entry[4];
    const tr = document.createElement("tr");
    tr.appendChild(textEl("td", "wstaw " + current + " obok " + left));
    tr.appendChild(textEl("td", decision === "shift_left" ? "przesu\u0144 w lewo" : "zatrzymaj"));
    tr.appendChild(textEl("td", "[" + after.join(", ") + "]"));
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
}

/* ------------------------------------------------------------------ */
/* Scenarios                                                          */
/* ------------------------------------------------------------------ */
async function renderScenarios() {
  const data = await apiGet("/api/scenarios");
  const wrap = $("#scenario-buttons");
  clear(wrap);
  for (const [name, label] of Object.entries(data.scenarios)) {
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.textContent = label;
    btn.onclick = () => loadScenario(name);
    wrap.appendChild(btn);
  }
}

async function loadScenario(name) {
  const r = await apiPost("/api/load_scenario/" + name, {});
  if (r.data.ok) {
    await refreshConfig();
    await refreshWorks();
  }
}

/* ------------------------------------------------------------------ */
/* Add / Edit form                                                    */
/* ------------------------------------------------------------------ */
function openForm(work) {
  pendingForm = null;
  pendingEditId = work ? work.id : null;
  $("#modal-title").textContent = work ? "Edytuj prac\u0119" : "Dodaj prac\u0119";
  $("#form-error").hidden = true;

  const idField = $("#f-id");
  idField.value = work ? work.id : "";
  idField.disabled = !!work;
  idField.setAttribute("aria-disabled", !!work ? "true" : "false");

  $("#f-title").value = work ? work.title : "";
  $("#f-authors").value = work ? work.authors.join(", ") : "";
  $("#f-year").value = work ? work.year : "";
  $("#f-subject").value = work ? work.subject : "";
  $("#f-type").value = work ? work.work_type : "projekt";
  $("#f-description").value = work ? work.description : "";
  $("#f-tags").value = work ? work.tags.join(", ") : "";
  $("#f-repo").value = work ? work.repo_url : "";

  $("#modal").hidden = false;
  $("#f-title").focus();
}

function closeForm() {
  $("#modal").hidden = true;
  pendingForm = null;
  pendingEditId = null;
}

function readForm() {
  return {
    id: $("#f-id").value.trim(),
    title: $("#f-title").value,
    authors: $("#f-authors").value.split(",").map(s => s.trim()).filter(Boolean),
    year: parseInt($("#f-year").value, 10),
    subject: $("#f-subject").value,
    work_type: $("#f-type").value,
    description: $("#f-description").value,
    tags: $("#f-tags").value.split(",").map(s => s.trim()).filter(Boolean),
    repo_url: $("#f-repo").value,
    materials: [],
  };
}

async function submitForm(confirmed) {
  const payload = readForm();
  if (confirmed !== undefined) payload.confirmed = confirmed;

  const url = pendingEditId ? "/api/edit/" + pendingEditId : "/api/add";
  const r = await apiPost(url, payload);

  if (r.data.duplicate) {
    pendingForm = payload;
    showDuplicateDialog(r.data.matches);
    return;
  }
  $("#form-error").hidden = true;
  if (r.data.ok) {
    closeForm();
    await refreshWorks();
  } else {
    $("#form-error").textContent = r.data.error || "B\u0142\u0105d walidacji.";
    $("#form-error").hidden = false;
  }
}

/* ------------------------------------------------------------------ */
/* Duplicate dialog                                                   */
/* ------------------------------------------------------------------ */
function showDuplicateDialog(matches) {
  const ul = $("#dup-list");
  clear(ul);
  for (const id of matches || []) {
    ul.appendChild(textEl("li", id));
  }
  $("#dup-modal").hidden = false;
}

function closeDuplicateDialog() {
  $("#dup-modal").hidden = true;
  pendingForm = null;
  pendingEditId = null;
}

/* ------------------------------------------------------------------ */
/* Delete dialog                                                      */
/* ------------------------------------------------------------------ */
function openDeleteDialog(w) {
  pendingDeleteId = w.id;
  $("#del-work-name").textContent = w.title + " (" + w.id + ")";
  $("#del-modal").hidden = false;
}

function closeDeleteDialog() {
  $("#del-modal").hidden = true;
  pendingDeleteId = null;
}

async function confirmDelete() {
  const id = pendingDeleteId;
  closeDeleteDialog();
  if (!id) return;
  const r = await apiDelete("/api/delete/" + encodeURIComponent(id));
  if (r.data.ok) {
    await refreshWorks();
  } else {
    alert(r.data.error || "Nie uda\u0142o si\u0119 usun\u0105\u0107.");
  }
}

/* ------------------------------------------------------------------ */
/* Import / export                                                    */
/* ------------------------------------------------------------------ */
async function importValidate() {
  importPath = $("#import-path").value.trim();
  if (!importPath) {
    $("#import-msg").textContent = "Podaj \u015bcie\u017ck\u0119 pliku.";
    return;
  }
  const r = await apiPost("/api/import", { path: importPath });
  if (r.data.ok) {
    importValidated = true;
    $("#import-msg").textContent = r.data.summary;
    $("#btn-import-apply").disabled = false;
  } else {
    importValidated = false;
    $("#btn-import-apply").disabled = true;
    $("#import-msg").textContent = "B\u0142\u0105d: " + (r.data.error || "niepoprawny plik") +
      " (istniej\u0105ce dane: " + (r.data.current_count ?? "?") + " prac).";
  }
}

async function importApply() {
  if (!importValidated) return;
  const r = await apiPost("/api/import/apply", { path: importPath, confirmed: true });
  if (r.data.ok) {
    $("#import-msg").textContent = "Zaimportowano. Liczba prac: " + r.data.count + ".";
    importValidated = false;
    $("#btn-import-apply").disabled = true;
    await refreshWorks();
  } else {
    $("#import-msg").textContent = "B\u0142\u0105d importu: " + (r.data.error || "");
  }
}

function openImport() {
  $("#import-modal").hidden = false;
  importValidated = false;
  $("#btn-import-apply").disabled = true;
  $("#import-msg").textContent = "";
}
function closeImport() { $("#import-modal").hidden = true; }

/* ------------------------------------------------------------------ */
/* Config / mode                                                      */
/* ------------------------------------------------------------------ */
async function refreshConfig() {
  config = await apiGet("/api/config");
  readOnly = !!config.read_only;
  $("#mode-badge").textContent = config.mode_label;

  const toggle = $("#btn-toggle-mode");
  const scenarios = $("#scenarios-section");
  if (!config.sandbox_enabled) {
    if (toggle) toggle.hidden = true;
    if (scenarios) scenarios.hidden = true;
  } else {
    if (toggle) toggle.hidden = false;
    if (scenarios) scenarios.hidden = false;
  }

  const add = $("#btn-add");
  const importOpenBtn = $("#btn-import-open");
  if (readOnly) {
    if (add) add.hidden = true;
    if (importOpenBtn) importOpenBtn.hidden = true;
  } else {
    if (add) add.hidden = false;
    if (importOpenBtn) importOpenBtn.hidden = false;
  }
}

async function toggleMode() {
  const next = config.active_mode === "sandbox" ? "archive" : "sandbox";
  const r = await apiPost("/api/mode", { mode: next });
  if (r.data.ok) {
    await refreshConfig();
    await refreshWorks();
  } else {
    alert(r.data.error || "Nie uda\u0142o si\u0119 prze\u0142\u0105czy\u0107 trybu.");
  }
}

/* ------------------------------------------------------------------ */
/* Wiring                                                             */
/* ------------------------------------------------------------------ */
async function doSearch() {
  const q = new URLSearchParams();
  if ($("#q-title").value.trim()) q.set("title", $("#q-title").value.trim());
  if ($("#q-authors").value.trim()) q.set("authors", $("#q-authors").value.trim());
  if ($("#q-keywords").value.trim()) q.set("keywords", $("#q-keywords").value.trim());
  if ($("#q-year").value) q.set("year", $("#q-year").value);
  if ($("#q-subject").value.trim()) q.set("subject", $("#q-subject").value.trim());
  if ($("#q-type").value) q.set("work_type", $("#q-type").value);

  const data = await apiGet("/api/search?" + q.toString());
  renderWorkList(data.works);
  $("#search-meta").textContent =
    "Znaleziono " + data.works.length + " prac \u00b7 sprawdzonych rekord\u00f3w: " + data.checked;
  $("#metrics").textContent =
    "Liczba sprawdzonych rekord\u00f3w (wyszukiwanie liniowe): " + data.checked;
}

function resetSearch() {
  $("#q-title").value = $("#q-authors").value = $("#q-keywords").value = "";
  $("#q-year").value = ""; $("#q-subject").value = ""; $("#q-type").value = "";
  $("#search-meta").textContent = "";
  refreshWorks();
}

$("#btn-search").onclick = doSearch;
$("#btn-reset").onclick = resetSearch;
$("#sort-select").onchange = async (e) => {
  currentSort = e.target.value;
  await refreshWorks();
};
$("#btn-add").onclick = () => openForm(null);
$("#work-form").onsubmit = (e) => { e.preventDefault(); submitForm(); };
$("#btn-cancel").onclick = closeForm;

$("#btn-confirm-dup").onclick = async () => {
  $("#dup-modal").hidden = true;
  const stored = pendingForm; const editId = pendingEditId;
  pendingForm = null; pendingEditId = null;
  if (stored) {
    const url = editId ? "/api/edit/" + editId : "/api/add";
    const r = await apiPost(url, Object.assign({}, stored, { confirmed: true }));
    if (r.data.ok) { closeForm(); await refreshWorks(); }
    else {
      $("#form-error").textContent = r.data.error || "B\u0142\u0105d.";
      $("#form-error").hidden = false;
      $("#modal").hidden = false;
      pendingForm = stored; pendingEditId = editId;
    }
  }
};
$("#btn-cancel-dup").onclick = closeDuplicateDialog;

$("#btn-confirm-del").onclick = confirmDelete;
$("#btn-cancel-del").onclick = closeDeleteDialog;
$("#btn-toggle-mode").onclick = toggleMode;

$("#btn-export").onclick = () => { window.location = "/api/export"; };
$("#btn-import-open").onclick = openImport;
$("#btn-import-validate").onclick = importValidate;
$("#btn-import-apply").onclick = importApply;
$("#btn-import-cancel").onclick = closeImport;

/* Escape closes any open modal. */
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeForm(); closeDuplicateDialog(); closeImport(); closeDeleteDialog();
  }
});

/* ------------------------------------------------------------------ */
/* Boot                                                               */
/* ------------------------------------------------------------------ */
(async function init() {
  await refreshConfig();
  await renderScenarios();
  await refreshWorks();
})();
