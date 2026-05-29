import { writable, derived } from 'svelte/store';

// Selección Galería Principal
export const selectedPaths = writable<string[]>([]);
export const isSelecting = derived(selectedPaths, $s => $s.length > 0);

// Selección Previsualización Carpeta
export const previewSelectedPaths = writable<string[]>([]);
export const previewSelectionMode = writable(false);

// Estado de selección por rango (Draft)
export const galleryRangeSelecting = writable(false);
export const galleryRangeAnchorPath = writable<string | null>(null);

export function clearSelection() {
    selectedPaths.set([]);
}

export function clearPreviewSelection() {
    previewSelectedPaths.set([]);
}
