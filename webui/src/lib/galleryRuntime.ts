import { get, writable } from "svelte/store";
import type { GalleryItem } from "./api";
import {
  countSelectedGalleryItems,
  mergeItemsKeepingBestThumb,
  isGalleryMediaKind,
  isGallerySelectableKind,
  shiftGalleryMediaIndicesAfterRemoval,
  collectRemovedMediaIndices,
} from "./galleryUtils";
import { getGalleryPerfConfig } from "./galleryPerfConfig";
import { clearMasonryHeightCache } from "./galleryMasonryHeightCache";
import {
  enrichItemsFromVisitedCache,
  stashGalleryItemsInVisitedCache,
} from "./galleryVisitedCache";
import {
  removeGalleryThumbHq,
  seedGalleryThumbHqFromItems,
  stripHqFromGalleryItems,
} from "./galleryThumbHqCache";
import { galleryDbg, logGallerySelectionDelta } from "./galleryDebugLog";
import { reorderGalleryItemsByLayout } from "./galleryLayoutOrder";
import type { GalleryLayoutSpan } from "./galleryFullVirtualLayout";

export type GalleryMutationResponse = {
  state?: GalleryState;
  items?: GalleryItem[];
  prependItems?: GalleryItem[];
  appendItems?: GalleryItem[];
  removedPaths?: string[];
  delta?: boolean;
  replaceWindow?: boolean;
  windowExpandIncremental?: boolean;
  windowStart?: number;
  windowEnd?: number;
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

function layoutReorderFromState(state: GalleryState | undefined, items: GalleryItem[]): GalleryItem[] {
  if (!state) return items;
  const spans = Array.isArray(state.layoutSpans) ? (state.layoutSpans as GalleryLayoutSpan[]) : [];
  return reorderGalleryItemsByLayout(items, String(state.layoutMode ?? "flat"), spans);
}

function mergeGalleryItemsByPath(...groups: GalleryItem[][]): GalleryItem[] {
  const byPath = new Map<string, GalleryItem>();
  for (const group of groups) {
    for (const it of group) byPath.set(it.path, it);
  }
  return [...byPath.values()];
}

export function setGalleryPayload(state: GalleryState, nextItems: GalleryItem[]) {
  const prevItems = getGalleryItems();
  seedGalleryThumbHqFromItems(nextItems);
  const stripped = stripHqFromGalleryItems(nextItems);
  galleryItems.set(stripped);
  galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(stripped) });
  logGallerySelectionDelta("payload:full_replace", prevItems, stripped, {
    total: state.total ?? 0,
    folder: state.folder ?? "",
  });
}

export function setGalleryState(state: GalleryState) {
  galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(getGalleryItems()) });
}

/** Fusiona metadatos del API sin pisar el conteo de selección local. */
export function setGalleryStateFromApi(state: GalleryState) {
  galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(getGalleryItems()) });
}

export function setGalleryItems(nextItems: GalleryItem[]) {
  galleryItems.set(nextItems);
}

export function updateGalleryItems(mutator: (items: GalleryItem[]) => GalleryItem[]) {
  galleryItems.update(mutator);
}

export function mergeGalleryItemsFromApi(
  nextItems: GalleryItem[],
  state?: GalleryState,
  opts?: { preserveSelection?: boolean },
) {
  seedGalleryThumbHqFromItems(nextItems);
  const prevItems = getGalleryItems();
  const merged = mergeItemsKeepingBestThumb(prevItems, nextItems, opts);
  galleryItems.set(stripHqFromGalleryItems(merged));
  logGallerySelectionDelta(
    opts?.preserveSelection === false ? "mergeApi:replace_selection" : "mergeApi:preserve",
    prevItems,
    merged,
    { preserveSelection: opts?.preserveSelection !== false },
  );
  if (state) {
    galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(merged) });
  } else {
    syncSelectedCountFromItems();
  }
}

/** Añade ítems al final sin descartar la ventana ya cargada (scroll hacia abajo). */
export function appendGalleryItemsFromApi(
  nextItems: GalleryItem[],
  state?: GalleryState,
  opts?: { preserveSelection?: boolean },
) {
  if (!Array.isArray(nextItems) || nextItems.length === 0) {
    if (state) setGalleryStateFromApi(state);
    return;
  }
  const prevItems = getGalleryItems();
  const prevPaths = new Set(prevItems.map((x) => x.path));
  seedGalleryThumbHqFromItems(nextItems);
  const mergedBatch = mergeItemsKeepingBestThumb(prevItems, nextItems, opts);
  const appended = mergedBatch.filter((it) => !prevPaths.has(it.path));
  if (appended.length === 0) {
    if (state) setGalleryStateFromApi(state);
    return;
  }
  const next = stripHqFromGalleryItems([...prevItems, ...appended]);
  const folders = next.filter((it) => it.kind === "folder" || it.kind === "folder_up");
  const body = layoutReorderFromState(
    state,
    next.filter((it) => it.kind !== "folder" && it.kind !== "folder_up"),
  );
  const finalItems = [...folders, ...body];
  galleryItems.set(finalItems);
  logGallerySelectionDelta("window:append", prevItems, finalItems, { appendCount: appended.length });
  if (state) {
    galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(finalItems) });
    galleryDbg("window", "ventana ampliada (append)", {
      windowStart: state.windowStart ?? 0,
      endIndex: state.endIndex ?? 0,
      appendCount: appended.length,
      itemCount: finalItems.length,
    });
  } else {
    syncSelectedCountFromItems();
  }
  if (state) applySlidingWindowTrim(state);
}

/** Recorta ítems antiguos fuera de la ventana deslizante (RAM estable al scroll largo). */
export function applySlidingWindowTrim(state?: GalleryState): number {
  const st = state ?? getGalleryState();
  const end = Number(st.endIndex ?? 0);
  let ws = Number(st.windowStart ?? 0);
  const perf = getGalleryPerfConfig();
  if (!perf.slidingWindowEnabled || end <= ws) return 0;
  if (end - ws <= perf.slidingWindowMaxItems) return 0;
  ws = Math.max(0, end - perf.slidingWindowMaxItems);

  const prev = getGalleryItems();
  const removedPaths: string[] = [];
  const kept = prev.filter((it) => {
    if (it.kind === "folder" || it.kind === "folder_up") return true;
    if (it.kind === "section" || it.kind === "day_break") return true;
    if (!isGalleryMediaKind(it.kind)) return true;
    const idx = it.mediaIndex;
    if (typeof idx !== "number" || !Number.isFinite(idx)) return true;
    if (idx < ws) {
      removedPaths.push(it.path);
      return false;
    }
    return true;
  });

  const prevWs = Number(st.windowStart ?? 0);
  if (removedPaths.length === 0 && ws === prevWs) return 0;

  if (removedPaths.length > 0) removeGalleryThumbHq(new Set(removedPaths));
  const trimmed = stripHqFromGalleryItems(kept);
  const folders = trimmed.filter((it) => it.kind === "folder" || it.kind === "folder_up");
  const body = layoutReorderFromState(
    st,
    trimmed.filter((it) => it.kind !== "folder" && it.kind !== "folder_up"),
  );
  const next = [...folders, ...body];
  galleryItems.set(next);
  const selectedRemoved = removedPaths.filter((p) =>
    prev.some((x) => x.path === p && isGallerySelectableKind(x.kind) && x.selected),
  );
  galleryState.set({
    ...st,
    windowStart: ws,
    selectedCount: countSelectedGalleryItems(next),
  });
  galleryDbg("window", "ventana recortada (sliding)", {
    windowStart: ws,
    endIndex: end,
    removed: removedPaths.length,
    itemCount: next.length,
    selectedRemoved: selectedRemoved.length,
  });
  logGallerySelectionDelta("window:sliding_trim_start", prev, next, {
    selectedRemoved,
    removedFromWindow: removedPaths.length,
  });
  return removedPaths.length;
}

/** Recorta ítems posteriores al prepend hacia atrás (ventana deslizante). */
export function applySlidingWindowTrimFromEnd(state?: GalleryState): number {
  const st = state ?? getGalleryState();
  let end = Number(st.endIndex ?? 0);
  const ws = Number(st.windowStart ?? 0);
  const perf = getGalleryPerfConfig();
  if (!perf.slidingWindowEnabled || end <= ws) return 0;
  if (end - ws <= perf.slidingWindowMaxItems) return 0;
  end = ws + perf.slidingWindowMaxItems;

  const prev = getGalleryItems();
  const removedPaths: string[] = [];
  const kept = prev.filter((it) => {
    if (it.kind === "folder" || it.kind === "folder_up") return true;
    if (it.kind === "section" || it.kind === "day_break") return true;
    if (!isGalleryMediaKind(it.kind)) return true;
    const idx = it.mediaIndex;
    if (typeof idx !== "number" || !Number.isFinite(idx)) return true;
    if (idx >= end) {
      removedPaths.push(it.path);
      return false;
    }
    return true;
  });

  const prevEnd = Number(st.endIndex ?? 0);
  if (removedPaths.length === 0 && end === prevEnd) return 0;

  if (removedPaths.length > 0) removeGalleryThumbHq(new Set(removedPaths));
  const trimmed = stripHqFromGalleryItems(kept);
  const folders = trimmed.filter((it) => it.kind === "folder" || it.kind === "folder_up");
  const body = layoutReorderFromState(
    st,
    trimmed.filter((it) => it.kind !== "folder" && it.kind !== "folder_up"),
  );
  const next = [...folders, ...body];
  galleryItems.set(next);
  const selectedRemoved = removedPaths.filter((p) =>
    prev.some((x) => x.path === p && isGallerySelectableKind(x.kind) && x.selected),
  );
  galleryState.set({
    ...st,
    endIndex: end,
    selectedCount: countSelectedGalleryItems(next),
  });
  galleryDbg("window", "ventana recortada (sliding end)", {
    windowStart: ws,
    endIndex: end,
    removed: removedPaths.length,
    itemCount: next.length,
    selectedRemoved: selectedRemoved.length,
  });
  logGallerySelectionDelta("window:sliding_trim_end", prev, next, {
    selectedRemoved,
    removedFromWindow: removedPaths.length,
  });
  return removedPaths.length;
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
  const prevItems = getGalleryItems();
  const removedMediaIndices = collectRemovedMediaIndices(prevItems, removed);
  removeGalleryThumbHq(removed);
  updateGalleryItems((items) => {
    let next = pruneOrphanGallerySections(items.filter((x) => !removed.has(x.path)));
    if (getGalleryPerfConfig().compactIndicesAfterMove) {
      next = shiftGalleryMediaIndicesAfterRemoval(next, removedMediaIndices);
    }
    return next;
  });
  if (getGalleryPerfConfig().compactIndicesAfterMove) clearMasonryHeightCache();
  const nextItems = getGalleryItems();
  galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(nextItems) });
  logGallerySelectionDelta("delta:remove_paths", prevItems, nextItems, {
    removedCount: removed.size,
    compactIndices: getGalleryPerfConfig().compactIndicesAfterMove,
  });
}

export function applyGalleryWindowItems(windowItems: GalleryItem[], state?: GalleryState) {
  if (!Array.isArray(windowItems) || windowItems.length === 0) {
    if (state) setGalleryStateFromApi(state);
    return;
  }
  const prevItems = getGalleryItems();
  stashGalleryItemsInVisitedCache(prevItems);
  const prefix = prevItems.filter(
    (it) => it.kind === "folder" || it.kind === "folder_up"
  );
  seedGalleryThumbHqFromItems(windowItems);
  const windowMerged = enrichItemsFromVisitedCache(prevItems, windowItems);
  const body = layoutReorderFromState(state, windowMerged);
  const next = stripHqFromGalleryItems([...prefix, ...body]);
  galleryItems.set(next);
  logGallerySelectionDelta("window:replace", prevItems, next, {
    windowStart: state?.windowStart ?? 0,
    endIndex: state?.endIndex ?? 0,
    itemCount: windowItems.length,
  });
  if (state) {
    galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(next) });
    galleryDbg("window", "ventana reemplazada", {
      windowStart: state.windowStart ?? 0,
      endIndex: state.endIndex ?? 0,
      total: state.total ?? 0,
      itemCount: windowItems.length,
    });
  } else {
    syncSelectedCountFromItems();
  }
}

/** Amplía la ventana tras salto sin reemplazar el núcleo ya renderizado. */
export function applyGalleryWindowExpand(
  prependItems: GalleryItem[],
  appendItems: GalleryItem[],
  state?: GalleryState,
) {
  const prep = Array.isArray(prependItems) ? prependItems : [];
  const app = Array.isArray(appendItems) ? appendItems : [];
  if (prep.length === 0 && app.length === 0) {
    if (state) setGalleryStateFromApi(state);
    return;
  }
  const prevItems = getGalleryItems();
  stashGalleryItemsInVisitedCache(prevItems);
  const prefix = prevItems.filter(
    (it) => it.kind === "folder" || it.kind === "folder_up",
  );
  const body = prevItems.filter((it) => it.kind !== "folder" && it.kind !== "folder_up");
  seedGalleryThumbHqFromItems([...prep, ...app]);
  const prepMerged = enrichItemsFromVisitedCache(prevItems, prep);
  const appMerged = enrichItemsFromVisitedCache(prevItems, app);
  const merged = mergeGalleryItemsByPath(body, prepMerged, appMerged);
  const reordered = layoutReorderFromState(state, merged);
  const next = stripHqFromGalleryItems([...prefix, ...reordered]);
  galleryItems.set(next);
  logGallerySelectionDelta("window:expand", prevItems, next, {
    prependCount: prep.length,
    appendCount: app.length,
  });
  if (state) {
    galleryState.set({ ...state, selectedCount: countSelectedGalleryItems(next) });
    galleryDbg("window", "ventana ampliada (incremental)", {
      windowStart: state.windowStart ?? 0,
      endIndex: state.endIndex ?? 0,
      total: state.total ?? 0,
      prependCount: prep.length,
      appendCount: app.length,
    });
  } else {
    syncSelectedCountFromItems();
  }
  if (state) {
    if (prep.length > 0 && app.length === 0) {
      applySlidingWindowTrimFromEnd(state);
    } else if (app.length > 0 && prep.length === 0) {
      applySlidingWindowTrim(state);
    } else {
      applySlidingWindowTrim(state);
      applySlidingWindowTrimFromEnd(state);
    }
  }
}

export function applyGalleryMutationResponse(out: GalleryMutationResponse) {
  if (out?.delta && Array.isArray(out.removedPaths) && !out.items) {
    if (out.state) applyGalleryRemovePathsDelta(out.state, out.removedPaths);
    return;
  }
  if (Array.isArray(out?.items)) {
    mergeGalleryItemsFromApi(out.items, out.state, { preserveSelection: true });
    return;
  }
  if (out?.state) setGalleryStateFromApi(out.state);
}

export function syncSelectedCountFromItems() {
  const n = countSelectedGalleryItems(getGalleryItems());
  galleryState.update((s) => ({ ...s, selectedCount: n }));
}

export function patchGallerySelection(
  mutator: (items: GalleryItem[]) => GalleryItem[],
  source = "selection:patch",
  detail?: Record<string, unknown>,
) {
  const prevItems = getGalleryItems();
  galleryItems.update(mutator);
  const nextItems = getGalleryItems();
  syncSelectedCountFromItems();
  logGallerySelectionDelta(source, prevItems, nextItems, detail);
}
