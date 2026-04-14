"""Tests für Skill-Loader und Semantic Matching."""

from __future__ import annotations

from nextstep_os.core.models import MatchQuality, SkillStatus
from nextstep_os.core.skill_loader import (
    best_match,
    load_registry,
    load_skill_by_id,
    match_skills,
)


def test_registry_loads_all_skills(real_config):
    entries = load_registry(real_config)
    ids = {e.id for e in entries}
    assert {
        "neuen-skill-erstellen",
        "angebot-erstellen",
        "kundenprojekt-onboarden",
        "tages-shutdown",
    }.issubset(ids)


def test_load_skill_parses_body_and_frontmatter(real_config):
    skill = load_skill_by_id(real_config, "angebot-erstellen")
    assert skill.name == "Angebot erstellen"
    assert skill.status == SkillStatus.AKTIV
    assert skill.ampel.value == "🟡"
    assert len(skill.body) > 100
    assert "SOP" in skill.body or "Arbeitsanweisung" in skill.body


def test_match_skills_prefers_keyword_hit(real_config):
    matches = match_skills(real_config, "Ich brauche ein Angebot für einen Kunden")
    assert matches[0].skill_id == "angebot-erstellen"
    assert matches[0].quality in {MatchQuality.HOCH, MatchQuality.MITTEL}


def test_match_skills_for_meta_skill(real_config):
    matches = match_skills(real_config, "Ich möchte einen neuen Skill anlegen")
    assert matches[0].skill_id == "neuen-skill-erstellen"


def test_best_match_returns_none_for_unrelated_query(real_config):
    result = best_match(real_config, "Aktienkurs Apple heute")
    assert result is None


def test_best_match_passes_quality_threshold(real_config):
    result = best_match(real_config, "angebot für neuen kunden")
    assert result is not None
    assert result.skill_id == "angebot-erstellen"
