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

export type VideoVolumePrefs = {
  volume: number;
  muted: boolean;
};

export const DEFAULT_VIDEO_VOLUME_PREFS: VideoVolumePrefs = {
  volume: 1,
  muted: false,
};

/** Normaliza volumen HTML5 (0–1). */
export function normalizeVideoVolume(volume: unknown): number {
  const n = Number(volume);
  if (!Number.isFinite(n)) return DEFAULT_VIDEO_VOLUME_PREFS.volume;
  return Math.min(1, Math.max(0, n));
}

export function normalizeVideoVolumePrefs(raw?: Partial<VideoVolumePrefs> | null): VideoVolumePrefs {
  return {
    volume: normalizeVideoVolume(raw?.volume ?? DEFAULT_VIDEO_VOLUME_PREFS.volume),
    muted: Boolean(raw?.muted),
  };
}

export function applyVideoVolumePrefs(
  el: HTMLVideoElement | null | undefined,
  prefs: VideoVolumePrefs
): void {
  if (!el) return;
  el.volume = normalizeVideoVolume(prefs.volume);
  el.muted = Boolean(prefs.muted);
}

export function readVideoVolumeFromElement(el: HTMLVideoElement): VideoVolumePrefs {
  return {
    volume: normalizeVideoVolume(el.volume),
    muted: Boolean(el.muted),
  };
}

/** Intenta reproducir (ignora fallos por política del navegador). */
export function tryAutoplayVideo(
  el: HTMLVideoElement | null | undefined,
  prefs?: VideoVolumePrefs
): void {
  if (!el) return;
  if (prefs) applyVideoVolumePrefs(el, prefs);
  try {
    const pending = el.play();
    if (pending && typeof pending.catch === "function") {
      void pending.catch(() => undefined);
    }
  } catch {
    /* ignore */
  }
}
