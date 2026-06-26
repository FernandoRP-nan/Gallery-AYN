import type { GalleryItem } from "./api";
import type { VirtualLayoutEntry } from "./galleryVirtualLayout";
import { resolveVirtualLayoutSpans } from "./galleryLayoutSpans";
import { resolveMasonrySlotHeight } from "./galleryMasonryHeightCache";
import { masonryMaxHeightPx } from "./galleryMasonryLayoutMetrics";
import {
  type GalleryFullVirtualLayout,
  type GalleryLayoutMode,
  type GalleryLayoutSpan,
  type GalleryScrollMarker,
} from "./galleryFullVirtualLayout";

export type { GalleryFullVirtualLayout, GalleryScrollMarker };
export { masonryTileHeightPx, masonryDisplayHeightPx } from "./galleryMasonryLayoutMetrics";

const END_SPACER_PX = 58;
const FOLDER_TILE_PAD_PX = 16;

function sectionHeightPx(item: GalleryItem): number {
  if (item.path.includes("section:timeline:")) return 72;
  return 52;
}

function placeholderItem(mediaIndex: number): GalleryItem {
  return {
    kind: "placeholder",
    name: "",
    path: `placeholder:media:${mediaIndex}`,
  };
}

function folderTileHeightPx(colWidth: number): number {
  return colWidth + FOLDER_TILE_PAD_PX;
}

/** Mapa índice de medio → ítem cargado (orden de la lista actual). */
export function buildMediaIndexMap(items: GalleryItem[]): Map<number, GalleryItem> {
  const map = new Map<number, GalleryItem>();
  let sequential = 0;
  for (const it of items) {
    if (it.kind === "image" || it.kind === "video") {
      const idx =
        typeof it.mediaIndex === "number" && Number.isFinite(it.mediaIndex)
          ? it.mediaIndex
          : sequential;
      map.set(idx, it);
      sequential = Math.max(sequential, idx + 1);
    }
  }
  return map;
}

/** Masonry virtual: columnas más cortas, altura total reservada con placeholders. */
export function buildGalleryFullMasonryVirtualLayout(opts: {
  folderItems: GalleryItem[];
  mediaByIndex: Map<number, GalleryItem>;
  totalMediaCount: number;
  layoutMode: GalleryLayoutMode;
  layoutSpans: GalleryLayoutSpan[];
  containerWidth: number;
  cellTargetPx: number;
  gapPx: number;
  rowGapPx?: number;
  tilePaddingPx?: number;
  edgePadPx: number;
  extraBottomPx?: number;
}): GalleryFullVirtualLayout {
  const {
    folderItems,
    mediaByIndex,
    totalMediaCount,
    layoutMode,
    layoutSpans,
    containerWidth,
    cellTargetPx,
    gapPx,
    rowGapPx = gapPx,
    tilePaddingPx = 8,
    edgePadPx,
    extraBottomPx = 0,
  } = opts;

  const inner = Math.max(0, containerWidth - edgePadPx * 2);
  const columnCount = Math.max(1, Math.floor((inner + gapPx) / (cellTargetPx + gapPx)));
  const colWidth =
    columnCount > 0 ? (inner - (columnCount - 1) * gapPx) / columnCount : cellTargetPx;
  const maxH = masonryMaxHeightPx(cellTargetPx);

  const entries: VirtualLayoutEntry[] = [];
  const markers: GalleryScrollMarker[] = [];
  const colTops = Array.from({ length: columnCount }, () => 0);
  let entryIndex = 0;

  const { spans, railOnlyTimeline } = resolveVirtualLayoutSpans(layoutMode, layoutSpans);

  const pushTimelineMarker = (label: string, startIndex: number) => {
    const top = colMaxTop();
    syncColsTo(top);
    markers.push({ label, kind: "timeline", top, height: colWidth, startIndex });
  };

  const syncColsTo = (y: number) => {
    for (let c = 0; c < columnCount; c += 1) colTops[c] = y;
  };

  const colMaxTop = () => Math.max(...colTops);
  const shortestCol = () => {
    let pick = 0;
    for (let c = 1; c < columnCount; c += 1) {
      if (colTops[c] < colTops[pick]) pick = c;
    }
    return pick;
  };

  const pushSection = (label: string, path: string, kind: GalleryLayoutSpan["kind"], startIndex: number) => {
    const top = colMaxTop();
    syncColsTo(top);
    const sectionItem: GalleryItem = {
      kind: "section",
      name: label,
      path,
      thumbDataUrl: null,
    };
    const height = sectionHeightPx(sectionItem);
    entries.push({
      item: sectionItem,
      index: entryIndex++,
      top,
      left: edgePadPx,
      width: inner,
      height,
      sectionLabel: label,
    });
    markers.push({ label, kind, top, height, startIndex });
    syncColsTo(top + height + rowGapPx);
  };

  for (const folder of folderItems) {
    const col = shortestCol();
    const top = colTops[col];
    const height = folderTileHeightPx(colWidth);
    entries.push({
      item: folder,
      index: entryIndex++,
      top,
      left: edgePadPx + col * (colWidth + gapPx),
      width: colWidth,
      height,
    });
    colTops[col] = top + height + rowGapPx;
  }

  const emitMediaRange = (
    start: number,
    end: number,
    sectionPath?: string,
    sectionLabel?: string,
  ) => {
    if (railOnlyTimeline && sectionLabel) {
      pushTimelineMarker(sectionLabel, start);
    } else if (sectionLabel && sectionPath) {
      pushSection(sectionLabel, sectionPath, layoutMode === "grouped" ? "folder" : layoutMode, start);
    }
    for (let mediaIndex = start; mediaIndex < end; mediaIndex += 1) {
      const item = mediaByIndex.get(mediaIndex) ?? placeholderItem(mediaIndex);
      const col = shortestCol();
      const top = colTops[col];
      const height = resolveMasonrySlotHeight(item, mediaIndex, colWidth, maxH, tilePaddingPx);
      entries.push({
        item,
        index: entryIndex++,
        top,
        left: edgePadPx + col * (colWidth + gapPx),
        width: colWidth,
        height,
        mediaIndex,
      });
      colTops[col] = top + height + rowGapPx;
    }
  };

  if (spans.length > 0) {
    for (const span of spans) {
      const sectionPath =
        span.kind === "timeline"
          ? `section:timeline:${span.key ?? span.label}`
          : `section:${span.key ?? span.start}`;
      emitMediaRange(
        span.start,
        Math.min(span.end, totalMediaCount),
        railOnlyTimeline ? undefined : sectionPath,
        span.label,
      );
    }
  } else {
    emitMediaRange(0, totalMediaCount);
  }

  const totalHeight = colMaxTop() + END_SPACER_PX + extraBottomPx;

  return {
    entries,
    totalHeight,
    columnCount,
    cellSize: colWidth,
    markers,
    loadedMediaCount: mediaByIndex.size,
    totalMediaCount,
  };
}
