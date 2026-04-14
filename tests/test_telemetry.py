"""Tests für Skill-Telemetrie."""

from __future__ import annotations

import json

import pytest

from nextstep_os.core.telemetry import (
    SkillRun,
    aggregate,
    can_promote,
    read_runs,
    record_run,
    telemetry_path,
    track,
)


def test_record_and_read_roundtrip(isolated_config):
    run = SkillRun(
        skill_id="angebot-erstellen",
        source="os_agent",
        status="ok",
        duration_s=1.23,
        tokens_in=100,
        tokens_out=50,
    )
    record_run(isolated_config, run)
    runs = read_runs(isolated_config)
    assert len(runs) == 1
    assert runs[0].skill_id == "angebot-erstellen"
    assert runs[0].tokens_in == 100
    assert runs[0].status == "ok"


def test_jsonl_is_append_only(isolated_config):
    record_run(isolated_config, SkillRun(skill_id="a", status="ok"))
    record_run(isolated_config, SkillRun(skill_id="a", status="error"))
    record_run(isolated_config, SkillRun(skill_id="b", status="dry_run"))

    path = telemetry_path(isolated_config)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    for line in lines:
        json.loads(line)  # jede Zeile ist gültiges JSON


def test_read_runs_skips_invalid_lines(isolated_config):
    path = telemetry_path(isolated_config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"skill_id": "ok", "status": "ok"}\n'
        "invalid json line\n"
        '{"skill_id": "ok2", "status": "ok"}\n',
        encoding="utf-8",
    )
    runs = read_runs(isolated_config)
    assert [r.skill_id for r in runs] == ["ok", "ok2"]


def test_track_contextmanager_records_duration(isolated_config):
    with track(isolated_config, "angebot-erstellen", source="os_agent") as run:
        run.tokens_in = 42
        run.tokens_out = 7
    runs = read_runs(isolated_config)
    assert len(runs) == 1
    assert runs[0].tokens_in == 42
    assert runs[0].duration_s >= 0.0
    assert runs[0].status == "ok"


def test_track_captures_exception(isolated_config):
    with pytest.raises(RuntimeError):
        with track(isolated_config, "broken-skill"):
            raise RuntimeError("boom")
    runs = read_runs(isolated_config)
    assert len(runs) == 1
    assert runs[0].status == "error"
    assert "boom" in (runs[0].error or "")


def test_aggregate_groups_per_skill(isolated_config):
    record_run(isolated_config, SkillRun(skill_id="a", status="ok", duration_s=1.0, tokens_in=10))
    record_run(isolated_config, SkillRun(skill_id="a", status="ok", duration_s=3.0, tokens_in=20))
    record_run(isolated_config, SkillRun(skill_id="a", status="error", duration_s=2.0))
    record_run(isolated_config, SkillRun(skill_id="a", status="dry_run"))
    record_run(isolated_config, SkillRun(skill_id="b", status="ok", duration_s=0.5))

    stats = aggregate(read_runs(isolated_config))
    assert stats["a"].total == 4
    assert stats["a"].ok == 2
    assert stats["a"].errors == 1
    assert stats["a"].dry_runs == 1
    assert stats["a"].avg_duration_s == 2.0  # (1+3+2)/3, dry_run ausgeschlossen
    assert stats["a"].total_tokens_in == 30
    assert stats["a"].success_rate == pytest.approx(2 / 3)
    assert stats["b"].total == 1


def test_can_promote_requires_min_runs(isolated_config):
    record_run(isolated_config, SkillRun(skill_id="new-skill", status="ok"))
    record_run(isolated_config, SkillRun(skill_id="new-skill", status="ok"))
    darf, reason = can_promote(isolated_config, "new-skill", min_runs=3, min_success=3)
    assert darf is False
    assert "2" in reason


def test_can_promote_excludes_dry_runs(isolated_config):
    for _ in range(5):
        record_run(isolated_config, SkillRun(skill_id="dry-skill", status="dry_run"))
    darf, _ = can_promote(isolated_config, "dry-skill")
    assert darf is False


def test_can_promote_success_threshold(isolated_config):
    record_run(isolated_config, SkillRun(skill_id="x", status="ok"))
    record_run(isolated_config, SkillRun(skill_id="x", status="ok"))
    record_run(isolated_config, SkillRun(skill_id="x", status="error"))
    darf, _ = can_promote(isolated_config, "x", min_runs=3, min_success=3)
    assert darf is False


def test_can_promote_success(isolated_config):
    for _ in range(3):
        record_run(
            isolated_config,
            SkillRun(skill_id="ready", status="ok", duration_s=1.5),
        )
    darf, reason = can_promote(isolated_config, "ready")
    assert darf is True
    assert "erfolgreiche" in reason.lower() or "runs" in reason.lower()
