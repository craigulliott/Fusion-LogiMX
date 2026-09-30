"""Stub of adsk.core: the custom-event surface that events.py and link.py use.

As in Fusion, fireCustomEvent only queues the event; handlers run later on the
main thread. Here the "main thread" is whichever thread calls pump_until(),
which in the tests is the test itself.
"""

import queue
import time


class EventHandler:
    def __init__(self):
        pass


class CustomEventHandler(EventHandler):
    pass


class CustomEventArgs:
    def __init__(self, additional_info: str):
        self.additionalInfo = additional_info


class _Event:
    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)
        return True

    def remove(self, handler):
        self.handlers.remove(handler)
        return True


class Application:
    def __init__(self):
        self._custom: dict[str, _Event] = {}
        self._queue: queue.Queue = queue.Queue()

    def registerCustomEvent(self, event_id: str):
        if event_id in self._custom:
            raise RuntimeError(f"{event_id} is already registered")
        self._custom[event_id] = _Event()
        return self._custom[event_id]

    def unregisterCustomEvent(self, event_id: str):
        if self._custom.pop(event_id, None) is None:
            raise RuntimeError(f"{event_id} is not registered")
        return True

    def fireCustomEvent(self, event_id: str, additional_info: str = ""):
        self._queue.put((event_id, additional_info))
        return True

    # Test helpers, not Fusion API ---------------------------------------------

    def registered_events(self) -> list[str]:
        return list(self._custom)

    def pump_until(self, condition, timeout: float = 2.0) -> bool:
        """Deliver queued custom events on this thread until condition() holds."""
        deadline = time.monotonic() + timeout
        while not condition():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            try:
                event_id, info = self._queue.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue
            event = self._custom.get(event_id)
            for handler in list(event.handlers if event else []):
                handler.notify(CustomEventArgs(info))
        return True
