"""addin_link.AddinLink — follows the add-in's state across reconnects, and asks it to start commands."""

import asyncio
import json
import unittest

import addin_link
from addin_link import HOST, AddinLink

TEST_PORT = 47898  # not a real port, so an add-in running in Fusion can't interfere
SKETCHING = {"type": "state", "context": "Sketch", "running": None, "icon": None, "choices": []}
DRAWING = {**SKETCHING, "context": "Sketch/Create", "running": "DrawPolyline"}


class FakeAddin:
    """Listens on the test port like the add-in: sends states and records the lines it receives."""

    def __init__(self):
        self.clients: list[asyncio.StreamWriter] = []
        self.received: list[dict] = []

    async def listen(self) -> None:
        self._server = await asyncio.start_server(self._accept, HOST, TEST_PORT)

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.clients.append(writer)
        async for line in reader:
            self.received.append(json.loads(line))

    def send(self, message: dict) -> None:
        for client in self.clients:
            client.write((json.dumps(message) + "\n").encode())

    def drop(self) -> None:
        for client in self.clients:
            client.close()
        self.clients.clear()

    async def close(self) -> None:
        self.drop()
        self._server.close()
        await self._server.wait_closed()


class AddinLinkTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        for name, value in (("RETRY_S", 0.05), ("START_TIMEOUT_S", 0.2)):
            self.addCleanup(setattr, addin_link, name, getattr(addin_link, name))
            setattr(addin_link, name, value)
        self.addin = FakeAddin()
        await self.addin.listen()
        self.link = AddinLink(TEST_PORT)
        self.following = asyncio.create_task(self.link.serve())
        await eventually(lambda: self.addin.clients)

    async def asyncTearDown(self):
        self.following.cancel()
        await self.addin.close()

    async def test_follows_the_add_in_s_state(self):
        self.assertIsNone(self.link.state)
        self.addin.send(SKETCHING)
        await eventually(lambda: self.link.state == SKETCHING)

    async def test_run_asks_for_the_command_and_returns_the_state_that_shows_it_running(self):
        self.addin.send(SKETCHING)
        await eventually(lambda: self.link.state == SKETCHING)
        running = asyncio.create_task(self.link.run("DrawPolyline"))
        await eventually(lambda: self.addin.received == [{"type": "run", "command": "DrawPolyline"}])
        self.addin.send(DRAWING)
        self.assertEqual(await running, DRAWING)

    async def test_a_command_already_running_counts_at_once(self):
        self.addin.send(DRAWING)  # the add-in won't resend it when the command starts again
        await eventually(lambda: self.link.state == DRAWING)
        self.assertEqual(await self.link.run("DrawPolyline"), DRAWING)

    async def test_run_gives_up_when_fusion_does_not_confirm_in_time(self):
        self.addin.send(SKETCHING)
        await eventually(lambda: self.link.state == SKETCHING)
        self.assertIsNone(await self.link.run("DrawPolyline"))

    async def test_has_no_state_while_disconnected_and_follows_again_after_reconnecting(self):
        self.addin.send(SKETCHING)
        await eventually(lambda: self.link.state == SKETCHING)
        self.addin.drop()
        await eventually(lambda: self.link.state is None)
        await eventually(lambda: self.addin.clients)
        self.addin.send(DRAWING)
        await eventually(lambda: self.link.state == DRAWING)


async def eventually(condition, timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
