import type { GalleryItem } from "./api";
import {
  masonryDisplayHeightPx,
  masonryTileHeightPx,
  MASONRY_TILE_PAD_PX,
} from "./galleryMasonryLayoutMetrics";

type Bucket = Map<number, number>;

const byLayout = new Map<string, Bucket>();

function layoutKey(colWidth: number, maxH: number): string {
  return `${Math.round(colWidth)}|${Math.round(maxH)}`;
}

function bucket(colWidth: number, maxH: number): Bucket {
  const key = layoutKey(colWidth, maxH);
  let b = byLayout.get(key);
  if (!b) {
    b = new Map();
    byLayout.set(key, b);
  }
  return b;
}

export function getMasonryCachedHeight(
  mediaIndex: number,
  colWidth: number,
  maxH: number,
): number | null {
  const h = bucket(colWidth, maxH).get(mediaIndex);
  return h != null && h > 0 ? h : null;
}

export function setMasonryCachedHeight(
  mediaIndex: number,
  colWidth: number,
  maxH: number,
  height: number,
): void {
  if (mediaIndex < 0 || height <= 0) return;
  bucket(colWidth, maxH).set(mediaIndex, height);
}

/** Altura de slot: proporción real del ítem o estimación pseudo-aleatoria. */
export function masonrySlotHeightForItem(
  item: GalleryItem,
  colWidth: number,
  maxH: number,
  mediaIndex: number,
  tilePadding = MASONRY_TILE_PAD_PX,
): number {
  const tw = item.thumbW;
  const th = item.thumbH;
  if (typeof tw === "number" && typeof th === "number" && tw > 0 && th > 0) {
    return masonryDisplayHeightPx(colWidth, maxH, tw, th) + tilePadding * 2;
  }
  return masonryTileHeightPx(colWidth, maxH, mediaIndex, tilePadding);
}

/** Resuelve altura de celda: caché > dimensiones del ítem > placeholder. */
export function resolveMasonrySlotHeight(
  item: GalleryItem,
  mediaIndex: number,
  colWidth: number,
  maxH: number,
): number {
  const cached = getMasonryCachedHeight(mediaIndex, colWidth, maxH);
  if (cached != null) return cached;

  const height = masonrySlotHeightForItem(item, colWidth, maxH, mediaIndex);
  if (item.kind === "image" || item.kind === "video") {
    const tw = item.thumbW;
    const th = item.thumbH;
    if (typeof tw === "number" && typeof th === "number" && tw > 0 && th > 0) {
      setMasonryCachedHeight(mediaIndex, colWidth, maxH, height);
    }
  }
  return height;
}

export function seedMasonryHeightsFromItems(
  items: GalleryItem[],
  colWidth: number,
  maxH: number,
): void {
  for (const it of items) {
    if (it.kind !== "image" && it.kind !== "video") continue;
    const idx =
      typeof it.mediaIndex === "number" && Number.isFinite(it.mediaIndex)
        ? it.mediaIndex
        : null;
    if (idx == null) continue;
    const tw = it.thumbW;
    const th = it.thumbH;
    if (typeof tw !== "number" || typeof th !== "number" || tw <= 0 || th <= 0) continue;
    setMasonryCachedHeight(
      idx,
      colWidth,
      maxH,
      masonrySlotHeightForItem(it, colWidth, maxH, idx),
    );
  }
}

export function clearMasonryHeightCache(): void {
  byLayout.clear();
}
