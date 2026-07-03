export type GallerySortPart = {
  key: "name_base" | "name_suffix" | "name" | "exif_month" | "mtime" | "ctime" | "exif" | "type";
  dir: "asc" | "desc";
};

const SORT_KEYS: GallerySortPart["key"][] = [
  "exif_month",
  "name_base",
  "name_suffix",
  "name",
  "mtime",
  "ctime",
  "exif",
  "type",
];

const DATE_DESC_KEYS = new Set<GallerySortPart["key"]>([
  "exif_month",
  "mtime",
  "ctime",
  "exif",
]);

export function parseGallerySortMode(mode: string): GallerySortPart[] {
  const rawParts = String(
    mode || "exif_month:desc,name_base:asc,name_suffix:asc,name:asc,mtime:desc,type:asc",
  )
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const parsed: GallerySortPart[] = [];
  for (const raw of rawParts) {
    const sp = raw.split(":");
    const key = sp[0]?.trim() as GallerySortPart["key"];
    if (!SORT_KEYS.includes(key)) continue;
    parsed.push({ key, dir: sp[1]?.trim() === "desc" ? "desc" : "asc" });
  }
  for (const key of SORT_KEYS) {
    if (!parsed.some((p) => p.key === key)) {
      parsed.push({ key, dir: DATE_DESC_KEYS.has(key) ? "desc" : "asc" });
    }
  }
  return parsed.filter((p) => SORT_KEYS.includes(p.key));
}

export function formatGallerySortMode(parts: GallerySortPart[]): string {
  return parts.map((p) => `${p.key}:${p.dir}`).join(",");
}

export function gallerySortModesEqual(a: string, b: string): boolean {
  return formatGallerySortMode(parseGallerySortMode(a)) === formatGallerySortMode(parseGallerySortMode(b));
}

export function sortPartLabelKey(key: GallerySortPart["key"]): string {
  if (key === "name_base") return "view.sortNameBase";
  if (key === "name_suffix") return "view.sortNameSuffix";
  if (key === "name") return "view.sortName";
  if (key === "exif_month") return "view.sortExifMonth";
  if (key === "mtime") return "view.sortDate";
  if (key === "ctime") return "view.sortCreated";
  if (key === "exif") return "view.sortExif";
  return "view.sortType";
}

/** Criterios de fecha válidos como primario en vista línea de tiempo. */
export function isTimelineDateSortKey(key: string): boolean {
  return key === "mtime" || key === "ctime" || key === "exif" || key === "exif_month";
}

export function isNameClusterPrimaryKey(key: string): boolean {
  return key === "name" || key === "name_base" || key === "name_suffix";
}

export function primaryGallerySortKey(mode: string): GallerySortPart["key"] {
  return parseGallerySortMode(mode)[0]?.key ?? "name_base";
}
