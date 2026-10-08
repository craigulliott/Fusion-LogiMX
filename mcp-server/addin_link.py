"""The connection to the Fusion add-in (docs/protocol.md): its latest `state`, and
asking it to start a command.

The link reconnects every RETRY_S while nothing listens, so the server outlives
Fusion and the add-in restarting.
"""

from __future__ import annotations

import asyncio
import json
import logging

HOST = "127.0.0.1"
ADDIN_PORT = 47824
RETRY_S = 1.0
START_TIMEOUT_S = 5.0  # how long Fusion can be busy: a marking menu open, AutoSave, a document switch
LINE_LIMIT = 1 << 20  # a state line carries the running tool's icons

log = logging.getLogger(__name__)


class AddinLink:
    def __init__(self, port: int = ADDIN_PORT):
        self._port = port
        self.state: dict | None = None  # the add-in's latest `state`; None while disconnected
        self._writer: asyncio.StreamWriter | None = None  # open whenever `state` isn't None
        self._changed = asyncio.Condition()  # notified on every new `state`

    async def serve(self) -> None:
        """Follow the add-in's `state` for as long as the server runs."""
        while True:
            try:
                reader, self._writer = await asyncio.open_connection(HOST, self._port, limit=LINE_LIMIT)
            except OSError:
                await asyncio.sleep(RETRY_S)
                continue
            log.info("connected to the add-in on %s:%d", HOST, self._port)
            try:
                async for line in reader:
                    await self._follow(json.loads(line))
            except ConnectionError:
                pass
            await self._follow(None)
            self._writer.close()
            self._writer = None
            log.info("disconnected from the add-in")

    async def run(self, command: str) -> dict | None:
        """Ask Fusion to start a command, while `state` isn't None.

        Returns the `state` that shows it running, or None if Fusion hasn't started
        it within START_TIMEOUT_S. A command that is already running counts at once:
        the add-in doesn't resend a `state` that hasn't changed.
        """
        self._writer.write((json.dumps({"type": "run", "command": command}) + "\n").encode())
        try:
            async with asyncio.timeout(START_TIMEOUT_S), self._changed:
                await self._changed.wait_for(lambda: self.state is not None and self.state["running"] == command)
        except TimeoutError:
            return None
        return self.state

    async def _follow(self, state: dict | None) -> None:
        async with self._changed:
            self.state = state
            self._changed.notify_all()
