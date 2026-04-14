"""CLI-Einstieg für `nextstep-os`."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .agents import os_agent, runner
from .agents.pipeline import (
    feedback_logger,
    meeting_insight,
    skill_executor,
    skill_scout,
    task_extractor,
)
from .agents.standalone import inbox_reply_drafter, lead_dossier
from .config import load_config
from .core import feedback as feedback_core
from .core.context_loader import load_boot_context, load_context_for_skill
from .core.feedback import list_feedback, silent_patch_skill
from .core.governance import evaluate
from .core.models import FeedbackTyp
from .core.skill_loader import load_registry, load_skill_by_id, match_skills


load_dotenv()
app = typer.Typer(help="NextStepKI KI-Betriebssystem — CLI")
console = Console()

skills_app = typer.Typer(help="Skill-Verwaltung (list, show, match)")
context_app = typer.Typer(help="Kontext-Verwaltung (boot, show)")
pipeline_app = typer.Typer(help="Pipeline-Agents (einzeln oder run/watch)")
standalone_app = typer.Typer(help="Standalone-Agents (inbox-reply, lead-dossier)")
feedback_app = typer.Typer(help="Feedback-Loop (list, record, review)")
app.add_typer(skills_app, name="skills")
app.add_typer(context_app, name="context")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(standalone_app, name="standalone")
app.add_typer(feedback_app, name="feedback")


# --------------------------------------------------------------------------- #
# Top-Level
# --------------------------------------------------------------------------- #


@app.command()
def chat(message: str = typer.Argument(..., help="Deine Anfrage an den OS-Agent.")) -> None:
    """Stelle eine Anfrage an den OS-Agent (einmaliger Durchlauf)."""
    out = os_agent.run_once(message)
    if out["match"]:
        console.print(
            Panel.fit(
                f"[bold]Skill:[/bold] {out['match']['name']} (score={out['match']['score']}, "
                f"quality={out['match']['quality']})",
                title="Skill-Selection",
            )
        )
    else:
        console.print(Panel.fit("Kein Skill-Match gefunden – Freitext-Antwort.", title="Skill-Selection"))
    if out["governance"]:
        console.print(Panel(out["governance"], title="Governance"))
    if out["dry_run"]:
        console.print(
            Panel(out["output"], title="Agent-Output (DryRun)", style="yellow")
        )
    else:
        console.print(Panel(Markdown(out["output"]), title="Agent-Output"))


@app.command()
def version() -> None:
    """Version ausgeben."""
    from . import __version__

    console.print(f"nextstep-os {__version__}")


@app.command()
def doctor() -> None:
    """Setup-Diagnose: Pfade, API-Key, Skill-Register, Abhängigkeiten."""
    cfg = load_config()
    table = Table(title="NextStepKI — Setup-Diagnose")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    def add(name: str, ok: bool, details: str) -> None:
        table.add_row(name, "✅" if ok else "⚠️", details)

    add(
        "ANTHROPIC_API_KEY",
        bool(cfg.anthropic_api_key),
        "gesetzt" if cfg.anthropic_api_key else "fehlt (DryRun-Modus aktiv)",
    )
    add(
        "Skill-Register",
        cfg.paths.skills_index.exists(),
        str(cfg.paths.skills_index),
    )
    add(
        "Kontext-Register",
        cfg.paths.context_index.exists(),
        str(cfg.paths.context_index),
    )
    add(
        "Governance-Handbuch",
        cfg.paths.governance_handbook.exists(),
        str(cfg.paths.governance_handbook),
    )
    try:
        entries = load_registry(cfg)
        add("Skills geladen", True, f"{len(entries)} Skills im Register")
    except Exception as exc:  # noqa: BLE001
        add("Skills geladen", False, str(exc))
    try:
        import claude_agent_sdk  # noqa: F401

        add("Claude Agent SDK", True, "installiert")
    except Exception as exc:  # noqa: BLE001
        add("Claude Agent SDK", False, f"nicht verfügbar: {exc}")
    console.print(table)


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #


@skills_app.command("list")
def skills_list() -> None:
    cfg = load_config()
    entries = load_registry(cfg)
    table = Table(title="Skills")
    for col in ("ID", "Name", "Ampel", "Modus", "Status", "Nutzung"):
        table.add_column(col)
    for e in entries:
        table.add_row(
            e.id,
            e.name,
            e.ampel,
            e.execution_mode.value,
            e.status.value,
            e.nutzungsart.value,
        )
    console.print(table)


@skills_app.command("show")
def skills_show(skill_id: str) -> None:
    cfg = load_config()
    skill = load_skill_by_id(cfg, skill_id)
    dec = evaluate(skill)
    console.print(
        Panel.fit(
            f"[bold]{skill.name}[/bold] ({skill.id})\n"
            f"Ampel: {skill.ampel.value}  ·  Modus: {skill.execution_mode.value}  "
            f"·  Status: {skill.status.value}\nOwner: {skill.owner}\n\n"
            f"{skill.beschreibung}",
            title="Skill",
        )
    )
    console.print(Panel(dec.summary(), title="Governance"))
    console.print(Panel(Markdown(skill.body), title="SOP"))


@skills_app.command("match")
def skills_match(query: str, limit: int = 5) -> None:
    cfg = load_config()
    matches = match_skills(cfg, query, limit=limit)
    table = Table(title=f"Matches für: {query}")
    for col in ("Skill", "Score", "Quality", "Begründung"):
        table.add_column(col)
    for m in matches:
        table.add_row(m.skill_id, f"{m.score:.2f}", m.quality.value, m.begruendung)
    console.print(table)


# --------------------------------------------------------------------------- #
# Kontext
# --------------------------------------------------------------------------- #


@context_app.command("boot")
def context_boot() -> None:
    cfg = load_config()
    bundle = load_boot_context(cfg)
    console.print(
        Panel.fit(
            f"Stufe 1: {len(bundle.stufe_1)} Einträge · "
            f"~{bundle.total_tokens()} Tokens",
            title="Boot-Kontext",
        )
    )
    for item in bundle.stufe_1:
        console.print(f"  • {item.entry.id} ({item.tokens} tokens) — {item.entry.path}")
    if bundle.skipped:
        console.print("[yellow]Übersprungen:[/yellow]")
        for sid, reason in bundle.skipped:
            console.print(f"  - {sid}: {reason}")


@context_app.command("show")
def context_show(skill_id: str, mit_hintergrund: bool = False) -> None:
    cfg = load_config()
    skill = load_skill_by_id(cfg, skill_id)
    bundle = load_context_for_skill(cfg, skill, mit_hintergrund=mit_hintergrund)
    console.print(
        Panel.fit(
            f"Stufe 1: {len(bundle.stufe_1)}  ·  Stufe 2: {len(bundle.stufe_2)}  "
            f"·  Stufe 3: {len(bundle.stufe_3)}  ·  ~{bundle.total_tokens()} Tokens",
            title=f"Kontext für {skill.id}",
        )
    )
    console.print(Markdown(bundle.render()))


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


@pipeline_app.command("run")
def pipeline_run() -> None:
    """Führe alle Pipeline-Stages einmal aus."""
    report = runner.run_once_sync()
    console.print(Panel(report.summary(), title="Pipeline-Run"))


@pipeline_app.command("watch")
def pipeline_watch(interval: float = 5.0) -> None:
    """Starte den File-Watcher."""
    runner.watch(interval=interval)


@pipeline_app.command("meeting")
def pipeline_meeting(path: Path) -> None:
    res = meeting_insight.run_once(path)
    console.print(Panel(f"Briefing geschrieben: {res.briefing_path}", title="Meeting-Insight"))
    console.print(Markdown(res.summary))


@pipeline_app.command("extract")
def pipeline_extract(briefing: Path) -> None:
    res = task_extractor.run_once(briefing)
    console.print(Panel(f"Tasks extrahiert: {len(res.tasks)}", title="Task-Extractor"))
    for t in res.tasks:
        console.print(f"  • {t.id}: {t.titel} ({t.prioritaet.name})")


@pipeline_app.command("scout")
def pipeline_scout(task: Path) -> None:
    dec = skill_scout.run_once(task)
    match = dec.match.model_dump() if dec.match else None
    console.print(Panel(f"Route: {dec.route}\nMatch: {match}", title="Skill-Scout"))


@pipeline_app.command("execute")
def pipeline_execute(task: Path) -> None:
    res = skill_executor.run_once(task)
    console.print(
        Panel(
            f"Skill: {res.skill_id}  ·  Status: {res.status.value}\n\n{res.output}",
            title="Skill-Executor",
        )
    )


@pipeline_app.command("log")
def pipeline_log(task: Path, learning: str = "") -> None:
    res = feedback_logger.run_once(task, learning=learning)
    console.print(
        Panel(
            f"Feedback: {res.feedback.path}\nSilent Patch: {res.patched_skill}",
            title="Feedback-Logger",
        )
    )


# --------------------------------------------------------------------------- #
# Standalone
# --------------------------------------------------------------------------- #


@standalone_app.command("inbox-reply")
def standalone_inbox_reply(path: Path) -> None:
    res = inbox_reply_drafter.run_on_file(path)
    console.print(Panel(res.reply_text, title="Reply-Draft"))


@standalone_app.command("lead-dossier")
def standalone_lead_dossier(path: Path, projekt: str = "") -> None:
    res = lead_dossier.run_on_file(path, projektname=projekt or None)
    console.print(Panel(f"Dossier: {res.dossier_path}\n\n{res.content}", title="Lead-Dossier"))


# --------------------------------------------------------------------------- #
# Feedback
# --------------------------------------------------------------------------- #


@feedback_app.command("list")
def feedback_list() -> None:
    cfg = load_config()
    entries = list_feedback(cfg)
    table = Table(title="Feedback-Einträge")
    for col in ("Datum", "Titel", "Typ", "Status", "Skill"):
        table.add_column(col)
    for e in entries:
        table.add_row(
            e.erstellt_am.isoformat(),
            e.titel,
            e.typ.value,
            e.status.value,
            e.skill_id or "-",
        )
    console.print(table)


@feedback_app.command("record")
def feedback_record(
    titel: str,
    typ: str = "verbesserungs-idee",
    learning: str = "",
    skill_id: str = "",
    patch: bool = False,
) -> None:
    cfg = load_config()
    try:
        ftyp = FeedbackTyp(typ)
    except ValueError:
        console.print(f"[red]Unbekannter Typ `{typ}`. Erlaubt: {[t.value for t in FeedbackTyp]}[/red]")
        raise typer.Exit(1)
    skill_path = None
    if skill_id:
        try:
            sk = load_skill_by_id(cfg, skill_id)
            skill_path = sk.path
        except KeyError:
            console.print(f"[yellow]Skill `{skill_id}` nicht im Register.[/yellow]")
    entry = feedback_core.record(
        cfg,
        titel=titel,
        typ=ftyp,
        learning=learning,
        skill_id=skill_id or None,
        skill_path=skill_path,
        patch_skill=patch,
    )
    console.print(Panel(f"Feedback gespeichert: {entry.path}", title="Feedback"))


@feedback_app.command("review")
def feedback_review() -> None:
    """Gruppiere Feedback-Einträge nach Typ/Skill (Monthly-Review-Helper)."""
    cfg = load_config()
    entries = list_feedback(cfg)
    if not entries:
        console.print("[yellow]Keine Feedback-Einträge gefunden.[/yellow]")
        return
    by_typ: dict[str, list] = {}
    for e in entries:
        by_typ.setdefault(e.typ.value, []).append(e)
    for typ, items in by_typ.items():
        console.print(Panel.fit(f"{typ} ({len(items)})", style="cyan"))
        for e in items:
            console.print(
                f"  • [{e.erstellt_am}] {e.titel} — Skill: {e.skill_id or '-'}  "
                f"Status: {e.status.value}"
            )


@feedback_app.command("patch")
def feedback_patch(skill_id: str, learning: str) -> None:
    """Silent-Patch: Learning-Zeile in Skill-MD schreiben."""
    cfg = load_config()
    skill = load_skill_by_id(cfg, skill_id)
    if skill.path is None:
        console.print("[red]Skill-Pfad unbekannt.[/red]")
        raise typer.Exit(1)
    silent_patch_skill(skill.path, learning)
    console.print(f"✅ Silent-Patch auf {skill.path}")


if __name__ == "__main__":
    app()
