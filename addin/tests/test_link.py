"""link.Link — the plugin connection: line framing, and every message handled on the main thread."""

import json
import socket
import threading
import unittest

import _bootstrap  # noqa: F401

import adsk.core
from FusionKeypad.lib import events
from FusionKeypad.lib.link import CONNECTED, HOST, Link

TEST_PORT = 47899  # not the real port, so an add-in running in Fusion can't interfere
PRESS = {"type": "press", "slot": 2, "layout": 1}


class LinkTest(unittest.TestCase):
    def setUp(self):
        self.app = adsk.core.Application()
        self.received: list[dict] = []
        self.handled_on: set[threading.Thread] = set()
        self.link = Link(self.app, self._on_message, port=TEST_PORT)
        self.assertTrue(self.link.start())
        self.addCleanup(events.unsubscribe_all)
        self.addCleanup(self.link.stop)

    def _on_message(self, message: dict) -> None:
        self.received.append(message)
        self.handled_on.add(threading.current_thread())

    def connect(self) -> socket.socket:
        client = socket.create_connection((HOST, TEST_PORT), timeout=2)
        self.addCleanup(client.close)
        connections = self.received.count(CONNECTED)
        self.assertTrue(self.app.pump_until(lambda: self.received.count(CONNECTED) > connections))
        return client

    def test_a_connecting_plugin_is_announced_on_the_main_thread(self):
        self.connect()
        self.assertEqual(self.received, [CONNECTED])
        self.assertEqual(self.handled_on, {threading.current_thread()})

    def test_sends_each_message_as_one_json_line(self):
        client = self.connect()
        message = {"type": "keys", "layout": 1, "keys": [{"label": "Create ›", "image": None}]}
        self.link.send(message)
        self.assertEqual(_read_line(client), message)

    def test_press_lines_reach_the_main_thread_even_when_split(self):
        client = self.connect()
        line = (json.dumps(PRESS) + "\n").encode()
        client.sendall(line[:9])
        client.sendall(line[9:])
        self.assertTrue(self.app.pump_until(lambda: PRESS in self.received))
        self.assertEqual(self.handled_on, {threading.current_thread()})

    def test_malformed_lines_are_ignored(self):
        client = self.connect()
        client.sendall(b"not json\n[1, 2]\n\n" + (json.dumps(PRESS) + "\n").encode())
        self.assertTrue(self.app.pump_until(lambda: PRESS in self.received))
        self.assertEqual(self.received, [CONNECTED, PRESS])

    def test_a_new_connection_replaces_the_old_one(self):
        first = self.connect()
        self.connect()
        self.assertEqual(first.recv(1), b"")  # the old connection was closed

    def test_stop_closes_the_connection_frees_the_port_and_unregisters(self):
        client = self.connect()
        self.link.stop()
        self.assertEqual(client.recv(1), b"")
        self.assertEqual(self.app.registered_events(), [])
        again = Link(adsk.core.Application(), self._on_message, port=TEST_PORT)
        self.assertTrue(again.start())
        again.stop()


def _read_line(client: socket.socket) -> dict:
    buffer = b""
    while b"\n" not in buffer:
        buffer += client.recv(65536)
    return json.loads(buffer.split(b"\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
