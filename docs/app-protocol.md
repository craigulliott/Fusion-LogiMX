# App protocol

Other programs on the same Mac can follow the Fusion add-in and start Fusion
tools through it. An app talks to the add-in running inside Fusion, never to
the Logi plugin or the keypad, and it works whether or not a keypad is
connected. It can't press keys or change what they show.

The pages and tools an app sees are the add-in's keypad definition,
[`contexts.py`](../addin/FusionKeypad/lib/contexts.py), not Fusion's toolbar.
"The user is adding constraints" means a tool filed under Constraints there is
running.

## Connection

Apps connect over TCP to `127.0.0.1:47824`, where the add-in listens while it
runs. Any number of apps can connect at once. Messages are UTF-8 JSON objects,
one per line (`\n`-terminated). A malformed line is ignored.

On connecting, an app is sent `definition` and then the current `state`. After
that, `state` is sent each time it changes. Nothing is queued while an app is
disconnected: reconnecting sends both again.

## Add-in → app: `definition`

Every page and key, in keypad order. It doesn't change while the add-in runs.

```json
{"type": "definition", "roots": [
  {"id": "Sketch", "name": "Sketch", "default": null, "icons": null, "items": [
    {"id": "Sketch/Create", "name": "Create", "default": null, "icons": "/…/DrawPolyline", "items": […]},
    {"id": "Sketch/Constraints", "name": "Constraints", "default": null, "icons": "/…/ConstraintCoincident", "items": [
      {"command": "ConstraintMidPoint", "label": "Midpoint", "name": "Midpoint", "icons": "/…/ConstraintMidPoint"},
      …]},
    …]},
  …]}
```

`roots` are the top-level contexts, such as Sketch and Part. An item with
`items` is a context (a page of keys); any other item is a tool (a key that
starts a Fusion command).

| Context field | Meaning |
|---|---|
| `id` | Its path of names from its root, such as `Sketch/Create/Circle`. No two contexts share one. |
| `name` | The name on its key. |
| `default` | For a tool with variants (Circle → 2-Point, 3-Point, …), the command its key starts. Otherwise `null`. |
| `icons` | See [Icons](#icons). |
| `items` | Its keys, tools and contexts, in keypad order. |

| Tool field | Meaning |
|---|---|
| `command` | Fusion's command ID: what `run` takes. |
| `label` | The short name on its key. |
| `name` | Fusion's own name for the command, or `null` if this Fusion build has no such command. |
| `icons` | See [Icons](#icons). |

## Add-in → app: `state`

```json
{"type": "state", "context": "Sketch/Constraints", "running": "ConstraintCoincident"}
```

| Field | Meaning |
|---|---|
| `context` | The `id` of the add-in's current context (which the keypad also shows), or `null` where no root applies, such as outside the Design workspace. |
| `running` | The `command` of the running tool if it has a key, otherwise `null`. |

The current context follows Fusion. Starting a tool, from the mouse, a key or
an app, moves it to the context holding that tool's key, and ending the tool
returns it to the top level for where the user is. The keypad's own page keys
and ‹ Back move it too. The full rules are in
[`navigator.py`](../addin/FusionKeypad/lib/navigator.py). Which page of a long
context the keypad shows (More ›) is the keypad's business and isn't part of
`state`.

## App → add-in: `run`

```json
{"type": "run", "command": "ConstraintTangent"}
```

Asks Fusion to start a command. Only commands with a key in the definition are
run; anything else is ignored.

Fusion starts a command asynchronously, and `state` changes once Fusion reports
that it started: usually about 50 ms later, but up to a few seconds while
Fusion is busy (a marking menu is open, or AutoSave is running). Show what's
running from `state`, not from what was asked. Starting a tool from an app also
moves the keypad, just as starting it with the mouse does.

## Icons

`icons` is the folder of Fusion's own artwork for the item, in every size and
theme Fusion ships, such as `32x32.png`, `32x32@2x.png`, `64x64-dark.png` or
`32x32-dark_gray.svg`. Which files exist varies by command, so pick by file
name from what's there. It's the same icon the item's key uses: a tool's own
command, or for a context its `default` or another command chosen in
`contexts.py`. It's `null` where there's no Fusion artwork: a root, or an item
whose key uses an image file of the add-in's own (`icon=` naming a file in
`FusionKeypad/icons/`).

The folders are inside Fusion's installation, which moves when Fusion updates,
so take them from the latest `definition` rather than storing them. Reading
them needs the app to run on the same Mac, outside the App Sandbox.

## Example client

[`examples/app_client.py`](../examples/app_client.py) uses only Python's
standard library:

```sh
python3 examples/app_client.py                        # print the keys of each context the add-in moves to
python3 examples/app_client.py run ConstraintTangent  # start a tool, then do the same
```

Each time the context changes, it prints the context's `id` and one line per
key: `▶` for the running tool, then its label, command, Fusion's name and icon
folder, or which context a page key opens. It shows the three steps every app
takes:

1. Index the contexts in `definition` by `id` (`index`).
2. On each `state`, look up `context` in that index to find the keys to show, and
   mark the one whose `command` is `running` (`show`).
3. Send `run` with a tool's `command` to start it, and leave the display to the
   `state` that follows.
