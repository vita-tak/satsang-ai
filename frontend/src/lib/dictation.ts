import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { TranscribeResponse } from "@/types/transcribe";

// Dictation for a text field: record the seeker's voice, send it to the backend when the recording
// stops, and hand back the transcript. Nothing is ever sent to the guide: the transcript goes into
// the field for the seeker to read, edit and send by hand.

export type DictationStatus = "idle" | "recording" | "transcribing";

// A longer recording is stopped and transcribed as it is.
const MAX_RECORDING_MS = 3 * 60 * 1000;
// Speech needs little: at this rate three minutes stay under one megabyte.
const AUDIO_BITS_PER_SECOND = 32_000;
// In order of preference; Chrome and Firefox record webm or ogg, Safari mp4.
const RECORDING_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];

const BLOCKED_NOTICE =
  "Microphone access is blocked. Allow it in your browser or device settings to speak.";
const NO_MICROPHONE_NOTICE = "No microphone was found.";
const UNAVAILABLE_NOTICE = "Voice input is not available right now.";
const NOTHING_HEARD_NOTICE = "Nothing was heard. Please try again.";
const RATE_LIMITED_NOTICE = "Too many recordings. Please wait a moment and try again.";
const FAILED_NOTICE = "The recording could not be turned into text. Please try again.";

const RATE_LIMITED = 429;

class TranscriptionError extends Error {
  constructor(readonly status: number) {
    super(`Transcription failed with status ${status}.`);
  }
}

interface Session {
  recorder: MediaRecorder;
  stream: MediaStream;
  chunks: Blob[];
  stopTimer: number;
  isDiscarded: boolean;
}

interface DictationOptions {
  onTranscript: (text: string) => void;
}

export interface Dictation {
  isSupported: boolean;
  status: DictationStatus;
  notice: string | null;
  toggle: () => void;
  cancel: () => void;
  dismissNotice: () => void;
}

// Where the transcript goes: after what is already in the field, separated by one space.
export function appendTranscript(current: string, transcript: string): string {
  return current.trim() === "" ? transcript : `${current.trimEnd()} ${transcript}`;
}

function subscribeToNothing(): () => void {
  return () => {};
}

function canRecord(): boolean {
  return Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined";
}

function pickRecordingType(): string | undefined {
  return RECORDING_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

function releaseStream(stream: MediaStream) {
  stream.getTracks().forEach((track) => track.stop());
}

function noticeForMicrophoneError(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return BLOCKED_NOTICE;
  }
  return name === "NotFoundError" ? NO_MICROPHONE_NOTICE : UNAVAILABLE_NOTICE;
}

function noticeForTranscriptionError(error: unknown): string {
  return error instanceof TranscriptionError && error.status === RATE_LIMITED
    ? RATE_LIMITED_NOTICE
    : FAILED_NOTICE;
}

async function requestTranscript(recording: Blob, signal: AbortSignal): Promise<string> {
  const body = new FormData();
  body.append("audio", recording, "recording");
  const res = await fetch("/api/transcribe", { method: "POST", body, signal });
  if (!res.ok) {
    throw new TranscriptionError(res.status);
  }
  const data: TranscribeResponse = await res.json();
  return data.text;
}

// Stops a recording and throws it away, and gives up on a transcript still on its way.
function abandon(session: Session | null, transcription: AbortController | null) {
  if (session) {
    session.isDiscarded = true;
    if (session.recorder.state === "recording") {
      session.recorder.stop();
    }
  }
  transcription?.abort();
}

export function useDictation({ onTranscript }: DictationOptions): Dictation {
  // The server snapshot is false, so there is no hydration mismatch and nothing shows where the
  // browser cannot record.
  const isSupported = useSyncExternalStore(subscribeToNothing, canRecord, () => false);
  const [status, setStatus] = useState<DictationStatus>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const sessionRef = useRef<Session | null>(null);
  const transcriptionRef = useRef<AbortController | null>(null);
  const isAskingRef = useRef(false);
  // Counts the times a recording was asked for or given up, so that a microphone granted after the
  // seeker moved on is released at once instead of being left open.
  const attemptRef = useRef(0);
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  });

  useEffect(() => {
    return () => {
      attemptRef.current += 1;
      abandon(sessionRef.current, transcriptionRef.current);
    };
  }, []);

  async function transcribe(recording: Blob) {
    const controller = new AbortController();
    transcriptionRef.current = controller;
    try {
      const text = await requestTranscript(recording, controller.signal);
      if (text) {
        onTranscriptRef.current(text);
      } else {
        setNotice(NOTHING_HEARD_NOTICE);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setNotice(noticeForTranscriptionError(error));
      }
    } finally {
      if (!controller.signal.aborted) {
        transcriptionRef.current = null;
        setStatus("idle");
      }
    }
  }

  function handleRecorderStopped(session: Session) {
    window.clearTimeout(session.stopTimer);
    releaseStream(session.stream);
    if (sessionRef.current === session) {
      sessionRef.current = null;
    }
    if (!session.isDiscarded) {
      void transcribe(new Blob(session.chunks, { type: session.recorder.mimeType }));
    }
  }

  function stopRecording() {
    const session = sessionRef.current;
    if (session?.recorder.state === "recording") {
      session.recorder.stop();
      setStatus("transcribing");
    }
  }

  function beginRecording(stream: MediaStream) {
    const recorder = new MediaRecorder(stream, {
      mimeType: pickRecordingType(),
      audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
    });
    const session: Session = {
      recorder,
      stream,
      chunks: [],
      stopTimer: window.setTimeout(stopRecording, MAX_RECORDING_MS),
      isDiscarded: false,
    };
    recorder.ondataavailable = (event) => {
      session.chunks.push(event.data);
    };
    recorder.onstop = () => handleRecorderStopped(session);
    sessionRef.current = session;
    recorder.start();
    setStatus("recording");
  }

  async function startRecording() {
    setNotice(null);
    isAskingRef.current = true;
    attemptRef.current += 1;
    const attempt = attemptRef.current;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      setNotice(noticeForMicrophoneError(error));
      return;
    } finally {
      isAskingRef.current = false;
    }
    if (attempt !== attemptRef.current) {
      releaseStream(stream);
      return;
    }
    try {
      beginRecording(stream);
    } catch {
      releaseStream(stream);
      setNotice(UNAVAILABLE_NOTICE);
    }
  }

  // Idle starts a recording, recording stops it and sends it on; a click while the transcript is
  // on its way, or while the browser is still asking for the microphone, does nothing.
  function toggle() {
    if (status === "recording") {
      stopRecording();
    } else if (status === "idle" && !isAskingRef.current) {
      void startRecording();
    }
  }

  function cancel() {
    attemptRef.current += 1;
    abandon(sessionRef.current, transcriptionRef.current);
    transcriptionRef.current = null;
    setStatus("idle");
  }

  return {
    isSupported,
    status,
    notice,
    toggle,
    cancel,
    dismissNotice: () => setNotice(null),
  };
}
