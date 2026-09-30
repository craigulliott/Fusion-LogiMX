"""GC-safe event subscriptions.

If a Python handler object is garbage-collected while Fusion still holds it,
Fusion crashes silently on the next callback. Every handler is therefore kept
in _subscriptions until unsubscribe_all(), and nothing attaches a handler any
other way.
"""

import traceback

import adsk.core

from .log import log

_subscriptions: list[tuple[object, object]] = []


def subscribe(event, handler_base, callback, label: str):
    """Attach callback(args) to a Fusion event; exceptions are logged, never raised."""

    class _Handler(handler_base):
        def __init__(self):
            super().__init__()

        def notify(self, args):
            try:
                callback(args)
            except Exception:
                detail = " | ".join(traceback.format_exc().strip().splitlines()[-3:])
                log("ERROR", f"{label}: {detail}")

    handler = _Handler()
    event.add(handler)
    _subscriptions.append((event, handler))
    return handler


def register_custom_event(app: adsk.core.Application, event_id: str, callback, label: str):
    """Register a custom event and subscribe callback(args). Returns the event or None."""
    try:
        # A registration left behind by a crashed or force-stopped add-in makes
        # the next registerCustomEvent fail.
        app.unregisterCustomEvent(event_id)
    except Exception:
        pass
    try:
        event = app.registerCustomEvent(event_id)
    except Exception:
        event = None
    if event is None:
        log("ERROR", f"could not register custom event {event_id}")
        return None
    subscribe(event, adsk.core.CustomEventHandler, callback, label)
    return event


def unsubscribe_all() -> None:
    for event, handler in _subscriptions:
        try:
            event.remove(handler)
        except Exception:
            pass
    _subscriptions.clear()
