"""Skill-Loader: lädt Skills aus `data/skills/` und wählt den besten Match.

Arbeitsweise
------------
1. Register (`_index.yaml`) lesen → Schnellübersicht aller Skills.
2. Für Matching: Keywords + Name + Beschreibung aus dem Register → lokaler
   Score (substring-basiert, lower-case).
3. Bei Bedarf: vollständige Skill-MD parsen (Frontmatter + Body) und als
   `Skill`-Pydantic-Objekt zurückgeben.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import frontmatter

from ..config import Config
from .models import (
    Ampel,
    ExecutionMode,
    MatchQuality,
    Nutzungsart,
    Skill,
    SkillContext,
    SkillMatch,
    SkillRegistryEntry,
    SkillStatus,
)
from .registry import load_skill_registry


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def _coerce_enum(enum_cls, value, default):
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        for member in enum_cls:
            if str(member.value).lower() == str(value).lower():
                return member
        return default


def _parse_registry_entry(raw: dict) -> SkillRegistryEntry:
    return SkillRegistryEntry(
        id=raw["id"],
        name=raw["name"],
        path=raw["path"],
        status=_coerce_enum(SkillStatus, raw.get("status"), SkillStatus.ENTWURF),
        owner=raw.get("owner", "[OWNER]"),
        ampel=raw.get("ampel", Ampel.GELB.value),
        execution_mode=_coerce_enum(
            ExecutionMode, raw.get("execution_mode"), ExecutionMode.STRICT
        ),
        nutzungsart=_coerce_enum(
            Nutzungsart, raw.get("nutzungsart"), Nutzungsart.PUBLIC
        ),
        keywords=list(raw.get("keywords") or []),
        beschreibung=raw.get("beschreibung", "").strip(),
    )


def load_registry(config: Config) -> list[SkillRegistryEntry]:
    """Lade alle Skill-Register-Einträge."""
    raw_entries = load_skill_registry(config.paths.skills_index)
    return [_parse_registry_entry(raw) for raw in raw_entries]


def load_skill(skill_path: Path) -> Skill:
    """Parse eine Skill-Markdown-Datei vollständig."""
    post = frontmatter.load(skill_path)
    fm = dict(post.metadata)
    ctx_raw = fm.get("context") or {}
    context = SkillContext(
        stufe_1_kern=list(ctx_raw.get("stufe_1_kern") or []),
        stufe_2_aufgabe=list(ctx_raw.get("stufe_2_aufgabe") or []),
        stufe_3_hintergrund=list(ctx_raw.get("stufe_3_hintergrund") or []),
    )
    return Skill(
        id=fm["id"],
        name=fm["name"],
        status=_coerce_enum(SkillStatus, fm.get("status"), SkillStatus.ENTWURF),
        owner=fm.get("owner", "[OWNER]"),
        ampel=_coerce_enum(Ampel, fm.get("ampel"), Ampel.GELB),
        execution_mode=_coerce_enum(
            ExecutionMode, fm.get("execution_mode"), ExecutionMode.STRICT
        ),
        nutzungsart=_coerce_enum(
            Nutzungsart, fm.get("nutzungsart"), Nutzungsart.PUBLIC
        ),
        keywords=list(fm.get("keywords") or []),
        beschreibung=(fm.get("beschreibung") or "").strip(),
        eingabe=list(fm.get("eingabe") or []),
        ausgabe=list(fm.get("ausgabe") or []),
        context=context,
        update_quellen=list(fm.get("update_quellen") or []),
        body=post.content.strip(),
        path=skill_path,
    )


def load_skill_by_id(config: Config, skill_id: str) -> Skill:
    """Hilfsfunktion: Skill vollständig über seine ID laden."""
    registry = load_registry(config)
    for entry in registry:
        if entry.id == skill_id:
            full_path = config.paths.data / entry.path
            return load_skill(full_path)
    raise KeyError(f"Skill `{skill_id}` nicht im Register gefunden")


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


_WORD_SPLIT_RE = re.compile(r"[^a-zäöüß0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    tokens = [t.strip().lower() for t in _WORD_SPLIT_RE.split(text or "") if t.strip()]
    return [t for t in tokens if len(t) > 1]


def _score_entry(query: str, entry: SkillRegistryEntry) -> tuple[float, str]:
    """Einfaches Keyword-/Substring-Scoring.

    - Treffer auf exaktem Keyword: +2.0
    - Teiltreffer auf Keyword (Substring): +1.0
    - Name/Beschreibung Token-Match: +0.5
    Rückgabe: (Score, Begründung)
    """
    q_lower = query.lower().strip()
    q_tokens = set(_tokenize(q_lower))
    if not q_tokens and not q_lower:
        return 0.0, "leere Anfrage"

    score = 0.0
    reasons: list[str] = []

    for kw in entry.keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        if kw_lower in q_lower or q_lower in kw_lower:
            score += 2.0
            reasons.append(f"Keyword-Match: »{kw}«")
        else:
            kw_tokens = set(_tokenize(kw_lower))
            overlap = kw_tokens & q_tokens
            if overlap:
                score += 1.0
                reasons.append(f"Teil-Match Keyword »{kw}« ({', '.join(overlap)})")

    name_tokens = set(_tokenize(entry.name))
    name_overlap = name_tokens & q_tokens
    if name_overlap:
        score += 0.5 * len(name_overlap)
        reasons.append(f"Name-Match: {', '.join(name_overlap)}")

    beschr_tokens = set(_tokenize(entry.beschreibung))
    beschr_overlap = beschr_tokens & q_tokens
    if beschr_overlap:
        score += 0.25 * len(beschr_overlap)
        reasons.append(f"Beschreibung-Match: {', '.join(list(beschr_overlap)[:3])}")

    return score, "; ".join(reasons) if reasons else "kein Treffer"


def _quality_from_score(score: float) -> MatchQuality:
    if score >= 3.0:
        return MatchQuality.HOCH
    if score >= 1.5:
        return MatchQuality.MITTEL
    if score > 0.0:
        return MatchQuality.NIEDRIG
    return MatchQuality.NONE


def match_skills(
    config: Config,
    query: str,
    *,
    nur_aktive: bool = True,
    limit: int = 5,
    entries: Iterable[SkillRegistryEntry] | None = None,
) -> list[SkillMatch]:
    """Finde die Top-N-Skills zu einer Nutzer-Anfrage.

    Rückgabe nach Score absteigend sortiert. Wenn keine Keywords treffen,
    ist die Liste leer bzw. enthält nur Niedrig-/None-Matches.
    """
    if entries is None:
        entries = load_registry(config)
    matches: list[SkillMatch] = []
    for entry in entries:
        if nur_aktive and entry.status != SkillStatus.AKTIV:
            continue
        score, reason = _score_entry(query, entry)
        matches.append(
            SkillMatch(
                skill_id=entry.id,
                name=entry.name,
                score=round(score, 3),
                quality=_quality_from_score(score),
                begruendung=reason,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:limit]


def best_match(
    config: Config,
    query: str,
    *,
    nur_aktive: bool = True,
    min_quality: MatchQuality = MatchQuality.MITTEL,
) -> SkillMatch | None:
    """Liefere den besten Treffer, sofern er `min_quality` erreicht."""
    order = {
        MatchQuality.NONE: 0,
        MatchQuality.NIEDRIG: 1,
        MatchQuality.MITTEL: 2,
        MatchQuality.HOCH: 3,
    }
    results = match_skills(config, query, nur_aktive=nur_aktive, limit=1)
    if not results:
        return None
    top = results[0]
    if order[top.quality] < order[min_quality]:
        return None
    return top
