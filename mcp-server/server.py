"""Fusion Keypad's MCP server: one tool, start_tool, that starts the Fusion tool the user names.

The tool offers the add-in's choices for where the user is (docs/protocol.md), so
the tool list follows Fusion and is never fresh for long: hosts list it again for
each request. An MCP host runs the server over stdio, so nothing may print to
stdout; it logs to LOG_PATH.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    Annotations,
    CallToolRequestParams,
    CallToolResult,
    ImageContent,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)

from addin_link import AddinLink

SERVER_NAME = "fusion-keypad"
TOOL_NAME = "start_tool"
LOG_PATH = Path.home() / "Library" / "Logs" / "FusionKeypad-mcp.log"
PNG_BASE64 = "iVBORw0KGgo"  # how every base64 PNG starts; the add-in's other images are SVG


def tool(state: dict | None) -> Tool | None:
    """The tool for where the user is, or None when there is nothing to offer."""
    if state is None or not state["choices"]:
        return None
    return Tool(
        name=TOOL_NAME,
        description=(
            "Starts a tool in Autodesk Fusion, as if the user had clicked it. Call it once, with the name that "
            f"matches what the user said. These are the tools available where the user is now ({_where(state)}), "
            "nearest first. If none matches, don't call it."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The tool's name, exactly as listed.",
                    "enum": [choice["name"] for choice in state["choices"]],
                },
            },
            "required": ["name"],
        },
        annotations=ToolAnnotations(destructive_hint=False, idempotent_hint=True, open_world_hint=False),
    )


async def start(link: AddinLink, name: str, background: str) -> CallToolResult:
    """Start the named tool.

    Once Fusion reports it running, the result also carries its icon for a "dark"
    or "light" background, meant for the user rather than the model.
    """
    if link.state is None:
        return _error("Fusion isn't reachable. Start Fusion and its Fusion Keypad add-in.")
    command = next((choice["command"] for choice in link.state["choices"] if choice["name"] == name), None)
    if command is None:
        return _error(f"{name} isn't one of the tools available where the user is now.")
    running = await link.run(command)
    if running is None:
        busy = f"Asked Fusion to start {name}. Fusion is busy and will start it when it's free; don't ask again."
        return CallToolResult(content=[TextContent(text=busy)])
    content = [TextContent(text=f"Started {name}.")]
    if (icon := running["icon"][background]) is not None:
        content.append(_image(icon))
    return CallToolResult(content=content)


async def appearance() -> str:
    """The Mac's appearance, which the host's images appear against: "dark" or "light"."""
    process = await asyncio.create_subprocess_exec(
        "/usr/bin/defaults", "read", "-g", "AppleInterfaceStyle",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    output, _ = await process.communicate()
    return "dark" if output.strip() == b"Dark" else "light"  # Light mode has no AppleInterfaceStyle


def _where(state: dict) -> str:
    place = state["context"].replace("/", " › ")
    running = next((choice["name"] for choice in state["choices"] if choice["command"] == state["running"]), None)
    return f"{place}, with {running} running" if running else place


def _image(data: str) -> ImageContent:
    mime_type = "image/png" if data.startswith(PNG_BASE64) else "image/svg+xml"
    return ImageContent(data=data, mime_type=mime_type, annotations=Annotations(audience=["user"]))


def _error(text: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(text=text)], is_error=True)


async def serve() -> None:
    link = AddinLink()

    async def list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
        offered = tool(link.state)
        return ListToolsResult(tools=[offered] if offered else [], ttl_ms=0)  # stale at once: it follows Fusion

    async def call_tool(ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
        if params.name != TOOL_NAME:
            return _error(f"There is no tool {params.name}.")
        return await start(link, (params.arguments or {}).get("name"), await appearance())

    server = Server(SERVER_NAME, on_list_tools=list_tools, on_call_tool=call_tool)
    async with asyncio.TaskGroup() as tasks:
        following = tasks.create_task(link.serve())
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
        following.cancel()


def main() -> None:
    logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    asyncio.run(serve())


if __name__ == "__main__":
    main()
