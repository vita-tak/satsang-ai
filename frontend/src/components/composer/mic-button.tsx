import type { DictationStatus } from "@/lib/dictation";

// Idle is quiet ink; recording is ember, with the capsule filled so the state does not rest on
// colour or motion alone. Transcribing is quiet ink again and breathes like "Answering" while the
// words are on their way.
const MIC_COLOR: Record<DictationStatus, string> = {
  idle: "text-ink-faint hover:text-ink",
  recording: "text-accent",
  transcribing: "text-ink-faint",
};

interface MicButtonProps {
  status: DictationStatus;
  onClick: () => void;
}

export function MicButton({ status, onClick }: MicButtonProps) {
  const isRecording = status === "recording";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Speak your question"
      aria-pressed={isRecording}
      aria-disabled={status === "transcribing"}
      className={`${MIC_COLOR[status]} grid size-11 shrink-0 cursor-pointer place-items-center transition-colors duration-500 ease-breath`}
    >
      {/* The pulse is on the wrapper, not the SVG or the button, so the focus ring stays steady. */}
      <span className={status === "idle" ? "block" : "block animate-breathe"}>
        <svg viewBox="0 0 20 20" className="size-4.5" aria-hidden="true">
          <rect
            x="7.25"
            y="2"
            width="5.5"
            height="9.5"
            rx="2.75"
            fill={isRecording ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="1.25"
          />
          <path
            d="M4.5 9.5a5.5 5.5 0 0 0 11 0M10 15v3M7.25 18h5.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinecap="round"
          />
        </svg>
      </span>
    </button>
  );
}
