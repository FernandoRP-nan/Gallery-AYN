import { writable, derived } from 'svelte/store';
import { readCachedUiTheme, type UiThemeId } from '../uiTheme';
import { t } from '../i18n';

// Tema de la interfaz
export const uiTheme = writable<UiThemeId>(readCachedUiTheme());

// Estado de modales y paneles
export const settingsOpen = writable<boolean>(false);
export const orgPanelOpen = writable<boolean>(false);
export const viewMenuOpen = writable<boolean>(false);
export const destinationsMode = writable<boolean>(false);

// Mensajes y carga
export const status = writable<string>(t('status.ready'));
export const loadCount = writable<number>(0);
export const uiLoading = derived(loadCount, ($count) => $count > 0);

// Configuraciones visuales generales
export const showThumbLabels = writable<boolean>(true);
export const thumbFrameVisible = writable<boolean>(true);
export const thumbCardStyle = writable<"soft" | "flat" | "outlined">("soft");
export const thumbGapPx = writable<number>(12);
export const thumbImageRadiusPx = writable<number>(6);
export const thumbTileRadiusPx = writable<number>(12);
