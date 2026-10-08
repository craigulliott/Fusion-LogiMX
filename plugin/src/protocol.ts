// Messages between this plugin and the Fusion add-in. docs/protocol.md is the
// specification; keep the two in step.

export const PORT = 47823;
export const SLOT_COUNT = 9;

export type KeyFace = { label: string; image: string | null };

/** Add-in → plugin: what all nine keys show. */
export type KeysMessage = { type: 'keys'; layout: number; keys: KeyFace[] };

/** Plugin → add-in: a key was pressed. */
export type PressMessage = { type: 'press'; slot: number; layout: number };
