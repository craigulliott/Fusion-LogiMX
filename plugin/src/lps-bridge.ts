import type { PluginSDK } from '@logitech/plugin-sdk';
import { log } from './log.ts';
import type { FaceChange, SlotAction } from './slots.ts';

// The public SDK (@logitech/plugin-sdk 0.1.1) answers every GetActionImage
// request with null and never tells the service that a key changed. The service
// itself supports both for Node plugins, the same way it does for C# plugins.
// This answers GetActionImage/GetActionText on the SDK's own WebSocket and sends
// ActionImageChanged/ActionTextChanged events. The technique comes from
// github.com/niklasberglund/herdr-logi-plugin (docs/dynamic-tile-images.md).
//
// This is the only module that relies on private SDK members, which is why
// package.json pins the SDK to an exact version.

type ServiceMessage = { id: number; name: string; messageType: string; parameters?: { actionName?: string } };

type SdkInternals = {
  _client?: {
    onMessage?(handler: (data: Buffer) => void): void;
    onClose?(handler: () => void): void;
    sendMessage?(message: unknown): void;
  };
  _handleMessage?(data: Buffer): Promise<void>;
};

export type Bridge = {
  /** Tell the service to redraw the parts of each slot that changed. */
  refresh(changes: FaceChange[]): void;
  /** Called when the service connection closes. */
  onClose(handler: () => void): void;
};

export function installBridge(sdk: PluginSDK, slots: SlotAction[]): Bridge {
  const internals = sdk as unknown as SdkInternals;
  const client = internals._client;
  if (
    typeof client?.onMessage !== 'function' ||
    typeof client.onClose !== 'function' ||
    typeof client.sendMessage !== 'function' ||
    typeof internals._handleMessage !== 'function'
  ) {
    log('FAIL SDK internals have changed, so keys cannot be redrawn. Pin @logitech/plugin-sdk to 0.1.1.');
    return { refresh() {}, onClose() {} };
  }
  if (!process.env.LPS_PLUGIN_NAME) {
    log('WARN LPS_PLUGIN_NAME is not set; the service ignores redraw events without it.');
  }

  const send = client.sendMessage.bind(client);
  const onClose = client.onClose.bind(client);
  const passToSdk = internals._handleMessage.bind(sdk);
  const byName = new Map(slots.map((slot) => [slot.name, slot]));
  let ready = false; // true once the service has our action list

  // Replaces the SDK's own handler (its client keeps only one), so every
  // message this does not answer is passed on to the SDK.
  client.onMessage((data) => {
    let message: ServiceMessage;
    try {
      message = JSON.parse(data.toString('utf8'));
    } catch {
      void passToSdk(data);
      return;
    }
    const slot = message.messageType === 'Request' ? byName.get(message.parameters?.actionName ?? '') : undefined;
    if (slot && message.name === 'GetActionImage') return reply(message, slot.imageData());
    if (slot && message.name === 'GetActionText') return reply(message, slot.textData());

    const handled = passToSdk(data);
    // The service keeps key faces from earlier runs and only asks again when
    // told, so repaint every key once it has our action list.
    if (message.name === 'GetActionList' && message.messageType === 'Request') {
      void handled.then(() => {
        ready = true;
        refresh(slots.map((slot) => ({ slot, text: true, image: true })));
      });
    }
  });

  function reply(request: ServiceMessage, data: unknown): void {
    send({ id: request.id, name: request.name, messageType: 'Response', data, failed: false, errorMessage: '', errorCode: 0 });
  }

  function notify(name: 'ActionImageChanged' | 'ActionTextChanged', slot: SlotAction): void {
    send({
      id: 0,
      name,
      messageType: 'Event',
      parameters: { pluginName: process.env.LPS_PLUGIN_NAME, actionName: slot.name, actionParameter: null },
    });
  }

  function refresh(changes: FaceChange[]): void {
    if (!ready) return; // the repaint after GetActionList covers these
    for (const { slot, text, image } of changes) {
      if (image) notify('ActionImageChanged', slot);
      if (text) notify('ActionTextChanged', slot);
    }
  }

  return { refresh, onClose };
}
