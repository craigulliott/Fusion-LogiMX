"""Starts and stops the add-in, and connects its parts:

    Fusion events ──▶ Tracker ──▶ Navigator ◀── key presses ◀── keypad Link ◀── plugin
                                      │
                                      ├──▶ layout.faces ──────▶ keypad Link ──▶ plugin
                                      └──▶ menu.choices ──────▶ mcp Link ─────▶ MCP server
    Fusion tools ◀──────────────────────────── run ◀─────────── mcp Link ◀───── MCP server
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import adsk.core

from . import contexts, events, layout, menu
from .fusion import Fusion
from .link import KEYPAD_PORT, MCP_PORT, Link
from .log import LOG_PATH, log
from .navigator import Navigator, Target
from .registry import Registry
from .tracker import Tracker

_addin: AddIn | None = None


def start(addin_dir: str) -> None:
    global _addin
    _addin = AddIn(adsk.core.Application.get(), Path(addin_dir))
    _addin.start()


def stop() -> None:
    global _addin
    if _addin is not None:
        _addin.stop()
    _addin = None


class AddIn:
    def __init__(self, app: adsk.core.Application, addin_dir: Path):
        self._app = app
        self._registry = Registry(contexts.ROOTS)
        self._fusion = Fusion(app, addin_dir / "icons")
        # Fusion's name for each command with a key; None where this Fusion build lacks the command.
        self._names = {command: self._fusion.command_name(command) for command in self._registry.commands()}
        self._navigator = Navigator(self._registry, self._fusion)
        self._tracker = Tracker(app, self._fusion, self._navigator, self._registry, self._refresh)
        self._keypad_link = Link(app, "keypad", KEYPAD_PORT, self._on_keypad_message)
        self._mcp_link = Link(app, "mcp", MCP_PORT, self._on_mcp_message)
        self._slots: list[Target | None] = []  # what each key does, as last published
        self._layout = 0  # changes whenever _slots does (docs/protocol.md)

    def start(self) -> None:
        log("START", f"Fusion {self._app.version}, Python {sys.version.split()[0]}, log {LOG_PATH}")
        for command, name in self._names.items():
            if name is None:
                log("WARN", f"contexts.py has a key for {command!r}, which this Fusion build doesn't have")
        self._navigator.fusion_changed(self._fusion.state())
        self._refresh()
        self._tracker.start()
        self._keypad_link.start()
        self._mcp_link.start()

    def stop(self) -> None:
        self._keypad_link.stop()
        self._mcp_link.stop()
        self._tracker.stop()
        events.unsubscribe_all()
        log("STOP")

    # Main thread --------------------------------------------------------------

    def _on_keypad_message(self, message: dict) -> None:
        if message.get("type") == "press":
            self._on_press(message.get("slot"), message.get("layout"))

    def _on_press(self, slot, layout_number) -> None:
        if layout_number != self._layout or slot not in range(len(self._slots)):
            log("INFO", f"ignored a press of key {slot} on layout {layout_number}; layout {self._layout} is showing")
            return
        target = self._slots[slot]
        if target is not None:
            self._navigator.press(target)
            self._refresh()

    def _on_mcp_message(self, message: dict) -> None:
        """Only asks Fusion to start a keyed command; its events move the add-in, as for a key press."""
        command = message.get("command")
        if message.get("type") != "run" or self._registry.home(command) is None:
            log("INFO", f"ignored an MCP server message that runs no keyed command: {str(message)[:80]}")
            return
        self._fusion.start(command)

    def _refresh(self) -> None:
        """Publish what the keys show and where the user is; the links skip whatever hasn't changed."""
        slots = self._navigator.slots()
        if slots != self._slots:
            self._slots = slots
            self._layout += 1
        self._keypad_link.publish(self._keys())
        self._mcp_link.publish(self._state())

    def _keys(self) -> dict:
        """The keypad plugin's message (docs/protocol.md)."""
        faces = layout.faces(self._slots, self._navigator.running, self._registry, self._fusion.icon)
        return {"type": "keys", "layout": self._layout, "keys": [asdict(face) for face in faces]}

    def _state(self) -> dict:
        """The MCP server's message (docs/protocol.md)."""
        context, key = self._navigator.context, self._navigator.running_key
        return {
            "type": "state",
            "context": self._registry.path(context) if context is not None else None,
            "running": self._navigator.running,
            "icon": self._fusion.icons(key.icon_source) if key is not None else None,
            "choices": [asdict(choice) for choice in menu.choices(context, self._registry, self._names)],
        }
