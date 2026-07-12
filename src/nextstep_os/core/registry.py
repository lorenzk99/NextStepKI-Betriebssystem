"""Lese- und Schreibzugriff auf die YAML-Register der Daten-Ordner.

Register (``_index.yaml``) sind Schnell-Indizes über die Markdown-Einträge
im jeweiligen Daten-Ordner. Quelle der Wahrheit bleibt die Markdown-Datei;
das Register wird beim Build oder Update synchron gehalten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import to_yaml_safe


def read_yaml(path: Path) -> dict[str, Any]:
    """Lies eine YAML-Datei, liefere leeres Dict bei Abwesenheit."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Erwartet Dict in {path}, erhalten {type(data).__name__}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Schreibe ein Dict als YAML (atomar: temp-Datei + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = to_yaml_safe(data)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            safe,
            fh,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    tmp.replace(path)


def load_skill_registry(path: Path) -> list[dict[str, Any]]:
    """Lade die `skills:`-Liste aus dem Skill-Register."""
    data = read_yaml(path)
    # `skills:` ohne Wert (YAML-null) ⇒ leere Liste
    skills = data.get("skills") or []
    if not isinstance(skills, list):
        raise ValueError(f"`skills` in {path} muss eine Liste sein")
    return skills


def load_context_registry(path: Path) -> list[dict[str, Any]]:
    """Lade die `entries:`-Liste aus dem Kontext-Register."""
    data = read_yaml(path)
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError(f"`entries` in {path} muss eine Liste sein")
    return entries


def update_skill_registry_entry(path: Path, skill_id: str, patch: dict[str, Any]) -> None:
    """Patch einen einzelnen Skill-Eintrag im Register (ID-basiert)."""
    data = read_yaml(path)
    skills = data.get("skills") or []
    updated = False
    for entry in skills:
        if entry.get("id") == skill_id:
            entry.update(patch)
            updated = True
            break
    if not updated:
        raise KeyError(f"Skill `{skill_id}` nicht im Register `{path}` gefunden")
    data["skills"] = skills
    write_yaml(path, data)


def append_skill_registry_entry(path: Path, entry: dict[str, Any]) -> None:
    """Hänge einen neuen Skill an das Register an (duplicate-safe)."""
    data = read_yaml(path)
    skills = data.get("skills") or []
    if any(existing.get("id") == entry.get("id") for existing in skills):
        raise ValueError(f"Skill `{entry.get('id')}` existiert bereits im Register")
    skills.append(entry)
    data["skills"] = skills
    write_yaml(path, data)
