"""Pipeline-Runner.

Zwei Modi:

- **once()**: Einmalige End-to-End-Ausführung aller Stages über alle
  offenen Dateien (`data/meetings/inbox/*.md`, `data/meetings/briefings/*.md`,
  `data/tasks/*.md`).
- **watch()**: Event-basiert via watchdog – triggert die Stages bei
  Status-Änderungen / neuen Dateien.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from ..config import Config, load_config
from .pipeline import feedback_logger, meeting_insight, skill_executor, skill_scout, task_extractor


@dataclass
class PipelineReport:
    meetings_processed: list[Path] = field(default_factory=list)
    briefings_processed: list[Path] = field(default_factory=list)
    tasks_scouted: list[Path] = field(default_factory=list)
    tasks_executed: list[Path] = field(default_factory=list)
    tasks_logged: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Meetings verarbeitet:  {len(self.meetings_processed)}",
            f"Briefings verarbeitet: {len(self.briefings_processed)}",
            f"Tasks gescoutet:       {len(self.tasks_scouted)}",
            f"Tasks ausgeführt:      {len(self.tasks_executed)}",
            f"Feedback geloggt:      {len(self.tasks_logged)}",
            f"Fehler:                {len(self.errors)}",
        ]
        for p, err in self.errors:
            lines.append(f"  ✖ {p.name}: {err}")
        return "\n".join(lines)


def _status(path: Path) -> str:
    try:
        post = frontmatter.load(path)
        return str(post.metadata.get("status", ""))
    except Exception:  # noqa: BLE001
        return ""


async def run_once(config: Config | None = None) -> PipelineReport:
    """Ein kompletter Pipeline-Durchlauf (once-and-done)."""
    config = config or load_config()
    report = PipelineReport()

    # 1) Meeting-Insights
    for meeting in sorted(config.paths.meetings_inbox.glob("*.md")):
        try:
            await meeting_insight.process_meeting(meeting, config=config)
            report.meetings_processed.append(meeting)
        except Exception as exc:  # noqa: BLE001
            report.errors.append((meeting, f"meeting_insight: {exc}"))

    # 2) Task-Extraction aus neuen Briefings
    for briefing in sorted(config.paths.briefings_dir.glob("*.md")):
        if _status(briefing) != "Zusammengefasst":
            continue
        try:
            await task_extractor.process_briefing(briefing, config=config)
            report.briefings_processed.append(briefing)
        except Exception as exc:  # noqa: BLE001
            report.errors.append((briefing, f"task_extractor: {exc}"))

    # 3) Skill-Scout für neue Tasks
    for task in sorted(config.paths.tasks_dir.glob("*.md")):
        if _status(task) != "Neu":
            continue
        try:
            await skill_scout.process_task(task, config=config)
            report.tasks_scouted.append(task)
        except Exception as exc:  # noqa: BLE001
            report.errors.append((task, f"skill_scout: {exc}"))

    # 4) Skill-Executor für zugewiesene Tasks
    for task in sorted(config.paths.tasks_dir.glob("*.md")):
        if _status(task) != "Skill zugewiesen":
            continue
        try:
            await skill_executor.execute_task(task, config=config)
            report.tasks_executed.append(task)
        except Exception as exc:  # noqa: BLE001
            report.errors.append((task, f"skill_executor: {exc}"))

    # 5) Feedback-Logger für ausgeführte Tasks
    for task in sorted(config.paths.tasks_dir.glob("*.md")):
        if _status(task) != "Skill ausgeführt":
            continue
        try:
            await feedback_logger.log_task(task, config=config)
            report.tasks_logged.append(task)
        except Exception as exc:  # noqa: BLE001
            report.errors.append((task, f"feedback_logger: {exc}"))

    return report


def run_once_sync(config: Config | None = None) -> PipelineReport:
    return asyncio.run(run_once(config))


# --------------------------------------------------------------------------- #
# Watcher
# --------------------------------------------------------------------------- #


def watch(config: Config | None = None, *, interval: float = 5.0) -> None:
    """Polling-basierter Watcher: alle `interval` Sekunden Pipeline-Run."""
    config = config or load_config()
    print(f"[runner] Watching data-Ordner, Intervall={interval}s (Ctrl+C zum Beenden)")
    try:
        while True:
            report = run_once_sync(config)
            if any([
                report.meetings_processed,
                report.briefings_processed,
                report.tasks_scouted,
                report.tasks_executed,
                report.tasks_logged,
            ]):
                print(report.summary())
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[runner] Beendet.")
