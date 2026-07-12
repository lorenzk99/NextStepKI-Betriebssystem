"""Gemeinsame Helper: Prompts dynamisch aus Datei + Kontext + Skill zusammenbauen."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..core.context_loader import ContextBundle
from ..core.governance import GovernanceDecision
from ..core.models import Skill


def read_prompt_file(config: Config, relative: str) -> str:
    """Lade einen Systemprompt aus `system_prompts/`."""
    path = config.paths.prompts / relative
    if not path.exists():
        raise FileNotFoundError(f"System-Prompt nicht gefunden: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_os_agent_system_prompt(
    config: Config,
    *,
    boot_context: ContextBundle,
    active_skill: Skill | None = None,
    task_context: ContextBundle | None = None,
    governance: GovernanceDecision | None = None,
) -> str:
    """Baue den Systemprompt für den OS-Agent dynamisch zusammen."""
    sections: list[str] = []

    # 1. OS-Anweisung
    sections.append("# OS-Anweisung (Betriebssystem-Modus)\n")
    sections.append(read_prompt_file(config, "os_agent.md"))

    # 2. Boot-Kontext (immer)
    sections.append("\n---\n# Boot-Kontext (Stufe 1)\n")
    if boot_context.stufe_1:
        sections.append(boot_context.render())
    else:
        sections.append("_Kein persönlicher Kontext gefunden. Bitte in `data/context/personal/` befüllen._")

    # 3. Aktiver Skill (falls vorhanden)
    if active_skill is not None:
        sections.append("\n---\n# Aktiver Skill\n")
        sections.append(f"**{active_skill.name}** (`{active_skill.id}`)\n")
        sections.append(f"Ampel: {active_skill.ampel.value}  ·  Modus: {active_skill.execution_mode.value}\n")
        sections.append(f"Owner: {active_skill.owner}\n")
        if active_skill.beschreibung:
            sections.append(f"\n{active_skill.beschreibung}\n")
        sections.append("\n## SOP (Skill-Body)\n")
        sections.append(active_skill.body)

    # 4. Task-spezifischer Kontext (Stufe 2) — Pfade, die schon im
    #    Boot-Kontext gerendert wurden, nicht doppelt einfügen.
    boot_paths = {
        item.entry.path
        for item in boot_context.stufe_1 + boot_context.stufe_2
    }
    if task_context is not None:
        stufe_2_neu = [i for i in task_context.stufe_2 if i.entry.path not in boot_paths]
        stufe_3_neu = [i for i in task_context.stufe_3 if i.entry.path not in boot_paths]
        if stufe_2_neu or stufe_3_neu:
            sections.append("\n---\n# Aufgaben-Kontext (Stufe 2/3)\n")
            rendered = []
            if stufe_2_neu:
                rendered.append("## Stufe 2 – Aufgabe\n")
                for item in stufe_2_neu:
                    rendered.append(f"### {item.entry.name}\n{item.content.strip()}\n")
            if stufe_3_neu:
                rendered.append("## Stufe 3 – Hintergrund\n")
                for item in stufe_3_neu:
                    rendered.append(f"### {item.entry.name}\n{item.content.strip()}\n")
            sections.append("\n".join(rendered))

    # 5. Governance-Entscheidung
    if governance is not None:
        sections.append("\n---\n# Governance-Entscheidung (bindend)\n")
        sections.append("```\n" + governance.summary() + "\n```")
        if governance.hil_markers:
            sections.append(
                f"\n**{len(governance.hil_markers)} HIL-Gates** im SOP. "
                "Dort zwingend pausieren, Nutzer einbeziehen, dann fortsetzen."
            )

    return "\n".join(sections).strip() + "\n"


def build_pipeline_system_prompt(
    config: Config,
    prompt_relative: str,
    *,
    extra_context: str = "",
) -> str:
    """Baue den Systemprompt für einen Pipeline- oder Standalone-Agent."""
    base = read_prompt_file(config, prompt_relative)
    if extra_context.strip():
        return f"{base}\n\n---\n# Laufzeit-Kontext\n\n{extra_context.strip()}\n"
    return base + "\n"
