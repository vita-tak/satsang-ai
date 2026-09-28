type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "theme";

// Inlined in <head> so a stored choice is applied before first paint and never flashes the system theme.
export const THEME_INIT_SCRIPT = `try {
  var theme = localStorage.getItem("${THEME_STORAGE_KEY}");
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
} catch (error) {}`;

function getActiveTheme(): Theme {
  const chosenTheme = document.documentElement.dataset.theme;
  if (chosenTheme === "light" || chosenTheme === "dark") {
    return chosenTheme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Storage can be unavailable (private browsing); the choice then lasts for this visit only.
  }
}

export function toggleTheme() {
  const nextTheme: Theme = getActiveTheme() === "dark" ? "light" : "dark";
  if (typeof document.startViewTransition !== "function") {
    applyTheme(nextTheme);
    return;
  }
  document.startViewTransition(() => applyTheme(nextTheme));
}
