"""Bridge zum Claude Agent SDK.

Kapselt den SDK-Aufruf. Falls das SDK nicht installiert oder kein
API-Key gesetzt ist, fällt die Bridge in einen ``DryRun``-Modus, der
den vollständigen Systemprompt ausgibt, aber keinen Request feuert.
So bleibt das Repository offline testbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

from ..config import Config


@dataclass
class AgentResult:
    """Ergebnis eines Agent-Aufrufs."""

    text: str
    dry_run: bool = False
    raw: Any = None


async def query_os_agent(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    stream: bool = False,
) -> AgentResult:
    """Rufe den OS-Agent über das Claude Agent SDK auf.

    Wenn das SDK nicht verfügbar ist, liefere einen DryRun-AgentResult.
    """
    model = model or config.models.os_agent

    if not config.anthropic_api_key:
        return AgentResult(
            text=(
                "[DryRun – ANTHROPIC_API_KEY fehlt]\n\n"
                f"Modell: {model}\n\n"
                f"User-Message:\n{user_message}\n\n"
                "System-Prompt (gekürzt):\n"
                + system_prompt[:1200]
                + ("\n…\n[truncated]" if len(system_prompt) > 1200 else "")
            ),
            dry_run=True,
        )

    try:  # pragma: no cover - SDK optional
        from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return AgentResult(
            text=f"[DryRun – claude_agent_sdk nicht verfügbar: {exc}]",
            dry_run=True,
        )

    try:
        options = ClaudeAgentOptions(system_prompt=system_prompt, model=model)
    except TypeError:
        # Fallback falls Signatur abweicht
        options = ClaudeAgentOptions()  # type: ignore[call-arg]

    collected: list[str] = []
    async for event in query(prompt=user_message, options=options):  # pragma: no cover
        text = _extract_text(event)
        if text:
            collected.append(text)
    return AgentResult(text="".join(collected).strip() or "[Kein Output]", raw=None)


async def stream_os_agent(
    config: Config,
    *,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Stream-Variante: yielded Text-Deltas."""
    result = await query_os_agent(
        config,
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
    )
    yield result.text


def _extract_text(event: Any) -> str:
    """Tolerant gegenüber verschiedenen Event-Shapes des SDK."""
    if event is None:
        return ""
    if isinstance(event, str):
        return event
    text = getattr(event, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(event, "content", None)
    if isinstance(content, list):
        parts = []
        for item in content:
            t = getattr(item, "text", None) or (
                item.get("text") if isinstance(item, dict) else None
            )
            if t:
                parts.append(t)
        return "".join(parts)
    if isinstance(event, dict):
        if "text" in event and isinstance(event["text"], str):
            return event["text"]
        if "delta" in event and isinstance(event["delta"], dict):
            return event["delta"].get("text", "")
    return ""
