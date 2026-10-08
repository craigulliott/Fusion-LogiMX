"""link.Link — clients get the latest message; their lines reach the main thread unless one isn't a JSON object."""

import json
import socket
import threading
import unittest

import _bootstrap  # noqa: F401

import adsk.core
from FusionKeypad.lib import events
from FusionKeypad.lib.link import HOST, Link

TEST_PORT = 47899  # not a real port, so an add-in running in Fusion can't interfere
SKETCHING = {"type": "state", "context": "Sketch", "running": None}
DRAWING = {"type": "state", "context": "Sketch/Create", "running": "DrawPolyline"}
RUN = {"type": "run", "command": "DrawPolyline"}


class LinkTest(unittest.TestCase):
    def setUp(self):
        self.app = adsk.core.Application()
        self.received: list[dict] = []
        self.handled_on: set[threading.Thread] = set()
        self.link = Link(self.app, "test", TEST_PORT, self._on_message)
        self.link.start()
        self.addCleanup(events.unsubscribe_all)
        self.addCleanup(self.link.stop)

    def _on_message(self, message: dict) -> None:
        self.received.append(message)
        self.handled_on.add(threading.current_thread())

    def connect(self) -> socket.socket:
        client = socket.create_connection((HOST, TEST_PORT), timeout=2)
        self.addCleanup(client.close)
        return client

    def test_a_client_gets_the_latest_message_on_connecting(self):
        for message in (SKETCHING, DRAWING):
            self.link.publish(message)
        self.assertEqual(_read_lines(self.connect(), 1), [DRAWING])

    def test_publishes_each_message_to_every_client_as_one_json_line(self):
        self.link.publish(SKETCHING)
        clients = [self.connect(), self.connect()]
        for client in clients:
            self.assertEqual(_read_lines(client, 1), [SKETCHING])  # so both are connected
        self.link.publish(DRAWING)
        for client in clients:
            self.assertEqual(_read_lines(client, 1), [DRAWING])

    def test_a_message_that_repeats_the_last_one_is_not_sent_again(self):
        self.link.publish(SKETCHING)
        client = self.connect()
        self.assertEqual(_read_lines(client, 1), [SKETCHING])
        self.link.publish(SKETCHING)
        self.link.publish(DRAWING)
        self.assertEqual(_read_lines(client, 1), [DRAWING])

    def test_lines_reach_the_main_thread_even_when_split(self):
        client = self.connect()
        line = (json.dumps(RUN) + "\n").encode()
        client.sendall(line[:9])
        client.sendall(line[9:])
        self.assertTrue(self.app.pump_until(lambda: RUN in self.received))
        self.assertEqual(self.handled_on, {threading.current_thread()})

    def test_an_http_request_is_disconnected_before_its_body_reaches_the_main_thread(self):
        client = self.connect()
        body = json.dumps(RUN)
        client.sendall(f"POST / HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n{body}\n".encode())
        self.assertTrue(_closed(client))
        self.assertFalse(self.app.pump_until(lambda: self.received, timeout=0.2))

    def test_any_line_that_is_not_a_json_object_disconnects_its_client(self):
        client = self.connect()
        client.sendall(b"[1, 2]\n" + (json.dumps(RUN) + "\n").encode())
        self.assertTrue(_closed(client))
        self.assertFalse(self.app.pump_until(lambda: self.received, timeout=0.2))

    def test_stop_closes_the_connections_frees_the_port_and_unregisters(self):
        self.link.publish(SKETCHING)
        client = self.connect()
        _read_lines(client, 1)
        self.link.stop()
        self.assertEqual(client.recv(1), b"")
        self.assertEqual(self.app.registered_events(), [])
        again = Link(adsk.core.Application(), "test", TEST_PORT, self._on_message)
        again.start()
        self.addCleanup(again.stop)
        self.connect()  # refused unless the new link could listen on the port


def _closed(client: socket.socket) -> bool:
    """Whether the link closed the connection, gracefully or with a reset."""
    try:
        return client.recv(1) == b""
    except ConnectionResetError:
        return True


def _read_lines(client: socket.socket, count: int) -> list[dict]:
    buffer = b""
    while buffer.count(b"\n") < count:
        buffer += client.recv(65536)
    return [json.loads(line) for line in buffer.split(b"\n")[:count]]


if __name__ == "__main__":
    unittest.main()
