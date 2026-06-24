/** Repara UTF-8 leído como Latin-1 (ImÃ¡genes → Imágenes). */
function repairMojibake(raw: string): string {
  if (!raw || !/[\u00c2-\u00c3][\u0080-\u00bf]/.test(raw)) return raw;
  try {
    const bytes = Uint8Array.from(raw, (ch) => ch.charCodeAt(0) & 0xff);
    const fixed = new TextDecoder("utf-8").decode(bytes);
    return fixed && fixed !== raw ? fixed : raw;
  } catch {
    return raw;
  }
}

/** Normaliza rutas antes de enviarlas al backend (NFC + mojibake). */
export function normalizePathForApi(raw: string): string {
  let s = String(raw ?? "").trim();
  if (!s) return s;
  s = repairMojibake(s);
  return s.normalize("NFC");
}

/** Codifica como urllib.parse.quote(path, safe='/') en Python. */
export function quoteMediaPath(path: string): string {
  return encodeURI(path);
}

/** URL de streaming (mismo origen; /media no lo intercepta el catch-all de PyWebView). */
export function buildMediaFileUrl(rawPath: string, opts?: { transcode?: boolean }): string {
  const path = normalizePathForApi(rawPath);
  const q = new URLSearchParams({ path });
  if (opts?.transcode) q.set("transcode", "1");
  const rel = `/media?${q.toString()}`;
  if (typeof window !== "undefined") {
    const origin = window.location?.origin;
    if (origin && origin !== "null" && origin.startsWith("http")) {
      return `${origin}${rel}`;
    }
  }
  return rel;
}
