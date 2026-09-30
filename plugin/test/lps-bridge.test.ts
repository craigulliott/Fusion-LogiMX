import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import type { PluginSDK } from '@logitech/plugin-sdk';
import { installBridge } from '../src/lps-bridge.ts';
import { SlotAction } from '../src/slots.ts';

type Sent = { id: number; name: string; messageType: string; data?: unknown; parameters?: { actionName: string } };

/** Stands in for the SDK internals the bridge hooks: its WebSocket client and message handler. */
function fakeSdk() {
  const sent: Sent[] = [];
  const passedToSdk: string[] = [];
  let receive: (data: Buffer) => void = () => {};
  const sdk = {
    _client: {
      onMessage(handler: (data: Buffer) => void) {
        receive = handler;
      },
      onClose() {},
      sendMessage(message: Sent) {
        sent.push(message);
      },
    },
    async _handleMessage(data: Buffer) {
      passedToSdk.push(JSON.parse(data.toString('utf8')).name);
    },
  };
  return {
    sdk: sdk as unknown as PluginSDK,
    sent,
    passedToSdk,
    deliver: (message: object) => receive(Buffer.from(JSON.stringify(message))),
  };
}

const request = (id: number, name: string, actionName = '') => ({
  id,
  name,
  messageType: 'Request',
  parameters: { pluginName: 'FusionKeypad', actionName, actionParameter: null },
});

const settle = () => new Promise((resolve) => setImmediate(resolve));

let slots: SlotAction[];

beforeEach(() => {
  slots = [new SlotAction(0, () => {}), new SlotAction(1, () => {})];
});

test('answers image and text requests for its keys with their current faces', () => {
  const { sdk, sent, deliver } = fakeSdk();
  installBridge(sdk, slots);
  slots[0].show({ label: 'Circle ›', image: 'PNGDATA' });

  deliver(request(7, 'GetActionImage', 'fusion_key_1'));
  deliver(request(8, 'GetActionText', 'fusion_key_1'));
  deliver(request(9, 'GetActionImage', 'fusion_key_2'));

  assert.deepEqual(
    sent.map(({ id, messageType, data }) => ({ id, messageType, data })),
    [
      { id: 7, messageType: 'Response', data: { image: 'PNGDATA' } },
      { id: 8, messageType: 'Response', data: { text: 'Circle ›' } },
      { id: 9, messageType: 'Response', data: null },
    ],
  );
});

test('answers a blank label with a zero-width space, because the service replaces empty text', () => {
  const { sdk, sent, deliver } = fakeSdk();
  installBridge(sdk, slots);

  deliver(request(1, 'GetActionText', 'fusion_key_2'));

  assert.deepEqual(sent[0].data, { text: '​' });
});

test('passes every other message on to the SDK', () => {
  const { sdk, sent, passedToSdk, deliver } = fakeSdk();
  installBridge(sdk, slots);

  deliver(request(1, 'ExecuteCommand', 'fusion_key_1'));
  deliver(request(2, 'GetActionImage', 'some_other_action'));
  deliver({ id: 3, name: 'InitConnection', messageType: 'Response' });

  assert.deepEqual(passedToSdk, ['ExecuteCommand', 'GetActionImage', 'InitConnection']);
  assert.equal(sent.length, 0);
});

test('sends no redraw events until the service has the action list, then repaints every key', async () => {
  const { sdk, sent, deliver } = fakeSdk();
  const bridge = installBridge(sdk, slots);

  bridge.refresh([slots[0].show({ label: 'early', image: null })]);
  assert.equal(sent.length, 0);

  deliver(request(1, 'GetActionList'));
  await settle();

  assert.deepEqual(
    sent.map(({ name, parameters }) => `${name} ${parameters?.actionName}`),
    [
      'ActionImageChanged fusion_key_1',
      'ActionTextChanged fusion_key_1',
      'ActionImageChanged fusion_key_2',
      'ActionTextChanged fusion_key_2',
    ],
  );
});

test('redraws only the parts of a key that changed', async () => {
  const { sdk, sent, deliver } = fakeSdk();
  const bridge = installBridge(sdk, slots);
  deliver(request(1, 'GetActionList'));
  await settle();
  sent.length = 0;

  bridge.refresh([
    slots[0].show({ label: 'Line', image: null }),
    slots[1].show({ label: '', image: null }),
  ]);

  assert.deepEqual(
    sent.map(({ name, parameters }) => `${name} ${parameters?.actionName}`),
    ['ActionTextChanged fusion_key_1'],
  );
});

test('degrades to a bridge that does nothing when the SDK internals are missing', () => {
  const bridge = installBridge({} as PluginSDK, slots);

  assert.doesNotThrow(() => bridge.refresh([slots[0].show({ label: 'x', image: null })]));
});
