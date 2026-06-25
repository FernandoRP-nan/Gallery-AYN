import { bridge } from "./api";
import {
  applyCachedDestPreviewThumbs,
  setDestPreviewThumb,
} from "./destPreviewThumbCache";

export type DestPreviewItem = {
  name: string;
  path: string;
  thumbDataUrl?: string | null;
  thumbQuality?: "lq" | "hq";
};

const LQ_BATCH = 36;
const HQ_WORKERS = 4;

function prioritizePathsByViewport(
  paths: string[],
  scrollEl: HTMLElement | null
): string[] {
  if (!scrollEl) return paths;
  const nodes = Array.from(scrollEl.querySelectorAll<HTMLElement>(".dest-preview-tile[data-preview-path]"));
  if (nodes.length === 0) return paths;
  const nodeByPath = new Map<string, HTMLElement>();
  for (const n of nodes) {
    const p = n.dataset.previewPath;
    if (p) nodeByPath.set(p, n);
  }
  const bounds = scrollEl.getBoundingClientRect();
  const visible: string[] = [];
  const rest: string[] = [];
  for (const p of paths) {
    const el = nodeByPath.get(p);
    if (!el) {
      rest.push(p);
      continue;
    }
    const r = el.getBoundingClientRect();
    const isVisible = r.bottom > bounds.top && r.top < bounds.bottom && r.right > bounds.left && r.left < bounds.right;
    (isVisible ? visible : rest).push(p);
  }
  return [...visible, ...rest];
}

/** Carga LQ por lotes y luego HQ (priorizando viewport), como la galería principal. */
export async function hydrateDestPreviewThumbs(
  snapshot: DestPreviewItem[],
  scale: number,
  token: number,
  scrollEl: HTMLElement | null,
  apply: (items: DestPreviewItem[]) => void
): Promise<void> {
  let items = [...snapshot];

  const needLq = items.filter((x) => !x.thumbDataUrl).map((x) => x.path);
  const lqOrder = prioritizePathsByViewport(needLq, scrollEl);

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

  const needHq = items.filter((x) => x.thumbQuality !== "hq").map((x) => x.path);
  const hqOrder = prioritizePathsByViewport(needHq, scrollEl);
  let idx = 0;
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
