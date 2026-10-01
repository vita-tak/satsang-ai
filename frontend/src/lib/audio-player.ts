import type { SpokenAudioFormat } from "@/types/chat";

// Plays speech while it is still being made. Each chunk that arrives is decoded and scheduled to
// start exactly where the one before it ends, so the pieces play as one voice with no gap, and the
// first sound starts as soon as the first chunk is here.

// The first chunk starts a moment after it arrives, so it is never scheduled in the past.
const START_LEAD_SECONDS = 0.08;

// The only format the backend streams: 16-bit little-endian PCM.
const L16 = "audio/l16";

function base64ToBytes(data: string): Uint8Array {
  return Uint8Array.from(atob(data), (character) => character.charCodeAt(0));
}

type Samples = Float32Array<ArrayBuffer>;

export class AudioPlayer {
  private context: AudioContext | null = null;
  private nextStart = 0;
  private sources = new Set<AudioBufferSourceNode>();
  // A chunk may end between the two bytes of a 16-bit sample; the first byte waits for the next.
  private spareByte: number | null = null;

  // Browsers only let audio start from a tap, so this runs inside one (iOS Safari is the strict
  // one), well before any sound exists.
  prime(): void {
    this.context ??= new AudioContext();
    this.context.resume().catch(() => {});
  }

  push(data: string, format: SpokenAudioFormat): void {
    const context = this.context;
    if (!context) {
      return;
    }
    const samples = this.decode(base64ToBytes(data), format.mime_type);
    if (samples.length === 0) {
      return;
    }
    const buffer = context.createBuffer(1, samples.length, format.sample_rate);
    buffer.copyToChannel(samples, 0);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    source.onended = () => this.sources.delete(source);
    // After a stall the next chunk starts from now rather than in the past.
    const startAt = Math.max(context.currentTime + START_LEAD_SECONDS, this.nextStart);
    source.start(startAt);
    this.nextStart = startAt + buffer.duration;
    this.sources.add(source);
  }

  // Silences what is playing and what is scheduled. The context stays, so it stays primed.
  stop(): void {
    this.sources.forEach((source) => {
      source.onended = null;
      source.stop();
      source.disconnect();
    });
    this.sources.clear();
    this.nextStart = 0;
    this.spareByte = null;
  }

  close(): void {
    this.stop();
    this.context?.close().catch(() => {});
    this.context = null;
  }

  private decode(chunk: Uint8Array, mimeType: string): Samples {
    return mimeType === L16 ? this.decodeL16(chunk) : new Float32Array(0);
  }

  private decodeL16(chunk: Uint8Array): Samples {
    let bytes = chunk;
    if (this.spareByte !== null) {
      bytes = new Uint8Array(chunk.length + 1);
      bytes[0] = this.spareByte;
      bytes.set(chunk, 1);
      this.spareByte = null;
    }
    if (bytes.length % 2 === 1) {
      this.spareByte = bytes[bytes.length - 1];
      bytes = bytes.subarray(0, bytes.length - 1);
    }
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    return Float32Array.from(
      { length: bytes.length / 2 },
      (_, index) => view.getInt16(index * 2, true) / 32768,
    );
  }
}
