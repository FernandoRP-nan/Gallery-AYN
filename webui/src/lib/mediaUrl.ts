import { bridge } from "./api";
import { t } from "./i18n";
import { normalizePathForApi } from "./pathUtils";

/** Convierte /om-media/… en URL absoluta del origen actual. */
export function absolutizeMediaUrl(relOrAbs: string | null | undefined): string {
  const raw = String(relOrAbs ?? "").trim();
  if (!raw) return "";
  if (raw.startsWith("data:")) return raw;
  if (raw.startsWith("http://") || raw.startsWith("https://") || raw.startsWith("file:")) return raw;
  const rel = raw.startsWith("/") ? raw : `/${raw}`;
  if (typeof window !== "undefined") {
    const origin = window.location?.origin;
    if (origin && origin !== "null" && origin.startsWith("http")) {
      return `${origin}${rel}`;
    }
  }
  return rel;
}

export function isDataPlaybackUrl(url: string | null | undefined): boolean {
  return String(url ?? "").startsWith("data:");
}

export type VideoPlaybackMode = "auto" | "direct" | "remux" | "turbo" | "fast" | "quality";

export type MediaPlaybackInfo = {
  fileUrl: string;
  transcodeUrl: string;
  needsTranscode: boolean;
  playbackMode?: VideoPlaybackMode;
  playbackStrategy?: "direct" | "remux" | "encode";
  playbackViaBlob?: boolean;
  ffmpegAvailable?: boolean;
  ffprobeAvailable?: boolean;
  transcodeCached?: boolean;
  playbackFormat?: string;
};

function pywebviewActive(): boolean {
  return typeof window !== "undefined" && Boolean(window.pywebview?.api);
}

/** URL de reproducción vía data URL cuando Qt no sirve /om-webm/ por HTTP. */
async function resolveBlobPlaybackUrl(path: string, streamUrl: string): Promise<string | null> {
  if (!pywebviewActive()) return null;
  try {
    const blob = await bridge.galleryVideoPlaybackBlob(normalizePathForApi(path));
    if (blob?.ok && blob.dataUrl) return String(blob.dataUrl);
  } catch {
    return null;
  }
  return null;
}

export async function resolveMediaPlaybackInfo(
  path: string,
  opts?: { warm?: boolean; tryBlob?: boolean; playbackMode?: VideoPlaybackMode }
): Promise<MediaPlaybackInfo> {
  const mode = opts?.playbackMode ?? "auto";
  const out = await bridge.galleryMediaUrl(normalizePathForApi(path), Boolean(opts?.warm), mode);
  const fileUrl = absolutizeMediaUrl(String(out?.fileUrl ?? ""));
  let transcodeUrl = absolutizeMediaUrl(String(out?.transcodeUrl ?? ""));
  const needsTranscode = Boolean(out?.needsTranscode);
  let playbackViaBlob = false;

  if (needsTranscode && pywebviewActive() && opts?.tryBlob) {
    const dataUrl = await resolveBlobPlaybackUrl(path, transcodeUrl);
    if (dataUrl) {
      transcodeUrl = dataUrl;
      playbackViaBlob = true;
    }
  }

  return {
    fileUrl,
    transcodeUrl,
    needsTranscode,
    playbackMode: (out?.playbackMode as VideoPlaybackMode) ?? mode,
    playbackStrategy: (out?.playbackStrategy as MediaPlaybackInfo["playbackStrategy"]) ?? undefined,
    playbackViaBlob,
    ffmpegAvailable: Boolean(out?.ffmpegAvailable),
    ffprobeAvailable: Boolean(out?.ffprobeAvailable),
    transcodeCached: Boolean(out?.transcodeCached),
    playbackFormat: String(out?.playbackFormat ?? ""),
  };
}

/** Texto de estado mientras se prepara la reproducción. */
export function playbackPrepareMessage(
  info: Pick<MediaPlaybackInfo, "playbackStrategy" | "needsTranscode" | "transcodeCached">
): string {
  if (!info.needsTranscode || info.playbackStrategy === "direct") return t("preview.videoLoadingDirect");
  if (info.transcodeCached) return t("preview.videoLoadingDirect");
  if (info.playbackStrategy === "remux") return t("preview.videoRemuxing");
  return t("preview.videoTranscodingProgressive");
}

/** URL inicial según compatibilidad detectada por ffprobe en el backend. */
export function pickInitialPlaybackUrl(info: MediaPlaybackInfo): string {
  if (info.playbackMode === "direct") return info.fileUrl || info.transcodeUrl;
  if (info.needsTranscode) return info.transcodeUrl || info.fileUrl;
  return info.fileUrl || info.transcodeUrl;
}

/** Reserva de compatibilidad con llamadas antiguas. */
export async function resolveMediaFileUrl(path: string): Promise<string> {
  const info = await resolveMediaPlaybackInfo(path);
  return pickInitialPlaybackUrl(info);
}

export function mediaUrlKey(raw: string | null | undefined): string {
  const s = String(raw ?? "").trim();
  if (!s) return "";
  if (s.startsWith("data:")) return `data:${s.length}`;
  try {
    const u = s.startsWith("http") ? new URL(s) : new URL(s, "http://local");
    return `${u.pathname}${u.search}`;
  } catch {
    return s;
  }
}

/** Normaliza para comparar URLs del mismo recurso (con o sin origen). */
export function sameMediaUrl(a: string | null | undefined, b: string | null | undefined): boolean {
  const norm = (raw: string) => {
    const s = String(raw ?? "").trim();
    if (!s) return "";
    if (s.startsWith("data:")) return `data:${s.length}`;
    try {
      const u = s.startsWith("http") ? new URL(s) : new URL(s, "http://local");
      return `${u.pathname}${u.search}`;
    } catch {
      return s;
    }
  };
  const na = norm(String(a ?? ""));
  const nb = norm(String(b ?? ""));
  return Boolean(na && nb && na === nb);
}
