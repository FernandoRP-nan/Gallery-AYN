import type { GalleryItem } from "./api";

export type VirtualLayoutEntry = {
  item: GalleryItem;
  index: number;
  top: number;
  left: number;
  width: number;
  height: number;
  /** Índice en ordered_paths (medios). */
  mediaIndex?: number;
  sectionLabel?: string;
};

export type GalleryVirtualLayout = {
  entries: VirtualLayoutEntry[];
  totalHeight: number;
  columnCount: number;
  cellSize: number;
};

const END_SPACER_PX = 58;
const DAY_BREAK_HEIGHT_PX = 36;

function sectionHeightPx(item: GalleryItem): number {
  if (item.path.includes("section:timeline:")) return 72;
  return 52;
}

/** Calcula posiciones absolutas equivalentes al CSS grid auto-fill. */
export function buildGalleryVirtualLayout(
  items: GalleryItem[],
  containerWidth: number,
  cellTargetPx: number,
  gapPx: number,
  edgePadPx: number,
  extraBottomPx = 0
): GalleryVirtualLayout {
  const inner = Math.max(0, containerWidth - edgePadPx * 2);
  const columnCount = Math.max(1, Math.floor((inner + gapPx) / (cellTargetPx + gapPx)));
  const cellSize =
    columnCount > 0 ? (inner - (columnCount - 1) * gapPx) / columnCount : cellTargetPx;

  const entries: VirtualLayoutEntry[] = [];
  let y = 0;
  let col = 0;
  let rowStartY = 0;

  for (let index = 0; index < items.length; index++) {
    const item = items[index];

    if (item.kind === "section" || item.kind === "day_break") {
      if (col > 0) {
        y = rowStartY + cellSize + gapPx;
        col = 0;
      }
      const height = item.kind === "day_break" ? DAY_BREAK_HEIGHT_PX : sectionHeightPx(item);
      entries.push({
        item,
        index,
        top: y,
        left: edgePadPx,
        width: inner,
        height,
      });
      y += height + gapPx;
      rowStartY = y;
      continue;
    }

    if (col === 0) rowStartY = y;
    entries.push({
      item,
      index,
      top: rowStartY,
      left: edgePadPx + col * (cellSize + gapPx),
      width: cellSize,
      height: cellSize,
    });
    col++;
    if (col >= columnCount) {
      y = rowStartY + cellSize + gapPx;
      col = 0;
    }
  }

  if (col > 0) y = rowStartY + cellSize;
  const totalHeight = y + END_SPACER_PX + extraBottomPx;

  return { entries, totalHeight, columnCount, cellSize };
}

export function getVisibleLayoutEntries(
  entries: VirtualLayoutEntry[],
  scrollTop: number,
  viewHeight: number,
  overscanPx = 520
): VirtualLayoutEntry[] {
  if (entries.length === 0) return [];
  const minY = scrollTop - overscanPx;
  const maxY = scrollTop + viewHeight + overscanPx;
  return entries.filter((e) => e.top + e.height >= minY && e.top <= maxY);
}
