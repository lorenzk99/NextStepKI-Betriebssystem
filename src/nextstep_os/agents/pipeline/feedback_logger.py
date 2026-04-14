"""Feedback-Logger-Agent.

Letzte Stufe der Pipeline: Für jeden erledigten Task einen Feedback-Entry
in die Feedback-DB schreiben und (optional) die zugehörige Skill-MD per
Silent Patch ergänzen.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ...core.feedback import record, silent_patch_skill
from ...core.models import FeedbackEntry, FeedbackTyp, TaskStatus
from ...core.skill_loader import load_skill_by_id


@dataclass
class FeedbackLogResult:
    task_path: Path
    feedback: FeedbackEntry
    patched_skill: bool


async def log_task(
    task_path: Path,
    *,
    learning: str = "",
    typ: FeedbackTyp = FeedbackTyp.ERFOLG,
    config: Config | None = None,
) -> FeedbackLogResult:
    config = config or load_config()
    post = frontmatter.load(task_path)
    meta = dict(post.metadata)
    skill_id = meta.get("zugewiesener_skill")
    titel = meta.get("titel") or task_path.stem
    status = meta.get("status", "")

    skill_path: Path | None = None
    patched = False
    if skill_id:
        try:
            sk = load_skill_by_id(config, skill_id)
            skill_path = sk.path
        except KeyError:
            skill_path = None

    fb = record(
        config,
        titel=f"Task `{titel}` abgeschlossen",
        typ=typ,
        was_ist_passiert=f"Task `{task_path.name}` wurde via Skill `{skill_id}` "
        f"bearbeitet (Status: {status}).",
        learning=learning,
        umgesetzte_aktion="",
        skill_id=skill_id,
        task_ref=str(task_path),
        patch_skill=bool(learning and skill_path),
        skill_path=skill_path,
    )
    if learning and skill_path:
        patched = True

    # Task-Status abschließen
    post.metadata["status"] = TaskStatus.ERLEDIGT.value
    post.metadata["feedback_ref"] = str(fb.path)
    with task_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))

    return FeedbackLogResult(task_path=task_path, feedback=fb, patched_skill=patched)


def run_once(
    task_path: Path,
    *,
    learning: str = "",
    typ: FeedbackTyp = FeedbackTyp.ERFOLG,
    config: Config | None = None,
) -> FeedbackLogResult:
    return asyncio.run(log_task(task_path, learning=learning, typ=typ, config=config))
