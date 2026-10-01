import { useEffect, useRef, useState } from "react";
import { AudioPlayer } from "@/lib/audio-player";
import type { ChatRequest, SpokenAudioFormat, SpokenEvent } from "@/types/chat";

// Spoken answers: with the speaker on, an answer arrives as one stream, its text just before its
// first chunk of audio, so the words and the voice appear together and the rest of the audio
// follows as it is made. With the speaker off nothing is requested, so nothing is spent.

// sessionStorage rather than localStorage, so a new browser session starts with the speaker off.
const SPEAK_STORAGE_KEY = "speakAloud";

export interface SpokenHandlers {
  onText: (event: Extract<SpokenEvent, { type: "text" }>) => void;
  onAudio: (data: string, format: SpokenAudioFormat) => void;
}

export interface Speech {
  isOn: boolean;
  toggle: () => void;
  prime: () => void;
  // Starts a spoken request: ends the one before it, and returns the signal to read the next with.
  beginRequest: () => AbortSignal;
  // The answer's text is on the page, so from here the request only carries audio.
  textShown: () => void;
  push: (data: string, format: SpokenAudioFormat) => void;
  stop: () => void;
}

function readStoredSpeak(): boolean {
  try {
    return sessionStorage.getItem(SPEAK_STORAGE_KEY) === "on";
  } catch {
    // Storage can be unavailable (private browsing); the speaker then starts off.
    return false;
  }
}

function storeSpeak(isOn: boolean) {
  try {
    sessionStorage.setItem(SPEAK_STORAGE_KEY, isOn ? "on" : "off");
  } catch {
    // Storage can be unavailable (private browsing); the choice then lasts for this page only.
  }
}

// Reads the lines of `/api/chat/spoken` as they arrive and hands each event on.
export async function readSpokenAnswer(
  requestBody: ChatRequest,
  signal: AbortSignal,
  { onText, onAudio }: SpokenHandlers,
): Promise<void> {
  const res = await fetch("/api/chat/spoken", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
    signal,
  });
  if (!res.ok || !res.body) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail ?? "Failed to send message.");
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let format: SpokenAudioFormat | null = null;
  let pending = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      return;
    }
    const lines = (pending + value).split("\n");
    pending = lines.pop() ?? "";
    for (const line of lines.filter((text) => text !== "")) {
      const event = JSON.parse(line) as SpokenEvent;
      if (event.type === "text") {
        format = event.audio;
        onText(event);
      } else if (event.type === "audio" && format) {
        onAudio(event.data, format);
      }
    }
  }
}

export function useSpeech(): Speech {
  const [isOn, setIsOn] = useState(false);
  // Read by the stream callbacks: a request sent before the seeker switched the speaker off would
  // otherwise still see it as on.
  const isOnRef = useRef(false);
  const playerRef = useRef<AudioPlayer | null>(null);
  const requestRef = useRef<{ controller: AbortController; hasText: boolean } | null>(null);

  useEffect(() => {
    // sessionStorage only exists in the browser, so this must run post-mount rather than in a lazy
    // useState initializer, or server and client would render different states.
    const stored = readStoredSpeak();
    isOnRef.current = stored;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsOn(stored);
  }, []);

  useEffect(() => {
    return () => {
      requestRef.current?.controller.abort();
      playerRef.current?.close();
    };
  }, []);

  function player(): AudioPlayer {
    playerRef.current ??= new AudioPlayer();
    return playerRef.current;
  }

  function prime() {
    player().prime();
  }

  function beginRequest(): AbortSignal {
    requestRef.current?.controller.abort();
    player().stop();
    const controller = new AbortController();
    requestRef.current = { controller, hasText: false };
    return controller.signal;
  }

  function textShown() {
    const request = requestRef.current;
    if (!request) {
      return;
    }
    request.hasText = true;
    // Switched off while the answer was on its way: the answer was kept, the audio is not wanted.
    if (!isOnRef.current) {
      request.controller.abort();
    }
  }

  function push(data: string, format: SpokenAudioFormat) {
    if (isOnRef.current) {
      player().push(data, format);
    }
  }

  // Ends the sound and, once the text is on the page, the request that still carries audio. A
  // request still waiting for its text is left alone: the answer must not be lost.
  function stop() {
    playerRef.current?.stop();
    const request = requestRef.current;
    if (request?.hasText) {
      request.controller.abort();
      requestRef.current = null;
    }
  }

  function toggle() {
    const next = !isOn;
    isOnRef.current = next;
    setIsOn(next);
    storeSpeak(next);
    if (next) {
      prime();
    } else {
      stop();
    }
  }

  return { isOn, toggle, prime, beginRequest, textShown, push, stop };
}
