import type { GalleryLayoutMode, GalleryLayoutSpan } from "./galleryFullVirtualLayout";

/** Ruta sintética de encabezado de sección en layout virtual (debe coincidir con el backend). */
export function virtualSectionPath(span: GalleryLayoutSpan): string {
  if (span.kind === "timeline") {
    return `section:timeline:${span.key ?? span.label}`;
  }
  if (span.kind === "alpha") {
    return `section:alpha:${span.key ?? span.label}`;
  }
  return `section:${span.key ?? span.start}`;
}

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
