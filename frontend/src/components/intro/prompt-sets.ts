import type { ResponseMode } from "@/lib/mode";

// Four rotating sets of four example questions per mode, in the register of the mode. Each fits
// on one line from 320px wide, so switching modes or rotating a set never changes the intro's
// height or moves the toggle.
export const MODE_PROMPT_SETS: Record<ResponseMode, string[][]> = {
  satsang: [
    [
      "Who am I, really?",
      "I feel lost and don’t know why.",
      "Is the self an illusion?",
      "I keep forgetting to practice.",
    ],
    [
      "Why do I suffer?",
      "My mind won’t quiet down.",
      "What is awareness, exactly?",
      "I’m scared of what I might find.",
    ],
    [
      "How do I begin self-inquiry?",
      "Nothing feels meaningful lately.",
      "Can I trust what I experience?",
      "How do I know I’m progressing?",
    ],
    [
      "I can’t stop worrying.",
      "Am I doing this wrong?",
      "Where does thought come from?",
      "This feels too simple to work.",
    ],
  ],
  teachings: [
    [
      "What is the nature of the Self?",
      "Why do thoughts feel so real?",
      "What does non-duality mean?",
      "How do I study these teachings?",
    ],
    [
      "What is the ‘I-thought’?",
      "What is true surrender?",
      "Is the ego real or illusory?",
      "Where do I start as a beginner?",
    ],
    [
      "What does Maya mean?",
      "Is the world truly unreal?",
      "Can knowledge itself liberate?",
      "Is inquiry not just meditation?",
    ],
    [
      "What is silent teaching?",
      "What is the witness?",
      "Does effort help or hinder?",
      "What did Ramana say about sleep?",
    ],
  ],
  ramana: [
    [
      "How can I control my mind?",
      "Did you ever feel fear?",
      "What is silence, really?",
      "Am I only deluding myself?",
    ],
    [
      "What happens after death?",
      "How did you wake up so suddenly?",
      "Is grace real or just a concept?",
      "What should I actually do each day?",
    ],
    [
      "Do I have free will?",
      "Was your path unique to you?",
      "What is the role of the guru?",
      "How do I deal with doubt?",
    ],
    [
      "How can I help the world?",
      "What did you mean by ‘Be still’?",
      "Can a busy life still awaken?",
      "Is deep sleep close to samadhi?",
    ],
  ],
  self_inquiry: [
    [
      "Guide me in self-inquiry now.",
      "I feel restless — guide me inward.",
      "What am I, beneath all this noise?",
      "How do I find the ‘I’?",
    ],
    [
      "My mind is restless right now.",
      "Where do thoughts arise from?",
      "Can I do this on my own?",
      "Something feels off today.",
    ],
    [
      "Where do I look for the ‘I’?",
      "I keep sliding into thought.",
      "What happens when I find nothing?",
      "Is this working? I can’t tell.",
    ],
    [
      "Something feels heavy today.",
      "I sat still — now what?",
      "The ‘I’ keeps slipping away.",
      "Am I the one who is aware?",
    ],
  ],
};

function promptSetStorageKey(mode: ResponseMode): string {
  return `promptSetIndex_${mode}`;
}

function readStoredPromptSetIndex(mode: ResponseMode): number {
  try {
    const stored = sessionStorage.getItem(promptSetStorageKey(mode));
    const index = stored === null ? NaN : Number(stored);
    const setCount = MODE_PROMPT_SETS[mode].length;
    return Number.isInteger(index) && index >= 0 && index < setCount ? index : -1;
  } catch {
    // Storage can be unavailable (private browsing); treated as no stored value yet.
    return -1;
  }
}

function storePromptSetIndex(mode: ResponseMode, index: number) {
  try {
    sessionStorage.setItem(promptSetStorageKey(mode), String(index));
  } catch {
    // Storage can be unavailable (private browsing); the choice then lasts for this page only.
  }
}

// Reads the last index seen for a mode, advances it by one set (wrapping), saves it back, and
// returns the new value. No stored value yet reads as -1, so the first-ever value is set 0.
export function advanceStoredPromptSetIndex(mode: ResponseMode): number {
  const setCount = MODE_PROMPT_SETS[mode].length;
  const nextIndex = (readStoredPromptSetIndex(mode) + 1) % setCount;
  storePromptSetIndex(mode, nextIndex);
  return nextIndex;
}
