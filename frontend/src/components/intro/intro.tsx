import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { ExamplePrompts } from "@/components/intro/example-prompts";
import { EASE_BREATH, introStagger, riseIn } from "@/lib/motion";

interface IntroProps {
  promptSetIndex: number;
  onChoose: (prompt: string) => void;
  onRotate: () => void;
  composer: ReactNode;
}

export function Intro({ promptSetIndex, onChoose, onRotate, composer }: IntroProps) {
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
        An AI guide to self-inquiry. Bring what is on your mind, or ask about the practice or a
        Sanskrit term.
      </motion.p>
      <motion.div variants={riseIn} className="mt-10">
        {composer}
      </motion.div>
      <motion.div variants={riseIn} className="mt-10">
        <ExamplePrompts
          promptSetIndex={promptSetIndex}
          onChoose={onChoose}
          onRotate={onRotate}
        />
      </motion.div>
    </motion.section>
  );
}
