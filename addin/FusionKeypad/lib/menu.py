"""The commands the MCP server offers by name (docs/protocol.md): every command
in the current root, nearest the current context first.

Pure Python: Fusion's names for commands come from a mapping the caller passes in.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from .registry import Context, Registry, Tool


@dataclass(frozen=True)
class Choice:
    name: str  # Fusion's name for the command, or a page's own name for its default
    command: str


def choices(context: Context | None, registry: Registry, names: Mapping[str, str | None]) -> list[Choice]:
    """From the context up to its root, each level adds its commands in keypad order.

    A name stays with the nearest command that has it. `names` holds Fusion's
    name for each command, or None where this Fusion build lacks it.
    """
    chosen: dict[str, str] = {}  # name → command
    while context is not None:
        for name, command in _named(context, names):
            chosen.setdefault(name, command)
        context = registry.parent(context)
    return [Choice(name, command) for name, command in chosen.items()]


def _named(context: Context, names: Mapping[str, str | None]) -> Iterator[tuple[str, str]]:
    """The context's commands in keypad order, each key by Fusion's name and each page with a default by its own.

    Commands this Fusion build lacks are left out.
    """
    for item in context.items:
        if isinstance(item, Tool):
            if (name := names.get(item.command)) is not None:
                yield name, item.command
            continue
        if item.default is not None and names.get(item.default) is not None:
            yield item.name, item.default
        yield from _named(item, names)
