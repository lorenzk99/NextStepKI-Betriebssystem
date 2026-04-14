"""Tests für den Filesystem-MCP-Sandbox-Layer (Path-Guards).

Wir testen die Pfad-Normalisierung direkt (die Tools sind dünne Wrapper
um diese Guards). Damit decken wir Escape-Versuche ab, ohne das SDK
tatsächlich zu starten.
"""

from __future__ import annotations

import pytest

from mcp_servers.filesystem_db import (
    _is_under,
    _read_roots,
    _resolve_safe,
    _write_roots,
    filesystem_tool_names,
)


def test_tool_names_stable():
    names = filesystem_tool_names()
    assert "mcp__nextstep_fs__fs_read" in names
    assert "mcp__nextstep_fs__fs_append" in names
    assert len(names) == 4


def test_read_roots_cover_data_folders(isolated_config):
    roots = _read_roots(isolated_config)
    names = {r.name for r in roots}
    assert {"skills", "context", "governance", "feedback", "tasks", "meetings"}.issubset(names)


def test_write_roots_are_subset_of_read(isolated_config):
    write_roots = _write_roots(isolated_config)
    read_roots = _read_roots(isolated_config)
    for w in write_roots:
        assert _is_under(w, read_roots), f"{w} muss unter read_roots liegen"


def test_resolve_safe_accepts_absolute_under_root(isolated_config):
    skills_dir = isolated_config.paths.data / "skills"
    skill_file = skills_dir / "test.md"
    skill_file.write_text("# test", encoding="utf-8")
    resolved = _resolve_safe(str(skill_file), _read_roots(isolated_config))
    assert resolved == skill_file.resolve()


def test_resolve_safe_rejects_escape(isolated_config):
    """`data/../../etc/passwd` darf nicht durchkommen."""
    evil = str(isolated_config.paths.data / ".." / ".." / "etc" / "passwd")
    with pytest.raises(ValueError):
        _resolve_safe(evil, _read_roots(isolated_config))


def test_resolve_safe_rejects_outside_root(isolated_config, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError):
        _resolve_safe(str(outside), _read_roots(isolated_config))


def test_write_roots_reject_governance(isolated_config):
    """Governance ist read-only – Schreiben muss scheitern."""
    gov = isolated_config.paths.data / "governance" / "handbuch.md"
    with pytest.raises(ValueError):
        _resolve_safe(str(gov), _write_roots(isolated_config))


def test_write_roots_allow_feedback_entries(isolated_config):
    target = isolated_config.paths.data / "feedback" / "entries" / "new.yaml"
    resolved = _resolve_safe(str(target), _write_roots(isolated_config))
    assert resolved == target.resolve()
