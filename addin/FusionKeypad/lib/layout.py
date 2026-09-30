"""What each physical key shows, from what the navigator says each key does.

Pure Python: icons come from a lookup the caller passes in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .navigator import Nav, Target
from .registry import Registry, Tool

BACK_LABEL = "‹ Back"
MORE_LABEL = "More ›"
RUNNING_MARK = "▶ "  # the running tool, and the context keys leading to it
OPENS_MARK = " ›"  # a key that opens another page


@dataclass(frozen=True)
class Face:
    label: str
    image: str | None  # base64 PNG or SVG; None for a text-only key


BLANK = Face("", None)

IconLookup = Callable[[str], str | None]


def faces(slots: list[Target | None], running: str | None, registry: Registry, icon: IconLookup) -> list[Face]:
    return [_face(target, running, registry, icon) for target in slots]


def _face(target: Target | None, running: str | None, registry: Registry, icon: IconLookup) -> Face:
    if target is None:
        return BLANK
    if target is Nav.BACK:
        return Face(BACK_LABEL, None)
    if target is Nav.MORE:
        return Face(MORE_LABEL, None)
    if isinstance(target, Tool):
        mark = RUNNING_MARK if target.command == running else ""
        return Face(mark + target.label, icon(target.icon_source))
    mark = RUNNING_MARK if running is not None and registry.contains(target, running) else ""
    return Face(mark + target.name + OPENS_MARK, icon(target.icon_source) if target.icon_source else None)
