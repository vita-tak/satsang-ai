import type { ResponseMode } from "@/lib/mode";

export interface ChatRequest {
  message: string;
  session_id: string | null;
  mode: ResponseMode;
}

export interface ChatResponse {
  response: string;
  session_id: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// The lines of `POST /api/chat/spoken`, mirroring `ai-service/src/api/spoken.py`: the answer once,
// then its audio in chunks, then done. The text comes just before the first chunk, so the answer
// and the voice arrive together; `audio` is null when no sound follows.
export interface SpokenAudioFormat {
  mime_type: string;
  sample_rate: number;
}

export type SpokenEvent =
  | { type: "text"; response: string; session_id: string; audio: SpokenAudioFormat | null }
  | { type: "audio"; data: string }
  | { type: "done" };
