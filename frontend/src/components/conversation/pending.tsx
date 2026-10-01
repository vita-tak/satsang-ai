import { motion } from "framer-motion";
import { EASE_BREATH } from "@/lib/motion";

export function Pending() {
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
