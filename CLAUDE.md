# Fusion Keypad — working notes

A Fusion add-in (Python, `addin/`) drives a Logitech MX Keypad through a thin Logi
plugin (Node.js/TypeScript, `plugin/`), and lets an LLM start Fusion's tools through
a thin local MCP server (Python, `mcp-server/`). See README.md for setup and use, and
docs/protocol.md for the messages between the add-in and its two clients.

## Architecture rules

- **The add-in decides; its clients relay.** Neither client knows anything about Fusion.
  The plugin shows the nine faces it is sent and reports presses by slot. The MCP server
  offers the choices it is sent as one tool, asks the add-in to `run` the one picked, and
  hands back the icon it was sent. New tools or pages never need a plugin or server change.
- **Fusion's events are the single source of truth.** A key press or the MCP server's `run`
  only asks Fusion to act (start a command, cancel the tool). The keypad moves, and the
  server reports a start, when Fusion reports the result (commandStarting/commandTerminated),
  never optimistically.
- **Pure core, thin edges.** `registry`, `contexts`, `navigator`, `layout` and `menu` never
  import `adsk` and carry the logic and its tests. `fusion` (every Fusion read and action),
  `tracker` (events and the poll → navigator), `link` (sockets ↔ main thread) and
  `lifecycle` (wiring) are thin.
- **The keypad definition is data.** All pages and keys live in `lib/contexts.py`.
  Each command has at most one key per root, so a running tool has one home; `Registry` enforces
  it along with the other definition rules.

## Conventions

- **Python, in both the add-in and the MCP server:**
  - ruff with the explicit E4/E7/E9/F set (the root `ruff.toml`);
  - `unittest` with hand-written fakes, no mocking framework.
- **The add-in:**
  - a thin entry file, logic in `lib/`;
  - imports within the add-in are relative (`from .lib import …`), and nothing touches
    `sys.path`. Fusion loads the add-in folder as a package and runs every add-in in one
    interpreter, so an absolute `from lib import …` picks up whichever add-in's `lib` loaded
    first. `tests/test_entry.py` guards this;
  - every Fusion accessor guarded, and handler exceptions logged, never raised;
  - standard library only (it runs in Fusion's Python), `.py` source only.
- **Event handlers** are only attached through `events.subscribe` / `events.register_custom_event`,
  which keep them referenced (a garbage-collected handler crashes Fusion silently on its next callback).
- **Worker threads never touch the Fusion API.** They only call `fireCustomEvent`, and the
  handler does the work on the main thread.
- **The MCP server:**
  - the `mcp` SDK's low-level `Server` (v2), run with uv and pinned by `uv.lock`;
  - stdout carries MCP, so nothing prints: it logs to `~/Library/Logs/FusionKeypad-mcp.log`;
  - a failed call is an `is_error` result the model can read, never an exception (v2 turns
    those into protocol errors);
  - `tool` and `start` are tested with a fake link; `appearance()` and `serve()` are thin edges.
- **TypeScript:**
  - strict `tsc` for type checking only;
  - esbuild bundles, and `node --test` runs the tests by stripping types, so imports use `.ts`
    extensions and no emitted syntax (enums, parameter properties) is allowed.

## Facts established by the probes (Fusion 2705, macOS, 2026-09-30)

**Fusion:**
- **Command IDs:**
  - Line is `DrawPolyline`; sketch create/edit/finish are `SketchCreate`, `SketchActivate`
    and `SketchStop`.
  - `CommandDefinition.resourceFolder` points at each native command's icon folder.
- **Tools stay active.** Sketch tools and constraints keep running after each shape, and no
  event fires while they add geometry. That's why the tracker polls `sketchCurves.count`.
- **Termination reasons:**
  - Esc, right-click → OK, and `ui.terminateActiveCommand()` all report `Completed`.
  - Starting another tool or finishing the sketch reports `PreEmpted`.
  - `SelectCommand.execute()` also reads as `PreEmpted`, so don't use it to cancel.
- **`terminateActiveCommand()` is synchronous:** the commandTerminated event fires before it
  returns. `navigator._back` relies on this.
- **Starting a command is asynchronous:** `execute()` returns, and commandStarting follows
  about 50 ms later on the main thread.
- **Commands the keypad must ignore:**
  - `ConstrainedOrbitCommand` (fires on every right-click);
  - `CommitCommand`, `SelectCommand` and `AutoSaveFilesCommand`;
  - document and workspace commands.
  They have no key, so the navigator ignores them.
- **Detecting sketch mode:** `app.activeEditObject` is reliable. `ui.activeToolbarTab` lags
  and flickers. Switching documents restores each document's sketch-edit state.
- **Sketch tools work outside a sketch:** Fusion asks for a plane, creates a sketch and
  enters it mid-command.
- **Main-thread availability:**
  - custom events usually wait 0–15 ms;
  - blocked while a marking menu is open (up to 5 s), during AutoSave (~2 s), on document
    switches (~3 s), and on sketch open/finish (~0.6 s).
  - Polling outside a sketch didn't break double-click on macOS.

**Logi Plugin Service (6.4.1):**
- The MX Keypad reports as `046d:c354`, the MX Creative Keypad's hardware.
- **The SDK hides runtime redraws.** `@logitech/plugin-sdk` 0.1.1 has no public API for
  changing key images or labels. `plugin/src/lps-bridge.ts` answers
  `GetActionImage`/`GetActionText` itself and sends `ActionImageChanged`/`ActionTextChanged`
  through the SDK's private `_client`. That's why the SDK is pinned exactly.
- **Only visible keys are requested,** and they're re-requested when their page reappears,
  so nothing needs resending when Fusion regains focus.
- **Labels:** an empty or whitespace label falls back to the action's display name, so a
  blank label is sent as a zero-width space.
- **Images:** base64 PNG and SVG both render; about 80 px suits the keys.
- **Speed:** redraws land in about 25–50 ms, and 10 full-keypad repaints 100 ms apart all land.
- **The physical page buttons** belong to Options+; a plugin can't intercept them outside a
  dynamic folder. Hence the on-screen More key.

**Icons and the MCP SDK (checked 2026-10-08):**
- Fusion ships each command icon for a dark and a light background: `64x64-dark.png` and
  `64x64.png`, `dark_gray` and `light_gray` SVGs, and for the newest commands only
  `weave_dark` and `weave_light` SVGs.
- `mcp` 2.3.0 serves both the initialize handshake (2024-11-05 to 2025-11-25) and the
  stateless 2026-07-28 protocol over stdio; both kinds of client were tried.

## Layout

```
addin/FusionKeypad/          the folder linked into Fusion's AddIns
  FusionKeypad.py            run/stop only
  lib/contexts.py            the keypad definition (edit this to add tools)
  lib/registry.py            Tool/Context/Root + lookups and definition checks
  lib/navigator.py           the rules that move the keypad
  lib/layout.py              key faces (labels, marks, icons)
  lib/menu.py                the MCP server's choices (by name, nearest first)
  lib/fusion.py              every Fusion read and action
  lib/tracker.py             Fusion events + sketch poll → navigator
  lib/link.py                localhost links (plugin, MCP server), messages → main thread
  lib/lifecycle.py           wiring, start/stop
addin/tests/                 unittest; stubs/adsk is a minimal stand-in
plugin/index.ts, src/        the Logi plugin
mcp-server/server.py         the MCP server: its tool, starting it, stdio
mcp-server/addin_link.py     the connection to the add-in
mcp-server/tests/            unittest
docs/protocol.md             add-in ⇄ plugin and add-in ⇄ MCP server messages
ruff.toml                    lint rules for all the Python
```
