"""Task-Übersicht: Aufgaben aus `data/tasks/` lesen und aufbereiten.

Die Task-Datenbank wird von der Pipeline (Meeting → Task-Extractor)
befüllt, kann aber auch manuell gepflegt werden (eine MD-Datei pro Task
mit Frontmatter). Dieses Modul ist die Lese-Seite für CLI (`tasks`,
`briefing`) und Dashboard.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import frontmatter

from ..config import Config
from .models import Prioritaet, Task, TaskStatus


#: Status, die als »offen« gelten (erfordern Aktion oder laufen noch)
OPEN_STATUSES = {
    TaskStatus.NEU,
    TaskStatus.SKILL_ZUGEWIESEN,
    TaskStatus.IN_ARBEIT,
    TaskStatus.SKILL_AUSGEFUEHRT,
    TaskStatus.WARTET_AUF_REVIEW,
    TaskStatus.FEHLER,
}

#: Status, bei denen der Nutzer selbst am Zug ist
ACTION_REQUIRED_STATUSES = {
    TaskStatus.WARTET_AUF_REVIEW,
    TaskStatus.FEHLER,
}


def _coerce_status(value: object) -> TaskStatus:
    try:
        return TaskStatus(str(value))
    except ValueError:
        return TaskStatus.NEU


def _coerce_prio(value: object) -> Prioritaet:
    text = str(value or "").strip()
    try:
        return Prioritaet(text)
    except ValueError:
        by_name = {"hoch": Prioritaet.HOCH, "mittel": Prioritaet.MITTEL, "niedrig": Prioritaet.NIEDRIG}
        return by_name.get(text.lower(), Prioritaet.MITTEL)


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def load_task(path: Path) -> Task | None:
    """Eine Task-MD-Datei robust parsen (None bei unbrauchbarem Inhalt)."""
    try:
        post = frontmatter.load(path)
    except Exception:  # noqa: BLE001
        return None
    meta = dict(post.metadata)
    if not meta:
        return None
    return Task(
        id=str(meta.get("id") or path.stem),
        titel=str(meta.get("titel") or path.stem),
        status=_coerce_status(meta.get("status")),
        prioritaet=_coerce_prio(meta.get("prioritaet")),
        faellig=_coerce_date(meta.get("faellig")),
        meeting_ref=meta.get("meeting_ref"),
        zugewiesener_skill=meta.get("zugewiesener_skill"),
        erstellt_am=_coerce_date(meta.get("erstellt_am")) or date.today(),
        body=post.content or "",
        path=path,
    )


_PRIO_ORDER = {Prioritaet.HOCH: 0, Prioritaet.MITTEL: 1, Prioritaet.NIEDRIG: 2}


def load_tasks(config: Config, *, nur_offene: bool = False) -> list[Task]:
    """Alle Tasks laden, sortiert: Priorität > Fälligkeit > Erstellungsdatum."""
    tasks_dir = config.paths.tasks_dir
    if not tasks_dir.exists():
        return []
    tasks: list[Task] = []
    for md in sorted(tasks_dir.glob("*.md")):
        task = load_task(md)
        if task is None:
            continue
        if nur_offene and task.status not in OPEN_STATUSES:
            continue
        tasks.append(task)
    tasks.sort(
        key=lambda t: (
            _PRIO_ORDER.get(t.prioritaet, 1),
            t.faellig or date.max,
            t.erstellt_am,
        )
    )
    return tasks


def overdue(tasks: list[Task], *, heute: date | None = None) -> list[Task]:
    """Überfällige offene Tasks."""
    heute = heute or date.today()
    return [
        t for t in tasks
        if t.faellig and t.faellig < heute and t.status in OPEN_STATUSES
    ]


def by_status(tasks: list[Task]) -> dict[str, list[Task]]:
    """Tasks nach Status gruppieren (Reihenfolge: Pipeline-Fluss)."""
    grouped: dict[str, list[Task]] = {}
    for status in TaskStatus:
        items = [t for t in tasks if t.status == status]
        if items:
            grouped[status.value] = items
    return grouped
