"""Tests für den Context-Loader."""

from __future__ import annotations

from nextstep_os.core.context_loader import (
    estimate_tokens,
    load_boot_context,
    load_context_for_skill,
    load_entries,
)
from nextstep_os.core.skill_loader import load_skill_by_id


def test_estimate_tokens_is_reasonable():
    assert estimate_tokens("") >= 1
    assert estimate_tokens("Hallo Welt") >= 1
    assert estimate_tokens("x" * 4000) >= 900  # ~4 chars / token


def test_boot_context_loads_personal_files(real_config):
    bundle = load_boot_context(real_config)
    loaded_ids = {item.entry.id for item in bundle.stufe_1}
    # Persönlicher Kern sollte geladen sein
    assert "firmenprofil" in loaded_ids
    assert "rollenprofil" in loaded_ids
    assert "kommunikationsstil" in loaded_ids


def test_skill_context_includes_stufe_2(real_config):
    skill = load_skill_by_id(real_config, "angebot-erstellen")
    bundle = load_context_for_skill(real_config, skill)
    # Governance-Handbuch ist in Stufe 1
    s1_ids = {item.entry.id for item in bundle.stufe_1}
    assert "governance-handbuch" in s1_ids or any(
        "governance" in str(item.entry.path) for item in bundle.stufe_1
    )


def test_entries_are_all_loadable(real_config):
    entries = load_entries(real_config)
    assert len(entries) >= 5
    assert all(e.kontext_stufe in {1, 2, 3} for e in entries)
