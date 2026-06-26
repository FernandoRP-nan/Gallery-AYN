import type { GalleryItem } from "./api";
import type { VirtualLayoutEntry } from "./galleryVirtualLayout";
import { resolveVirtualLayoutSpans } from "./galleryLayoutSpans";
import {
  type GalleryFullVirtualLayout,
  type GalleryLayoutMode,
  type GalleryLayoutSpan,
  type GalleryScrollMarker,
} from "./galleryFullVirtualLayout";

export type { GalleryFullVirtualLayout, GalleryScrollMarker };

const END_SPACER_PX = 58;
const MASONRY_HEIGHT_FACTOR = 2.4;
const TILE_PAD_PX = 8;
const FOLDER_TILE_PAD_PX = 16;

/** Proporciones pseudo-deterministas (ancho:alto) para huecos sin miniatura. */
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

/** Altura de tile masonry alineada con masonry_thumb_target_size del backend. */
export function masonryTileHeightPx(
  colWidth: number,
  maxH: number,
  mediaIndex: number,
  tilePadding = TILE_PAD_PX,
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

/** Altura visible de imagen masonry (sin padding del tile). */
function masonryDisplayHeightPx(
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

function masonryItemHeightPx(
  item: GalleryItem,
  colWidth: number,
  maxH: number,
  mediaIndex: number,
  tilePadding = TILE_PAD_PX,
): number {
  const tw = item.thumbW;
  const th = item.thumbH;
  if (typeof tw === "number" && typeof th === "number" && tw > 0 && th > 0) {
    return masonryDisplayHeightPx(colWidth, maxH, tw, th) + tilePadding * 2;
  }
  return masonryTileHeightPx(colWidth, maxH, mediaIndex, tilePadding);
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
    edgePadPx,
    extraBottomPx = 0,
  } = opts;

  const inner = Math.max(0, containerWidth - edgePadPx * 2);
  const columnCount = Math.max(1, Math.floor((inner + gapPx) / (cellTargetPx + gapPx)));
  const colWidth =
    columnCount > 0 ? (inner - (columnCount - 1) * gapPx) / columnCount : cellTargetPx;
  const maxH = Math.round(cellTargetPx * MASONRY_HEIGHT_FACTOR);

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

  const colMinTop = () => Math.min(...colTops);
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
    syncColsTo(top + height + gapPx);
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
    colTops[col] = top + height + gapPx;
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
      const height = masonryItemHeightPx(item, colWidth, maxH, mediaIndex);
      entries.push({
        item,
        index: entryIndex++,
        top,
        left: edgePadPx + col * (colWidth + gapPx),
        width: colWidth,
        height,
        mediaIndex,
      });
      colTops[col] = top + height + gapPx;
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
