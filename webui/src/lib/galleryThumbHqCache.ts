import { writable, type Readable } from "svelte/store";
import type { GalleryItem } from "./api";

function isGalleryMediaKind(kind: GalleryItem["kind"]): boolean {
  return kind === "image" || kind === "video";
}

export type GalleryThumbHqEntry = {
  hqUrl: string;
  lqUrl: string | null;
};

const hqByPath = new Map<string, GalleryThumbHqEntry>();
const pathStores = new Map<string, ReturnType<typeof writable<GalleryThumbHqEntry | null>>>();
/** Incrementa al vaciar caché para que ThumbImage re-suscriba stores vivos. */
export const galleryThumbHqCacheRevision = writable(0);
/** Tamaño en px para el que la caché HQ es válida; null = hay que re-hidratar. */
let hqValidForThumbPx: number | null = null;

function ensurePathStore(key: string) {
  let store = pathStores.get(key);
  if (!store) {
    store = writable<GalleryThumbHqEntry | null>(hqByPath.get(key) ?? null);
    pathStores.set(key, store);
  }
  return store;
}

export function getGalleryThumbHqValidPx(): number | null {
  return hqValidForThumbPx;
}

export function setGalleryThumbHqValidPx(px: number | null) {
  hqValidForThumbPx = px;
}

function lqFromItem(it: GalleryItem): string | null {
  if (it.thumbLqDataUrl) return it.thumbLqDataUrl;
  if (it.thumbQuality === "lq" && it.thumbDataUrl) return it.thumbDataUrl;
  return null;
}

function hqFromItem(it: GalleryItem): string | null {
  if (it.thumbQuality === "hq" && it.thumbDataUrl) return it.thumbDataUrl;
  return null;
}

function notifyPath(path: string, entry: GalleryThumbHqEntry | null) {
  ensurePathStore(path).set(entry);
}

/** Suscripción fina por ruta: store estable (no recrear derived en cada ciclo). */
export function galleryThumbHqFor(path: string): Readable<GalleryThumbHqEntry | null> {
  const key = String(path ?? "").trim();
  if (!key) return writable<GalleryThumbHqEntry | null>(null);
  return ensurePathStore(key);
}

export function getGalleryThumbHq(path: string): GalleryThumbHqEntry | null {
  const key = String(path ?? "").trim();
  return key ? hqByPath.get(key) ?? null : null;
}

export function hasGalleryThumbHq(path: string): boolean {
  return getGalleryThumbHq(path) !== null;
}

export function isGalleryThumbHqValidForPx(px: number): boolean {
  return hqValidForThumbPx === px;
}

export function setGalleryThumbHq(path: string, hqUrl: string, lqUrl?: string | null) {
  const key = String(path ?? "").trim();
  const hq = String(hqUrl ?? "").trim();
  if (!key || !hq) return;
  const prev = hqByPath.get(key);
  if (prev?.hqUrl === hq && prev.lqUrl === (lqUrl ?? null)) return;
  const entry: GalleryThumbHqEntry = { hqUrl: hq, lqUrl: lqUrl ?? prev?.lqUrl ?? null };
  hqByPath.set(key, entry);
  notifyPath(key, entry);
}

export function preserveItemThumbInCache(it: GalleryItem) {
  if (!isGalleryMediaKind(it.kind)) return;
  const hq = hqFromItem(it) ?? getGalleryThumbHq(it.path)?.hqUrl ?? null;
  if (!hq) return;
  setGalleryThumbHq(it.path, hq, lqFromItem(it));
}

export function seedGalleryThumbHqFromItems(items: GalleryItem[]) {
  for (const it of items) {
    if (!isGalleryMediaKind(it.kind)) continue;
    const hq = hqFromItem(it);
    if (!hq) continue;
    setGalleryThumbHq(it.path, hq, lqFromItem(it));
  }
}

export function removeGalleryThumbHq(paths: Iterable<string>) {
  for (const raw of paths) {
    const key = String(raw ?? "").trim();
    if (!key) continue;
    hqByPath.delete(key);
    const store = pathStores.get(key);
    if (store) {
      store.set(null);
      pathStores.delete(key);
    }
  }
}

export function clearGalleryThumbHqCache() {
  hqByPath.clear();
  hqValidForThumbPx = null;
  for (const store of pathStores.values()) store.set(null);
  galleryThumbHqCacheRevision.update((n) => n + 1);
}

/** Ítem con thumb LQ en el store reactivo; HQ vive en la caché externa. */
export function stripHqFromGalleryItem(it: GalleryItem): GalleryItem {
  if (!isGalleryMediaKind(it.kind)) return it;
  if (hasGalleryThumbHq(it.path)) {
    const cached = getGalleryThumbHq(it.path);
    const lq = lqFromItem(it) ?? cached?.lqUrl ?? cached?.hqUrl ?? null;
    return {
      ...it,
      thumbDataUrl: lq,
      thumbLqDataUrl: lq,
      thumbQuality: lq ? ("lq" as const) : undefined,
    };
  }
  const hq = hqFromItem(it);
  if (hq) {
    preserveItemThumbInCache(it);
    const cached = getGalleryThumbHq(it.path);
    const lq = lqFromItem(it) ?? cached?.lqUrl ?? null;
    // Vídeos LQ del listado venían marcados como hq; conservar la URL visible.
    const visibleLq = lq ?? (it.kind === "video" ? hq : null);
    return {
      ...it,
      thumbDataUrl: visibleLq,
      thumbLqDataUrl: visibleLq,
      thumbQuality: visibleLq ? ("lq" as const) : undefined,
    };
  }
  return it;
}

export function stripHqFromGalleryItems(items: GalleryItem[]): GalleryItem[] {
  return items.map(stripHqFromGalleryItem);
}
