"""Which context the keypad shows, and the rules that move it.

1. Where the user is in Fusion picks the top-level context. While a keyed tool
   runs, the tool's context wins until it ends.
2. A keyed tool starting, from the keypad or the mouse, shows the context that
   holds its key, on the page with the key.
3. Pressing a tool key only asks Fusion to start it; rule 2 does the rest, so
   Fusion's own events stay the single source of truth.
4. Pressing a context key opens it, and starts its default tool if it has one.
5. When the running tool draws a shape while its variants are showing, the
   keypad goes back to the page above. The tool keeps running.
6. When the running tool ends, the keypad returns to the top level. When another
   tool replaced it, rule 2 decides instead.
7. Back goes up one level. Arriving at the top level cancels the running tool.
8. More steps through the pages of a context that doesn't fit on one.

Pure Python: Fusion is reached only through the Commands interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from .registry import Context, FusionState, Registry, Tool

SLOT_COUNT = 9


class Nav(Enum):
    """Keys that move around the keypad rather than acting in Fusion."""

    BACK = "back"
    MORE = "more"


Target = Tool | Context | Nav


class Commands(Protocol):
    """What the navigator may ask of Fusion."""

    def start(self, command: str) -> None: ...

    def cancel(self) -> None: ...


class Navigator:
    def __init__(self, registry: Registry, commands: Commands):
        self._registry = registry
        self._commands = commands
        self._fusion: FusionState | None = None
        self.context: Context | None = None
        self.page = 0
        self.running: str | None = None  # the running tool's command, if it has a key

    @property
    def running_key(self) -> Tool | None:
        """The running tool's key: the one marked ▶."""
        return self._registry.key(self.running, self._fusion) if self.running is not None else None

    # What the keys are ------------------------------------------------------

    def slots(self) -> list[Target | None]:
        """What each key does, in reading order: Back first and More last when shown."""
        if self.context is None:
            return [None] * SLOT_COUNT
        pages = self._pages(self.context)
        keys: list[Target | None] = [Nav.BACK] if self._below_top(self.context) else []
        keys += pages[self.page]
        keys += [None] * (SLOT_COUNT - len(keys))
        if len(pages) > 1:
            keys[-1] = Nav.MORE
        return keys

    def _pages(self, context: Context) -> list[list[Tool | Context]]:
        room = SLOT_COUNT - (1 if self._below_top(context) else 0)
        items = list(context.items)
        if len(items) <= room:
            return [items]
        per_page = room - 1  # the last key becomes More
        return [items[start:start + per_page] for start in range(0, len(items), per_page)]

    def _below_top(self, context: Context) -> bool:
        return self._registry.parent(context) is not None

    # Fusion's side ----------------------------------------------------------

    def fusion_changed(self, fusion: FusionState) -> None:
        """Rule 1."""
        self._fusion = fusion
        if self.running is not None:
            return
        top = self._top()
        current = self._registry.root_of(self.context) if self.context else None
        if top is not current:
            self._show(top)

    def command_started(self, command: str) -> None:
        """Rule 2. Commands without a key (orbit, OK, Select, …) are ignored."""
        home = self._registry.home(command, self._fusion)
        if home is None:
            return
        self.running = command
        self._show(home, holding=command)

    def command_ended(self, command: str, replaced: bool) -> None:
        """Rule 6."""
        if command != self.running:
            return
        self.running = None
        if not replaced:
            self._show(self._top())

    def shape_drawn(self) -> None:
        """Rule 5."""
        home = self._registry.home(self.running, self._fusion) if self.running else None
        if home is not None and home.default is not None and self.context is home:
            self._show(self._registry.parent(home), holding=home)

    # The keypad's side ------------------------------------------------------

    def press(self, target: Target) -> None:
        if isinstance(target, Tool):
            self._commands.start(target.command)  # rule 3
        elif isinstance(target, Context):
            self._open(target)
        elif target is Nav.BACK:
            self._back()
        elif target is Nav.MORE and self.context is not None:
            self.page = (self.page + 1) % len(self._pages(self.context))  # rule 8

    def _open(self, context: Context) -> None:
        """Rule 4."""
        self._show(context)
        if context.default is not None:
            self._commands.start(context.default)

    def _back(self) -> None:
        """Rule 7."""
        parent = self._registry.parent(self.context) if self.context else None
        if parent is None:
            return
        self._show(parent, holding=self.context)
        if not self._below_top(parent) and self.running is not None:
            # Fusion ends the tool before cancel() returns, so rule 6 runs
            # inside this call; it shows the top level, which is already showing.
            self._commands.cancel()

    # Helpers ----------------------------------------------------------------

    def _top(self) -> Context | None:
        return self._registry.root_for(self._fusion) if self._fusion else None

    def _show(self, context: Context | None, holding: str | Context | None = None) -> None:
        """Show a context, on the page with the key for `holding` (a command or a context)."""
        self.context = context
        self.page = 0
        if context is None or holding is None:
            return
        for number, page in enumerate(self._pages(context)):
            if any(item is holding or (isinstance(item, Tool) and item.command == holding) for item in page):
                self.page = number
                return
