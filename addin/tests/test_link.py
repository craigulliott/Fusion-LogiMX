"""link.Link — clients get the latest message of each type, and every line from them is handled on the main thread."""

import json
import socket
import threading
import unittest

import _bootstrap  # noqa: F401

import adsk.core
from FusionKeypad.lib import events
from FusionKeypad.lib.link import HOST, Link

TEST_PORT = 47899  # not a real port, so an add-in running in Fusion can't interfere
DEFINITION = {"type": "definition", "roots": []}
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

    def test_a_client_gets_the_latest_message_of_each_type_on_connecting(self):
        for message in (DEFINITION, SKETCHING, DRAWING):
            self.link.publish(message)
        self.assertEqual(_read_lines(self.connect(), 2), [DEFINITION, DRAWING])

    def test_publishes_each_message_to_every_client_as_one_json_line(self):
        self.link.publish(SKETCHING)
        clients = [self.connect(), self.connect()]
        for client in clients:
            self.assertEqual(_read_lines(client, 1), [SKETCHING])  # so both are connected
        self.link.publish(DRAWING)
        for client in clients:
            self.assertEqual(_read_lines(client, 1), [DRAWING])

    def test_a_message_that_repeats_the_latest_of_its_type_is_not_sent_again(self):
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

    def test_malformed_lines_are_ignored(self):
        client = self.connect()
        client.sendall(b"not json\n[1, 2]\n\n" + (json.dumps(RUN) + "\n").encode())
        self.assertTrue(self.app.pump_until(lambda: RUN in self.received))
        self.assertEqual(self.received, [RUN])

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


def _read_lines(client: socket.socket, count: int) -> list[dict]:
    buffer = b""
    while buffer.count(b"\n") < count:
        buffer += client.recv(65536)
    return [json.loads(line) for line in buffer.split(b"\n")[:count]]


if __name__ == "__main__":
    unittest.main()
