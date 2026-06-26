import type { GalleryScrollMarker } from "./galleryFullVirtualLayout";
import { formatFolderRailLabel, formatPathTail } from "./galleryUtils";

export type GalleryScrollRailLabel = {
  top: number;
  label: string;
  startIndex: number;
  marker: GalleryScrollMarker;
};

const MONTH_SHORT_ES: Record<string, string> = {
  enero: "Ene",
  febrero: "Feb",
  marzo: "Mar",
  abril: "Abr",
  mayo: "May",
  junio: "Jun",
  julio: "Jul",
  agosto: "Ago",
  septiembre: "Sep",
  octubre: "Oct",
  noviembre: "Nov",
  diciembre: "Dic",
};

/** Separación mínima entre etiquetas en píxeles de pantalla (rail visible). */
const RAIL_LABEL_MIN_GAP_PX = 18;

/** Marca activa para una coordenada Y del contenido virtual. */
export function scrollMarkerAtContentY(
  markers: GalleryScrollMarker[],
  contentY: number,
): GalleryScrollMarker | null {
  if (markers.length === 0) return null;
  let active = markers[0];
  for (const m of markers) {
    if (m.top <= contentY) active = m;
    else break;
  }
  return active;
}

function parseTimelineLabel(label: string): { month: string; year: string } | null {
  const text = String(label ?? "").trim();
  const m = text.match(/^(\S+)\s+(\d{4})$/);
  if (!m) return null;
  return { month: m[1], year: m[2] };
}

/** Formato compacto fijo para el rail: Jun'24 */
function formatMonthRailLabel(label: string): string {
  const parsed = parseTimelineLabel(label);
  if (!parsed) return String(label ?? "").trim();
  const short =
    MONTH_SHORT_ES[parsed.month.toLowerCase()] ?? parsed.month.slice(0, 3);
  return `${short}'${parsed.year.slice(2)}`;
}

function extractYear(label: string): string {
  return parseTimelineLabel(label)?.year ?? String(label ?? "").match(/\d{4}/)?.[0] ?? String(label ?? "");
}

function markerToLabel(m: GalleryScrollMarker, text: string): GalleryScrollRailLabel {
  return { top: m.top, label: text, startIndex: m.startIndex, marker: m };
}

/** Filtra etiquetas que quedarían demasiado juntas en el rail visible. */
export function decimateByRailScreenGap(
  labels: GalleryScrollRailLabel[],
  totalHeight: number,
  railHeightPx: number,
  minGapPx = RAIL_LABEL_MIN_GAP_PX,
): GalleryScrollRailLabel[] {
  if (labels.length <= 1 || totalHeight <= 0 || railHeightPx <= 0) return labels;

  const out: GalleryScrollRailLabel[] = [labels[0]];
  for (let i = 1; i < labels.length; i += 1) {
    const prev = out[out.length - 1];
    const screenGap = ((labels[i].top - prev.top) / totalHeight) * railHeightPx;
    if (screenGap >= minGapPx) out.push(labels[i]);
  }

  const last = labels[labels.length - 1];
  const tail = out[out.length - 1];
  if (tail !== last) {
    const screenGap = ((last.top - tail.top) / totalHeight) * railHeightPx;
    if (screenGap >= minGapPx * 0.85) out.push(last);
  }
  return out;
}

function buildTimelineMonthLabels(markers: GalleryScrollMarker[]): GalleryScrollRailLabel[] {
  return markers.map((m) => markerToLabel(m, formatMonthRailLabel(m.label)));
}

function buildTimelineYearLabels(markers: GalleryScrollMarker[]): GalleryScrollRailLabel[] {
  const byYear = new Map<string, GalleryScrollMarker>();
  for (const m of markers) {
    const year = extractYear(m.label);
    if (!byYear.has(year)) byYear.set(year, m);
  }
  return [...byYear.values()].map((m) => markerToLabel(m, extractYear(m.label)));
}

/** Etiquetas del rail según espacio en pantalla: meses o años, sin solaparse. */
export function buildScrollRailLabels(
  markers: GalleryScrollMarker[],
  cellSize: number,
  totalHeight: number,
  railHeightPx: number,
): GalleryScrollRailLabel[] {
  if (markers.length === 0 || totalHeight <= 0 || railHeightPx <= 0) return [];

  const kind = markers[0]?.kind ?? "flat";
  const maxLabels = Math.max(3, Math.floor(railHeightPx / RAIL_LABEL_MIN_GAP_PX));
  const preferMonths = cellSize >= 80 && kind === "timeline";

  if (kind === "timeline") {
    let labels = preferMonths
      ? buildTimelineMonthLabels(markers)
      : buildTimelineYearLabels(markers);
    labels = decimateByRailScreenGap(labels, totalHeight, railHeightPx);

    if (labels.length > maxLabels && preferMonths) {
      labels = decimateByRailScreenGap(
        buildTimelineYearLabels(markers),
        totalHeight,
        railHeightPx,
      );
    }
    if (labels.length > maxLabels) {
      labels = decimateByRailScreenGap(labels, totalHeight, railHeightPx, RAIL_LABEL_MIN_GAP_PX * 1.35);
    }
    return labels;
  }

  if (kind === "folder") {
    const labels = markers.map((m) => markerToLabel(m, formatFolderRailLabel(m.label)));
    return decimateByRailScreenGap(labels, totalHeight, railHeightPx);
  }

  if (kind === "alpha") {
    const labels = markers.map((m) =>
      markerToLabel(m, m.label.length > 10 ? formatPathTail(m.label, 10) : m.label),
    );
    return decimateByRailScreenGap(labels, totalHeight, railHeightPx);
  }

  const generic = markers.map((m) =>
    markerToLabel(m, m.label.length > 10 ? formatPathTail(m.label, 10) : m.label),
  );
  return decimateByRailScreenGap(generic, totalHeight, railHeightPx);
}

export function contentYFromGutterRatio(ratio: number, totalHeight: number): number {
  const r = Math.min(1, Math.max(0, ratio));
  return r * Math.max(0, totalHeight);
}

export function gutterRatioFromClientY(
  clientY: number,
  gutterTop: number,
  gutterHeight: number,
): number {
  if (gutterHeight <= 0) return 0;
  return (clientY - gutterTop) / gutterHeight;
}
