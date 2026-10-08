# Keypad protocol

The Logi plugin (`plugin/`) and the Fusion add-in (`addin/`) talk over one TCP
connection on `127.0.0.1:47823`. The add-in listens. The plugin connects, and
retries once a second while nothing is listening. Both halves are built from
this repository, so there is no version negotiation. Apps use a port and
protocol of their own: see [app-protocol.md](app-protocol.md).

Messages are UTF-8 JSON objects, one per line (`\n`-terminated). A malformed
line is ignored.

The add-in decides everything the keys show and do. The plugin only draws what
it is sent and reports which key was pressed.

## Add-in → plugin: `keys`

Sent when the plugin connects and whenever any key changes.

```json
{"type": "keys", "layout": 12, "keys": [{"label": "Circle ›", "image": "iVBORw0KG…"}, …]}
```

| Field | Meaning |
|---|---|
| `layout` | Identifies what the keys *do*. It changes only when a key's action changes, not when a label or image changes (for example, the `▶` mark on the running tool). |
| `keys` | Exactly 9 entries, in reading order: key 1 is top-left and key 9 is bottom-right. |
| `keys[].label` | The text shown on the key. An empty string gives a blank label. |
| `keys[].image` | A base64-encoded PNG or SVG, or `null` for a text-only key. |

## Plugin → add-in: `press`

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

## Disconnection

When the connection drops, the plugin shows an "add-in offline" face and keeps
retrying. On reconnect the add-in sends a fresh `keys` message. Neither side
queues messages while disconnected.
