import {
  useEffect,
  useEffectEvent,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import type { RefObject } from "react";

// Voice input for a text field, on the browser's Web Speech API. What is said is written into the
// field as it is recognised and nothing is ever sent: the field stays an ordinary controlled field
// that the seeker reads, edits and sends by hand.

export type VoiceStatus = "idle" | "recording" | "processing";

// TypeScript's DOM types have the Web Speech result types but not the recognizer, its events or the
// window constructors, so the small part used here is declared locally instead of adding a types
// package.
interface RecognizerResultEvent extends Event {
  readonly results: SpeechRecognitionResultList;
}

interface RecognizerErrorEvent extends Event {
  readonly error: string;
}

interface Recognizer {
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognizerResultEvent) => void) | null;
  onerror: ((event: RecognizerErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

type RecognizerConstructor = new () => Recognizer;

type SpeechWindow = Window & {
  SpeechRecognition?: RecognizerConstructor;
  webkitSpeechRecognition?: RecognizerConstructor;
};

const BLOCKED_NOTICE =
  "Microphone access is blocked. Allow it in your browser or device settings to speak.";
const UNAVAILABLE_NOTICE = "Voice input is not available right now";

// The seeker or the browser said no to the microphone or to speech recognition.
const BLOCKED_ERRORS = ["not-allowed", "service-not-allowed"];
// Silence and a deliberate abort are not failures: the mic returns to rest without a message.
const QUIET_ERRORS = ["no-speech", "aborted"];

function noticeFor(error: string): string | null {
  if (BLOCKED_ERRORS.includes(error)) {
    return BLOCKED_NOTICE;
  }
  return QUIET_ERRORS.includes(error) ? null : `${UNAVAILABLE_NOTICE} (${error})`;
}

function getRecognizerConstructor(): RecognizerConstructor | undefined {
  const speechWindow = window as SpeechWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

// Support never changes while the page is open, so there is nothing to subscribe to. The store only
// lets the server render "unsupported" and the client correct it after hydration.
function subscribeToNothing(): () => void {
  return () => {};
}

function supportsRecognition(): boolean {
  return getRecognizerConstructor() !== undefined;
}

function doesNotSupportRecognition(): boolean {
  return false;
}

// Phone browsers do not keep a continuous session reliably and are known to repeat earlier results
// in one, so a touch screen listens for a single utterance per tap.
function listensContinuously(): boolean {
  return !window.matchMedia("(pointer: coarse)").matches;
}

// Everything said in the session so far, in order: finished phrases and the one still being spoken.
// Rebuilding it from the whole list on every event lets an interim result be replaced by the next
// one, and by its final, without anything being appended twice.
function transcriptOf(results: SpeechRecognitionResultList): string {
  const phrases = Array.from(results, (result) => result[0].transcript);
  return phrases.join(" ").replace(/\s+/g, " ").trim();
}

function appendTranscript(base: string, transcript: string): string {
  if (transcript === "") {
    return base;
  }
  const needsSpace = base !== "" && !/\s$/.test(base);
  return needsSpace ? `${base} ${transcript}` : `${base}${transcript}`;
}

// Ends a session without waiting for it: what it might still say must not reach the field or show a
// notice. Its end event is left attached so the hook can return to rest.
function discard(recognizer: Recognizer) {
  recognizer.onresult = null;
  recognizer.onerror = null;
  recognizer.abort();
}

interface VoiceInputOptions {
  fieldRef: RefObject<HTMLTextAreaElement | null>;
  value: string;
  // Captured when recording starts, so it should be a stable setter such as a useState setter.
  onChange: (value: string) => void;
}

export function useVoiceInput({ fieldRef, value, onChange }: VoiceInputOptions) {
  const isSupported = useSyncExternalStore(
    subscribeToNothing,
    supportsRecognition,
    doesNotSupportRecognition,
  );
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const recognizerRef = useRef<Recognizer | null>(null);
  // What the field held when recording began, and what the voice last wrote into it.
  const baseRef = useRef("");
  const lastWrittenRef = useRef("");

  useEffect(() => {
    // The intro's composer unmounts when the first question is sent; nothing may go on listening.
    return () => {
      if (recognizerRef.current !== null) {
        discard(recognizerRef.current);
      }
    };
  }, []);

  // While recording, the field belongs to the voice. Any other change to it (typing, a chosen
  // example question, or sending, which clears it) means the seeker has taken over, so listening
  // stops and the field keeps whatever it holds. It also keeps a sent question from reappearing.
  useLayoutEffect(() => {
    if (recognizerRef.current !== null && value !== lastWrittenRef.current) {
      discard(recognizerRef.current);
    }
  }, [value]);

  useEffect(() => {
    const field = fieldRef.current;
    if (status === "recording" && field !== null) {
      // The field stops growing at its max height, so keep the newest words in view.
      field.scrollTop = field.scrollHeight;
    }
  }, [fieldRef, status, value]);

  useEffect(() => {
    if (notice === null) {
      return;
    }
    // The next interaction anywhere dismisses the notice. A click rather than a pointerdown: the
    // layout moves when it goes, and that must not happen between a press and its release.
    const dismiss = () => setNotice(null);
    document.addEventListener("click", dismiss);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("click", dismiss);
      document.removeEventListener("keydown", dismiss);
    };
  }, [notice]);

  function start() {
    const RecognizerClass = getRecognizerConstructor();
    if (RecognizerClass === undefined) {
      return;
    }
    const recognizer = new RecognizerClass();
    recognizer.continuous = listensContinuously();
    recognizer.interimResults = true;
    recognizer.onresult = (event) => {
      const next = appendTranscript(baseRef.current, transcriptOf(event.results));
      lastWrittenRef.current = next;
      onChange(next);
    };
    recognizer.onerror = (event) => {
      const message = noticeFor(event.error);
      if (message !== null) {
        setNotice(message);
      }
    };
    recognizer.onend = () => {
      // A late end from a session that was already replaced must not reset the current one.
      if (recognizerRef.current === recognizer) {
        recognizerRef.current = null;
        setStatus("idle");
      }
    };
    baseRef.current = value;
    lastWrittenRef.current = value;
    recognizerRef.current = recognizer;
    setNotice(null);
    setStatus("recording");
    recognizer.start();
  }

  function stop() {
    // The last words are still being finalised: the field gets them before the session ends.
    recognizerRef.current?.stop();
    setStatus("processing");
  }

  // Not waiting for an end event that a broken browser might never send.
  function endSession() {
    const recognizer = recognizerRef.current;
    recognizerRef.current = null;
    if (recognizer !== null) {
      discard(recognizer);
    }
    setStatus("idle");
  }

  function toggle() {
    if (status === "idle") {
      start();
    } else if (status === "recording") {
      stop();
    } else {
      endSession();
    }
  }

  return { isSupported, status, notice, toggle };
}

interface VoiceShortcutOptions {
  fieldRef: RefObject<HTMLTextAreaElement | null>;
  isEnabled: boolean;
  status: VoiceStatus;
  onToggle: () => void;
}

function isVoiceShortcut(event: KeyboardEvent): boolean {
  return (
    event.ctrlKey &&
    event.shiftKey &&
    !event.altKey &&
    !event.metaKey &&
    !event.repeat &&
    event.key.toLowerCase() === "v"
  );
}

// Ctrl+Shift+V toggles recording from anywhere on the page, except in the field: there it is the
// browser's paste-as-plain-text, which stays. Only a recording that is running can be stopped
// from the field.
export function useVoiceShortcut({ fieldRef, isEnabled, status, onToggle }: VoiceShortcutOptions) {
  const handleKeyDown = useEffectEvent((event: KeyboardEvent) => {
    if (!isVoiceShortcut(event)) {
      return;
    }
    const isInField = event.target === fieldRef.current;
    if (isInField && status !== "recording") {
      return;
    }
    event.preventDefault();
    onToggle();
  });

  useEffect(() => {
    if (!isEnabled) {
      return;
    }
    const listen = (event: KeyboardEvent) => handleKeyDown(event);
    document.addEventListener("keydown", listen);
    return () => document.removeEventListener("keydown", listen);
  }, [isEnabled]);
}
