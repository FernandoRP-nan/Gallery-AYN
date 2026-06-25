import { buildMediaFileUrl } from "./pathUtils";
import { absolutizeMediaUrl, isDataPlaybackUrl } from "./mediaUrl";

export type PreviewPayload = {
  path?: string;
  name?: string;
  dataUrl?: string | null;
  mediaType?: "image" | "video" | "svg";
  fileUrl?: string | null;
  transcodeUrl?: string | null;
  needsTranscode?: boolean;
};

function inferMediaType(
  path: string,
  kind?: string,
  apiType?: string
): "image" | "video" | "svg" {
  const mt = String(apiType ?? "").toLowerCase();
  if (mt === "video" || kind === "video") return "video";
  if (mt === "svg" || path.toLowerCase().endsWith(".svg")) return "svg";
  return "image";
}

/** URL de reproducción: vídeo → versión transcodificada (H.264/AAC) si existe. */
export function pickPreviewPlaybackUrl(
  mediaType: "image" | "video" | "svg",
  api: PreviewPayload,
  current?: PreviewPayload,
  sourcePath?: string
): string | null {
  const transcode = absolutizeMediaUrl(api.transcodeUrl ?? current?.transcodeUrl ?? null);
  const direct = absolutizeMediaUrl(
    api.fileUrl ??
      current?.fileUrl ??
      (mediaType === "video" || mediaType === "svg" || mediaType === "image"
        ? buildMediaFileUrl(sourcePath ?? "")
        : null)
  );
  if (mediaType === "video") {
    const needs = Boolean(api.needsTranscode ?? current?.needsTranscode);
    if (needs) return transcode || direct || null;
    return direct || transcode || null;
  }
  return direct || transcode || null;
}

/** Fusiona la respuesta del API sin perder fileUrl/mediaType del vídeo ya resuelto. */
export function mergePreviewApiResult(
  current: PreviewPayload,
  api: PreviewPayload,
  sourcePath: string,
  sourceKind?: string
): PreviewPayload {
  const path = String(api.path ?? current.path ?? sourcePath);
  const mediaType = inferMediaType(path, sourceKind, api.mediaType);
  const transcodeUrl = absolutizeMediaUrl(api.transcodeUrl ?? current.transcodeUrl ?? null) || null;
  const currentPlayback = absolutizeMediaUrl(current.fileUrl ?? null);

  // PyWebView: no sobrescribir data URL (blob) con /om-webm/ HTTP de gallery_preview.
  if (mediaType === "video" && isDataPlaybackUrl(currentPlayback)) {
    return {
      path,
      name: String(api.name ?? current.name ?? ""),
      mediaType,
      fileUrl: currentPlayback,
      transcodeUrl: isDataPlaybackUrl(transcodeUrl) ? transcodeUrl : currentPlayback,
      needsTranscode: Boolean(api.needsTranscode ?? current.needsTranscode),
      dataUrl: null,
    };
  }

  const fileUrl = pickPreviewPlaybackUrl(mediaType, api, current, path);

  return {
    path,
    name: String(api.name ?? current.name ?? ""),
    mediaType,
    fileUrl,
    transcodeUrl,
    needsTranscode: Boolean(api.needsTranscode ?? current.needsTranscode),
    dataUrl: mediaType === "video" ? null : api.dataUrl ?? current.dataUrl ?? null,
  };
}
