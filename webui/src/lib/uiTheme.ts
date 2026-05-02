/** Tema visual (tokens CSS vía `data-om-theme` en `<html>`). */

export const UI_THEME_IDS = ["midnight", "ocean", "ember", "forest", "paper"] as const;
export type UiThemeId = (typeof UI_THEME_IDS)[number];

const STORAGE_KEY = "om_web_ui_theme";

export function normalizeUiTheme(raw: unknown): UiThemeId {
  const s = String(raw ?? "")
    .trim()
    .toLowerCase();
  if ((UI_THEME_IDS as readonly string[]).includes(s)) return s as UiThemeId;
  return "midnight";
}

/** Aplica el tema en el documento y sincroniza caché local (anti-parpadeo al arrancar). */
export function applyUiThemeToDocument(theme: UiThemeId): void {
  if (typeof document === "undefined") return;
  if (theme === "midnight") {
    document.documentElement.removeAttribute("data-om-theme");
  } else {
    document.documentElement.setAttribute("data-om-theme", theme);
  }
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* ignore */
  }
}

export function readCachedUiTheme(): UiThemeId {
  if (typeof localStorage === "undefined") return "midnight";
  try {
    return normalizeUiTheme(localStorage.getItem(STORAGE_KEY));
  } catch {
    return "midnight";
  }
}
