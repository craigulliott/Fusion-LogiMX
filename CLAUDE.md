# Fusion Keypad — working notes

A Fusion add-in (Python, `addin/`) drives a Logitech MX Keypad through a thin Logi
plugin (Node.js/TypeScript, `plugin/`). See README.md for setup and use, and
docs/keypad-protocol.md for the message format between the two halves. Other apps
follow the add-in and start tools through it over docs/app-protocol.md.

## Architecture rules

- **The add-in decides; the plugin draws.** The plugin knows nothing about Fusion: it
  shows the nine faces it is sent and reports presses by slot. New tools or pages never
  need a plugin change.
- **Apps follow and ask.** An app gets the keypad definition and the add-in's current
  context, and can only ask Fusion to start a keyed command. It talks to the add-in, never
  to the plugin or the keypad.
- **Fusion's events are the single source of truth.** A key press or an app's `run` only
  asks Fusion to act (start a command, cancel the tool). The keypad moves when Fusion
  reports the result (commandStarting/commandTerminated), never optimistically.
- **Pure core, thin edges.** `registry`, `contexts`, `navigator`, `layout` and `apps` never
  import `adsk` and carry the logic and its tests. `fusion` (every Fusion read and action),
  `tracker` (events and the poll → navigator), `link` (sockets ↔ main thread) and
  `lifecycle` (wiring) are thin.
- **The keypad definition is data.** All pages and keys live in `lib/contexts.py`.
  Each command has at most one key per root, so a running tool has one home; `Registry` enforces
  it along with the other definition rules.

## Conventions

- **Python:**
  - a thin entry file, logic in `lib/`;
  - imports within the add-in are relative (`from .lib import …`), and nothing touches
    `sys.path`. Fusion loads the add-in folder as a package and runs every add-in in one
    interpreter, so an absolute `from lib import …` picks up whichever add-in's `lib` loaded
    first. `tests/test_entry.py` guards this;
  - every Fusion accessor guarded, and handler exceptions logged, never raised;
  - standard library only, `.py` source only;
  - ruff with the explicit E4/E7/E9/F set;
  - `unittest` with hand-written fakes, no mocking framework.
- **Event handlers** are only attached through `events.subscribe` / `events.register_custom_event`,
  which keep them referenced (a garbage-collected handler crashes Fusion silently on its next callback).
- **Worker threads never touch the Fusion API.** They only call `fireCustomEvent`, and the
  handler does the work on the main thread.
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

## Layout

```
addin/FusionKeypad/          the folder linked into Fusion's AddIns
  FusionKeypad.py            run/stop only
  lib/contexts.py            the keypad definition (edit this to add tools)
  lib/registry.py            Tool/Context/Root + lookups and definition checks
  lib/navigator.py           the rules that move the keypad
  lib/layout.py              key faces (labels, marks, icons)
  lib/apps.py                what apps are told (definition, state)
  lib/fusion.py              every Fusion read and action
  lib/tracker.py             Fusion events + sketch poll → navigator
  lib/link.py                localhost sockets (keypad, apps), messages → main thread
  lib/lifecycle.py           wiring, start/stop
addin/tests/                 unittest; stubs/adsk is a minimal stand-in
plugin/index.ts, src/        the Logi plugin
docs/keypad-protocol.md      plugin ⇄ add-in messages
docs/app-protocol.md         app ⇄ add-in messages
examples/app_client.py       an example app
```
