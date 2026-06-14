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

/** URL de streaming en el mismo origen que la UI (vídeo / SVG). */
export function buildMediaFileUrl(rawPath: string): string {
  const path = normalizePathForApi(rawPath);
  return `/media?path=${encodeURIComponent(path)}`;
}
