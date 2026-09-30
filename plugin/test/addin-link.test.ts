import assert from 'node:assert/strict';
import net from 'node:net';
import { once } from 'node:events';
import { afterEach, test } from 'node:test';
import { connectToAddin, type AddinLink } from '../src/addin-link.ts';
import type { KeysMessage } from '../src/protocol.ts';

// Each test plays the add-in with a real TCP server on a free local port.

let server: net.Server | undefined;
let link: AddinLink | undefined;

afterEach(async () => {
  link?.close();
  if (server?.listening) {
    server.close();
    await once(server, 'close');
  }
});

async function listen(): Promise<{ port: number; connection: Promise<net.Socket> }> {
  server = net.createServer();
  const connection = once(server, 'connection').then(([socket]) => socket as net.Socket);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return { port: (server.address() as net.AddressInfo).port, connection };
}

function recorder() {
  const keys: KeysMessage[] = [];
  let disconnects = 0;
  let wake = () => {};
  const changed = () => new Promise<void>((resolve) => (wake = resolve));
  return {
    keys,
    disconnects: () => disconnects,
    changed,
    handlers: {
      onKeys(message: KeysMessage) {
        keys.push(message);
        wake();
      },
      onDisconnect() {
        disconnects += 1;
        wake();
      },
    },
  };
}

const keysMessage: KeysMessage = { type: 'keys', layout: 3, keys: [{ label: 'Create ›', image: null }] };

test('delivers keys messages, even when a line arrives in pieces', async () => {
  const { port, connection } = await listen();
  const seen = recorder();
  link = connectToAddin(port, seen.handlers);
  const socket = await connection;

  const line = JSON.stringify(keysMessage) + '\n';
  const received = seen.changed();
  socket.write(line.slice(0, 10));
  socket.write(line.slice(10));
  await received;

  assert.deepEqual(seen.keys, [keysMessage]);
});

test('ignores malformed and unexpected lines and carries on', async () => {
  const { port, connection } = await listen();
  const seen = recorder();
  link = connectToAddin(port, seen.handlers);
  const socket = await connection;

  const received = seen.changed();
  socket.write('not json\n{"type":"surprise"}\n' + JSON.stringify(keysMessage) + '\n');
  await received;

  assert.deepEqual(seen.keys, [keysMessage]);
});

test('sends presses as one JSON line', async () => {
  const { port, connection } = await listen();
  const seen = recorder();
  link = connectToAddin(port, seen.handlers);
  const socket = await connection;
  socket.setEncoding('utf8');
  const received = seen.changed(); // a delivered message proves the client side is connected too
  socket.write(JSON.stringify(keysMessage) + '\n');
  await received;

  link.send({ type: 'press', slot: 4, layout: 3 });
  const [data] = await once(socket, 'data');

  assert.equal(data, '{"type":"press","slot":4,"layout":3}\n');
});

test('reports a lost connection and reconnects when the add-in is back', async () => {
  const { port, connection } = await listen();
  const seen = recorder();
  link = connectToAddin(port, seen.handlers);
  const first = await connection;

  const dropped = seen.changed();
  first.destroy();
  await dropped;
  assert.equal(seen.disconnects(), 1);

  const second = await once(server!, 'connection').then(([socket]) => socket as net.Socket);
  const received = seen.changed();
  second.write(JSON.stringify(keysMessage) + '\n');
  await received;

  assert.deepEqual(seen.keys, [keysMessage]);
});
