"""Everything the add-in reads from or asks of Fusion. Main thread only.

Accessors are guarded: several raise depending on the build, the document or
what is being edited, and an exception escaping a handler can deactivate the
add-in.
"""

from __future__ import annotations

import base64
from pathlib import Path

import adsk.core
import adsk.fusion

from .log import log
from .registry import FusionState

# Fusion ships several sizes and themes of each command icon; best first. The
# keys are black, so dark-theme artwork leads. Some newer commands ship their
# best artwork only as SVG: the "weave" set (Finish Sketch) or the theme set
# (Normal/Construction). Where nothing here suits a key, the `icon=` override
# in contexts.py picks another.
ICON_FILES = (
    "64x64-dark.png",
    "32x32-dark@2x.png",
    "32x32-weave_dark.svg",
    "32x32-dark_gray.svg",
    "64x64.png",
    "32x32@2x.png",
    "32x32.png",
)
ICON_FILE_SUFFIXES = (".png", ".svg")


def _safe(getter, default=None):
    try:
        return getter()
    except Exception:
        return default


class Fusion:
    def __init__(self, app: adsk.core.Application, icons_dir: Path):
        self._app = app
        self._ui = app.userInterface
        self._icons_dir = icons_dir
        self._icons: dict[str, str | None] = {}

    # Where the user is ------------------------------------------------------

    def state(self) -> FusionState:
        return FusionState(
            workspace=_safe(lambda: self._ui.activeWorkspace.id),
            editing_sketch=self._active_sketch() is not None,
            assembly=self._designing_assembly(),
        )

    def sketch_curve_count(self) -> int | None:
        """Curves in the sketch being edited, or None outside a sketch."""
        sketch = self._active_sketch()
        return _safe(lambda: sketch.sketchCurves.count) if sketch is not None else None

    def _active_sketch(self):
        return _safe(lambda: adsk.fusion.Sketch.cast(self._app.activeEditObject))

    def _designing_assembly(self) -> bool:
        """Whether the active design's intent is Assembly. The workspace is the same for every intent."""
        return _safe(
            lambda: adsk.fusion.Design.cast(self._app.activeProduct).designIntent
            == adsk.fusion.DesignIntentTypes.AssemblyDesignIntentType,
            False,
        )

    # Commands (the navigator's Commands interface) --------------------------

    def start(self, command: str) -> None:
        definition = self._definition(command)
        if definition is None:
            log("ERROR", f"Fusion has no command {command!r}")
            return
        definition.execute()

    def cancel(self) -> None:
        """Ends the running tool. Fusion reports it as Completed, exactly like Esc."""
        self._ui.terminateActiveCommand()

    def missing_commands(self, commands: list[str]) -> list[str]:
        return [command for command in commands if self._definition(command) is None]

    def command_name(self, command: str) -> str | None:
        return _safe(lambda: self._definition(command).name)

    def _definition(self, command: str):
        return _safe(lambda: self._ui.commandDefinitions.itemById(command))

    # Icons ------------------------------------------------------------------

    def icon(self, source: str) -> str | None:
        """A key image, base64: a .png/.svg file from icons/, or a command's own icon."""
        if source not in self._icons:
            path = self._icon_path(source)
            if path is None:
                log("WARN", f"no icon found for {source!r}")
            self._icons[source] = base64.b64encode(path.read_bytes()).decode("ascii") if path else None
        return self._icons[source]

    def icon_folder(self, command: str) -> str | None:
        """The folder of Fusion's artwork for a command, in every size and theme; None if Fusion has no such command."""
        return _safe(lambda: self._definition(command).resourceFolder) or None

    def _icon_path(self, source: str) -> Path | None:
        if source.endswith(ICON_FILE_SUFFIXES):
            path = self._icons_dir / source
            return path if path.is_file() else None
        folder = self.icon_folder(source)
        if folder is None:
            return None
        return next((Path(folder) / name for name in ICON_FILES if (Path(folder) / name).is_file()), None)
