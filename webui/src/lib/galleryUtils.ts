import type { GalleryItem } from "./api";
import {
  preserveItemThumbInCache,
  hasGalleryThumbHq,
  getGalleryThumbHq,
} from "./galleryThumbHqCache";

export function isGalleryMediaKind(kind: GalleryItem["kind"]): boolean {
  return kind === "image" || kind === "video";
}

/** Seleccionable en modo edición (incluye subcarpetas; no folder_up ni secciones). */
export function isGallerySelectableKind(kind: GalleryItem["kind"]): boolean {
  return kind === "image" || kind === "video" || kind === "folder";
}

/** Extensión del archivo en mayúsculas (p. ej. MP4) para la insignia en miniaturas de vídeo. */
export function videoFormatLabel(pathOrName: string): string | null {
  const raw = String(pathOrName ?? "").trim();
  if (!raw) return null;
  const base = raw.split(/[/\\]/).pop() ?? raw;
  const dot = base.lastIndexOf(".");
  if (dot < 0 || dot >= base.length - 1) return null;
  const ext = base.slice(dot + 1).trim().toLowerCase();
  return ext ? ext.toUpperCase() : null;
}

export function mergeItemsKeepingBestThumb(
  prevItems: GalleryItem[],
  nextItems: GalleryItem[],
  opts?: { preserveSelection?: boolean },
): GalleryItem[] {
  const preserveSelection = opts?.preserveSelection !== false;
  const prevByPath = new Map(prevItems.map((x) => [x.path, x] as const));
  return nextItems.map((it) => {
    const prev = prevByPath.get(it.path);
    if (!prev) return it;

    if (!isGalleryMediaKind(it.kind) || !isGalleryMediaKind(prev.kind)) {
      if (prev.kind === it.kind && prev.name === it.name && prev.path === it.path) {
        return preserveSelection ? { ...prev, selected: prev.selected } : prev;
      }
      return preserveSelection ? { ...it, selected: prev.selected } : it;
    }

    const prevQ = hasGalleryThumbHq(prev.path)
      ? "hq"
      : prev.thumbQuality ?? (prev.thumbDataUrl ? "hq" : undefined);
    const nextQ = it.thumbQuality ?? (it.thumbDataUrl ? "hq" : undefined);
    const prevScore = prevQ === "hq" ? 2 : prevQ === "lq" ? 1 : 0;
    const nextScore = nextQ === "hq" ? 2 : nextQ === "lq" ? 1 : 0;

    let thumbUrl = it.thumbDataUrl;
    let thumbQ = it.thumbQuality;
    let thumbLq = it.thumbLqDataUrl ?? prev.thumbLqDataUrl ?? null;

    if (prevScore > nextScore) {
      preserveItemThumbInCache(prev);
      const cached = getGalleryThumbHq(prev.path);
      thumbLq =
        prev.thumbLqDataUrl ??
        (prev.thumbQuality === "lq" ? prev.thumbDataUrl : null) ??
        cached?.lqUrl ??
        cached?.hqUrl ??
        thumbLq;
      thumbUrl = thumbLq;
      thumbQ = thumbLq ? ("lq" as const) : undefined;
      if (!thumbUrl && it.thumbDataUrl) return preserveSelection ? { ...it, selected: prev.selected } : it;
    }

    const selected = preserveSelection ? prev.selected : it.selected;
    const hasChanges =
      Boolean(prev.selected) !== Boolean(selected) ||
      prev.thumbDataUrl !== thumbUrl ||
      prev.thumbQuality !== thumbQ ||
      prev.thumbLqDataUrl !== thumbLq ||
      prev.name !== it.name ||
      prev.kind !== it.kind;

    if (!hasChanges) return prev;

    return {
      ...prev,
      selected,
      thumbDataUrl: thumbUrl,
      thumbLqDataUrl: thumbLq,
      thumbQuality: thumbQ,
      name: it.name,
      kind: it.kind,
    };
  });
}

const TIMELINE_DAY_MIN_PX = 130;

/** Meses abreviados para marcas de día en la línea de tiempo. */
const TIMELINE_MONTH_ABBR_ES = [
  "",
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
] as const;

/** Etiqueta de día: «15 Ene 2024» a partir de ISO YYYY-MM-DD. */
export function formatTimelineDayLabel(isoDate: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(isoDate ?? "").trim());
  if (!m) return String(isoDate ?? "").trim();
  const year = m[1];
  const monthIdx = parseInt(m[2], 10);
  const day = parseInt(m[3], 10);
  const abbr = TIMELINE_MONTH_ABBR_ES[monthIdx] ?? m[2];
  const month = abbr.charAt(0).toUpperCase() + abbr.slice(1);
  return `${day} ${month} ${year}`;
}

export function expandTimelineDayBreaks(raw: GalleryItem[], timeline: boolean, cellPx: number): GalleryItem[] {
  if (!timeline || cellPx < TIMELINE_DAY_MIN_PX) return raw;
  const out: GalleryItem[] = [];
  let lastDay: string | null = null;
  for (const it of raw) {
    if (it.kind === "section") {
      lastDay = null;
      out.push(it);
      continue;
    }
    if (!isGalleryMediaKind(it.kind)) {
      out.push(it);
      continue;
    }
    const iso = it.mtimeIso?.trim();
    if (iso && iso.length >= 10) {
      const day = iso.slice(0, 10);
      if (lastDay !== null && day !== lastDay) {
        out.push({
          kind: "day_break",
          name: formatTimelineDayLabel(day),
          path: `daybreak:${day}:${out.length}`,
          thumbDataUrl: null,
        });
      }
      lastDay = day;
    }
    out.push(it);
  }
  return out;
}

export function countSelectedMedia(items: GalleryItem[]): number {
  return items.filter((x) => isGalleryMediaKind(x.kind) && x.selected).length;
}

export function countSelectedGalleryItems(items: GalleryItem[]): number {
  return items.filter((x) => isGallerySelectableKind(x.kind) && x.selected).length;
}

/** Tras quitar medios, decrementa mediaIndex global para cerrar huecos en scroll virtual. */
export function shiftGalleryMediaIndicesAfterRemoval(
  items: GalleryItem[],
  removedMediaIndices: number[],
): GalleryItem[] {
  const removed = [...removedMediaIndices]
    .filter((n) => Number.isFinite(n))
    .sort((a, b) => a - b);
  if (removed.length === 0) return items;
  return items.map((it) => {
    if (!isGalleryMediaKind(it.kind)) return it;
    const idx = it.mediaIndex;
    if (typeof idx !== "number" || !Number.isFinite(idx)) return it;
    let shift = 0;
    for (const r of removed) {
      if (idx > r) shift += 1;
    }
    const nextIdx = idx - shift;
    return nextIdx === idx ? it : { ...it, mediaIndex: nextIdx };
  });
}

export function collectRemovedMediaIndices(items: GalleryItem[], removedPaths: Set<string>): number[] {
  const out: number[] = [];
  for (const it of items) {
    if (!isGalleryMediaKind(it.kind) || !removedPaths.has(it.path)) continue;
    if (typeof it.mediaIndex === "number" && Number.isFinite(it.mediaIndex)) {
      out.push(it.mediaIndex);
    }
  }
  return out;
}
