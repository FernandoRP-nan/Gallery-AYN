import { writable } from 'svelte/store';
import type { GalleryItem } from '../lib/api';

// Estado de navegación
export const currentFolder = writable("");
export const galleryItems = writable<GalleryItem[]>([]);
export const galleryState = writable({ page: 1, totalPages: 1, total: 0, selectedCount: 0 });

// Configuración de visualización
export const thumbScale = writable(1);
export const thumbGapPx = writable(12);
export const showThumbLabels = writable(true);
export const thumbCardStyle = writable<"soft" | "flat" | "outlined">("soft");
export const thumbFrameVisible = writable(true);
export const thumbImageRadiusPx = writable(6);
export const thumbTileRadiusPx = writable(12);

// Filtros y Orden
export const includeSubfolders = writable(false);
export const groupByFolder = writable(false);
export const sectionDominantColor = writable(true);
export const timelineView = writable(false);
export const gallerySortMode = writable<"name" | "mtime">("name");
export const orgPath = writable("");

// Estado de carga
export const galleryLoadingMore = writable(false);
export const galleryHasMore = writable(false);

// Carpetas destino
export const destRows = writable<Array<{ label: string; path: string }>>([]);
