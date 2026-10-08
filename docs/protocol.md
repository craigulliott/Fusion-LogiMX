# The add-in's links

The Fusion add-in (`addin/`) has two clients, each on a localhost port of its own:

| Port | Client | Messages |
|---|---|---|
| 47823 | The Logi plugin (`plugin/`), which draws the keypad | [Keypad plugin](#keypad-plugin-port-47823) |
| 47824 | The MCP server (`mcp-server/`), which offers Fusion's tools to an LLM | [MCP server](#mcp-server-port-47824) |

The add-in decides everything, and its clients relay. All three are built from
this repository, so there is no version negotiation.

## Connection

- The add-in listens on `127.0.0.1`, and each port takes any number of clients.
  A client connects, and retries once a second while nothing is listening.
- Messages are UTF-8 JSON objects, one per line (`\n`-terminated).
- On connecting, a client is sent the add-in's latest message, and after that
  each message that differs from the one before.
- The add-in disconnects a client that sends a line that isn't a JSON object, so
  an HTTP request (from a web page, say) never reaches Fusion.
- Nothing is queued while a client is disconnected.

## Keypad plugin (port 47823)

The plugin only draws what it is sent and reports which key was pressed.

### Add-in → plugin: `keys`

Sent whenever any key changes.

```json
{"type": "keys", "layout": 12, "keys": [{"label": "Circle ›", "image": "iVBORw0KG…"}, …]}
```

| Field | Meaning |
|---|---|
| `layout` | Identifies what the keys *do*. It changes only when a key's action changes, not when a label or image changes (for example, the `▶` mark on the running tool). |
| `keys` | Exactly 9 entries, in reading order: key 1 is top-left and key 9 is bottom-right. |
| `keys[].label` | The text shown on the key. An empty string gives a blank label. |
| `keys[].image` | A base64-encoded PNG or SVG, or `null` for a text-only key. |

### Plugin → add-in: `press`

```json
{"type": "press", "slot": 3, "layout": 12}
```

| Field | Meaning |
|---|---|
| `slot` | The key's index, from 0 to 8, in the same order as `keys`. |
| `layout` | The `layout` of the `keys` message on screen when the key was pressed. |

The add-in ignores a press whose `layout` isn't the current one. That way a
press can't act on a key that changed meaning just before, such as when drawing
a circle moved the keypad back to the Create list.

While the connection is down, the plugin shows an "add-in offline" face.

## MCP server (port 47824)

The MCP server offers the add-in's choices to an LLM as one tool, and asks the
add-in to start the one chosen.

### Add-in → MCP server: `state`

Sent whenever any field changes.

```json
{"type": "state", "context": "Sketch/Constraints", "running": "ConstraintTangent",
 "icon": {"dark": "iVBORw0KG…", "light": "iVBORw0KG…"},
 "choices": [{"name": "Tangent", "command": "ConstraintTangent"}, …]}
```

| Field | Meaning |
|---|---|
| `context` | Where the user is: the add-in's current context, named by its path from its root, such as `Sketch/Constraints`. `null` where no root applies, such as outside the Design workspace. |
| `running` | The command of the running tool if it has a key, otherwise `null`. |
| `icon` | The running tool's key image, for a `dark` and a `light` background: each a base64-encoded PNG or SVG, or `null` where there is none. `null` while nothing is running. |
| `choices` | What the server can offer, nearest first: each command's `name` (Fusion's own, or a page's name for its default) and `command`. Empty where `context` is `null`. |

The choices are every command in the current root. From the current context up
to the root, each level adds its commands in keypad order. A name stays with the
nearest command that has it, and commands this Fusion build lacks are left out.
[`menu.py`](../addin/FusionKeypad/lib/menu.py) has the rules.

### MCP server → add-in: `run`

```json
{"type": "run", "command": "ConstraintTangent"}
```

Asks Fusion to start a command. The add-in ignores a command without a key.

The command has started once a `state` names it `running`: usually about 50 ms
later, but up to a few seconds while Fusion is busy (a marking menu is open,
AutoSave runs, a document switch). Starting the running command again leaves
`state` unchanged, so no new `state` comes: a `run` for the command already
running is confirmed at once.
