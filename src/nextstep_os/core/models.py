"""Pydantic-Modelle für Skills, Kontext, Tasks, Meetings, Feedback.

Alle persistierten Artefakte werden als YAML/Markdown mit Frontmatter abgelegt.
Diese Modelle sind die In-Memory-Repräsentation.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Governance
# --------------------------------------------------------------------------- #


class Ampel(str, Enum):
    GRUEN = "🟢"
    GELB = "🟡"
    ROT = "🔴"


class ExecutionMode(str, Enum):
    STRICT = "Strict"
    SEARCH = "Search"


class SkillStatus(str, Enum):
    ENTWURF = "Entwurf"
    AKTIV = "Aktiv"
    ARCHIVIERT = "Archiviert"


class Nutzungsart(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


# --------------------------------------------------------------------------- #
# Skill
# --------------------------------------------------------------------------- #


class SkillContext(BaseModel):
    """3-Stufen-Kontext eines Skills (Pfade relativ zu data/)."""

    stufe_1_kern: list[str] = Field(default_factory=list)
    stufe_2_aufgabe: list[str] = Field(default_factory=list)
    stufe_3_hintergrund: list[str] = Field(default_factory=list)


class Skill(BaseModel):
    """Vollständige Skill-Definition (Frontmatter + Markdown-Body)."""

    id: str
    name: str
    status: SkillStatus = SkillStatus.ENTWURF
    owner: str = "[OWNER]"
    ampel: Ampel = Ampel.GELB
    execution_mode: ExecutionMode = ExecutionMode.STRICT
    nutzungsart: Nutzungsart = Nutzungsart.PUBLIC
    keywords: list[str] = Field(default_factory=list)
    beschreibung: str = ""
    eingabe: list[str] = Field(default_factory=list)
    ausgabe: list[str] = Field(default_factory=list)
    context: SkillContext = Field(default_factory=SkillContext)
    update_quellen: list[str] = Field(default_factory=list)

    # Markdown-Body-Sektionen
    body: str = ""  # kompletter Markdown-Body (SOP + DoD + Learnings)

    # Laufzeit-Meta
    path: Path | None = None


class SkillRegistryEntry(BaseModel):
    """Eintrag im Skill-Register (`_index.yaml`)."""

    id: str
    name: str
    path: str
    status: SkillStatus
    owner: str
    ampel: str  # als Emoji-String persistiert
    execution_mode: ExecutionMode
    nutzungsart: Nutzungsart
    keywords: list[str]
    beschreibung: str


# --------------------------------------------------------------------------- #
# Kontext
# --------------------------------------------------------------------------- #


class ContextTyp(str, Enum):
    DOKUMENT = "dokument"
    DATENBANK = "datenbank"
    WEBSEITE = "webseite"
    PERSONEN_KONTEXT = "personen_kontext"
    API = "api"
    PERSONAL = "personal"


class ContextEntry(BaseModel):
    """Ein Eintrag aus `data/context/_index.yaml`."""

    id: str
    name: str
    path: str
    typ: ContextTyp
    kontext_stufe: int  # 1, 2 oder 3
    token_schaetzung: int = 0
    aktualisierung: str = "bei_bedarf"
    status: str = "Aktiv"
    tags: list[str] = Field(default_factory=list)
    beschreibung: str = ""
    skills: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Task / Meeting / Feedback
# --------------------------------------------------------------------------- #


class TaskStatus(str, Enum):
    NEU = "Neu"
    SKILL_ZUGEWIESEN = "Skill zugewiesen"
    IN_ARBEIT = "In Arbeit"
    SKILL_AUSGEFUEHRT = "Skill ausgeführt"
    WARTET_AUF_REVIEW = "Wartet auf Review"
    FEHLER = "Fehler"
    ERLEDIGT = "Erledigt"


class Prioritaet(str, Enum):
    HOCH = "🔴"
    MITTEL = "🟡"
    NIEDRIG = "🟢"


class Task(BaseModel):
    id: str
    titel: str
    status: TaskStatus = TaskStatus.NEU
    prioritaet: Prioritaet = Prioritaet.MITTEL
    faellig: date | None = None
    meeting_ref: str | None = None
    zugewiesener_skill: str | None = None
    erstellt_am: date = Field(default_factory=date.today)
    body: str = ""
    path: Path | None = None


class MeetingTyp(str, Enum):
    KUNDENGESPRAECH = "Kundengespräch"
    VERTRIEBSTERMIN = "Vertriebstermin"
    EIN_ZU_EINS = "1:1"
    TEAM_MEETING = "Team-Meeting"
    STRATEGIE_WORKSHOP = "Strategie/Workshop"
    PODCAST = "Podcast"
    SONSTIGES = "Sonstiges"


class Meeting(BaseModel):
    id: str
    titel: str
    datum: date
    typ: MeetingTyp = MeetingTyp.SONSTIGES
    teilnehmer: list[str] = Field(default_factory=list)
    status: str = "Neu"
    zusammenfassung: str = ""
    body: str = ""
    path: Path | None = None


class FeedbackTyp(str, Enum):
    ERFOLG = "erfolg"
    FEHLER = "fehler"
    VERBESSERUNGS_IDEE = "verbesserungs-idee"
    SKILL_SELECTION = "skill-selection"


class FeedbackStatus(str, Enum):
    NEU = "neu"
    GEPRUEFT = "geprueft"
    UMGESETZT = "umgesetzt"
    KI_AUSFUEHRUNG = "ki-ausfuehrung"


class FeedbackEntry(BaseModel):
    id: str
    titel: str
    typ: FeedbackTyp
    status: FeedbackStatus = FeedbackStatus.NEU
    verantwortlich: str = "[OWNER]"
    erstellt_von: str = "user"
    erstellt_am: date = Field(default_factory=date.today)
    skill_id: str | None = None
    task_ref: str | None = None
    was_ist_passiert: str = ""
    learning: str = ""
    umgesetzte_aktion: str = ""
    tags: list[str] = Field(default_factory=list)
    path: Path | None = None


# --------------------------------------------------------------------------- #
# Skill-Selection
# --------------------------------------------------------------------------- #


class MatchQuality(str, Enum):
    HOCH = "hoch"
    MITTEL = "mittel"
    NIEDRIG = "niedrig"
    NONE = "none"


class SkillMatch(BaseModel):
    skill_id: str
    name: str
    score: float
    quality: MatchQuality
    begruendung: str = ""


# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def to_yaml_safe(value: Any) -> Any:
    """Konvertiere Enums zu ihrem Wert für YAML-Dumps."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_yaml_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_yaml_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value
