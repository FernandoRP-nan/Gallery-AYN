import type { GalleryLayoutMode, GalleryLayoutSpan } from "./galleryFullVirtualLayout";

/** Spans para layout virtual: secciones visibles o solo rail de fechas en modo plano. */
export function resolveVirtualLayoutSpans(
  layoutMode: GalleryLayoutMode,
  layoutSpans: GalleryLayoutSpan[],
): { spans: GalleryLayoutSpan[]; railOnlyTimeline: boolean } {
  const railOnlyTimeline =
    layoutMode === "flat" &&
    layoutSpans.length > 0 &&
    layoutSpans.every((s) => s.kind === "timeline");
  const spans =
    layoutSpans.length > 0 && (layoutMode !== "flat" || railOnlyTimeline)
      ? layoutSpans
      : [];
  return { spans, railOnlyTimeline };
}
