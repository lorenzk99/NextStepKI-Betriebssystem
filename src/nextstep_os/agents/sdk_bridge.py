"""Bridge zum Claude Agent SDK.

Kapselt den SDK-Aufruf. Falls kein API-Key gesetzt oder das SDK im
aktuellen Environment nicht funktioniert (z.B. fehlende CLI), fällt die
Bridge in einen `DryRun`-Modus, der den vollständigen Systemprompt
ausgibt, aber keinen Request feuert. So bleibt das Repository offline
testbar.
"""

from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Sequence

from ..config import Config


# --------------------------------------------------------------------------- #
# Ergebnis-Typ
# --------------------------------------------------------------------------- #


@dataclass
class AgentResult:
    """Ergebnis eines Agent-Aufrufs."""

    text: str
    dry_run: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    error: str | None = None
    raw: Any = None


# --------------------------------------------------------------------------- #
# Helper: Text aus SDK-Events extrahieren
# --------------------------------------------------------------------------- #


def _extract_text(event: Any) -> str:
    """Tolerant gegenüber verschiedenen Event-Shapes des SDK."""
    if event is None:
        return ""
    if isinstance(event, str):
        return event
    # claude-agent-sdk AssistantMessage hat .content: list[ContentBlock]
    content = getattr(event, "content", None)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        if parts:
            return "".join(parts)
    # Direkte .text-Felder (StreamEvent etc.)
    text = getattr(event, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(event, dict):
        if isinstance(event.get("text"), str):
            return event["text"]
        delta = event.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            return delta["text"]
    return ""


def _extract_usage(event: Any) -> tuple[int, int, int, int]:
    """ResultMessage → (in, out, cache_read, cache_write)."""
    usage = getattr(event, "usage", None) or (
        event.get("usage") if isinstance(event, dict) else None
    )
    if not usage:
        return 0, 0, 0, 0
    if hasattr(usage, "__dict__"):
        data = usage.__dict__
    elif isinstance(usage, dict):
        data = usage
    else:
        return 0, 0, 0, 0
    return (
        int(data.get("input_tokens", 0) or 0),
        int(data.get("output_tokens", 0) or 0),
        int(data.get("cache_read_input_tokens", 0) or 0),
        int(data.get("cache_creation_input_tokens", 0) or 0),
    )


# --------------------------------------------------------------------------- #
# DryRun-Fallback
# --------------------------------------------------------------------------- #


def _dry_run(reason: str, system_prompt: str, user_message: str, model: str) -> AgentResult:
    preview = system_prompt[:1200]
    if len(system_prompt) > 1200:
        preview += "\n…\n[truncated]"
    text = (
        f"[DryRun – {reason}]\n\n"
        f"Modell: {model}\n\n"
        f"User-Message:\n{user_message}\n\n"
        f"System-Prompt (gekürzt):\n{preview}"
    )
    return AgentResult(text=text, dry_run=True)


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


async def query_os_agent(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    mcp_servers: dict | None = None,
    allowed_tools: Sequence[str] | None = None,
    max_retries: int = 3,
    stream_cb: Any = None,
) -> AgentResult:
    """Rufe den OS-Agent über das Claude Agent SDK auf.

    Args:
        stream_cb: optionaler Callback `(delta: str) -> None` für Streaming.
        max_retries: Retries bei transienten Fehlern (Rate-Limit, Netzwerk).
    """
    model = model or config.models.os_agent

    if not config.anthropic_api_key:
        return _dry_run("ANTHROPIC_API_KEY fehlt", system_prompt, user_message, model)

    try:  # pragma: no cover - SDK optional
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            CLINotFoundError,
            RateLimitEvent,
            ResultMessage,
            query,
        )
    except Exception as exc:  # noqa: BLE001
        return _dry_run(f"claude_agent_sdk nicht verfügbar: {exc}", system_prompt, user_message, model)

    kwargs: dict[str, Any] = {"system_prompt": system_prompt, "model": model}
    if mcp_servers:
        kwargs["mcp_servers"] = mcp_servers
    if allowed_tools:
        kwargs["allowed_tools"] = list(allowed_tools)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            options = ClaudeAgentOptions(**kwargs)
            collected: list[str] = []
            tin = tout = cread = cwrite = 0
            async for event in query(prompt=user_message, options=options):
                if isinstance(event, AssistantMessage):
                    text = _extract_text(event)
                    if text:
                        collected.append(text)
                        if stream_cb is not None:
                            try:
                                stream_cb(text)
                            except Exception:  # noqa: BLE001
                                pass
                elif isinstance(event, ResultMessage):
                    tin, tout, cread, cwrite = _extract_usage(event)
                elif isinstance(event, RateLimitEvent):
                    last_error = RuntimeError("Rate-Limit erreicht")
                    raise last_error
            text = "".join(collected).strip() or "[Kein Output]"
            return AgentResult(
                text=text,
                tokens_in=tin,
                tokens_out=tout,
                cache_read=cread,
                cache_write=cwrite,
            )
        except CLINotFoundError as exc:
            return _dry_run(f"Claude-CLI nicht gefunden: {exc}", system_prompt, user_message, model)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            # Exponential backoff mit Jitter
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)

    return AgentResult(
        text=f"[Fehler nach {max_retries} Versuchen: {last_error}]",
        error=str(last_error),
    )


# --------------------------------------------------------------------------- #
# Streaming (dünner Wrapper)
# --------------------------------------------------------------------------- #


async def stream_os_agent(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    mcp_servers: dict | None = None,
    allowed_tools: Sequence[str] | None = None,
) -> AsyncIterator[str]:
    """Yielde Text-Deltas. Intern nutzt es `query_os_agent` mit Callback."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def cb(delta: str) -> None:
        queue.put_nowait(delta)

    async def runner() -> AgentResult:
        result = await query_os_agent(
            config,
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
            stream_cb=cb,
        )
        queue.put_nowait(None)
        return result

    task = asyncio.create_task(runner())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        await task
