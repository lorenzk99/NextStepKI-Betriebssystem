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
from .core.briefing import build_daily_briefing, summarize_briefing
from .core.tasks import by_status, load_tasks
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
from .core.models import FeedbackTyp, SkillStatus
from .core.registry import update_skill_registry_entry
from .core.review import build_monthly_report, suggest_skill_patch, write_report
from .core.skill_loader import load_registry, load_skill_by_id, match_skills
from .core.telemetry import aggregate, can_promote, read_runs


load_dotenv()
app = typer.Typer(help="NextStepKI KI-Betriebssystem — CLI")
console = Console()

skills_app = typer.Typer(help="Skill-Verwaltung (list, show, match)")
context_app = typer.Typer(help="Kontext-Verwaltung (boot, show)")
pipeline_app = typer.Typer(help="Pipeline-Agents (einzeln oder run/watch)")
standalone_app = typer.Typer(help="Standalone-Agents (inbox-reply, lead-dossier)")
feedback_app = typer.Typer(help="Feedback-Loop (list, record, review)")
review_app = typer.Typer(help="Monthly Review & LLM-Patch-Vorschläge")
tasks_app = typer.Typer(help="Aufgaben-Übersicht (list, show)")
app.add_typer(skills_app, name="skills")
app.add_typer(context_app, name="context")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(standalone_app, name="standalone")
app.add_typer(feedback_app, name="feedback")
app.add_typer(review_app, name="review")
app.add_typer(tasks_app, name="tasks")


# --------------------------------------------------------------------------- #
# Top-Level
# --------------------------------------------------------------------------- #


@app.command()
def chat(
    message: str = typer.Argument(None, help="Deine Anfrage. Weglassen → REPL-Modus."),
    stream: bool = typer.Option(True, help="Tokens live streamen."),
) -> None:
    """OS-Agent: Einzelnachricht (mit Argument) oder REPL (ohne)."""
    if message is None:
        asyncio.run(_chat_repl(stream=stream))
        return
    asyncio.run(_chat_one(message, stream=stream))


async def _chat_one(message: str, *, stream: bool) -> None:
    state = await os_agent.boot()
    top = await os_agent.select_skill(state, message)

    if top:
        console.print(
            Panel.fit(
                f"[bold]Skill:[/bold] {top.name}  ·  score={top.score}  ·  quality={top.quality.value}",
                title="Skill-Selection",
            )
        )
    else:
        console.print(
            Panel.fit(
                "Kein eindeutiger Skill-Match – Freitext-Antwort.",
                title="Skill-Selection",
            )
        )
    if state.governance:
        console.print(Panel(state.governance.summary(), title="Governance"))

    if stream:
        console.print(Panel.fit("[dim]Agent antwortet…[/dim]", title="Agent-Output"))
        buffer: list[str] = []

        def on_delta(delta: str) -> None:
            buffer.append(delta)
            console.print(delta, end="", soft_wrap=True, highlight=False)

        result = await os_agent.handle(state, message, auto_select=False, stream_cb=on_delta)
        console.print()  # Newline am Ende
        if result.dry_run:
            console.print(Panel(result.text, title="DryRun", style="yellow"))
        if not buffer and not result.dry_run:
            console.print(Panel(Markdown(result.text), title="Agent-Output"))
    else:
        result = await os_agent.handle(state, message, auto_select=False)
        title = "Agent-Output (DryRun)" if result.dry_run else "Agent-Output"
        body = result.text if result.dry_run else Markdown(result.text)
        style = "yellow" if result.dry_run else None
        console.print(Panel(body, title=title, style=style) if style else Panel(body, title=title))


async def _chat_repl(*, stream: bool) -> None:
    state = await os_agent.boot()
    console.print(
        Panel.fit(
            "[bold]NextStepKI OS-Agent — REPL[/bold]\n"
            "Tippe deine Anfrage. `/exit` oder Ctrl-D zum Beenden.\n"
            "`/reset` setzt den aktiven Skill zurück.",
            title="Chat",
        )
    )
    while True:
        try:
            msg = console.input("[bold cyan]›[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Beendet.[/dim]")
            return
        msg = msg.strip()
        if not msg:
            continue
        if msg in {"/exit", "/quit"}:
            return
        if msg == "/reset":
            state.active_skill = None
            state.task_context = None
            state.governance = None
            console.print("[dim]Skill zurückgesetzt.[/dim]")
            continue

        top = await os_agent.select_skill(state, msg)
        if top:
            console.print(
                f"[dim]↳ Skill: {top.name} (score={top.score}, {top.quality.value})[/dim]"
            )
        if stream:
            repl_buffer: list[str] = []

            def on_delta(delta: str) -> None:
                repl_buffer.append(delta)
                console.print(delta, end="", soft_wrap=True, highlight=False)

            result = await os_agent.handle(state, msg, auto_select=False, stream_cb=on_delta)
            console.print()
            if result.dry_run:
                console.print(Panel(result.text, title="DryRun", style="yellow"))
            elif result.error and not repl_buffer:
                console.print(Panel(result.text, title="Fehler", style="red"))
        else:
            result = await os_agent.handle(state, msg, auto_select=False)
            console.print(
                Panel(
                    result.text if result.dry_run else Markdown(result.text),
                    title="Agent",
                    style="yellow" if result.dry_run else None,
                )
            )


@app.command()
def briefing(
    llm: bool = typer.Option(False, "--llm", help="Zusätzlich LLM-Summary mit Empfehlungen."),
) -> None:
    """☀️ Tagesbriefing: offene Aufgaben, Prioritäten, frische Learnings."""
    cfg = load_config()
    daily = build_daily_briefing(cfg)
    console.print(Markdown(daily.to_markdown()))
    if llm:
        summary = asyncio.run(summarize_briefing(cfg, daily))
        console.print(Panel(Markdown(summary), title="🤖 Founders-Associate-Summary"))


@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", help="Bind-Adresse (nur lokal: 127.0.0.1)."),
    port: int = typer.Option(8321, help="Port des Dashboards."),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Browser automatisch öffnen."),
) -> None:
    """Web-Dashboard starten: Skills ansehen, neue Skills anlegen."""
    from .dashboard import serve

    cfg = load_config()
    serve(cfg, host=host, port=port, open_browser=open_browser)


@app.command()
def version() -> None:
    """Version ausgeben."""
    from . import __version__

    console.print(f"nextstep-os {__version__}")


@app.command()
def stats(skill_id: str = typer.Argument(None, help="Optional: nur ein Skill.")) -> None:
    """Zeige aggregierte Skill-Run-Telemetrie."""
    cfg = load_config()
    runs = read_runs(cfg)
    if not runs:
        console.print("[yellow]Keine Telemetrie-Daten vorhanden.[/yellow]")
        return
    stats_map = aggregate(runs)
    if skill_id:
        stats_map = {k: v for k, v in stats_map.items() if k == skill_id}
        if not stats_map:
            console.print(f"[yellow]Keine Runs für `{skill_id}` registriert.[/yellow]")
            return
    table = Table(title="Skill-Run-Statistik")
    for col in (
        "Skill", "Total", "OK", "Errors", "DryRuns", "Ø Dauer (s)",
        "Tokens in", "Tokens out", "Cache read",
    ):
        table.add_column(col)
    for sid, s in sorted(stats_map.items()):
        table.add_row(
            sid,
            str(s.total),
            str(s.ok),
            str(s.errors),
            str(s.dry_runs),
            f"{s.avg_duration_s:.2f}",
            str(s.total_tokens_in),
            str(s.total_tokens_out),
            str(s.total_cache_read),
        )
    console.print(table)


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


@skills_app.command("promote")
def skills_promote(
    skill_id: str,
    min_runs: int = typer.Option(3, help="Minimum Produktiv-Runs."),
    min_success: int = typer.Option(3, help="Minimum erfolgreiche Runs."),
    force: bool = typer.Option(False, help="Gate ignorieren (nicht empfohlen)."),
) -> None:
    """Activation Gate: Skill von Entwurf → Aktiv setzen (prüft Telemetrie)."""
    cfg = load_config()
    skill = load_skill_by_id(cfg, skill_id)
    if skill.status == SkillStatus.AKTIV:
        console.print(f"[yellow]Skill `{skill_id}` ist bereits Aktiv.[/yellow]")
        return
    if skill.status == SkillStatus.ARCHIVIERT:
        console.print(f"[red]Skill `{skill_id}` ist archiviert und kann nicht aktiviert werden.[/red]")
        raise typer.Exit(1)

    darf, begruendung = can_promote(
        cfg, skill_id, min_runs=min_runs, min_success=min_success
    )
    console.print(Panel.fit(begruendung, title="Activation-Gate"))
    if not darf and not force:
        console.print("[red]Aktivierung blockiert. --force zum Überschreiben.[/red]")
        raise typer.Exit(1)

    # Register-Eintrag patchen
    update_skill_registry_entry(
        cfg.paths.skills_index, skill_id, {"status": SkillStatus.AKTIV.value}
    )
    # Frontmatter in Skill-MD patchen
    if skill.path is not None:
        import frontmatter  # lokaler Import

        post = frontmatter.load(skill.path)
        post.metadata["status"] = SkillStatus.AKTIV.value
        with skill.path.open("w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post, sort_keys=False))
    console.print(f"✅ Skill `{skill_id}` ist jetzt Aktiv.")


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
            f"Stufe 2: {len(bundle.stufe_2)} Einträge · "
            f"~{bundle.total_tokens()} Tokens",
            title="Boot-Kontext",
        )
    )
    for item in bundle.stufe_1:
        console.print(f"  • [1] {item.entry.id} ({item.tokens} tokens) — {item.entry.path}")
    for item in bundle.stufe_2:
        console.print(f"  • [2] {item.entry.id} ({item.tokens} tokens) — {item.entry.path}")
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


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


@tasks_app.command("list")
def tasks_list(
    alle: bool = typer.Option(False, "--alle", help="Auch erledigte Tasks anzeigen."),
) -> None:
    """Offene Aufgaben, gruppiert nach Status."""
    cfg = load_config()
    tasks = load_tasks(cfg, nur_offene=not alle)
    if not tasks:
        console.print("[yellow]Keine Aufgaben in der Task-DB.[/yellow]")
        console.print(
            "[dim]Tasks entstehen über die Meeting-Pipeline "
            "(`nextstep-os pipeline run`) oder manuell in data/tasks/.[/dim]"
        )
        return
    for status, items in by_status(tasks).items():
        console.print(Panel.fit(f"[bold]{status}[/bold] ({len(items)})"))
        for t in items:
            faellig = f"  fällig: {t.faellig}" if t.faellig else ""
            skill = f"  skill: {t.zugewiesener_skill}" if t.zugewiesener_skill else ""
            console.print(f"  {t.prioritaet.value} {t.titel}  [dim]({t.id}){faellig}{skill}[/dim]")


@tasks_app.command("show")
def tasks_show(task_id: str) -> None:
    """Details einer Aufgabe anzeigen."""
    cfg = load_config()
    for t in load_tasks(cfg):
        if t.id == task_id or (t.path and t.path.stem == task_id):
            console.print(
                Panel.fit(
                    f"[bold]{t.titel}[/bold]\n"
                    f"Status: {t.status.value}  ·  Priorität: {t.prioritaet.value}\n"
                    f"Fällig: {t.faellig or '—'}  ·  Skill: {t.zugewiesener_skill or '—'}\n"
                    f"Meeting: {t.meeting_ref or '—'}  ·  Erstellt: {t.erstellt_am}",
                    title=t.id,
                )
            )
            if t.body.strip():
                console.print(Panel(Markdown(t.body), title="Inhalt"))
            return
    console.print(f"[red]Task `{task_id}` nicht gefunden.[/red]")
    raise typer.Exit(1)


# --------------------------------------------------------------------------- #
# Review
# --------------------------------------------------------------------------- #


@review_app.command("monthly")
def review_monthly(
    tage: int = typer.Option(30, help="Zeitraum in Tagen."),
    save: bool = typer.Option(True, help="Report als Markdown speichern."),
) -> None:
    """Offline Monthly-Review-Briefing aus Feedback-DB + Telemetrie."""
    cfg = load_config()
    report = build_monthly_report(cfg, tage=tage)
    if save:
        path = write_report(cfg, report)
        console.print(Panel.fit(f"Report gespeichert: {path}", title="Monthly Review"))
    console.print(Markdown(report.to_markdown()))


@review_app.command("suggest")
def review_suggest(
    skill_id: str,
    apply: bool = typer.Option(False, help="Vorschlag direkt als Silent-Patch schreiben."),
) -> None:
    """LLM-gestützter Silent-Patch-Vorschlag aus Feedback-Einträgen."""
    cfg = load_config()
    proposal = asyncio.run(suggest_skill_patch(cfg, skill_id, apply=apply))
    title = "Patch-Vorschlag" + (" (DryRun)" if proposal.dry_run else "")
    style = "yellow" if proposal.dry_run else None
    panel_body = (
        f"Skill: {proposal.skill_id}\n"
        f"Applied: {proposal.applied}\n\n"
        f"{proposal.suggestion}"
    )
    console.print(Panel(panel_body, title=title, style=style) if style else Panel(panel_body, title=title))


if __name__ == "__main__":
    app()
