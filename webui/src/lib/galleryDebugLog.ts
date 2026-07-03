import { get, writable } from "svelte/store";
import type { GalleryItem } from "./api";
import { copyTextToClipboard } from "./clipboardText";
import { isGallerySelectableKind } from "./galleryUtils";

export type GalleryDebugKind =
  | "scroll"
  | "scroll_drag"
  | "rail_jump"
  | "prefetch"
  | "load_lq"
  | "load_hq"
  | "user"
  | "window"
  | "selection"
  | "selection_reset"
  | "sort";

export const GALLERY_DEBUG_KINDS: GalleryDebugKind[] = [
  "scroll",
  "scroll_drag",
  "rail_jump",
  "prefetch",
  "load_lq",
  "load_hq",
  "user",
  "window",
  "selection",
  "selection_reset",
  "sort",
];

export type GalleryDebugFilters = Record<GalleryDebugKind, boolean>;

export const DEFAULT_GALLERY_DEBUG_FILTERS: GalleryDebugFilters = {
  scroll: true,
  scroll_drag: true,
  rail_jump: true,
  prefetch: true,
  load_lq: true,
  load_hq: true,
  user: true,
  window: true,
  selection: true,
  selection_reset: true,
  sort: true,
};

export type GalleryDebugEntry = {
  id: number;
  ts: number;
  kind: GalleryDebugKind;
  message: string;
  detail?: Record<string, unknown>;
};

const MAX_ENTRIES = 500;
let nextId = 1;
const entries: GalleryDebugEntry[] = [];

export const galleryDebugLogEnabled = writable(false);
export const galleryDebugLogEntries = writable<GalleryDebugEntry[]>([]);
export const galleryDebugFilters = writable<GalleryDebugFilters>({ ...DEFAULT_GALLERY_DEBUG_FILTERS });

export function normalizeGalleryDebugFilters(raw: unknown): GalleryDebugFilters {
  const out = { ...DEFAULT_GALLERY_DEBUG_FILTERS };
  if (!raw || typeof raw !== "object") return out;
  for (const kind of GALLERY_DEBUG_KINDS) {
    const v = (raw as Record<string, unknown>)[kind];
    if (typeof v === "boolean") out[kind] = v;
  }
  return out;
}

function isKindEnabled(kind: GalleryDebugKind): boolean {
  return get(galleryDebugFilters)[kind] !== false;
}

function selectedPaths(items: GalleryItem[]): string[] {
  return items.filter((x) => isGallerySelectableKind(x.kind) && x.selected).map((x) => x.path);
}

export function logGallerySelectionDelta(
  source: string,
  prevItems: GalleryItem[],
  nextItems: GalleryItem[],
  extra?: Record<string, unknown>,
) {
  const prev = selectedPaths(prevItems);
  const next = selectedPaths(nextItems);
  if (prev.length === next.length && prev.every((p) => next.includes(p))) return;

  const lost = prev.filter((p) => !next.includes(p));
  const gained = next.filter((p) => !prev.includes(p));
  const detail: Record<string, unknown> = {
    source,
    prevCount: prev.length,
    nextCount: next.length,
    ...extra,
  };
  if (gained.length > 0) {
    detail.gainedCount = gained.length;
    if (gained.length <= 8) detail.gained = gained;
    else {
      detail.gainedSample = gained.slice(0, 8);
      detail.gainedOmitted = gained.length - 8;
    }
  }
  if (lost.length > 0) {
    detail.lostCount = lost.length;
    if (lost.length <= 8) detail.lost = lost;
    else {
      detail.lostSample = lost.slice(0, 8);
      detail.lostOmitted = lost.length - 8;
    }
  }

  const userSources = new Set([
    "selection:click_toggle",
    "selection:range",
    "selection:clear",
    "selection:invert",
    "selection:keyboard_range",
    "selection:ctrl_toggle",
    "selection:select_page",
  ]);
  const isUser = userSources.has(source);
  const kind: GalleryDebugKind =
    lost.length > 0 && !isUser ? "selection_reset" : "selection";

  pushEntry(kind, source, detail);
}

function pushEntry(kind: GalleryDebugKind, message: string, detail?: Record<string, unknown>) {
  if (!get(galleryDebugLogEnabled)) return;
  if (!isKindEnabled(kind)) return;
  const row: GalleryDebugEntry = {
    id: nextId++,
    ts: Date.now(),
    kind,
    message,
    detail: detail && Object.keys(detail).length > 0 ? detail : undefined,
  };
  entries.push(row);
  while (entries.length > MAX_ENTRIES) entries.shift();
  galleryDebugLogEntries.set([...entries]);
}

export function setGalleryDebugLogEnabled(enabled: boolean) {
  galleryDebugLogEnabled.set(Boolean(enabled));
}

export function setGalleryDebugFilters(filters: GalleryDebugFilters) {
  galleryDebugFilters.set(normalizeGalleryDebugFilters(filters));
}

export function setGalleryDebugFilter(kind: GalleryDebugKind, enabled: boolean) {
  galleryDebugFilters.update((f) => ({ ...f, [kind]: Boolean(enabled) }));
}

export function galleryDbg(
  kind: GalleryDebugKind,
  message: string,
  detail?: Record<string, unknown>,
) {
  pushEntry(kind, message, detail);
}

export function clearGalleryDebugLog() {
  entries.length = 0;
  galleryDebugLogEntries.set([]);
}

function formatTs(ts: number): string {
  const d = new Date(ts);
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`;
}

export function formatGalleryDebugLogText(rows = entries): string {
  return rows
    .map((e) => {
      const detail = e.detail ? ` ${JSON.stringify(e.detail)}` : "";
      return `[${formatTs(e.ts)}] ${e.kind.toUpperCase()} ${e.message}${detail}`;
    })
    .join("\n");
}

export async function copyGalleryDebugLog(): Promise<boolean> {
  const text = formatGalleryDebugLogText();
  if (!text) return false;
  return copyTextToClipboard(text);
}
