import { get, writable } from "svelte/store";
import { galleryState, type GalleryState } from "./galleryRuntime";

/** Scroll, carga incremental o hidratación HQ activos. */
export const galleryChromeBusy = writable(false);

function defaultPagerState(): GalleryState {
  return { page: 1, totalPages: 1, total: 0, selectedCount: 0 };
}

/** Snapshot del pager: no se actualiza mientras `galleryChromeBusy` es true. */
export const frozenPagerState = writable<GalleryState>(get(galleryState) ?? defaultPagerState());

let latestGalleryState = get(galleryState) ?? defaultPagerState();

galleryState.subscribe((next) => {
  latestGalleryState = next;
  if (!get(galleryChromeBusy)) {
    frozenPagerState.set(next);
  }
});

galleryChromeBusy.subscribe((busy) => {
  if (!busy) {
    frozenPagerState.set(latestGalleryState);
  }
});

/** Fuerza commit del estado congelado (p. ej. tras navegar de carpeta). */
export function commitChromePagerState() {
  latestGalleryState = get(galleryState) ?? latestGalleryState;
  frozenPagerState.set(latestGalleryState);
}
