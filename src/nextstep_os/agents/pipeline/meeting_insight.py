"""Meeting-Insight-Agent.

Liest ein Meeting aus `data/meetings/inbox/` (Markdown mit Frontmatter +
Transkript-Body), erzeugt eine strukturierte Zusammenfassung und
verschiebt das Meeting in `data/meetings/briefings/`.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ..prompt_builder import build_pipeline_system_prompt
from ..sdk_bridge import AgentResult, query_os_agent


SYSTEM_PROMPT_FILE = "pipeline/meeting_insight.md"


@dataclass
class MeetingInsightResult:
    briefing_path: Path
    summary: str
    dry_run: bool


async def process_meeting(
    meeting_path: Path,
    *,
    config: Config | None = None,
) -> MeetingInsightResult:
    config = config or load_config()
    if not meeting_path.exists():
        raise FileNotFoundError(meeting_path)

    post = frontmatter.load(meeting_path)
    transkript = post.content
    meta = dict(post.metadata)
    titel = meta.get("titel") or meeting_path.stem

    system_prompt = build_pipeline_system_prompt(config, SYSTEM_PROMPT_FILE)
    user_message = (
        f"Meeting: **{titel}**\n"
        f"Meta: {meta}\n\n"
        "Erstelle eine strukturierte Zusammenfassung nach den Vorgaben "
        "des System-Prompts. Verwende folgende Rohdaten:\n\n"
        f"---\n{transkript.strip()}\n---"
    )

    result: AgentResult = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=config.models.pipeline,
    )

    # Fehler/DryRun: Meeting bleibt in der Inbox (Retry möglich), es wird
    # KEIN Briefing mit Fehlertext erzeugt und nichts archiviert.
    if result.error:
        raise RuntimeError(
            f"Meeting-Insight fehlgeschlagen für `{meeting_path.name}`: {result.error}"
        )
    if result.dry_run:
        return MeetingInsightResult(
            briefing_path=meeting_path, summary=result.text, dry_run=True
        )

    # Briefing schreiben
    briefings = config.paths.briefings_dir
    briefings.mkdir(parents=True, exist_ok=True)
    briefing_path = briefings / meeting_path.name

    meta_out = {
        **meta,
        "status": "Zusammengefasst",
        "zusammengefasst_am": datetime.now().isoformat(timespec="seconds"),
        "pipeline_stage": "meeting_insight",
    }
    post_out = frontmatter.Post(
        content=result.text.strip() + "\n\n---\n\n## Original-Transkript\n\n" + transkript.strip(),
        **meta_out,
    )
    with briefing_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post_out, sort_keys=False))

    # Original archivieren (aus inbox entfernen)
    archive_dir = config.paths.meetings_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(meeting_path), str(archive_dir / meeting_path.name))

    return MeetingInsightResult(
        briefing_path=briefing_path, summary=result.text, dry_run=result.dry_run
    )


def run_once(meeting_path: Path, *, config: Config | None = None) -> MeetingInsightResult:
    return asyncio.run(process_meeting(meeting_path, config=config))
