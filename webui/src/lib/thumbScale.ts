/** Debe coincidir con org_multimedia.web_api._thumb_px_from_gallery_scale */

const G_LO = 0.01;
const G_HI = 2.25;
const G_PX_MIN = 48;
const G_PX_MAX = 340;

export function galleryThumbPx(scale: number): number {
  const s = Math.min(G_HI, Math.max(G_LO, scale));
  return Math.round(G_PX_MIN + ((s - G_LO) / (G_HI - G_LO)) * (G_PX_MAX - G_PX_MIN));
}

/** Padding visual aproximado (borde + etiqueta) para ancho de celda en CSS */
export function galleryGridCellPx(scale: number): number {
  return galleryThumbPx(scale) + 36;
}

/** Coincide con org_multimedia.web_api._thumb_px_from_dest_scale */
const D_LO = 0.7;
const D_HI = 2.1;
const D_PX_MIN = 72;
const D_PX_MAX = 320;

export function destPreviewThumbPx(scale: number): number {
  const s = Math.min(D_HI, Math.max(D_LO, scale));
  return Math.round(D_PX_MIN + ((s - D_LO) / (D_HI - D_LO)) * (D_PX_MAX - D_PX_MIN));
}

/** Mínimo de pista en la rejilla del modal destino (auto-fill, sin scroll horizontal). */
export function destPreviewGridMinPx(scale: number): number {
  return destPreviewThumbPx(scale) + 28;
}
