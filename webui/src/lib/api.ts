import { normalizePathForApi } from "./pathUtils";

export type GalleryItem = {
  kind: "image" | "video" | "folder" | "folder_up" | "section" | "day_break";
  name: string;
  path: string;
  /** Carpeta destino de la sección (solo kind === "section"). */
  sectionFolder?: string;
  /** Fecha del archivo YYYY-MM-DD (vista línea de tiempo). */
  mtimeIso?: string;
  /** Tinte de fondo (#rrggbb) según color medio de la sección (agrupar por carpeta). */
  sectionTintHex?: string;
  thumbDataUrl?: string | null;
  /** Placeholder LQ conservado durante el crossfade a HQ. */
  thumbLqDataUrl?: string | null;
  thumbQuality?: "lq" | "hq";
  selected?: boolean;
  /** Miniaturas del contenido interior (solo kind === "folder", hasta 4 elementos). */
  folderPreviewUrls?: (string | null)[];
};


type WebApi = Record<string, (...args: any[]) => Promise<any>>;

declare global {
  interface Window {
    pywebview?: {
      api: WebApi;
    };
  }
}

const isDevBrowser = (): boolean =>
  typeof import.meta !== "undefined" && Boolean((import.meta as any).env?.DEV) && !window.pywebview?.api;

const mockGalleryState = () => ({
  folder: "",
  total: 0,
  totalImages: 0,
  totalVideos: 0,
  totalElements: 0,
  totalBytes: 0,
  page: 1,
  totalPages: 1,
  startIndex: 0,
  endIndex: 0,
  selectedCount: 0,
  subfoldersCount: 0,
});

const mockGalleryPayload = () => ({
  state: mockGalleryState(),
  items: [] as GalleryItem[],
});

/** Respuestas mínimas para desarrollo en el navegador (sin PyWebView). */
const devMockApi: WebApi = {
  get_initial_state: async () => ({
    settings: {
      web_ui_theme: "midnight",
      gallery_thumb_scale: 1,
      dest_preview_thumb_scale: 1,
      web_preview_ratio: 0.4,
      web_dest_panel_ratio: 0.26,
      dest_preview_modal_w: 0.9,
      dest_preview_modal_h: 0.8,
      gallery_recent_folders: [] as string[],
      gallery_thumbs_per_page: 48,
      gallery_include_subfolders: false,
      gallery_sort_mode: "name,mtime,type",
      gallery_group_by_folder: false,
      gallery_timeline_view: false,
      gallery_section_dominant_color: true,
    },
    gallery: mockGalleryState(),
    destinations: [],
  }),
  gallery_load_folder: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_reload: async () => mockGalleryPayload(),
  gallery_load_more: async () => ({ ...mockGalleryPayload(), hasMore: false }),
  gallery_pin_folder: async () => ({ pinnedFolders: [] as string[] }),
  gallery_unpin_folder: async () => ({ pinnedFolders: [] as string[] }),
  gallery_go_page: async () => mockGalleryPayload(),
  gallery_open_folder_tile: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_toggle_select: async () => mockGalleryPayload(),
  gallery_apply_selection_delta: async () => mockGalleryPayload(),
  gallery_refresh_items: async () => mockGalleryPayload(),
  gallery_select_page: async () => mockGalleryPayload(),
  gallery_clear_selection: async () => mockGalleryPayload(),
  gallery_invert_selection: async () => mockGalleryPayload(),
  gallery_preview: async () => ({
    path: "",
    name: "",
    dataUrl: null,
    mediaType: "image" as const,
    fileUrl: null as string | null,
    transcodeUrl: null as string | null,
    needsTranscode: false,
  }),
  gallery_media_url: async () => ({
    path: "",
    fileUrl: null as string | null,
    transcodeUrl: null as string | null,
    needsTranscode: false,
    mimeType: null as string | null,
  }),
  gallery_video_playback_blob: async () => ({ ok: false, error: "mock" }),
  gallery_video_diagnostics: async () => ({
    path: "",
    exists: false,
    error: "Solo disponible con la app Python (PyWebView).",
  }),
  gallery_open_external: async () => ({ ok: true }),
  gallery_file_base64: async () => ({
    dataUrl: null as string | null,
    error: null as string | null,
  }),
  gallery_copy_to_clipboard: async () => ({
    ok: false,
    error: null as string | null,
  }),
  gallery_copy_text_to_clipboard: async () => ({ ok: true }),
  gallery_file_stat: async () => ({
    path: "",
    name: "",
    sizeBytes: 0,
    mtimeIso: "",
    extension: "",
    mediaType: "image",
    mimeType: "",
  }),
  destination_move_selected: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  destination_move_paths: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  destination_move_from_preview: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  gallery_delete_selected: async () => ({
    ...mockGalleryPayload(),
    deleteResult: { deleted: 0, errors: 0 },
  }),
  gallery_delete_paths: async () => ({
    ...mockGalleryPayload(),
    deleteResult: { deleted: 0, errors: 0 },
  }),
  gallery_move_path: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  gallery_undo_last_move: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  gallery_image_rotate: async () => mockGalleryPayload(),
  gallery_image_crop_normalized: async () => mockGalleryPayload(),
  gallery_thumb_hq: async (path: string) => ({ path, thumbDataUrl: null }),
  destination_preview: async () => ({ items: [], cols: 4 }),
  destination_thumb_hq: async (path: string) => ({ path, thumbDataUrl: null }),
  destinations_add: async () => ({ destinations: [] }),
  destinations_edit: async () => ({ destinations: [] }),
  destinations_remove: async () => ({ destinations: [] }),
  destinations_reorder: async () => ({ destinations: [] }),
  destinations_get: async () => ({ destinations: [] }),
  settings_patch: async (data: Record<string, unknown>) => ({ settings: { ...data } }),
  organizer_start: async () => ({ ok: false, error: "Solo disponible con la app Python (PyWebView)." }),
  organizer_cancel: async () => ({ ok: true }),
  organizer_status: async () => ({
    running: false,
    progress: { current: 0, total: 0, detail: "Modo navegador (mock)" },
    done: null,
  }),
  dialog_pick_folder: async () => ({
    path: null as string | null,
    cancelled: true,
    hint:
      "En el navegador no hay explorador del sistema. Abre la app con Python (PyWebView) o escribe la ruta a mano.",
  }),
};

const call = async <T>(method: string, ...args: any[]): Promise<T> => {
  let api = window.pywebview?.api;
  if (isDevBrowser()) {
    api = devMockApi as unknown as WebApi;
  }
  if (!api || !api[method]) {
    throw new Error(
      `API no disponible: ${method}. Ejecuta la app con Python+PyWebView o usa npm run dev con el mock del navegador.`
    );
  }
  return api[method](...args) as Promise<T>;
};

export const bridge = {
  getInitialState: () => call<any>("get_initial_state"),
  galleryLoadFolder: (path: string) => call<any>("gallery_load_folder", path),
  galleryReload: () => call<any>("gallery_reload"),
  galleryLoadMore: () => call<any>("gallery_load_more"),
  galleryPinFolder: (path: string) => call<any>("gallery_pin_folder", path),
  galleryUnpinFolder: (path: string) => call<any>("gallery_unpin_folder", path),
  galleryGoPage: (page: number) => call<any>("gallery_go_page", page),
  galleryOpenFolderTile: (path: string) => call<any>("gallery_open_folder_tile", path),
  galleryToggleSelect: (path: string) => call<any>("gallery_toggle_select", path),
  galleryApplySelectionDelta: (addPaths: string[], removePaths: string[]) =>
    call<any>("gallery_apply_selection_delta", addPaths, removePaths),
  galleryRefreshItems: () => call<any>("gallery_refresh_items"),
  gallerySelectPage: () => call<any>("gallery_select_page"),
  galleryClearSelection: () => call<any>("gallery_clear_selection"),
  galleryInvertSelection: () => call<any>("gallery_invert_selection"),
  galleryPreview: (path: string, width: number, height: number) =>
    call<any>("gallery_preview", normalizePathForApi(path), width, height),
  galleryMediaUrl: (path: string) => call<any>("gallery_media_url", normalizePathForApi(path)),
  galleryVideoDiagnostics: (path: string, testTranscode = false) =>
    call<any>("gallery_video_diagnostics", normalizePathForApi(path), testTranscode),
  galleryVideoPlaybackBlob: (path: string) =>
    call<any>("gallery_video_playback_blob", normalizePathForApi(path)),
  galleryOpenExternal: (path: string) => call<any>("gallery_open_external", normalizePathForApi(path)),
  galleryFileBase64: (path: string) => call<any>("gallery_file_base64", path),
  galleryCopyToClipboard: (path: string) => call<any>("gallery_copy_to_clipboard", path),
  galleryCopyTextToClipboard: (text: string) => call<any>("gallery_copy_text_to_clipboard", text),
  galleryFileStat: (path: string) => call<any>("gallery_file_stat", normalizePathForApi(path)),
  destinationMoveSelected: (path: string) => call<any>("destination_move_selected", path),
  destinationMovePaths: (paths: string[], destPath: string) =>
    call<any>("destination_move_paths", paths, destPath),
  destinationMoveFromPreview: (paths: string[]) => call<any>("destination_move_from_preview", paths),
  galleryDeleteSelected: () => call<any>("gallery_delete_selected"),
  galleryDeletePaths: (paths: string[]) => call<any>("gallery_delete_paths", paths),
  galleryMovePath: (srcPath: string, destPath: string) => call<any>("gallery_move_path", srcPath, destPath),
  galleryUndoLastMove: () => call<any>("gallery_undo_last_move"),
  galleryImageRotate: (path: string, degrees: number) => call<any>("gallery_image_rotate", path, degrees),
  galleryImageCropNormalized: (path: string, left: number, top: number, width: number, height: number) =>
    call<any>("gallery_image_crop_normalized", path, left, top, width, height),
  galleryThumbHq: (path: string, scale: number) => call<any>("gallery_thumb_hq", path, scale),
  destinationPreview: (path: string, scale: number, width: number) =>
    call<any>("destination_preview", path, scale, width),
  destinationThumbHq: (path: string, scale: number) => call<any>("destination_thumb_hq", path, scale),
  destinationsAdd: (label: string, path: string) => call<any>("destinations_add", label, path),
  destinationsEdit: (idx: number, label: string, path: string) =>
    call<any>("destinations_edit", idx, label, path),
  destinationsRemove: (idx: number) => call<any>("destinations_remove", idx),
  destinationsReorder: (fromIdx: number, toIdx: number) => call<any>("destinations_reorder", fromIdx, toIdx),
  /** Lista corta solo destinos (menos datos que get_initial_state; más fiable con Qt). */
  destinationsGet: () => call<any>("destinations_get"),
  settingsPatch: (data: Record<string, any>) => call<any>("settings_patch", data),
  organizerStart: (path: string, options: Record<string, any>) => call<any>("organizer_start", path, options),
  organizerCancel: () => call<any>("organizer_cancel"),
  organizerStatus: () => call<any>("organizer_status"),
  dialogPickFolder: (startPath?: string) => call<any>("dialog_pick_folder", startPath ?? ""),
};
