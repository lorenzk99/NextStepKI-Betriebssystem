"""Tests für Monthly-Review-Report und Patch-Proposals."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from nextstep_os.core.feedback import record
from nextstep_os.core.models import FeedbackTyp
from nextstep_os.core.review import (
    build_monthly_report,
    suggest_skill_patch,
    write_report,
)
from nextstep_os.core.telemetry import SkillRun, record_run


def test_empty_report_renders(isolated_config):
    report = build_monthly_report(isolated_config)
    md = report.to_markdown()
    assert "Monthly Review" in md
    assert "Keine Feedback-Einträge" in md
    assert "Keine Telemetrie-Daten" in md


def test_report_includes_feedback_and_telemetry(isolated_config):
    record(
        isolated_config,
        titel="Test-Feedback",
        typ=FeedbackTyp.VERBESSERUNGS_IDEE,
        learning="Immer auf Deutsch antworten.",
        skill_id="angebot-erstellen",
    )
    record_run(
        isolated_config,
        SkillRun(
            skill_id="angebot-erstellen",
            status="ok",
            duration_s=1.5,
            tokens_in=100,
            tokens_out=50,
        ),
    )
    report = build_monthly_report(isolated_config, tage=30)
    md = report.to_markdown()
    assert "Test-Feedback" in md
    assert "angebot-erstellen" in md
    assert "Immer auf Deutsch" in md
    assert len(report.feedback) == 1
    assert "angebot-erstellen" in report.stats


def test_report_filters_by_timeframe(isolated_config):
    # Feedback im Scope
    record(
        isolated_config,
        titel="Aktuell",
        typ=FeedbackTyp.ERFOLG,
        learning="Frisches Learning.",
        skill_id="x",
    )
    # Telemetrie außerhalb (Datum manipulieren)
    old_ts = (date.today() - timedelta(days=60)).isoformat() + "T12:00:00"
    record_run(
        isolated_config,
        SkillRun(skill_id="old-skill", status="ok", ts=old_ts),
    )
    report = build_monthly_report(isolated_config, tage=30)
    assert "old-skill" not in report.stats
    assert any(e.titel == "Aktuell" for e in report.feedback)


def test_write_report_creates_file(isolated_config):
    report = build_monthly_report(isolated_config, tage=7)
    path = write_report(isolated_config, report)
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("# Monthly Review")
    assert path.parent.name == "reviews"


def test_suggest_skill_patch_handles_missing_feedback(isolated_config, monkeypatch, tmp_path):
    """Ohne passende Feedback-Einträge gibt es einen stub-Proposal."""
    # Seed-Skill via Registry + MD
    from nextstep_os.core.registry import write_yaml

    skill_md = tmp_path / "skill.md"
    skill_md.write_text(
        "---\nid: leer-skill\nname: Leer\nstatus: Aktiv\nowner: X\nampel: '🟢'\n"
        "execution_mode: Strict\nnutzungsart: public\nkeywords: [x]\n"
        "beschreibung: ''\n---\n\nBody",
        encoding="utf-8",
    )
    # In data/skills kopieren
    target = isolated_config.paths.data / "skills" / "leer-skill.md"
    target.write_text(skill_md.read_text(encoding="utf-8"), encoding="utf-8")
    write_yaml(
        isolated_config.paths.skills_index,
        {"skills": [{
            "id": "leer-skill", "name": "Leer", "path": "skills/leer-skill.md",
            "status": "Aktiv", "owner": "X", "ampel": "🟢",
            "execution_mode": "Strict", "nutzungsart": "public",
            "keywords": ["x"], "beschreibung": "",
        }]},
    )
    proposal = asyncio.run(suggest_skill_patch(isolated_config, "leer-skill"))
    assert proposal.skill_id == "leer-skill"
    assert "Keine relevanten" in proposal.suggestion
    assert proposal.applied is False
