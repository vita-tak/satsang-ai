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
