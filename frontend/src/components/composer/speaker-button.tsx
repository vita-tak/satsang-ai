// Off is quiet ink with a cross where the sound would be; on is full ink with sound waves, so the
// state does not rest on colour alone. Ember stays with the microphone.
export function SpeakerButton({ isOn, onClick }: { isOn: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Read answers aloud"
      aria-pressed={isOn}
      className={`${isOn ? "text-ink" : "text-ink-faint hover:text-ink"} grid size-11 shrink-0 cursor-pointer place-items-center transition-colors duration-500 ease-breath`}
    >
      <svg viewBox="0 0 20 20" className="size-4.5" aria-hidden="true">
        <path
          d="M3 7.75h2.75L10 4.25v11.5l-4.25-3.5H3z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinejoin="round"
        />
        <path
          d={isOn ? "M12.5 7.5a3.5 3.5 0 0 1 0 5M14.75 5.25a6.5 6.5 0 0 1 0 9.5" : "M13 8l4 4M17 8l-4 4"}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
        />
      </svg>
    </button>
  );
}
