export type GallerySortPart = {
  key: "name" | "mtime" | "type";
  dir: "asc" | "desc";
};

const SORT_KEYS: GallerySortPart["key"][] = ["name", "mtime", "type"];

export function parseGallerySortMode(mode: string): GallerySortPart[] {
  const rawParts = String(mode || "name:asc,mtime:desc,type:asc")
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
      parsed.push({ key, dir: key === "mtime" ? "desc" : "asc" });
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
  if (key === "name") return "view.sortName";
  if (key === "mtime") return "view.sortDate";
  return "view.sortType";
}
