import { normalizePathForApi } from "./pathUtils";

export type GalleryItem = {
  kind: "image" | "video" | "file" | "folder" | "folder_up" | "section" | "day_break" | "placeholder";
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
  /** Índice absoluto en ordered_paths (scroll virtual). */
  mediaIndex?: number;
  /** Ancho/alto de miniatura masonry en px (proporción real en la UI). */
  thumbW?: number;
  thumbH?: number;
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
      gallery_show_other_files: false,
      gallery_warm_index_on_startup: false,
      gallery_warm_include_children: true,
      gallery_warm_max_depth: 2,
      gallery_sort_mode: "name,mtime,type",
      gallery_group_by_folder: false,
      gallery_group_by_alpha: false,
      gallery_timeline_view: false,
      gallery_section_dominant_color: true,
      web_settings_show_advanced: false,
      web_ui_show_processes: false,
      web_ui_show_scan_hint: false,
      web_ui_show_build_tag: false,
      web_debug_log_enabled: false,
    },
    gallery: mockGalleryState(),
    destinations: [],
    markers: [],
  }),
  gallery_load_folder: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_layout_report: async (_max = 0) => ({
    config: {
      gallery_sort_mode: "name,mtime,type",
      gallery_group_by_folder: false,
      gallery_group_by_alpha: false,
      gallery_timeline_view: false,
      gallery_include_subfolders: false,
      gallery_show_other_files: false,
      layoutMode: "flat",
    },
    total: 0,
    listed: 0,
    truncated: false,
    sections: [] as Array<{ start: number; end: number; label: string; kind: string; key: string; count: number }>,
    sectionSummaries: [] as Array<{
      category: string;
      count: number;
      first: string;
      last: string;
      files: string[];
      sample: string[] | null;
      sortType: string;
      temporalBase: string;
      groupKey: string;
    }>,
    items: [] as never[],
  }),
  gallery_reload: async () => mockGalleryPayload(),
  gallery_load_more: async () => ({ ...mockGalleryPayload(), hasMore: false }),
  gallery_load_until_index: async (_target: number) => ({ ...mockGalleryPayload(), hasMore: false, items: [] }),
  gallery_pin_folder: async () => ({ pinnedFolders: [] as string[] }),
  gallery_unpin_folder: async () => ({ pinnedFolders: [] as string[] }),
  gallery_go_page: async () => mockGalleryPayload(),
  gallery_open_folder_tile: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_toggle_select: async () => mockGalleryPayload(),
  gallery_apply_selection_delta: async () => mockGalleryPayload(),
  gallery_refresh_items: async () => mockGalleryPayload(),
  gallery_index_warm_start: async (_paths: string[] | null = null, _includeChildren = true) => ({
    running: false,
    done: 0,
    total: 0,
    currentPath: "",
    errors: [] as Array<{ path: string; error: string }>,
    cancelled: false,
  }),
  gallery_index_warm_status: async () => ({
    running: false,
    done: 0,
    total: 0,
    currentPath: "",
    errors: [] as Array<{ path: string; error: string }>,
    cancelled: false,
  }),
  gallery_index_warm_cancel: async () => ({ running: false, cancelled: true }),
  gallery_index_status: async (_path: string) => ({
    ok: true,
    cached: false,
    source: "miss",
    pathCount: 0,
    previewCached: false,
    pinned: false,
  }),
  gallery_index_reindex: async (_path: string) => ({
    ok: true,
    path: _path,
    source: "fresh",
    count: 0,
  }),
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
    ffmpegAvailable: false,
    ffprobeAvailable: false,
    transcodeCached: false,
    playbackFormat: "mp4",
  }),
  gallery_transcode_active: async () => ({ jobs: [] as Array<{ id: string; path: string; name: string; format: string }>, count: 0 }),
  gallery_transcode_cancel: async (_path: string) => ({ ok: true, cancelled: false, path: _path }),
  gallery_video_playback_blob: async () => ({ ok: false, error: "mock" }),
  gallery_video_diagnostics: async () => ({
    path: "",
    exists: false,
    error: "Solo disponible con la app Python (PyWebView).",
  }),
  gallery_video_system_diagnostics: async () => ({
    engine: "mock",
    prefersWebm: false,
    qtFreeworld: false,
    ffmpegAvailable: false,
    hwEncodersAvailable: [] as string[],
    webmHwEncodersAvailable: [] as string[],
    transcodeMaxJobs: 1,
    transcodeCacheFiles: 0,
    transcodeCacheBytes: 0,
    activeTranscodeJobs: 0,
  }),
  gallery_open_external: async () => ({ ok: true }),
  gallery_show_in_explorer: async () => ({ ok: true }),
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
  destination_move_paths_new_folder: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0, destFolder: "" },
  }),
  destination_move_folder: async () => ({
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
  gallery_rename_path: async () => ({
    ...mockGalleryPayload(),
    renameResult: { previousPath: "", newPath: "", newName: "" },
  }),
  gallery_delete_folder: async () => ({
    ...mockGalleryPayload(),
    deleteResult: { deleted: 0, errors: 0 },
  }),
  gallery_image_rotate: async () => mockGalleryPayload(),
  gallery_image_crop_normalized: async () => mockGalleryPayload(),
  gallery_thumb_hq: async (path: string) => ({ path, thumbDataUrl: null }),
  destination_preview: async () => ({ items: [], cols: 4, total: 0 }),
  destination_preview_thumbs: async () => ({ items: [] }),
  destination_thumb_hq: async (path: string) => ({ path, thumbDataUrl: null }),
  destinations_add: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_edit: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_remove: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_reorder: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_get: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_save_tree: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_set_toolbar_folder: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_folder_add: async () => ({ destinations: [], toolbarFolderId: "", folderId: "" }),
  destinations_folder_edit: async () => ({ destinations: [], toolbarFolderId: "" }),
  destinations_folder_remove: async () => ({ destinations: [], toolbarFolderId: "" }),
  markers_get: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_save_tree: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_set_toolbar_folder: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_add: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_edit: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_remove: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_reorder: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_folder_add: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[], folderId: "" }),
  markers_folder_edit: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  markers_folder_remove: async () => ({ markers: [], toolbarFolderId: "", pinnedFolders: [] as string[] }),
  settings_patch: async (data: Record<string, unknown>) => ({ settings: { ...data } }),
  organizer_start: async () => ({ ok: false, error: "Solo disponible con la app Python (PyWebView)." }),
  organizer_cancel: async () => ({ ok: true }),
  organizer_status: async () => ({
    running: false,
    progress: { current: 0, total: 0, detail: "Modo navegador (mock)" },
    done: null,
  }),
  mess_scan_start: async () => ({ ok: false, error: "Solo disponible con la app Python (PyWebView)." }),
  mess_scan_cancel: async () => ({ ok: true }),
  mess_scan_status: async () => ({
    running: false,
    progress: { current: 0, total: 0, detail: "Modo navegador (mock)" },
    result: null,
    error: null,
  }),
  mess_move_cluster: async () => ({ ok: false, moved: 0, errors: 0 }),
  mess_save_settings: async (_folder: string, _sim?: number) => ({ settings: {} }),
  mess_thumbs: async () => ({ items: [] }),
  mess_list_images: async () => ({ ok: true, paths: [], folder: "", total: 0, truncated: false }),
  mess_similar_paths: async () => ({ ok: true, anchor: "", items: [] }),
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
  galleryLoadFolder: (path: string, deferThumbs = false) =>
    call<any>("gallery_load_folder", path, Boolean(deferThumbs)),
  galleryLayoutReport: (maxItems = 0) => call<any>("gallery_layout_report", maxItems),
  galleryReload: () => call<any>("gallery_reload"),
  galleryLoadMore: () => call<any>("gallery_load_more"),
  galleryLoadUntilIndex: (targetIndex: number, jump = false, expand = false) =>
    call<any>(
      "gallery_load_until_index",
      Math.max(0, Math.floor(targetIndex)),
      Boolean(jump),
      Boolean(expand),
    ),
  galleryPinFolder: (path: string) => call<any>("gallery_pin_folder", path),
  galleryUnpinFolder: (path: string) => call<any>("gallery_unpin_folder", path),
  galleryGoPage: (page: number) => call<any>("gallery_go_page", page),
  galleryOpenFolderTile: (path: string) => call<any>("gallery_open_folder_tile", path),
  galleryToggleSelect: (path: string) => call<any>("gallery_toggle_select", path),
  galleryApplySelectionDelta: (addPaths: string[], removePaths: string[]) =>
    call<any>("gallery_apply_selection_delta", addPaths, removePaths),
  galleryRefreshItems: () => call<any>("gallery_refresh_items"),
  galleryIndexWarmStart: (paths: string[] | null, includeChildren = true) =>
    call<any>("gallery_index_warm_start", paths, includeChildren),
  galleryIndexWarmStatus: () => call<any>("gallery_index_warm_status"),
  galleryIndexWarmCancel: () => call<any>("gallery_index_warm_cancel"),
  galleryIndexStatus: (path: string) => call<any>("gallery_index_status", normalizePathForApi(path)),
  galleryIndexReindex: (path: string) => call<any>("gallery_index_reindex", normalizePathForApi(path)),
  gallerySelectPage: () => call<any>("gallery_select_page"),
  galleryClearSelection: () => call<any>("gallery_clear_selection"),
  galleryInvertSelection: () => call<any>("gallery_invert_selection"),
  galleryPreview: (path: string, width: number, height: number) =>
    call<any>("gallery_preview", normalizePathForApi(path), width, height),
  galleryMediaUrl: (path: string, warm = false, playbackMode = "auto") =>
    call<any>("gallery_media_url", normalizePathForApi(path), warm, playbackMode),
  galleryVideoProfiles: (path: string) =>
    call<{ profiles: Array<{ id: string; available: boolean; recommended?: boolean; strategy?: string }>; defaultMode?: string; strategy?: string }>(
      "gallery_video_profiles",
      normalizePathForApi(path)
    ),
  galleryTranscodeActive: () => call<{ jobs: Array<{ id: string; path: string; name: string; format: string; progress?: string; status?: string; queuePosition?: string }>; count: number }>("gallery_transcode_active"),
  galleryTranscodePrioritize: (path: string, playbackMode = "auto") =>
    call<{ ok: boolean; bumped?: number; drained?: number; preempted?: number; path?: string; error?: string }>(
      "gallery_transcode_prioritize",
      normalizePathForApi(path),
      playbackMode
    ),
  galleryTranscodeDrainWarm: () =>
    call<{ ok: boolean; removed?: number; queued?: number; preempted?: number; workers?: number }>(
      "gallery_transcode_drain_warm"
    ),
  galleryTranscodeCancel: (path: string) => call<{ ok: boolean; cancelled?: boolean; path?: string; error?: string }>("gallery_transcode_cancel", path),
  galleryVideoDiagnostics: (path: string, testTranscode = false) =>
    call<any>("gallery_video_diagnostics", normalizePathForApi(path), testTranscode),
  galleryVideoDirectRejected: (path: string) =>
    call<{ ok: boolean; path?: string; error?: string }>("gallery_video_direct_rejected", normalizePathForApi(path)),
  galleryVideoSystemDiagnostics: () => call<any>("gallery_video_system_diagnostics"),
  galleryVideoPlaybackBlob: (path: string) =>
    call<any>("gallery_video_playback_blob", normalizePathForApi(path)),
  galleryOpenExternal: (path: string) => call<any>("gallery_open_external", normalizePathForApi(path)),
  galleryShowInExplorer: (path: string) => call<any>("gallery_show_in_explorer", normalizePathForApi(path)),
  galleryFileBase64: (path: string) => call<any>("gallery_file_base64", path),
  galleryCopyToClipboard: (path: string) => call<any>("gallery_copy_to_clipboard", path),
  galleryCopyTextToClipboard: (text: string) => call<any>("gallery_copy_text_to_clipboard", text),
  galleryFileStat: (path: string) => call<any>("gallery_file_stat", normalizePathForApi(path)),
  destinationMoveSelected: (path: string) => call<any>("destination_move_selected", path),
  destinationMovePaths: (paths: string[], destPath: string) =>
    call<any>("destination_move_paths", paths, destPath),
  destinationMovePathsNewFolder: (paths: string[], parentPath: string, folderName: string, merge = false) =>
    call<any>("destination_move_paths_new_folder", paths, parentPath, folderName, merge),
  destinationMoveFolder: (folderPath: string, destPath: string) =>
    call<any>("destination_move_folder", normalizePathForApi(folderPath), destPath),
  destinationMoveFromPreview: (paths: string[]) => call<any>("destination_move_from_preview", paths),
  galleryDeleteSelected: () => call<any>("gallery_delete_selected"),
  galleryDeletePaths: (paths: string[]) => call<any>("gallery_delete_paths", paths),
  galleryMovePath: (srcPath: string, destPath: string) => call<any>("gallery_move_path", srcPath, destPath),
  galleryUndoLastMove: () => call<any>("gallery_undo_last_move"),
  galleryRenamePath: (path: string, newName: string) =>
    call<any>("gallery_rename_path", normalizePathForApi(path), newName),
  galleryDeleteFolder: (path: string) =>
    call<any>("gallery_delete_folder", normalizePathForApi(path)),
  galleryImageRotate: (path: string, degrees: number) => call<any>("gallery_image_rotate", path, degrees),
  galleryImageCropNormalized: (path: string, left: number, top: number, width: number, height: number) =>
    call<any>("gallery_image_crop_normalized", path, left, top, width, height),
  galleryThumbHq: (path: string, scale: number) => call<any>("gallery_thumb_hq", path, scale),
  destinationPreview: (path: string, scale: number, width: number) =>
    call<any>("destination_preview", path, scale, width),
  destinationPreviewThumbs: (paths: string[], scale: number, profile: "lq" | "hq" = "lq") =>
    call<any>("destination_preview_thumbs", paths, scale, profile),
  destinationThumbHq: (path: string, scale: number) => call<any>("destination_thumb_hq", path, scale),
  destinationsAdd: (label: string, path: string, parentId = "") =>
    call<any>("destinations_add", label, path, parentId),
  destinationsEdit: (parentId: string, idx: number, label: string, path: string) =>
    call<any>("destinations_edit", parentId, idx, label, path),
  destinationsRemove: (parentId: string, idx: number) => call<any>("destinations_remove", parentId, idx),
  destinationsReorder: (parentId: string, fromIdx: number, toIdx: number) =>
    call<any>("destinations_reorder", parentId, fromIdx, toIdx),
  destinationsSaveTree: (tree: unknown[]) => call<any>("destinations_save_tree", tree),
  destinationsSetToolbarFolder: (folderId = "") => call<any>("destinations_set_toolbar_folder", folderId),
  destinationsFolderAdd: (label: string, parentId = "") => call<any>("destinations_folder_add", label, parentId),
  destinationsFolderEdit: (folderId: string, label: string) =>
    call<any>("destinations_folder_edit", folderId, label),
  destinationsFolderRemove: (folderId: string) => call<any>("destinations_folder_remove", folderId),
  /** Lista de destinos en árbol (menos datos que get_initial_state; más fiable con Qt). */
  destinationsGet: () => call<any>("destinations_get"),
  markersGet: () => call<any>("markers_get"),
  markersSaveTree: (tree: unknown[]) => call<any>("markers_save_tree", tree),
  markersSetToolbarFolder: (folderId = "") => call<any>("markers_set_toolbar_folder", folderId),
  markersAdd: (path: string, label = "", parentId = "") => call<any>("markers_add", path, label, parentId),
  markersEdit: (parentId: string, idx: number, label: string, path: string) =>
    call<any>("markers_edit", parentId, idx, label, path),
  markersRemove: (parentId: string, idx: number) => call<any>("markers_remove", parentId, idx),
  markersReorder: (parentId: string, fromIdx: number, toIdx: number) =>
    call<any>("markers_reorder", parentId, fromIdx, toIdx),
  markersFolderAdd: (label: string, parentId = "") => call<any>("markers_folder_add", label, parentId),
  markersFolderEdit: (folderId: string, label: string) => call<any>("markers_folder_edit", folderId, label),
  markersFolderRemove: (folderId: string) => call<any>("markers_folder_remove", folderId),
  settingsPatch: (data: Record<string, any>) => call<any>("settings_patch", data),
  organizerStart: (path: string, options: Record<string, any>) => call<any>("organizer_start", path, options),
  organizerCancel: () => call<any>("organizer_cancel"),
  organizerStatus: () => call<any>("organizer_status"),
  messScanStart: (folderPath: string, minSimilarity?: number) =>
    call<any>("mess_scan_start", folderPath, minSimilarity),
  messScanCancel: () => call<any>("mess_scan_cancel"),
  messScanStatus: () => call<any>("mess_scan_status"),
  messMoveCluster: (paths: string[], destPath: string) => call<any>("mess_move_cluster", paths, destPath),
  messSaveSettings: (folderPath: string, minSimilarity?: number) =>
    call<any>("mess_save_settings", folderPath, minSimilarity),
  messThumbs: (paths: string[], size = 120) => call<any>("mess_thumbs", paths, size),
  messListImages: (folderPath?: string, limit?: number) =>
    call<any>("mess_list_images", folderPath ?? "", limit),
  messSimilarPaths: (anchorPath: string, candidatePaths: string[], minSimilarity?: number, limit = 32) =>
    call<any>("mess_similar_paths", anchorPath, candidatePaths, minSimilarity, limit),
  dialogPickFolder: (startPath?: string) => call<any>("dialog_pick_folder", startPath ?? ""),
};
