import { bridge } from "./api";
import { normalizePathForApi } from "./pathUtils";
import type { MediaPlaybackInfo } from "./mediaUrl";

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Espera a que la caché de transcodificación esté lista (o ffmpeg falte). */
export async function waitForTranscodeCache(
  path: string,
  isCancelled: () => boolean,
  maxMs = 3_600_000
): Promise<boolean> {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    if (isCancelled()) return false;
    try {
      const out = await bridge.galleryMediaUrl(normalizePathForApi(path), false);
      if (!out?.ffmpegAvailable && out?.needsTranscode) return false;
      if (out?.transcodeCached) return true;
      if (!out?.needsTranscode) return true;
    } catch {
      return false;
    }
    await sleep(900);
  }
  return false;
}

export function canTranscodeVideo(info: Pick<MediaPlaybackInfo, "needsTranscode" | "ffmpegAvailable">): boolean {
  return !info.needsTranscode || Boolean(info.ffmpegAvailable);
}

/** Intenta reproducir (ignora fallos por política del navegador). */
export function tryAutoplayVideo(el: HTMLVideoElement | null | undefined): void {
  if (!el) return;
  try {
    const pending = el.play();
    if (pending && typeof pending.catch === "function") {
      void pending.catch(() => undefined);
    }
  } catch {
    /* ignore */
  }
}
