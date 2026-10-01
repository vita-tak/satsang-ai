import { DEFAULT_MODE, isResponseMode } from "@/lib/mode";
import type { ChatRequest } from "@/types/chat";

// What the two chat routes (plain and spoken) share: checking the body before any upstream call,
// and filling in what the client left out.

export function validateChatRequest(body: Partial<ChatRequest>): string | null {
  if (!body.message || !body.message.trim()) {
    return "Message cannot be empty.";
  }
  if (body.mode !== undefined && !isResponseMode(body.mode)) {
    return "Unknown response mode.";
  }
  return null;
}

// Call only after `validateChatRequest` passed.
export function toBackendRequest(body: Partial<ChatRequest>): ChatRequest {
  return {
    message: body.message as string,
    session_id: body.session_id ?? crypto.randomUUID(),
    mode: body.mode ?? DEFAULT_MODE,
  };
}
