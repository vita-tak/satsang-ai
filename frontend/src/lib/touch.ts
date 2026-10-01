export function isTouchScreen(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

// On a touch screen the keyboard is still closing when a sent question is scrolled into view, so
// the view's height from before it opened is the one to judge by.
export function viewHeightWithoutKeyboard(heightBeforeKeyboard: number): number {
  return isTouchScreen() && heightBeforeKeyboard > 0 ? heightBeforeKeyboard : window.innerHeight;
}
