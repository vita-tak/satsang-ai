"use client";

import { memo, useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, ReactNode, RefObject } from "react";
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from "framer-motion";
import type { Transition, Variants } from "framer-motion";
import Markdown from "react-markdown";
import { toggleTheme } from "@/lib/theme";
import type { ChatMessage, ChatRequest, ChatResponse } from "@/types/chat";

const PROMPT_SETS = [
  [
    "Who am I?",
    "What is self-inquiry?",
    "What does Maya mean?",
    "I feel unable to quiet my mind.",
  ],
  [
    "What is the nature of the Self?",
    "What does Advaita mean?",
    "Is the mind the same as the Self?",
    "How do I practice self-inquiry in daily life?",
  ],
  [
    "What is meant by the ‘I-thought’?",
    "What is the difference between the ego and the Self?",
    "What does Turiya mean?",
    "I keep getting distracted during practice.",
  ],
  [
    "Is there a method to self-inquiry?",
    "What does it mean to abide as the Self?",
    "What does Moksha mean?",
    "I feel like I am making no progress.",
  ],
];

const PROMPT_SET_INDEX_KEY = "promptSetIndex";

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

function isTouchScreen(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
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
  const [promptSetIndex, setPromptSetIndex] = useState(0);
  const [hasIntroLeft, setHasIntroLeft] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const latestQuestionRef = useRef<HTMLParagraphElement>(null);
  const prefersReducedMotion = useReducedMotion();

  const exchanges = toExchanges(messages);

  useEffect(() => {
    // sessionStorage only exists in the browser, so this must run post-mount rather than
    // during the lazy useState initializer, or server and client would compute different indexes.
    try {
      const stored = sessionStorage.getItem(PROMPT_SET_INDEX_KEY);
      const lastIndex = stored === null ? -1 : Number(stored);
      const nextIndex = (lastIndex + 1) % PROMPT_SETS.length;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPromptSetIndex(nextIndex);
      sessionStorage.setItem(PROMPT_SET_INDEX_KEY, String(nextIndex));
    } catch {
      setPromptSetIndex(0);
    }
  }, []);

  useEffect(() => {
    latestQuestionRef.current?.scrollIntoView({
      block: "start",
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }, [exchanges.length, prefersReducedMotion]);

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
      const requestBody: ChatRequest = { message: text, session_id: sessionId };
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

  const composer = (
    <Composer
      value={input}
      canSubmit={!isLoading && input.trim() !== ""}
      inputRef={inputRef}
      onChange={setInput}
      onSubmit={handleSubmit}
    />
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
                  prompts={PROMPT_SETS[promptSetIndex]}
                  onChoose={choosePrompt}
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
  prompts: string[];
  onChoose: (prompt: string) => void;
  composer: ReactNode;
}

function Intro({ prompts, onChoose, composer }: IntroProps) {
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
        <p className="font-serif text-note text-ink-faint italic">Or begin with</p>
        <ul className="mt-2">
          {prompts.map((prompt) => (
            <li key={prompt}>
              <PromptRow prompt={prompt} onChoose={onChoose} />
            </li>
          ))}
        </ul>
      </motion.div>
    </motion.section>
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
        className="scroll-mt-8 whitespace-pre-wrap break-words text-body text-ink-soft sm:text-body-lg"
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

const Answer = memo(function Answer({ content }: { content: string }) {
  return (
    <motion.div variants={riseIn} initial="hidden" animate="visible" className="answer mt-5">
      <Markdown>{withTypographicQuotes(content)}</Markdown>
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
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function Composer({ value, canSubmit, inputRef, onChange, onSubmit }: ComposerProps) {
  return (
    <form onSubmit={onSubmit}>
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
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={submitOnEnter}
          autoComplete="off"
          placeholder="Ask a question…"
          enterKeyHint="send"
          className="field-sizing-content max-h-[40dvh] min-w-0 flex-1 resize-none bg-transparent py-3 text-body text-ink caret-accent sm:text-body-lg placeholder:text-ink-faint focus:outline-none"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="min-h-11 min-w-11 shrink-0 cursor-pointer text-right text-label text-accent uppercase decoration-1 underline-offset-4 transition-colors duration-500 ease-breath enabled:hover:underline disabled:cursor-default disabled:text-ink-faint"
        >
          Ask
        </button>
      </div>
    </form>
  );
}
