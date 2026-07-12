"""Lokales Web-Dashboard: Skills ansehen, neue Skills anlegen.

Läuft komplett auf der Python-Standardbibliothek (`http.server`) — keine
zusätzlichen Dependencies. Start via ``nextstep-os dashboard``.

Sicherheitsmodell: bindet per Default an 127.0.0.1 (nur lokal erreichbar).
Neue Skills entstehen als **Entwurf** — die Aktivierung läuft weiter über
das Activation Gate (``nextstep-os skills promote``).
"""

from __future__ import annotations

import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from .config import Config
from .core.feedback import list_feedback
from .core.registry import append_skill_registry_entry
from .core.skill_loader import load_registry, load_skill_by_id
from .core.tasks import load_tasks
from .core.telemetry import aggregate, read_runs


# --------------------------------------------------------------------------- #
# Daten-Funktionen (UI-unabhängig, einzeln testbar)
# --------------------------------------------------------------------------- #


_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slugify(name: str) -> str:
    """Skill-Name → Datei-/Register-ID (z.B. »Belege prüfen« → belege-pruefen)."""
    slug = name.strip().lower().translate(_UMLAUTS)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def list_skills_data(config: Config) -> list[dict[str, Any]]:
    """Alle Skill-Register-Einträge als JSON-fähige Dicts."""
    return [
        {
            "id": e.id,
            "name": e.name,
            "status": e.status.value,
            "owner": e.owner,
            "ampel": e.ampel,
            "execution_mode": e.execution_mode.value,
            "nutzungsart": e.nutzungsart.value,
            "keywords": e.keywords,
            "beschreibung": e.beschreibung,
        }
        for e in load_registry(config)
    ]


def skill_detail_data(config: Config, skill_id: str) -> dict[str, Any]:
    """Vollständiger Skill (Frontmatter + Markdown-Body)."""
    skill = load_skill_by_id(config, skill_id)
    return {
        "id": skill.id,
        "name": skill.name,
        "status": skill.status.value,
        "owner": skill.owner,
        "ampel": skill.ampel.value,
        "execution_mode": skill.execution_mode.value,
        "nutzungsart": skill.nutzungsart.value,
        "keywords": skill.keywords,
        "beschreibung": skill.beschreibung,
        "eingabe": skill.eingabe,
        "ausgabe": skill.ausgabe,
        "body": skill.body,
        "path": str(skill.path) if skill.path else None,
    }


_GOVERNANCE_LINES = {
    "🟢": "🟢 GRÜN – Läuft autonom im definierten Rahmen. Stichproben-Review genügt.",
    "🟡": "🟡 GELB – Output-Review durch den Owner, bevor das Ergebnis verwendet oder versendet wird.",
    "🔴": "🔴 ROT – Hochsensibel. Jeder Output wird geprüft, keine autonomen Aktionen, im Zweifel Expertenprüfung.",
}


def _as_list(value: Any) -> list[str]:
    """Formular-Eingaben normalisieren: Liste, Komma- oder Zeilen-getrennt."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    parts = re.split(r"[\n,]", str(value))
    return [p.strip() for p in parts if p.strip()]


def create_skill(config: Config, payload: dict[str, Any]) -> tuple[str, Path]:
    """Neuen Skill-Entwurf anlegen: MD-Datei schreiben + Register-Eintrag.

    Pflichtfeld: ``name``. Alles andere hat sinnvolle Defaults.
    Liefert (skill_id, pfad). Wirft ValueError bei Duplikat/fehlendem Namen.
    """
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Feld `name` ist Pflicht")

    skill_id = slugify(payload.get("id") or name)
    if not skill_id:
        raise ValueError(f"Aus `{name}` lässt sich keine gültige ID ableiten")

    skill_path = config.paths.skills_dir / f"{skill_id}.md"
    if skill_path.exists():
        raise ValueError(f"Skill-Datei `{skill_path.name}` existiert bereits")

    ampel = str(payload.get("ampel") or "🟡")
    if ampel not in _GOVERNANCE_LINES:
        raise ValueError(f"Ungültige Ampel `{ampel}` (erlaubt: 🟢 🟡 🔴)")
    execution_mode = str(payload.get("execution_mode") or "Strict")
    if execution_mode not in {"Strict", "Search"}:
        raise ValueError(f"Ungültiger execution_mode `{execution_mode}`")
    nutzungsart = str(payload.get("nutzungsart") or "public")
    if nutzungsart not in {"public", "private"}:
        raise ValueError(f"Ungültige nutzungsart `{nutzungsart}`")
    status = str(payload.get("status") or "Entwurf")
    if status not in {"Entwurf", "Aktiv"}:
        raise ValueError(f"Ungültiger status `{status}` (erlaubt: Entwurf, Aktiv)")

    owner = str(payload.get("owner") or "[OWNER]").strip() or "[OWNER]"
    beschreibung = str(payload.get("beschreibung") or "").strip()
    keywords = _as_list(payload.get("keywords"))
    eingabe = _as_list(payload.get("eingabe"))
    ausgabe = _as_list(payload.get("ausgabe"))
    sop = str(payload.get("sop") or "").strip()

    if not keywords:
        # Minimal-Fallback, damit der Skill überhaupt matchbar ist
        keywords = [t for t in slugify(name).split("-") if len(t) >= 3]

    frontmatter_data = {
        "id": skill_id,
        "name": name,
        "status": status,
        "owner": owner,
        "ampel": ampel,
        "execution_mode": execution_mode,
        "nutzungsart": nutzungsart,
        "keywords": keywords,
        "beschreibung": beschreibung or f"Skill `{name}` (via Dashboard angelegt).",
        "eingabe": eingabe,
        "ausgabe": ausgabe,
        "context": {
            "stufe_1_kern": ["governance/handbuch.md"],
            "stufe_2_aufgabe": [],
            "stufe_3_hintergrund": [],
        },
        "update_quellen": ["data/feedback/entries/"],
    }

    review_gate = (
        "\n⏸️ **REVIEW GATE:** Output wird vom Owner geprüft, bevor er verwendet wird.\n"
        if ampel in {"🟡", "🔴"}
        else ""
    )
    sop_body = sop if sop else (
        "1. [Schritt 1 — bitte ausfüllen]\n"
        "2. [Schritt 2]\n"
        "3. [Schritt 3]"
    )
    body = (
        f"## 🚦 Governance\n{_GOVERNANCE_LINES[ampel]}\n\n"
        "## 📋 Startprotokoll\n"
        "1. Prüfe, ob alle Pflicht-Eingaben vorliegen.\n"
        "2. Fehlt etwas: ⏸️ INPUT GATE — konkrete Rückfrage stellen und stoppen.\n\n"
        f"## 🔧 Arbeitsanweisung (SOP)\n\n{sop_body}\n{review_gate}\n"
        "## ✅ Definition of Done\n\n"
        "- ✅ Alle Ausgaben vollständig und geprüft\n"
        "- ✅ Kommunikationsstil eingehalten (siehe persönlicher Kontext)\n\n"
        "### No-Gos\n"
        "- 🚫 Fehlende Angaben erfinden\n\n"
        "## 📝 Learnings\n"
        "<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->\n"
    )

    yaml_header = yaml.safe_dump(
        frontmatter_data, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(f"---\n{yaml_header}---\n\n{body}", encoding="utf-8")

    try:
        append_skill_registry_entry(
            config.paths.skills_index,
            {
                "id": skill_id,
                "name": name,
                "path": f"skills/{skill_id}.md",
                "status": status,
                "owner": owner,
                "ampel": ampel,
                "execution_mode": execution_mode,
                "nutzungsart": nutzungsart,
                "keywords": keywords,
                "beschreibung": frontmatter_data["beschreibung"],
            },
        )
    except ValueError:
        skill_path.unlink(missing_ok=True)  # Rollback: Datei ohne Register-Eintrag
        raise

    return skill_id, skill_path


def feedback_data(config: Config) -> list[dict[str, Any]]:
    entries = list_feedback(config)
    return [
        {
            "datum": e.erstellt_am.isoformat(),
            "titel": e.titel,
            "typ": e.typ.value,
            "status": e.status.value,
            "skill_id": e.skill_id,
            "learning": e.learning,
        }
        for e in entries
    ]


def stats_data(config: Config) -> list[dict[str, Any]]:
    runs = read_runs(config)
    if not runs:
        return []
    return [
        {
            "skill_id": sid,
            "total": s.total,
            "ok": s.ok,
            "errors": s.errors,
            "dry_runs": s.dry_runs,
            "avg_duration_s": round(s.avg_duration_s, 2),
            "tokens_in": s.total_tokens_in,
            "tokens_out": s.total_tokens_out,
        }
        for sid, s in sorted(aggregate(runs).items())
    ]


def tasks_data(config: Config) -> list[dict[str, Any]]:
    """Alle Aufgaben aus data/tasks/ (sortiert nach Priorität/Fälligkeit)."""
    return [
        {
            "id": t.id,
            "titel": t.titel,
            "status": t.status.value,
            "prioritaet": t.prioritaet.value,
            "faellig": t.faellig.isoformat() if t.faellig else None,
            "skill": t.zugewiesener_skill,
            "meeting": t.meeting_ref,
            "erstellt_am": t.erstellt_am.isoformat(),
        }
        for t in load_tasks(config)
    ]


def context_data(config: Config) -> list[dict[str, Any]]:
    """Persönliche Kontext-Profile mit Status (befüllt vs. Template)."""
    result = []
    personal = config.paths.context_personal
    if not personal.exists():
        return result
    for md in sorted(personal.glob("*.md")):
        try:
            post = frontmatter.load(md)
            meta = dict(post.metadata)
            content = post.content
        except Exception:  # noqa: BLE001
            meta, content = {}, ""
        letzte = str(meta.get("letzte_aktualisierung", ""))
        befuellt = "[" not in letzte and bool(letzte.strip())
        result.append(
            {
                "id": meta.get("id", md.stem),
                "name": meta.get("name", md.stem),
                "stufe": meta.get("kontext_stufe", "?"),
                "letzte_aktualisierung": letzte,
                "befuellt": befuellt,
                "platzhalter": content.count("["),
            }
        )
    return result


# --------------------------------------------------------------------------- #
# HTTP-Layer
# --------------------------------------------------------------------------- #


def _make_handler(config: Config):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "NextStepKI-Dashboard/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:  # leiser Server
            pass

        # ---------------- Helpers ---------------- #

        def _send_json(self, data: Any, status: int = 200) -> None:
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, html: str) -> None:
            raw = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        # ---------------- Routes ---------------- #

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            try:
                if path == "/":
                    self._send_html(DASHBOARD_HTML)
                elif path == "/api/skills":
                    self._send_json(list_skills_data(config))
                elif path.startswith("/api/skills/"):
                    skill_id = path.removeprefix("/api/skills/")
                    try:
                        self._send_json(skill_detail_data(config, skill_id))
                    except KeyError:
                        self._send_json({"error": f"Skill `{skill_id}` nicht gefunden"}, 404)
                elif path == "/api/tasks":
                    self._send_json(tasks_data(config))
                elif path == "/api/feedback":
                    self._send_json(feedback_data(config))
                elif path == "/api/stats":
                    self._send_json(stats_data(config))
                elif path == "/api/context":
                    self._send_json(context_data(config))
                else:
                    self._send_json({"error": "Nicht gefunden"}, 404)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": str(exc)}, 500)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0].rstrip("/")
            if path != "/api/skills":
                self._send_json({"error": "Nicht gefunden"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length) or b"{}")
                skill_id, skill_path = create_skill(config, payload)
                self._send_json(
                    {"ok": True, "id": skill_id, "path": str(skill_path)}, 201
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, 400)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": str(exc)}, 500)

    return DashboardHandler


def serve(
    config: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8321,
    open_browser: bool = True,
) -> None:
    """Dashboard-Server starten (blockierend, Ctrl-C zum Beenden)."""
    server = ThreadingHTTPServer((host, port), _make_handler(config))
    url = f"http://{host}:{port}"
    print(f"NextStepKI-Dashboard läuft auf {url}  (Ctrl-C zum Beenden)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard beendet.")
    finally:
        server.server_close()


# --------------------------------------------------------------------------- #
# Frontend (Single-Page, eingebettet — keine externen Ressourcen)
# --------------------------------------------------------------------------- #


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NextStepKI — Dashboard</title>
<style>
:root {
  --bg: #f6f7f9; --card: #ffffff; --text: #1a1d21; --muted: #6b7280;
  --border: #e5e7eb; --accent: #2563eb; --accent-soft: #eff6ff;
  --green: #16a34a; --yellow: #d97706; --red: #dc2626;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111418; --card: #1a1f26; --text: #e8eaed; --muted: #9aa3af;
    --border: #2a313a; --accent: #60a5fa; --accent-soft: #1c2733;
  }
}
* { box-sizing: border-box; margin: 0; }
body { background: var(--bg); color: var(--text); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { padding: 20px 28px 0; max-width: 1080px; margin: 0 auto; }
h1 { font-size: 20px; }
h1 small { color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 8px; }
nav { display: flex; gap: 4px; margin-top: 16px; border-bottom: 1px solid var(--border); }
nav button { background: none; border: none; color: var(--muted); font: inherit; padding: 9px 14px; cursor: pointer; border-bottom: 2px solid transparent; }
nav button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
main { max-width: 1080px; margin: 0 auto; padding: 20px 28px 60px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; cursor: pointer; transition: border-color .12s; }
.card:hover { border-color: var(--accent); }
.card h3 { font-size: 15px; margin-bottom: 4px; }
.card p { color: var(--muted); font-size: 13px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.badge { font-size: 11.5px; padding: 2px 8px; border-radius: 20px; background: var(--accent-soft); color: var(--accent); border: 1px solid var(--border); }
.badge.status-Entwurf { color: var(--yellow); }
.badge.status-Aktiv { color: var(--green); }
.badge.status-Archiviert { color: var(--muted); }
.searchbar { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--card); color: var(--text); font: inherit; margin-bottom: 16px; }
.detail { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 24px; }
.detail .back { color: var(--accent); cursor: pointer; font-size: 13px; margin-bottom: 12px; display: inline-block; background: none; border: none; padding: 0; font-family: inherit; }
.detail h2 { margin-bottom: 6px; }
.detail .meta { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.kv { display: grid; grid-template-columns: 130px 1fr; gap: 4px 12px; font-size: 13.5px; margin: 14px 0; }
.kv dt { color: var(--muted); }
.md { margin-top: 18px; border-top: 1px solid var(--border); padding-top: 16px; }
.md h2 { font-size: 16px; margin: 18px 0 8px; }
.md h3 { font-size: 14.5px; margin: 14px 0 6px; }
.md p { margin: 6px 0; }
.md ul, .md ol { margin: 6px 0 6px 22px; }
.md li { margin: 3px 0; }
.md code { background: var(--accent-soft); border-radius: 4px; padding: 1px 5px; font-size: 13px; }
.md pre { background: var(--accent-soft); border-radius: 8px; padding: 12px; overflow-x: auto; margin: 8px 0; }
.md pre code { background: none; padding: 0; }
form { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 24px; max-width: 720px; }
form label { display: block; font-size: 13px; font-weight: 600; margin: 14px 0 4px; }
form label .opt { color: var(--muted); font-weight: 400; }
form input, form textarea, form select { width: 100%; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font: inherit; }
form textarea { min-height: 70px; resize: vertical; }
form .row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
form button[type=submit] { margin-top: 20px; background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 10px 22px; font: inherit; font-weight: 600; cursor: pointer; }
.hint { color: var(--muted); font-size: 12.5px; margin-top: 4px; }
.msg { margin-top: 14px; padding: 10px 14px; border-radius: 8px; font-size: 14px; display: none; }
.msg.ok { display: block; background: #dcfce7; color: #14532d; }
.msg.err { display: block; background: #fee2e2; color: #7f1d1d; }
@media (prefers-color-scheme: dark) {
  .msg.ok { background: #14331e; color: #86efac; }
  .msg.err { background: #3b1414; color: #fca5a5; }
}
table { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 10px 14px; font-size: 13.5px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
tr:last-child td { border-bottom: none; }
.empty { color: var(--muted); padding: 30px; text-align: center; }
.tablewrap { overflow-x: auto; }
</style>
</head>
<body>
<header>
  <h1>🧠 NextStepKI <small>KI-Betriebssystem — Dashboard</small></h1>
  <nav>
    <button data-tab="skills" class="active">Skills</button>
    <button data-tab="neu">＋ Neuer Skill</button>
    <button data-tab="aufgaben">Aufgaben</button>
    <button data-tab="kontext">Kontext</button>
    <button data-tab="feedback">Feedback</button>
    <button data-tab="telemetrie">Telemetrie</button>
  </nav>
</header>
<main>
  <section id="tab-skills">
    <input class="searchbar" id="skillsearch" placeholder="Skills durchsuchen … (Name, Keyword, Beschreibung)">
    <div class="grid" id="skillgrid"></div>
    <div class="detail" id="skilldetail" style="display:none"></div>
  </section>

  <section id="tab-neu" style="display:none">
    <form id="newskill">
      <h2 style="margin-bottom:4px">Neuen Skill anlegen</h2>
      <p class="hint">Der Skill wird als Markdown-Datei in <code>data/skills/</code> angelegt und im Register eingetragen.
      Empfehlung: als <b>Entwurf</b> starten und nach 3 erfolgreichen Testläufen via <code>nextstep-os skills promote</code> aktivieren.</p>

      <label>Name *</label>
      <input name="name" required placeholder="z.B. Rechnung schreiben">

      <label>Beschreibung <span class="opt">(was macht der Skill, 1–3 Sätze)</span></label>
      <textarea name="beschreibung" placeholder="Erstellt eine Rechnung auf Basis von Kundendaten und Leistungsübersicht …"></textarea>

      <label>Keywords <span class="opt">(Komma-getrennt — wichtig fürs Matching)</span></label>
      <input name="keywords" placeholder="rechnung, rechnung schreiben, invoice">

      <div class="row">
        <div>
          <label>Ampel</label>
          <select name="ampel">
            <option value="🟡" selected>🟡 GELB — Review vor Nutzung</option>
            <option value="🟢">🟢 GRÜN — autonom</option>
            <option value="🔴">🔴 ROT — hochsensibel</option>
          </select>
        </div>
        <div>
          <label>Modus</label>
          <select name="execution_mode">
            <option selected>Strict</option>
            <option>Search</option>
          </select>
        </div>
        <div>
          <label>Status</label>
          <select name="status">
            <option selected>Entwurf</option>
            <option>Aktiv</option>
          </select>
        </div>
      </div>

      <label>Eingaben <span class="opt">(eine pro Zeile)</span></label>
      <textarea name="eingabe" placeholder="Kundendaten (Pflicht)&#10;Leistungszeitraum (Pflicht)"></textarea>

      <label>Ausgaben <span class="opt">(eine pro Zeile)</span></label>
      <textarea name="ausgabe" placeholder="Fertige Rechnung als Entwurf"></textarea>

      <label>Arbeitsanweisung (SOP) <span class="opt">(Markdown, optional — sonst Platzhalter)</span></label>
      <textarea name="sop" style="min-height:120px" placeholder="1. Kundendaten prüfen&#10;2. Positionen zusammenstellen&#10;3. …"></textarea>

      <label>Owner</label>
      <input name="owner" placeholder="Lorenz Kopp">

      <button type="submit">Skill anlegen</button>
      <div class="msg" id="formmsg"></div>
    </form>
  </section>

  <section id="tab-aufgaben" style="display:none">
    <div class="tablewrap"><table id="taskstable"></table></div>
  </section>

  <section id="tab-kontext" style="display:none">
    <div class="tablewrap"><table id="contexttable"></table></div>
  </section>

  <section id="tab-feedback" style="display:none">
    <div class="tablewrap"><table id="feedbacktable"></table></div>
  </section>

  <section id="tab-telemetrie" style="display:none">
    <div class="tablewrap"><table id="statstable"></table></div>
  </section>
</main>

<script>
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// ---- Mini-Markdown-Renderer (Headings, Listen, Bold, Code) ----
function md(src) {
  const lines = String(src || "").split("\\n");
  let html = "", inUl = false, inOl = false, inPre = false;
  const closeLists = () => { if (inUl) { html += "</ul>"; inUl = false; } if (inOl) { html += "</ol>"; inOl = false; } };
  const inline = t => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\\*\\*([^*]+)\\*\\*/g, "<b>$1</b>")
    .replace(/(?<!\\*)\\*([^*\\s][^*]*)\\*(?!\\*)/g, "<i>$1</i>");
  for (const line of lines) {
    if (line.trim().startsWith("```")) { closeLists(); html += inPre ? "</code></pre>" : "<pre><code>"; inPre = !inPre; continue; }
    if (inPre) { html += esc(line) + "\\n"; continue; }
    if (line.trim().startsWith("<!--")) continue;
    const h = line.match(/^(#{1,4})\\s+(.*)/);
    if (h) { closeLists(); html += `<h${h[1].length+1}>${inline(h[2])}</h${h[1].length+1}>`; continue; }
    const ul = line.match(/^\\s*[-•]\\s+(.*)/);
    if (ul) { if (!inUl) { closeLists(); html += "<ul>"; inUl = true; } html += `<li>${inline(ul[1])}</li>`; continue; }
    const ol = line.match(/^\\s*\\d+\\.\\s+(.*)/);
    if (ol) { if (!inOl) { closeLists(); html += "<ol>"; inOl = true; } html += `<li>${inline(ol[1])}</li>`; continue; }
    if (!line.trim()) { closeLists(); continue; }
    closeLists(); html += `<p>${inline(line)}</p>`;
  }
  closeLists(); if (inPre) html += "</code></pre>";
  return html;
}

// ---- Tabs ----
document.querySelectorAll("nav button").forEach(btn => btn.onclick = () => {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b === btn));
  document.querySelectorAll("main > section").forEach(s => s.style.display = "none");
  $("#tab-" + btn.dataset.tab).style.display = "";
  if (btn.dataset.tab === "aufgaben") loadTasks();
  if (btn.dataset.tab === "kontext") loadContext();
  if (btn.dataset.tab === "feedback") loadFeedback();
  if (btn.dataset.tab === "telemetrie") loadStats();
});

// ---- Skills ----
let SKILLS = [];
async function loadSkills() {
  SKILLS = await (await fetch("/api/skills")).json();
  renderSkills();
}
function renderSkills() {
  const q = $("#skillsearch").value.toLowerCase();
  const hits = SKILLS.filter(s =>
    !q || s.name.toLowerCase().includes(q) || s.beschreibung.toLowerCase().includes(q)
      || s.keywords.some(k => k.toLowerCase().includes(q)));
  $("#skilldetail").style.display = "none";
  const grid = $("#skillgrid");
  grid.style.display = "";
  grid.innerHTML = hits.map(s => `
    <div class="card" onclick="showSkill('${esc(s.id)}')">
      <h3>${esc(s.ampel)} ${esc(s.name)}</h3>
      <p>${esc(s.beschreibung)}</p>
      <div class="badges">
        <span class="badge status-${esc(s.status)}">${esc(s.status)}</span>
        <span class="badge">${esc(s.execution_mode)}</span>
        <span class="badge">${esc(s.nutzungsart)}</span>
        ${s.keywords.slice(0,3).map(k => `<span class="badge">${esc(k)}</span>`).join("")}
      </div>
    </div>`).join("") || `<div class="empty">Keine Skills gefunden.</div>`;
}
$("#skillsearch").oninput = renderSkills;

async function showSkill(id) {
  const s = await (await fetch("/api/skills/" + encodeURIComponent(id))).json();
  if (s.error) return alert(s.error);
  $("#skillgrid").style.display = "none";
  const d = $("#skilldetail");
  d.style.display = "";
  d.innerHTML = `
    <button class="back" onclick="renderSkills()">← zurück zur Übersicht</button>
    <h2>${esc(s.ampel)} ${esc(s.name)}</h2>
    <div class="meta">${esc(s.id)} · ${esc(s.path || "")}</div>
    <div class="badges">
      <span class="badge status-${esc(s.status)}">${esc(s.status)}</span>
      <span class="badge">${esc(s.execution_mode)}</span>
      <span class="badge">${esc(s.nutzungsart)}</span>
      <span class="badge">Owner: ${esc(s.owner)}</span>
    </div>
    <dl class="kv">
      <dt>Beschreibung</dt><dd>${esc(s.beschreibung)}</dd>
      <dt>Keywords</dt><dd>${s.keywords.map(esc).join(", ")}</dd>
      <dt>Eingaben</dt><dd>${s.eingabe.map(esc).join("<br>") || "—"}</dd>
      <dt>Ausgaben</dt><dd>${s.ausgabe.map(esc).join("<br>") || "—"}</dd>
    </dl>
    <div class="md">${md(s.body)}</div>`;
  d.scrollIntoView({behavior: "smooth"});
}

// ---- Neuer Skill ----
$("#newskill").onsubmit = async ev => {
  ev.preventDefault();
  const f = ev.target, msg = $("#formmsg");
  const payload = Object.fromEntries(new FormData(f).entries());
  const res = await fetch("/api/skills", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const out = await res.json();
  msg.className = "msg " + (res.ok ? "ok" : "err");
  msg.textContent = res.ok
    ? `✅ Skill »${payload.name}« angelegt (${out.id}). ${payload.status === "Entwurf" ? "Status: Entwurf — Aktivierung nach Testläufen via CLI." : ""}`
    : `Fehler: ${out.error}`;
  if (res.ok) { f.reset(); loadSkills(); }
};

// ---- Aufgaben ----
async function loadTasks() {
  const rows = await (await fetch("/api/tasks")).json();
  $("#taskstable").innerHTML = `
    <tr><th>Prio</th><th>Aufgabe</th><th>Status</th><th>Fällig</th><th>Skill</th><th>Meeting</th></tr>` +
    (rows.map(t => `<tr>
      <td>${esc(t.prioritaet)}</td><td>${esc(t.titel)}</td><td>${esc(t.status)}</td>
      <td>${esc(t.faellig || "—")}</td><td>${esc(t.skill || "—")}</td>
      <td>${esc(t.meeting || "—")}</td></tr>`).join("")
     || `<tr><td colspan="6" class="empty">Keine Aufgaben — sie entstehen über die Meeting-Pipeline oder manuell in data/tasks/.</td></tr>`);
}

// ---- Kontext ----
async function loadContext() {
  const rows = await (await fetch("/api/context")).json();
  $("#contexttable").innerHTML = `
    <tr><th>Profil</th><th>Stufe</th><th>Status</th><th>Zuletzt aktualisiert</th></tr>` +
    (rows.map(c => `<tr>
      <td>${esc(c.name)}</td><td>${esc(c.stufe)}</td>
      <td>${c.befuellt ? "✅ befüllt" : "📝 Template (" + c.platzhalter + " Platzhalter)"}</td>
      <td>${esc(c.letzte_aktualisierung)}</td></tr>`).join("")
     || `<tr><td colspan="4" class="empty">Keine Kontext-Profile gefunden.</td></tr>`);
}

// ---- Feedback ----
async function loadFeedback() {
  const rows = await (await fetch("/api/feedback")).json();
  $("#feedbacktable").innerHTML = `
    <tr><th>Datum</th><th>Titel</th><th>Typ</th><th>Status</th><th>Skill</th></tr>` +
    (rows.map(e => `<tr>
      <td>${esc(e.datum)}</td><td>${esc(e.titel)}</td><td>${esc(e.typ)}</td>
      <td>${esc(e.status)}</td><td>${esc(e.skill_id || "—")}</td></tr>`).join("")
     || `<tr><td colspan="5" class="empty">Noch kein Feedback aufgezeichnet.</td></tr>`);
}

// ---- Telemetrie ----
async function loadStats() {
  const rows = await (await fetch("/api/stats")).json();
  $("#statstable").innerHTML = `
    <tr><th>Skill</th><th>Runs</th><th>OK</th><th>Fehler</th><th>DryRuns</th><th>Ø Dauer</th><th>Tokens in/out</th></tr>` +
    (rows.map(s => `<tr>
      <td>${esc(s.skill_id)}</td><td>${s.total}</td><td>${s.ok}</td><td>${s.errors}</td>
      <td>${s.dry_runs}</td><td>${s.avg_duration_s}s</td>
      <td>${s.tokens_in} / ${s.tokens_out}</td></tr>`).join("")
     || `<tr><td colspan="7" class="empty">Noch keine Skill-Runs aufgezeichnet.</td></tr>`);
}

loadSkills();
</script>
</body>
</html>
"""
