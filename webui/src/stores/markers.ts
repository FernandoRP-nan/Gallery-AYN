import { writable } from 'svelte/store';

// Carpetas fijadas (Marcadores)
export const pinnedFolders = writable<Array<{ label: string; path: string }>>([]);

// Carpetas recientes
export const recentUnpinnedFolders = writable<Array<{ label: string; path: string }>>([]);

// Historial de navegación (Back/Forward)
export const folderBackStack = writable<string[]>([]);
export const folderForwardStack = writable<string[]>([]);

// Marcador actual en edición
export const pinMarkerOpen = writable(false);
export const pinMarkerPath = writable("");
export const pinMarkerName = writable("");
