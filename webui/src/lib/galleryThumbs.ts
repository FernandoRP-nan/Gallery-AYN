import { get, writable } from "svelte/store";
import { bridge } from "./api";
import type { GalleryItem } from "./api";
import {
  hasGalleryThumbHq,
  setGalleryThumbHq,
  clearGalleryThumbHqCache,
} from "./galleryThumbHqCache";
import { getGalleryNavigationGeneration, isGalleryNavigationCurrent } from "./gallerySession";
import { getGalleryItems } from "./galleryRuntime";
import { galleryScrolling } from "./galleryScrollState";

/** True mientras corre la hidratación HQ (para estabilizar el chrome de la UI). */
export const galleryThumbHydrating = writable(false);

let galleryThumbHydrationToken = 0;
let pendingGalleryThumbHq = new Map<string, string>();
let galleryThumbFlushTimer: ReturnType<typeof setTimeout> | null = null;
let galleryThumbFlushToken = 0;
let scrollFlushDeferrals = 0;
/** Intervalo de lote al aplicar HQ (ms). */
const THUMB_FLUSH_MS = 96;
const THUMB_FLUSH_SCROLL_RETRY_MS = 120;
const MAX_SCROLL_FLUSH_DEFERRALS = 48;

function prioritizePathsByViewport(paths: string[], selector: string, attrName: string): string[] {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>(selector));
  if (nodes.length === 0) return paths;
  const nodeByPath = new Map<string, HTMLElement>();
  for (const n of nodes) {
    const p = n.dataset[attrName];
    if (p) nodeByPath.set(p, n);
  }
  const visible: string[] = [];
  const rest: string[] = [];
  for (const p of paths) {
    const el = nodeByPath.get(p);
    if (!el) {
      rest.push(p);
      continue;
    }
    const r = el.getBoundingClientRect();
    const isVisible = r.bottom > 0 && r.right > 0 && r.top < window.innerHeight && r.left < window.innerWidth;
    (isVisible ? visible : rest).push(p);
  }
  return [...visible, ...rest];
}

/** Precarga/decodifica data-URLs antes de tocar el DOM (evita parpadeo al cambiar src). */
function preloadDataUrl(url: string): Promise<boolean> {
  return Promise.race([
    new Promise<boolean>((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.decoding = "async";
      img.src = url;
    }),
    new Promise<boolean>((resolve) => setTimeout(() => resolve(false), 12000)),
  ]);
}

export function cancelPendingGalleryThumbFlush() {
  pendingGalleryThumbHq.clear();
  scrollFlushDeferrals = 0;
  if (galleryThumbFlushTimer !== null) {
    clearTimeout(galleryThumbFlushTimer);
    galleryThumbFlushTimer = null;
  }
}

export function bumpGalleryThumbHydrationToken(clearCache = false): number {
  galleryThumbHydrationToken++;
  cancelPendingGalleryThumbFlush();
  if (clearCache) clearGalleryThumbHqCache();
  return galleryThumbHydrationToken;
}

export function getGalleryThumbHydrationToken(): number {
  return galleryThumbHydrationToken;
}

async function flushPendingGalleryThumbs(token: number, force = false) {
  if (galleryThumbHydrationToken !== token) {
    pendingGalleryThumbHq.clear();
    scrollFlushDeferrals = 0;
    return;
  }
  if (pendingGalleryThumbHq.size === 0) {
    scrollFlushDeferrals = 0;
    return;
  }

  // Durante scroll activo: posponer el lote salvo forzado o límite de reintentos.
  if (!force && get(galleryScrolling)) {
    scrollFlushDeferrals++;
    if (scrollFlushDeferrals < MAX_SCROLL_FLUSH_DEFERRALS) {
      scheduleGalleryThumbFlush(token, THUMB_FLUSH_SCROLL_RETRY_MS);
      return;
    }
  }
  scrollFlushDeferrals = 0;

  const batch = pendingGalleryThumbHq;
  pendingGalleryThumbHq = new Map();

  const decoded = new Map<string, string>();
  await Promise.all(
    [...batch.entries()].map(async ([path, url]) => {
      if (await preloadDataUrl(url)) decoded.set(path, url);
      else pendingGalleryThumbHq.set(path, url);
    })
  );

  if (decoded.size === 0) {
    if (pendingGalleryThumbHq.size > 0) scheduleGalleryThumbFlush(token);
    return;
  }

  for (const [path, url] of decoded) {
    const it = getGalleryItems().find((x) => x.path === path);
    const lq =
      it?.thumbLqDataUrl ??
      (it?.thumbQuality === "lq" ? it?.thumbDataUrl : null) ??
      null;
    setGalleryThumbHq(path, url, lq);
  }

  if (pendingGalleryThumbHq.size > 0) scheduleGalleryThumbFlush(token);
}

function scheduleGalleryThumbFlush(token: number, delayMs = THUMB_FLUSH_MS) {
  galleryThumbFlushToken = token;
  if (galleryThumbFlushTimer !== null) {
    clearTimeout(galleryThumbFlushTimer);
  }
  galleryThumbFlushTimer = setTimeout(() => {
    galleryThumbFlushTimer = null;
    void flushPendingGalleryThumbs(galleryThumbFlushToken);
  }, delayMs);
}

function queueGalleryThumbHq(path: string, thumbDataUrl: string, token: number) {
  if (galleryThumbHydrationToken !== token) return;
  pendingGalleryThumbHq.set(path, thumbDataUrl);
  scheduleGalleryThumbFlush(token);
}

export async function hydrateGalleryThumbsHq(snapshot: GalleryItem[], scale: number, token: number) {
  const navGen = getGalleryNavigationGeneration();
  const base = snapshot.filter(
    (x) =>
      (x.kind === "image" || x.kind === "video") &&
      x.thumbQuality !== "hq" &&
      !hasGalleryThumbHq(x.path)
  );
  if (base.length === 0) {
    galleryThumbHydrating.set(false);
    return;
  }

  const orderedPaths = prioritizePathsByViewport(
    base.map((x) => x.path),
    ".tile[data-item-path]",
    "itemPath"
  );
  const targets = orderedPaths
    .map((p) => base.find((x) => x.path === p))
    .filter((x): x is GalleryItem => Boolean(x));

  galleryThumbHydrating.set(true);
  galleryThumbFlushToken = token;
  let idx = 0;
  try {
    const workers = Array.from({ length: 4 }, async () => {
      while (idx < targets.length) {
        const cur = idx++;
        const it = targets[cur];
        try {
          const out = await bridge.galleryThumbHq(it.path, scale);
          if (galleryThumbHydrationToken !== token || !isGalleryNavigationCurrent(navGen)) return;
          if (!out?.thumbDataUrl) continue;
          queueGalleryThumbHq(it.path, out.thumbDataUrl, token);
        } catch {
          /* ignore: se queda LQ */
        }
      }
    });
    await Promise.all(workers);
    if (galleryThumbFlushTimer !== null) {
      clearTimeout(galleryThumbFlushTimer);
      galleryThumbFlushTimer = null;
    }
    await flushPendingGalleryThumbs(token, true);
  } finally {
    galleryThumbHydrating.set(false);
    if (pendingGalleryThumbHq.size > 0 && galleryThumbHydrationToken === token) {
      scheduleGalleryThumbFlush(token);
    }
  }
}

/** Aplica HQ pendientes cuando termina el scroll (evita perder lotes diferidos). */
galleryScrolling.subscribe((scrolling) => {
  if (scrolling || pendingGalleryThumbHq.size === 0) return;
  void flushPendingGalleryThumbs(galleryThumbHydrationToken, true);
});

export function disposeGalleryThumbs() {
  cancelPendingGalleryThumbFlush();
}
