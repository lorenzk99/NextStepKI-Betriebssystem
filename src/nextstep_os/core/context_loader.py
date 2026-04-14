"""Context-Loader: lädt Kontext in der 3-Stufen-Hierarchie.

- **Stufe 1 (Kern):** Immer geladen (persönlicher Kern + Governance + Skill-Kern).
- **Stufe 2 (Aufgabe):** Situativ – abhängig vom aktiven Skill.
- **Stufe 3 (Hintergrund):** On-Demand – nur wenn explizit angefordert.

Der Loader respektiert Token-Budgets pro Stufe (grobe Heuristik:
~4 Zeichen ≈ 1 Token).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..config import Config
from .models import ContextEntry, ContextTyp, Skill
from .registry import load_context_registry


# --------------------------------------------------------------------------- #
# Heuristik
# --------------------------------------------------------------------------- #


def estimate_tokens(text: str) -> int:
    """Sehr grobe Token-Schätzung (~4 Zeichen / Token)."""
    return max(1, len(text) // 4)


# --------------------------------------------------------------------------- #
# Parsing des Registers
# --------------------------------------------------------------------------- #


def _parse_entry(raw: dict) -> ContextEntry:
    typ_raw = raw.get("typ", "dokument")
    try:
        typ = ContextTyp(typ_raw)
    except ValueError:
        typ = ContextTyp.DOKUMENT
    return ContextEntry(
        id=raw["id"],
        name=raw["name"],
        path=raw["path"],
        typ=typ,
        kontext_stufe=int(raw.get("kontext_stufe", 1)),
        token_schaetzung=int(raw.get("token_schaetzung", 0)),
        aktualisierung=raw.get("aktualisierung", "bei_bedarf"),
        status=raw.get("status", "Aktiv"),
        tags=list(raw.get("tags") or []),
        beschreibung=(raw.get("beschreibung") or "").strip(),
        skills=list(raw.get("skills") or []),
    )


def load_entries(config: Config) -> list[ContextEntry]:
    """Alle Kontext-Einträge aus dem Register laden."""
    raw_entries = load_context_registry(config.paths.context_index)
    return [_parse_entry(raw) for raw in raw_entries]


# --------------------------------------------------------------------------- #
# Daten-Modell für das geladene Kontext-Set
# --------------------------------------------------------------------------- #


@dataclass
class LoadedContext:
    """Ein geladener Kontext-Block (Pfad + Inhalt + Meta)."""

    entry: ContextEntry
    content: str
    tokens: int


@dataclass
class ContextBundle:
    """Das Ergebnis des Context-Loadings – alle 3 Stufen gebündelt."""

    stufe_1: list[LoadedContext] = field(default_factory=list)
    stufe_2: list[LoadedContext] = field(default_factory=list)
    stufe_3: list[LoadedContext] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (entry_id, reason)

    def render(self) -> str:
        """Gib den gesamten Kontext als Markdown-String zurück."""
        parts: list[str] = []
        for label, items in (
            ("Stufe 1 – Kern-Kontext", self.stufe_1),
            ("Stufe 2 – Aufgaben-Kontext", self.stufe_2),
            ("Stufe 3 – Hintergrund", self.stufe_3),
        ):
            if not items:
                continue
            parts.append(f"# {label}\n")
            for item in items:
                parts.append(f"## {item.entry.name} (`{item.entry.path}`)\n")
                parts.append(item.content.strip())
                parts.append("")  # Leerzeile
        return "\n".join(parts).strip()

    def total_tokens(self) -> int:
        return sum(i.tokens for i in self.stufe_1 + self.stufe_2 + self.stufe_3)


# --------------------------------------------------------------------------- #
# Lade-Logik
# --------------------------------------------------------------------------- #


def _read_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _read_directory(path: Path, *, limit: int = 10) -> str:
    """Inhalte eines Verzeichnisses (Top-Level-MD) aggregieren."""
    if not path.exists() or not path.is_dir():
        return ""
    md_files = sorted(path.glob("*.md"))[:limit]
    parts: list[str] = []
    for md in md_files:
        parts.append(f"### {md.name}\n")
        parts.append(_read_file(md))
        parts.append("")
    return "\n".join(parts)


def _load_entry(entry: ContextEntry, config: Config) -> LoadedContext | None:
    full_path = config.paths.data / entry.path
    if entry.typ in {ContextTyp.DOKUMENT, ContextTyp.PERSONAL, ContextTyp.PERSONEN_KONTEXT}:
        content = _read_file(full_path)
    elif entry.typ == ContextTyp.DATENBANK:
        content = _read_directory(full_path)
    elif entry.typ == ContextTyp.WEBSEITE:
        content = f"[Webseiten-Kontext »{entry.name}«: {entry.path}]"
    elif entry.typ == ContextTyp.API:
        content = f"[API-Kontext »{entry.name}«: {entry.path}]"
    else:
        content = _read_file(full_path) or _read_directory(full_path)
    if not content:
        return None
    return LoadedContext(entry=entry, content=content, tokens=estimate_tokens(content))


def _fits(tokens: int, used: int, budget: int) -> bool:
    return used + tokens <= budget


def load_context_for_skill(
    config: Config,
    skill: Skill | None,
    *,
    all_entries: Iterable[ContextEntry] | None = None,
    mit_hintergrund: bool = False,
) -> ContextBundle:
    """Kontext für einen (optionalen) Skill zusammenstellen.

    - Stufe 1: persönlicher Kern + Governance + Skill-spezifisch deklarierte
      Stufe-1-Pfade.
    - Stufe 2: alle Einträge, die `skill.id` in ihren `skills` listen, plus
      Stufe-2-Pfade aus dem Skill-Frontmatter.
    - Stufe 3: nur wenn `mit_hintergrund=True`.
    """
    entries = list(all_entries) if all_entries is not None else load_entries(config)
    budgets = config.token_budgets
    bundle = ContextBundle()

    # --- Stufe 1 ----------------------------------------------------------- #
    used_1 = 0
    stufe_1_paths: set[str] = set()

    # a) Register-Einträge mit Stufe 1 + (global oder für diesen Skill)
    for entry in entries:
        if entry.status != "Aktiv" or entry.kontext_stufe != 1:
            continue
        is_for_skill = (
            "*" in entry.skills
            or not entry.skills
            or (skill is not None and skill.id in entry.skills)
        )
        # Personal-Kontext immer laden
        is_personal = entry.typ == ContextTyp.PERSONAL
        if not (is_for_skill or is_personal):
            continue
        loaded = _load_entry(entry, config)
        if not loaded:
            bundle.skipped.append((entry.id, "Inhalt leer oder nicht gefunden"))
            continue
        if not _fits(loaded.tokens, used_1, budgets.stufe_1):
            bundle.skipped.append((entry.id, "Token-Budget Stufe 1 überschritten"))
            continue
        bundle.stufe_1.append(loaded)
        used_1 += loaded.tokens
        stufe_1_paths.add(entry.path)

    # b) Skill-spezifische Stufe-1-Pfade (Freitext-Pfade aus dem Frontmatter)
    if skill is not None:
        for rel in skill.context.stufe_1_kern:
            if rel in stufe_1_paths:
                continue
            loaded = _load_path(rel, config, stufe=1)
            if not loaded:
                bundle.skipped.append((rel, "Skill-Kern-Pfad nicht lesbar"))
                continue
            if not _fits(loaded.tokens, used_1, budgets.stufe_1):
                bundle.skipped.append((rel, "Token-Budget Stufe 1 überschritten"))
                continue
            bundle.stufe_1.append(loaded)
            used_1 += loaded.tokens

    # --- Stufe 2 ----------------------------------------------------------- #
    used_2 = 0
    if skill is not None:
        # a) Register-Einträge für diesen Skill auf Stufe 2
        for entry in entries:
            if entry.status != "Aktiv" or entry.kontext_stufe != 2:
                continue
            if skill.id not in entry.skills and "*" not in entry.skills:
                continue
            loaded = _load_entry(entry, config)
            if not loaded:
                bundle.skipped.append((entry.id, "Inhalt leer"))
                continue
            if not _fits(loaded.tokens, used_2, budgets.stufe_2):
                bundle.skipped.append((entry.id, "Token-Budget Stufe 2 überschritten"))
                continue
            bundle.stufe_2.append(loaded)
            used_2 += loaded.tokens

        # b) Freitext-Pfade aus dem Skill-Frontmatter
        for rel in skill.context.stufe_2_aufgabe:
            loaded = _load_path(rel, config, stufe=2)
            if not loaded:
                bundle.skipped.append((rel, "Stufe-2-Pfad nicht lesbar"))
                continue
            if not _fits(loaded.tokens, used_2, budgets.stufe_2):
                bundle.skipped.append((rel, "Token-Budget Stufe 2 überschritten"))
                continue
            bundle.stufe_2.append(loaded)
            used_2 += loaded.tokens

    # --- Stufe 3 ----------------------------------------------------------- #
    if mit_hintergrund and skill is not None:
        used_3 = 0
        for rel in skill.context.stufe_3_hintergrund:
            loaded = _load_path(rel, config, stufe=3)
            if not loaded:
                bundle.skipped.append((rel, "Stufe-3-Pfad nicht lesbar"))
                continue
            if not _fits(loaded.tokens, used_3, budgets.stufe_3):
                bundle.skipped.append((rel, "Token-Budget Stufe 3 überschritten"))
                continue
            bundle.stufe_3.append(loaded)
            used_3 += loaded.tokens

    return bundle


def _load_path(rel_path: str, config: Config, *, stufe: int) -> LoadedContext | None:
    """Hilfsfunktion: relativen Daten-Pfad als anonymen LoadedContext laden."""
    path = config.paths.data / rel_path
    if path.is_dir():
        content = _read_directory(path)
    else:
        content = _read_file(path)
    if not content:
        return None
    ad_hoc = ContextEntry(
        id=f"ad-hoc::{rel_path}",
        name=Path(rel_path).name,
        path=rel_path,
        typ=ContextTyp.DOKUMENT,
        kontext_stufe=stufe,
    )
    return LoadedContext(entry=ad_hoc, content=content, tokens=estimate_tokens(content))


def load_boot_context(config: Config) -> ContextBundle:
    """Boot-Kontext: nur persönlicher Kern + Governance (kein Skill aktiv)."""
    return load_context_for_skill(config, skill=None)
