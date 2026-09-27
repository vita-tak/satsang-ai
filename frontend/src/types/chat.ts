export interface ChatRequest {
  message: string;
  session_id: string | null;
}

export interface ChatResponse {
  response: string;
  session_id: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
