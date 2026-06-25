import type { GalleryItem } from "./api";

export type MasonrySegment =
  | { kind: "span"; item: GalleryItem }
  | { kind: "grid"; columns: GalleryItem[][] };

/** Número de columnas que caben según ancho útil y tamaño de celda. */
export function computeMasonryColumnCount(
  containerWidth: number,
  cellPx: number,
  gapPx: number,
  edgePadPx: number,
): number {
  const inner = Math.max(0, containerWidth - edgePadPx * 2);
  if (inner <= 0 || cellPx <= 0) return 1;
  return Math.max(1, Math.floor((inner + gapPx) / (cellPx + gapPx)));
}

function isMasonrySpanItem(item: GalleryItem): boolean {
  return item.kind === "section" || item.kind === "day_break";
}

/** Reparte ítems en columnas (round-robin) entre encabezados a ancho completo. */
export function buildMasonrySegments(
  items: GalleryItem[],
  columnCount: number,
): MasonrySegment[] {
  const cols = Math.max(1, columnCount);
  const segments: MasonrySegment[] = [];
  let bucket: GalleryItem[] = [];

  function flushBucket() {
    if (bucket.length === 0) return;
    const columns: GalleryItem[][] = Array.from({ length: cols }, () => []);
    bucket.forEach((item, index) => {
      columns[index % cols].push(item);
    });
    segments.push({ kind: "grid", columns });
    bucket = [];
  }

  for (const item of items) {
    if (isMasonrySpanItem(item)) {
      flushBucket();
      segments.push({ kind: "span", item });
    } else {
      bucket.push(item);
    }
  }
  flushBucket();
  return segments;
}

/** Reparto round-robin en N columnas (p. ej. sugerencias). */
export function packIntoColumns<T>(items: T[], columnCount: number): T[][] {
  const cols = Math.max(1, columnCount);
  const columns: T[][] = Array.from({ length: cols }, () => []);
  items.forEach((item, index) => {
    columns[index % cols].push(item);
  });
  return columns;
}
