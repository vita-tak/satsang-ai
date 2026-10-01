import { motion } from "framer-motion";
import { RESPONSE_MODES } from "@/lib/mode";
import type { ResponseMode } from "@/lib/mode";
import { EASE_BREATH } from "@/lib/motion";

const MODE_COPY: Record<ResponseMode, { label: string; description: string }> = {
  satsang: { label: "Satsang", description: "Whatever you bring, met where you are." },
  teachings: { label: "Teachings", description: "The teachings explained, from the texts." },
  ramana: { label: "Ramana", description: "As Ramana answered: briefly, and back to you." },
  self_inquiry: { label: "Self-inquiry", description: "No teaching. A question for you, now." },
};

const MODE_DESCRIPTION_ID = "response-mode-description";

interface ModeToggleProps {
  mode: ResponseMode;
  isQuiet: boolean;
  onChange: (mode: ResponseMode) => void;
}

export function ModeToggle({ mode, isQuiet, onChange }: ModeToggleProps) {
  return (
    <fieldset
      aria-describedby={isQuiet ? undefined : MODE_DESCRIPTION_ID}
      className="mx-auto mt-1 w-full max-w-measure"
    >
      <legend className="sr-only">How the guide answers</legend>
      {/* Four labels need 317px with 24px gaps: the gap narrows below 375px and wraps below 353px. */}
      <div className="flex flex-wrap gap-x-5 min-[375px]:gap-x-6">
        {RESPONSE_MODES.map((option) => (
          <ModeOption
            key={option}
            mode={option}
            isSelected={option === mode}
            isQuiet={isQuiet}
            onChange={onChange}
          />
        ))}
      </div>
      {isQuiet ? null : (
        <motion.p
          key={mode}
          id={MODE_DESCRIPTION_ID}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, ease: EASE_BREATH }}
          className="font-serif text-note text-ink-faint italic"
        >
          {MODE_COPY[mode].description}
        </motion.p>
      )}
    </fieldset>
  );
}

interface ModeOptionProps {
  mode: ResponseMode;
  isSelected: boolean;
  isQuiet: boolean;
  onChange: (mode: ResponseMode) => void;
}

function ModeOption({ mode, isSelected, isQuiet, onChange }: ModeOptionProps) {
  // Selection is marked by the underline in both states; only the intro also gives it full ink.
  // The outline colour is set at rest (invisible without an outline style), so focus shows the ember
  // ring at once instead of easing to it from the ink colour with the colour transition.
  const colorClass = isSelected && !isQuiet ? "text-ink" : "text-ink-faint";
  const underlineClass = isSelected ? "decoration-current" : "decoration-transparent";
  return (
    <label className="group inline-flex min-h-11 min-w-11 cursor-pointer items-center">
      <input
        type="radio"
        name="response-mode"
        value={mode}
        checked={isSelected}
        onChange={() => onChange(mode)}
        className="peer sr-only"
      />
      <span
        className={`${colorClass} ${underlineClass} whitespace-nowrap text-note underline decoration-1 underline-offset-4 outline-accent outline-offset-4 transition-colors duration-500 ease-breath group-hover:text-ink peer-focus-visible:text-ink peer-focus-visible:outline-1`}
      >
        {MODE_COPY[mode].label}
      </span>
    </label>
  );
}
