import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { ExamplePrompts } from "@/components/intro/example-prompts";
import type { ResponseMode } from "@/lib/mode";
import { EASE_BREATH, introStagger, riseIn } from "@/lib/motion";

interface IntroProps {
  mode: ResponseMode;
  promptSetIndex: number;
  onChoose: (prompt: string) => void;
  onRotate: () => void;
  composer: ReactNode;
}

export function Intro({ mode, promptSetIndex, onChoose, onRotate, composer }: IntroProps) {
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
        <ExamplePrompts
          mode={mode}
          promptSetIndex={promptSetIndex}
          onChoose={onChoose}
          onRotate={onRotate}
        />
      </motion.div>
    </motion.section>
  );
}
