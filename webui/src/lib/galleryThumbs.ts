import { bridge } from "./api";
import type { GalleryItem } from "./api";
import { updateGalleryItems } from "./galleryRuntime";

let galleryThumbHydrationToken = 0;
let pendingGalleryThumbHq = new Map<string, string>();
let galleryThumbFlushRaf: number | null = null;
let galleryThumbFlushToken = 0;

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

export function cancelPendingGalleryThumbFlush() {
  pendingGalleryThumbHq.clear();
  if (galleryThumbFlushRaf !== null) {
    cancelAnimationFrame(galleryThumbFlushRaf);
    galleryThumbFlushRaf = null;
  }
}

export function bumpGalleryThumbHydrationToken(): number {
  galleryThumbHydrationToken++;
  cancelPendingGalleryThumbFlush();
  return galleryThumbHydrationToken;
}

export function getGalleryThumbHydrationToken(): number {
  return galleryThumbHydrationToken;
}

function flushPendingGalleryThumbs(token: number) {
  if (galleryThumbHydrationToken !== token) {
    pendingGalleryThumbHq.clear();
    return;
  }
  if (pendingGalleryThumbHq.size === 0) return;
  const batch = pendingGalleryThumbHq;
  pendingGalleryThumbHq = new Map();
  updateGalleryItems((items) =>
    items.map((x) => {
      if (x.kind !== "image" && x.kind !== "video") return x;
      const url = batch.get(x.path);
      if (!url) return x;
      return { ...x, thumbDataUrl: url, thumbQuality: "hq" };
    })
  );
}

function queueGalleryThumbHq(path: string, thumbDataUrl: string, token: number) {
  if (galleryThumbHydrationToken !== token) return;
  pendingGalleryThumbHq.set(path, thumbDataUrl);
  if (galleryThumbFlushRaf !== null) return;
  galleryThumbFlushToken = token;
  galleryThumbFlushRaf = requestAnimationFrame(() => {
    galleryThumbFlushRaf = null;
    flushPendingGalleryThumbs(galleryThumbFlushToken);
  });
}

export async function hydrateGalleryThumbsHq(snapshot: GalleryItem[], scale: number, token: number) {
  const base = snapshot.filter((x) => x.kind === "image" || x.kind === "video");
  const orderedPaths = prioritizePathsByViewport(
    base.map((x) => x.path),
    ".tile[data-item-path]",
    "itemPath"
  );
  const targets = orderedPaths
    .map((p) => base.find((x) => x.path === p))
    .filter((x): x is GalleryItem => Boolean(x));
  galleryThumbFlushToken = token;
  let idx = 0;
  const workers = Array.from({ length: 4 }, async () => {
    while (idx < targets.length) {
      const cur = idx++;
      const it = targets[cur];
      try {
        const out = await bridge.galleryThumbHq(it.path, scale);
        if (galleryThumbHydrationToken !== token) return;
        if (!out?.thumbDataUrl) continue;
        queueGalleryThumbHq(it.path, out.thumbDataUrl, token);
      } catch {
        /* ignore: se queda LQ */
      }
    }
  });
  await Promise.all(workers);
  if (galleryThumbFlushRaf !== null) {
    cancelAnimationFrame(galleryThumbFlushRaf);
    galleryThumbFlushRaf = null;
  }
  flushPendingGalleryThumbs(token);
}

export function disposeGalleryThumbs() {
  cancelPendingGalleryThumbFlush();
}
