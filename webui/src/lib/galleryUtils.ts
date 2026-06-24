import type { GalleryItem } from "./api";
import {
  preserveItemThumbInCache,
  hasGalleryThumbHq,
  getGalleryThumbHq,
} from "./galleryThumbHqCache";

export function isGalleryMediaKind(kind: GalleryItem["kind"]): boolean {
  return kind === "image" || kind === "video";
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

export function mergeItemsKeepingBestThumb(prevItems: GalleryItem[], nextItems: GalleryItem[]): GalleryItem[] {
  const prevByPath = new Map(prevItems.map((x) => [x.path, x] as const));
  return nextItems.map((it) => {
    const prev = prevByPath.get(it.path);
    if (!prev) return it;

    if (!isGalleryMediaKind(it.kind) || !isGalleryMediaKind(prev.kind)) {
      if (prev.kind === it.kind && prev.name === it.name && prev.path === it.path) {
        return prev;
      }
      return it;
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
        thumbLq;
      thumbUrl = thumbLq;
      thumbQ = thumbLq ? ("lq" as const) : undefined;
    }

    const hasChanges =
      Boolean(prev.selected) !== Boolean(it.selected) ||
      prev.thumbDataUrl !== thumbUrl ||
      prev.thumbQuality !== thumbQ ||
      prev.thumbLqDataUrl !== thumbLq ||
      prev.name !== it.name ||
      prev.kind !== it.kind;

    if (!hasChanges) return prev;

    return {
      ...prev,
      selected: it.selected,
      thumbDataUrl: thumbUrl,
      thumbLqDataUrl: thumbLq,
      thumbQuality: thumbQ,
      name: it.name,
      kind: it.kind,
    };
  });
}

const TIMELINE_DAY_MIN_PX = 130;

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
        const dayNum = iso.slice(8, 10);
        out.push({
          kind: "day_break",
          name: dayNum,
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
