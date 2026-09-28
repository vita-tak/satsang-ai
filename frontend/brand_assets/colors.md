# Colors

Two flat grounds and one accent. No texture, no gradients except the fade above the composer, no
shadows.

- **Ash** (light theme): a stone-grey ground at L\* 87, deliberately neither white nor cream. It
  reads like e-ink or sacred ash (vibhuti): low glare, still.
- **Char** (dark theme): a warm near-black at L\* 5, like a lamp-lit hall at night. Not pure black,
  which smears on OLED screens while scrolling.
- **Ember**: the only saturated colour. Burnt rust on Ash, a glowing ember on Char.

## Tokens

| Token       | Light (Ash) | Contrast | Dark (Char) | Contrast | Role                                        |
| ----------- | ----------- | -------- | ----------- | -------- | ------------------------------------------- |
| `ground`    | `#dad9d5`   |          | `#131211`   |          | Page background                             |
| `ink`       | `#1c1b19`   | 12.2:1   | `#ddd8ce`   | 13.2:1   | Answers, headings, wordmark, typed input    |
| `ink-soft`  | `#45413b`   | 7.2:1    | `#a8a195`   | 7.3:1    | The seeker's words, intro line, prompts     |
| `ink-faint` | `#5c5750`   | 5.1:1    | `#858075`   | 4.8:1    | Labels, placeholder, idle controls, bullets |
| `rule`      | `#b9b7b2`   | 1.4:1    | `#34312d`   | 1.5:1    | Hairlines only (composer underline). Never text |
| `accent`    | `#963e13`   | 5.0:1    | `#e2894f`   | 7.1:1    | Ember: the point, Ask, focus, caret         |
| `error`     | `#94281e`   | 5.8:1    | `#ef8a7a`   | 7.7:1    | Inline error text                           |

Contrast is WCAG 2 against the ground of the same theme. Every text token passes AA (4.5:1); `ink`
and `ink-soft` pass AAA (7:1). Dark `ink` is intentionally softer than near-white: long reading on a
dark ground glares above about 13:1.

**Ember outside the page.** The favicon cannot follow the theme, so it uses a middle ember,
`#c8683a`, which keeps at least 3:1 against common browser chrome (3.8:1 on white, 4.2:1 on a dark
tab bar, about 3:1 on grey tab strips). `mark.svg` switches between the two theme embers itself.

## Mechanism

Each token is defined once, with both values side by side:

```css
:root {
  color-scheme: light dark;
  --ground: light-dark(#dad9d5, #131211);
}
:root[data-theme="light"] { color-scheme: light; }
:root[data-theme="dark"] { color-scheme: dark; }
```

- `color-scheme: light dark` makes the system preference (`prefers-color-scheme`) the default.
- The theme toggle writes `data-theme` on `<html>` and stores the choice in `localStorage`; a small
  inline script in `<head>` re-applies it before first paint, so a reload never flashes.
- Tailwind's Lightning CSS pass compiles `light-dark()` into a `prefers-color-scheme` polyfill that
  still honours `data-theme`, so it works in every browser Tailwind targets.
- `@theme inline` maps the tokens to utilities (`bg-ground`, `text-ink`, ...). The default Tailwind
  palette is reset with `--color-*: initial`, so no other colour utilities exist.

## Adding or changing a colour

1. Change it in `src/app/globals.css` first; that file is the source of truth.
2. Check contrast against both grounds. Text needs 4.5:1; meaningful non-text marks need 3:1.
3. Update this table, `tokens.json`, and, for `ground`, the `themeColor` values in `layout.tsx`.
4. Do not add a second accent. If something needs attention, it is either ember or it is text.
