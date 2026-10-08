"""Localhost connections: one Link for the keypad plugin (docs/keypad-protocol.md)
and one for apps (docs/app-protocol.md).

A Link keeps the latest message of each type it publishes and sends it to every
client connected to its port, and to each client that connects later. A worker
thread owns the sockets and never touches the Fusion API: each message from a
client crosses to the main thread as a custom event. Publishing happens on the
main thread.
"""

from __future__ import annotations

import json
import selectors
import socket
import threading
from collections.abc import Callable

import adsk.core

from . import events
from .log import log

HOST = "127.0.0.1"
KEYPAD_PORT = 47823
APP_PORT = 47824
SEND_TIMEOUT_S = 1.0


class Link:
    def __init__(self, app: adsk.core.Application, name: str, port: int, on_message: Callable[[dict], None]):
        self._app = app
        self._name = name  # names the custom event and the log lines
        self._port = port
        self._event_id = f"FusionKeypad.{name}"
        self._on_message = on_message  # runs on the main thread
        self._lock = threading.Lock()  # guards _clients and _latest, and keeps each line whole
        self._clients: set[socket.socket] = set()
        self._latest: dict[str, bytes] = {}  # message type → the line last published
        self._listener: socket.socket | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if events.register_custom_event(self._app, self._event_id, self._on_event, f"{self._name} message") is None:
            return
        try:
            self._listener = socket.create_server((HOST, self._port))
        except OSError as error:
            log("ERROR", f"cannot listen on {HOST}:{self._port}: {error}")
            return
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        log("READY", f"waiting for {self._name} clients on {HOST}:{self._port}")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            for client in self._clients:
                client.close()
            self._clients.clear()
        if self._listener is not None:
            self._listener.close()
        try:
            self._app.unregisterCustomEvent(self._event_id)
        except Exception:
            pass

    def publish(self, message: dict) -> None:
        """Send a message to every client, now and on connecting, unless it repeats the latest of its type.

        Main thread.
        """
        line = (json.dumps(message) + "\n").encode("utf-8")
        with self._lock:
            if self._latest.get(message["type"]) == line:
                return
            self._latest[message["type"]] = line
            for client in self._clients:
                self._send(client, line)

    def _send(self, client: socket.socket, line: bytes) -> None:
        """The caller holds the lock."""
        try:
            client.sendall(line)
        except OSError as error:
            log("WARN", f"sending to a {self._name} client failed ({error}); dropping the connection")
            try:
                client.shutdown(socket.SHUT_RDWR)  # the worker sees it close and cleans up
            except OSError:
                pass

    def _on_event(self, args) -> None:
        self._on_message(json.loads(args.additionalInfo))

    # Worker thread ----------------------------------------------------------

    def _serve(self) -> None:
        selector = selectors.DefaultSelector()
        selector.register(self._listener, selectors.EVENT_READ)
        while not self._stop.is_set():
            for key, _ in selector.select(timeout=0.5):
                if key.fileobj is self._listener:
                    selector.register(self._accept(), selectors.EVENT_READ, bytearray())  # data: the unread bytes
                else:
                    self._read(selector, key)
        selector.close()

    def _accept(self) -> socket.socket:
        client, _ = self._listener.accept()
        client.settimeout(SEND_TIMEOUT_S)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with self._lock:
            self._clients.add(client)
            for line in self._latest.values():
                self._send(client, line)
        log("INFO", f"{self._name} client connected")
        return client

    def _read(self, selector: selectors.BaseSelector, key: selectors.SelectorKey) -> None:
        client, buffer = key.fileobj, key.data
        try:
            data = client.recv(65536)
        except OSError:
            data = b""
        if not data:
            selector.unregister(client)
            with self._lock:
                self._clients.discard(client)
            client.close()
            log("INFO", f"{self._name} client disconnected")
            return
        buffer += data
        while (end := buffer.find(b"\n")) >= 0:
            self._receive(bytes(buffer[:end]))
            del buffer[:end + 1]

    def _receive(self, line: bytes) -> None:
        if not line.strip():
            return
        try:
            message = json.loads(line)
        except ValueError:
            log("WARN", f"ignored a malformed line from a {self._name} client: {line[:80]!r}")
            return
        if isinstance(message, dict):
            self._app.fireCustomEvent(self._event_id, json.dumps(message))
