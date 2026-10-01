import type { FormEvent, KeyboardEvent, RefObject } from "react";
import { animate } from "framer-motion";
import type { Transition } from "framer-motion";
import { DictationNotice } from "@/components/composer/dictation-notice";
import { MicButton } from "@/components/composer/mic-button";
import { SpeakerButton } from "@/components/composer/speaker-button";
import { appendTranscript, useDictation } from "@/lib/dictation";
import type { DictationStatus } from "@/lib/dictation";
import { EASE_BREATH } from "@/lib/motion";
import { isTouchScreen } from "@/lib/touch";

function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
  const isPlainEnter = event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing;
  if (isPlainEnter) {
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }
}

interface ComposerProps {
  value: string;
  canSubmit: boolean;
  isSpeakerOn: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  onToggleSpeaker: () => void;
  onChange: (value: string) => void;
  onFocus: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

const TRANSCRIPT_FADE: Transition = { duration: 0.6, ease: EASE_BREATH };

// The field is made clear first: the new text is drawn on the next frame, before the animation's
// own first frame, and would show for that frame at full strength.
function fadeIn(element: HTMLElement) {
  element.style.opacity = "0";
  animate(element, { opacity: [0, 1] }, TRANSCRIPT_FADE);
}

const PLACEHOLDER: Record<DictationStatus, string> = {
  idle: "Ask a question…",
  recording: "Listening…",
  transcribing: "Transcribing…",
};

// Read out by screen readers; the placeholder above is only there while the field is empty.
const ANNOUNCEMENT: Record<DictationStatus, string> = {
  idle: "",
  recording: "Listening",
  transcribing: "Transcribing",
};

export function Composer({
  value,
  canSubmit,
  isSpeakerOn,
  inputRef,
  onToggleSpeaker,
  onChange,
  onFocus,
  onSubmit,
}: ComposerProps) {
  const dictation = useDictation({
    onTranscript: (text) => {
      // A textarea cannot fade part of its text, so the words fade in only when they are all there is.
      const isFieldEmpty = value.trim() === "";
      onChange(appendTranscript(value, text));
      if (isFieldEmpty && inputRef.current) {
        fadeIn(inputRef.current);
      }
      if (!isTouchScreen()) {
        inputRef.current?.focus();
      }
    },
  });

  // Sending takes over from a recording or a transcript still on its way: the field as it is goes.
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    if (canSubmit) {
      dictation.cancel();
    }
    onSubmit(event);
  }

  function handleChange(text: string) {
    dictation.dismissNotice();
    onChange(text);
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="mx-auto flex w-full max-w-measure items-end gap-4 border-b border-rule transition-colors duration-500 ease-breath focus-within:border-accent">
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <textarea
          id="question"
          name="question"
          ref={inputRef}
          rows={1}
          value={value}
          onChange={(event) => handleChange(event.target.value)}
          onFocus={onFocus}
          onKeyDown={submitOnEnter}
          autoComplete="off"
          placeholder={PLACEHOLDER[dictation.status]}
          enterKeyHint="send"
          className="field-sizing-content max-h-[40dvh] min-w-0 flex-1 resize-none bg-transparent py-3 text-body text-ink caret-accent sm:text-body-lg placeholder:text-ink-faint focus:outline-none"
        />
        <div className="flex shrink-0">
          <SpeakerButton isOn={isSpeakerOn} onClick={onToggleSpeaker} />
          {dictation.isSupported ? (
            <MicButton status={dictation.status} onClick={dictation.toggle} />
          ) : null}
          <button
            type="submit"
            disabled={!canSubmit}
            className="min-h-11 min-w-11 shrink-0 cursor-pointer text-right text-label text-accent uppercase decoration-1 underline-offset-4 transition-colors duration-500 ease-breath enabled:hover:underline disabled:cursor-default disabled:text-ink-faint"
          >
            Ask
          </button>
        </div>
      </div>
      <p role="status" className="sr-only">
        {ANNOUNCEMENT[dictation.status]}
      </p>
      {dictation.notice ? <DictationNotice message={dictation.notice} /> : null}
    </form>
  );
}
