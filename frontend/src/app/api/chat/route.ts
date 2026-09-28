import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_MODE, isResponseMode } from "@/lib/mode";
import type { ChatRequest, ChatResponse } from "@/types/chat";

function validateMessage(body: Partial<ChatRequest>): string | null {
  if (!body.message || !body.message.trim()) {
    return "Message cannot be empty.";
  }
  return null;
}

function validateMode(body: Partial<ChatRequest>): string | null {
  if (body.mode === undefined || isResponseMode(body.mode)) {
    return null;
  }
  return "Unknown response mode.";
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as Partial<ChatRequest>;

  const validationError = validateMessage(body) ?? validateMode(body);
  if (validationError) {
    return NextResponse.json({ detail: validationError }, { status: 400 });
  }

  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return NextResponse.json({ detail: "API_URL is not configured." }, { status: 500 });
  }

  const requestBody: ChatRequest = {
    message: body.message as string,
    session_id: body.session_id ?? crypto.randomUUID(),
    mode: body.mode ?? DEFAULT_MODE,
  };

  try {
    const upstreamResponse = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    if (!upstreamResponse.ok) {
      throw new Error(`Upstream chat service responded with status ${upstreamResponse.status}.`);
    }

    const data = (await upstreamResponse.json()) as ChatResponse;
    return NextResponse.json(data);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Failed to reach the chat service.";
    return NextResponse.json({ detail }, { status: 502 });
  }
}
