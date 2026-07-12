"""Tagesbriefing: proaktive Übersicht für den Arbeitsstart.

Aggregiert offline (kein API-Call nötig):
- Offene Aufgaben (überfällig zuerst, dann nach Priorität)
- Aufgaben, bei denen der Nutzer am Zug ist (Review / Fehler)
- Aktuelle Prioritäten aus dem Kontextprofil
- Frisches Feedback der letzten Tage

Optional (`mit_llm=True`): der OS-Agent verdichtet das Briefing zu einer
persönlichen Management-Summary mit Empfehlungen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from ..config import Config
from .feedback import list_feedback
from .models import Task
from .tasks import ACTION_REQUIRED_STATUSES, load_tasks, overdue


@dataclass
class DailyBriefing:
    datum: date
    offene_tasks: list[Task]
    ueberfaellig: list[Task]
    am_zug: list[Task]
    prioritaeten: str
    frisches_feedback: list[str]

    def to_markdown(self) -> str:
        lines = [f"# ☀️ Tagesbriefing — {self.datum.isoformat()}", ""]

        if self.ueberfaellig:
            lines.append("## 🔥 Überfällig")
            for t in self.ueberfaellig:
                lines.append(f"- {t.prioritaet.value} **{t.titel}** (fällig {t.faellig})")
            lines.append("")

        if self.am_zug:
            lines.append("## 👉 Du bist am Zug")
            for t in self.am_zug:
                grund = "Review ausstehend" if t.status.value == "Wartet auf Review" else "Fehler prüfen"
                lines.append(f"- {t.prioritaet.value} **{t.titel}** — {grund}")
            lines.append("")

        lines.append(f"## 📋 Offene Aufgaben ({len(self.offene_tasks)})")
        if self.offene_tasks:
            for t in self.offene_tasks[:15]:
                faellig = f" · fällig {t.faellig}" if t.faellig else ""
                skill = f" · Skill: {t.zugewiesener_skill}" if t.zugewiesener_skill else ""
                lines.append(f"- {t.prioritaet.value} {t.titel} ({t.status.value}{faellig}{skill})")
            if len(self.offene_tasks) > 15:
                lines.append(f"- … und {len(self.offene_tasks) - 15} weitere")
        else:
            lines.append("_Keine offenen Aufgaben in der Task-DB._")
        lines.append("")

        if self.prioritaeten:
            lines.append("## 🎯 Aktuelle Prioritäten")
            lines.append(self.prioritaeten)
            lines.append("")

        if self.frisches_feedback:
            lines.append("## 📝 Frische Learnings (letzte 7 Tage)")
            for fb in self.frisches_feedback[:5]:
                lines.append(f"- {fb}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"


def _extract_prioritaeten(config: Config) -> str:
    """Top-Priorität + Fokusthemen aus dem Kontextprofil ziehen."""
    path = config.paths.context_personal / "prioritaeten-und-ziele.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")

    parts: list[str] = []
    m = re.search(r"## #1 Priorität.*?\n\n\*\*(.+?)\*\*", text, re.DOTALL)
    if m:
        parts.append(f"**#1:** {m.group(1).strip()}")
    m = re.search(
        r"## Aktuelle Fokusthemen.*?\n\n(.*?)(?=\n## )", text, re.DOTALL
    )
    if m:
        for line in m.group(1).strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.", line):
                # »1. **Thema** — Beschreibung« → »Thema«
                thema = re.sub(r"^\d+\.\s*\*\*(.+?)\*\*.*$", r"\1", line)
                parts.append(f"- {thema}")
    return "\n".join(parts)


def build_daily_briefing(config: Config, *, heute: date | None = None) -> DailyBriefing:
    """Briefing offline zusammenstellen (kein API-Call)."""
    heute = heute or date.today()
    offene = load_tasks(config, nur_offene=True)
    ueberfaellig = overdue(offene, heute=heute)
    am_zug = [t for t in offene if t.status in ACTION_REQUIRED_STATUSES]

    cutoff = heute - timedelta(days=7)
    frisch = [
        f"[{e.erstellt_am}] {e.titel}" + (f" — {e.learning}" if e.learning else "")
        for e in list_feedback(config)
        if e.erstellt_am >= cutoff
    ]

    return DailyBriefing(
        datum=heute,
        offene_tasks=offene,
        ueberfaellig=ueberfaellig,
        am_zug=am_zug,
        prioritaeten=_extract_prioritaeten(config),
        frisches_feedback=frisch,
    )


async def summarize_briefing(config: Config, briefing: DailyBriefing) -> str:
    """Optional: LLM-Summary mit konkreten Empfehlungen (braucht API-Key)."""
    from ..agents.sdk_bridge import query_os_agent

    system_prompt = (
        "Du bist der Founders Associate von NextStepHR. Aus dem folgenden "
        "Tagesbriefing destillierst du eine persönliche Management-Summary: "
        "max. 5 Sätze, dann die 3 wichtigsten konkreten nächsten Schritte "
        "als nummerierte Liste. Direkt, ohne Floskeln, auf Deutsch."
    )
    result = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=briefing.to_markdown(),
        model=config.models.fast,
    )
    return result.text
