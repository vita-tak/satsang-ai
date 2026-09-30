"use client";

import { Children, isValidElement, memo, useEffect, useRef, useState } from "react";
import type {
  ComponentProps,
  FormEvent,
  KeyboardEvent,
  ReactElement,
  ReactNode,
  RefObject,
} from "react";
import { AnimatePresence, MotionConfig, animate, motion, useReducedMotion } from "framer-motion";
import type { Transition, Variants } from "framer-motion";
import Markdown from "react-markdown";
import type { Components, ExtraProps } from "react-markdown";
import { DEFAULT_MODE, RESPONSE_MODES, readStoredMode, storeMode } from "@/lib/mode";
import type { ResponseMode } from "@/lib/mode";
import { appendTranscript, useDictation } from "@/lib/dictation";
import type { DictationStatus } from "@/lib/dictation";
import { toggleTheme } from "@/lib/theme";
import type { ChatMessage, ChatRequest, ChatResponse } from "@/types/chat";

const MODE_COPY: Record<ResponseMode, { label: string; description: string }> = {
  satsang: { label: "Satsang", description: "Whatever you bring, met where you are." },
  teachings: { label: "Teachings", description: "The teachings explained, from the texts." },
  ramana: { label: "Ramana", description: "As Ramana answered: briefly, and back to you." },
  self_inquiry: { label: "Self-inquiry", description: "No teaching. A question for you, now." },
};

// Four rotating sets of four example questions per mode, in the register of the mode. Each fits
// on one line from 320px wide, so switching modes or rotating a set never changes the intro's
// height or moves the toggle.
const MODE_PROMPT_SETS: Record<ResponseMode, string[][]> = {
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
function advanceStoredPromptSetIndex(mode: ResponseMode): number {
  const setCount = MODE_PROMPT_SETS[mode].length;
  const nextIndex = (readStoredPromptSetIndex(mode) + 1) % setCount;
  storePromptSetIndex(mode, nextIndex);
  return nextIndex;
}

const MODE_DESCRIPTION_ID = "response-mode-description";

const EASE_BREATH = [0.37, 0, 0.63, 1] as const;

const BREATH: Transition = { duration: 1.2, ease: EASE_BREATH };

const introStagger: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.14, delayChildren: 0.1 } },
};

const riseIn: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};

interface Exchange {
  question: string;
  answer: string | null;
}

function toExchanges(messages: ChatMessage[]): Exchange[] {
  const exchanges: Exchange[] = [];
  for (const message of messages) {
    if (message.role === "user") {
      exchanges.push({ question: message.content, answer: null });
    } else {
      exchanges[exchanges.length - 1].answer = message.content;
    }
  }
  return exchanges;
}

const OPENING_DOUBLE_QUOTE = /(^|[\s([*_\u2014])"/g;
const OPENING_SINGLE_QUOTE = /(^|[\s([*_\u2014])'/g;

function withTypographicQuotes(text: string): string {
  return text
    .replace(OPENING_DOUBLE_QUOTE, "$1\u201c")
    .replace(/"/g, "\u201d")
    .replace(OPENING_SINGLE_QUOTE, "$1\u2018")
    .replace(/'/g, "\u2019");
}

// A final question mark, allowing closing emphasis, quotes or brackets after it.
const QUESTION_ENDING = /\?[*_"'\u201d\u2019)\]]*$/;

function endsOnQuestion(markdown: string): boolean {
  const lines = markdown.trimEnd().split("\n");
  const lastLine = lines[lines.length - 1].trim();
  // A quote is his, not the guide's closing: an answer that ends inside a blockquote gets no point.
  if (lastLine.startsWith(">")) {
    return false;
  }
  return QUESTION_ENDING.test(lastLine);
}

// Where a quote comes from, as the guide writes it: "Talk 107", "Be As You Are, Ch. 5",
// "Be As You Are, chapter 16". The whole paragraph must be the reference, not just start like one.
const TALK_REFERENCE = /^(Talks with Sri Ramana Maharshi, )?Talk \d+$/;
const BOOK_REFERENCE = /^Be As You Are(, (Ch\.|chapter) \d+.*)?$/;
const REFERENCE_MAX_LENGTH = 80;

function isQuoteReference(text: string): boolean {
  let reference = text.trim().replace(/\.$/, "");
  if (reference.startsWith("(") && reference.endsWith(")")) {
    reference = reference.slice(1, -1);
  }
  if (reference.length > REFERENCE_MAX_LENGTH) {
    return false;
  }
  return TALK_REFERENCE.test(reference) || BOOK_REFERENCE.test(reference);
}

type MarkdownNode = NonNullable<ExtraProps["node"]>;
type MarkdownChild = MarkdownNode["children"][number];

function textContent(node: MarkdownChild): string {
  if (node.type === "text") {
    return node.value;
  }
  if (node.type === "element") {
    return node.children.map(textContent).join("");
  }
  return "";
}

function isTouchScreen(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

// On a touch screen the keyboard is still closing when a sent question is scrolled into view, so
// the view's height from before it opened is the one to judge by.
function viewHeightWithoutKeyboard(heightBeforeKeyboard: number): number {
  return isTouchScreen() && heightBeforeKeyboard > 0 ? heightBeforeKeyboard : window.innerHeight;
}

// Pinned to the top, a question keeps "Answering" in view only if it fits between its scroll
// margins; the bottom margin leaves room for "Answering" above the composer and its fade.
function isTallerThanView(question: HTMLElement, viewHeight: number): boolean {
  const { scrollMarginTop, scrollMarginBottom } = getComputedStyle(question);
  const room = viewHeight - parseFloat(scrollMarginTop) - parseFloat(scrollMarginBottom);
  return question.offsetHeight > room;
}

function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
  const isPlainEnter = event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing;
  if (isPlainEnter) {
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<ResponseMode>(DEFAULT_MODE);
  const [promptSetIndex, setPromptSetIndex] = useState(0);
  const [hasIntroLeft, setHasIntroLeft] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const latestQuestionRef = useRef<HTMLParagraphElement>(null);
  const viewHeightBeforeKeyboardRef = useRef(0);
  const prefersReducedMotion = useReducedMotion();

  const exchanges = toExchanges(messages);

  useEffect(() => {
    // sessionStorage only exists in the browser, so this must run post-mount rather than in a lazy
    // useState initializer, or server and client would render different modes. The intro is still
    // fading in, so the switch from the default mode and its questions is never seen.
    const storedMode = readStoredMode();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMode(storedMode);
    setPromptSetIndex(advanceStoredPromptSetIndex(storedMode));
  }, []);

  useEffect(() => {
    // Runs for each new question, and once more when the intro has left, since only then does the
    // first question mount. A question is pinned to the top; one too long to keep "Answering" in
    // view there, such as a letter, is scrolled to its end instead. A short first question stays
    // where it lands.
    const question = latestQuestionRef.current;
    if (!question) {
      return;
    }
    const viewHeight = viewHeightWithoutKeyboard(viewHeightBeforeKeyboardRef.current);
    const isLong = isTallerThanView(question, viewHeight);
    if (exchanges.length === 1 && !isLong) {
      return;
    }
    question.scrollIntoView({
      block: isLong ? "end" : "start",
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }, [exchanges.length, hasIntroLeft, prefersReducedMotion]);

  useEffect(() => {
    if (hasIntroLeft && !isTouchScreen()) {
      inputRef.current?.focus();
    }
  }, [hasIntroLeft]);

  async function sendMessage(text: string) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    setError(null);

    try {
      const requestBody: ChatRequest = { message: text, session_id: sessionId, mode };
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!res.ok) {
        const errorBody = await res.json();
        throw new Error(errorBody.detail ?? "Failed to send message.");
      }

      const data: ChatResponse = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) {
      return;
    }
    setInput("");
    if (isTouchScreen()) {
      inputRef.current?.blur();
    }
    sendMessage(trimmed);
  }

  function choosePrompt(prompt: string) {
    setInput(prompt);
    inputRef.current?.focus();
  }

  function chooseMode(nextMode: ResponseMode) {
    setMode(nextMode);
    storeMode(nextMode);
    setPromptSetIndex(advanceStoredPromptSetIndex(nextMode));
  }

  function rotatePrompts() {
    setPromptSetIndex(advanceStoredPromptSetIndex(mode));
  }

  function rememberViewHeight() {
    // Focus comes before the on-screen keyboard opens, so this is the full height of the view.
    viewHeightBeforeKeyboardRef.current = window.innerHeight;
  }

  // The mode toggle travels with the composer: inline in the intro, pinned to the bottom after.
  const composer = (
    <>
      <Composer
        value={input}
        canSubmit={!isLoading && input.trim() !== ""}
        inputRef={inputRef}
        onChange={setInput}
        onFocus={rememberViewHeight}
        onSubmit={handleSubmit}
      />
      <ModeToggle mode={mode} isQuiet={hasIntroLeft} onChange={chooseMode} />
    </>
  );

  return (
    <MotionConfig transition={BREATH} reducedMotion="user">
      <div className="flex min-h-dvh flex-col">
        <Header />
        <main className="flex flex-1 flex-col px-6 sm:px-8">
          <div className="mx-auto flex w-full max-w-measure flex-1 flex-col">
            <AnimatePresence mode="wait" onExitComplete={() => setHasIntroLeft(true)}>
              {exchanges.length === 0 ? (
                <Intro
                  key="intro"
                  mode={mode}
                  promptSetIndex={promptSetIndex}
                  onChoose={choosePrompt}
                  onRotate={rotatePrompts}
                  composer={composer}
                />
              ) : (
                <Conversation
                  key="conversation"
                  exchanges={exchanges}
                  isLoading={isLoading}
                  error={error}
                  latestQuestionRef={latestQuestionRef}
                />
              )}
            </AnimatePresence>
          </div>
        </main>
        {hasIntroLeft ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, ease: EASE_BREATH }}
            className="composer-fade sticky bottom-0 bg-ground px-6 pb-4 sm:px-8 sm:pb-8"
          >
            {composer}
          </motion.div>
        ) : null}
      </div>
    </MotionConfig>
  );
}

function Header() {
  return (
    <header className="flex items-center justify-between px-6 pt-2 sm:px-8 sm:pt-4">
      <h1 translate="no" className="flex items-center gap-3 font-serif text-body text-ink">
        <span className="size-1.5 rounded-full bg-accent" aria-hidden="true" />
        Satsang
      </h1>
      <ThemeToggle />
    </header>
  );
}

function ThemeToggle() {
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Switch between light and dark theme"
      className="-mr-3 grid size-11 cursor-pointer place-items-center text-ink-faint transition-colors duration-500 ease-breath hover:text-ink"
    >
      <svg viewBox="0 0 20 20" className="size-4.5" aria-hidden="true">
        <circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
        <path d="M10 1.75a8.25 8.25 0 0 1 0 16.5z" fill="currentColor" />
      </svg>
    </button>
  );
}

interface IntroProps {
  mode: ResponseMode;
  promptSetIndex: number;
  onChoose: (prompt: string) => void;
  onRotate: () => void;
  composer: ReactNode;
}

function Intro({ mode, promptSetIndex, onChoose, onRotate, composer }: IntroProps) {
  return (
    <motion.section
      variants={introStagger}
      initial="hidden"
      animate="visible"
      exit={{ opacity: 0, transition: { duration: 0.7, ease: EASE_BREATH } }}
      className="my-auto py-12"
    >
      <motion.h2
        variants={riseIn}
        className="font-serif text-display text-balance text-ink sm:text-display-lg"
      >
        Sit with a question.
      </motion.h2>
      <motion.p variants={riseIn} className="mt-5 max-w-[32rem] text-body text-pretty text-ink-soft sm:text-body-lg">
        An AI guide to self-inquiry in the tradition of Ramana Maharshi. Ask about the teachings,
        the practice, or a Sanskrit term.
      </motion.p>
      <motion.div variants={riseIn} className="mt-10">
        {composer}
      </motion.div>
      <motion.div variants={riseIn} className="mt-10">
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
      </motion.div>
    </motion.section>
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

interface ConversationProps {
  exchanges: Exchange[];
  isLoading: boolean;
  error: string | null;
  latestQuestionRef: RefObject<HTMLParagraphElement | null>;
}

function Conversation({ exchanges, isLoading, error, latestQuestionRef }: ConversationProps) {
  const latestIndex = exchanges.length - 1;
  return (
    <div role="log" aria-label="Conversation" className="pb-10">
      {exchanges.map((exchange, index) => {
        const isLatest = index === latestIndex;
        return (
          <ExchangeView
            key={index}
            exchange={exchange}
            isPending={isLatest && isLoading}
            error={isLatest ? error : null}
            questionRef={isLatest ? latestQuestionRef : undefined}
          />
        );
      })}
    </div>
  );
}

interface ExchangeViewProps {
  exchange: Exchange;
  isPending: boolean;
  error: string | null;
  questionRef?: RefObject<HTMLParagraphElement | null>;
}

function ExchangeView({ exchange, isPending, error, questionRef }: ExchangeViewProps) {
  return (
    <section className="pt-16 first:pt-10 last:min-h-[calc(100dvh-5rem)]">
      <motion.p
        ref={questionRef}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, ease: EASE_BREATH }}
        className="scroll-mt-8 scroll-mb-56 whitespace-pre-wrap break-words text-body text-ink-soft sm:text-body-lg"
      >
        {exchange.question}
      </motion.p>
      <AnimatePresence mode="wait">
        {exchange.answer !== null ? <Answer key="answer" content={exchange.answer} /> : null}
        {exchange.answer === null && isPending ? <Pending key="pending" /> : null}
      </AnimatePresence>
      {error ? (
        <motion.div
          role="alert"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-5 text-note break-words"
        >
          <p className="text-error">The answer did not come through. Please ask again.</p>
          <p className="mt-1 text-ink-faint">{error}</p>
        </motion.div>
      ) : null}
    </section>
  );
}

// When a quote's last paragraph is its reference, the reference moves out of the quote into the
// figure's caption, where HTML puts attribution: it is the page's citation, not his words.
function Quote({ node, children }: ComponentProps<"blockquote"> & ExtraProps) {
  const elements = node?.children.filter((child) => child.type === "element") ?? [];
  const last = elements[elements.length - 1];
  const endsOnReference =
    elements.length >= 2 &&
    last.type === "element" &&
    last.tagName === "p" &&
    isQuoteReference(textContent(last));
  if (!endsOnReference) {
    return <blockquote>{children}</blockquote>;
  }
  // react-markdown renders the node's children in order, so the last element is that paragraph.
  const parts = Children.toArray(children);
  const referenceIndex = parts.findLastIndex(isValidElement);
  const reference = parts[referenceIndex] as ReactElement<{ children?: ReactNode }>;
  return (
    <figure>
      <blockquote>{parts.filter((_, index) => index !== referenceIndex)}</blockquote>
      <figcaption>{reference.props.children}</figcaption>
    </figure>
  );
}

const MARKDOWN_COMPONENTS: Components = { blockquote: Quote };

const Answer = memo(function Answer({ content }: { content: string }) {
  const isQuestionEnding = endsOnQuestion(content);
  return (
    <motion.div
      variants={riseIn}
      initial="hidden"
      animate="visible"
      data-ends-on-question={isQuestionEnding ? "" : undefined}
      className="answer mt-5"
    >
      <Markdown components={MARKDOWN_COMPONENTS}>{withTypographicQuotes(content)}</Markdown>
    </motion.div>
  );
});

function Pending() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { delay: 0.4, duration: 0.9, ease: EASE_BREATH } }}
      exit={{ opacity: 0, transition: { duration: 0.4, ease: EASE_BREATH } }}
      className="mt-5"
    >
      <p className="animate-breathe font-serif text-reading text-ink sm:text-reading-lg">Answering</p>
    </motion.div>
  );
}

interface ComposerProps {
  value: string;
  canSubmit: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
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

function Composer({ value, canSubmit, inputRef, onChange, onFocus, onSubmit }: ComposerProps) {
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

function MicButton({ status, onClick }: MicButtonProps) {
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

function DictationNotice({ message }: { message: string }) {
  return (
    <motion.p
      role="alert"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: EASE_BREATH }}
      className="mx-auto mt-2 w-full max-w-measure text-note text-error"
    >
      {message}
    </motion.p>
  );
}

interface ModeToggleProps {
  mode: ResponseMode;
  isQuiet: boolean;
  onChange: (mode: ResponseMode) => void;
}

function ModeToggle({ mode, isQuiet, onChange }: ModeToggleProps) {
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
