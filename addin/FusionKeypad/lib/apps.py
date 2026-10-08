"""What apps are told (docs/app-protocol.md): the keypad definition, and the
add-in's current context.

Pure Python: Fusion's names and icon folders come through the FusionInfo interface.
"""

from __future__ import annotations

from typing import Protocol

from .registry import Context, Registry, Tool


class FusionInfo(Protocol):
    """What the definition reads from Fusion."""

    def command_name(self, command: str) -> str | None: ...

    def icon_folder(self, command: str) -> str | None: ...


def definition(registry: Registry, fusion: FusionInfo) -> dict:
    return {"type": "definition", "roots": [_context(root.context, registry, fusion) for root in registry.roots]}


def state(context: Context | None, running: str | None, registry: Registry) -> dict:
    return {"type": "state", "context": registry.path(context) if context is not None else None, "running": running}


def _context(context: Context, registry: Registry, fusion: FusionInfo) -> dict:
    return {
        "id": registry.path(context),
        "name": context.name,
        "default": context.default,
        "icons": _icons(context.icon_source, fusion),
        "items": [
            _context(item, registry, fusion) if isinstance(item, Context) else _tool(item, fusion)
            for item in context.items
        ],
    }


def _tool(tool: Tool, fusion: FusionInfo) -> dict:
    return {
        "command": tool.command,
        "label": tool.label,
        "name": fusion.command_name(tool.command),
        "icons": _icons(tool.icon_source, fusion),
    }


def _icons(source: str | None, fusion: FusionInfo) -> str | None:
    """Fusion's artwork for the key's icon. A file from icons/ isn't a command, so it has none."""
    return fusion.icon_folder(source) if source else None
