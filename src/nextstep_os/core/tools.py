"""Tool-Allowlist-Logik für Skills.

Welcher Skill darf welche Tools (MCP oder built-in) nutzen? Regel:

1. Wenn der Skill im Frontmatter ein nicht-leeres Feld ``tools: [...]`` hat,
   gilt exakt diese Liste (Override).
2. Sonst wählt `resolve_tools_for_skill` auf Basis des `ExecutionMode`:
   - **Strict:**  Nur lese-orientierte Filesystem-Tools. Keine Web-Search.
   - **Search:**  Filesystem-Tools + Web-Tools (sofern verfügbar).
3. `🟢 GRÜN`-Skills dürfen zusätzlich `fs_append` und `fs_write_new`.
4. `🔴 ROT`-Skills bekommen nur Read-Tools (Schreiben ist grundsätzlich
   blockiert – Governance entscheidet, ob überhaupt ausgeführt wird).

Die Funktion liefert zwei Werte:
    - ``allowed_tools``: Liste der Tool-Namen für ClaudeAgentOptions.
    - ``mcp_servers``:   Dict mit MCP-Servern (oder leer).

Hinweis: Wenn keine Tools benötigt werden (z.B. reiner Textoutput), kann
der Caller `allowed_tools = []` setzen, dann wird gar kein Tool-Use
zugelassen.
"""

from __future__ import annotations

from typing import Any

from ..config import Config
from .models import Ampel, ExecutionMode, Skill


# Built-in Web-Search-Tools des Anthropic-SDK (Namen folgen der SDK-Konvention)
WEB_SEARCH_TOOLS: tuple[str, ...] = ("web_search",)


# MCP-Filesystem-Tool-Namen (siehe mcp_servers.filesystem_db)
FS_READ_TOOLS: tuple[str, ...] = (
    "mcp__nextstep_fs__fs_read",
    "mcp__nextstep_fs__fs_list",
)
FS_WRITE_TOOLS: tuple[str, ...] = (
    "mcp__nextstep_fs__fs_append",
    "mcp__nextstep_fs__fs_write_new",
)


def resolve_tools_for_skill(
    config: Config,
    skill: Skill | None,
    *,
    include_filesystem: bool = True,
) -> tuple[list[str], dict[str, Any]]:
    """Berechne Tool-Allowlist + MCP-Server für einen Skill.

    Args:
        config: Zentrale Config.
        skill:  Aktiver Skill oder None (Freitext-Modus → minimales Toolset).
        include_filesystem: Ob der in-proc Filesystem-MCP-Server bereitgestellt
            werden soll. Für Freitext standardmäßig aus.
    """
    # Freitext-Modus
    if skill is None:
        return [], {}

    # Explizite Frontmatter-Override
    if skill.tools:
        mcp = _maybe_build_fs_server(config) if _needs_fs_server(skill.tools) else {}
        return list(skill.tools), mcp

    # Default: auf Basis von Ampel + ExecutionMode
    tools: list[str] = []
    if include_filesystem:
        tools.extend(FS_READ_TOOLS)
        if skill.ampel == Ampel.GRUEN:
            tools.extend(FS_WRITE_TOOLS)
        # 🟡 GELB: Review-Gate → keine automatischen Schreib-Tools
        # 🔴 ROT:  nur Read

    if skill.execution_mode == ExecutionMode.SEARCH:
        tools.extend(WEB_SEARCH_TOOLS)

    mcp = _maybe_build_fs_server(config) if include_filesystem else {}
    return tools, mcp


def _needs_fs_server(tool_names: list[str]) -> bool:
    return any(t.startswith("mcp__nextstep_fs__") for t in tool_names)


def _maybe_build_fs_server(config: Config) -> dict[str, Any]:
    """Lazy-Build: nur wenn das SDK verfügbar ist, sonst leeres Dict."""
    try:
        from mcp_servers.filesystem_db import build_filesystem_server
    except ImportError:
        return {}
    try:
        return build_filesystem_server(config)
    except RuntimeError:
        # SDK nicht verfügbar → DryRun-Modus
        return {}
