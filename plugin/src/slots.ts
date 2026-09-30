import { CommandAction } from '@logitech/plugin-sdk';
import type { KeyFace } from './protocol.ts';

// The service falls back to the action's display name when a label is empty or
// whitespace; a zero-width space is the only way to get a blank label.
const BLANK_LABEL = '​';

/** Which parts of a slot's face changed, so only those are redrawn. */
export type FaceChange = { slot: SlotAction; text: boolean; image: boolean };

/**
 * One physical key. It knows nothing about Fusion: it shows the face it was
 * last given and reports presses by index.
 */
export class SlotAction extends CommandAction {
  readonly name: string;
  displayName: string;
  description: string;
  readonly groupName = 'Fusion Keys';
  readonly index: number;
  private face: KeyFace = { label: '', image: null };
  private readonly onPress: (index: number) => void;

  constructor(index: number, onPress: (index: number) => void) {
    super();
    this.index = index;
    this.name = `fusion_key_${index + 1}`;
    this.displayName = `Fusion Key ${index + 1}`;
    this.description = `Key ${index + 1} of 9 in reading order. Shows whatever the Fusion Keypad add-in sends.`;
    this.onPress = onPress;
  }

  show(face: KeyFace): FaceChange {
    const change = { slot: this, text: face.label !== this.face.label, image: face.image !== this.face.image };
    this.face = face;
    return change;
  }

  textData(): { text: string } {
    return { text: this.face.label.trim() ? this.face.label : BLANK_LABEL };
  }

  imageData(): { image: string } | null {
    return this.face.image ? { image: this.face.image } : null;
  }

  onKeyDown(): void {
    this.onPress(this.index);
  }
}
