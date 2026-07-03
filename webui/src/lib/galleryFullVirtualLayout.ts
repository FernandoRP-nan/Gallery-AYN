import type { GalleryItem } from "./api";
import type { VirtualLayoutEntry } from "./galleryVirtualLayout";
import { resolveVirtualLayoutSpans, virtualSectionPath } from "./galleryLayoutSpans";

export type GalleryLayoutSpan = {
  start: number;
  end: number;
  label: string;
  kind: "timeline" | "folder" | "alpha";
  key?: string;
};

export type GalleryLayoutMode = "flat" | "timeline" | "grouped" | "alpha";

export type GalleryScrollMarker = {
  label: string;
  kind: GalleryLayoutSpan["kind"] | "flat";
  top: number;
  height: number;
  startIndex: number;
};

export type GalleryFullVirtualLayout = {
  entries: VirtualLayoutEntry[];
  totalHeight: number;
  columnCount: number;
  cellSize: number;
  markers: GalleryScrollMarker[];
  loadedMediaCount: number;
  totalMediaCount: number;
};

const END_SPACER_PX = 58;
const DAY_BREAK_HEIGHT_PX = 36;

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

function pushGridCell(
  entries: VirtualLayoutEntry[],
  item: GalleryItem,
  index: number,
  col: number,
  rowStartY: number,
  cellSize: number,
  gapPx: number,
  edgePadPx: number,
  inner: number,
  mediaIndex?: number
) {
  entries.push({
    item,
    index,
    top: rowStartY,
    left: edgePadPx + col * (cellSize + gapPx),
    width: cellSize,
    height: cellSize,
    mediaIndex,
  });
}

function advanceGridRow(
  col: number,
  rowStartY: number,
  cellSize: number,
  gapPx: number,
  columnCount: number
): { col: number; rowStartY: number; y: number } {
  col += 1;
  if (col >= columnCount) {
    return { col: 0, rowStartY: rowStartY + cellSize + gapPx, y: rowStartY + cellSize + gapPx };
  }
  return { col, rowStartY, y: rowStartY };
}

/** Rejilla virtual con huecos para medios aún no cargados y secciones completas. */
export function buildGalleryFullVirtualLayout(opts: {
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
  const cellSize =
    columnCount > 0 ? (inner - (columnCount - 1) * gapPx) / columnCount : cellTargetPx;

  const entries: VirtualLayoutEntry[] = [];
  const markers: GalleryScrollMarker[] = [];
  let y = 0;
  let col = 0;
  let rowStartY = 0;
  let entryIndex = 0;

  const { spans, railOnlyTimeline } = resolveVirtualLayoutSpans(layoutMode, layoutSpans);

  const pushTimelineMarker = (label: string, startIndex: number) => {
    markers.push({
      label,
      kind: "timeline",
      top: y,
      height: cellSize,
      startIndex,
    });
  };

  const pushSection = (
    label: string,
    path: string,
    kind: GalleryLayoutSpan["kind"],
    startIndex: number,
    sectionFolder = "",
  ) => {
    if (col > 0) {
      y = rowStartY + cellSize + gapPx;
      col = 0;
      rowStartY = y;
    }
    const sectionItem: GalleryItem = {
      kind: "section",
      name: label,
      path: path,
      sectionFolder: sectionFolder || undefined,
      thumbDataUrl: null,
    };
    const height = sectionHeightPx(sectionItem);
    entries.push({
      item: sectionItem,
      index: entryIndex++,
      top: y,
      left: edgePadPx,
      width: inner,
      height,
      sectionLabel: label,
    });
    markers.push({
      label,
      kind,
      top: y,
      height,
      startIndex,
    });
    y += height + gapPx;
    rowStartY = y;
  };

  if (folderItems.length > 0 && col > 0) {
    y = rowStartY + cellSize + gapPx;
    col = 0;
    rowStartY = y;
  }

  for (const folder of folderItems) {
    entries.push({
      item: folder,
      index: entryIndex++,
      top: rowStartY,
      left: edgePadPx + col * (cellSize + gapPx),
      width: cellSize,
      height: cellSize,
    });
    const next = advanceGridRow(col, rowStartY, cellSize, gapPx, columnCount);
    col = next.col;
    rowStartY = next.rowStartY;
    y = next.y;
  }

  const emitMediaRange = (
    start: number,
    end: number,
    sectionPath?: string,
    sectionLabel?: string,
    sectionFolder = "",
  ) => {
    if (railOnlyTimeline && sectionLabel) {
      pushTimelineMarker(sectionLabel, start);
    } else if (sectionLabel && sectionPath) {
      pushSection(
        sectionLabel,
        sectionPath,
        layoutMode === "grouped" ? "folder" : layoutMode,
        start,
        sectionFolder,
      );
    }
    for (let mediaIndex = start; mediaIndex < end; mediaIndex += 1) {
      const item = mediaByIndex.get(mediaIndex) ?? placeholderItem(mediaIndex);
      pushGridCell(
        entries,
        item,
        entryIndex++,
        col,
        rowStartY,
        cellSize,
        gapPx,
        edgePadPx,
        inner,
        mediaIndex
      );
      const next = advanceGridRow(col, rowStartY, cellSize, gapPx, columnCount);
      col = next.col;
      rowStartY = next.rowStartY;
      y = next.y;
    }
  };

  if (spans.length > 0) {
    for (const span of spans) {
      const sectionPath = virtualSectionPath(span);
      emitMediaRange(
        span.start,
        Math.min(span.end, totalMediaCount),
        railOnlyTimeline ? undefined : sectionPath,
        span.label,
        span.kind === "folder" ? String(span.key ?? "") : "",
      );
    }
  } else {
    emitMediaRange(0, totalMediaCount);
  }

  if (col > 0) y = rowStartY + cellSize;
  const totalHeight = y + END_SPACER_PX + extraBottomPx;

  return {
    entries,
    totalHeight,
    columnCount,
    cellSize,
    markers,
    loadedMediaCount: mediaByIndex.size,
    totalMediaCount,
  };
}

/** Y inferior del tramo virtual ya cargado (índices < loadedEnd). */
export function virtualLoadedBottomY(
  entries: VirtualLayoutEntry[],
  loadedEnd: number,
): number {
  let bottom = 0;
  for (const e of entries) {
    if (e.mediaIndex == null || e.mediaIndex >= loadedEnd) continue;
    bottom = Math.max(bottom, e.top + e.height);
  }
  return bottom;
}

/** Y superior del tramo virtual ya cargado (índices >= loadedStart). */
export function virtualLoadedTopY(
  entries: VirtualLayoutEntry[],
  loadedStart: number,
): number {
  let top = Number.POSITIVE_INFINITY;
  for (const e of entries) {
    if (e.mediaIndex == null || e.mediaIndex < loadedStart) continue;
    top = Math.min(top, e.top);
  }
  return Number.isFinite(top) ? top : 0;
}

/** Índice de medio más alto visible + cola de precarga. */
export function estimateTargetMediaIndex(
  entries: VirtualLayoutEntry[],
  scrollTop: number,
  viewHeight: number,
  overscanPx = 640
): number {
  const minY = scrollTop - overscanPx;
  const maxY = scrollTop + viewHeight + overscanPx;
  let maxIndex = -1;
  let minIndex = Number.POSITIVE_INFINITY;
  for (const e of entries) {
    if (e.mediaIndex == null) continue;
    if (e.top + e.height < minY || e.top > maxY) continue;
    maxIndex = Math.max(maxIndex, e.mediaIndex);
    minIndex = Math.min(minIndex, e.mediaIndex);
  }
  if (maxIndex < 0) return -1;
  // Si el viewport está en zona aún no cargada, pedir desde el primer hueco visible.
  return Number.isFinite(minIndex) ? Math.max(maxIndex, minIndex) : maxIndex;
}

/** Marca de sección activa según el scroll. */
export function scrollMarkerAt(
  markers: GalleryScrollMarker[],
  scrollTop: number,
  viewHeight: number
): GalleryScrollMarker | null {
  if (markers.length === 0) return null;
  const anchor = scrollTop + Math.min(96, viewHeight * 0.18);
  let active: GalleryScrollMarker | null = markers[0];
  for (const m of markers) {
    if (m.top <= anchor) active = m;
    else break;
  }
  return active;
}

export function markerPositionRatio(marker: GalleryScrollMarker, totalHeight: number): number {
  if (totalHeight <= 0) return 0;
  return Math.min(1, Math.max(0, marker.top / totalHeight));
}
