"""Zentrale Konfiguration — Pfade, Modell-IDs, Token-Budgets.

Alle Werte können über Environment-Variablen überschrieben werden. Lade
`.env` am Programmstart (erfolgt in `cli.py`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# Projekt-Root ermitteln (Ordner, der `pyproject.toml` enthält)
def _project_root() -> Path:
    # src/nextstep_os/config.py -> ../../..
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT: Path = _project_root()


@dataclass(frozen=True)
class Paths:
    root: Path = PROJECT_ROOT
    data: Path = field(default_factory=lambda: PROJECT_ROOT / _env("NEXTSTEP_DATA_DIR", "data"))
    prompts: Path = field(
        default_factory=lambda: PROJECT_ROOT / _env("NEXTSTEP_PROMPTS_DIR", "system_prompts")
    )

    @property
    def skills_dir(self) -> Path:
        return self.data / "skills"

    @property
    def skills_index(self) -> Path:
        return self.skills_dir / "_index.yaml"

    @property
    def context_dir(self) -> Path:
        return self.data / "context"

    @property
    def context_index(self) -> Path:
        return self.context_dir / "_index.yaml"

    @property
    def context_personal(self) -> Path:
        return self.context_dir / "personal"

    @property
    def context_sources(self) -> Path:
        return self.context_dir / "sources"

    @property
    def governance_handbook(self) -> Path:
        return self.data / "governance" / "handbuch.md"

    @property
    def feedback_dir(self) -> Path:
        return self.data / "feedback" / "entries"

    @property
    def tasks_dir(self) -> Path:
        return self.data / "tasks"

    @property
    def meetings_dir(self) -> Path:
        return self.data / "meetings"

    @property
    def meetings_inbox(self) -> Path:
        return self.meetings_dir / "inbox"

    @property
    def briefings_dir(self) -> Path:
        return self.meetings_dir / "briefings"


@dataclass(frozen=True)
class Models:
    os_agent: str = field(
        default_factory=lambda: _env("NEXTSTEP_MODEL_OS_AGENT", "claude-opus-4-6")
    )
    pipeline: str = field(
        default_factory=lambda: _env("NEXTSTEP_MODEL_PIPELINE", "claude-sonnet-4-6")
    )
    fast: str = field(
        default_factory=lambda: _env("NEXTSTEP_MODEL_FAST", "claude-haiku-4-5-20251001")
    )


@dataclass(frozen=True)
class TokenBudgets:
    stufe_1: int = field(default_factory=lambda: _env_int("NEXTSTEP_TOKEN_BUDGET_STUFE_1", 6000))
    stufe_2: int = field(default_factory=lambda: _env_int("NEXTSTEP_TOKEN_BUDGET_STUFE_2", 8000))
    stufe_3: int = field(default_factory=lambda: _env_int("NEXTSTEP_TOKEN_BUDGET_STUFE_3", 4000))


@dataclass(frozen=True)
class Config:
    paths: Paths = field(default_factory=Paths)
    models: Models = field(default_factory=Models)
    token_budgets: TokenBudgets = field(default_factory=TokenBudgets)
    log_level: str = field(default_factory=lambda: _env("NEXTSTEP_LOG_LEVEL", "INFO"))
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )


def load_config() -> Config:
    """Lade die aktuelle Konfiguration (auf Basis von Env-Vars)."""
    return Config()
