import { useState } from "react";
import type { ResponseMode } from "@/lib/mode";
import { readSpokenAnswer } from "@/lib/speech";
import type { Speech } from "@/lib/speech";
import type { ChatMessage, ChatRequest, ChatResponse } from "@/types/chat";

// The conversation with the guide: what was asked and answered, and the request for each answer,
// plain or spoken depending on the speaker.

export interface Exchange {
  question: string;
  answer: string | null;
}

export interface Chat {
  exchanges: Exchange[];
  isLoading: boolean;
  error: string | null;
  send: (text: string, mode: ResponseMode) => Promise<void>;
}

function toExchanges(messages: ChatMessage[]): Exchange[] {
  const exchanges: Exchange[] = [];
  for (const message of messages) {
    if (message.role === "user") {
      exchanges.push({ question: message.content, answer: null });
    } else {
      exchanges[exchanges.length - 1].answer = message.content;
    }
  }
  return exchanges;
}

type ShowAnswer = (content: string, sessionId: string) => void;

async function receivePlain(requestBody: ChatRequest, showAnswer: ShowAnswer) {
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
  showAnswer(data.response, data.session_id);
}

// The answer is shown when its text arrives, which is when the first sound does too.
async function receiveSpoken(requestBody: ChatRequest, speech: Speech, showAnswer: ShowAnswer) {
  const signal = speech.beginRequest();
  await readSpokenAnswer(requestBody, signal, {
    onText: (event) => {
      showAnswer(event.response, event.session_id);
      speech.textShown();
    },
    onAudio: speech.push,
  });
}

export function useChat(speech: Speech): Chat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(text: string, mode: ResponseMode) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    setError(null);

    let hasAnswer = false;
    // The answer ends the wait. With the speaker on its audio is still arriving after this.
    function showAnswer(content: string, answerSessionId: string) {
      hasAnswer = true;
      setSessionId(answerSessionId);
      setMessages((prev) => [...prev, { role: "assistant", content }]);
      setIsLoading(false);
    }

    try {
      const requestBody: ChatRequest = { message: text, session_id: sessionId, mode };
      if (speech.isOn) {
        await receiveSpoken(requestBody, speech, showAnswer);
      } else {
        await receivePlain(requestBody, showAnswer);
      }
    } catch (err) {
      // Once the answer is on the page, a failure of its audio is not reported: the text is there.
      if (!hasAnswer) {
        setError(err instanceof Error ? err.message : "Something went wrong.");
        setIsLoading(false);
      }
    }
  }

  return { exchanges: toExchanges(messages), isLoading, error, send };
}
