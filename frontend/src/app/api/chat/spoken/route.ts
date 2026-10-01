import { NextRequest, NextResponse } from "next/server";
import { toBackendRequest, validateChatRequest } from "@/lib/chat-request";
import type { ChatRequest } from "@/types/chat";

// The answer and its audio, as lines of JSON. The body is passed on as it arrives: nothing here
// reads it, and `no-transform` keeps the server's compression from holding chunks back to fill a
// block, which would delay the first sound.
const STREAM_HEADERS = {
  "Content-Type": "application/x-ndjson",
  "Cache-Control": "no-cache, no-transform",
  "X-Accel-Buffering": "no",
};

export async function POST(request: NextRequest) {
  const body = (await request.json()) as Partial<ChatRequest>;

  const validationError = validateChatRequest(body);
  if (validationError) {
    return NextResponse.json({ detail: validationError }, { status: 400 });
  }

  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return NextResponse.json({ detail: "API_URL is not configured." }, { status: 500 });
  }

  try {
    const upstreamResponse = await fetch(`${apiUrl}/chat/spoken`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toBackendRequest(body)),
      // The seeker leaving or asking again ends the upstream request, and so the speech.
      signal: request.signal,
    });

    if (!upstreamResponse.ok || !upstreamResponse.body) {
      throw new Error(`Upstream chat service responded with status ${upstreamResponse.status}.`);
    }

    return new Response(upstreamResponse.body, { headers: STREAM_HEADERS });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Failed to reach the chat service.";
    return NextResponse.json({ detail }, { status: 502 });
  }
}
