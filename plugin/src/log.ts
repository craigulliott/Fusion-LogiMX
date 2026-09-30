import { appendFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

// Logi Plugin Service only shows a Node plugin's console in developer mode, so
// every line also goes to a file: `npm run log` follows it.
export const LOG_PATH =
  process.env.FUSION_KEYPAD_PLUGIN_LOG || join(homedir(), 'Library', 'Logs', 'FusionKeypad-plugin.log');

export function log(text: string): void {
  const line = `${new Date().toISOString()} ${text}`;
  console.log(line);
  try {
    appendFileSync(LOG_PATH, line + '\n');
  } catch {
    // A missing log file must never stop the keys from working.
  }
}
