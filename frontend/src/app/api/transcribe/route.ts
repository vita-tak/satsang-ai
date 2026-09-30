import { NextRequest, NextResponse } from "next/server";
import type { TranscribeResponse } from "@/types/transcribe";

const RATE_LIMITED = 429;

async function readRecording(request: NextRequest): Promise<File | null> {
  try {
    const form = await request.formData();
    const audio = form.get("audio");
    return audio instanceof File && audio.size > 0 ? audio : null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  const recording = await readRecording(request);
  if (!recording) {
    return NextResponse.json({ detail: "The recording is empty." }, { status: 400 });
  }

  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return NextResponse.json({ detail: "API_URL is not configured." }, { status: 500 });
  }

  const body = new FormData();
  body.append("audio", recording, "recording");

  try {
    const upstreamResponse = await fetch(`${apiUrl}/transcribe`, { method: "POST", body });

    if (upstreamResponse.status === RATE_LIMITED) {
      return NextResponse.json({ detail: "Too many recordings." }, { status: RATE_LIMITED });
    }
    if (!upstreamResponse.ok) {
      throw new Error(`Upstream transcription service responded with status ${upstreamResponse.status}.`);
    }

    const data = (await upstreamResponse.json()) as TranscribeResponse;
    return NextResponse.json(data);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Failed to reach the transcription service.";
    return NextResponse.json({ detail }, { status: 502 });
  }
}
