// Four rotating sets of four example questions. Each fits on one line from 320px wide, so
// rotating a set never changes the intro's height.
export const PROMPT_SETS: string[][] = [
  [
    "Who am I, really?",
    "I never know what to look for.",
    "Is the self an illusion?",
    "I keep forgetting to practice.",
  ],
  [
    "Why do I suffer?",
    "My mind won’t quiet down.",
    "What is awareness, exactly?",
    "Why does looking feel so hard?",
  ],
  [
    "How do I begin self-inquiry?",
    "I keep waiting for a shift.",
    "Can I trust what I experience?",
    "How do I know I’m progressing?",
  ],
  [
    "I can’t stop worrying.",
    "Am I doing this wrong?",
    "Where does thought come from?",
    "This feels too simple to work.",
  ],
];

const PROMPT_SET_STORAGE_KEY = "promptSetIndex";

function readStoredPromptSetIndex(): number {
  try {
    const stored = sessionStorage.getItem(PROMPT_SET_STORAGE_KEY);
    const index = stored === null ? NaN : Number(stored);
    return Number.isInteger(index) && index >= 0 && index < PROMPT_SETS.length ? index : -1;
  } catch {
    // Storage can be unavailable (private browsing); treated as no stored value yet.
    return -1;
  }
}

function storePromptSetIndex(index: number) {
  try {
    sessionStorage.setItem(PROMPT_SET_STORAGE_KEY, String(index));
  } catch {
    // Storage can be unavailable (private browsing); the choice then lasts for this page only.
  }
}

// Reads the last index seen, advances it by one set (wrapping), saves it back, and returns the new
// value. No stored value yet reads as -1, so the first-ever value is set 0.
export function advanceStoredPromptSetIndex(): number {
  const nextIndex = (readStoredPromptSetIndex() + 1) % PROMPT_SETS.length;
  storePromptSetIndex(nextIndex);
  return nextIndex;
}
