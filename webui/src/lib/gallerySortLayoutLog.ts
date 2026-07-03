import { get } from "svelte/store";
import { galleryDebugLogEnabled, galleryDebugFilters, galleryDbg } from "./galleryDebugLog";

export type GalleryLayoutReportSection = {
  start: number;
  end: number;
  label: string;
  kind: string;
  key: string;
  count: number;
};

export type GalleryLayoutSectionSummary = {
  category: string;
  count: number;
  first: string;
  last: string;
  files?: string[];
  sample: string[] | null;
  sortType: string;
  start?: number;
  end?: number;
  kind?: string;
  key?: string;
  groupKey?: string;
  temporalBase?: string;
};

export type GalleryLayoutReport = {
  config: {
    gallery_sort_mode: string;
    gallery_group_by_folder: boolean;
    gallery_group_by_alpha: boolean;
    gallery_timeline_view: boolean;
    gallery_include_subfolders: boolean;
    layoutMode: string;
  };
  total: number;
  listed: number;
  truncated: boolean;
  sections: GalleryLayoutReportSection[];
  sectionSummaries: GalleryLayoutSectionSummary[];
};

/** Máximo de secciones por tipo en el log de depuración. */
const LOG_LARGE_SECTION_LIMIT = 5;
const LOG_SMALL_SECTION_LIMIT = 5;
const LARGE_MIN_COUNT = 5;

export type LogSectionSample = {
  large: GalleryLayoutSectionSummary[];
  small: GalleryLayoutSectionSummary[];
  totalLarge: number;
  totalSmall: number;
};

function temporalBaseOf(sec: GalleryLayoutSectionSummary): string {
  if (sec.temporalBase) return sec.temporalBase;
  const gk = sec.groupKey ?? "";
  const idx = gk.indexOf("_");
  return idx > 0 ? gk.slice(0, idx) : "unknown-date";
}

/** Fecha reciente primero; unknown-date al final. */
export function sortSummariesByRecentDate(
  summaries: GalleryLayoutSectionSummary[],
): GalleryLayoutSectionSummary[] {
  return [...summaries].sort((a, b) => {
    const da = temporalBaseOf(a);
    const db = temporalBaseOf(b);
    if (da === "unknown-date" && db !== "unknown-date") return 1;
    if (db === "unknown-date" && da !== "unknown-date") return -1;
    if (da !== db) return db.localeCompare(da);
    return (a.groupKey ?? a.category).localeCompare(b.groupKey ?? b.category);
  });
}

/** Elige 5 grandes y 5 pequeñas con fecha más reciente; dentro de cada una se listan todos los archivos. */
export function pickSectionSummariesForLog(
  summaries: GalleryLayoutSectionSummary[],
): LogSectionSample {
  const large = summaries.filter((s) => s.count >= LARGE_MIN_COUNT);
  const small = summaries.filter((s) => s.count < LARGE_MIN_COUNT);

  const pickedLarge = sortSummariesByRecentDate(large).slice(0, LOG_LARGE_SECTION_LIMIT);
  const pickedSmall = sortSummariesByRecentDate(small).slice(0, LOG_SMALL_SECTION_LIMIT);

  return {
    large: pickedLarge,
    small: pickedSmall,
    totalLarge: large.length,
    totalSmall: small.length,
  };
}

function sectionFiles(sec: GalleryLayoutSectionSummary): string[] {
  if (Array.isArray(sec.files) && sec.files.length > 0) return sec.files;
  if (sec.first && sec.last && sec.first !== sec.last) return [sec.first, sec.last];
  if (sec.first) return [sec.first];
  return [];
}

function formatSectionBlock(sec: GalleryLayoutSectionSummary): string[] {
  const date = temporalBaseOf(sec);
  const files = sectionFiles(sec);
  const lines = [
    `[${sec.category}] (${date}) -> Total: ${sec.count} archivos | Tipo Orden: ${sec.sortType ?? "Natural"}`,
  ];
  for (const name of files) {
    lines.push(`  · ${name}`);
  }
  return lines;
}

export function formatSortLayoutReportLines(report: GalleryLayoutReport): string[] {
  const c = report.config;
  const all = report.sectionSummaries ?? [];
  const sample = pickSectionSummariesForLog(all);

  const lines = [
    "── Ordenamiento actual ──",
    `sort: ${c.gallery_sort_mode}`,
    `layout: ${c.layoutMode} | carpeta: ${c.gallery_group_by_folder} | alpha: ${c.gallery_group_by_alpha} | timeline: ${c.gallery_timeline_view}`,
    `subcarpetas: ${c.gallery_include_subfolders} | total archivos: ${report.total} | secciones totales: ${all.length}`,
    "",
    `── Muestra depuración (${sample.large.length}/${sample.totalLarge} grandes ≥${LARGE_MIN_COUNT}, ${sample.small.length}/${sample.totalSmall} pequeñas <${LARGE_MIN_COUNT}; fecha reciente primero; todos los elementos por sección) ──`,
  ];

  if (all.length === 0) {
    lines.push("(sin secciones)");
    return lines;
  }

  if (sample.large.length > 0) {
    lines.push("", `▸ Secciones grandes (≥${LARGE_MIN_COUNT} archivos):`);
    for (const sec of sample.large) {
      lines.push(...formatSectionBlock(sec));
      lines.push("");
    }
  } else {
    lines.push("", `▸ Secciones grandes (≥${LARGE_MIN_COUNT} archivos): (ninguna en muestra)`);
  }

  if (sample.small.length > 0) {
    lines.push(`▸ Secciones pequeñas (<${LARGE_MIN_COUNT} archivos):`);
    for (const sec of sample.small) {
      lines.push(...formatSectionBlock(sec));
      lines.push("");
    }
  } else {
    lines.push("", `▸ Secciones pequeñas (<${LARGE_MIN_COUNT} archivos): (ninguna en muestra)`);
  }

  if (sample.totalLarge + sample.totalSmall > sample.large.length + sample.small.length) {
    lines.push(
      `(Omitidas ${Math.max(0, sample.totalLarge - sample.large.length)} secciones grandes y ${Math.max(0, sample.totalSmall - sample.small.length)} pequeñas adicionales.)`,
    );
  }

  if (lines[lines.length - 1] === "") lines.pop();
  return lines;
}

export async function logGallerySortLayout(
  fetchReport: () => Promise<GalleryLayoutReport>,
): Promise<void> {
  if (!get(galleryDebugLogEnabled)) return;
  if (get(galleryDebugFilters).sort === false) return;
  try {
    const report = await fetchReport();
    const all = report.sectionSummaries ?? [];
    const sample = pickSectionSummariesForLog(all);
    const shown = [...sample.large, ...sample.small];
    const fileCount = shown.reduce(
      (n, s) => n + (s.files?.length ?? s.count ?? 0),
      0,
    );
    galleryDbg("sort", formatSortLayoutReportLines(report).join("\n"), {
      config: report.config,
      total: report.total,
      sectionCount: all.length,
      shownLarge: sample.large.length,
      shownSmall: sample.small.length,
      totalLarge: sample.totalLarge,
      totalSmall: sample.totalSmall,
      fileLines: fileCount,
      truncated: report.truncated,
    });
  } catch (e: unknown) {
    galleryDbg("sort", "error leyendo ordenamiento", {
      error: e instanceof Error ? e.message : String(e),
    });
  }
}
