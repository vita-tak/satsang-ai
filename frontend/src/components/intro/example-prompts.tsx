import { motion } from "framer-motion";
import { MODE_PROMPT_SETS } from "@/components/intro/prompt-sets";
import type { ResponseMode } from "@/lib/mode";
import { EASE_BREATH } from "@/lib/motion";

interface ExamplePromptsProps {
  mode: ResponseMode;
  promptSetIndex: number;
  onChoose: (prompt: string) => void;
  onRotate: () => void;
}

export function ExamplePrompts({ mode, promptSetIndex, onChoose, onRotate }: ExamplePromptsProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <p className="font-serif text-note text-ink-faint italic">Or begin with</p>
        <RotatePromptsButton onClick={onRotate} />
      </div>
      {/* Keyed by mode and set, so a new mode's questions or a rotated set fade in together. */}
      <motion.ul
        key={`${mode}-${promptSetIndex}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: EASE_BREATH }}
        className="mt-2"
      >
        {MODE_PROMPT_SETS[mode][promptSetIndex].map((prompt) => (
          <li key={prompt}>
            <PromptRow prompt={prompt} onChoose={onChoose} />
          </li>
        ))}
      </motion.ul>
    </>
  );
}

function RotatePromptsButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Show different example questions"
      className="-mr-3 grid size-11 shrink-0 cursor-pointer place-items-center text-ink-faint transition-colors duration-500 ease-breath hover:text-ink"
    >
      <svg viewBox="0 0 20 20" className="size-3" aria-hidden="true">
        <path
          d="M15.5 10a5.5 5.5 0 1 1-1.94-4.2M15.5 3.5v3.5h-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

interface PromptRowProps {
  prompt: string;
  onChoose: (prompt: string) => void;
}

function PromptRow({ prompt, onChoose }: PromptRowProps) {
  return (
    <button
      type="button"
      onClick={() => onChoose(prompt)}
      className="group relative flex min-h-11 w-full cursor-pointer items-center py-1.5 text-left text-body text-ink-soft sm:text-body-lg transition-colors duration-500 ease-breath hover:text-ink focus-visible:text-ink focus-visible:outline-none active:text-ink"
    >
      <span
        className="absolute -left-4 size-1.5 rounded-full bg-accent opacity-0 transition-opacity duration-500 ease-breath group-hover:opacity-100 group-focus-visible:opacity-100"
        aria-hidden="true"
      />
      {prompt}
    </button>
  );
}
