import { writable } from 'svelte/store';
import type { GalleryItem } from '../api';

// Estado de navegación
export const folder = writable<string>("");
export const folderBackStack = writable<string[]>([]);
export const folderForwardStack = writable<string[]>([]);

// Estado de la galería actual
export const galleryState = writable<any>({ page: 1, totalPages: 1, total: 0, selectedCount: 0 });
export const items = writable<GalleryItem[]>([]);
export const destRows = writable<Array<{ label: string; path: string }>>([]);

// Historial y favoritos
export const recentFolders = writable<string[]>([]);
export const pinnedFolders = writable<string[]>([]);
export const pinnedFolderLabels = writable<Record<string, string>>({});

// Parámetros de visualización y configuración de galería
export const thumbScale = writable<number>(1);
export const thumbsPerPage = writable<number>(48);
export const includeSubfolders = writable<boolean>(false);
export const groupByFolder = writable<boolean>(false);
export const sectionDominantColor = writable<boolean>(true);
export const timelineView = writable<boolean>(false);
export const gallerySortMode = writable<"name" | "mtime">("name");

// Atajos de teclado
export const keyboardShortcuts = writable<Record<string, string>>({});
