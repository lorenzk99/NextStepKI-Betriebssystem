"""Bridge zum Claude Agent SDK / Anthropic Messages API.

Zwei Modi:

1. **Direct API** (Default): Nutzt `anthropic.AsyncAnthropic.messages.create`
   direkt. Zuverlässiger, kein CLI nötig, Streaming via SSE.
2. **Agent SDK**: Falls MCP-Server oder Tool-Use benötigt wird UND das SDK
   verfügbar ist, wird `claude_agent_sdk.query()` verwendet.
3. **DryRun**: Falls kein API-Key gesetzt oder beide Backends fehlen.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
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
# Direct API (anthropic SDK)
# --------------------------------------------------------------------------- #


async def _query_direct(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str,
    max_retries: int = 3,
    stream_cb: Any = None,
) -> AgentResult:
    """Direkt über anthropic.AsyncAnthropic — kein CLI nötig."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            if stream_cb is not None:
                return await _query_direct_stream(
                    client, system_prompt=system_prompt,
                    user_message=user_message, model=model,
                    stream_cb=stream_cb,
                )
            msg = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            text_parts = [
                block.text for block in msg.content
                if hasattr(block, "text")
            ]
            text = "".join(text_parts).strip() or "[Kein Output]"
            usage = msg.usage
            return AgentResult(
                text=text,
                tokens_in=getattr(usage, "input_tokens", 0),
                tokens_out=getattr(usage, "output_tokens", 0),
                cache_read=getattr(usage, "cache_read_input_tokens", 0),
                cache_write=getattr(usage, "cache_creation_input_tokens", 0),
            )
        except anthropic.RateLimitError as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)
        except anthropic.AuthenticationError as exc:
            return AgentResult(
                text=f"[Auth-Fehler: {exc}]", error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)

    return AgentResult(
        text=f"[Fehler nach {max_retries} Versuchen: {last_error}]",
        error=str(last_error),
    )


async def _query_direct_stream(
    client: Any,
    *,
    system_prompt: str,
    user_message: str,
    model: str,
    stream_cb: Any,
) -> AgentResult:
    """Streaming via anthropic SDK."""
    collected: list[str] = []
    tin = tout = cread = cwrite = 0

    async with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            collected.append(text)
            if stream_cb is not None:
                try:
                    stream_cb(text)
                except Exception:  # noqa: BLE001
                    pass

    msg = await stream.get_final_message()
    usage = msg.usage
    tin = getattr(usage, "input_tokens", 0)
    tout = getattr(usage, "output_tokens", 0)
    cread = getattr(usage, "cache_read_input_tokens", 0)
    cwrite = getattr(usage, "cache_creation_input_tokens", 0)

    text = "".join(collected).strip() or "[Kein Output]"
    return AgentResult(
        text=text,
        tokens_in=tin,
        tokens_out=tout,
        cache_read=cread,
        cache_write=cwrite,
    )


# --------------------------------------------------------------------------- #
# Agent SDK (für MCP/Tool-Use)
# --------------------------------------------------------------------------- #


async def _query_sdk(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str,
    mcp_servers: dict | None = None,
    allowed_tools: Sequence[str] | None = None,
    max_retries: int = 3,
    stream_cb: Any = None,
) -> AgentResult:
    """Über das Claude Agent SDK (nutzt CLI unter der Haube)."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        CLINotFoundError,
        RateLimitEvent,
        ResultMessage,
        query,
    )

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
                    text = _extract_text_sdk(event)
                    if text:
                        collected.append(text)
                        if stream_cb is not None:
                            try:
                                stream_cb(text)
                            except Exception:  # noqa: BLE001
                                pass
                elif isinstance(event, ResultMessage):
                    tin, tout, cread, cwrite = _extract_usage_sdk(event)
                elif isinstance(event, RateLimitEvent):
                    last_error = RuntimeError("Rate-Limit erreicht (SDK)")
                    raise last_error
            text = "".join(collected).strip() or "[Kein Output]"
            return AgentResult(
                text=text,
                tokens_in=tin, tokens_out=tout,
                cache_read=cread, cache_write=cwrite,
            )
        except CLINotFoundError as exc:
            return _dry_run(
                f"Claude-CLI nicht gefunden: {exc}",
                system_prompt, user_message, model,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)

    return AgentResult(
        text=f"[SDK-Fehler nach {max_retries} Versuchen: {last_error}]",
        error=str(last_error),
    )


def _extract_text_sdk(event: Any) -> str:
    content = getattr(event, "content", None)
    if isinstance(content, list):
        parts = []
        for block in content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        if parts:
            return "".join(parts)
    text = getattr(event, "text", None)
    return text if isinstance(text, str) else ""


def _extract_usage_sdk(event: Any) -> tuple[int, int, int, int]:
    usage = getattr(event, "usage", None)
    if not usage:
        return 0, 0, 0, 0
    data = usage.__dict__ if hasattr(usage, "__dict__") else {}
    return (
        int(data.get("input_tokens", 0) or 0),
        int(data.get("output_tokens", 0) or 0),
        int(data.get("cache_read_input_tokens", 0) or 0),
        int(data.get("cache_creation_input_tokens", 0) or 0),
    )


# --------------------------------------------------------------------------- #
# Haupt-Entry-Point
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
    """Rufe den OS-Agent auf. Wählt automatisch den besten Backend-Modus.

    - Ohne MCP/Tools → Direct API (zuverlässiger, kein CLI nötig).
    - Mit MCP/Tools → Agent SDK (braucht CLI).
    - Ohne API-Key → DryRun.
    """
    model = model or config.models.os_agent

    if not config.anthropic_api_key:
        return _dry_run("ANTHROPIC_API_KEY fehlt", system_prompt, user_message, model)

    # MCP/Tools → Agent SDK (mit Fallback auf Direct API)
    if mcp_servers or allowed_tools:
        try:
            result = await _query_sdk(
                config,
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
                mcp_servers=mcp_servers,
                allowed_tools=allowed_tools,
                max_retries=max_retries,
                stream_cb=stream_cb,
            )
            if not result.error:
                return result
            # SDK fehlgeschlagen → Fallback auf Direct API (ohne Tools)
        except Exception:  # noqa: BLE001
            pass

    # Direct API (Default)
    try:
        return await _query_direct(
            config,
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            max_retries=max_retries,
            stream_cb=stream_cb,
        )
    except ImportError:
        return _dry_run(
            "anthropic SDK nicht installiert",
            system_prompt, user_message, model,
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
