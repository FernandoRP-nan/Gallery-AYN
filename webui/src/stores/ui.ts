import { writable } from 'svelte/store';
import { readCachedUiTheme, type UiThemeId } from '../lib/uiTheme';
import { t } from '../lib/i18n';

// Tema visual
export const uiTheme = writable<UiThemeId>(readCachedUiTheme());

// Estados de carga y mensajes
export const uiLoading = writable(false);
export const status = writable(t("status.ready"));

// Visibilidad de modales principales
export const settingsOpen = writable(false);
export const orgPanelOpen = writable(false);
export const confirmDeleteOpen = writable(false);
export const viewMenuOpen = writable(false);
export const routePickerOpen = writable(false);
export const destinationsMode = writable(false);

// Configuración de borrado
export const confirmDeleteTitle = writable("");
export const confirmDeleteDetail = writable("");
export const confirmDeleteConfirmLabel = writable("");
export const confirmDeleteBypassEnabled = writable(false);
export const confirmDeleteBypassLabel = writable("");
export const confirmDeleteBypassChecked = writable(false);
export let onConfirmDelete: (() => void) | null = null;

export function openConfirmDelete(title: string, detail: string, onConfirm: () => void, opts: { confirmLabel?: string, bypassLabel?: string, bypassEnabled?: boolean } = {}) {
    confirmDeleteTitle.set(title);
    confirmDeleteDetail.set(detail);
    confirmDeleteConfirmLabel.set(opts.confirmLabel || "");
    confirmDeleteBypassEnabled.set(opts.bypassEnabled || false);
    confirmDeleteBypassLabel.set(opts.bypassLabel || "");
    onConfirmDelete = onConfirm;
    confirmDeleteOpen.set(true);
}

export function closeConfirmDelete() {
    confirmDeleteOpen.set(false);
    onConfirmDelete = null;
}
