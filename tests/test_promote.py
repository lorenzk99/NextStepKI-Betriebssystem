"""Tests für Skill-Promotion (Activation-Gate-Flow über Register)."""

from __future__ import annotations

import frontmatter
import yaml

from nextstep_os.core.models import SkillStatus
from nextstep_os.core.registry import (
    load_skill_registry,
    update_skill_registry_entry,
    write_yaml,
)
from nextstep_os.core.telemetry import SkillRun, can_promote, record_run


SKILL_MD = """---
id: test-skill
name: Test Skill
status: Entwurf
owner: "[OWNER]"
ampel: "🟢"
execution_mode: Strict
nutzungsart: public
keywords: [test]
beschreibung: Ein Test-Skill.
---

## 🚦 Governance
🟢 GRÜN

## 🔧 Arbeitsanweisung (SOP)
1. Test

## ✅ Definition of Done
- ✅ Fertig
"""


def _seed_skill(config, status: str = "Entwurf") -> None:
    skill_path = config.paths.data / "skills" / "test-skill.md"
    skill_path.write_text(SKILL_MD.replace("status: Entwurf", f"status: {status}"), encoding="utf-8")
    write_yaml(
        config.paths.skills_index,
        {
            "skills": [
                {
                    "id": "test-skill",
                    "name": "Test Skill",
                    "path": "skills/test-skill.md",
                    "status": status,
                    "owner": "[OWNER]",
                    "ampel": "🟢",
                    "execution_mode": "Strict",
                    "nutzungsart": "public",
                    "keywords": ["test"],
                    "beschreibung": "Ein Test-Skill.",
                }
            ]
        },
    )


def test_update_skill_registry_entry_patches_status(isolated_config):
    _seed_skill(isolated_config)
    update_skill_registry_entry(
        isolated_config.paths.skills_index,
        "test-skill",
        {"status": SkillStatus.AKTIV.value},
    )
    entries = load_skill_registry(isolated_config.paths.skills_index)
    assert entries[0]["status"] == "Aktiv"


def test_promote_flow_with_telemetry(isolated_config):
    """End-to-End: Telemetrie → Gate → Register-Patch → Frontmatter-Patch."""
    _seed_skill(isolated_config)
    # 3 erfolgreiche Runs loggen
    for _ in range(3):
        record_run(isolated_config, SkillRun(skill_id="test-skill", status="ok"))

    darf, _ = can_promote(isolated_config, "test-skill")
    assert darf is True

    # Register patchen
    update_skill_registry_entry(
        isolated_config.paths.skills_index,
        "test-skill",
        {"status": SkillStatus.AKTIV.value},
    )
    # Frontmatter patchen
    skill_path = isolated_config.paths.data / "skills" / "test-skill.md"
    post = frontmatter.load(skill_path)
    post.metadata["status"] = SkillStatus.AKTIV.value
    skill_path.write_text(frontmatter.dumps(post, sort_keys=False), encoding="utf-8")

    # Verifizieren
    reloaded = frontmatter.load(skill_path)
    assert reloaded.metadata["status"] == "Aktiv"
    index_data = yaml.safe_load(isolated_config.paths.skills_index.read_text(encoding="utf-8"))
    assert index_data["skills"][0]["status"] == "Aktiv"


def test_promote_blocked_without_sufficient_runs(isolated_config):
    _seed_skill(isolated_config)
    record_run(isolated_config, SkillRun(skill_id="test-skill", status="ok"))
    darf, reason = can_promote(isolated_config, "test-skill")
    assert darf is False
    assert "1" in reason
