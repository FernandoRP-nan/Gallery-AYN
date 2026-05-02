import { writable } from 'svelte/store';

// Selección múltiple (modo selección)
export const previewSelectedPaths = writable<string[]>([]);
export const previewSelectionMode = writable<boolean>(false);

// Zoom/Fullscreen y recorte
export const previewZoomOpen = writable<boolean>(false);
export const previewZoomPath = writable<string>("");
export const previewZoomName = writable<string>("");
export const previewZoomDataUrl = writable<string | null>(null);
export const previewZoomScale = writable<number>(1);
export const previewZoomMode = writable<"fit" | "fillWidth">("fit");
export const previewZoomMediaType = writable<"image" | "video" | "svg">("image");
export const previewZoomFileUrl = writable<string | null>(null);

export const zoomEditMode = writable<boolean>(false);
export const zoomCropMode = writable<boolean>(false);

// Colas de trabajo para mover/borrar
export const zoomMoveQueue = writable<Array<{ srcPath: string; destPath: string }>>([]);
export const galleryMoveQueue = writable<Array<{ srcPaths: string[]; destPath: string }>>([]);
export const galleryDeleteQueue = writable<Array<{ paths: string[] }>>([]);
