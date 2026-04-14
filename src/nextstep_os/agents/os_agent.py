"""Der OS-Agent – zentraler interaktiver Agent des KI-Betriebssystems.

Phasen-Pipeline (siehe `system_prompts/os_agent.md`):
    1. Boot          – persönlicher Kontext (Stufe 1) laden.
    2. Skill-Select  – via Semantic Matching passenden Skill finden.
    3. Kontext-Load  – Stufe 2 für Skill laden.
    4. Governance    – Ampel, HIL, Execution-Mode prüfen.
    5. Execute       – SDK-Call mit vollständigem Prompt.
    6. Validate      – Output-Validierung + HIL-Gates.
    7. Feedback      – Silent Patch / Feedback-DB.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from ..config import Config, load_config
from ..core.context_loader import (
    ContextBundle,
    load_boot_context,
    load_context_for_skill,
)
from ..core.governance import GovernanceDecision, evaluate
from ..core.models import Skill, SkillMatch
from ..core.skill_loader import best_match, load_skill_by_id, match_skills
from .prompt_builder import build_os_agent_system_prompt
from .sdk_bridge import AgentResult, query_os_agent


@dataclass
class OSAgentState:
    """Zustand einer OS-Agent-Session."""

    config: Config
    boot_context: ContextBundle
    active_skill: Skill | None = None
    task_context: ContextBundle | None = None
    governance: GovernanceDecision | None = None
    match_candidates: list[SkillMatch] = field(default_factory=list)


async def boot(config: Config | None = None) -> OSAgentState:
    """Phase 1: Boot-Kontext laden (persönlicher Kern + Governance)."""
    config = config or load_config()
    boot_ctx = load_boot_context(config)
    return OSAgentState(config=config, boot_context=boot_ctx)


async def select_skill(state: OSAgentState, user_request: str) -> SkillMatch | None:
    """Phase 2+3: Skill matchen, Kontext laden, Governance prüfen.

    Setzt state.active_skill, state.task_context, state.governance.
    Liefert den besten Match zurück (kann None sein bei keinem Treffer).
    """
    candidates = match_skills(state.config, user_request, limit=5)
    state.match_candidates = candidates

    top = best_match(state.config, user_request)
    if top is None:
        return None

    skill = load_skill_by_id(state.config, top.skill_id)
    state.active_skill = skill
    state.task_context = load_context_for_skill(state.config, skill)
    state.governance = evaluate(skill)
    return top


def assemble_prompt(state: OSAgentState) -> str:
    """Baue den finalen Systemprompt aus aktuellem State."""
    return build_os_agent_system_prompt(
        state.config,
        boot_context=state.boot_context,
        active_skill=state.active_skill,
        task_context=state.task_context,
        governance=state.governance,
    )


async def handle(
    state: OSAgentState,
    user_message: str,
    *,
    auto_select: bool = True,
) -> AgentResult:
    """Vollständiger Durchlauf: Skill-Select → Prompt → SDK-Call."""
    if auto_select and state.active_skill is None:
        await select_skill(state, user_message)
    system_prompt = assemble_prompt(state)
    return await query_os_agent(
        state.config,
        system_prompt=system_prompt,
        user_message=user_message,
    )


# --------------------------------------------------------------------------- #
# Synchroner Helper (für CLI)
# --------------------------------------------------------------------------- #


def run_once(user_message: str, *, config: Config | None = None) -> dict[str, Any]:
    """Ein einzelner Durchlauf – synchroner Helper für CLI/Tests."""

    async def _go() -> dict[str, Any]:
        st = await boot(config)
        top = await select_skill(st, user_message)
        result = await handle(st, user_message, auto_select=False)
        return {
            "match": top.model_dump() if top else None,
            "candidates": [c.model_dump() for c in st.match_candidates],
            "governance": st.governance.summary() if st.governance else None,
            "skill": st.active_skill.id if st.active_skill else None,
            "output": result.text,
            "dry_run": result.dry_run,
        }

    return asyncio.run(_go())
