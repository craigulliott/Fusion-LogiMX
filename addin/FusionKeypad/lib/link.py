"""The connection to the Logi plugin (docs/protocol.md).

A worker thread owns the listening socket and the plugin's connection and never
touches the Fusion API: each message from the plugin crosses to the main thread
as a custom event. Sends happen on the main thread.
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
PORT = 47823
MESSAGE_EVENT_ID = "FusionKeypad.message"
SEND_TIMEOUT_S = 1.0

# Handed to on_message when a plugin connects, so it can be sent the keys.
CONNECTED = {"type": "connected"}


class Link:
    def __init__(self, app: adsk.core.Application, on_message: Callable[[dict], None], port: int = PORT):
        self._app = app
        self._on_message = on_message  # runs on the main thread
        self._port = port
        self._client: socket.socket | None = None
        self._client_lock = threading.Lock()
        self._listener: socket.socket | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if events.register_custom_event(self._app, MESSAGE_EVENT_ID, self._on_event, "plugin message") is None:
            return False
        try:
            self._listener = socket.create_server((HOST, self._port))
        except OSError as error:
            log("ERROR", f"cannot listen on {HOST}:{self._port}: {error}")
            return False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._client_lock:
            if self._client is not None:
                self._client.close()
                self._client = None
        if self._listener is not None:
            self._listener.close()
        try:
            self._app.unregisterCustomEvent(MESSAGE_EVENT_ID)
        except Exception:
            pass

    def send(self, message: dict) -> None:
        """Send one message to the plugin, if one is connected. Main thread."""
        data = (json.dumps(message) + "\n").encode("utf-8")
        with self._client_lock:
            client = self._client
            if client is None:
                return
            try:
                client.sendall(data)
            except OSError as error:
                log("WARN", f"sending to the plugin failed ({error}); dropping the connection")
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
        buffer = b""
        while not self._stop.is_set():
            for key, _ in selector.select(timeout=0.5):
                if key.fileobj is self._listener:
                    connection, _ = self._listener.accept()
                    previous = self._replace_client(connection)
                    if previous is not None:
                        selector.unregister(previous)
                        previous.close()
                    selector.register(connection, selectors.EVENT_READ)
                    buffer = b""
                    log("INFO", "plugin connected")
                    self._fire(CONNECTED)
                    continue
                try:
                    data = key.fileobj.recv(65536)
                except OSError:
                    data = b""
                if not data:
                    selector.unregister(key.fileobj)
                    self._forget_client(key.fileobj)
                    log("INFO", "plugin disconnected")
                    continue
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._receive(line)
        selector.close()

    def _receive(self, line: bytes) -> None:
        if not line.strip():
            return
        try:
            message = json.loads(line)
        except ValueError:
            log("WARN", f"ignored a malformed line from the plugin: {line[:80]!r}")
            return
        if isinstance(message, dict):
            self._fire(message)

    def _fire(self, message: dict) -> None:
        self._app.fireCustomEvent(MESSAGE_EVENT_ID, json.dumps(message))

    def _replace_client(self, connection: socket.socket) -> socket.socket | None:
        connection.settimeout(SEND_TIMEOUT_S)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with self._client_lock:
            previous, self._client = self._client, connection
        return previous

    def _forget_client(self, connection: socket.socket) -> None:
        with self._client_lock:
            if self._client is connection:
                self._client = None
        connection.close()
