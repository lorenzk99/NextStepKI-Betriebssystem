"""Task-Extractor-Agent.

Liest ein Briefing aus `data/meetings/briefings/`, extrahiert Tasks und
schreibt jeden Task als eigene MD-Datei in `data/tasks/` (Status `Neu`).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ...core.feedback import _slugify
from ...core.models import Prioritaet, Task, TaskStatus, now_iso, to_yaml_safe
from ..prompt_builder import build_pipeline_system_prompt
from ..sdk_bridge import AgentResult, query_os_agent


SYSTEM_PROMPT_FILE = "pipeline/task_extractor.md"


@dataclass
class TaskExtractResult:
    tasks: list[Task] = field(default_factory=list)
    raw_output: str = ""
    dry_run: bool = False


# Einfaches Output-Format im Prompt vorgesehen:
#   - [ ] <Titel> (Priorität: hoch/mittel/niedrig; fällig: YYYY-MM-DD)
_TASK_LINE_RE = re.compile(
    r"^[-*]\s*\[\s?\]\s*(?P<titel>[^(\n]+?)"
    r"(?:\s*\((?P<meta>[^)]+)\))?\s*$",
    re.IGNORECASE,
)

_PRIO_MAP = {
    "hoch": Prioritaet.HOCH,
    "mittel": Prioritaet.MITTEL,
    "niedrig": Prioritaet.NIEDRIG,
    "high": Prioritaet.HOCH,
    "medium": Prioritaet.MITTEL,
    "low": Prioritaet.NIEDRIG,
}


def _parse_meta(raw: str) -> tuple[Prioritaet, date | None]:
    prio = Prioritaet.MITTEL
    faellig: date | None = None
    for fragment in re.split(r"[;,]", raw or ""):
        part = fragment.strip().lower()
        if ":" in part:
            key, _, val = part.partition(":")
            key, val = key.strip(), val.strip()
            if key.startswith("prio"):
                prio = _PRIO_MAP.get(val, Prioritaet.MITTEL)
            elif key.startswith("fä") or key.startswith("fa") or key == "due":
                try:
                    faellig = date.fromisoformat(val)
                except ValueError:
                    pass
    return prio, faellig


def parse_tasks(raw_output: str, meeting_ref: str | None = None) -> list[Task]:
    tasks: list[Task] = []
    for i, line in enumerate(raw_output.splitlines(), 1):
        m = _TASK_LINE_RE.match(line.strip())
        if not m:
            continue
        titel = m.group("titel").strip()
        if not titel:
            continue
        prio, faellig = _parse_meta(m.group("meta") or "")
        tid = f"task-{date.today().isoformat()}-{_slugify(titel, maxlen=32)}-{i}"
        tasks.append(
            Task(
                id=tid,
                titel=titel,
                status=TaskStatus.NEU,
                prioritaet=prio,
                faellig=faellig,
                meeting_ref=meeting_ref,
                body=f"Aus Meeting `{meeting_ref}` extrahiert am {now_iso()}.",
            )
        )
    return tasks


def write_task(config: Config, task: Task) -> Path:
    config.paths.tasks_dir.mkdir(parents=True, exist_ok=True)
    path = config.paths.tasks_dir / f"{task.id}.md"
    meta = to_yaml_safe(task.model_dump(exclude={"body", "path"}))
    post = frontmatter.Post(content=task.body, **meta)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))
    task.path = path
    return path


async def process_briefing(
    briefing_path: Path,
    *,
    config: Config | None = None,
) -> TaskExtractResult:
    config = config or load_config()
    post = frontmatter.load(briefing_path)
    system_prompt = build_pipeline_system_prompt(config, SYSTEM_PROMPT_FILE)
    user_message = (
        f"Briefing: {briefing_path.name}\n\n"
        "Extrahiere alle Action-Items als Markdown-Checkliste im Format:\n"
        "`- [ ] Titel (Priorität: hoch/mittel/niedrig; fällig: YYYY-MM-DD)`\n\n"
        f"---\n{post.content}\n---"
    )
    result: AgentResult = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=config.models.pipeline,
    )

    # Fehler/DryRun: Status NICHT fortschreiben — sonst gehen die
    # Action-Items still verloren und das Briefing wird nie erneut geprüft.
    if result.error:
        raise RuntimeError(
            f"Task-Extraktion fehlgeschlagen für `{briefing_path.name}`: {result.error}"
        )
    if result.dry_run:
        return TaskExtractResult(tasks=[], raw_output=result.text, dry_run=True)

    meeting_ref = post.metadata.get("id") or briefing_path.stem
    tasks = parse_tasks(result.text, meeting_ref=str(meeting_ref))
    for t in tasks:
        write_task(config, t)

    # Briefing-Status updaten. 0 geparste Tasks können legitim sein
    # (Meeting ohne Action-Items) — aber auch ein Format-Miss des Modells.
    # Deshalb: zur Sicherheit auf Review stellen statt still abschließen.
    post.metadata["status"] = "Tasks extrahiert" if tasks else "Wartet auf Review"
    post.metadata["pipeline_stage"] = "task_extractor"
    if not tasks:
        post.metadata["review_grund"] = (
            "Keine Action-Items erkannt — bitte prüfen, ob das Meeting "
            "wirklich keine hatte."
        )
    with briefing_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))

    return TaskExtractResult(tasks=tasks, raw_output=result.text, dry_run=result.dry_run)


def run_once(briefing_path: Path, *, config: Config | None = None) -> TaskExtractResult:
    return asyncio.run(process_briefing(briefing_path, config=config))
