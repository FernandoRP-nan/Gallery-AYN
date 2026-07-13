import { bridge, type GalleryItem } from "./api";
import {
  applyCachedDestPreviewThumbs,
  setDestPreviewThumb,
} from "./destPreviewThumbCache";
import { prioritizeThumbPaths, type ThumbPointerAnchor } from "./thumbPriority";

export type DestPreviewItem = {
  name: string;
  path: string;
  kind?: GalleryItem["kind"];
  thumbDataUrl?: string | null;
  thumbQuality?: "lq" | "hq";
};

const LQ_BATCH = 36;
const HQ_WORKERS = 4;
const IMMEDIATE_HQ_FLUSH = 10;

export type DestPreviewHydrateOpts = {
  cursorPath?: string | null;
  pointer?: ThumbPointerAnchor | null;
  /** Si se define, solo hidrata estos paths (p. ej. visibles tras scroll). */
  limitPaths?: string[];
};

/** Carga LQ por lotes y luego HQ (priorizando cursor/viewport), como la galería principal. */
export async function hydrateDestPreviewThumbs(
  snapshot: DestPreviewItem[],
  scale: number,
  token: number,
  scrollEl: HTMLElement | null,
  apply: (items: DestPreviewItem[]) => void,
  hydrateOpts?: DestPreviewHydrateOpts
): Promise<void> {
  let items = [...snapshot];
  const pathOrder = snapshot.map((x) => x.path);
  const inScope = (path: string) =>
    !hydrateOpts?.limitPaths?.length || hydrateOpts.limitPaths.includes(path);
  const priorityOpts = {
    selector: ".dest-preview-tile[data-preview-path]",
    attrName: "previewPath",
    scrollContainer: scrollEl,
    cursorPath: hydrateOpts?.cursorPath ?? null,
    pointer: hydrateOpts?.pointer ?? null,
    pathOrder,
  };

  const needLq = items.filter((x) => !x.thumbDataUrl && inScope(x.path)).map((x) => x.path);
  const lqOrder = prioritizeThumbPaths(needLq, priorityOpts);

  for (let i = 0; i < lqOrder.length; i += LQ_BATCH) {
    if (token !== activeDestPreviewThumbToken) return;
    const batch = lqOrder.slice(i, i + LQ_BATCH);
    try {
      const out = await bridge.destinationPreviewThumbs(batch, scale, "lq");
      for (const row of out?.items ?? []) {
        const p = String(row?.path ?? "").trim();
        const url = row?.thumbDataUrl;
        if (!p || !url) continue;
        items = items.map((x) =>
          x.path === p ? { ...x, thumbDataUrl: url, thumbQuality: "lq" as const } : x
        );
        setDestPreviewThumb(p, url, "lq");
      }
      apply(items);
    } catch {
      /* siguiente lote */
    }
  }

  const needHq = items.filter((x) => x.thumbQuality !== "hq" && inScope(x.path)).map((x) => x.path);
  const hqOrder = prioritizeThumbPaths(needHq, priorityOpts);
  let idx = 0;
  let immediateLeft = IMMEDIATE_HQ_FLUSH;
  const workers = Array.from({ length: HQ_WORKERS }, async () => {
    while (idx < hqOrder.length) {
      if (token !== activeDestPreviewThumbToken) return;
      const cur = idx++;
      const path = hqOrder[cur];
      try {
        const out = await bridge.destinationThumbHq(path, scale);
        if (token !== activeDestPreviewThumbToken) return;
        const url = out?.thumbDataUrl;
        if (!url) continue;
        items = items.map((x) =>
          x.path === path ? { ...x, thumbDataUrl: url, thumbQuality: "hq" as const } : x
        );
        setDestPreviewThumb(path, url, "hq");
        apply(items);
        if (immediateLeft > 0) immediateLeft--;
      } catch {
        /* se queda LQ */
      }
    }
  });
  await Promise.all(workers);
}

let activeDestPreviewThumbToken = 0;

export function bumpDestPreviewThumbToken(): number {
  activeDestPreviewThumbToken++;
  return activeDestPreviewThumbToken;
}

export function getDestPreviewThumbToken(): number {
  return activeDestPreviewThumbToken;
}
