export type GalleryItem = {
  kind: "image" | "folder" | "folder_up";
  name: string;
  path: string;
  thumbDataUrl?: string | null;
  selected?: boolean;
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
      gallery_thumb_scale: 1,
      dest_preview_thumb_scale: 1,
      web_preview_ratio: 0.4,
      web_dest_panel_ratio: 0.26,
      dest_preview_modal_w: 0.9,
      dest_preview_modal_h: 0.8,
      gallery_recent_folders: [] as string[],
      gallery_thumbs_per_page: 48,
    },
    gallery: mockGalleryState(),
    destinations: [],
  }),
  gallery_load_folder: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_reload: async () => mockGalleryPayload(),
  gallery_go_page: async () => mockGalleryPayload(),
  gallery_open_folder_tile: async () => ({ ...mockGalleryPayload(), recentFolders: [] as string[] }),
  gallery_toggle_select: async () => mockGalleryPayload(),
  gallery_refresh_items: async () => mockGalleryPayload(),
  gallery_select_page: async () => mockGalleryPayload(),
  gallery_clear_selection: async () => mockGalleryPayload(),
  gallery_invert_selection: async () => mockGalleryPayload(),
  gallery_preview: async () => ({ path: "", name: "", dataUrl: null }),
  destination_move_selected: async () => ({
    ...mockGalleryPayload(),
    moveResult: { moved: 0, errors: 0 },
  }),
  destination_preview: async () => ({ items: [], cols: 4 }),
  destinations_add: async () => ({ destinations: [] }),
  destinations_remove: async () => ({ destinations: [] }),
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
  galleryGoPage: (page: number) => call<any>("gallery_go_page", page),
  galleryOpenFolderTile: (path: string) => call<any>("gallery_open_folder_tile", path),
  galleryToggleSelect: (path: string) => call<any>("gallery_toggle_select", path),
  galleryRefreshItems: () => call<any>("gallery_refresh_items"),
  gallerySelectPage: () => call<any>("gallery_select_page"),
  galleryClearSelection: () => call<any>("gallery_clear_selection"),
  galleryInvertSelection: () => call<any>("gallery_invert_selection"),
  galleryPreview: (path: string, width: number, height: number) =>
    call<any>("gallery_preview", path, width, height),
  destinationMoveSelected: (path: string) => call<any>("destination_move_selected", path),
  destinationPreview: (path: string, scale: number, width: number) =>
    call<any>("destination_preview", path, scale, width),
  destinationsAdd: (label: string, path: string) => call<any>("destinations_add", label, path),
  destinationsRemove: (idx: number) => call<any>("destinations_remove", idx),
  settingsPatch: (data: Record<string, any>) => call<any>("settings_patch", data),
  organizerStart: (path: string, options: Record<string, any>) => call<any>("organizer_start", path, options),
  organizerCancel: () => call<any>("organizer_cancel"),
  organizerStatus: () => call<any>("organizer_status"),
  dialogPickFolder: (startPath?: string) => call<any>("dialog_pick_folder", startPath ?? ""),
};
