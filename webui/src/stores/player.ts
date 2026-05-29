import { writable } from 'svelte/store';
import type { GalleryItem } from '../lib/api';

export const previewZoomOpen = writable(false);
export const previewZoomPath = writable("");
export const previewZoomName = writable("");
export const previewZoomDataUrl = writable<string | null>(null);
export const previewZoomFileUrl = writable<string | null>(null);
export const previewZoomMediaType = writable<"image" | "video" | "svg">("image");

// Transformaciones
export const previewZoomScale = writable(1);
export const previewZoomMode = writable<"fit" | "fillWidth">("fit");
export const previewPanX = writable(0);
export const previewPanY = writable(0);

// UI del visor
export const previewZoomCarouselVisible = writable(true);
export const zoomHudVisible = writable(false);
export const previewZoomDestMode = writable(false);

// Navegación
export const zoomNavItems = writable<GalleryItem[]>([]);

// Edición
export const zoomEditMode = writable(false);
export const zoomCropMode = writable(false);
