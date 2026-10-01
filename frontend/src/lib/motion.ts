import type { Transition, Variants } from "framer-motion";

export const EASE_BREATH = [0.37, 0, 0.63, 1] as const;

export const BREATH: Transition = { duration: 1.2, ease: EASE_BREATH };

export const introStagger: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.14, delayChildren: 0.1 } },
};

export const riseIn: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};
