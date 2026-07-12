"""Regressions-Tests für die im Projekt-Review gefundenen Bugs."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from nextstep_os.core.briefing import build_daily_briefing
from nextstep_os.core.context_loader import load_boot_context, load_context_for_skill
from nextstep_os.core.feedback import build_feedback, silent_patch_skill, write_feedback
from nextstep_os.core.governance import detect_hil_markers
from nextstep_os.core.models import Ampel, FeedbackTyp, Prioritaet, TaskStatus
from nextstep_os.core.registry import (
    append_skill_registry_entry,
    load_skill_registry,
    update_skill_registry_entry,
)
from nextstep_os.core.skill_loader import _coerce_enum, load_registry, load_skill_by_id
from nextstep_os.core.tasks import load_tasks, overdue
from nextstep_os.core.telemetry import SkillRun, read_runs, record_run


# --------------------------------------------------------------------------- #
# feedback.py
# --------------------------------------------------------------------------- #


def test_feedback_same_title_same_day_not_overwritten(isolated_config):
    """Zwei Feedbacks mit gleichem Titel am selben Tag → zwei Dateien."""
    e1 = build_feedback(titel="Fehler im Angebot", typ=FeedbackTyp.FEHLER, learning="A")
    e2 = build_feedback(titel="Fehler im Angebot", typ=FeedbackTyp.FEHLER, learning="B")
    p1 = write_feedback(isolated_config, e1)
    p2 = write_feedback(isolated_config, e2)
    assert p1 != p2
    assert p1.exists() and p2.exists()


def test_silent_patch_preserves_frontmatter_comments(tmp_path):
    """Silent Patch darf YAML-Kommentare im Frontmatter nicht zerstören."""
    skill = tmp_path / "test-skill.md"
    skill.write_text(
        "---\n"
        "id: test-skill\n"
        "name: Test\n"
        "context:\n"
        "  stufe_1_kern:\n"
        "    - governance/handbuch.md\n"
        "    # Wichtiger Kommentar der erhalten bleiben muss\n"
        "---\n\n"
        "## SOP\nMach was.\n\n"
        "## 📝 Learnings\n",
        encoding="utf-8",
    )
    silent_patch_skill(skill, "Immer ohne Emojis antworten.")
    raw = skill.read_text(encoding="utf-8")
    assert "# Wichtiger Kommentar der erhalten bleiben muss" in raw
    assert "Immer ohne Emojis antworten." in raw


def test_silent_patch_strips_duplicate_date(tmp_path):
    """Learning mit führendem Datum wird nicht doppelt datiert."""
    skill = tmp_path / "s.md"
    skill.write_text("---\nid: s\nname: S\n---\n\n## 📝 Learnings\n", encoding="utf-8")
    silent_patch_skill(skill, "2026-07-12: Keine Floskeln.", heute=date(2026, 7, 12))
    raw = skill.read_text(encoding="utf-8")
    assert "- **2026-07-12:** Keine Floskeln." in raw
    assert raw.count("2026-07-12") == 1  # Datum nur einmal, nicht doppelt


# --------------------------------------------------------------------------- #
# registry.py
# --------------------------------------------------------------------------- #


def test_registry_handles_null_skills_key(tmp_path):
    """`skills:` ohne Wert (YAML-null) darf nicht crashen."""
    index = tmp_path / "_index.yaml"
    index.write_text("skills:\n", encoding="utf-8")
    assert load_skill_registry(index) == []
    append_skill_registry_entry(index, {"id": "a", "name": "A"})
    assert len(load_skill_registry(index)) == 1
    update_skill_registry_entry(index, "a", {"name": "A2"})
    assert load_skill_registry(index)[0]["name"] == "A2"


# --------------------------------------------------------------------------- #
# skill_loader.py
# --------------------------------------------------------------------------- #


def test_coerce_enum_matches_member_names():
    """`ampel: rot` (Text statt Emoji) darf nicht still zu GELB werden."""
    assert _coerce_enum(Ampel, "rot", Ampel.GELB) == Ampel.ROT
    assert _coerce_enum(Ampel, "ROT", Ampel.GELB) == Ampel.ROT
    assert _coerce_enum(Ampel, "grün", Ampel.GELB) == Ampel.GRUEN
    assert _coerce_enum(Ampel, "🔴", Ampel.GELB) == Ampel.ROT
    assert _coerce_enum(Ampel, "unbekannt", Ampel.GELB) == Ampel.GELB


def test_null_beschreibung_in_registry_does_not_crash(isolated_config):
    index = isolated_config.paths.skills_index
    index.write_text(
        "skills:\n"
        "  - id: x\n    name: X\n    path: skills/x.md\n"
        "    status: Aktiv\n    owner: o\n    ampel: \"🟢\"\n"
        "    execution_mode: Strict\n    nutzungsart: public\n"
        "    keywords: [x]\n    beschreibung:\n",
        encoding="utf-8",
    )
    entries = load_registry(isolated_config)
    assert entries[0].beschreibung == ""


def test_load_skill_by_id_missing_file_gives_clear_error(isolated_config):
    index = isolated_config.paths.skills_index
    index.write_text(
        "skills:\n"
        "  - id: weg\n    name: Weg\n    path: skills/weg.md\n"
        "    status: Aktiv\n    owner: o\n    ampel: \"🟢\"\n"
        "    execution_mode: Strict\n    nutzungsart: public\n"
        "    keywords: [weg]\n    beschreibung: x\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="auseinandergelaufen"):
        load_skill_by_id(isolated_config, "weg")


# --------------------------------------------------------------------------- #
# governance.py
# --------------------------------------------------------------------------- #


def test_review_gate_with_freigabe_word_is_review_not_approval():
    """»⏸️ REVIEW GATE: … ohne explizite Freigabe« ist ein Review-Gate."""
    body = "⏸️ **REVIEW GATE:** Prüfen. Kein Versand ohne explizite Freigabe."
    markers = detect_hil_markers(body)
    assert len(markers) == 1
    assert markers[0].typ == "review"


def test_hil_marker_in_backticks_is_not_a_gate():
    body = "- HIL-Punkte mit `⏸️ APPROVAL GATE:` markieren"
    assert detect_hil_markers(body) == []


def test_erklaerung_does_not_match_klaerung():
    body = "⏸️ GATE: Hier folgt eine Erklärung des Vorgehens."
    markers = detect_hil_markers(body)
    assert markers[0].typ == "generic"


# --------------------------------------------------------------------------- #
# context_loader.py — Stufe 2 personal wird geladen
# --------------------------------------------------------------------------- #


def _write_personal_context(cfg, stem: str, stufe: int) -> None:
    (cfg.paths.context_personal / f"{stem}.md").write_text(
        f"---\nid: {stem}\nname: {stem}\nkontext_stufe: {stufe}\ntyp: personal\n---\n"
        f"# {stem}\nInhalt {stem}.",
        encoding="utf-8",
    )


def test_stufe_2_personal_context_is_loaded(isolated_config):
    cfg = isolated_config
    _write_personal_context(cfg, "prioritaeten", 2)
    cfg.paths.context_index.write_text(
        "entries:\n"
        "  - id: prioritaeten\n    name: Prioritäten\n"
        "    path: context/personal/prioritaeten.md\n"
        "    typ: personal\n    kontext_stufe: 2\n    skills: []\n",
        encoding="utf-8",
    )
    bundle = load_boot_context(cfg)
    ids = [i.entry.id for i in bundle.stufe_2]
    assert "prioritaeten" in ids, "Stufe-2-Personal-Kontext muss auch ohne Skill geladen werden"


def test_stufe_2_real_data_loaded_for_skill(real_config):
    """Mit den echten Projektdaten: Prioritäten & Team landen in Stufe 2."""
    skill = load_skill_by_id(real_config, "email-entwurf")
    bundle = load_context_for_skill(real_config, skill)
    stufe_2_ids = {i.entry.id for i in bundle.stufe_2}
    assert "prioritaeten-und-ziele" in stufe_2_ids
    assert "team-kontext" in stufe_2_ids


# --------------------------------------------------------------------------- #
# telemetry.py
# --------------------------------------------------------------------------- #


def test_read_runs_tolerates_unknown_fields(isolated_config):
    record_run(isolated_config, SkillRun(skill_id="a"))
    path = isolated_config.paths.data / "telemetry" / "skill_runs.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"skill_id": "b", "status": "ok", "zukunfts_feld": 42}\n')
    runs = read_runs(isolated_config)
    assert {r.skill_id for r in runs} == {"a", "b"}


# --------------------------------------------------------------------------- #
# tasks.py + briefing.py
# --------------------------------------------------------------------------- #


def _write_task(cfg, task_id: str, status: str, prio: str = "🟡", faellig: str = "") -> None:
    faellig_line = f"faellig: {faellig}\n" if faellig else ""
    (cfg.paths.tasks_dir / f"{task_id}.md").write_text(
        f"---\nid: {task_id}\ntitel: {task_id}\nstatus: {status}\n"
        f"prioritaet: \"{prio}\"\n{faellig_line}---\nBody.",
        encoding="utf-8",
    )


def test_load_tasks_sorted_and_filtered(isolated_config):
    cfg = isolated_config
    _write_task(cfg, "t-niedrig", "Neu", "🟢")
    _write_task(cfg, "t-hoch", "Neu", "🔴")
    _write_task(cfg, "t-erledigt", "Erledigt", "🔴")
    offene = load_tasks(cfg, nur_offene=True)
    assert [t.id for t in offene] == ["t-hoch", "t-niedrig"]
    alle = load_tasks(cfg)
    assert len(alle) == 3


def test_overdue_detection(isolated_config):
    cfg = isolated_config
    gestern = (date.today() - timedelta(days=1)).isoformat()
    morgen = (date.today() + timedelta(days=1)).isoformat()
    _write_task(cfg, "t-spaet", "Neu", "🔴", gestern)
    _write_task(cfg, "t-ok", "Neu", "🟡", morgen)
    tasks = load_tasks(cfg)
    late = overdue(tasks)
    assert [t.id for t in late] == ["t-spaet"]


def test_daily_briefing_renders(isolated_config):
    cfg = isolated_config
    _write_task(cfg, "t-review", "Wartet auf Review", "🔴")
    _write_task(cfg, "t-neu", "Neu", "🟡")
    briefing = build_daily_briefing(cfg)
    md = briefing.to_markdown()
    assert "Tagesbriefing" in md
    assert "Du bist am Zug" in md
    assert "t-review" in md
    assert "Offene Aufgaben (2)" in md
