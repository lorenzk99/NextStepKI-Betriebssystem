"""Gemeinsame Test-Fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nextstep_os.config import Config, Models, Paths, TokenBudgets  # noqa: E402


@pytest.fixture
def real_config() -> Config:
    """Echte Config, die auf die Projekt-Daten zeigt."""
    return Config()


@pytest.fixture
def isolated_config(tmp_path: Path) -> Config:
    """Isolierte Config mit leeren Data- und Prompt-Ordnern."""
    data_dir = tmp_path / "data"
    prompts_dir = tmp_path / "system_prompts"
    (data_dir / "skills").mkdir(parents=True)
    (data_dir / "context/personal").mkdir(parents=True)
    (data_dir / "context/sources").mkdir(parents=True)
    (data_dir / "governance").mkdir(parents=True)
    (data_dir / "feedback/entries").mkdir(parents=True)
    (data_dir / "tasks").mkdir(parents=True)
    (data_dir / "meetings/inbox").mkdir(parents=True)
    (data_dir / "meetings/briefings").mkdir(parents=True)
    prompts_dir.mkdir(parents=True)

    return Config(
        paths=Paths(root=tmp_path, data=data_dir, prompts=prompts_dir),
        models=Models(),
        token_budgets=TokenBudgets(stufe_1=10_000, stufe_2=10_000, stufe_3=5_000),
        log_level="INFO",
        anthropic_api_key=None,
    )
