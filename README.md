# Fusion Keypad

Drives a Logitech MX Keypad from Autodesk Fusion. The nine keys follow what
you're doing in Fusion and start Fusion's own tools. For example: open a sketch
and the keys offer Create and Constraints; tap Circle and they show the circle
types; draw the circle and they return to the Create list; start a constraint
with the mouse and they switch to the constraints.

It has three parts in this repository:

| | What it does |
|---|---|
| [`addin/`](addin/) | A Fusion add-in in Python. It decides everything: which keys to show, what they do, and how the keypad follows Fusion. |
| [`plugin/`](plugin/) | A small Logitech plugin in Node.js/TypeScript. It draws whatever the add-in sends on the keys and reports presses back. |
| [`mcp-server/`](mcp-server/) | An optional MCP server in Python. It lets an LLM, in a dictation app say, start the Fusion tool you name. |

```
Fusion events ──▶ add-in ──(localhost, docs/protocol.md)──▶ plugin ──▶ Logi Plugin Service ──▶ keypad
Fusion tools  ◀── add-in ◀────────── key presses ◀───────── plugin ◀────────────────────────── keypad
Fusion tools  ◀── add-in ◀──(localhost, docs/protocol.md)── MCP server ◀──(MCP over stdio)── dictation app
```

You can also start tools by voice: see [Voice and LLM control](#voice-and-llm-control).

## Setup

You need Logi Options+ (it includes Logi Plugin Service) and Node.js 22.18 or newer.

**1. The Fusion add-in.** Link the add-in folder into Fusion's add-ins folder:

```sh
ln -s "$PWD/addin/FusionKeypad" ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/AddIns/FusionKeypad
```

Then, in Fusion, open **Utilities → Add-Ins → Scripts and Add-Ins** (`Shift+S`) and go to the
**Add-Ins** tab. Select **FusionKeypad**, click **Run**, and tick **Run on Startup**.

**2. The Logitech plugin.**

```sh
cd plugin
npm install
npm run build
npm run link      # links dist/ into Logi Plugin Service and reloads the plugin
```

**3. Logi Options+.**
1. Select the MX Keypad and add an application profile for **Autodesk Fusion**, so the keys
   appear whenever Fusion is in front.
2. Under **All actions → Fusion Keypad → Fusion Keys**, drag **Fusion Key 1** to **Fusion Key 9**
   onto the nine keys in reading order: 1 is top-left, 9 is bottom-right.

## How the keypad follows you

- **Where you are picks the top level.** Editing a sketch shows Create, Constraints, Dimension,
  Construction, Centerline and Finish. Elsewhere in a part design (or a hybrid one), it shows New
  Sketch, Create, Modify, Construct, Joint Origin, Parameters, Section Analysis and Derive; in an
  assembly design, Insert Component, Joint and Section Analysis. Any other workspace gives a blank
  keypad.
- **Starting a tool, from the keypad or the mouse, shows the page with its key,** marked `▶`.
- **A key marked `›` opens a page.** Pages for tools with variants (Circle, Arc, Slot, …) also
  start the default variant.
- **Drawing a shape with a variant tool returns you to the Create list.** The tool keeps
  running, as it does in Fusion.
- **When a tool ends** (Esc, OK, Finish), the keypad returns to the top level.
- **‹ Back goes up one level.** Backing out to the top level cancels the running tool.
- **More ›** appears on pages that don't fit on one screen.

The exact rules, with their reasons, are in
[`addin/FusionKeypad/lib/navigator.py`](addin/FusionKeypad/lib/navigator.py).

## Adding tools and pages

Everything the keypad offers is defined in
[`addin/FusionKeypad/lib/contexts.py`](addin/FusionKeypad/lib/contexts.py), with instructions at
the top of the file.

- **A new key** is one `Tool(command_id, label)` line in the page where it belongs.
- **Finding a command's ID:** use the tool once with the mouse. The add-in logs the ID of every
  command that has no key yet.
- **Icons** come from Fusion automatically. To use a different one, add `icon=` with another
  command's ID, or with a `.png`/`.svg` file placed in `addin/FusionKeypad/icons/`.

After editing, restart the add-in (`Shift+S` → Stop, then Run). Neither the plugin nor the MCP
server needs changing to add tools.

## Voice and LLM control

[`mcp-server/`](mcp-server/) is a local MCP server, so an LLM (in a dictation app, say) can start
the Fusion tool you name: "coincident", "tangent", "line".

- **It offers one tool, `start_tool`.** Its names are the tools on the keypad for where you are in
  Fusion, nearest first, so adding a tool to `contexts.py` adds it here too.
- **Starting a tool works like clicking it.** The keypad follows, and the call returns once Fusion
  reports the tool running.
- **The result shows the tool's icon,** in the artwork for the Mac's current Light or Dark
  appearance, marked for the user rather than the model.

It can't enter values ("extrude 10 mm") or cancel a tool. Fusion's own MCP server (turned on in
Fusion's preferences) is a different thing: it runs Python an LLM writes, and doesn't know where
you are.

**Setup.** You need [uv](https://docs.astral.sh/uv/).

```sh
cd mcp-server
uv sync
```

Then add the server to your MCP host, such as your dictation app. Give absolute paths, because apps
started from the Dock don't get your shell's `PATH` (`which uv` shows where uv is):

```json
{"command": "/opt/homebrew/bin/uv", "args": ["run", "--directory", "/path/to/Fusion-LogiMX/mcp-server", "server.py"]}
```

**What the host should do:**
- **List the tools at the start of each dictation.** The list follows Fusion and is never fresh for
  long. While Fusion or the add-in isn't running, or outside the Design workspace, there are none.
- **Allow at least 6 s for a call.** A tool usually starts within about 50 ms, but Fusion can be busy
  for up to 5 s.
- **Never retry a call.** "Fusion is busy and will start it" means the tool is on its way.
- **Show image content marked for the user.**

## Development

```sh
cd addin/tests && python3 -m unittest discover             # add-in tests (no Fusion needed)
cd mcp-server && uv run python -m unittest discover tests   # MCP server tests
uvx ruff check .                                            # lint all the Python
cd plugin && npm test                                       # plugin tests
cd plugin && npm run build                                  # type check + bundle
cd plugin && npm run watch                                  # rebuild and reload the plugin on every save
npx @modelcontextprotocol/inspector uv run --directory mcp-server server.py   # try the MCP server
```

`fusion.py` and `tracker.py` are thin adapters over Fusion's API and are checked in Fusion
itself, as is the MCP server's wiring, through the Inspector. Everything else is covered by the
tests above.

Logs:
- `~/Library/Logs/FusionKeypad-addin.log`
- `~/Library/Logs/FusionKeypad-plugin.log` (`npm run log` follows it)
- `~/Library/Logs/FusionKeypad-mcp.log`

## Troubleshooting

| The keys show… | Meaning |
|---|---|
| "Fusion add-in offline" | The plugin can't reach the add-in: start it in Fusion (`Shift+S`). |
| "Fusion Key 1" … "Fusion Key 9" | The plugin couldn't hook the Logitech SDK. Check the plugin log for `FAIL`. |
| Nothing, or another app's keys | The keys aren't on the Autodesk Fusion profile in Options+, or Fusion isn't the app in front. |
