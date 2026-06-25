import { bridge } from "./api";
import { normalizePathForApi } from "./pathUtils";

let warmToken = 0;
let warmTimer: ReturnType<typeof setTimeout> | null = null;

/** Precalienta solo el siguiente vídeo del carrusel fullscreen (1 job, cancelable). */
export function scheduleNextZoomVideoWarm(
  items: Array<{ path: string; kind?: string }>,
  activePath: string
) {
  if (warmTimer) clearTimeout(warmTimer);
  const token = ++warmToken;
  warmTimer = setTimeout(() => {
    warmTimer = null;
    if (token !== warmToken) return;
    const videos = items.filter((x) => x.kind === "video");
    if (videos.length < 2) return;
    const idx = videos.findIndex((x) => x.path === activePath);
    if (idx < 0) return;
    const next = videos[(idx + 1) % videos.length];
    if (!next || next.path === activePath) return;
    void bridge.galleryMediaUrl(normalizePathForApi(next.path), true).catch(() => undefined);
  }, 1200);
}

export function cancelZoomVideoWarm() {
  warmToken += 1;
  if (warmTimer) clearTimeout(warmTimer);
  warmTimer = null;
}
