"""Tests für Konversations-Gedächtnis und Fallback-Verhalten der Bridge."""

from __future__ import annotations

import asyncio

import pytest

from nextstep_os.agents import os_agent, sdk_bridge
from nextstep_os.agents.sdk_bridge import (
    AgentResult,
    _build_messages,
    _history_as_text,
    query_os_agent,
    stream_os_agent,
)


# --------------------------------------------------------------------------- #
# Message-Building
# --------------------------------------------------------------------------- #


def test_build_messages_appends_current():
    history = [
        {"role": "user", "content": "Hallo"},
        {"role": "assistant", "content": "Hi!"},
    ]
    msgs = _build_messages("Wie hieß meine erste Frage?", history)
    assert len(msgs) == 3
    assert msgs[-1] == {"role": "user", "content": "Wie hieß meine erste Frage?"}
    assert msgs[0]["content"] == "Hallo"


def test_history_as_text_renders_roles():
    text = _history_as_text([
        {"role": "user", "content": "Frage"},
        {"role": "assistant", "content": "Antwort"},
    ])
    assert "Nutzer" in text and "Agent" in text
    assert "Frage" in text and "Antwort" in text


# --------------------------------------------------------------------------- #
# OSAgentState-Historie
# --------------------------------------------------------------------------- #


@pytest.fixture
def isolated_config(isolated_config):
    """Isolierte Config + minimaler OS-Agent-Systemprompt."""
    (isolated_config.paths.prompts / "os_agent.md").write_text(
        "# OS-Agent Testprompt\n", encoding="utf-8"
    )
    return isolated_config


def test_state_remember_caps_history(isolated_config):
    async def go():
        return await os_agent.boot(isolated_config)

    state = asyncio.run(go())
    for i in range(30):
        state.remember(f"frage {i}", f"antwort {i}")
    assert len(state.history) == os_agent.MAX_HISTORY_MESSAGES
    # Die ältesten fliegen raus, die neuesten bleiben
    assert state.history[-1]["content"] == "antwort 29"


def test_handle_records_history_on_success(isolated_config, monkeypatch):
    async def fake_query(config, **kwargs):
        return AgentResult(text="Antwort!", dry_run=False)

    monkeypatch.setattr(os_agent, "query_os_agent", fake_query)

    async def go():
        state = await os_agent.boot(isolated_config)
        await os_agent.handle(state, "Hallo Agent", auto_select=False)
        return state

    state = asyncio.run(go())
    assert state.history == [
        {"role": "user", "content": "Hallo Agent"},
        {"role": "assistant", "content": "Antwort!"},
    ]


def test_handle_skips_history_on_dry_run(isolated_config):
    """Ohne API-Key (DryRun) darf die Historie nicht wachsen."""

    async def go():
        state = await os_agent.boot(isolated_config)
        result = await os_agent.handle(state, "Hallo", auto_select=False)
        return state, result

    state, result = asyncio.run(go())
    assert result.dry_run
    assert state.history == []


def test_handle_passes_history_to_bridge(isolated_config, monkeypatch):
    captured: dict = {}

    async def fake_query(config, **kwargs):
        captured.update(kwargs)
        return AgentResult(text="ok")

    monkeypatch.setattr(os_agent, "query_os_agent", fake_query)

    async def go():
        state = await os_agent.boot(isolated_config)
        state.remember("erste frage", "erste antwort")
        await os_agent.handle(state, "zweite frage", auto_select=False)

    asyncio.run(go())
    assert captured["history"] is not None
    assert captured["history"][0]["content"] == "erste frage"


# --------------------------------------------------------------------------- #
# select_skill: Reset bei No-Match
# --------------------------------------------------------------------------- #


def test_select_skill_resets_state_on_no_match(real_config):
    async def go():
        state = await os_agent.boot(real_config)
        top = await os_agent.select_skill(state, "Schreib eine Mail an einen Kunden")
        assert top is not None and state.active_skill is not None
        # Themenfremde Nachricht ohne Match → Skill-Zustand muss weg
        await os_agent.select_skill(state, "xyzzy quux zorp")
        return state

    state = asyncio.run(go())
    assert state.active_skill is None
    assert state.governance is None
    assert state.task_context is None


# --------------------------------------------------------------------------- #
# stream_os_agent: kein Deadlock, DryRun wird geliefert
# --------------------------------------------------------------------------- #


def test_stream_yields_dry_run_text(isolated_config):
    """Ohne API-Key darf der Stream nicht leer/stumm enden."""

    async def go():
        chunks = []
        async for delta in stream_os_agent(
            isolated_config, system_prompt="s", user_message="u"
        ):
            chunks.append(delta)
        return chunks

    chunks = asyncio.run(asyncio.wait_for(go(), timeout=5))
    assert chunks, "Stream muss DryRun-Text liefern statt nichts"
    assert "DryRun" in "".join(chunks)


def test_stream_no_deadlock_on_runner_exception(isolated_config, monkeypatch):
    """Exception im Runner → Sentinel kommt trotzdem, kein Endlos-Hänger."""

    async def boom(config, **kwargs):
        raise RuntimeError("kaputt")

    monkeypatch.setattr(sdk_bridge, "query_os_agent", boom)

    async def go():
        chunks = []
        with pytest.raises(RuntimeError, match="kaputt"):
            async for delta in stream_os_agent(
                isolated_config, system_prompt="s", user_message="u"
            ):
                chunks.append(delta)

    asyncio.run(asyncio.wait_for(go(), timeout=5))


# --------------------------------------------------------------------------- #
# Fallback: SDK-DryRun (kein CLI) → Direct API wird trotzdem versucht
# --------------------------------------------------------------------------- #


def test_sdk_failure_falls_back_to_direct(monkeypatch, isolated_config):
    from dataclasses import replace

    cfg = replace(isolated_config, anthropic_api_key="sk-test-123")
    calls: list[str] = []

    async def fake_sdk(config, **kwargs):
        calls.append("sdk")
        return AgentResult(text="[Claude-CLI nicht gefunden]", error="CLINotFoundError")

    async def fake_direct(config, **kwargs):
        calls.append("direct")
        return AgentResult(text="direct-antwort")

    monkeypatch.setattr(sdk_bridge, "_query_sdk", fake_sdk)
    monkeypatch.setattr(sdk_bridge, "_query_direct", fake_direct)

    result = asyncio.run(
        query_os_agent(
            cfg,
            system_prompt="s",
            user_message="u",
            allowed_tools=["mcp__nextstep_fs__fs_read"],
        )
    )
    assert calls == ["sdk", "direct"]
    assert result.text == "direct-antwort"
