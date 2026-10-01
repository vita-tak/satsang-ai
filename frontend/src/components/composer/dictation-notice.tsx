import { motion } from "framer-motion";
import { EASE_BREATH } from "@/lib/motion";

export function DictationNotice({ message }: { message: string }) {
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
