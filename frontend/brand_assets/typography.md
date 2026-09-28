# Typography

## Two voices

The seeker and the guide speak in different typefaces, the way the recorded dialogues of the Talks
set questions and answers apart.

**EB Garamond: the guide's voice.** Georg Duffner's revival of Claude Garamond's sixteenth-century
book types (variable weight 400 to 800, with italic). It replaced Literata, which read as
e-book-technical: Garamond carries the humane, old-style texture of a printed book of dialogues and
settles into a still, even page of long text. Its small x-height means it is set larger than a
screen serif would be (19px on phones, 21px from 640px) at 1.6 leading. Used for answers, the
"Answering" state, the intro heading, the wordmark and the "Or begin with" note.

A broad comparison rendered a real answer in EB Garamond, Crimson Pro, Alegreya, Spectral,
Newsreader, Castoro, Brygada 1918, Libre Caslon Text, Sorts Mill Goudy, Gentium Book Plus, Source
Serif 4 and Cormorant Garamond, on both grounds. Spectral and Crimson Pro were close but still felt
screen-tuned; Alegreya was too lively for a still page; Cormorant is the meditation-app cliché and
too delicate for body text.

**Mukta: the seeker's voice and the interface.** A humanist sans from Ek Type, an Indian foundry;
the family also covers Devanagari and Tamil. Quiet and open, it stays out of the serif's way. Used
for the seeker's questions, the prompts, the intro line, the input, the Ask action and errors. Only
weight 400 is loaded: Mukta's Medium (500) has a spacing defect in capitals ("WITH" renders as
"WIT H"), so do not add it back.

Both load through `next/font/google` in `src/app/layout.tsx` as `--font-garamond` and
`--font-mukta`, exposed as the `font-serif` and `font-sans` utilities.

## Sanskrit transliteration

Sanskrit terms appear, but full IAST coverage (ā ī ū ṛ ḷ ṅ ñ ṭ ḍ ṇ ś ṣ ḥ ṃ) is a nice-to-have rather than
a hard requirement: it is rare in practice. Both current faces happen to cover it fully. Keep the
`latin-ext` subset in both font definitions so the glyphs load when they do appear.

## Scale

Sizes are theme tokens in `globals.css`. The default Tailwind scale is reset, so these are the only
text sizes.

| Utility              | Size    | Line height | Use                                               |
| -------------------- | ------- | ----------- | ------------------------------------------------- |
| `text-display`       | 34px    | 1.15        | Intro heading on phones                           |
| `text-display-lg`    | 44px    | 1.12        | Intro heading from 640px                          |
| `text-reading`       | 19px    | 1.6         | Answers and "Answering" on phones                |
| `text-reading-lg`    | 21px    | 1.6         | Answers and "Answering" from 640px               |
| `text-body`          | 17px    | 1.6         | Seeker's voice and interface on phones            |
| `text-body-lg`       | 18px    | 1.6         | Seeker's voice from 640px                         |
| `text-note`          | 15px    | 1.5         | "Or begin with" (EB Garamond italic), errors      |
| `text-label`         | 12px    | 1.4         | "Ask" (uppercase, 0.16em tracking)                |

Rules:
- Input text never goes below 16px, or iOS zooms the page on focus.
- Answers use old-style figures and `text-wrap: pretty`; the heading uses `text-wrap: balance`.
- Ramana's quoted words (markdown blockquotes) are italic and indented 1.25em, with no border.
- The closing question of an answer gets 2em of space above it and the hanging ember point. The
  model often sets that question in bold; bold inside it is neutralised, because the space and the
  point already set it apart and heavy type would make the page's resting point shout.
- Headings inside answers are set at text size in semibold. The answer never shouts.
- The guide's text uses typographic quotes (“ ” ‘ ’), converted from the model's straight quotes by
  `withTypographicQuotes` in `page.tsx`. Em dashes come from the model and are left as written.
