# Motion

Motion is slow, settling and never playful. Things only move when they arrive or leave. The page is
otherwise still.

## The breath curve

Every transition uses one curve, a sine ease-in-out: `cubic-bezier(0.37, 0, 0.63, 1)`. Movement
starts at rest and ends at rest, like a breath. It is `EASE_BREATH` in `page.tsx` and `--breath` /
the `ease-breath` utility in CSS.

An ease-out curve was tried first and rejected: it front-loads the change (about 58% opacity after a
quarter of the duration), so even long fades felt abrupt.

## What moves

| Moment                    | Motion                                                        | Tool          |
| ------------------------- | ------------------------------------------------------------- | ------------- |
| Page load                 | Intro settles in: fade and 8px rise, 0.14s stagger, 1.2s each | Framer Motion |
| First question sent       | Intro fades out over 0.7s, then the conversation appears      | Framer Motion |
| A question appears        | Fade in over 0.8s                                             | Framer Motion |
| Waiting for the answer    | "Answering" fades in after 0.4s, then pulses (opacity 0.35 to 1, 4s loop) | Framer Motion + CSS |
| The answer arrives        | "Answering" fades out (0.4s), then the answer fades and rises 8px over 1.2s | Framer Motion |
| Hover and focus           | Colour and opacity transitions, 500ms                        | CSS           |
| Theme toggle              | Whole-page cross-fade over 700ms (View Transitions API)       | CSS           |

Framer Motion handles presence (arriving and leaving). One default transition is set once in
`MotionConfig`; only durations are overridden. CSS handles the ambient loop and hover states.

## What never moves

- Nothing bounces, springs, scales up or slides in from the side. Movement is at most 8px, and only
  upward on arrival.
- Nothing animates on scroll, and nothing moves to attract attention.
- Nothing already on the page re-animates when new content arrives. The question never shifts when
  its answer lands.

## Reduced motion

- `MotionConfig reducedMotion="user"` drops all movement and keeps the fades.
- The "Answering" pulse animates only opacity, so it stays as a quiet loading signal.
- The theme cross-fade is disabled, so the switch is instant.
- Scrolling to a new question is instant instead of smooth.

## Tools not used

- **Three.js:** a WebGL scene would add motion, bundle weight and battery drain to a page whose
  point is stillness.
- **GSAP:** a second animation engine is unnecessary; Framer Motion plus CSS covers every case above.
