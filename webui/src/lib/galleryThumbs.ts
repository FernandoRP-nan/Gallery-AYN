import { writable, get } from "svelte/store";
import type { GalleryItem } from "./api";
import {
  clearGalleryThumbHqCache,
  setGalleryThumbHqValidPx,
  getGalleryThumbHqValidPx,
} from "./galleryThumbHqCache";
import { getGalleryItems, updateGalleryItems } from "./galleryRuntime";
import { stripHqFromGalleryItems } from "./galleryThumbHqCache";
import { galleryScrolling } from "./galleryScrollState";
import { galleryThumbPx } from "./thumbScale";
import { listGalleryItemsNeedingHq } from "./galleryThumbNeeding";
import { isGalleryHqJumpGraceActive } from "./gallerySession";
import {
  cancelPendingGalleryThumbFlush as cancelPendingFlush,
  flushPendingThumbsOnScrollEnd,
  runGalleryThumbHydration,
  type GalleryThumbHydrateOpts,
} from "./galleryThumbHydrateCore";

export type { GalleryThumbHydrateOpts };

export const galleryThumbHydrating = writable(false);

let galleryLqLoading = false;
let galleryExpandPending = false;

/** Pausa hidratación HQ mientras hay cargas LQ en curso. */
export function setGalleryLqLoading(active: boolean) {
  galleryLqLoading = Boolean(active);
}

/** Pausa HQ mientras la fase expand del salto está en curso. */
export function setGalleryExpandPending(active: boolean) {
  galleryExpandPending = Boolean(active);
}

function isGalleryLqLoading(): boolean {
  return galleryLqLoading;
}

function isGalleryExpandPending(): boolean {
  return galleryExpandPending;
}

async function waitForLqIdle(token: number, maxMs = 120000): Promise<void> {
  const start = Date.now();
  while (isGalleryLqLoading() && isHydrationTokenActive(token)) {
    if (Date.now() - start > maxMs) return;
    await new Promise<void>((r) => setTimeout(r, 50));
  }
}

async function waitForExpandIdle(token: number, maxMs = 120000): Promise<void> {
  const start = Date.now();
  while (isGalleryExpandPending() && isHydrationTokenActive(token)) {
    if (Date.now() - start > maxMs) return;
    await new Promise<void>((r) => setTimeout(r, 50));
  }
}

/** Espera scroll estable antes de HQ (evita trabajo sobre layout transitorio). */
async function waitForScrollStable(
  token: number,
  stableMs = 200,
  maxMs = 8000,
): Promise<void> {
  const start = Date.now();
  let stableSince = get(galleryScrolling) ? Date.now() : 0;
  while (isHydrationTokenActive(token)) {
    if (get(galleryScrolling)) {
      stableSince = 0;
    } else if (stableSince === 0) {
      stableSince = Date.now();
    } else if (Date.now() - stableSince >= stableMs) {
      return;
    }
    if (Date.now() - start > maxMs) return;
    await new Promise<void>((r) => setTimeout(r, 40));
  }
}

let galleryThumbHydrationToken = 0;
let hydrationQueue: Promise<void> = Promise.resolve();
let continueTimer: ReturnType<typeof setTimeout> | null = null;
let lastHydrationScale = 1;
let continueAttempts = 0;
const MAX_CONTINUE_ATTEMPTS = 24;

export function cancelPendingGalleryThumbFlush() {
  cancelPendingFlush();
}

export function bumpGalleryThumbHydrationToken(clearCache = false): number {
  galleryThumbHydrationToken++;
  continueAttempts = 0;
  if (continueTimer !== null) {
    clearTimeout(continueTimer);
    continueTimer = null;
  }
  cancelPendingFlush();
  if (clearCache) {
    updateGalleryItems((items) => stripHqFromGalleryItems(items));
    clearGalleryThumbHqCache();
  }
  return galleryThumbHydrationToken;
}

export function invalidateGalleryThumbHqForScale(scale: number): boolean {
  const px = galleryThumbPx(scale);
  if (getGalleryThumbHqValidPx() === px) return false;
  setGalleryThumbHqValidPx(null);
  clearGalleryThumbHqCache();
  updateGalleryItems((items) => stripHqFromGalleryItems(items));
  return true;
}

export function getGalleryThumbHydrationToken(): number {
  return galleryThumbHydrationToken;
}

function isHydrationTokenActive(token: number): boolean {
  return galleryThumbHydrationToken === token;
}

function scheduleContinueHydration(token: number, opts?: GalleryThumbHydrateOpts) {
  if (continueAttempts >= MAX_CONTINUE_ATTEMPTS) return;
  continueAttempts++;
  if (continueTimer !== null) clearTimeout(continueTimer);
  continueTimer = setTimeout(() => {
    continueTimer = null;
    if (!isHydrationTokenActive(token)) return;
    void requestGalleryThumbHqHydration(lastHydrationScale, token, opts);
  }, 350);
}

async function hydrateOnce(
  scale: number,
  token: number,
  opts?: GalleryThumbHydrateOpts
): Promise<void> {
  if (!isHydrationTokenActive(token)) return;

  await waitForLqIdle(token);
  await waitForExpandIdle(token);
  if (isGalleryHqJumpGraceActive()) {
    if (get(galleryScrolling)) {
      await new Promise<void>((r) => setTimeout(r, 60));
    }
  } else {
    await waitForScrollStable(token);
  }

  lastHydrationScale = scale;
  const allNeeding = listGalleryItemsNeedingHq(getGalleryItems());
  if (allNeeding.length === 0) {
    setGalleryThumbHqValidPx(galleryThumbPx(scale));
    galleryThumbHydrating.set(false);
    return;
  }

  galleryThumbHydrating.set(true);
  try {
    let remaining = await runGalleryThumbHydration(
      allNeeding,
      scale,
      token,
      () => isHydrationTokenActive(token),
      opts
    );

    // Reintento rápido si ninguna HQ aplicó (p. ej. backend aún calentando).
    if (
      remaining >= allNeeding.length &&
      allNeeding.length > 0 &&
      isHydrationTokenActive(token)
    ) {
      await new Promise<void>((r) => setTimeout(r, 180));
      await waitForLqIdle(token);
      await waitForExpandIdle(token);
      if (isGalleryHqJumpGraceActive()) {
        if (get(galleryScrolling)) {
          await new Promise<void>((r) => setTimeout(r, 60));
        }
      } else {
        await waitForScrollStable(token);
      }
      if (isHydrationTokenActive(token)) {
        remaining = await runGalleryThumbHydration(
          listGalleryItemsNeedingHq(getGalleryItems()),
          scale,
          token,
          () => isHydrationTokenActive(token),
          opts
        );
      }
    }

    if (!isHydrationTokenActive(token)) return;

    const px = galleryThumbPx(scale);
    if (remaining === 0) {
      setGalleryThumbHqValidPx(px);
    } else {
      scheduleContinueHydration(token, opts);
    }
  } finally {
    if (isHydrationTokenActive(token)) {
      galleryThumbHydrating.set(false);
    }
  }
}

/** Encola hidratación HQ; siempre procesa toda la galería pendiente. */
export function requestGalleryThumbHqHydration(
  scale: number,
  token: number,
  opts?: GalleryThumbHydrateOpts
): Promise<void> {
  hydrationQueue = hydrationQueue
    .catch(() => undefined)
    .then(() => hydrateOnce(scale, token, opts));
  return hydrationQueue;
}

/** Compat: ignora snapshot parcial y usa toda la galería. */
export async function hydrateGalleryThumbsHq(
  _snapshot: GalleryItem[],
  scale: number,
  token: number,
  opts?: GalleryThumbHydrateOpts
): Promise<void> {
  return requestGalleryThumbHqHydration(scale, token, opts);
}

galleryScrolling.subscribe((scrolling) => {
  if (scrolling) return;
  flushPendingThumbsOnScrollEnd(galleryThumbHydrationToken);
});

export function disposeGalleryThumbs() {
  cancelPendingFlush();
  if (continueTimer !== null) {
    clearTimeout(continueTimer);
    continueTimer = null;
  }
}

export async function refreshGalleryThumbsForScale(
  scale: number,
  hydrateOpts?: GalleryThumbHydrateOpts
) {
  const token = bumpGalleryThumbHydrationToken(true);
  await requestGalleryThumbHqHydration(scale, token, hydrateOpts);
}
