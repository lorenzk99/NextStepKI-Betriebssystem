"""In-Process MCP-Server für sicheren Dateizugriff auf `data/`.

Stellt Tools bereit, die der Agent (per Allowlist) nutzen darf:

- `fs_read`:      Lesen einer Datei innerhalb erlaubter Pfade
- `fs_list`:      Liste der Einträge in einem erlaubten Verzeichnis
- `fs_append`:    Anhängen an eine Datei in `data/feedback` oder `data/tasks`
- `fs_write_new`: Neue Datei anlegen (nur in Schreib-Ordnern, kein Overwrite)

Sicherheitsmodell:
- Jeder Pfad wird auf `data/` normalisiert (keine Escapes via `..`).
- Read-Pfade: `data/skills`, `data/context`, `data/governance`,
  `data/feedback`, `data/tasks`, `data/meetings`, `data/telemetry`.
- Write-Pfade (append/new): `data/feedback/entries`, `data/tasks`,
  `data/meetings/inbox`.

Der Server ist in-process (keine zusätzliche Prozess-Koordination) und
wird über `claude_agent_sdk.create_sdk_mcp_server` registriert.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nextstep_os.config import Config


# --------------------------------------------------------------------------- #
# Pfad-Guards
# --------------------------------------------------------------------------- #


def _read_roots(config: Config) -> list[Path]:
    data = config.paths.data
    return [
        data / "skills",
        data / "context",
        data / "governance",
        data / "feedback",
        data / "tasks",
        data / "meetings",
        data / "telemetry",
    ]


def _write_roots(config: Config) -> list[Path]:
    data = config.paths.data
    return [
        data / "feedback" / "entries",
        data / "tasks",
        data / "meetings" / "inbox",
    ]


def _resolve_safe(target: str, roots: list[Path]) -> Path:
    """Normalisiere `target` und prüfe, dass er unter einem Root liegt.

    Relative Pfade werden gegen ALLE Roots probiert; ein Kandidat, der
    bereits existiert, gewinnt (sonst der erste gültige). Damit findet
    `fs_read("personal/firmenprofil.md")` die Datei unter `data/context/`,
    auch wenn `data/skills/` der erste Root ist.
    """
    p = Path(target).expanduser()
    if not p.is_absolute():
        first_valid: Path | None = None
        for root in roots:
            candidate = (root / target).resolve()
            if not _is_under(candidate, roots):
                continue
            if candidate.exists():
                return candidate
            if first_valid is None:
                first_valid = candidate
        if first_valid is not None:
            return first_valid
        raise ValueError(f"Pfad `{target}` liegt außerhalb erlaubter Roots.")
    p = p.resolve()
    if not _is_under(p, roots):
        raise ValueError(f"Pfad `{target}` liegt außerhalb erlaubter Roots.")
    return p


def _is_under(path: Path, roots: list[Path]) -> bool:
    path_str = str(path)
    for root in roots:
        root_str = str(root.resolve())
        if path_str == root_str or path_str.startswith(root_str + "/"):
            return True
    return False


# --------------------------------------------------------------------------- #
# Tool-Implementierungen (konfig-gebunden)
# --------------------------------------------------------------------------- #


def build_filesystem_server(config: Config) -> Any:
    """Baue den in-process MCP-Server mit Config-bezogener Sandbox.

    Rückgabe: das Config-Objekt, das an `ClaudeAgentOptions(mcp_servers=...)`
    übergeben wird (Dict `{name: McpSdkServerConfig}`).
    """
    try:
        from claude_agent_sdk import create_sdk_mcp_server, tool
    except ImportError as exc:  # pragma: no cover - SDK optional
        raise RuntimeError(f"claude_agent_sdk nicht verfügbar: {exc}") from exc

    read_roots = _read_roots(config)
    write_roots = _write_roots(config)

    @tool(
        "fs_read",
        "Lies den Inhalt einer Datei unter data/. Pfade außerhalb werden "
        "abgelehnt. UTF-8 erwartet.",
        {"path": str},
    )
    async def fs_read(args: dict[str, Any]) -> dict[str, Any]:
        try:
            p = _resolve_safe(args["path"], read_roots)
            if not p.exists():
                return _err(f"Datei nicht gefunden: {p}")
            if p.is_dir():
                return _err(f"Pfad ist ein Verzeichnis: {p}")
            text = p.read_text(encoding="utf-8")
            return _ok(text)
        except Exception as exc:  # noqa: BLE001
            return _err(str(exc))

    @tool(
        "fs_list",
        "Liste Einträge eines Verzeichnisses unter data/ (nicht rekursiv).",
        {"path": str},
    )
    async def fs_list(args: dict[str, Any]) -> dict[str, Any]:
        try:
            p = _resolve_safe(args["path"], read_roots)
            if not p.exists() or not p.is_dir():
                return _err(f"Kein Verzeichnis: {p}")
            items = sorted(
                f"{'[DIR] ' if sub.is_dir() else ''}{sub.name}" for sub in p.iterdir()
            )
            return _ok("\n".join(items) or "(leer)")
        except Exception as exc:  # noqa: BLE001
            return _err(str(exc))

    @tool(
        "fs_append",
        "Hänge Text an eine Datei in Schreib-Ordnern an "
        "(data/feedback/entries, data/tasks, data/meetings/inbox). "
        "Erstellt die Datei, falls sie nicht existiert.",
        {"path": str, "text": str},
    )
    async def fs_append(args: dict[str, Any]) -> dict[str, Any]:
        try:
            p = _resolve_safe(args["path"], write_roots)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as fh:
                fh.write(args["text"])
            return _ok(f"{len(args['text'])} Zeichen an {p.name} angehängt.")
        except Exception as exc:  # noqa: BLE001
            return _err(str(exc))

    @tool(
        "fs_write_new",
        "Lege eine neue Datei in Schreib-Ordnern an. Überschreibt NICHT.",
        {"path": str, "text": str},
    )
    async def fs_write_new(args: dict[str, Any]) -> dict[str, Any]:
        try:
            p = _resolve_safe(args["path"], write_roots)
            if p.exists():
                return _err(f"Datei existiert bereits: {p}")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["text"], encoding="utf-8")
            return _ok(f"Datei {p} angelegt ({len(args['text'])} Zeichen).")
        except Exception as exc:  # noqa: BLE001
            return _err(str(exc))

    server = create_sdk_mcp_server(
        name="nextstep_fs",
        version="1.0.0",
        tools=[fs_read, fs_list, fs_append, fs_write_new],
    )
    return {"nextstep_fs": server}


def filesystem_tool_names() -> list[str]:
    """Kanonische Tool-Namen im MCP-Adressraum."""
    return [
        "mcp__nextstep_fs__fs_read",
        "mcp__nextstep_fs__fs_list",
        "mcp__nextstep_fs__fs_append",
        "mcp__nextstep_fs__fs_write_new",
    ]


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"ERROR: {msg}"}], "isError": True}
