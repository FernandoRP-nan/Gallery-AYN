import type { GalleryItem } from "./api";
import { hasGalleryThumbHq } from "./galleryThumbHqCache";

export function isGalleryThumbMediaItem(it: GalleryItem): boolean {
  return it.kind === "image" || it.kind === "video";
}

export function listGalleryItemsNeedingHq(items: GalleryItem[]): GalleryItem[] {
  return items.filter((x) => isGalleryThumbMediaItem(x) && !hasGalleryThumbHq(x.path));
}
