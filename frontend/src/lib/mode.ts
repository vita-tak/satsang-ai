export const RESPONSE_MODES = ["satsang", "teachings", "self_inquiry", "ramana"] as const;

export type ResponseMode = (typeof RESPONSE_MODES)[number];

export const DEFAULT_MODE: ResponseMode = "satsang";

// sessionStorage rather than localStorage, so a new browser session starts from the default again.
const MODE_STORAGE_KEY = "responseMode";

export function isResponseMode(value: unknown): value is ResponseMode {
  return RESPONSE_MODES.includes(value as ResponseMode);
}

export function readStoredMode(): ResponseMode {
  try {
    const storedMode = sessionStorage.getItem(MODE_STORAGE_KEY);
    return isResponseMode(storedMode) ? storedMode : DEFAULT_MODE;
  } catch {
    // Storage can be unavailable (private browsing); the page then starts from the default.
    return DEFAULT_MODE;
  }
}

export function storeMode(mode: ResponseMode) {
  try {
    sessionStorage.setItem(MODE_STORAGE_KEY, mode);
  } catch {
    // Storage can be unavailable (private browsing); the choice then lasts for this page only.
  }
}
