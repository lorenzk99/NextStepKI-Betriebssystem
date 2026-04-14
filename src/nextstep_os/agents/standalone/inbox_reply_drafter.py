"""Inbox-Reply-Drafter-Agent.

Nimmt eine E-Mail (als Markdown/Text-Datei oder als Freitext) entgegen
und entwirft eine Antwort gemäß `system_prompts/standalone/inbox_reply_drafter.md`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from ...config import Config, load_config
from ...core.context_loader import load_boot_context
from ..prompt_builder import build_pipeline_system_prompt
from ..sdk_bridge import AgentResult, query_os_agent


SYSTEM_PROMPT_FILE = "standalone/inbox_reply_drafter.md"


@dataclass
class ReplyDraftResult:
    reply_text: str
    dry_run: bool


async def draft_reply(
    mail_text: str,
    *,
    config: Config | None = None,
    mit_boot_kontext: bool = True,
) -> ReplyDraftResult:
    config = config or load_config()
    extra = ""
    if mit_boot_kontext:
        bundle = load_boot_context(config)
        extra = bundle.render()
    system_prompt = build_pipeline_system_prompt(
        config, SYSTEM_PROMPT_FILE, extra_context=extra
    )
    user_message = (
        "Entwirf eine Antwort auf folgende E-Mail. Gib **nur** den "
        "Antworttext aus, keine Meta-Kommentare.\n\n"
        f"---\n{mail_text.strip()}\n---"
    )
    result: AgentResult = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=config.models.pipeline,
    )
    return ReplyDraftResult(reply_text=result.text, dry_run=result.dry_run)


def run_once(mail_text: str, *, config: Config | None = None) -> ReplyDraftResult:
    return asyncio.run(draft_reply(mail_text, config=config))


def run_on_file(path: Path, *, config: Config | None = None) -> ReplyDraftResult:
    return run_once(path.read_text(encoding="utf-8"), config=config)
