# Satsang AI: visual identity

This folder preserves the visual language of Satsang AI. Read it before changing anything visual.
The implementation lives in `src/app/globals.css` (tokens), `src/app/layout.tsx` (fonts, theme
bootstrap) and `src/app/page.tsx` (components).

| File                             | What it holds                                                    |
| -------------------------------- | ---------------------------------------------------------------- |
| [colors.md](colors.md)           | The palette, its roles, contrast ratios and the theming mechanism |
| [typography.md](typography.md)   | Typefaces, the two voices, the type scale, Sanskrit coverage      |
| [motion.md](motion.md)           | The breath curve, what moves and what never moves                 |
| [tokens.json](tokens.json)       | Machine-readable tokens (Design Tokens Community Group format)     |
| [mark.svg](mark.svg)             | The ember point, the only brand mark                              |
| [reference/](reference/)         | Reference screenshots: mobile and desktop, light and dark         |

## The idea

**The page, not the app.** Satsang means sitting in the company of truth. Every answer is grounded in
*Talks with Sri Ramana Maharshi*, a book of recorded dialogues, so the interface is typeset like that
book, read by lamplight: one column of text, the seeker's question and the guide's answer, and
nothing else asking for attention.

**The ember point.** One motif carries the identity: a single point of attention (a bindu). It
echoes the image from *Who am I?* of the stick that stirs the pyre and is itself consumed, and the
flame on Arunachala. The point appears in exactly these places:

1. Before the wordmark, as the brand mark.
2. In the margin before each answer's closing question. The guide always ends with a single question
   that points inward, so the page always comes to rest on it.
3. Beside a suggested prompt on hover or keyboard focus, and as the focus outline and text caret.

## Principles

1. **Stillness first.** Nothing moves unless something arrived or left. The only loop on the page is
   the slow pulse of "Answering" while an answer is on its way.
2. **Text is the interface.** No bubbles, cards, boxes, avatars, pills or rounded corners. Hierarchy
   comes only from typeface, size, colour and space.
3. **Two voices.** The guide speaks in EB Garamond (serif). The seeker and the interface speak in Mukta
   (sans). Never swap them.
4. **One accent, used sparingly.** Ember is the only saturated colour. If more than a few ember
   marks are visible at once, something is wrong.
5. **Answers come to rest on their question.** The closing question gets space above it and the
   hanging point. Do not add anything after it.

## Layout

- One flush-left column with a reading measure of 39rem (`max-w-measure`), centred on wide screens.
  Gutters are 24px on phones and 32px from 640px. Wider screens only get more margin, never more
  columns.
- The header is peripheral and scrolls away: the point and "Satsang" on the left, the theme toggle
  on the right.
- The intro (empty state) is vertically centred, in this order: heading, one line of orientation,
  the composer, "Or begin with", four rotating prompts as plain text rows. Asking is the primary
  path; the prompts are the alternative.
- Once the first question is sent, the intro dissolves and the composer reappears pinned to the
  bottom: a textarea on a single underline, the word "Ask", and a short fade above so text dissolves
  instead of being cut off. There is only ever one composer on the page.
- Every interactive element is at least 44 by 44px.

## Voice and copy

- Plain, quiet, direct. No exclamation marks, no emojis, no em dashes, no marketing words.
- Heading: "Sit with a question."
- Orientation: "An AI guide to self-inquiry in the tradition of Ramana Maharshi. Ask about the
  teachings, the practice, or a Sanskrit term." This sentence carries the AI disclosure; keep it.
- Label "Or begin with", placeholder "Ask a question…" (with a true ellipsis), action "Ask".
- While the guide answers: "Answering", in the guide's voice at answer size and colour, pulsing
  slowly. It is visible text, so screen readers announce it through the conversation log.
- Errors lead with a human line and a next step, "The answer did not come through. Please ask
  again.", with the technical detail below it in `ink-faint`.
- The guide's answers are set with typographic quotes (“ ” ‘ ’); the model writes straight ones, so
  `withTypographicQuotes` in `page.tsx` converts them. The seeker's words are shown as typed.
- The visible wordmark is "Satsang". The product name in the page title stays "Satsang AI".

## Do and do not

Do:
- Use only brand utilities: `bg-ground`, `text-ink`, `text-ink-soft`, `text-ink-faint`,
  `border-rule`, `text-accent`, `text-error`, `font-serif`, `font-sans`, `text-label`, `text-note`,
  `text-body`, `text-reading`, `text-display`, `ease-breath`, `animate-breathe`.
- Let the tokens switch themes. Both themes come from the same classes.
- Check every new text colour for at least 4.5:1 contrast in both themes.

Do not:
- Use the `dark:` variant. It follows only the system setting and ignores the reader's toggle.
- Reach for Tailwind's default palette, sizes or radii. They are reset and no longer exist.
- Add a second accent colour, gradients (other than the composer fade), textures, shadows or glows.
- Use springs, bounces, scale pops or anything faster than about half a second for things arriving.
- Put the seeker's words in the serif or the guide's words in the sans.
- Use off-white or cream grounds, pill buttons, cards, or a calm-app look with rounded corners.

## Reference screenshots

The finished design, captured with Playwright. The answer is a real response from the backend
(question: "What is the nature of the Self?"). Compare new visual work against these.

| File                       | Viewport          | Shows                                              |
| -------------------------- | ----------------- | -------------------------------------------------- |
| `mobile-light-intro.png`   | 390x844 at 2x     | The empty state on Ash                             |
| `mobile-dark-intro.png`    | 390x844 at 2x     | The empty state on Char                            |
| `mobile-light-answer.png`  | 390x844 at 2x     | The end of an answer: the closing question at rest |
| `mobile-dark-answer.png`   | 390x844 at 2x     | The same on Char                                   |
| `desktop-light-intro.png`  | 1440x900          | The empty state, centred column                    |
| `desktop-dark-intro.png`   | 1440x900          | The same on Char                                   |
| `desktop-light-answer.png` | 1440x900          | A question and the opening of its answer           |
| `desktop-dark-answer.png`  | 1440x900          | The same on Char                                   |

## Maintenance

`src/app/globals.css` is the source of truth. When a token changes, update in the same change:
`globals.css`, [tokens.json](tokens.json), [colors.md](colors.md) (including the contrast table),
and the `themeColor` values in `src/app/layout.tsx`, which must equal the two `ground` values.
