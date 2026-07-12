"""Bridge zum Claude Agent SDK / Anthropic Messages API.

Zwei Modi:

1. **Direct API** (Default): Nutzt `anthropic.AsyncAnthropic.messages.create`
   direkt. Zuverlässiger, kein CLI nötig, Streaming via SSE. Unterstützt
   Konversations-Historie (Multi-Turn).
2. **Agent SDK**: Falls MCP-Server oder Tool-Use benötigt wird UND das SDK
   verfügbar ist, wird `claude_agent_sdk.query()` verwendet. Schlägt das
   fehl (kein CLI, Fehler), fällt der Aufruf auf die Direct API zurück.
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
# Konversations-Historie
# --------------------------------------------------------------------------- #


def _build_messages(user_message: str, history: list[dict] | None) -> list[dict]:
    """Historie + aktuelle Nachricht zu API-Messages kombinieren."""
    messages = [dict(m) for m in (history or [])]
    messages.append({"role": "user", "content": user_message})
    return messages


def _history_as_text(history: list[dict] | None) -> str:
    """Historie als Klartext-Transkript (für Backends ohne Message-API)."""
    if not history:
        return ""
    lines = ["# Bisheriger Gesprächsverlauf\n"]
    for msg in history:
        role = "Nutzer" if msg.get("role") == "user" else "Agent"
        lines.append(f"**{role}:** {msg.get('content', '')}\n")
    return "\n".join(lines)


class _StreamAborted(Exception):
    """Stream brach ab, NACHDEM bereits Text an den Nutzer ging.

    Dann darf nicht still neu gestreamt werden — der Nutzer würde den
    Anfang doppelt sehen. Der Fehler wird stattdessen transparent gemeldet.
    """

    def __init__(self, original: Exception, emitted_chars: int) -> None:
        super().__init__(str(original))
        self.original = original
        self.emitted_chars = emitted_chars


# --------------------------------------------------------------------------- #
# Direct API (anthropic SDK)
# --------------------------------------------------------------------------- #


async def _query_direct(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str,
    history: list[dict] | None = None,
    max_retries: int = 3,
    stream_cb: Any = None,
) -> AgentResult:
    """Direkt über anthropic.AsyncAnthropic — kein CLI nötig."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
    messages = _build_messages(user_message, history)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            if stream_cb is not None:
                return await _query_direct_stream(
                    client, system_prompt=system_prompt,
                    messages=messages, model=model,
                    stream_cb=stream_cb,
                )
            msg = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
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
        except _StreamAborted as exc:
            # Teilweise gestreamt → kein stiller Retry (doppelter Text!)
            return AgentResult(
                text=f"\n[Stream abgebrochen: {exc.original}]",
                error=str(exc.original),
            )
        except anthropic.AuthenticationError as exc:
            return AgentResult(
                text=f"[Auth-Fehler: {exc}]", error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 — inkl. RateLimitError
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
    messages: list[dict],
    model: str,
    stream_cb: Any,
) -> AgentResult:
    """Streaming via anthropic SDK."""
    collected: list[str] = []
    emitted = 0

    try:
        async with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                collected.append(text)
                if stream_cb is not None:
                    try:
                        stream_cb(text)
                        emitted += len(text)
                    except Exception:  # noqa: BLE001
                        pass
            msg = await stream.get_final_message()
    except Exception as exc:  # noqa: BLE001
        if emitted > 0:
            raise _StreamAborted(exc, emitted) from exc
        raise

    usage = msg.usage
    text = "".join(collected).strip() or "[Kein Output]"
    return AgentResult(
        text=text,
        tokens_in=getattr(usage, "input_tokens", 0),
        tokens_out=getattr(usage, "output_tokens", 0),
        cache_read=getattr(usage, "cache_read_input_tokens", 0),
        cache_write=getattr(usage, "cache_creation_input_tokens", 0),
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
    """Über das Claude Agent SDK (nutzt CLI unter der Haube).

    Hinweis: Das SDK startet pro Aufruf eine frische Session — Historie
    wird vom Aufrufer ggf. als Text in `user_message` eingebettet.
    """
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
            # Kein CLI → als Fehler melden, damit der Aufrufer auf die
            # Direct API zurückfallen kann (nicht als DryRun tarnen).
            return AgentResult(
                text=f"[Claude-CLI nicht gefunden: {exc}]",
                error=f"CLINotFoundError: {exc}",
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
    history: list[dict] | None = None,
    mcp_servers: dict | None = None,
    allowed_tools: Sequence[str] | None = None,
    max_retries: int = 3,
    stream_cb: Any = None,
) -> AgentResult:
    """Rufe den OS-Agent auf. Wählt automatisch den besten Backend-Modus.

    - Ohne MCP/Tools → Direct API (zuverlässiger, kein CLI nötig).
    - Mit MCP/Tools → Agent SDK; bei Fehler/fehlendem CLI → Direct API.
    - Ohne API-Key → DryRun.

    `history` ist eine Liste von `{"role": "user"|"assistant", "content": str}`
    — vorherige Gesprächs-Turns für Multi-Turn-Konversationen.
    """
    model = model or config.models.os_agent

    if not config.anthropic_api_key:
        return _dry_run("ANTHROPIC_API_KEY fehlt", system_prompt, user_message, model)

    # MCP/Tools → Agent SDK (mit Fallback auf Direct API)
    if mcp_servers or allowed_tools:
        sdk_emitted = 0

        def counting_cb(delta: str) -> None:
            nonlocal sdk_emitted
            sdk_emitted += len(delta)
            if stream_cb is not None:
                stream_cb(delta)

        # SDK kennt keine Message-Historie → als Text einbetten
        sdk_message = user_message
        transcript = _history_as_text(history)
        if transcript:
            sdk_message = f"{transcript}\n---\n\n{user_message}"

        try:
            result = await _query_sdk(
                config,
                system_prompt=system_prompt,
                user_message=sdk_message,
                model=model,
                mcp_servers=mcp_servers,
                allowed_tools=allowed_tools,
                max_retries=max_retries,
                stream_cb=counting_cb if stream_cb is not None else None,
            )
            if not result.error and not result.dry_run:
                return result
            # SDK fehlgeschlagen → Fallback auf Direct API (ohne Tools).
            # Falls das SDK schon Text gestreamt hat: Trenner senden, damit
            # der Neustart für den Nutzer sichtbar ist (kein stilles Doppel).
            if sdk_emitted > 0 and stream_cb is not None:
                try:
                    stream_cb("\n\n---\n[Neustart über Direct API]\n\n")
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    # Direct API (Default)
    try:
        return await _query_direct(
            config,
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            history=history,
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
    history: list[dict] | None = None,
    mcp_servers: dict | None = None,
    allowed_tools: Sequence[str] | None = None,
) -> AsyncIterator[str]:
    """Yielde Text-Deltas. Intern nutzt es `query_os_agent` mit Callback.

    DryRun-/Fehler-Ergebnisse (die nicht streamen) werden am Ende als
    ein Block geyieldet, damit nie stumm nichts zurückkommt.
    """
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    streamed_chars = 0

    def cb(delta: str) -> None:
        nonlocal streamed_chars
        streamed_chars += len(delta)
        queue.put_nowait(delta)

    async def runner() -> AgentResult:
        try:
            return await query_os_agent(
                config,
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
                history=history,
                mcp_servers=mcp_servers,
                allowed_tools=allowed_tools,
                stream_cb=cb,
            )
        finally:
            # Sentinel IMMER enqueuen — sonst hängt der Konsument bei
            # einer Exception im Runner für immer auf queue.get().
            queue.put_nowait(None)

    task = asyncio.create_task(runner())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        result = await task
        # Nicht-streamende Ergebnisse (DryRun, Fehler) trotzdem liefern
        if streamed_chars == 0 and result.text:
            yield result.text
    finally:
        if not task.done():
            task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
