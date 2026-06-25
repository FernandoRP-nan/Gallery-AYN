export type ImageZoomMode = "fit" | "fillWidth";

export function pickImageDisplaySrc(
  mode: ImageZoomMode,
  scale: number,
  fileUrl: string | null | undefined,
  dataUrl: string | null | undefined
): string | null {
  const useNative = mode === "fillWidth" || scale > 1.01 || scale < 0.99;
  if (useNative && fileUrl) return fileUrl;
  return dataUrl ?? fileUrl ?? null;
}

export function buildImageZoomTransform(
  mode: ImageZoomMode,
  scale: number,
  panX: number,
  panY: number
): string {
  if (mode === "fit" && Math.round(scale * 100) === 100) {
    return "translate(-50%, -50%)";
  }
  if (mode === "fillWidth") {
    return `translate(-50%, 0%) translate(0px, ${panY}px) scale(${scale})`;
  }
  return `translate(-50%, -50%) translate(${panX}px, ${panY}px) scale(${scale})`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function getFillWidthPanLimitY(
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number,
  scale: number
): number {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  const layoutH = stageW * (nh / nw);
  const scaledH = layoutH * scale;
  return Math.max(0, scaledH - stageH);
}

export function getFitPanLimits(
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number,
  scale: number
): { x: number; y: number } {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  let layoutW = stageW;
  let layoutH = (stageW * nh) / nw;
  if (layoutH > stageH) {
    layoutH = stageH;
    layoutW = (stageH * nw) / nh;
  }
  const scaledW = layoutW * scale;
  const scaledH = layoutH * scale;
  return {
    x: Math.max(0, (scaledW - stageW) / 2),
    y: Math.max(0, (scaledH - stageH) / 2),
  };
}

export function getPanLimits(
  mode: ImageZoomMode,
  stageW: number,
  stageH: number,
  naturalW: number,
  naturalH: number,
  scale: number
): { x: number; y: number } {
  if (mode === "fillWidth") {
    return { x: 0, y: getFillWidthPanLimitY(stageW, stageH, naturalW, naturalH, scale) };
  }
  return getFitPanLimits(stageW, stageH, naturalW, naturalH, scale);
}

export function clampPan(
  mode: ImageZoomMode,
  panX: number,
  panY: number,
  limits: { x: number; y: number }
): { panX: number; panY: number } {
  const nextX = mode === "fillWidth" ? 0 : clamp(panX, -limits.x, limits.x);
  const nextY =
    mode === "fillWidth" ? clamp(panY, -limits.y, 0) : clamp(panY, -limits.y, limits.y);
  return { panX: nextX, panY: nextY };
}
