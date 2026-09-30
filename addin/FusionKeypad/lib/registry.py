"""The building blocks of the keypad definition, and the lookups over it.

A Context is a page of keys. Its items are Tools (a key that starts a Fusion
command) and child Contexts (a key that opens another page). A Context with a
`default` is a tool with variants: opening it starts that command. A Root picks
the top-level context from where the user is in Fusion.

Pure Python: nothing here touches the Fusion API.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class FusionState:
    """Where the user is in Fusion, as far as choosing a root is concerned."""

    workspace: str | None
    editing_sketch: bool


@dataclass(frozen=True)
class Tool:
    """A key that starts a Fusion command.

    `icon` overrides the command's own icon: another command's id, or the name
    of a .png/.svg file in FusionKeypad/icons/.
    """

    command: str
    label: str
    icon: str | None = None

    @property
    def icon_source(self) -> str:
        return self.icon or self.command


@dataclass(eq=False)  # compared by identity: each context is defined once
class Context:
    """A page of keys. `icon` works as on Tool and defaults to the default command's icon."""

    name: str
    items: Sequence[Tool | Context]
    default: str | None = None
    icon: str | None = None

    @property
    def icon_source(self) -> str | None:
        return self.icon or self.default


@dataclass(frozen=True)
class Root:
    """A top-level context, shown while `when` holds for where the user is."""

    context: Context
    when: Callable[[FusionState], bool]


class Registry:
    """Lookups over the keypad definition, which is checked once when built."""

    def __init__(self, roots: Sequence[Root]):
        self.roots = list(roots)
        self._parents: dict[Context, Context | None] = {}
        self._homes: dict[str, Context] = {}
        self._names: set[str] = set()
        for root in self.roots:
            self._add(root.context, parent=None)

    def _add(self, context: Context, parent: Context | None) -> None:
        if context in self._parents or context.name in self._names:
            raise ValueError(f"context {context.name!r} is defined more than once")
        self._parents[context] = parent
        self._names.add(context.name)
        for item in context.items:
            if isinstance(item, Context):
                self._add(item, parent=context)
            elif item.command in self._homes:
                # A command's key must have one home, so a running tool always has one place to show.
                raise ValueError(f"command {item.command!r} has more than one key")
            else:
                self._homes[item.command] = context
        if context.default is not None and self._homes.get(context.default) is not context:
            raise ValueError(f"context {context.name!r} defaults to {context.default!r}, which is not one of its keys")

    def root_for(self, fusion: FusionState) -> Context | None:
        """The top-level context for where the user is, or None for a blank keypad."""
        return next((root.context for root in self.roots if root.when(fusion)), None)

    def home(self, command: str) -> Context | None:
        """The context holding the command's key, or None if it has no key."""
        return self._homes.get(command)

    def parent(self, context: Context) -> Context | None:
        return self._parents[context]

    def root_of(self, context: Context) -> Context:
        while (parent := self._parents[context]) is not None:
            context = parent
        return context

    def contains(self, context: Context, command: str) -> bool:
        """Whether the command's key is in this context or in any context below it."""
        home = self._homes.get(command)
        while home is not None:
            if home is context:
                return True
            home = self._parents[home]
        return False

    def commands(self) -> list[str]:
        """Every command that has a key."""
        return list(self._homes)
