import { derived, writable, type Readable } from "svelte/store";
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
  const store = pathStores.get(path);
  if (store) store.set(entry);
}

/** Suscripción fina por ruta: solo la tile afectada re-renderiza al llegar HQ. */
export function galleryThumbHqFor(path: string): Readable<GalleryThumbHqEntry | null> {
  const key = String(path ?? "").trim();
  if (!key) return writable<GalleryThumbHqEntry | null>(null);
  let store = pathStores.get(key);
  if (!store) {
    store = writable<GalleryThumbHqEntry | null>(hqByPath.get(key) ?? null);
    pathStores.set(key, store);
  }
  return derived(store, (x) => x);
}

export function getGalleryThumbHq(path: string): GalleryThumbHqEntry | null {
  const key = String(path ?? "").trim();
  return key ? hqByPath.get(key) ?? null : null;
}

export function hasGalleryThumbHq(path: string): boolean {
  return getGalleryThumbHq(path) !== null;
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
    pathStores.delete(key);
  }
}

export function clearGalleryThumbHqCache() {
  hqByPath.clear();
  for (const store of pathStores.values()) store.set(null);
  pathStores.clear();
}

/** Ítem con thumb LQ en el store reactivo; HQ vive en la caché externa. */
export function stripHqFromGalleryItem(it: GalleryItem): GalleryItem {
  if (!isGalleryMediaKind(it.kind)) return it;
  if (hasGalleryThumbHq(it.path)) {
    const cached = getGalleryThumbHq(it.path);
    const lq = lqFromItem(it) ?? cached?.lqUrl ?? null;
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
    const lq = lqFromItem(it);
    return {
      ...it,
      thumbDataUrl: lq,
      thumbLqDataUrl: lq,
      thumbQuality: lq ? ("lq" as const) : undefined,
    };
  }
  return it;
}

export function stripHqFromGalleryItems(items: GalleryItem[]): GalleryItem[] {
  return items.map(stripHqFromGalleryItem);
}
