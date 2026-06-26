import type { GalleryItem } from "./api";
import { mergeItemsKeepingBestThumb } from "./galleryUtils";

const visitedByPath = new Map<string, GalleryItem>();

/** Guarda ítems ya mostrados para reutilizar miniaturas al volver a una fecha. */
export function stashGalleryItemsInVisitedCache(items: GalleryItem[]) {
  for (const it of items) {
    if (it.kind === "folder" || it.kind === "folder_up" || it.kind === "image" || it.kind === "video") {
      visitedByPath.set(it.path, it);
    }
  }
}

export function clearVisitedGalleryCache() {
  visitedByPath.clear();
}

/** Fusiona respuesta del API con ítems vistos antes (misma sesión / carpeta). */
export function enrichItemsFromVisitedCache(
  prevItems: GalleryItem[],
  nextItems: GalleryItem[],
): GalleryItem[] {
  const prevByPath = new Map(prevItems.map((x) => [x.path, x] as const));
  return nextItems.map((it) => {
    const seed = prevByPath.get(it.path) ?? visitedByPath.get(it.path);
    if (!seed) return it;
    return mergeItemsKeepingBestThumb([seed], [it], { preserveSelection: true })[0] ?? it;
  });
}
