"""Feedback-Loop: Silent Patch (Skill-MD) + Feedback-DB (YAML-Einträge).

Zwei Wirkmechanismen, die in `system_prompts/os_agent.md` festgelegt sind:

1. **Silent Patch:** Eine Skill-Learning-Zeile wird direkt in die Sektion
   `## 📝 Learnings` der Skill-MD geschrieben (chronologisch).
2. **Feedback-DB:** Strukturierte Einträge in `data/feedback/entries/` für
   Monthly Reviews und systemische Auswertungen.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import frontmatter
import yaml

from ..config import Config
from .models import FeedbackEntry, FeedbackStatus, FeedbackTyp, to_yaml_safe


LEARNINGS_HEADER_RE = re.compile(r"^##\s+📝?\s*Learnings\s*$", re.MULTILINE)


# --------------------------------------------------------------------------- #
# Silent Patch
# --------------------------------------------------------------------------- #


def silent_patch_skill(skill_path: Path, learning: str, *, heute: date | None = None) -> None:
    """Hänge einen Learning-Eintrag an die `📝 Learnings`-Sektion der Skill-MD.

    Wenn die Sektion nicht existiert, wird sie am Ende des Body angelegt.
    """
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill-Datei nicht gefunden: {skill_path}")
    heute = heute or date.today()
    learning = learning.strip()
    if not learning:
        raise ValueError("Leeres Learning kann nicht gepatcht werden.")

    post = frontmatter.load(skill_path)
    body = post.content
    entry = f"- **{heute.isoformat()}:** {learning}"

    match = LEARNINGS_HEADER_RE.search(body)
    if match:
        # An Header anhängen: finde Header-Ende und füge direkt danach ein.
        insert_at = match.end()
        # Optional: Kommentar-Block direkt nach Header überspringen.
        rest = body[insert_at:]
        prefix = body[:insert_at]
        # Leerzeile + Eintrag + Rest beibehalten
        new_body = f"{prefix}\n{entry}\n{rest.lstrip(chr(10))}"
    else:
        new_body = f"{body.rstrip()}\n\n## 📝 Learnings\n\n{entry}\n"

    post.content = new_body
    with skill_path.open("w", encoding="utf-8") as fh:
        fh.write(frontmatter.dumps(post, sort_keys=False))


# --------------------------------------------------------------------------- #
# Feedback-DB
# --------------------------------------------------------------------------- #


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, *, maxlen: int = 40) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug or "eintrag")[:maxlen]


def _feedback_path(config: Config, entry: FeedbackEntry) -> Path:
    dir_ = config.paths.feedback_dir
    dir_.mkdir(parents=True, exist_ok=True)
    fname = f"{entry.erstellt_am.isoformat()}-{_slugify(entry.titel)}.yaml"
    return dir_ / fname


def write_feedback(config: Config, entry: FeedbackEntry) -> Path:
    """Persistiere einen Feedback-Eintrag als YAML."""
    path = _feedback_path(config, entry)
    data = to_yaml_safe(entry.model_dump(exclude={"path"}))
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
    entry.path = path
    return path


def build_feedback(
    *,
    titel: str,
    typ: FeedbackTyp,
    was_ist_passiert: str = "",
    learning: str = "",
    umgesetzte_aktion: str = "",
    skill_id: str | None = None,
    task_ref: str | None = None,
    tags: list[str] | None = None,
    verantwortlich: str = "[OWNER]",
    erstellt_von: str = "user",
    status: FeedbackStatus = FeedbackStatus.NEU,
) -> FeedbackEntry:
    """Hilfsfunktion: erzeugt einen FeedbackEntry mit Default-ID (Datum-Slug)."""
    heute = date.today()
    entry_id = f"{heute.isoformat()}-{_slugify(titel)}"
    return FeedbackEntry(
        id=entry_id,
        titel=titel.strip(),
        typ=typ,
        status=status,
        verantwortlich=verantwortlich,
        erstellt_von=erstellt_von,
        erstellt_am=heute,
        skill_id=skill_id,
        task_ref=task_ref,
        was_ist_passiert=was_ist_passiert.strip(),
        learning=learning.strip(),
        umgesetzte_aktion=umgesetzte_aktion.strip(),
        tags=list(tags or []),
    )


def record(
    config: Config,
    *,
    titel: str,
    typ: FeedbackTyp,
    learning: str = "",
    was_ist_passiert: str = "",
    umgesetzte_aktion: str = "",
    skill_id: str | None = None,
    skill_path: Path | None = None,
    patch_skill: bool = False,
    **kwargs,
) -> FeedbackEntry:
    """Komfort-Funktion: Feedback + optionaler Silent Patch in einem Aufruf."""
    entry = build_feedback(
        titel=titel,
        typ=typ,
        was_ist_passiert=was_ist_passiert,
        learning=learning,
        umgesetzte_aktion=umgesetzte_aktion,
        skill_id=skill_id,
        **kwargs,
    )
    write_feedback(config, entry)
    if patch_skill and skill_path and learning:
        silent_patch_skill(skill_path, learning)
    return entry


# --------------------------------------------------------------------------- #
# Auswertung (Monthly Review)
# --------------------------------------------------------------------------- #


def list_feedback(config: Config) -> list[FeedbackEntry]:
    """Alle Feedback-YAMLs im Verzeichnis einlesen."""
    dir_ = config.paths.feedback_dir
    if not dir_.exists():
        return []
    entries: list[FeedbackEntry] = []
    for yml in sorted(dir_.glob("*.yaml")):
        with yml.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        try:
            entry = FeedbackEntry(**data)
        except Exception:  # noqa: BLE001 - best-effort parse
            continue
        entry.path = yml
        entries.append(entry)
    return entries
