import net from 'node:net';
import { log } from './log.ts';
import type { KeysMessage, PressMessage } from './protocol.ts';

const RETRY_MS = 1000;

type Handlers = {
  onKeys(message: KeysMessage): void;
  onDisconnect(): void;
};

export type AddinLink = {
  send(message: PressMessage): void;
  close(): void;
};

/**
 * Keeps a connection to the Fusion add-in on 127.0.0.1 (one JSON message per
 * line, see docs/protocol.md), retrying every second while nothing listens.
 */
export function connectToAddin(port: number, handlers: Handlers): AddinLink {
  let socket: net.Socket | null = null;
  let connected = false;
  let closed = false;
  let waitingLogged = false;
  let retry: NodeJS.Timeout | undefined;

  function open(): void {
    let buffer = '';
    const current = net.createConnection({ host: '127.0.0.1', port });
    socket = current;
    current.setEncoding('utf8');
    current.setNoDelay(true);

    current.on('connect', () => {
      connected = true;
      waitingLogged = false;
      log(`add-in connected on 127.0.0.1:${port}`);
    });

    current.on('data', (chunk: string) => {
      buffer += chunk;
      let end: number;
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end).trim();
        buffer = buffer.slice(end + 1);
        if (line) receive(line);
      }
    });

    current.on('error', (error: NodeJS.ErrnoException) => {
      if (!connected && !waitingLogged) {
        log(`add-in not reachable on 127.0.0.1:${port} (${error.code}); retrying every ${RETRY_MS} ms`);
        waitingLogged = true;
      }
    });

    current.on('close', () => {
      socket = null;
      if (connected) {
        connected = false;
        log('add-in disconnected');
        handlers.onDisconnect();
      }
      if (!closed) retry = setTimeout(open, RETRY_MS);
    });
  }

  function receive(line: string): void {
    let message: unknown;
    try {
      message = JSON.parse(line);
    } catch {
      log('ignored a malformed line from the add-in');
      return;
    }
    if (isKeysMessage(message)) handlers.onKeys(message);
    else log(`ignored an unexpected message from the add-in: ${line.slice(0, 80)}`);
  }

  open();

  return {
    send(message) {
      if (connected) socket?.write(JSON.stringify(message) + '\n');
    },
    close() {
      closed = true;
      clearTimeout(retry);
      socket?.destroy();
    },
  };
}

function isKeysMessage(message: unknown): message is KeysMessage {
  const candidate = message as Partial<KeysMessage> | null;
  return candidate?.type === 'keys' && typeof candidate.layout === 'number' && Array.isArray(candidate.keys);
}
