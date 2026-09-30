"""Starts and stops the add-in, and connects its parts:

    Fusion events ──▶ Tracker ──▶ Navigator ◀── key presses ◀── Link ◀── plugin
                                      │
                                      └──▶ layout.faces ──▶ Link ──▶ plugin
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import adsk.core

from . import contexts, events, layout
from .fusion import Fusion
from .link import CONNECTED, HOST, PORT, Link
from .log import LOG_PATH, log
from .navigator import Navigator, Target
from .registry import Registry
from .tracker import Tracker

_keypad: Keypad | None = None


def start(addin_dir: str) -> None:
    global _keypad
    _keypad = Keypad(adsk.core.Application.get(), Path(addin_dir))
    _keypad.start()


def stop() -> None:
    global _keypad
    if _keypad is not None:
        _keypad.stop()
    _keypad = None


class Keypad:
    def __init__(self, app: adsk.core.Application, addin_dir: Path):
        self._app = app
        self._registry = Registry(contexts.ROOTS)
        self._fusion = Fusion(app, addin_dir / "icons")
        self._navigator = Navigator(self._registry, self._fusion)
        self._tracker = Tracker(app, self._fusion, self._navigator, self._registry, self._refresh)
        self._link = Link(app, self._on_message)
        self._slots: list[Target | None] = []  # what each key does, as last sent
        self._faces: list[layout.Face] = []  # what each key shows, as last sent
        self._layout = 0  # changes whenever _slots does (docs/protocol.md)

    def start(self) -> None:
        log("START", f"Fusion {self._app.version}, Python {sys.version.split()[0]}, log {LOG_PATH}")
        for command in self._fusion.missing_commands(self._registry.commands()):
            log("WARN", f"contexts.py has a key for {command!r}, which this Fusion build doesn't have")
        self._navigator.fusion_changed(self._fusion.state())
        self._refresh()
        self._tracker.start()
        if self._link.start():
            log("READY", f"waiting for the plugin on {HOST}:{PORT}")

    def stop(self) -> None:
        self._link.stop()
        self._tracker.stop()
        events.unsubscribe_all()
        log("STOP")

    # Main thread --------------------------------------------------------------

    def _on_message(self, message: dict) -> None:
        if message == CONNECTED:
            self._send()
        elif message.get("type") == "press":
            self._on_press(message.get("slot"), message.get("layout"))

    def _on_press(self, slot, layout_number) -> None:
        if layout_number != self._layout or slot not in range(len(self._slots)):
            log("INFO", f"ignored a press of key {slot} on layout {layout_number}; layout {self._layout} is showing")
            return
        target = self._slots[slot]
        if target is not None:
            self._navigator.press(target)
            self._refresh()

    def _refresh(self) -> None:
        """Send the keys if anything about them changed."""
        slots = self._navigator.slots()
        faces = layout.faces(slots, self._navigator.running, self._registry, self._fusion.icon)
        if slots == self._slots and faces == self._faces:
            return
        if slots != self._slots:
            self._layout += 1
        self._slots, self._faces = slots, faces
        self._send()

    def _send(self) -> None:
        self._link.send({"type": "keys", "layout": self._layout, "keys": [asdict(face) for face in self._faces]})
