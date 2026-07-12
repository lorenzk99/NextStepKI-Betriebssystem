"""Tests für das Web-Dashboard (Daten-Layer + Skill-Erstellung)."""

from __future__ import annotations

import pytest
import yaml

from nextstep_os.core.skill_loader import load_registry, load_skill_by_id
from nextstep_os.dashboard import (
    context_data,
    create_skill,
    list_skills_data,
    skill_detail_data,
    slugify,
)


# --------------------------------------------------------------------------- #
# slugify
# --------------------------------------------------------------------------- #


def test_slugify_umlauts_and_spaces():
    assert slugify("Belege prüfen") == "belege-pruefen"
    assert slugify("  Größere Anfrage!! ") == "groessere-anfrage"
    assert slugify("E-Mail-Entwurf") == "e-mail-entwurf"


# --------------------------------------------------------------------------- #
# list / detail (echtes Register)
# --------------------------------------------------------------------------- #


def test_list_skills_data_contains_new_skills(real_config):
    ids = {s["id"] for s in list_skills_data(real_config)}
    assert {
        "email-entwurf",
        "vertrag-erstellen",
        "belege-buchhaltung",
        "linkedin-beitrag",
    }.issubset(ids)


def test_skill_detail_data_has_body_and_meta(real_config):
    detail = skill_detail_data(real_config, "vertrag-erstellen")
    assert detail["ampel"] == "🔴"
    assert "REVIEW GATE" in detail["body"]
    assert detail["eingabe"]


def test_context_data_reports_filled_profiles(real_config):
    rows = {c["id"]: c for c in context_data(real_config)}
    assert rows["firmenprofil"]["befuellt"] is True
    assert rows["rollenprofil"]["befuellt"] is True


# --------------------------------------------------------------------------- #
# create_skill (isoliert)
# --------------------------------------------------------------------------- #


@pytest.fixture
def config_with_registry(isolated_config):
    """Isolierte Config mit leerem Skill-Register."""
    isolated_config.paths.skills_index.write_text("skills: []\n", encoding="utf-8")
    return isolated_config


def test_create_skill_writes_file_and_registry(config_with_registry):
    cfg = config_with_registry
    skill_id, path = create_skill(
        cfg,
        {
            "name": "Rechnung schreiben",
            "beschreibung": "Erstellt eine Rechnung.",
            "keywords": "rechnung, rechnung schreiben",
            "ampel": "🟡",
            "eingabe": "Kundendaten (Pflicht)\nLeistungszeitraum",
            "sop": "1. Daten prüfen\n2. Rechnung schreiben",
        },
    )
    assert skill_id == "rechnung-schreiben"
    assert path.exists()

    # Über den normalen Loader lesbar?
    skill = load_skill_by_id(cfg, skill_id)
    assert skill.name == "Rechnung schreiben"
    assert skill.status.value == "Entwurf"  # Default: Activation Gate
    assert skill.ampel.value == "🟡"
    assert "REVIEW GATE" in skill.body
    assert skill.eingabe == ["Kundendaten (Pflicht)", "Leistungszeitraum"]

    entries = load_registry(cfg)
    assert entries[0].id == skill_id


def test_create_skill_green_has_no_review_gate(config_with_registry):
    _, path = create_skill(
        config_with_registry, {"name": "Notiz ablegen", "ampel": "🟢"}
    )
    assert "REVIEW GATE" not in path.read_text(encoding="utf-8")


def test_create_skill_rejects_duplicate(config_with_registry):
    create_skill(config_with_registry, {"name": "Doppelt"})
    with pytest.raises(ValueError, match="existiert bereits"):
        create_skill(config_with_registry, {"name": "Doppelt"})


def test_create_skill_requires_name(config_with_registry):
    with pytest.raises(ValueError, match="Pflicht"):
        create_skill(config_with_registry, {"name": "  "})


def test_create_skill_rejects_bad_ampel(config_with_registry):
    with pytest.raises(ValueError, match="Ampel"):
        create_skill(config_with_registry, {"name": "X-Skill", "ampel": "blau"})


def test_create_skill_rollback_on_registry_conflict(config_with_registry):
    """Wenn das Register den Eintrag ablehnt, bleibt keine Waisen-Datei zurück."""
    cfg = config_with_registry
    create_skill(cfg, {"name": "Kollision"})
    # Datei manuell entfernen, Register-Eintrag bleibt → nächster Anlage-Versuch
    # schlägt im Register fehl und muss die neue Datei zurückrollen.
    (cfg.paths.skills_dir / "kollision.md").unlink()
    with pytest.raises(ValueError):
        create_skill(cfg, {"name": "Kollision"})
    assert not (cfg.paths.skills_dir / "kollision.md").exists()


def test_create_skill_frontmatter_is_valid_yaml(config_with_registry):
    _, path = create_skill(
        config_with_registry,
        {"name": "YAML Check", "beschreibung": 'Mit "Anführungszeichen": und Doppelpunkt'},
    )
    raw = path.read_text(encoding="utf-8")
    _, fm, _ = raw.split("---", 2)
    parsed = yaml.safe_load(fm)
    assert parsed["id"] == "yaml-check"
    assert "Doppelpunkt" in parsed["beschreibung"]
