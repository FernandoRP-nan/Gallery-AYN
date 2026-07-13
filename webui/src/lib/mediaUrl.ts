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
  transcodeReason?: string;
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
    transcodeReason: String(out?.transcodeReason ?? "").trim() || undefined,
    playbackViaBlob,
    ffmpegAvailable: Boolean(out?.ffmpegAvailable),
    ffprobeAvailable: Boolean(out?.ffprobeAvailable),
    transcodeCached: Boolean(out?.transcodeCached),
    playbackFormat: String(out?.playbackFormat ?? ""),
  };
}

/** Texto de estado mientras se prepara la reproducción. */
export function playbackPrepareMessage(
  info: Pick<MediaPlaybackInfo, "playbackStrategy" | "needsTranscode" | "transcodeCached" | "transcodeReason">
): string {
  if (!info.needsTranscode || info.playbackStrategy === "direct") return t("preview.videoLoadingDirect");
  if (info.transcodeCached) return t("preview.videoLoadingDirect");
  const reason = transcodeReasonLabel(info.transcodeReason);
  if (info.playbackStrategy === "remux") {
    return reason ? tFmt("preview.videoRemuxingReason", { reason }) : t("preview.videoRemuxing");
  }
  return reason ? tFmt("preview.videoTranscodingReason", { reason }) : t("preview.videoTranscodingProgressive");
}

function tFmt(path: string, vars: Record<string, string>): string {
  let s = t(path);
  for (const [key, value] of Object.entries(vars)) {
    s = s.replace(`{${key}}`, value);
  }
  return s;
}

/** Motivo legible devuelto por ffprobe en el backend. */
export function transcodeReasonLabel(reason: string | undefined): string {
  const raw = String(reason ?? "").trim();
  if (!raw) return "";
  if (raw === "compatible" || raw === "modo_original" || raw === "direct") return "";
  if (raw === "motor_webm") return t("preview.transcodeReasonMotorWebm");
  if (raw === "webm_no_compatible") return t("preview.transcodeReasonWebmBad");
  if (raw.startsWith("contenedor ")) {
    return tFmt("preview.transcodeReasonContainer", { detail: raw.replace(/^contenedor /, "") });
  }
  if (raw.startsWith("vídeo ")) {
    return tFmt("preview.transcodeReasonVideo", { detail: raw.replace(/^vídeo /, "") });
  }
  if (raw.startsWith("audio ")) {
    return tFmt("preview.transcodeReasonAudio", { detail: raw.replace(/^audio /, "") });
  }
  if (raw.startsWith("pix_fmt ")) {
    return tFmt("preview.transcodeReasonPixFmt", { detail: raw.replace(/^pix_fmt /, "") });
  }
  return raw;
}

/** Añade parámetro de versión para forzar recarga del reproductor tras transcodificar. */
export function bustMediaUrl(url: string): string {
  const raw = String(url ?? "").trim();
  if (!raw || raw.startsWith("data:")) return raw;
  const sep = raw.includes("?") ? "&" : "?";
  return `${raw}${sep}v=${Date.now()}`;
}

/** Normaliza URL ignorando el parámetro de versión (?v=). */
export function normalizeMediaCompareKey(raw: string): string {
  const s = String(raw ?? "").trim();
  if (!s) return "";
  if (s.startsWith("data:")) return `data:${s.length}`;
  try {
    const u = s.startsWith("http") ? new URL(s) : new URL(s, "http://local");
    u.searchParams.delete("v");
    const qs = u.searchParams.toString();
    return qs ? `${u.pathname}?${qs}` : u.pathname;
  } catch {
    return s;
  }
}

/** URL inicial según compatibilidad detectada por ffprobe en el backend. */
export function pickInitialPlaybackUrl(info: MediaPlaybackInfo): string {
  if (info.playbackMode === "direct") return info.fileUrl || info.transcodeUrl;
  if (info.transcodeCached && info.transcodeUrl) return info.transcodeUrl;
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
  const na = normalizeMediaCompareKey(String(a ?? ""));
  const nb = normalizeMediaCompareKey(String(b ?? ""));
  return Boolean(na && nb && na === nb);
}
