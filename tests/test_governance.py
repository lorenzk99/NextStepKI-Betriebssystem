"""Tests für die Governance-Engine."""

from __future__ import annotations

from nextstep_os.core.governance import (
    check_activation_gate,
    detect_hil_markers,
    evaluate,
)
from nextstep_os.core.models import Ampel, ExecutionMode, Skill, SkillStatus
from nextstep_os.core.skill_loader import load_skill_by_id


def _skill_stub(**overrides) -> Skill:
    defaults = dict(
        id="test",
        name="Test",
        status=SkillStatus.AKTIV,
        ampel=Ampel.GRUEN,
        execution_mode=ExecutionMode.STRICT,
        body="",
    )
    defaults.update(overrides)
    return Skill(**defaults)


def test_detect_hil_markers_finds_approval_gate():
    body = """
    Schritt 1: ...
    ⏸️ **Approval Gate:** Freigabe einholen.
    Schritt 2: ...
    """
    markers = detect_hil_markers(body)
    assert len(markers) == 1
    assert markers[0].typ == "approval"


def test_detect_hil_markers_typisiert_review_und_input():
    body = "⏸️ Input Gate: Kläre offene Frage\n⏸️ Review Gate: Output prüfen"
    markers = detect_hil_markers(body)
    types = {m.typ for m in markers}
    assert types == {"input", "review"}


def test_activation_gate_warnt_bei_entwurf():
    skill = _skill_stub(status=SkillStatus.ENTWURF)
    warnings = check_activation_gate(skill)
    assert any("Entwurf" in w for w in warnings)


def test_activation_gate_blockt_archivierte_skills():
    skill = _skill_stub(status=SkillStatus.ARCHIVIERT)
    warnings = check_activation_gate(skill)
    assert any("archiviert" in w.lower() for w in warnings)


def test_evaluate_sets_review_flag_for_gelb():
    skill = _skill_stub(ampel=Ampel.GELB)
    decision = evaluate(skill)
    assert decision.requires_review is True
    assert decision.requires_approval_before_execution is False


def test_evaluate_sets_approval_flag_for_rot():
    skill = _skill_stub(ampel=Ampel.ROT)
    decision = evaluate(skill)
    assert decision.requires_approval_before_execution is True


def test_evaluate_respects_execution_mode():
    strict = _skill_stub(execution_mode=ExecutionMode.STRICT)
    search = _skill_stub(execution_mode=ExecutionMode.SEARCH)
    assert evaluate(strict).web_search_allowed is False
    assert evaluate(search).web_search_allowed is True


def test_evaluate_on_real_skill(real_config):
    skill = load_skill_by_id(real_config, "angebot-erstellen")
    decision = evaluate(skill)
    assert decision.skill_id == "angebot-erstellen"
    assert decision.darf_ausfuehren is True
