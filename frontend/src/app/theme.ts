export const THEME_STORAGE_KEY = "fitcv-theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme {
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === "light" || stored === "dark") {
        return stored;
      }
    } catch {
      // Storage access blocked or unavailable
    }
  }
  if (typeof document !== "undefined") {
    const existing = document.documentElement.dataset?.theme || document.documentElement.getAttribute("data-theme");
    if (existing === "light" || existing === "dark") {
      return existing;
    }
  }
  return "light";
}

export function applyTheme(theme: Theme): void {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
    if (document.documentElement.dataset) {
      document.documentElement.dataset.theme = theme;
    }
  }
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Storage access blocked or unavailable
    }
  }
}
