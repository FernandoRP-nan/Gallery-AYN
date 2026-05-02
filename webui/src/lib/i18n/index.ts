import { es, type I18nTree } from "./es";

/** Idioma activo (futuro: selector o detección del sistema). */
let tree: I18nTree = es;

export function setLocale(next: I18nTree): void {
  tree = next;
}

type Path = keyof I18nTree | string;

/** Resuelve claves anidadas tipo "view.title" sobre el árbol i18n. */
export function t(path: Path): string {
  const parts = String(path).split(".");
  let cur: unknown = tree;
  for (const p of parts) {
    if (cur === null || typeof cur !== "object" || !(p in (cur as object))) {
      return String(path);
    }
    cur = (cur as Record<string, unknown>)[p];
  }
  return typeof cur === "string" ? cur : String(path);
}
