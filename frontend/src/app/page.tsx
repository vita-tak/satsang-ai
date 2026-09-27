"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { ChatMessage, ChatRequest, ChatResponse } from "@/types/chat";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendMessage(text: string) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    setError(null);

    try {
      const requestBody: ChatRequest = { message: text, session_id: sessionId };
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!res.ok) {
        const errorBody = await res.json();
        throw new Error(errorBody.detail ?? "Failed to send message.");
      }

      const data: ChatResponse = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) {
      return;
    }
    setInput("");
    sendMessage(trimmed);
  }

  return (
    <div className="flex flex-1 flex-col mx-auto w-full max-w-2xl p-4">
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto mb-4">
        {messages.map((message, index) => (
          <p
            key={index}
            className={
              message.role === "user"
                ? "self-end rounded-lg bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-black"
                : "self-start rounded-lg bg-zinc-100 px-3 py-2 dark:bg-zinc-800"
            }
          >
            {message.content}
          </p>
        ))}
        {isLoading && <p className="text-sm text-zinc-500">Thinking...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask a question..."
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-black"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-black"
        >
          Send
        </button>
      </form>
    </div>
  );
}
