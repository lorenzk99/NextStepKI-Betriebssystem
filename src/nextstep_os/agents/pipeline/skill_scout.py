"""Skill-Scout-Agent.

Liest einen Task und ordnet einen Skill zu (oder markiert ihn für die
Meta-Skill-Route: »Neuen Skill erstellen«).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ...core.models import MatchQuality, SkillMatch, TaskStatus, to_yaml_safe
from ...core.skill_loader import match_skills


@dataclass
class ScoutDecision:
    task_path: Path
    match: SkillMatch | None
    route: str  # "skill_executor" | "meta_skill" | "needs_review"
    candidates: list[SkillMatch]


def _choose_route(match: SkillMatch | None) -> str:
    if match is None or match.quality == MatchQuality.NONE:
        return "meta_skill"
    if match.quality == MatchQuality.NIEDRIG:
        return "needs_review"
    return "skill_executor"


async def process_task(task_path: Path, *, config: Config | None = None) -> ScoutDecision:
    config = config or load_config()
    post = frontmatter.load(task_path)
    titel = post.metadata.get("titel") or task_path.stem
    body = post.content or ""
    query = f"{titel}\n{body}"

    candidates = match_skills(config, query, limit=5)
    top = candidates[0] if candidates else None
    if top and top.quality == MatchQuality.NONE:
        top = None
    route = _choose_route(top)

    # Task-Frontmatter updaten
    post.metadata["status"] = (
        TaskStatus.SKILL_ZUGEWIESEN.value
        if route == "skill_executor"
        else TaskStatus.WARTET_AUF_REVIEW.value
    )
    post.metadata["zugewiesener_skill"] = top.skill_id if top else None
    post.metadata["skill_scout"] = to_yaml_safe(
        {
            "route": route,
            "top_match": top.model_dump() if top else None,
            "candidates": [c.model_dump() for c in candidates],
        }
    )
    with task_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))

    return ScoutDecision(task_path=task_path, match=top, route=route, candidates=candidates)


def run_once(task_path: Path, *, config: Config | None = None) -> ScoutDecision:
    return asyncio.run(process_task(task_path, config=config))
