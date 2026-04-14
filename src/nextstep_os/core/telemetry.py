"""Skill-Telemetrie: JSONL-Log aller Skill-Runs.

Pro Skill-Run wird eine Zeile in `data/telemetry/skill_runs.jsonl`
geschrieben. Struktur:

    {
        "ts": "2026-04-14T10:23:11",
        "skill_id": "angebot-erstellen",
        "source": "os_agent" | "pipeline",
        "status": "ok" | "error" | "dry_run" | "blocked",
        "duration_s": 4.82,
        "hil_count": 1,
        "tokens_in": 3200,
        "tokens_out": 740,
        "cache_read": 1800,
        "cache_write": 1400,
        "error": null
    }

Für Aggregation via `stats`-CLI und Activation-Gate (`promote`).
"""

from __future__ import annotations

import json
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Iterator

from ..config import Config


@dataclass
class SkillRun:
    skill_id: str
    source: str = "os_agent"  # os_agent | pipeline | standalone
    status: str = "ok"  # ok | error | dry_run | blocked
    duration_s: float = 0.0
    hil_count: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    error: str | None = None
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def telemetry_path(config: Config) -> Path:
    """Zentrale Telemetry-Datei."""
    return config.paths.data / "telemetry" / "skill_runs.jsonl"


def record_run(config: Config, run: SkillRun) -> Path:
    """Hänge einen Skill-Run als JSONL-Zeile an."""
    path = telemetry_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")
    return path


def read_runs(config: Config) -> list[SkillRun]:
    """Lade alle Skill-Runs."""
    path = telemetry_path(config)
    if not path.exists():
        return []
    runs: list[SkillRun] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                runs.append(SkillRun(**data))
            except Exception:  # noqa: BLE001
                continue
    return runs


@contextmanager
def track(
    config: Config,
    skill_id: str,
    *,
    source: str = "os_agent",
) -> Iterator[SkillRun]:
    """Kontext-Manager: misst Dauer und persistiert Run am Ende.

    Usage::

        with track(cfg, "angebot-erstellen") as run:
            result = await query_os_agent(...)
            run.tokens_in = result.tokens_in
            run.tokens_out = result.tokens_out
            run.hil_count = len(governance.hil_markers)
    """
    run = SkillRun(skill_id=skill_id, source=source)
    t0 = perf_counter()
    try:
        yield run
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.error = str(exc)
        raise
    finally:
        run.duration_s = round(perf_counter() - t0, 3)
        record_run(config, run)


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


@dataclass
class SkillStats:
    skill_id: str
    total: int = 0
    ok: int = 0
    errors: int = 0
    dry_runs: int = 0
    avg_duration_s: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cache_read: int = 0

    @property
    def success_rate(self) -> float:
        """Quote erfolgreicher nicht-DryRun-Runs."""
        real = self.total - self.dry_runs
        return (self.ok / real) if real else 0.0


def aggregate(runs: list[SkillRun]) -> dict[str, SkillStats]:
    """Gruppiere Runs pro Skill und berechne Summen/Durchschnitte."""
    grouped: dict[str, list[SkillRun]] = defaultdict(list)
    for r in runs:
        grouped[r.skill_id].append(r)

    stats: dict[str, SkillStats] = {}
    for sid, items in grouped.items():
        total = len(items)
        ok = sum(1 for r in items if r.status == "ok")
        errors = sum(1 for r in items if r.status == "error")
        dry = sum(1 for r in items if r.status == "dry_run")
        durations = [r.duration_s for r in items if r.status != "dry_run"]
        avg = sum(durations) / len(durations) if durations else 0.0
        stats[sid] = SkillStats(
            skill_id=sid,
            total=total,
            ok=ok,
            errors=errors,
            dry_runs=dry,
            avg_duration_s=round(avg, 3),
            total_tokens_in=sum(r.tokens_in for r in items),
            total_tokens_out=sum(r.tokens_out for r in items),
            total_cache_read=sum(r.cache_read for r in items),
        )
    return stats


# --------------------------------------------------------------------------- #
# Activation-Gate-Helfer
# --------------------------------------------------------------------------- #


def can_promote(
    config: Config, skill_id: str, *, min_runs: int = 3, min_success: int = 3
) -> tuple[bool, str]:
    """Prüft, ob ein Skill aktiviert werden darf.

    Rückgabe: `(darf, begründung)`.
    """
    runs = [r for r in read_runs(config) if r.skill_id == skill_id]
    real = [r for r in runs if r.status != "dry_run"]
    ok = [r for r in real if r.status == "ok"]
    if len(real) < min_runs:
        return False, (
            f"Nur {len(real)} Produktiv-Runs registriert (mind. {min_runs} nötig). "
            f"Bitte mehrere Testläufe mit echten Daten durchführen."
        )
    if len(ok) < min_success:
        return False, (
            f"Nur {len(ok)}/{len(real)} Runs erfolgreich. "
            f"Fehler-Quote zu hoch für Aktivierung."
        )
    return True, f"{len(ok)} erfolgreiche Runs, Durchschnitts-Dauer "\
        f"{sum(r.duration_s for r in ok)/len(ok):.2f}s."
