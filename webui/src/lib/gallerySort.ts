export type GallerySortPart = {
  key: "name_base" | "name_suffix" | "name" | "name_lex" | "random" | "exif_month" | "mtime" | "ctime" | "exif" | "type";
  dir: "asc" | "desc";
};

export const SORT_KEYS: GallerySortPart["key"][] = [
  "name",
  "name_lex",
  "name_base",
  "name_suffix",
  "exif_month",
  "mtime",
  "ctime",
  "exif",
  "type",
  "random",
];

const DATE_DESC_KEYS = new Set<GallerySortPart["key"]>([
  "exif_month",
  "mtime",
  "ctime",
  "exif",
]);

export function parseGallerySortMode(mode: string): GallerySortPart[] {
  const rawParts = String(
    mode || "name:asc",
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
  if (parsed.length === 0) {
    parsed.push({ key: "name", dir: "asc" });
  }
  return parsed;
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
  if (key === "name_lex") return "view.sortNameLex";
  if (key === "random") return "view.sortRandom";
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
  return key === "name" || key === "name_lex" || key === "name_base" || key === "name_suffix";
}

export function primaryGallerySortKey(mode: string): GallerySortPart["key"] {
  return parseGallerySortMode(mode)[0]?.key ?? "name";
}
