import type { ExtraProps } from "react-markdown";

const OPENING_DOUBLE_QUOTE = /(^|[\s([*_\u2014])"/g;
const OPENING_SINGLE_QUOTE = /(^|[\s([*_\u2014])'/g;

export function withTypographicQuotes(text: string): string {
  return text
    .replace(OPENING_DOUBLE_QUOTE, "$1\u201c")
    .replace(/"/g, "\u201d")
    .replace(OPENING_SINGLE_QUOTE, "$1\u2018")
    .replace(/'/g, "\u2019");
}

// A final question mark, allowing closing emphasis, quotes or brackets after it.
const QUESTION_ENDING = /\?[*_"'\u201d\u2019)\]]*$/;

export function endsOnQuestion(markdown: string): boolean {
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

export function isQuoteReference(text: string): boolean {
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

export function textContent(node: MarkdownChild): string {
  if (node.type === "text") {
    return node.value;
  }
  if (node.type === "element") {
    return node.children.map(textContent).join("");
  }
  return "";
}
