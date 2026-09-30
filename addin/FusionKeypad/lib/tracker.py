"""Turns Fusion's events into navigator calls.

Fusion fires commandStarting/commandTerminated for every command, with a key or
without, but nothing while a running sketch tool adds geometry. For that, a
worker thread polls the sketch's curve count while a keyed tool runs. The worker
only fires a custom event, because the API may only be used on the main thread,
and it skips a tick while the previous one is still waiting, so a busy main
thread never builds up a queue of them.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

import adsk.core

from . import events
from .fusion import Fusion
from .log import log
from .navigator import Navigator
from .registry import Registry

POLL_EVENT_ID = "FusionKeypad.poll"
POLL_INTERVAL_S = 0.25


class Tracker:
    def __init__(
        self,
        app: adsk.core.Application,
        fusion: Fusion,
        navigator: Navigator,
        registry: Registry,
        on_change: Callable[[], None],
    ):
        self._app = app
        self._fusion = fusion
        self._navigator = navigator
        self._registry = registry
        self._on_change = on_change
        self._curves: int | None = None  # the sketch's curve count at the last look
        self._unkeyed_logged: set[str] = set()
        self._polling = threading.Event()  # set while a keyed tool runs
        self._in_flight = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        ui = self._app.userInterface
        command_handler = adsk.core.ApplicationCommandEventHandler
        events.subscribe(ui.commandStarting, command_handler, self._on_command_starting, "commandStarting")
        events.subscribe(ui.commandTerminated, command_handler, self._on_command_terminated, "commandTerminated")
        events.subscribe(self._app.documentActivated, adsk.core.DocumentEventHandler, self._on_moved, "documentActivated")
        events.subscribe(ui.workspaceActivated, adsk.core.WorkspaceEventHandler, self._on_moved, "workspaceActivated")
        if events.register_custom_event(self._app, POLL_EVENT_ID, self._on_poll, "poll") is not None:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        try:
            self._app.unregisterCustomEvent(POLL_EVENT_ID)
        except Exception:
            pass

    # Fusion events (main thread) --------------------------------------------

    def _on_command_starting(self, args) -> None:
        command = args.commandId
        if self._registry.home(command) is None:
            self._log_unkeyed(command)
            return
        self._navigator.command_started(command)
        self._curves = self._fusion.sketch_curve_count()
        self._changed()

    def _on_command_terminated(self, args) -> None:
        replaced = args.terminationReason == adsk.core.CommandTerminationReason.PreEmptedTerminationReason
        self._navigator.command_ended(args.commandId, replaced)
        self._navigator.fusion_changed(self._fusion.state())  # finishing a sketch changes where the user is
        self._changed()

    def _on_moved(self, args) -> None:
        self._navigator.fusion_changed(self._fusion.state())
        self._changed()

    def _on_poll(self, args) -> None:
        try:
            curves = self._fusion.sketch_curve_count()
            if curves is not None and self._curves is not None and curves > self._curves:
                self._navigator.shape_drawn()
            self._curves = curves
            self._changed()
        finally:
            self._in_flight.clear()  # in a finally so a raising tick can't stop the poll for good

    def _changed(self) -> None:
        if self._navigator.running is not None:
            self._polling.set()
        else:
            self._polling.clear()
        self._on_change()

    def _log_unkeyed(self, command: str) -> None:
        """Log each command without a key once: this is how to find the id for a new Tool."""
        if command in self._unkeyed_logged:
            return
        self._unkeyed_logged.add(command)
        name = self._fusion.command_name(command)
        log("INFO", f"no key for {command} ({name}); add Tool({command!r}, ...) to contexts.py to give it one")

    # Worker thread ----------------------------------------------------------

    def _poll_loop(self) -> None:
        # wait() is both the sleep and the check for stop().
        while not self._stop.wait(POLL_INTERVAL_S):
            if not self._polling.is_set() or self._in_flight.is_set():
                continue  # nothing to watch, or the main thread is still busy: skip rather than queue
            self._in_flight.set()
            try:
                self._app.fireCustomEvent(POLL_EVENT_ID)
            except Exception:
                self._in_flight.clear()
                return
