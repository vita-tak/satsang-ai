import type { RefObject } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Answer } from "@/components/conversation/answer";
import { Pending } from "@/components/conversation/pending";
import type { Exchange } from "@/lib/chat";
import { EASE_BREATH } from "@/lib/motion";

interface ConversationProps {
  exchanges: Exchange[];
  isLoading: boolean;
  error: string | null;
  latestQuestionRef: RefObject<HTMLParagraphElement | null>;
}

export function Conversation({ exchanges, isLoading, error, latestQuestionRef }: ConversationProps) {
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
