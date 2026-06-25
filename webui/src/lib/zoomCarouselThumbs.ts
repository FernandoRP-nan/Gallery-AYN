import { bridge } from "./api";

export type ZoomNavThumbItem = {
  path: string;
  name: string;
  thumbDataUrl?: string | null;
  thumbQuality?: "lq" | "hq";
  kind?: string;
};

let hydrateToken = 0;

export function cancelZoomCarouselHydration() {
  hydrateToken++;
}

/** Precarga HQ para el carrusel fullscreen (prioriza activo y vecinos). */
export async function hydrateZoomCarouselThumbs(
  items: ZoomNavThumbItem[],
  scale: number,
  activePath: string,
  onUpdate: (path: string, thumbDataUrl: string) => void
) {
  const token = ++hydrateToken;
  const media = items.filter((x) => x.kind === "image" || x.kind === "video");
  if (media.length === 0) return;

  const paths = media.map((x) => x.path);
  const activeIdx = Math.max(0, paths.indexOf(activePath));
  const prioritized: string[] = [];
  const seen = new Set<string>();
  const push = (p: string) => {
    if (!seen.has(p)) {
      seen.add(p);
      prioritized.push(p);
    }
  };
  push(paths[activeIdx] ?? paths[0]);
  for (let d = 1; d < paths.length; d++) {
    if (activeIdx - d >= 0) push(paths[activeIdx - d]);
    if (activeIdx + d < paths.length) push(paths[activeIdx + d]);
  }

  const targets = prioritized
    .map((p) => media.find((x) => x.path === p))
    .filter((x): x is ZoomNavThumbItem => Boolean(x))
    .filter((x) => x.thumbQuality !== "hq" || !x.thumbDataUrl);

  let idx = 0;
  const workers = Array.from({ length: 6 }, async () => {
    while (idx < targets.length) {
      if (token !== hydrateToken) return;
      const cur = idx++;
      const it = targets[cur];
      try {
        const out = await bridge.galleryThumbHq(it.path, scale);
        if (token !== hydrateToken || !out?.thumbDataUrl) continue;
        onUpdate(it.path, out.thumbDataUrl);
      } catch {
        /* conservar LQ */
      }
    }
  });
  await Promise.all(workers);
}
