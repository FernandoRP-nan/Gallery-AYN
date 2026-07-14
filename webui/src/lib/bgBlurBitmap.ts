import { normalizeBgBlur } from "./uiAppearance";

/** Resolución de la textura de fondo (suficiente con blur; menos trabajo en canvas). */
const CANVAS_W = 1120;
const CANVAS_H = 630;
const CACHE_MAX = 6;

const cache = new Map<string, string>();

function cacheSet(key: string, value: string): void {
  if (cache.has(key)) cache.delete(key);
  cache.set(key, value);
  if (cache.size > CACHE_MAX) {
    const oldest = cache.keys().next().value;
    if (oldest) cache.delete(oldest);
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("background image load failed"));
    img.src = src;
  });
}

/** Rectángulo tipo object-fit: cover con margen extra para el blur en los bordes. */
function coverRect(
  imageW: number,
  imageH: number,
  canvasW: number,
  canvasH: number,
  bleed: number
): { dx: number; dy: number; dw: number; dh: number } {
  const imageRatio = imageW / imageH;
  const canvasRatio = canvasW / canvasH;
  let dw: number;
  let dh: number;
  if (imageRatio > canvasRatio) {
    dh = canvasH + bleed * 2;
    dw = dh * imageRatio;
  } else {
    dw = canvasW + bleed * 2;
    dh = dw / imageRatio;
  }
  return {
    dx: (canvasW - dw) / 2,
    dy: (canvasH - dh) / 2,
    dw,
    dh,
  };
}

/**
 * Devuelve URL lista para <img>: nítida si blur=0, o bitmap pre-desenfocado (sin filter CSS en vivo).
 */
export async function resolveBgDisplayUrl(imageUrl: string, blurPx: number): Promise<string> {
  const url = String(imageUrl ?? "").trim();
  const blur = normalizeBgBlur(blurPx);
  if (!url) return "";
  if (blur <= 0) return url;

  const key = `${url}\0${blur}`;
  const cached = cache.get(key);
  if (cached) return cached;

  if (typeof document === "undefined") return url;

  try {
    const img = await loadImage(url);
    const iw = Math.max(1, img.naturalWidth);
    const ih = Math.max(1, img.naturalHeight);
    const bleed = blur * 3;
    const { dx, dy, dw, dh } = coverRect(iw, ih, CANVAS_W, CANVAS_H, bleed);

    const canvas = document.createElement("canvas");
    canvas.width = CANVAS_W;
    canvas.height = CANVAS_H;
    const ctx = canvas.getContext("2d");
    if (!ctx) return url;

    ctx.filter = `blur(${blur}px)`;
    ctx.drawImage(img, dx, dy, dw, dh);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.82);
    cacheSet(key, dataUrl);
    return dataUrl;
  } catch {
    return url;
  }
}
