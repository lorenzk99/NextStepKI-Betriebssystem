"""Skill-Executor-Agent.

Führt einen Task mit zugewiesenem Skill aus. Baut den vollständigen
Systemprompt (OS-Anweisung + Skill-SOP + Kontext + Governance) und ruft
das Claude Agent SDK.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ...core.context_loader import load_boot_context, load_context_for_skill
from ...core.governance import evaluate
from ...core.models import TaskStatus
from ...core.skill_loader import load_skill_by_id
from ...core.telemetry import track
from ...core.tools import resolve_tools_for_skill
from ..prompt_builder import build_os_agent_system_prompt
from ..sdk_bridge import AgentResult, query_os_agent


@dataclass
class ExecutionResult:
    task_path: Path
    skill_id: str
    output: str
    status: TaskStatus
    dry_run: bool
    blocked_reason: str | None = None


async def execute_task(task_path: Path, *, config: Config | None = None) -> ExecutionResult:
    config = config or load_config()
    post = frontmatter.load(task_path)
    meta = dict(post.metadata)
    skill_id = meta.get("zugewiesener_skill")
    if not skill_id:
        raise ValueError(f"Task `{task_path.name}` hat keinen zugewiesenen Skill.")

    skill = load_skill_by_id(config, skill_id)
    governance = evaluate(skill)

    # Blockade-Fälle
    if not governance.darf_ausfuehren:
        post.metadata["status"] = TaskStatus.FEHLER.value
        post.metadata["fehler_grund"] = "Skill ist archiviert / nicht ausführbar"
        with task_path.open("w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post, sort_keys=False))
        return ExecutionResult(
            task_path=task_path,
            skill_id=skill_id,
            output="",
            status=TaskStatus.FEHLER,
            dry_run=False,
            blocked_reason="Skill nicht ausführbar",
        )

    boot_ctx = load_boot_context(config)
    task_ctx = load_context_for_skill(config, skill)
    system_prompt = build_os_agent_system_prompt(
        config,
        boot_context=boot_ctx,
        active_skill=skill,
        task_context=task_ctx,
        governance=governance,
    )
    user_message = (
        f"Task: **{meta.get('titel') or task_path.stem}**\n"
        f"Priorität: {meta.get('prioritaet', '')}\n"
        f"Fällig: {meta.get('faellig', '-')}\n\n"
        "Arbeitsanweisung: Folge dem SOP des aktiven Skills. Produziere den "
        "Output gemäß Definition of Done. Bei HIL-Gates pausiere und frage "
        "explizit nach.\n\n"
        f"---\nTask-Body:\n{post.content}\n---"
    )

    allowed_tools, mcp_servers = resolve_tools_for_skill(config, skill)
    with track(config, skill.id, source="pipeline") as run:
        result: AgentResult = await query_os_agent(
            config,
            system_prompt=system_prompt,
            user_message=user_message,
            model=config.models.pipeline,
            allowed_tools=allowed_tools or None,
            mcp_servers=mcp_servers or None,
        )
        run.tokens_in = result.tokens_in
        run.tokens_out = result.tokens_out
        run.cache_read = result.cache_read
        run.cache_write = result.cache_write
        run.hil_count = len(governance.hil_markers)
        if result.dry_run:
            run.status = "dry_run"
        elif result.error:
            run.status = "error"
            run.error = result.error

    # Fehler/DryRun: Task NICHT als ausgeführt markieren.
    if result.error:
        post.metadata["status"] = TaskStatus.FEHLER.value
        post.metadata["fehler_grund"] = result.error
        with task_path.open("w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post, sort_keys=False))
        return ExecutionResult(
            task_path=task_path,
            skill_id=skill_id,
            output=result.text,
            status=TaskStatus.FEHLER,
            dry_run=False,
            blocked_reason=f"Agent-Fehler: {result.error}",
        )
    if result.dry_run:
        # Kein API-Key: Status unverändert lassen (Retry sobald Key da ist)
        try:
            unchanged = TaskStatus(meta.get("status", TaskStatus.SKILL_ZUGEWIESEN.value))
        except ValueError:
            unchanged = TaskStatus.SKILL_ZUGEWIESEN
        return ExecutionResult(
            task_path=task_path,
            skill_id=skill_id,
            output=result.text,
            status=unchanged,
            dry_run=True,
            blocked_reason="DryRun — kein API-Key",
        )

    # Status je nach Ampel
    new_status = (
        TaskStatus.WARTET_AUF_REVIEW
        if governance.requires_review
        else TaskStatus.SKILL_AUSGEFUEHRT
    )
    post.metadata["status"] = new_status.value
    post.metadata["ausgefuehrt_am"] = datetime.now().isoformat(timespec="seconds")
    post.metadata["pipeline_stage"] = "skill_executor"
    post.content = (
        (post.content or "").rstrip()
        + "\n\n---\n\n## 🤖 Skill-Executor-Output\n\n"
        + result.text.strip()
        + "\n"
    )
    with task_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))

    return ExecutionResult(
        task_path=task_path,
        skill_id=skill_id,
        output=result.text,
        status=new_status,
        dry_run=result.dry_run,
    )


def run_once(task_path: Path, *, config: Config | None = None) -> ExecutionResult:
    return asyncio.run(execute_task(task_path, config=config))
