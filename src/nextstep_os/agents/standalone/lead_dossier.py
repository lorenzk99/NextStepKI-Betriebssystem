"""Lead-Dossier-Agent.

Extrahiert Lead-Infos aus einer Eingangsnachricht und erzeugt ein
strukturiertes Dossier gemäß `system_prompts/standalone/lead_dossier.md`.
Persistiert als YAML+MD unter `data/context/sources/leads/`.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import frontmatter

from ...config import Config, load_config
from ..prompt_builder import build_pipeline_system_prompt
from ..sdk_bridge import AgentResult, query_os_agent


SYSTEM_PROMPT_FILE = "standalone/lead_dossier.md"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug or "lead")[:60]


@dataclass
class LeadDossierResult:
    dossier_path: Path
    content: str
    dry_run: bool


async def build_dossier(
    mail_text: str,
    *,
    config: Config | None = None,
    projektname: str | None = None,
) -> LeadDossierResult:
    config = config or load_config()
    system_prompt = build_pipeline_system_prompt(config, SYSTEM_PROMPT_FILE)
    user_message = (
        "Verarbeite folgende Eingangsnachricht und erstelle den Dossier-Entwurf "
        "nach Vorgabe des Systemprompts. Gib den Dossier-Text direkt als "
        "Markdown zurück.\n\n"
        f"---\n{mail_text.strip()}\n---"
    )
    result: AgentResult = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=config.models.pipeline,
    )

    leads_dir = config.paths.context_sources / "leads"
    leads_dir.mkdir(parents=True, exist_ok=True)
    name = projektname or f"lead-{date.today().isoformat()}"
    dossier_path = leads_dir / f"{_slug(name)}.md"

    meta = {
        "id": dossier_path.stem,
        "typ": "lead",
        "erstellt_am": date.today().isoformat(),
        "projektname": projektname or "",
        "status": "Neu",
        "quelle": "inbox",
    }
    post = frontmatter.Post(content=result.text.strip(), **meta)
    with dossier_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))

    return LeadDossierResult(
        dossier_path=dossier_path, content=result.text, dry_run=result.dry_run
    )


def run_once(
    mail_text: str, *, config: Config | None = None, projektname: str | None = None
) -> LeadDossierResult:
    return asyncio.run(build_dossier(mail_text, config=config, projektname=projektname))


def run_on_file(
    path: Path, *, config: Config | None = None, projektname: str | None = None
) -> LeadDossierResult:
    return run_once(
        path.read_text(encoding="utf-8"), config=config, projektname=projektname
    )
