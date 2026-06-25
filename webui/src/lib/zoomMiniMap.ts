import {
  clampPan,
  getPanLimits,
  type ImageZoomMode,
} from "./imageZoomView";

export type MiniMapImageLayout = {
  offsetX: number;
  offsetY: number;
  imgW: number;
  imgH: number;
};

/** Dimensiones del minimapa según proporción de la imagen y espacio del visor. */
export function computeMiniMapSize(
  naturalW: number,
  naturalH: number,
  stageW: number,
  stageH: number
): { width: number; height: number } {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  const ar = nw / nh;
  const maxW = Math.min(200, Math.max(120, stageW * 0.22));
  const maxH = Math.min(380, Math.max(120, stageH * 0.58));
  const minW = 72;
  const minH = 48;

  let width: number;
  let height: number;
  if (ar >= 1) {
    width = maxW;
    height = width / ar;
    if (height < minH) {
      height = minH;
      width = Math.min(maxW, height * ar);
    }
  } else {
    height = maxH;
    width = height * ar;
    if (width < minW) {
      width = minW;
      height = Math.min(maxH, width / ar);
    }
  }
  return {
    width: Math.round(Math.min(maxW, Math.max(minW, width))),
    height: Math.round(Math.min(maxH, Math.max(minH, height))),
  };
}

export function computeMiniMapImageLayout(
  miniW: number,
  miniH: number,
  naturalW: number,
  naturalH: number
): MiniMapImageLayout {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  const miniScale = Math.min(miniW / nw, miniH / nh);
  const imgW = nw * miniScale;
  const imgH = nh * miniScale;
  return {
    offsetX: (miniW - imgW) / 2,
    offsetY: (miniH - imgH) / 2,
    imgW,
    imgH,
  };
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

/** Porción visible de la imagen en coordenadas normalizadas [0,1]. */
export function computeViewportNorm(
  mode: ImageZoomMode,
  scale: number,
  panX: number,
  panY: number,
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number
): { x0: number; y0: number; x1: number; y1: number } {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);

  if (mode === "fillWidth") {
    const scaledH = stageW * (nh / nw) * scale;
    if (scaledH <= stageH + 0.5) {
      return { x0: 0, y0: 0, x1: 1, y1: 1 };
    }
    const y0 = clamp01(-panY / scaledH);
    const y1 = clamp01((-panY + stageH) / scaledH);
    return { x0: 0, y0, x1: 1, y1: Math.max(y0 + 0.02, y1) };
  }

  let layoutW = stageW;
  let layoutH = (stageW * nh) / nw;
  if (layoutH > stageH) {
    layoutH = stageH;
    layoutW = (stageH * nw) / nh;
  }
  const scaledW = layoutW * scale;
  const scaledH = layoutH * scale;

  if (scaledW <= stageW + 0.5 && scaledH <= stageH + 0.5) {
    return { x0: 0, y0: 0, x1: 1, y1: 1 };
  }

  const imgLeft = stageW / 2 + panX - scaledW / 2;
  const imgTop = stageH / 2 + panY - scaledH / 2;
  const x0 = clamp01((0 - imgLeft) / scaledW);
  const x1 = clamp01((stageW - imgLeft) / scaledW);
  const y0 = clamp01((0 - imgTop) / scaledH);
  const y1 = clamp01((stageH - imgTop) / scaledH);
  return {
    x0,
    y0,
    x1: Math.max(x0 + 0.02, x1),
    y1: Math.max(y0 + 0.02, y1),
  };
}

export function computeMiniMapRectStyle(
  layout: MiniMapImageLayout,
  viewport: { x0: number; y0: number; x1: number; y1: number }
): string {
  const left = layout.offsetX + viewport.x0 * layout.imgW;
  const top = layout.offsetY + viewport.y0 * layout.imgH;
  const width = Math.max(3, (viewport.x1 - viewport.x0) * layout.imgW);
  const height = Math.max(3, (viewport.y1 - viewport.y0) * layout.imgH);
  return `left:${left}px;top:${top}px;width:${width}px;height:${height}px;`;
}

/** Convierte un clic dentro del minimapa a pan del visor principal. */
export function panFromMiniMapNorm(
  mode: ImageZoomMode,
  scale: number,
  panX: number,
  panY: number,
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number,
  normX: number,
  normY: number
): { panX: number; panY: number } {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  const nx = clamp01(normX);
  const ny = clamp01(normY);

  if (mode === "fillWidth") {
    const scaledH = stageW * (nh / nw) * scale;
    const targetTop = ny * scaledH - stageH / 2;
    let nextPanY = -targetTop;
    const limits = getPanLimits(mode, stageW, stageH, nw, nh, scale);
    return clampPan(mode, 0, nextPanY, limits);
  }

  let layoutW = stageW;
  let layoutH = (stageW * nh) / nw;
  if (layoutH > stageH) {
    layoutH = stageH;
    layoutW = (stageH * nw) / nh;
  }
  const scaledW = layoutW * scale;
  const scaledH = layoutH * scale;
  let nextPanX = scaledW / 2 - nx * scaledW;
  let nextPanY = scaledH / 2 - ny * scaledH;
  const limits = getPanLimits(mode, stageW, stageH, nw, nh, scale);
  return clampPan(mode, nextPanX, nextPanY, limits);
}

/** Punto del minimapa → coordenadas normalizadas sobre la imagen. */
export function miniMapPointToNorm(
  layout: MiniMapImageLayout,
  localX: number,
  localY: number
): { normX: number; normY: number } | null {
  const x = localX - layout.offsetX;
  const y = localY - layout.offsetY;
  if (x < 0 || y < 0 || x > layout.imgW || y > layout.imgH) return null;
  return {
    normX: x / Math.max(1, layout.imgW),
    normY: y / Math.max(1, layout.imgH),
  };
}

export function miniMapHasOverflow(
  mode: ImageZoomMode,
  scale: number,
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number
): boolean {
  const limits = getPanLimits(mode, stageW, stageH, naturalW, naturalH, scale);
  return limits.x > 0.5 || limits.y > 0.5;
}
