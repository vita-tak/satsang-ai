"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from "framer-motion";
import { Composer } from "@/components/composer/composer";
import { Conversation } from "@/components/conversation/conversation";
import { Intro } from "@/components/intro/intro";
import { advanceStoredPromptSetIndex } from "@/components/intro/prompt-sets";
import { useChat } from "@/lib/chat";
import { BREATH, EASE_BREATH } from "@/lib/motion";
import { useSpeech } from "@/lib/speech";
import { isTouchScreen, viewHeightWithoutKeyboard } from "@/lib/touch";

// The page under the header: the intro until the first question, then the conversation, with the
// composer moving from inline in the intro to pinned at the bottom.

// Pinned to the top, a question keeps "Answering" in view only if it fits between its scroll
// margins; the bottom margin leaves room for "Answering" above the composer and its fade.
function isTallerThanView(question: HTMLElement, viewHeight: number): boolean {
  const { scrollMarginTop, scrollMarginBottom } = getComputedStyle(question);
  const room = viewHeight - parseFloat(scrollMarginTop) - parseFloat(scrollMarginBottom);
  return question.offsetHeight > room;
}

export function Satsang() {
  const [input, setInput] = useState("");
  const [promptSetIndex, setPromptSetIndex] = useState(0);
  const [hasIntroLeft, setHasIntroLeft] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const latestQuestionRef = useRef<HTMLParagraphElement>(null);
  const viewHeightBeforeKeyboardRef = useRef(0);
  const prefersReducedMotion = useReducedMotion();
  const speech = useSpeech();
  const chat = useChat(speech);

  const { exchanges } = chat;

  useEffect(() => {
    // sessionStorage only exists in the browser, so this must run post-mount rather than in a lazy
    // useState initializer, or server and client would render different questions. The intro is
    // still fading in, so the switch from the first set is never seen.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPromptSetIndex(advanceStoredPromptSetIndex());
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || chat.isLoading) {
      return;
    }
    setInput("");
    if (isTouchScreen()) {
      inputRef.current?.blur();
    }
    // A new question ends the answer still being read, and a tap is what lets the next one play.
    speech.stop();
    if (speech.isOn) {
      speech.prime();
    }
    chat.send(trimmed);
  }

  function choosePrompt(prompt: string) {
    setInput(prompt);
    inputRef.current?.focus();
  }

  function rotatePrompts() {
    setPromptSetIndex(advanceStoredPromptSetIndex());
  }

  function rememberViewHeight() {
    // Focus comes before the on-screen keyboard opens, so this is the full height of the view.
    viewHeightBeforeKeyboardRef.current = window.innerHeight;
  }

  // The composer is inline in the intro and pinned to the bottom after.
  const composer = (
    <Composer
      value={input}
      canSubmit={!chat.isLoading && input.trim() !== ""}
      isSpeakerOn={speech.isOn}
      inputRef={inputRef}
      onToggleSpeaker={speech.toggle}
      onChange={setInput}
      onFocus={rememberViewHeight}
      onSubmit={handleSubmit}
    />
  );

  return (
    <MotionConfig transition={BREATH} reducedMotion="user">
      <main className="flex flex-1 flex-col px-6 sm:px-8">
        <div className="mx-auto flex w-full max-w-measure flex-1 flex-col">
          <AnimatePresence mode="wait" onExitComplete={() => setHasIntroLeft(true)}>
            {exchanges.length === 0 ? (
              <Intro
                key="intro"
                promptSetIndex={promptSetIndex}
                onChoose={choosePrompt}
                onRotate={rotatePrompts}
                composer={composer}
              />
            ) : (
              <Conversation
                key="conversation"
                exchanges={exchanges}
                isLoading={chat.isLoading}
                error={chat.error}
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
    </MotionConfig>
  );
}
