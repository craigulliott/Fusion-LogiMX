"""An example app for the Fusion Keypad add-in (docs/app-protocol.md).

    python3 examples/app_client.py                        # print the keys of each context the add-in moves to
    python3 examples/app_client.py run ConstraintTangent  # start a tool, then do the same

Standard library only. Fusion must be running with the add-in started.
"""

from __future__ import annotations

import json
import socket
import sys

ADDRESS = ("127.0.0.1", 47824)


def main() -> None:
    with socket.create_connection(ADDRESS) as connection:
        if sys.argv[1:2] == ["run"]:
            send(connection, {"type": "run", "command": sys.argv[2]})
        follow(connection)


def follow(connection: socket.socket) -> None:
    contexts: dict[str, dict] = {}
    for message in receive(connection):
        if message["type"] == "definition":
            contexts = index(message["roots"])
        elif message["type"] == "state":
            show(contexts.get(message["context"]), message["running"])


def index(roots: list[dict]) -> dict[str, dict]:
    """Every context in the definition, by id."""
    contexts = {}
    pending = list(roots)
    while pending:
        context = pending.pop()
        contexts[context["id"]] = context
        pending += [item for item in context["items"] if "items" in item]
    return contexts


def show(context: dict | None, running: str | None) -> None:
    if context is None:
        print("(no context: the keypad is blank)\n")
        return
    print(context["id"])
    for item in context["items"]:
        if "items" in item:
            print(f"    {item['name'] + ' ›':<14} opens {item['id']}")
        else:
            mark = "▶" if item["command"] == running else " "
            print(f"  {mark} {item['label']:<14} {item['command']:<32} {item['name'] or '':<24} {item['icons'] or ''}")
    print()


def receive(connection: socket.socket):
    """The add-in's messages: JSON, one per line."""
    with connection.makefile(encoding="utf-8") as lines:
        for line in lines:
            yield json.loads(line)


def send(connection: socket.socket, message: dict) -> None:
    connection.sendall((json.dumps(message) + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
