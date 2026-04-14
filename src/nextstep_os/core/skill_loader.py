"""Skill-Loader: lädt Skills aus `data/skills/` und wählt den besten Match.

Matching-Strategie
------------------
Keyword-Matching mit Phrase-Gewichtung:

1. Exakter Phrase-Treffer (Multi-Wort-Keyword als zusammenhängende Phrase
   in der Query): +3.0 · gewichtet mit Wortzahl (phrase_len * 1.5).
2. Exakter Einzel-Wort-Keyword-Treffer (Token-Match): +2.0.
3. Teilweiser Token-Überlapp (Mehrwort-Keyword, einzelne Wörter matchen):
   +0.5 pro überlappendem Token.
4. Name-Match: +0.75 pro Token.
5. Beschreibungs-Match: +0.15 pro Token (sehr leicht, reines Tie-Breaking).

Stop-Wörter ("für", "und", "ein", ...) werden ignoriert. Kurze Keywords
(<3 Zeichen) ebenfalls. Gemeinsame Endungen wie "erstellen", "anlegen"
sind als Keyword in mehreren Skills möglich — dadurch löst die Phrase-
Regel (1) die Kollision: »angebot erstellen« schlägt »neuen skill erstellen«.
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

# Deutsche + englische Stop-Wörter (reduziertes Set — nur die wirklich nichtssagenden)
_STOPWORDS = frozenset({
    # Deutsch
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "einer", "eines", "und", "oder", "aber", "für", "fuer", "mit", "ohne",
    "von", "vom", "zum", "zur", "zu", "bei", "nach", "auf", "aus", "in", "im",
    "an", "am", "als", "auch", "schon", "noch", "heute", "morgen", "gestern",
    "ich", "du", "er", "sie", "es", "wir", "ihr", "mir", "mich", "dich", "dir",
    "sich", "ist", "war", "sind", "hat", "habe", "haben", "werde", "wird",
    "kann", "möchte", "moechte", "muss", "soll", "nicht", "kein", "keine",
    "mein", "meine", "meinen", "meinem", "meiner", "dein", "deine",
    "so", "nun", "mal", "doch", "wie", "was", "wer", "wenn", "dann", "weil",
    # Englisch (für gemischte Queries)
    "the", "a", "an", "and", "or", "but", "for", "with", "from", "to",
    "at", "in", "on", "of", "is", "are", "was", "were", "be", "been",
    "i", "you", "we", "they", "my", "your", "this", "that",
})


def _tokenize(text: str, *, filter_stopwords: bool = True, min_len: int = 3) -> list[str]:
    tokens = [t.strip().lower() for t in _WORD_SPLIT_RE.split(text or "") if t.strip()]
    if filter_stopwords:
        return [t for t in tokens if len(t) >= min_len and t not in _STOPWORDS]
    return [t for t in tokens if len(t) >= min_len]


def _is_phrase(keyword: str) -> bool:
    return len(keyword.split()) > 1


def _phrase_match(query_lower: str, phrase_lower: str) -> bool:
    """Prüft, ob die Phrase als zusammenhängende Tokenfolge in der Query vorkommt."""
    # Wortgrenzen erzwingen, damit »angebot« nicht in »angebotsseite« matcht
    # es sei denn, wir wollen das explizit.
    escaped = re.escape(phrase_lower)
    pattern = rf"(?<![a-zäöüß0-9]){escaped}(?![a-zäöüß0-9])"
    return re.search(pattern, query_lower) is not None


def _score_entry(query: str, entry: SkillRegistryEntry) -> tuple[float, str]:
    """Scoring mit Phrase-Bevorzugung und Stop-Wort-Filter."""
    if not query.strip():
        return 0.0, "leere Anfrage"

    q_lower = query.lower().strip()
    q_tokens_raw = _tokenize(q_lower, filter_stopwords=False, min_len=1)
    q_tokens = set(_tokenize(q_lower))

    score = 0.0
    reasons: list[str] = []
    matched_phrases: set[str] = set()

    # ---------- 1. Keyword-Phrase-Matching ------------------------------- #
    for kw in entry.keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        if _is_phrase(kw_lower):
            if _phrase_match(q_lower, kw_lower):
                phrase_len = len(kw_lower.split())
                boost = 3.0 + 1.5 * (phrase_len - 1)  # 3.0 (2 Wörter), 4.5 (3 Wörter), ...
                score += boost
                matched_phrases.add(kw_lower)
                reasons.append(f"Phrase-Match: »{kw}« (+{boost:.1f})")

    # ---------- 2. Einzel-Token-Keyword-Matching ------------------------- #
    for kw in entry.keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower or kw_lower in matched_phrases:
            continue
        if _is_phrase(kw_lower):
            # Mehrwort-Keyword ohne Phrase-Treffer: Teil-Überlapp zählt leicht
            kw_tokens = set(_tokenize(kw_lower))
            overlap = kw_tokens & q_tokens
            if overlap:
                boost = 0.5 * len(overlap)
                score += boost
                reasons.append(
                    f"Teil-Match »{kw}«: {', '.join(sorted(overlap))} (+{boost:.2f})"
                )
        else:
            # Single-Wort-Keyword → Token muss identisch in Query vorkommen
            if kw_lower in q_tokens:
                score += 2.0
                reasons.append(f"Keyword-Match: »{kw}« (+2.0)")

    # ---------- 3. Name-Match -------------------------------------------- #
    name_tokens = set(_tokenize(entry.name))
    name_overlap = name_tokens & q_tokens
    if name_overlap:
        boost = 0.75 * len(name_overlap)
        score += boost
        reasons.append(f"Name-Match: {', '.join(sorted(name_overlap))} (+{boost:.2f})")

    # ---------- 4. Beschreibungs-Match (schwach) ------------------------- #
    beschr_tokens = set(_tokenize(entry.beschreibung))
    beschr_overlap = beschr_tokens & q_tokens
    # Name-Token nicht doppelt zählen
    beschr_overlap -= name_tokens
    if beschr_overlap:
        boost = 0.15 * len(beschr_overlap)
        score += boost
        reasons.append(
            f"Beschreibung: {', '.join(sorted(list(beschr_overlap))[:3])} (+{boost:.2f})"
        )

    # Für vollständig keywordlose Queries, die trotzdem den Skill-Namen enthalten,
    # ist das okay. Sonst sinkt der Score natürlich gegen 0.
    if not reasons:
        return 0.0, "kein Treffer"

    return score, "; ".join(reasons)


def _quality_from_score(score: float) -> MatchQuality:
    # Neue Schwellen angepasst an die neue Scoring-Skala
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
    """Finde die Top-N-Skills zu einer Nutzer-Anfrage."""
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
