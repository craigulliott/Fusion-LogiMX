"""The building blocks of the keypad definition, and the lookups over it.

A Context is a page of keys. Its items are Tools (a key that starts a Fusion
command) and child Contexts (a key that opens another page). A Context with a
`default` is a tool with variants: opening it starts that command. A Root picks
the top-level context from where the user is in Fusion. Each context is known by
its path of names from its root, such as Sketch/Create/Circle.

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
    assembly: bool  # the active design's intent is Assembly (not Part or Hybrid)


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
        self._paths: dict[Context, str] = {}
        self._homes: dict[str, dict[Context, Context]] = {}  # command → {root: the context holding its key}
        for root in self.roots:
            self._add(root.context, parent=None, root=root.context)

    def _add(self, context: Context, parent: Context | None, root: Context) -> None:
        if context in self._parents:
            raise ValueError(f"context {context.name!r} is defined more than once")
        self._parents[context] = parent
        self._paths[context] = context.name if parent is None else f"{self._paths[parent]}/{context.name}"
        for item in context.items:
            if isinstance(item, Context):
                self._add(item, parent=context, root=root)
            elif root in self._homes.get(item.command, {}):
                # A command's key must have one home per root, so a running tool always has one place to show.
                raise ValueError(f"command {item.command!r} has more than one key in {root.name!r}")
            else:
                self._homes.setdefault(item.command, {})[root] = context
        if context.default is not None and self._homes.get(context.default, {}).get(root) is not context:
            raise ValueError(f"context {context.name!r} defaults to {context.default!r}, which is not one of its keys")

    def root_for(self, fusion: FusionState) -> Context | None:
        """The top-level context for where the user is, or None for a blank keypad."""
        return next((root.context for root in self.roots if root.when(fusion)), None)

    def home(self, command: str, fusion: FusionState | None = None) -> Context | None:
        """The context holding the command's key, or None if it has no key.

        A command may have a key in each root. The first root that applies to where the user is
        and has one wins; failing that, the first root that has one (a sketch tool started
        outside a sketch, say).
        """
        homes = self._homes.get(command, {})
        applying = [root.context for root in self.roots if fusion is not None and root.when(fusion)]
        return next((homes[root] for root in applying if root in homes), next(iter(homes.values()), None))

    def key(self, command: str, fusion: FusionState | None = None) -> Tool | None:
        """The command's key, in the context home() picks; None if it has no key."""
        home = self.home(command, fusion)
        items = home.items if home is not None else []
        return next((item for item in items if isinstance(item, Tool) and item.command == command), None)

    def parent(self, context: Context) -> Context | None:
        return self._parents[context]

    def path(self, context: Context) -> str:
        return self._paths[context]

    def root_of(self, context: Context) -> Context:
        while (parent := self._parents[context]) is not None:
            context = parent
        return context

    def contains(self, context: Context, command: str) -> bool:
        """Whether one of the command's keys is in this context or in any context below it."""
        for home in self._homes.get(command, {}).values():
            while home is not None:
                if home is context:
                    return True
                home = self._parents[home]
        return False

    def commands(self) -> list[str]:
        """Every command that has a key."""
        return list(self._homes)
