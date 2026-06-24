import { get, writable } from "svelte/store";
import type { GalleryItem } from "./api";
import { countSelectedMedia, mergeItemsKeepingBestThumb } from "./galleryUtils";

export type GalleryMutationResponse = {
  state?: GalleryState;
  items?: GalleryItem[];
  removedPaths?: string[];
  delta?: boolean;
};

export type GalleryState = {
  page: number;
  totalPages: number;
  total: number;
  totalImages?: number;
  totalVideos?: number;
  selectedCount: number;
  endIndex?: number;
  totalElements?: number;
  totalBytes?: number;
  subfoldersCount?: number;
  folder?: string;
  [key: string]: unknown;
};

const defaultState = (): GalleryState => ({
  page: 1,
  totalPages: 1,
  total: 0,
  selectedCount: 0,
});

/** Ítems de la galería: solo los suscriptores de la rejilla deben re-renderizar al cambiar. */
export const galleryItems = writable<GalleryItem[]>([]);

/** Metadatos de paginación/conteos: el pager de App suscribe solo a esto. */
export const galleryState = writable<GalleryState>(defaultState());

export function getGalleryItems(): GalleryItem[] {
  return get(galleryItems);
}

export function getGalleryState(): GalleryState {
  return get(galleryState);
}

export function setGalleryPayload(state: GalleryState, nextItems: GalleryItem[]) {
  galleryItems.set(nextItems);
  galleryState.set({ ...state, selectedCount: countSelectedMedia(nextItems) });
}

export function setGalleryState(state: GalleryState) {
  galleryState.set({ ...state, selectedCount: countSelectedMedia(getGalleryItems()) });
}

/** Fusiona metadatos del API sin pisar el conteo de selección local. */
export function setGalleryStateFromApi(state: GalleryState) {
  galleryState.set({ ...state, selectedCount: countSelectedMedia(getGalleryItems()) });
}

export function setGalleryItems(nextItems: GalleryItem[]) {
  galleryItems.set(nextItems);
}

export function updateGalleryItems(mutator: (items: GalleryItem[]) => GalleryItem[]) {
  galleryItems.update(mutator);
}

export function mergeGalleryItemsFromApi(nextItems: GalleryItem[], state?: GalleryState) {
  const merged = mergeItemsKeepingBestThumb(getGalleryItems(), nextItems);
  galleryItems.set(merged);
  if (state) {
    galleryState.set({ ...state, selectedCount: countSelectedMedia(merged) });
  } else {
    syncSelectedCountFromItems();
  }
}

/** Elimina rutas del store local y sincroniza metadatos (respuesta delta del API). */
function pruneOrphanGallerySections(items: GalleryItem[]): GalleryItem[] {
  const out: GalleryItem[] = [];
  let pendingSection: GalleryItem | null = null;
  for (const it of items) {
    if (it.kind === "section" || it.kind === "day_break") {
      pendingSection = it;
      continue;
    }
    if (pendingSection) {
      out.push(pendingSection);
      pendingSection = null;
    }
    out.push(it);
  }
  return out;
}

export function applyGalleryRemovePathsDelta(state: GalleryState, removedPaths: string[]) {
  const removed = new Set(removedPaths.filter(Boolean));
  if (removed.size === 0) {
    setGalleryStateFromApi(state);
    return;
  }
  updateGalleryItems((items) =>
    pruneOrphanGallerySections(items.filter((x) => !removed.has(x.path)))
  );
  galleryState.set({ ...state, selectedCount: countSelectedMedia(getGalleryItems()) });
}

export function applyGalleryMutationResponse(out: GalleryMutationResponse) {
  if (out?.delta && Array.isArray(out.removedPaths) && !out.items) {
    if (out.state) applyGalleryRemovePathsDelta(out.state, out.removedPaths);
    return;
  }
  if (Array.isArray(out?.items)) {
    mergeGalleryItemsFromApi(out.items, out.state);
    return;
  }
  if (out?.state) setGalleryStateFromApi(out.state);
}

export function syncSelectedCountFromItems() {
  const n = countSelectedMedia(getGalleryItems());
  galleryState.update((s) => ({ ...s, selectedCount: n }));
}

export function patchGallerySelection(mutator: (items: GalleryItem[]) => GalleryItem[]) {
  galleryItems.update(mutator);
  syncSelectedCountFromItems();
}
