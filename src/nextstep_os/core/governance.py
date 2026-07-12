"""Governance-Engine: Ampel-Parsing, HIL-Detection, Execution-Mode.

Die Engine arbeitet auf einem geladenen `Skill` (siehe `models.py`) und
liefert strukturierte Governance-Entscheidungen, die der OS-Agent und
der Skill-Executor durchsetzen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Ampel, ExecutionMode, Skill, SkillStatus


# --------------------------------------------------------------------------- #
# Konstanten
# --------------------------------------------------------------------------- #


HIL_MARKER = "⏸️"
AMPEL_EMOJI = {Ampel.GRUEN: "🟢", Ampel.GELB: "🟡", Ampel.ROT: "🔴"}

# Explizite Gate-Labels haben Vorrang (»⏸️ **REVIEW GATE:** … Freigabe …«
# ist ein Review-Gate, kein Approval-Gate, auch wenn »Freigabe« im Text steht).
HIL_GATE_LABELS = {
    "approval": re.compile(r"approval[\s-]*gate", re.IGNORECASE),
    "input": re.compile(r"input[\s-]*gate", re.IGNORECASE),
    "review": re.compile(r"review[\s-]*gate", re.IGNORECASE),
}

# Keyword-Fallback mit Wortgrenzen (»Erklärung« darf nicht als »Klärung« zählen)
HIL_KEYWORDS = {
    "approval": re.compile(r"\b(freigabe|genehmigung|bestätigung)\b", re.IGNORECASE),
    "input": re.compile(r"\b(rückfrage|klärung|nachfrage)\b", re.IGNORECASE),
    "review": re.compile(r"\b(prüfung|review|qualitätssicherung)\b", re.IGNORECASE),
}

_INLINE_CODE_RE = re.compile(r"`[^`]*`")


# --------------------------------------------------------------------------- #
# Ergebnis-Typen
# --------------------------------------------------------------------------- #


@dataclass
class HILMarker:
    """Ein im SOP-Body entdeckter Human-in-the-Loop-Gate."""

    position: int
    line: str
    typ: str = "generic"  # approval | input | review | generic


@dataclass
class GovernanceDecision:
    """Strukturiertes Ergebnis des Governance-Checks."""

    skill_id: str
    ampel: Ampel
    execution_mode: ExecutionMode
    status: SkillStatus
    darf_ausfuehren: bool
    requires_review: bool
    requires_approval_before_execution: bool
    web_search_allowed: bool
    hil_markers: list[HILMarker] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Kompakte Textzusammenfassung für Logs / Chat-Output."""
        lines = [
            f"Skill:       {self.skill_id}",
            f"Ampel:       {AMPEL_EMOJI[self.ampel]}  ({self.ampel.name})",
            f"Modus:       {self.execution_mode.value}",
            f"Status:      {self.status.value}",
            f"Ausführbar:  {'ja' if self.darf_ausfuehren else 'nein'}",
            f"Review:      {'erforderlich' if self.requires_review else 'nicht nötig'}",
            (
                "Approval:    erforderlich vor Start"
                if self.requires_approval_before_execution
                else "Approval:    nicht vorab nötig"
            ),
            f"Web-Search:  {'erlaubt' if self.web_search_allowed else 'gesperrt'}",
            f"HIL-Gates:   {len(self.hil_markers)}",
        ]
        if self.warnungen:
            lines.append("Warnungen:")
            for w in self.warnungen:
                lines.append(f"  - {w}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def detect_hil_markers(body: str) -> list[HILMarker]:
    """Finde alle HIL-Gates (⏸️) im Skill-Body und klassifiziere sie.

    Doku-Zeilen, in denen das ⏸️ nur innerhalb von Inline-Code (`…`) steht
    (z.B. Format-Beschreibungen im Meta-Skill), zählen nicht als Gate.
    """
    markers: list[HILMarker] = []
    for i, line in enumerate(body.splitlines()):
        # ⏸️ in Backticks ist Dokumentation, kein Gate
        effective = _INLINE_CODE_RE.sub("", line)
        if HIL_MARKER not in effective:
            continue
        typ = "generic"
        for label, regex in HIL_GATE_LABELS.items():
            if regex.search(effective):
                typ = label
                break
        else:
            for label, regex in HIL_KEYWORDS.items():
                if regex.search(effective):
                    typ = label
                    break
        markers.append(HILMarker(position=i, line=line.strip(), typ=typ))
    return markers


def check_activation_gate(skill: Skill) -> list[str]:
    """Prüft das Activation Gate.

    Rückgabe: Liste von Warnungen (leer = alles ok).
    Regel: Nur Status `Aktiv` darf produktiv genutzt werden. Skills im Status
    `Entwurf` sind für Tests freigegeben, sollten aber nicht im
    Autonom-Modus laufen. `Archiviert` ist gesperrt.
    """
    warnings: list[str] = []
    if skill.status == SkillStatus.ARCHIVIERT:
        warnings.append("Skill ist archiviert – Ausführung gesperrt.")
    elif skill.status == SkillStatus.ENTWURF:
        warnings.append(
            "Skill ist im Status »Entwurf«. Activation Gate (3+ Testläufe) "
            "noch nicht passiert – nur im Test-Modus ausführen, Output "
            "immer reviewen."
        )
    return warnings


def evaluate(skill: Skill) -> GovernanceDecision:
    """Führe einen vollständigen Governance-Check auf einem Skill durch."""
    markers = detect_hil_markers(skill.body)
    warnings = check_activation_gate(skill)

    # Ampel-Logik (siehe Governance-Handbuch)
    requires_review = skill.ampel in {Ampel.GELB, Ampel.ROT}
    requires_approval = skill.ampel == Ampel.ROT or any(
        m.typ == "approval" for m in markers
    )
    darf_ausfuehren = skill.status != SkillStatus.ARCHIVIERT

    # Search-Mode kann Web-Recherche (später via MCP) erlauben.
    web_search_allowed = skill.execution_mode == ExecutionMode.SEARCH

    return GovernanceDecision(
        skill_id=skill.id,
        ampel=skill.ampel,
        execution_mode=skill.execution_mode,
        status=skill.status,
        darf_ausfuehren=darf_ausfuehren,
        requires_review=requires_review,
        requires_approval_before_execution=requires_approval,
        web_search_allowed=web_search_allowed,
        hil_markers=markers,
        warnungen=warnings,
    )


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


def render_ampel_header(skill: Skill) -> str:
    """Einzeiler: Emoji + Label für Logs und UI."""
    return f"{AMPEL_EMOJI[skill.ampel]} {skill.ampel.name} · Modus: {skill.execution_mode.value}"
