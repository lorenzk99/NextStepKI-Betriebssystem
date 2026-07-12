"""Monthly-Review: fasst Feedback + Telemetrie zu einem Briefing zusammen.

Zwei Modi:

- **offline** (Default): rein deterministischer Markdown-Report aus
  Feedback-DB + Telemetrie. Kein LLM-Call nötig.
- **suggest**: schickt Skill-SOP + dazugehörige Feedback-Einträge an den
  Agent und lässt ihn Silent-Patch-Vorschläge formulieren. Per Default
  DryRun — mit ``apply=True`` werden die Learnings direkt gepatcht.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..config import Config
from .feedback import list_feedback, silent_patch_skill
from .models import FeedbackEntry, FeedbackTyp
from .skill_loader import load_registry, load_skill_by_id
from .telemetry import SkillStats, aggregate, read_runs


# --------------------------------------------------------------------------- #
# Offline-Report
# --------------------------------------------------------------------------- #


@dataclass
class ReviewReport:
    period_from: date
    period_to: date
    feedback: list[FeedbackEntry] = field(default_factory=list)
    stats: dict[str, SkillStats] = field(default_factory=dict)
    top_learnings: list[tuple[str, str]] = field(default_factory=list)  # (skill_id, learning)
    path: Path | None = None

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# Monthly Review — {self.period_from} bis {self.period_to}")
        lines.append("")
        lines.append(f"- Feedback-Einträge: **{len(self.feedback)}**")
        lines.append(f"- Skills mit Runs: **{len(self.stats)}**")
        lines.append(
            f"- Top-Learnings: **{len(self.top_learnings)}**"
        )
        lines.append("")

        # Feedback nach Typ
        lines.append("## Feedback nach Typ")
        by_typ: dict[str, list[FeedbackEntry]] = {}
        for e in self.feedback:
            by_typ.setdefault(e.typ.value, []).append(e)
        if not by_typ:
            lines.append("_Keine Feedback-Einträge im Zeitraum._")
        for typ, items in sorted(by_typ.items()):
            lines.append(f"### {typ} ({len(items)})")
            for e in items:
                skill = e.skill_id or "—"
                lines.append(f"- [{e.erstellt_am}] **{e.titel}** · Skill: `{skill}` · {e.status.value}")
                if e.learning:
                    lines.append(f"  - Learning: {e.learning}")
            lines.append("")

        # Telemetrie
        lines.append("## Skill-Telemetrie")
        if not self.stats:
            lines.append("_Keine Telemetrie-Daten im Zeitraum._")
        else:
            lines.append("| Skill | Total | OK | Errors | DryRuns | Ø s | Tokens in | Cache read |")
            lines.append("|---|--:|--:|--:|--:|--:|--:|--:|")
            for sid, s in sorted(self.stats.items()):
                lines.append(
                    f"| `{sid}` | {s.total} | {s.ok} | {s.errors} | {s.dry_runs} | "
                    f"{s.avg_duration_s:.2f} | {s.total_tokens_in} | {s.total_cache_read} |"
                )
            lines.append("")

        # Top-Learnings
        lines.append("## Top-Learnings (unverarbeitet)")
        if not self.top_learnings:
            lines.append("_Keine offenen Learnings._")
        for sid, learning in self.top_learnings:
            lines.append(f"- `{sid}`: {learning}")
        lines.append("")
        return "\n".join(lines)


def build_monthly_report(
    config: Config,
    *,
    heute: date | None = None,
    tage: int = 30,
) -> ReviewReport:
    """Baue einen Offline-Report für den letzten Zeitraum."""
    heute = heute or date.today()
    ab = heute - timedelta(days=tage)

    # Feedback filtern
    all_feedback = list_feedback(config)
    in_scope = [e for e in all_feedback if e.erstellt_am >= ab]

    # Telemetrie filtern (ISO-String-Prefix-Vergleich reicht)
    runs = [r for r in read_runs(config) if r.ts[:10] >= ab.isoformat()]
    stats = aggregate(runs)

    # Top-Learnings: `neu`-Einträge mit nicht-leerem Learning, skill-gebunden
    top_learnings = [
        (e.skill_id or "—", e.learning)
        for e in in_scope
        if e.learning and e.status.value == "neu" and e.skill_id
    ][:10]

    return ReviewReport(
        period_from=ab,
        period_to=heute,
        feedback=in_scope,
        stats=stats,
        top_learnings=top_learnings,
    )


def write_report(config: Config, report: ReviewReport) -> Path:
    """Persistiere den Report als Markdown unter `data/feedback/reviews/`."""
    dir_ = config.paths.data / "feedback" / "reviews"
    dir_.mkdir(parents=True, exist_ok=True)
    fname = f"{report.period_to.isoformat()}-monthly-review.md"
    path = dir_ / fname
    path.write_text(report.to_markdown(), encoding="utf-8")
    report.path = path
    return path


# --------------------------------------------------------------------------- #
# LLM-Patch-Vorschlag
# --------------------------------------------------------------------------- #


@dataclass
class PatchProposal:
    skill_id: str
    suggestion: str
    dry_run: bool
    applied: bool = False


async def suggest_skill_patch(
    config: Config,
    skill_id: str,
    *,
    apply: bool = False,
) -> PatchProposal:
    """Lass den Agent einen Silent-Patch-Vorschlag auf Basis der Feedback-DB formulieren."""
    from ..agents.sdk_bridge import query_os_agent  # lokaler Import

    skill = load_skill_by_id(config, skill_id)
    feedbacks = [
        e for e in list_feedback(config)
        if e.skill_id == skill_id and e.learning
        and e.typ in {FeedbackTyp.ERFOLG, FeedbackTyp.FEHLER, FeedbackTyp.VERBESSERUNGS_IDEE}
    ]
    if not feedbacks:
        return PatchProposal(
            skill_id=skill_id,
            suggestion="Keine relevanten Feedback-Einträge mit Learning vorhanden.",
            dry_run=True,
        )

    feedback_block = "\n\n".join(
        f"- [{e.erstellt_am}] ({e.typ.value}) {e.titel}\n  Learning: {e.learning}"
        for e in feedbacks
    )

    system_prompt = (
        "Du bist der Feedback-Kurator des NextStepKI-Betriebssystems. "
        "Aus einer Liste von Feedback-Einträgen zu einem Skill verdichtest du "
        "die wiederkehrenden Muster zu **EINER einzigen Learning-Zeile**. "
        "Format exakt: EINE konkrete Regel, imperativ formuliert — "
        "OHNE Datum (das ergänzt das System beim Patchen selbst).\n"
        "Keine Einleitung, keine Liste, keine Meta-Kommentare — "
        "nur EINE Zeile."
    )
    user_message = (
        f"Skill: **{skill.name}** (`{skill.id}`)\n\n"
        f"Aktuelle SOP-Auszug (ersten 500 Zeichen):\n"
        f"{skill.body[:500]}\n\n"
        f"Feedback-Einträge:\n{feedback_block}"
    )

    result = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=config.models.fast,
        allowed_tools=[],  # rein textlicher Output
    )
    proposal = PatchProposal(
        skill_id=skill_id,
        suggestion=result.text.strip(),
        dry_run=result.dry_run,
    )
    if apply and not result.dry_run and skill.path is not None and proposal.suggestion:
        silent_patch_skill(skill.path, proposal.suggestion)
        proposal.applied = True
    return proposal
