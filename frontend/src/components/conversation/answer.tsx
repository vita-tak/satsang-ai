import { Children, isValidElement, memo } from "react";
import type { ComponentProps, ReactElement, ReactNode } from "react";
import { motion } from "framer-motion";
import Markdown from "react-markdown";
import type { Components, ExtraProps } from "react-markdown";
import {
  endsOnQuestion,
  isQuoteReference,
  textContent,
  withTypographicQuotes,
} from "@/components/conversation/answer-text";
import { riseIn } from "@/lib/motion";

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

export const Answer = memo(function Answer({ content }: { content: string }) {
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
