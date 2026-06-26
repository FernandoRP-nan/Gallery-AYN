import { get } from "svelte/store";
import { bridge } from "./api";
import type { GalleryItem } from "./api";
import { setGalleryThumbHq } from "./galleryThumbHqCache";
import {
  getGalleryNavigationGeneration,
  isGalleryHqJumpGraceActive,
  isGalleryNavigationCurrent,
} from "./gallerySession";
import { getGalleryItems } from "./galleryRuntime";
import { galleryScrolling } from "./galleryScrollState";
import { prioritizeThumbPaths, type ThumbPointerAnchor } from "./thumbPriority";
import { getGalleryPerfConfig } from "./galleryPerfConfig";
import { galleryDbg } from "./galleryDebugLog";
import { listGalleryItemsNeedingHq } from "./galleryThumbNeeding";

/** Máximo de miniaturas HQ por pasada (el resto continúa en cola). */
function hqBatchCapPerPass(): number {
  const batch = getGalleryPerfConfig().unlimitedBatchSize;
  return Math.max(48, Math.min(128, batch * 2));
}

export type GalleryThumbHydrateOpts = {
  cursorPath?: string | null;
  scrollContainer?: HTMLElement | null;
  pathOrder?: string[];
  pointer?: ThumbPointerAnchor | null;
};

const THUMB_HQ_FETCH_MS = 22000;

function fetchGalleryThumbHq(path: string, scale: number): Promise<{ thumbDataUrl?: string } | null> {
  return Promise.race([
    bridge.galleryThumbHq(path, scale),
    new Promise<null>((resolve) => setTimeout(() => resolve(null), THUMB_HQ_FETCH_MS)),
  ]);
}
const THUMB_FLUSH_MS = 80;
const THUMB_FLUSH_SCROLL_RETRY_MS = 100;
const MAX_SCROLL_FLUSH_DEFERRALS = 64;
const PRELOAD_FAIL_APPLY = 2;

let pendingGalleryThumbHq = new Map<string, string>();
let galleryThumbFlushTimer: ReturnType<typeof setTimeout> | null = null;
let galleryThumbFlushToken = 0;
let scrollFlushDeferrals = 0;
const preloadFailCount = new Map<string, number>();

function preloadDataUrl(url: string): Promise<boolean> {
  return Promise.race([
    new Promise<boolean>((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.decoding = "async";
      img.src = url;
    }),
    new Promise<boolean>((resolve) => setTimeout(() => resolve(false), 18000)),
  ]);
}

export function cancelPendingGalleryThumbFlush() {
  pendingGalleryThumbHq.clear();
  preloadFailCount.clear();
  scrollFlushDeferrals = 0;
  if (galleryThumbFlushTimer !== null) {
    clearTimeout(galleryThumbFlushTimer);
    galleryThumbFlushTimer = null;
  }
}

async function flushPendingGalleryThumbs(
  hydrationToken: number,
  force = false
): Promise<void> {
  if (galleryThumbFlushToken !== hydrationToken) {
    pendingGalleryThumbHq.clear();
    scrollFlushDeferrals = 0;
    return;
  }
  if (pendingGalleryThumbHq.size === 0) {
    scrollFlushDeferrals = 0;
    return;
  }

  if (!force && get(galleryScrolling) && !isGalleryHqJumpGraceActive()) {
    scrollFlushDeferrals++;
    if (scrollFlushDeferrals < MAX_SCROLL_FLUSH_DEFERRALS) {
      scheduleGalleryThumbFlush(hydrationToken, THUMB_FLUSH_SCROLL_RETRY_MS);
      return;
    }
  }
  scrollFlushDeferrals = 0;

  const batch = pendingGalleryThumbHq;
  pendingGalleryThumbHq = new Map();

  const decoded = new Map<string, string>();
  await Promise.all(
    [...batch.entries()].map(async ([path, url]) => {
      if (await preloadDataUrl(url)) {
        decoded.set(path, url);
        preloadFailCount.delete(path);
        return;
      }
      const fails = (preloadFailCount.get(path) ?? 0) + 1;
      preloadFailCount.set(path, fails);
      if (fails >= PRELOAD_FAIL_APPLY) {
        decoded.set(path, url);
        preloadFailCount.delete(path);
      } else {
        pendingGalleryThumbHq.set(path, url);
      }
    })
  );

  for (const [path, url] of decoded) {
    applyGalleryThumbHq(path, url);
  }

  if (pendingGalleryThumbHq.size > 0) {
    scheduleGalleryThumbFlush(hydrationToken);
  }
}

export async function drainPendingGalleryThumbs(hydrationToken: number): Promise<void> {
  for (let i = 0; i < 10 && pendingGalleryThumbHq.size > 0; i++) {
    if (galleryThumbFlushTimer !== null) {
      clearTimeout(galleryThumbFlushTimer);
      galleryThumbFlushTimer = null;
    }
    await flushPendingGalleryThumbs(hydrationToken, true);
    if (pendingGalleryThumbHq.size > 0) {
      await new Promise<void>((r) => setTimeout(r, 40));
    }
  }
}

function scheduleGalleryThumbFlush(hydrationToken: number, delayMs = THUMB_FLUSH_MS) {
  galleryThumbFlushToken = hydrationToken;
  if (galleryThumbFlushTimer !== null) clearTimeout(galleryThumbFlushTimer);
  galleryThumbFlushTimer = setTimeout(() => {
    galleryThumbFlushTimer = null;
    void flushPendingGalleryThumbs(galleryThumbFlushToken);
  }, delayMs);
}

function queueGalleryThumbHq(path: string, thumbDataUrl: string, hydrationToken: number) {
  pendingGalleryThumbHq.set(path, thumbDataUrl);
  scheduleGalleryThumbFlush(hydrationToken);
}

function applyGalleryThumbHq(path: string, thumbDataUrl: string, lqHint?: string | null) {
  const storePath = String(path ?? "").trim();
  const it = getGalleryItems().find((x) => x.path === storePath || x.path === path);
  const lq =
    lqHint ??
    it?.thumbLqDataUrl ??
    (it?.thumbQuality === "lq" ? it?.thumbDataUrl : null) ??
    null;
  setGalleryThumbHq(storePath, thumbDataUrl, lq);
}

function pathFromTileNode(n: HTMLElement): string | null {
  return n.getAttribute("data-item-path")?.trim() || null;
}

export function splitTargetsByVisibility(
  targets: GalleryItem[],
  opts: GalleryThumbHydrateOpts
): { visible: GalleryItem[]; rest: GalleryItem[] } {
  const scroll = opts.scrollContainer;
  if (!scroll) return { visible: [], rest: targets };

  const bounds = scroll.getBoundingClientRect();
  const visiblePaths = new Set<string>();
  for (const n of scroll.querySelectorAll<HTMLElement>("[data-item-path]")) {
    const p = pathFromTileNode(n);
    if (!p) continue;
    const r = n.getBoundingClientRect();
    if (r.bottom > bounds.top - 32 && r.top < bounds.bottom + 32) {
      visiblePaths.add(p);
    }
  }

  const visible: GalleryItem[] = [];
  const rest: GalleryItem[] = [];
  for (const it of targets) {
    if (visiblePaths.has(it.path)) visible.push(it);
    else rest.push(it);
  }
  return { visible, rest };
}

function orderTargets(base: GalleryItem[], opts: GalleryThumbHydrateOpts): GalleryItem[] {
  const pathOrder = opts.pathOrder ?? base.map((x) => x.path);
  const orderedPaths = prioritizeThumbPaths(
    base.map((x) => x.path),
    {
      selector: "[data-item-path]",
      attrName: "itemPath",
      scrollContainer: opts.scrollContainer ?? null,
      cursorPath: opts.cursorPath ?? null,
      pointer: opts.pointer ?? null,
      pathOrder,
    }
  );
  return orderedPaths
    .map((p) => base.find((x) => x.path === p))
    .filter((x): x is GalleryItem => Boolean(x));
}

async function fetchHqSequential(
  targets: GalleryItem[],
  scale: number,
  hydrationToken: number,
  navGen: number,
  isActive: () => boolean
): Promise<void> {
  for (const it of targets) {
    if (!isActive() || !isGalleryNavigationCurrent(navGen)) return;
    try {
      const out = await fetchGalleryThumbHq(it.path, scale);
      if (!isActive() || !isGalleryNavigationCurrent(navGen)) return;
      if (!out?.thumbDataUrl) continue;
      const storePath = String(out.path ?? it.path).trim();
      pendingGalleryThumbHq.set(storePath, out.thumbDataUrl);
      await flushPendingGalleryThumbs(hydrationToken, true);
      if (pendingGalleryThumbHq.has(storePath)) {
        applyGalleryThumbHq(storePath, out.thumbDataUrl);
        pendingGalleryThumbHq.delete(storePath);
      }
    } catch {
      /* LQ hasta reintento */
    }
  }
}

async function fetchHqBatchParallel(
  targets: GalleryItem[],
  scale: number,
  hydrationToken: number,
  navGen: number,
  isActive: () => boolean,
  workers: number
): Promise<void> {
  if (targets.length === 0) return;
  let idx = 0;

  await Promise.all(
    Array.from({ length: workers }, async () => {
      while (idx < targets.length) {
        if (!isActive() || !isGalleryNavigationCurrent(navGen)) return;
        const cur = idx++;
        const it = targets[cur];
        try {
          const out = await fetchGalleryThumbHq(it.path, scale);
          if (!isActive() || !isGalleryNavigationCurrent(navGen)) return;
          if (!out?.thumbDataUrl) continue;
          const storePath = String(out.path ?? it.path).trim();
          queueGalleryThumbHq(storePath, out.thumbDataUrl, hydrationToken);
        } catch {
          /* LQ hasta reintento */
        }
      }
    })
  );
}

export async function runGalleryThumbHydration(
  snapshot: GalleryItem[],
  scale: number,
  hydrationToken: number,
  isActive: () => boolean,
  opts?: GalleryThumbHydrateOpts
): Promise<number> {
  const hydrateOpts = opts ?? {};
  const allNeeding = listGalleryItemsNeedingHq(snapshot);
  if (allNeeding.length === 0) return 0;

  const navGen = getGalleryNavigationGeneration();
  const ordered = orderTargets(allNeeding, hydrateOpts);
  let { visible, rest } = splitTargetsByVisibility(ordered, hydrateOpts);
  const perf = getGalleryPerfConfig();
  const maxVisibleSeq = perf.thumbHqVisibleSequential;
  const hqWorkers = perf.thumbHqWorkers;

  // Sin tiles en DOM (post-salto): priorizar el frente de la cola como pseudo-visibles.
  if (visible.length === 0 && rest.length > 0) {
    visible = ordered.slice(0, maxVisibleSeq);
    rest = ordered.slice(maxVisibleSeq);
  }

  galleryDbg("load_hq", "inicio hidratación HQ", {
    pending: allNeeding.length,
    visible: visible.length,
    rest: rest.length,
    workers: hqWorkers,
    visibleSequential: maxVisibleSeq,
    phase: "viewport",
  });

  galleryThumbFlushToken = hydrationToken;

  // Fase 1: solo viewport (secuencial + paralelo visible).
  await fetchHqSequential(visible.slice(0, maxVisibleSeq), scale, hydrationToken, navGen, isActive);
  const visibleOverflow = visible.slice(maxVisibleSeq);
  if (visibleOverflow.length > 0 && isActive() && isGalleryNavigationCurrent(navGen)) {
    await fetchHqBatchParallel(
      visibleOverflow,
      scale,
      hydrationToken,
      navGen,
      isActive,
      Math.min(hqWorkers, 8),
    );
  }

  if (galleryThumbFlushTimer !== null) {
    clearTimeout(galleryThumbFlushTimer);
    galleryThumbFlushTimer = null;
  }
  await drainPendingGalleryThumbs(hydrationToken);

  if (!isActive() || !isGalleryNavigationCurrent(navGen)) {
    return listGalleryItemsNeedingHq(getGalleryItems()).length;
  }

  // Fase 2: fuera de pantalla en background (diferida si hay scroll activo).
  if (rest.length === 0) {
    const remaining = listGalleryItemsNeedingHq(getGalleryItems()).length;
    galleryDbg("load_hq", "fin hidratación HQ", { remaining, phase: "viewport" });
    return remaining;
  }

  if (get(galleryScrolling) && !isGalleryHqJumpGraceActive()) {
    const remaining = listGalleryItemsNeedingHq(getGalleryItems()).length;
    galleryDbg("load_hq", "HQ fuera de pantalla diferida (scroll)", { rest: rest.length, remaining });
    return remaining;
  }

  const graceBoost = isGalleryHqJumpGraceActive() && allNeeding.length <= 512;
  const bgCap = graceBoost ? Math.min(allNeeding.length, 512) : hqBatchCapPerPass();
  const bgBatch = rest.slice(0, bgCap);
  galleryDbg("load_hq", "tanda HQ paralela (background)", {
    count: bgBatch.length,
    workers: hqWorkers,
    graceBoost,
  });
  await fetchHqBatchParallel(bgBatch, scale, hydrationToken, navGen, isActive, hqWorkers);

  if (galleryThumbFlushTimer !== null) {
    clearTimeout(galleryThumbFlushTimer);
    galleryThumbFlushTimer = null;
  }
  await drainPendingGalleryThumbs(hydrationToken);

  const remaining = listGalleryItemsNeedingHq(getGalleryItems()).length;
  galleryDbg("load_hq", "fin hidratación HQ", { remaining, phase: "background" });
  return remaining;
}

export function flushPendingThumbsOnScrollEnd(hydrationToken: number) {
  if (pendingGalleryThumbHq.size === 0) return;
  void drainPendingGalleryThumbs(hydrationToken);
}
