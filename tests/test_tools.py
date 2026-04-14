"""Tests für Tool-Allowlist-Logik."""

from __future__ import annotations

from nextstep_os.core.models import (
    Ampel,
    ExecutionMode,
    Skill,
    SkillContext,
    SkillStatus,
)
from nextstep_os.core.tools import (
    FS_READ_TOOLS,
    FS_WRITE_TOOLS,
    WEB_SEARCH_TOOLS,
    resolve_tools_for_skill,
)


def _mk_skill(**kwargs) -> Skill:
    defaults = dict(
        id="test-skill",
        name="Test",
        status=SkillStatus.AKTIV,
        ampel=Ampel.GELB,
        execution_mode=ExecutionMode.STRICT,
        keywords=[],
        beschreibung="",
        context=SkillContext(),
        body="",
    )
    defaults.update(kwargs)
    return Skill(**defaults)


def test_freitext_has_no_tools(isolated_config):
    allowed, mcp = resolve_tools_for_skill(isolated_config, None)
    assert allowed == []
    assert mcp == {}


def test_gelb_skill_has_only_read_tools(isolated_config):
    skill = _mk_skill(ampel=Ampel.GELB)
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    assert set(FS_READ_TOOLS).issubset(allowed)
    assert not set(FS_WRITE_TOOLS) & set(allowed)


def test_gruen_skill_gets_write_tools(isolated_config):
    skill = _mk_skill(ampel=Ampel.GRUEN)
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    assert set(FS_READ_TOOLS).issubset(allowed)
    assert set(FS_WRITE_TOOLS).issubset(allowed)


def test_rot_skill_has_only_read(isolated_config):
    skill = _mk_skill(ampel=Ampel.ROT)
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    assert set(FS_READ_TOOLS).issubset(allowed)
    assert not set(FS_WRITE_TOOLS) & set(allowed)


def test_search_mode_adds_web_search(isolated_config):
    skill = _mk_skill(execution_mode=ExecutionMode.SEARCH)
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    for t in WEB_SEARCH_TOOLS:
        assert t in allowed


def test_strict_mode_no_web_search(isolated_config):
    skill = _mk_skill(execution_mode=ExecutionMode.STRICT)
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    for t in WEB_SEARCH_TOOLS:
        assert t not in allowed


def test_explicit_tools_override(isolated_config):
    skill = _mk_skill(ampel=Ampel.GRUEN, tools=["only_this_tool"])
    allowed, _ = resolve_tools_for_skill(isolated_config, skill)
    assert allowed == ["only_this_tool"]


def test_include_filesystem_false_drops_fs_tools(isolated_config):
    skill = _mk_skill(ampel=Ampel.GRUEN)
    allowed, _ = resolve_tools_for_skill(
        isolated_config, skill, include_filesystem=False
    )
    assert not set(FS_READ_TOOLS) & set(allowed)
    assert not set(FS_WRITE_TOOLS) & set(allowed)
