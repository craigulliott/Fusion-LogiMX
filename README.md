# Fusion Keypad

Drives a Logitech MX Keypad from Autodesk Fusion. The nine keys follow what
you're doing in Fusion and start Fusion's own tools. For example: open a sketch
and the keys offer Create and Constraints; tap Circle and they show the circle
types; draw the circle and they return to the Create list; start a constraint
with the mouse and they switch to the constraints.

It has two halves in this repository:

| | What it does |
|---|---|
| [`addin/`](addin/) | A Fusion add-in in Python. It decides everything: which keys to show, what they do, and how the keypad follows Fusion. |
| [`plugin/`](plugin/) | A small Logitech plugin in Node.js/TypeScript. It draws whatever the add-in sends on the keys and reports presses back. |

```
Fusion events ──▶ add-in ──(localhost, docs/protocol.md)──▶ plugin ──▶ Logi Plugin Service ──▶ keypad
Fusion tools  ◀── add-in ◀────────── key presses ◀────────── plugin ◀──────────────────────── keypad
```

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

After editing, restart the add-in (`Shift+S` → Stop, then Run). The plugin never needs changing
to add tools.

## Development

```sh
cd addin/tests && python3 -m unittest discover   # add-in tests (no Fusion needed)
cd addin && uvx ruff check .                      # add-in lint
cd plugin && npm test                             # plugin tests
cd plugin && npm run build                        # type check + bundle
cd plugin && npm run watch                        # rebuild and reload the plugin on every save
```

`fusion.py` and `tracker.py` are thin adapters over Fusion's API and are checked in Fusion
itself; everything else is covered by the tests above.

Logs:
- `~/Library/Logs/FusionKeypad-addin.log`
- `~/Library/Logs/FusionKeypad-plugin.log` (`npm run log` follows it)

## Troubleshooting

| The keys show… | Meaning |
|---|---|
| "Fusion add-in offline" | The plugin can't reach the add-in: start it in Fusion (`Shift+S`). |
| "Fusion Key 1" … "Fusion Key 9" | The plugin couldn't hook the Logitech SDK. Check the plugin log for `FAIL`. |
| Nothing, or another app's keys | The keys aren't on the Autodesk Fusion profile in Options+, or Fusion isn't the app in front. |
