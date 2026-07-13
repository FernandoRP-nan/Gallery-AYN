/** Apariencia global: temas (preset + personalizados), tipografía e imagen de fondo. */

import { buildMediaFileUrl } from "./pathUtils";
import { UI_THEME_IDS, normalizeUiTheme, type UiThemeId } from "./uiTheme";

export const UI_FONT_IDS = ["outfit", "system", "inter", "serif", "mono"] as const;
export type UiFontId = (typeof UI_FONT_IDS)[number];

export const THEME_COLOR_FIELDS = [
  "bgBase",
  "bgElevated",
  "surface1",
  "surface2",
  "textPrimary",
  "textSecondary",
  "accent",
  "accent2",
] as const;

export type ThemeColorField = (typeof THEME_COLOR_FIELDS)[number];
export type ThemeColors = Record<ThemeColorField, string>;

export type CustomTheme = {
  id: string;
  name: string;
  colors: ThemeColors;
};

export type ThemeSelection = UiThemeId | `custom:${string}`;

export const PRESET_SWATCH: Record<UiThemeId, string> = {
  midnight: "#7c8cff",
  ocean: "#38b8e8",
  ember: "#ff8a65",
  forest: "#5ecf8a",
  paper: "#4c5dff",
};

export const PRESET_COLORS: Record<UiThemeId, ThemeColors> = {
  midnight: {
    bgBase: "#07080f",
    bgElevated: "#10121c",
    surface1: "#15182a",
    surface2: "#1c2036",
    textPrimary: "#eef0fb",
    textSecondary: "#a8b0d8",
    accent: "#7c8cff",
    accent2: "#5ee4d4",
  },
  ocean: {
    bgBase: "#06121c",
    bgElevated: "#0c1a2a",
    surface1: "#122536",
    surface2: "#183044",
    textPrimary: "#e8f4ff",
    textSecondary: "#9ec8e8",
    accent: "#38b8e8",
    accent2: "#5ee4d4",
  },
  ember: {
    bgBase: "#100b0a",
    bgElevated: "#1a1210",
    surface1: "#241a16",
    surface2: "#2e221c",
    textPrimary: "#fff5f0",
    textSecondary: "#d8c4b8",
    accent: "#ff8a65",
    accent2: "#ffd54f",
  },
  forest: {
    bgBase: "#080f0c",
    bgElevated: "#0d1612",
    surface1: "#14221c",
    surface2: "#1a2e26",
    textPrimary: "#eef7f2",
    textSecondary: "#a8c9b8",
    accent: "#5ecf8a",
    accent2: "#7dd3c0",
  },
  paper: {
    bgBase: "#eef0f6",
    bgElevated: "#ffffff",
    surface1: "#e4e8f2",
    surface2: "#dce2ef",
    textPrimary: "#1a1d2e",
    textSecondary: "#4a5068",
    accent: "#4c5dff",
    accent2: "#0891b2",
  },
};

const FONT_STACKS: Record<UiFontId, string> = {
  outfit: '"Outfit", "Segoe UI", system-ui, sans-serif',
  system: '"Segoe UI", system-ui, -apple-system, sans-serif',
  inter: '"Inter", "Segoe UI", system-ui, sans-serif',
  serif: '"Source Serif 4", Georgia, "Times New Roman", serif',
  mono: '"JetBrains Mono", ui-monospace, "Cascadia Code", monospace',
};

const FONT_LINKS: Partial<Record<UiFontId, string>> = {
  inter: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
  serif: "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap",
  mono: "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap",
};

const STORAGE_KEY = "om_web_ui_appearance";

const CUSTOM_CSS_VARS = [
  "--om-bg-base",
  "--om-bg-elevated",
  "--om-surface-1",
  "--om-surface-2",
  "--om-surface-3",
  "--om-text-primary",
  "--om-text-secondary",
  "--om-text-muted",
  "--om-accent",
  "--om-accent-soft",
  "--om-accent-glow",
  "--om-accent-2",
  "--om-bg-spot",
  "--om-border-subtle",
  "--om-border-default",
] as const;

export type UiAppearanceState = {
  themeSelection: ThemeSelection;
  customThemes: CustomTheme[];
  font: UiFontId;
  bgImagePath: string;
  bgBlur: number;
};

export function defaultAppearance(): UiAppearanceState {
  return {
    themeSelection: "midnight",
    customThemes: [],
    font: "outfit",
    bgImagePath: "",
    bgBlur: 0,
  };
}

export function generateThemeId(): string {
  return `t${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`;
}

export function parseThemeSelection(raw: unknown): ThemeSelection {
  const s = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (s.startsWith("custom:") && s.length > 7) return s as `custom:${string}`;
  return normalizeUiTheme(s);
}

function parseHexColor(raw: unknown, fallback: string): string {
  const s = String(raw ?? "")
    .trim()
    .toLowerCase();
  return /^#[0-9a-f]{6}$/.test(s) ? s : fallback;
}

export function normalizeThemeColors(raw: unknown, fallback: ThemeColors = PRESET_COLORS.midnight): ThemeColors {
  const row = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const out = { ...fallback };
  for (const key of THEME_COLOR_FIELDS) {
    out[key] = parseHexColor(row[key], fallback[key]);
  }
  return out;
}

export function parseCustomThemes(raw: unknown): CustomTheme[] {
  if (!Array.isArray(raw)) return [];
  const out: CustomTheme[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const id = String(row.id ?? "").trim();
    const name = String(row.name ?? "").trim();
    if (!id || !name) continue;
    let colors: ThemeColors;
    if (row.colors && typeof row.colors === "object") {
      colors = normalizeThemeColors(row.colors);
    } else {
      const base = normalizeUiTheme(row.basePreset);
      colors = { ...PRESET_COLORS[base] };
      const accentRaw = String(row.accent ?? "").trim();
      if (/^#[0-9a-f]{6}$/i.test(accentRaw)) colors.accent = accentRaw.toLowerCase();
    }
    out.push({ id, name, colors });
  }
  return out;
}

export function createCustomThemeFromColors(name: string, colors: ThemeColors): CustomTheme {
  return { id: generateThemeId(), name, colors: { ...colors } };
}

export function duplicatePresetAsCustom(name: string, preset: UiThemeId): CustomTheme {
  return createCustomThemeFromColors(name, { ...PRESET_COLORS[preset] });
}

export function normalizeFont(raw: unknown): UiFontId {
  const s = String(raw ?? "")
    .trim()
    .toLowerCase();
  if ((UI_FONT_IDS as readonly string[]).includes(s)) return s as UiFontId;
  return "outfit";
}

export function normalizeBgBlur(raw: unknown): number {
  const n = Number(raw);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(32, Math.round(n)));
}

export function isCustomThemeActive(selection: ThemeSelection, id: string): boolean {
  return selection === `custom:${id}`;
}

function hexToAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "").trim();
  if (!/^[0-9a-f]{6}$/i.test(h)) return `rgb(124 140 255 / ${alpha})`;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgb(${r} ${g} ${b} / ${alpha})`;
}

function isLightHex(hex: string): boolean {
  const h = hex.replace("#", "");
  if (h.length !== 6) return false;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150;
}

function clearCustomThemeVars(root: HTMLElement): void {
  for (const key of CUSTOM_CSS_VARS) root.style.removeProperty(key);
}

function applyCustomThemeColors(root: HTMLElement, colors: ThemeColors): void {
  const light = isLightHex(colors.bgBase);
  root.style.setProperty("--om-bg-base", colors.bgBase);
  root.style.setProperty("--om-bg-elevated", colors.bgElevated);
  root.style.setProperty("--om-surface-1", colors.surface1);
  root.style.setProperty("--om-surface-2", colors.surface2);
  root.style.setProperty("--om-surface-3", colors.surface2);
  root.style.setProperty("--om-text-primary", colors.textPrimary);
  root.style.setProperty("--om-text-secondary", colors.textSecondary);
  root.style.setProperty("--om-text-muted", hexToAlpha(colors.textSecondary, light ? 0.72 : 0.62));
  root.style.setProperty("--om-accent", colors.accent);
  root.style.setProperty("--om-accent-soft", hexToAlpha(colors.accent, 0.2));
  root.style.setProperty("--om-accent-glow", hexToAlpha(colors.accent, 0.35));
  root.style.setProperty("--om-accent-2", colors.accent2);
  root.style.setProperty("--om-bg-spot", hexToAlpha(colors.accent, light ? 0.08 : 0.12));
  if (light) {
    root.style.setProperty("--om-border-subtle", "rgb(0 0 0 / 0.06)");
    root.style.setProperty("--om-border-default", "rgb(0 0 0 / 0.1)");
  } else {
    root.style.removeProperty("--om-border-subtle");
    root.style.removeProperty("--om-border-default");
  }
}

function ensureFontLink(font: UiFontId): void {
  if (typeof document === "undefined") return;
  const href = FONT_LINKS[font];
  if (!href) return;
  const id = `om-font-${font}`;
  if (document.getElementById(id)) return;
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

let lastThemeKey = "";
let lastBgKey = "";
let lastPersistKey = "";
let persistTimer: ReturnType<typeof setTimeout> | null = null;

/** Aplica solo tema y tipografía (sin tocar fondo). */
export function applyThemeAppearance(
  state: Pick<UiAppearanceState, "themeSelection" | "customThemes" | "font">
): void {
  if (typeof document === "undefined") return;
  const key = JSON.stringify({
    themeSelection: state.themeSelection,
    customThemes: state.customThemes,
    font: state.font,
  });
  if (key === lastThemeKey) return;
  lastThemeKey = key;

  const root = document.documentElement;
  const customId = state.themeSelection.startsWith("custom:") ? state.themeSelection.slice(7) : "";
  const custom = state.customThemes.find((t) => t.id === customId);

  if (custom) {
    root.removeAttribute("data-om-theme");
    applyCustomThemeColors(root, custom.colors);
  } else {
    clearCustomThemeVars(root);
    const preset = state.themeSelection as UiThemeId;
    if (preset === "midnight") root.removeAttribute("data-om-theme");
    else root.setAttribute("data-om-theme", preset);
  }

  root.style.setProperty("--om-font-sans", FONT_STACKS[state.font]);
  ensureFontLink(state.font);
}

/** Aplica solo imagen de fondo y desenfoque (CSS vars; sin re-tematizar). */
export function applyBackgroundAppearance(bgImagePath: string, bgBlur: number): void {
  if (typeof document === "undefined") return;
  const path = String(bgImagePath ?? "").trim();
  const blur = normalizeBgBlur(bgBlur);
  const key = `${path}\0${blur}`;
  if (key === lastBgKey) return;
  lastBgKey = key;

  const root = document.documentElement;
  if (path) {
    root.setAttribute("data-om-has-bg", "1");
    const url = buildMediaFileUrl(path);
    root.style.setProperty("--om-bg-image", `url("${url.replace(/"/g, '\\"')}")`);
  } else {
    root.removeAttribute("data-om-has-bg");
    root.style.removeProperty("--om-bg-image");
  }
  root.style.setProperty("--om-bg-blur", `${blur}px`);
}

/** Persistencia en localStorage con debounce (evita parpadeos al mover sliders). */
export function queueAppearancePersist(state: UiAppearanceState): void {
  if (typeof localStorage === "undefined") return;
  const key = JSON.stringify(state);
  if (key === lastPersistKey) return;
  lastPersistKey = key;
  if (persistTimer !== null) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    persistTimer = null;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      localStorage.setItem("om_web_ui_theme", state.themeSelection);
    } catch {
      /* ignore */
    }
  }, 400);
}

/** Aplica tema, fuente y fondo en el documento (y caché local anti-parpadeo). */
export function applyAppearanceToDocument(state: UiAppearanceState): void {
  lastThemeKey = "";
  lastBgKey = "";
  lastPersistKey = "";
  applyThemeAppearance(state);
  applyBackgroundAppearance(state.bgImagePath, state.bgBlur);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    localStorage.setItem("om_web_ui_theme", state.themeSelection);
  } catch {
    /* ignore */
  }
}

export function readCachedAppearance(): Partial<UiAppearanceState> {
  if (typeof localStorage === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const data = JSON.parse(raw) as Partial<UiAppearanceState>;
      return {
        themeSelection: data.themeSelection ? parseThemeSelection(data.themeSelection) : undefined,
        customThemes: data.customThemes ? parseCustomThemes(data.customThemes) : undefined,
        font: data.font ? normalizeFont(data.font) : undefined,
        bgImagePath: typeof data.bgImagePath === "string" ? data.bgImagePath : undefined,
        bgBlur: data.bgBlur !== undefined ? normalizeBgBlur(data.bgBlur) : undefined,
      };
    }
    const legacy = localStorage.getItem("om_web_ui_theme");
    if (legacy) return { themeSelection: parseThemeSelection(legacy) };
  } catch {
    /* ignore */
  }
  return {};
}

export function appearanceFromSettings(settings: Record<string, unknown> | undefined | null): UiAppearanceState {
  const base = defaultAppearance();
  if (!settings) return base;
  return {
    themeSelection: parseThemeSelection(settings.web_ui_theme),
    customThemes: parseCustomThemes(settings.web_ui_custom_themes),
    font: normalizeFont(settings.web_ui_font),
    bgImagePath: String(settings.web_ui_bg_image ?? "").trim(),
    bgBlur: normalizeBgBlur(settings.web_ui_bg_blur),
  };
}

export { UI_THEME_IDS };
