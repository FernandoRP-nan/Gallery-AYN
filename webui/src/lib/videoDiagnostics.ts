import { t } from "./i18n";

function tFmt(path: string, vars: Record<string, string>): string {
  let s = t(path);
  for (const [key, value] of Object.entries(vars)) {
    s = s.replace(`{${key}}`, value);
  }
  return s;
}

export type VideoHttpProbe = {
  status: number;
  contentType: string;
  acceptRanges: string;
  hasMp4Header: boolean;
  fetchError: string;
};

export type VideoBackendDiagnostics = {
  path?: string;
  exists?: boolean;
  sizeBytes?: number;
  extension?: string;
  ffmpegAvailable?: boolean;
  ffmpegPath?: string | null;
  ffprobeAvailable?: boolean;
  ffprobePath?: string | null;
  videoCodec?: string | null;
  audioCodec?: string | null;
  pixFmt?: string | null;
  width?: number | null;
  height?: number | null;
  isBrowserPlayable?: boolean;
  needsTranscode?: boolean;
  ffprobeError?: string | null;
  transcodeCached?: boolean;
  transcodeCacheBytes?: number;
  transcodeTestOk?: boolean | null;
  transcodeError?: string | null;
  transcodeTestBytes?: number;
  transcodeTestMime?: string;
  viewerEngine?: string;
  playbackFormat?: string;
  playbackMime?: string;
  viewerPrefersWebm?: boolean;
  needsViewerTranscode?: boolean;
  error?: string;
  apiError?: string;
};

const MEDIA_ERROR_KEYS: Record<number, string> = {
  1: "preview.videoDiagErrAborted",
  2: "preview.videoDiagErrNetwork",
  3: "preview.videoDiagErrDecode",
  4: "preview.videoDiagErrCodec",
};

const NETWORK_STATE_KEYS = [
  "preview.videoDiagNetEmpty",
  "preview.videoDiagNetIdle",
  "preview.videoDiagNetLoading",
  "preview.videoDiagNetNoSource",
];

const READY_STATE_KEYS = [
  "preview.videoDiagReadyNothing",
  "preview.videoDiagReadyMeta",
  "preview.videoDiagReadyCurrent",
  "preview.videoDiagReadyFuture",
  "preview.videoDiagReadyEnough",
];

export function mediaErrorLabel(code: number): string {
  const key = MEDIA_ERROR_KEYS[code];
  return key ? t(key) : tFmt("preview.videoDiagErrUnknown", { code: String(code) });
}

function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function shortUrl(url: string): string {
  const raw = String(url ?? "").trim();
  if (!raw) return "—";
  try {
    const u = new URL(raw, window.location.origin);
    const path = `${u.pathname}${u.search}`;
    return path.length > 120 ? `${path.slice(0, 117)}…` : path;
  } catch {
    return raw.length > 120 ? `${raw.slice(0, 117)}…` : raw;
  }
}

/** Comprueba cabecera WebM/MP4 en la respuesta HTTP. */
export async function probeVideoHttpUrl(url: string): Promise<VideoHttpProbe> {
  const empty: VideoHttpProbe = {
    status: 0,
    contentType: "",
    acceptRanges: "",
    hasMp4Header: false,
    fetchError: "",
  };
  const raw = String(url ?? "").trim();
  if (!raw) return { ...empty, fetchError: t("preview.videoDiagHttpNoUrl") };
  if (raw.startsWith("data:")) {
    return { ...empty, status: 200, contentType: raw.slice(5).split(";")[0] || "video/webm", fetchError: "" };
  }

  try {
    const resp = await fetch(raw, {
      method: "GET",
      headers: { Range: "bytes=0-15" },
      cache: "no-store",
    });
    const blob = await resp.blob();
    const head = new Uint8Array(await blob.slice(0, 12).arrayBuffer());
    const text = Array.from(head)
      .map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : "."))
      .join("");
    const hasMp4Header = text.includes("ftyp");
    const isWebm = head[0] === 0x1a && head[1] === 0x45 && head[2] === 0xdf && head[3] === 0xa3;
    return {
      status: resp.status,
      contentType: resp.headers.get("Content-Type") ?? "",
      acceptRanges: resp.headers.get("Accept-Ranges") ?? "",
      hasMp4Header: hasMp4Header || isWebm,
      fetchError: resp.ok || resp.status === 206 ? "" : tFmt("preview.videoDiagHttpBad", { code: String(resp.status) }),
    };
  } catch (err) {
    return {
      ...empty,
      fetchError: err instanceof Error ? err.message : String(err),
    };
  }
}

export function isQtPlayerCreationError(message: string): boolean {
  return /error creating media player/i.test(String(message ?? ""));
}

export function formatVideoDiagnosticReport(opts: {
  mediaErrorCode: number;
  mediaErrorMessage: string;
  videoUrl: string;
  urlKind: "direct" | "transcode" | "webm" | "unknown";
  networkState: number;
  readyState: number;
  httpProbe: VideoHttpProbe | null;
  backend: VideoBackendDiagnostics | null;
  triedUrls: string[];
}): string {
  const lines: string[] = [];
  lines.push(t("preview.videoDiagTitle"));
  lines.push("");
  lines.push(`${t("preview.videoDiagPlayerError")}: ${mediaErrorLabel(opts.mediaErrorCode)} (${opts.mediaErrorCode})`);
  if (opts.mediaErrorMessage) {
    lines.push(`${t("preview.videoDiagPlayerDetail")}: ${opts.mediaErrorMessage}`);
  }
  lines.push(`${t("preview.videoDiagNetworkState")}: ${t(NETWORK_STATE_KEYS[opts.networkState] ?? "preview.videoDiagErrUnknown")}`);
  lines.push(`${t("preview.videoDiagReadyState")}: ${t(READY_STATE_KEYS[opts.readyState] ?? "preview.videoDiagErrUnknown")}`);
  lines.push("");
  lines.push(`${t("preview.videoDiagUrlKind")}: ${t(`preview.videoDiagUrlKind_${opts.urlKind}`)}`);
  lines.push(`${t("preview.videoDiagUrl")}: ${shortUrl(opts.videoUrl)}`);

  if (opts.triedUrls.length > 1) {
    lines.push(`${t("preview.videoDiagTriedUrls")}: ${opts.triedUrls.map(shortUrl).join(" → ")}`);
  }

  const http = opts.httpProbe;
  if (http) {
    lines.push("");
    lines.push(t("preview.videoDiagHttpSection"));
    if (http.fetchError) {
      lines.push(`${t("preview.videoDiagHttpFetch")}: ${http.fetchError}`);
      if (http.status === 0) lines.push(t("preview.videoDiagHttpZero"));
    } else {
      lines.push(`HTTP ${http.status} · ${http.contentType || "?"}`);
      lines.push(`${t("preview.videoDiagHttpRanges")}: ${http.acceptRanges || "—"}`);
      lines.push(`${t("preview.videoDiagHttpMp4")}: ${http.hasMp4Header ? t("preview.videoDiagYes") : t("preview.videoDiagNo")}`);
      const urlKey = (() => {
        try {
          const u = opts.videoUrl.startsWith("http") ? new URL(opts.videoUrl) : new URL(opts.videoUrl, "http://local");
          return `${u.pathname}${u.search}`;
        } catch {
          return opts.videoUrl;
        }
      })();
      if (urlKey.includes(".webm") || urlKey.startsWith("/om-webm/")) {
        lines.push(`${t("preview.videoDiagPlaybackFormat")}: webm`);
      }
    }
  }

  const b = opts.backend;
  if (b) {
    lines.push("");
    lines.push(t("preview.videoDiagViewerSection"));
    if (b.viewerEngine) lines.push(`${t("preview.videoDiagViewerEngine")}: ${b.viewerEngine}`);
    if (b.playbackFormat) {
      lines.push(`${t("preview.videoDiagPlaybackFormat")}: ${b.playbackFormat} (${b.playbackMime ?? "?"})`);
    }
    if (b.viewerPrefersWebm) lines.push(t("preview.videoDiagViewerWebmHint"));
    if (isQtPlayerCreationError(opts.mediaErrorMessage) && b.isBrowserPlayable) {
      lines.push(t("preview.videoDiagQtNoH264"));
    }
    lines.push("");
    lines.push(t("preview.videoDiagFileSection"));
    if (b.apiError) lines.push(`${t("preview.videoDiagApiError")}: ${b.apiError}`);
    if (b.error) lines.push(b.error);
    if (b.exists === false) lines.push(t("preview.videoDiagFileMissing"));
    if (b.sizeBytes != null) lines.push(`${t("preview.videoDiagFileSize")}: ${fmtBytes(b.sizeBytes)} (${b.extension ?? ".?"})`);
    if (b.videoCodec || b.audioCodec) {
      const v = b.videoCodec ?? "—";
      const a = b.audioCodec ?? t("preview.videoDiagNoAudio");
      const pix = b.pixFmt ? ` · ${b.pixFmt}` : "";
      const dim = b.width && b.height ? ` · ${b.width}×${b.height}` : "";
      lines.push(`${t("preview.videoDiagCodecs")}: ${v}${pix}${dim} + ${a}`);
    }
    if (b.ffprobeError) lines.push(`${t("preview.videoDiagFfprobeError")}: ${b.ffprobeError}`);
    lines.push(
      `${t("preview.videoDiagFileCodecOk")}: ${b.isBrowserPlayable ? t("preview.videoDiagYes") : t("preview.videoDiagNo")}`
    );
    if (b.needsViewerTranscode ?? b.needsTranscode) lines.push(t("preview.videoDiagViewerTranscode"));
    lines.push("");
    lines.push(t("preview.videoDiagToolsSection"));
    lines.push(
      `ffmpeg: ${b.ffmpegAvailable ? b.ffmpegPath ?? t("preview.videoDiagYes") : t("preview.videoDiagMissing")}`
    );
    lines.push(
      `ffprobe: ${b.ffprobeAvailable ? b.ffprobePath ?? t("preview.videoDiagYes") : t("preview.videoDiagMissing")}`
    );
    if (b.transcodeCached != null) {
      lines.push(
        `${t("preview.videoDiagTranscodeCache")}: ${b.transcodeCached ? `${t("preview.videoDiagYes")} (${fmtBytes(b.transcodeCacheBytes ?? 0)})` : t("preview.videoDiagNo")}`
      );
    }
    if (b.transcodeTestOk === true) {
      const mime = b.transcodeTestMime ? ` · ${b.transcodeTestMime}` : "";
      lines.push(`${t("preview.videoDiagTranscodeTest")}: ${t("preview.videoDiagOk")} (${fmtBytes(b.transcodeTestBytes ?? 0)}${mime})`);
    } else if (b.transcodeTestOk === false && b.transcodeError) {
      lines.push(`${t("preview.videoDiagTranscodeTest")}: ${t("preview.videoDiagFailed")}`);
      lines.push(`${t("preview.videoDiagTranscodeError")}: ${b.transcodeError}`);
    }
  }

  return lines.join("\n");
}
