/** Debe coincidir con org_multimedia.web_api._thumb_px_from_gallery_scale */

const G_LO = 0.75;
const G_HI = 2.25;
const G_PX_MIN = 80;
const G_PX_MAX = 340;

export function galleryThumbPx(scale: number): number {
  const s = Math.min(G_HI, Math.max(G_LO, scale));
  return Math.round(G_PX_MIN + ((s - G_LO) / (G_HI - G_LO)) * (G_PX_MAX - G_PX_MIN));
}

/** Padding visual aproximado (borde + etiqueta) para ancho de celda en CSS */
export function galleryGridCellPx(scale: number): number {
  return galleryThumbPx(scale) + 36;
}
