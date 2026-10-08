// Fusion Keypad: a thin Logi plugin. Nine key slots show whatever the Fusion
// add-in sends (docs/keypad-protocol.md) and report presses back; the add-in
// decides everything else.
import { PluginSDK } from '@logitech/plugin-sdk';
import { connectToAddin } from './src/addin-link.ts';
import { installBridge } from './src/lps-bridge.ts';
import { LOG_PATH, log } from './src/log.ts';
import { PORT, SLOT_COUNT, type KeyFace } from './src/protocol.ts';
import { SlotAction } from './src/slots.ts';

const BLANK: KeyFace = { label: '', image: null };
const OFFLINE: KeyFace[] = [{ label: 'Fusion add-in offline', image: null }];

const slots = Array.from({ length: SLOT_COUNT }, (_, index) => new SlotAction(index, onPress));
const sdk = new PluginSDK();
for (const slot of slots) sdk.registerAction(slot);
const bridge = installBridge(sdk, slots);

let layout: number | null = null; // layout of the keys on screen; null while offline

const addin = connectToAddin(PORT, {
  onKeys(message) {
    layout = message.layout;
    show(message.keys);
  },
  onDisconnect() {
    layout = null;
    show(OFFLINE);
  },
});

function onPress(slot: number): void {
  if (layout !== null) addin.send({ type: 'press', slot, layout });
}

function show(faces: KeyFace[]): void {
  bridge.refresh(slots.map((slot, index) => slot.show(faces[index] ?? BLANK)));
}

// The add-in link's retry timer would keep this process alive after the
// service stops the plugin, so leave when the service connection closes.
bridge.onClose(() => {
  log('Logi Plugin Service disconnected; exiting');
  process.exit(0);
});

log(`START ${process.env.LPS_PLUGIN_NAME ?? '(LPS_PLUGIN_NAME unset)'} on Node ${process.version}; log ${LOG_PATH}`);
show(OFFLINE);
try {
  await sdk.connect();
} catch (error) {
  log(`FAIL could not connect to Logi Plugin Service: ${error}`);
  process.exit(1);
}
