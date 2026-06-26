import { get, writable } from "svelte/store";
import { copyTextToClipboard } from "./clipboardText";

export type GalleryDebugKind =
  | "scroll"
  | "scroll_drag"
  | "rail_jump"
  | "prefetch"
  | "load_lq"
  | "load_hq"
  | "user"
  | "window";

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

function pushEntry(kind: GalleryDebugKind, message: string, detail?: Record<string, unknown>) {
  if (!get(galleryDebugLogEnabled)) return;
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
