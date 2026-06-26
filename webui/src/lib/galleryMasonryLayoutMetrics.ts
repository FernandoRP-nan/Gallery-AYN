/** Métricas compartidas del layout masonry virtual (sin dependencias circulares). */

export const MASONRY_HEIGHT_FACTOR = 2.4;
export const MASONRY_TILE_PAD_PX = 8;

const PLACEHOLDER_ASPECTS: Array<[number, number]> = [
  [3, 4],
  [4, 3],
  [16, 9],
  [9, 16],
  [1, 1],
  [5, 7],
  [7, 5],
  [2, 3],
  [3, 2],
  [4, 5],
];

export function masonryTileHeightPx(
  colWidth: number,
  maxH: number,
  mediaIndex: number,
  tilePadding = MASONRY_TILE_PAD_PX,
): number {
  const [sw, sh] = PLACEHOLDER_ASPECTS[mediaIndex % PLACEHOLDER_ASPECTS.length];
  const jitter = 1 + ((mediaIndex * 17) % 11) / 100;
  const srcH = sh * jitter;
  const srcW = sw;
  if (srcH > srcW) {
    const th = Math.min(maxH, Math.max(1, Math.round(colWidth * (srcH / srcW))));
    return th + tilePadding * 2;
  }
  const ratio = Math.min(colWidth / srcW, maxH / srcH);
  const th = Math.max(1, Math.round(srcH * ratio));
  return th + tilePadding * 2;
}

export function masonryDisplayHeightPx(
  colWidth: number,
  maxH: number,
  srcW: number,
  srcH: number,
): number {
  if (srcH > srcW) {
    return Math.min(maxH, Math.max(1, Math.round(colWidth * (srcH / srcW))));
  }
  const ratio = Math.min(colWidth / srcW, maxH / srcH);
  return Math.max(1, Math.round(srcH * ratio));
}

export function masonryMaxHeightPx(cellTargetPx: number): number {
  return Math.round(cellTargetPx * MASONRY_HEIGHT_FACTOR);
}
