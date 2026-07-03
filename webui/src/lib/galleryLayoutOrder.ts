import type { GalleryItem } from "./api";
import type { GalleryLayoutSpan } from "./galleryFullVirtualLayout";
import { normalizePathForApi } from "./pathUtils";
import { isGalleryMediaKind } from "./galleryUtils";

function isSectionKind(kind: GalleryItem["kind"]): boolean {
  return kind === "section" || kind === "day_break";
}

function mediaIndexOf(it: GalleryItem): number | null {
  const idx = it.mediaIndex;
  return typeof idx === "number" && Number.isFinite(idx) ? idx : null;
}

function sectionMatchesSpan(sec: GalleryItem, span: GalleryLayoutSpan): boolean {
  if (span.kind === "folder") {
    const folder = normalizePathForApi(String(sec.sectionFolder ?? ""));
    const key = normalizePathForApi(String(span.key ?? ""));
    return Boolean(folder && key && folder === key);
  }
  if (span.kind === "timeline") {
    const key = String(span.key ?? span.label ?? "");
    return sec.path === `section:timeline:${key}` || sec.name === span.label;
  }
  if (span.kind === "alpha") {
    const key = String(span.key ?? span.label ?? "");
    return sec.path === `section:alpha:${key}` || sec.name === span.label;
  }
  const key = String(span.key ?? span.label ?? "");
  return sec.path === `section:${key}` || sec.name === span.label;
}

/** Reordena medios y encabezados según layoutSpans (agrupar / timeline / alfabético). */
export function reorderGalleryItemsByLayout(
  items: GalleryItem[],
  layoutMode: string,
  layoutSpans: GalleryLayoutSpan[] | undefined,
): GalleryItem[] {
  const mode = String(layoutMode ?? "flat");
  if (mode !== "grouped" && mode !== "timeline" && mode !== "alpha") {
    return items;
  }
  const spans = Array.isArray(layoutSpans) ? layoutSpans : [];
  if (spans.length === 0) return items;

  const prefix = items.filter((it) => it.kind === "folder" || it.kind === "folder_up");
  const sections = items.filter((it) => isSectionKind(it.kind));
  const media = items.filter((it) => isGalleryMediaKind(it.kind));

  const mediaByIndex = new Map<number, GalleryItem>();
  const mediaWithoutIndex: GalleryItem[] = [];
  for (const m of media) {
    const idx = mediaIndexOf(m);
    if (idx == null) mediaWithoutIndex.push(m);
    else mediaByIndex.set(idx, m);
  }

  const body: GalleryItem[] = [];
  const placedPaths = new Set<string>();

  for (const span of spans) {
    const hasMediaInRange = [...mediaByIndex.keys()].some((i) => i >= span.start && i < span.end);
    if (!hasMediaInRange) continue;

    const sec = sections.find((s) => sectionMatchesSpan(s, span));
    if (sec) body.push(sec);

    for (let i = span.start; i < span.end; i += 1) {
      const m = mediaByIndex.get(i);
      if (!m) continue;
      body.push(m);
      placedPaths.add(m.path);
    }
  }

  for (const m of mediaWithoutIndex) {
    if (!placedPaths.has(m.path)) body.push(m);
  }
  for (const m of media) {
    if (!placedPaths.has(m.path)) body.push(m);
  }

  return [...prefix, ...body];
}
