<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  let pollTimer: number | null = null;
  import { bridge, type GalleryItem } from "./lib/api";
  import ConfirmDeleteModal from "./components/ConfirmDeleteModal.svelte";
  import LoadOverlay from "./components/LoadOverlay.svelte";
  import SettingsModal from "./components/SettingsModal.svelte";
  import { t } from "./lib/i18n";
  import { galleryGridCellPx } from "./lib/thumbScale";
  import {
    applyUiThemeToDocument,
    normalizeUiTheme,
    readCachedUiTheme,
    type UiThemeId,
  } from "./lib/uiTheme";

  const BLANK_DRAG_IMG =
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  let folder = "";
  let galleryState: any = { page: 1, totalPages: 1, total: 0, selectedCount: 0 };
  let items: GalleryItem[] = [];
  /** Carpetas destino (mismo patrón reactivo que `items`: `let` + asignación tras el API). */
  let destRows: Array<{ label: string; path: string }> = [];
  let selectedPreview: {
    path: string;
    name: string;
    dataUrl: string | null;
    mediaType?: "image" | "video" | "svg";
    fileUrl?: string | null;
  } | null = null;
  let status = t("status.ready");
  let thumbScale = 1;
  let previewOpen = false;
  let previewItems: Array<{ name: string; path: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }> = [];
  let previewSelectedPaths: string[] = [];
  let previewSelectionMode = false;
  let previewLongPressTimer: ReturnType<typeof setTimeout> | null = null;
  let previewLongPressPath: string | null = null;
  let previewLongPressTriggered = false;
  let previewRangeSelecting = false;
  let previewRangeAnchorPath: string | null = null;
  let previewRangeMode: "select" | "deselect" = "select";
  let previewRangeBaseSelectedPaths: string[] = [];
  let previewSuppressClick = false;
  let previewDragActive = false;
  let galleryRangeSelecting = false;
  let galleryRangeAnchorPath: string | null = null;
  let galleryRangeMode: "select" | "deselect" = "select";
  let galleryRangeBaseSelectedPaths: string[] = [];
  let galleryRangeBaseSelectedSet: Set<string> | null = null;
  let galleryRangeDraftSelectedPaths: string[] | null = null;
  let galleryRangeDraftSelectedSet: Set<string> | null = null;
  let galleryRangeCurrentPath: string | null = null;
  let galleryRangePendingPath: string | null = null;
  let galleryRangeRaf: number | null = null;
  let galleryRangeSuppressClick = false;
  let galleryCursorPath: string | null = null;
  let galleryKeyboardRangeAnchorPath: string | null = null;
  let galleryKeyboardNavHintActive = false;
  let previewZoomOpen = false;
  let previewZoomPath = "";
  let previewZoomName = "";
  let previewZoomDataUrl: string | null = null;
  let previewZoomScale = 1;
  let previewZoomMode: "fit" | "fillWidth" = "fit";
  let previewFillWidthAlignPending = false;
  let previewPanX = 0;
  let previewPanY = 0;
  let previewPanDrag = false;
  let previewPanMoved = false;
  let previewPanStartX = 0;
  let previewPanStartY = 0;
  let previewZoomCarouselVisible = true;
  let previewZoomDestMode = false;
  let previewZoomCanUndoMove = false;
  let zoomMoveQueue: Array<{ srcPath: string; destPath: string }> = [];
  let zoomMoveWorkerRunning = false;
  let galleryMoveQueue: Array<{ srcPaths: string[]; destPath: string }> = [];
  let galleryMoveWorkerRunning = false;
  let galleryDeleteQueue: Array<{ paths: string[] }> = [];
  let galleryDeleteWorkerRunning = false;
  let zoomHudVisible = false;
  let zoomHudTimer: ReturnType<typeof setTimeout> | null = null;
  let zoomStageEl: HTMLDivElement | null = null;
  let zoomCarouselEl: HTMLDivElement | null = null;
  let zoomImgEl: HTMLImageElement | null = null;
  let zoomVideoEl: HTMLVideoElement | null = null;
  let previewZoomMediaType: "image" | "video" | "svg" = "image";
  let previewZoomFileUrl: string | null = null;
  let previewZoomNaturalW = 1;
  let previewZoomNaturalH = 1;
  let zoomMiniEl: HTMLDivElement | null = null;
  let galleryGridEl: HTMLDivElement | null = null;
  let galleryScrollEl: HTMLDivElement | null = null;
  let galleryPlainEl: HTMLDivElement | null = null;
  let routePathEl: HTMLInputElement | null = null;
  let galleryGridObservedEl: HTMLDivElement | null = null;
  let galleryGridResizeObserver: ResizeObserver | null = null;
  let galleryGridWidth = 0;
  const GALLERY_GRID_EDGE_PAD_PX = 8;
  let zoomNavItems: Array<{
    path: string;
    name: string;
    thumbDataUrl?: string | null;
    thumbQuality?: "lq" | "hq";
    kind?: GalleryItem["kind"];
  }> = [];
  /** Modo edición fullscreen: rotación y recorte (persisten en disco vía backend). */
  let zoomEditMode = false;
  let zoomCropMode = false;
  let zoomCropDrag = false;
  let zoomCropStartX = 0;
  let zoomCropStartY = 0;
  let zoomCropCurX = 0;
  let zoomCropCurY = 0;
  let deferredZoomMoveRefresh: { state: any; items: GalleryItem[] } | null = null;
  let galleryThumbHydrationToken = 0;
  let galleryLoadingMore = false;
  let galleryHasMore = false;
  let galleryAutoLoadRunId = 0;
  let galleryScrollAtTop = true;
  let previewThumbHydrationToken = 0;
  let previewVisible = true;
  let previewDestPath = "";
  let destinationsMode = false;
  let folderBackStack: string[] = [];
  let folderForwardStack: string[] = [];
  /** Panel organizador en ventana flotante (tarea por lotes). */
  let orgPanelOpen = false;
  /** Menú Vista (subcarpetas, orden, futuro agrupar). */
  let viewMenuOpen = false;
  let includeSubfolders = false;
  let groupByFolder = false;
  /** Tinte de cabecera según color medio de imágenes (solo vista agrupada por carpeta). */
  let sectionDominantColor = true;
  /** Vista calendario: secciones por mes; marcas por día según zoom (solo cliente). */
  let timelineView = false;
  let gallerySortMode = "name,mtime,type";
  /** Resaltado al arrastrar sobre encabezado de sección (agrupar por carpeta). */
  let dragOverSectionPath: string | null = null;
  let settingsOpen = false;
  let thumbsPerPage = 48;
  let thumbsPerPageBackup = 48;
  let settingsThumbScaleDraft = 1;
  let thumbGapPx = 12;
  let showThumbLabels = true;
  let thumbCardStyle: "soft" | "flat" | "outlined" = "soft";
  let thumbFrameVisible = true;
  let thumbImageRadiusPx = 6;
  let thumbTileRadiusPx = 12;
  let thumbGapPxBackup = 12;
  let showThumbLabelsBackup = true;
  let thumbCardStyleBackup: "soft" | "flat" | "outlined" = "soft";
  let thumbFrameVisibleBackup = true;
  let thumbImageRadiusPxBackup = 6;
  let thumbTileRadiusPxBackup = 12;
  const defaultKeyboardShortcuts = {
    toggleMode: "Shift",
    deleteAction: "R",
    zoomPrev: "ArrowLeft,ArrowUp,A,W",
    zoomNext: "ArrowRight,ArrowDown,D,S",
    escape: "Escape",
  };
  let keyboardShortcuts = { ...defaultKeyboardShortcuts };
  let keyboardShortcutsBackup = { ...defaultKeyboardShortcuts };
  let uiTheme: UiThemeId = readCachedUiTheme();
  let uiThemeBackup: UiThemeId = "midnight";

  const themeNameLabel = (id: UiThemeId): string =>
    t(
      (
        {
          midnight: "settings.themeNames.midnight",
          ocean: "settings.themeNames.ocean",
          ember: "settings.themeNames.ember",
          forest: "settings.themeNames.forest",
          paper: "settings.themeNames.paper",
        } as const
      )[id]
    );
  const thumbScalePresets = [
    { id: "compacto", labelKey: "settings.thumbPresetCompact", value: 0.62 },
    { id: "medio", labelKey: "settings.thumbPresetMedium", value: 1.0 },
    { id: "comodo", labelKey: "settings.thumbPresetComfort", value: 1.18 },
    { id: "grande", labelKey: "settings.thumbPresetLarge", value: 1.45 },
    { id: "xgrande", labelKey: "settings.thumbPresetXL", value: 1.8 }
  ] as const;
  let settingsThumbPresetIdx = 1;
  let pageJumpDraft = 1;
  let previewRatio = 0.4;
  /** Fracción de altura para el panel inferior de destinos (solo pestaña Destinos). */
  let destPanelRatio = 0.26;
  let destSplitDrag = false;
  /** Modal “ver carpeta destino”: ~80 % del viewport (sin sliders). */
  const DEST_MODAL_FRAC = 0.8;
  let orgPath = "";
  let orgRunning = false;
  let orgDetail = t("status.orgDetailIdle");
  let orgProgress = "0/0";
  let orgOptions = {
    includeOrganized: false,
    includeComics: false,
    includePending: false,
    removeDuplicates: false,
    groupSimilarImages: false
  };

  /** Rutas recientes (persistidas en settings) para acceso rápido si el campo está vacío. */
  let recentFolders: string[] = [];
  /** Rutas ancladas (no se descartan del historial). */
  let pinnedFolders: string[] = [];
  let pinnedFolderLabels: Record<string, string> = {};
  $: recentUnpinnedFolders = recentFolders.filter((p) => !pinnedFolders.includes(p));
  let pinMarkerOpen = false;
  let pinMarkerName = "";
  let pinMarkerPath = "";

  let ghostVisible = false;
  let ghostX = 0;
  let ghostY = 0;
  let ghostThumb: string | null = null;
  let ghostCount = 1;
  let ghostCaption = "";
  /** Listeners globales durante HTML5 DnD (Qt WebEngine: document + capture). */
  let dragWinMove: ((ev: DragEvent) => void) | null = null;
  let dragWinEnd: (() => void) | null = null;
  /** Throttle: true mientras hay un rAF pendiente del dragWinMove. */
  let dragRafPending = false;

  let splitDrag = false;
  /** Contador para overlay de carga (carpetas, API, etc.). */
  let loadCount = 0;
  $: uiLoading = loadCount > 0;
  $: galleryHasMore = galleryHasMoreNow();

  function trackLoad<T>(promise: Promise<T>): Promise<T> {
    loadCount++;
    return promise.finally(() => {
      loadCount--;
    });
  }

  function galleryHasMoreNow(): boolean {
    if (thumbsPerPage !== 0) return false;
    return Number(galleryState?.endIndex ?? 0) < Number(galleryState?.total ?? 0);
  }

  /** Evita clics encolados mientras corre una operación de galería (Qt WebEngine + Python). */
  let galleryActionBusy = false;
  let thumbScaleDebounce: ReturnType<typeof setTimeout> | null = null;

  const isDevMock = () =>
    typeof import.meta !== "undefined" && Boolean((import.meta as any).env?.DEV) && !window.pywebview?.api;

  /** Qt/WebEngine inyecta la API un poco después del load; evita error get_initial_state. */
  async function waitForPywebviewApi(): Promise<void> {
    if (isDevMock()) return;
    const hasApi = () =>
      Boolean(
        (window as any).pywebview?.api &&
          typeof (window as any).pywebview.api.get_initial_state === "function"
      );
    if (hasApi()) return;
    await new Promise<void>((resolve, reject) => {
      const t0 = Date.now();
      const tryResolve = () => {
        if (hasApi()) {
          clearInterval(iv);
          window.removeEventListener("pywebviewready", onReady);
          resolve();
        } else if (Date.now() - t0 > 25000) {
          clearInterval(iv);
          window.removeEventListener("pywebviewready", onReady);
          reject(new Error("pywebview API no disponible a tiempo"));
        }
      };
      const onReady = () => tryResolve();
      window.addEventListener("pywebviewready", onReady);
      const iv = setInterval(tryResolve, 50);
    });
  }

  /** Destinos: la API puede devolverlos en la raíz, dentro de settings, o el payload puede ser el array. */
  function normalizeDestinationsFromPayload(data: any): Array<{ label: string; path: string }> {
    const raw = Array.isArray(data)
      ? data
      : (data?.destinations ?? data?.settings?.destinations);
    if (!Array.isArray(raw)) return [];
    const out: Array<{ label: string; path: string }> = [];
    for (const x of raw) {
      if (!x || typeof x !== "object") continue;
      const o = x as { path?: string; label?: string; folder?: string; dir?: string };
      const path = String(o.path ?? o.folder ?? o.dir ?? "").trim();
      if (!path) continue;
      const label = String(o.label ?? "").trim() || path;
      out.push({ label, path });
    }
    return out;
  }

  function normalizeShortcutValue(raw: unknown, fallback: string): string {
    const v = String(raw ?? "").trim();
    return v.length > 0 ? v : fallback;
  }

  function eventKeyToken(e: KeyboardEvent): string {
    const k = String(e.key ?? "").trim();
    if (k.length === 1) return k.toLowerCase();
    return k;
  }

  function shortcutMatchesSingle(e: KeyboardEvent, binding: string): boolean {
    const token = eventKeyToken(e);
    const want = normalizeShortcutValue(binding, "").trim();
    return token === want || token.toLowerCase() === want.toLowerCase();
  }

  function shortcutMatchesList(e: KeyboardEvent, bindingsCsv: string): boolean {
    const token = eventKeyToken(e);
    const opts = String(bindingsCsv ?? "")
      .split(",")
      .map((x) => x.trim())
      .filter((x) => x.length > 0);
    return opts.some((x) => token === x || token.toLowerCase() === x.toLowerCase());
  }

  function isGalleryMediaKind(kind: GalleryItem["kind"]): boolean {
    return kind === "image" || kind === "video";
  }

  function mergeItemsKeepingBestThumb(prevItems: GalleryItem[], nextItems: GalleryItem[]): GalleryItem[] {
    const prevByPath = new Map(prevItems.map((x) => [x.path, x] as const));
    return nextItems.map((it) => {
      if (!isGalleryMediaKind(it.kind)) return it;
      const prev = prevByPath.get(it.path);
      if (!prev || !isGalleryMediaKind(prev.kind)) return it;
      const prevQ = prev.thumbQuality ?? (prev.thumbDataUrl ? "hq" : undefined);
      const nextQ = it.thumbQuality ?? (it.thumbDataUrl ? "hq" : undefined);
      const prevScore = prevQ === "hq" ? 2 : prevQ === "lq" ? 1 : 0;
      const nextScore = nextQ === "hq" ? 2 : nextQ === "lq" ? 1 : 0;
      if (prevScore > nextScore && prev.thumbDataUrl) {
        return { ...it, thumbDataUrl: prev.thumbDataUrl, thumbQuality: prev.thumbQuality ?? "hq" };
      }
      return it;
    });
  }

  function prioritizePathsByViewport(paths: string[], selector: string, attrName: string): string[] {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(selector));
    if (nodes.length === 0) return paths;
    const nodeByPath = new Map<string, HTMLElement>();
    for (const n of nodes) {
      const p = n.dataset[attrName];
      if (p) nodeByPath.set(p, n);
    }
    const visible: string[] = [];
    const rest: string[] = [];
    for (const p of paths) {
      const el = nodeByPath.get(p);
      if (!el) {
        rest.push(p);
        continue;
      }
      const r = el.getBoundingClientRect();
      const isVisible = r.bottom > 0 && r.right > 0 && r.top < window.innerHeight && r.left < window.innerWidth;
      (isVisible ? visible : rest).push(p);
    }
    return [...visible, ...rest];
  }

  async function hydrateGalleryThumbsHq(snapshot: GalleryItem[], scale: number, token: number) {
    const base = snapshot.filter((x) => x.kind === "image" || x.kind === "video");
    const orderedPaths = prioritizePathsByViewport(
      base.map((x) => x.path),
      ".tile[data-item-path]",
      "itemPath"
    );
    const targets = orderedPaths
      .map((p) => base.find((x) => x.path === p))
      .filter((x): x is GalleryItem => Boolean(x));
    let idx = 0;
    const workers = Array.from({ length: 4 }, async () => {
      while (idx < targets.length) {
        const cur = idx++;
        const it = targets[cur];
        try {
          const out = await bridge.galleryThumbHq(it.path, scale);
          if (galleryThumbHydrationToken !== token) return;
          if (!out?.thumbDataUrl) continue;
          items = items.map((x) =>
            (x.kind === "image" || x.kind === "video") && x.path === it.path
              ? { ...x, thumbDataUrl: out.thumbDataUrl, thumbQuality: "hq" }
              : x
          );
        } catch {
          /* ignore: se queda LQ */
        }
      }
    });
    await Promise.all(workers);
  }

  async function hydratePreviewThumbsHq(
    snapshot: Array<{ name: string; path: string; thumbDataUrl?: string | null }>,
    scale: number,
    token: number
  ) {
    const orderedPaths = prioritizePathsByViewport(
      snapshot.map((x) => x.path),
      ".pv-tile[data-preview-path]",
      "previewPath"
    );
    const targets = orderedPaths
      .map((p) => snapshot.find((x) => x.path === p))
      .filter((x): x is { name: string; path: string; thumbDataUrl?: string | null } => Boolean(x));
    let idx = 0;
    const workers = Array.from({ length: 4 }, async () => {
      while (idx < targets.length) {
        const cur = idx++;
        const it = targets[cur];
        try {
          const out = await bridge.destinationThumbHq(it.path, scale);
          if (previewThumbHydrationToken !== token) return;
          if (!out?.thumbDataUrl) continue;
          previewItems = previewItems.map((x) =>
            x.path === it.path ? { ...x, thumbDataUrl: out.thumbDataUrl, thumbQuality: "hq" } : x
          );
          if (
            previewZoomOpen &&
            previewZoomPath === it.path &&
            previewZoomMediaType !== "video" &&
            previewZoomMediaType !== "svg"
          )
            previewZoomDataUrl = out.thumbDataUrl;
        } catch {
          /* ignore: se queda LQ */
        }
      }
    });
    await Promise.all(workers);
  }

  /** Prioriza destinations_get (payload pequeño); get_initial_state a veces falla el parse en Qt. */
  async function syncDestinationsFromApi() {
    try {
      const d = await bridge.destinationsGet();
      destRows = normalizeDestinationsFromPayload(d);
    } catch {
      try {
        const data = await bridge.getInitialState();
        destRows = normalizeDestinationsFromPayload(data);
      } catch {
        destRows = [];
      }
    }
  }

  async function refreshDestinationsFromServer() {
    await syncDestinationsFromApi();
  }

  const loadInitial = async () => {
    const data = await trackLoad(bridge.getInitialState());
    thumbScale = Number(data.settings?.gallery_thumb_scale ?? 1);
    thumbGapPx = Math.max(0, Math.min(20, Number(data.settings?.web_thumb_gap_px ?? 12)));
    showThumbLabels = Boolean(data.settings?.web_show_thumb_labels ?? true);
    {
      const style = String(data.settings?.web_thumb_card_style ?? "soft");
      thumbCardStyle = style === "flat" || style === "outlined" ? style : "soft";
    }
    thumbFrameVisible = Boolean(data.settings?.web_thumb_frame_visible ?? true);
    thumbImageRadiusPx = Math.max(0, Math.min(18, Number(data.settings?.web_thumb_image_radius_px ?? 6)));
    thumbTileRadiusPx = Math.max(0, Math.min(28, Number(data.settings?.web_thumb_tile_radius_px ?? 12)));
    const persistedShortcuts = (data.settings?.web_shortcuts ?? {}) as Record<string, unknown>;
    keyboardShortcuts = {
      toggleMode: normalizeShortcutValue(persistedShortcuts?.toggleMode, defaultKeyboardShortcuts.toggleMode),
      deleteAction: normalizeShortcutValue(persistedShortcuts?.deleteAction, defaultKeyboardShortcuts.deleteAction),
      zoomPrev: normalizeShortcutValue(persistedShortcuts?.zoomPrev, defaultKeyboardShortcuts.zoomPrev),
      zoomNext: normalizeShortcutValue(persistedShortcuts?.zoomNext, defaultKeyboardShortcuts.zoomNext),
      escape: normalizeShortcutValue(persistedShortcuts?.escape, defaultKeyboardShortcuts.escape),
    };
    uiTheme = normalizeUiTheme(data.settings?.web_ui_theme);
    previewVisible = Boolean(data.settings?.web_preview_visible ?? true);
    previewRatio = Math.min(0.68, Math.max(0.14, Number(data.settings?.web_preview_ratio ?? 0.4)));
    destPanelRatio = Math.min(0.55, Math.max(0.12, Number(data.settings?.web_dest_panel_ratio ?? 0.26)));
    const last = (data.settings?.gallery_last_folder ?? "").trim();
    folder = (data.gallery?.folder ?? last) || "";
    orgPath = folder || orgPath;
    galleryState = data.gallery ?? galleryState;
    recentFolders = Array.isArray(data.settings?.gallery_recent_folders)
      ? (data.settings.gallery_recent_folders as string[])
      : [];
    pinnedFolders = Array.isArray(data.settings?.gallery_pinned_folders)
      ? (data.settings.gallery_pinned_folders as string[])
      : [];
    pinnedFolderLabels = typeof data.settings?.web_pinned_folder_labels === "object" && data.settings?.web_pinned_folder_labels
      ? (data.settings.web_pinned_folder_labels as Record<string, string>)
      : {};
    const initialPerPage = Number(data.settings?.gallery_thumbs_per_page ?? 48);
    const perPageRaw = Number.isFinite(initialPerPage) ? Math.round(initialPerPage) : 48;
    thumbsPerPage = perPageRaw <= 0 ? 0 : Math.max(12, perPageRaw);
    pageJumpDraft = Number(data.gallery?.page ?? 1);
    includeSubfolders = Boolean(data.settings?.gallery_include_subfolders ?? false);
    groupByFolder = Boolean(data.settings?.gallery_group_by_folder ?? false);
    sectionDominantColor = Boolean(data.settings?.gallery_section_dominant_color ?? true);
    timelineView = Boolean(data.settings?.gallery_timeline_view ?? false);
    gallerySortMode = String(data.settings?.gallery_sort_mode ?? "name,mtime,type");
    await syncDestinationsFromApi();
  };

  $: applyUiThemeToDocument(uiTheme);

  async function persistViewAndReload() {
    try {
      await trackLoad(
        bridge.settingsPatch({
          gallery_include_subfolders: includeSubfolders,
          gallery_sort_mode: gallerySortMode,
          gallery_group_by_folder: groupByFolder,
          gallery_timeline_view: timelineView,
          gallery_section_dominant_color: sectionDominantColor,
        })
      );
      await reload();
      status = t("status.viewUpdated");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.viewApplyError");
    }
  }

  async function onIncludeSubfoldersChange(checked: boolean) {
    includeSubfolders = checked;
    if (checked) groupByFolder = false;
    await persistViewAndReload();
  }

  async function onGroupByFolderChange(checked: boolean) {
    groupByFolder = checked;
    if (checked) {
      includeSubfolders = false;
      timelineView = false;
    }
    await persistViewAndReload();
  }

  async function onSectionDominantColorChange(checked: boolean) {
    sectionDominantColor = checked;
    await persistViewAndReload();
  }

  async function onTimelineViewChange(checked: boolean) {
    timelineView = checked;
    if (checked) {
      groupByFolder = false;
      // La línea de tiempo requiere que la fecha (mtime) sea la prioridad más alta.
      // Reordenamos para colocar 'mtime' al inicio.
      const currentParts = gallerySortMode.split(",").map(p => p.trim());
      const filtered = currentParts.filter(p => p !== "mtime");
      gallerySortMode = ["mtime", ...filtered].join(",");
    }
    await persistViewAndReload();
  }

  async function onGallerySortChange(mode: string) {
    gallerySortMode = mode;
    // Si la fecha ('mtime') no está en la primera prioridad y la línea de tiempo está activa, desactivarla.
    const primarySort = mode.split(",")[0]?.trim();
    if (primarySort !== "mtime" && timelineView) {
      timelineView = false;
    }
    await persistViewAndReload();
  }

  async function navigateToFolder(path: string, opts?: { pushHistory?: boolean }) {
    closeGalleryItemCtxMenu();
    const target = path.trim();
    if (!target) return;
    const current = String(galleryState?.folder ?? folder ?? "").trim();
    if (opts?.pushHistory !== false && current && current !== target) {
      folderBackStack = [...folderBackStack, current];
      folderForwardStack = [];
    }
    const out = await trackLoad(bridge.galleryLoadFolder(target));
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    if (thumbsPerPage === 0) {
      await tick();
      void maybeAutoLoadMoreForViewport();
      void autoLoadUnlimitedBatches();
    }
    if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
    pageJumpDraft = out.state.page;
    folder = out.state?.folder ?? target;
    orgPath = folder || orgPath;
    status = t("status.folderLoaded").replace("{path}", folder);
  }

  const loadFolder = async (closePicker = true) => {
    await navigateToFolder(folder, { pushHistory: true });
    if (closePicker) routePickerOpen = false;
  };

  const pickRecentFolder = async (path: string) => {
    folder = path;
    await navigateToFolder(path, { pushHistory: true });
    routePickerOpen = false;
  };

  function getParentFolder(rawPath: string): string {
    const p = rawPath.replace(/\\/g, "/").replace(/\/+$/, "");
    const i = p.lastIndexOf("/");
    if (i <= 0) return p;
    return p.slice(0, i);
  }

  async function goBackFolder() {
    if (folderBackStack.length === 0) return;
    const current = String(galleryState?.folder ?? folder ?? "").trim();
    const target = folderBackStack[folderBackStack.length - 1];
    folderBackStack = folderBackStack.slice(0, -1);
    if (current && current !== target) folderForwardStack = [...folderForwardStack, current];
    await navigateToFolder(target, { pushHistory: false });
  }

  async function goForwardFolder() {
    if (folderForwardStack.length === 0) return;
    const current = String(galleryState?.folder ?? folder ?? "").trim();
    const target = folderForwardStack[folderForwardStack.length - 1];
    folderForwardStack = folderForwardStack.slice(0, -1);
    if (current && current !== target) folderBackStack = [...folderBackStack, current];
    await navigateToFolder(target, { pushHistory: false });
  }

  async function goUpFolder() {
    const current = String(galleryState?.folder ?? folder ?? "").trim();
    if (!current) return;
    const parent = getParentFolder(current);
    if (!parent || parent === current) return;
    await navigateToFolder(parent, { pushHistory: true });
  }

  const pinFolder = async (path: string) => {
    try {
      const out = await bridge.galleryPinFolder(path);
      pinnedFolders = Array.isArray(out.pinnedFolders) ? out.pinnedFolders : pinnedFolders;
      status = t("status.routePinned");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.routePinError");
    }
  };

  const unpinFolder = async (path: string) => {
    try {
      const out = await bridge.galleryUnpinFolder(path);
      pinnedFolders = Array.isArray(out.pinnedFolders) ? out.pinnedFolders : pinnedFolders.filter((x) => x !== path);
      if (pinnedFolderLabels[path]) {
        const next = { ...pinnedFolderLabels };
        delete next[path];
        pinnedFolderLabels = next;
        await bridge.settingsPatch({ web_pinned_folder_labels: next });
      }
      status = t("status.routeUnpinned");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.routeUnpinError");
    }
  };

  const pickGalleryFolder = async () => {
    try {
      const out = await bridge.dialogPickFolder(folder);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      folder = out.path;
      await loadFolder();
      routePickerOpen = false;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.folderPickerError");
    }
  };

  const pickOrgFolder = async () => {
    try {
      const out = await bridge.dialogPickFolder(orgPath);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      orgPath = out.path;
      status = t("status.orgPathSet").replace("{path}", orgPath);
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.folderPickerError");
    }
  };

  /** Recarga ítems de la galería. `silent`: no muestra overlay (p. ej. tras mover el slider de miniaturas). */
  const reload = async (opts?: { silent?: boolean }) => {
    const p = bridge.galleryReload();
    const out = opts?.silent ? await p : await trackLoad(p);
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    if (thumbsPerPage === 0) {
      await tick();
      void maybeAutoLoadMoreForViewport();
      void autoLoadUnlimitedBatches();
    }
  };

  const goPage = async (page: number) => {
    const out = await trackLoad(bridge.galleryGoPage(page));
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    pageJumpDraft = out.state.page;
  };

  async function onGalleryScroll(e: Event) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    galleryScrollAtTop = el.scrollTop <= 2;
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 280;
    if (!nearBottom) return;
    await loadMoreGalleryBatch();
  }

  async function loadMoreGalleryBatch() {
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return false;
    galleryLoadingMore = true;
    try {
      const beforeEnd = Number(galleryState?.endIndex ?? 0);
      const out = await bridge.galleryLoadMore();
      if (out?.state) galleryState = out.state;
      const extra = Array.isArray(out?.items) ? out.items : [];
      if (extra.length > 0) {
        items = [...items, ...extra];
        // No incrementar token: evita cancelar hidración HQ en curso de tandas previas.
        void hydrateGalleryThumbsHq(extra, thumbScale, galleryThumbHydrationToken);
      }
      const afterEnd = Number(galleryState?.endIndex ?? 0);
      return afterEnd > beforeEnd || extra.length > 0;
    } finally {
      galleryLoadingMore = false;
    }
  }

  async function maybeAutoLoadMoreForViewport() {
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    const el = galleryScrollEl ?? galleryPlainEl;
    if (!el) return;
    // Si aún no hay suficiente contenido para scrollear, precarga otra tanda.
    if (el.scrollHeight <= el.clientHeight + 40) {
      await loadMoreGalleryBatch();
    }
  }

  async function autoLoadUnlimitedBatches() {
    const runId = ++galleryAutoLoadRunId;
    let guard = 0;
    while (runId === galleryAutoLoadRunId && thumbsPerPage === 0 && galleryHasMoreNow() && guard < 200) {
      guard++;
      const progressed = await loadMoreGalleryBatch();
      await tick();
      if (!progressed) break;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }

  $: if (thumbsPerPage === 0 && galleryHasMoreNow() && !galleryLoadingMore && items.length > 0 && (galleryScrollEl || galleryPlainEl)) {
    setTimeout(() => {
      void maybeAutoLoadMoreForViewport();
    }, 0);
  }

  const jumpToPageDraft = async () => {
    const n = Math.min(galleryState.totalPages, Math.max(1, Math.round(Number(pageJumpDraft)) || 1));
    pageJumpDraft = n;
    await goPage(n);
  };

  const openSettingsModal = () => {
    uiThemeBackup = uiTheme;
    thumbsPerPageBackup = thumbsPerPage;
    thumbGapPxBackup = thumbGapPx;
    showThumbLabelsBackup = showThumbLabels;
    thumbCardStyleBackup = thumbCardStyle;
    thumbFrameVisibleBackup = thumbFrameVisible;
    thumbImageRadiusPxBackup = thumbImageRadiusPx;
    thumbTileRadiusPxBackup = thumbTileRadiusPx;
    keyboardShortcutsBackup = { ...keyboardShortcuts };
    settingsThumbScaleDraft = thumbScale;
    let bestIdx = 0;
    let bestDiff = Number.POSITIVE_INFINITY;
    for (let i = 0; i < thumbScalePresets.length; i++) {
      const d = Math.abs(thumbScalePresets[i].value - settingsThumbScaleDraft);
      if (d < bestDiff) {
        bestDiff = d;
        bestIdx = i;
      }
    }
    settingsThumbPresetIdx = bestIdx;
    settingsOpen = true;
  };

  const cancelSettingsModal = () => {
    uiTheme = uiThemeBackup;
    thumbsPerPage = thumbsPerPageBackup;
    thumbGapPx = thumbGapPxBackup;
    showThumbLabels = showThumbLabelsBackup;
    thumbCardStyle = thumbCardStyleBackup;
    thumbFrameVisible = thumbFrameVisibleBackup;
    thumbImageRadiusPx = thumbImageRadiusPxBackup;
    thumbTileRadiusPx = thumbTileRadiusPxBackup;
    keyboardShortcuts = { ...keyboardShortcutsBackup };
    settingsOpen = false;
  };

  const saveSettingsModal = async () => {
    const parsedPerPage = Number(thumbsPerPage);
    const perPageRaw = Number.isFinite(parsedPerPage) ? Math.round(parsedPerPage) : 48;
    const n = perPageRaw <= 0 ? 0 : Math.max(12, perPageRaw);
    thumbsPerPage = n;
    const ts = Math.max(0.01, Math.min(2.25, Number(settingsThumbScaleDraft) || 1));
    thumbScale = ts;
    keyboardShortcuts = {
      toggleMode: normalizeShortcutValue(keyboardShortcuts.toggleMode, defaultKeyboardShortcuts.toggleMode),
      deleteAction: normalizeShortcutValue(keyboardShortcuts.deleteAction, defaultKeyboardShortcuts.deleteAction),
      zoomPrev: normalizeShortcutValue(keyboardShortcuts.zoomPrev, defaultKeyboardShortcuts.zoomPrev),
      zoomNext: normalizeShortcutValue(keyboardShortcuts.zoomNext, defaultKeyboardShortcuts.zoomNext),
      escape: normalizeShortcutValue(keyboardShortcuts.escape, defaultKeyboardShortcuts.escape),
    };
    await bridge.settingsPatch({
      gallery_thumbs_per_page: n, // 0 = sin límite
      gallery_thumb_scale: Number(ts.toFixed(3)),
      web_ui_theme: uiTheme,
      web_thumb_gap_px: Math.max(0, Math.round(thumbGapPx)),
      web_show_thumb_labels: Boolean(showThumbLabels),
      web_thumb_card_style: thumbCardStyle,
      web_thumb_frame_visible: Boolean(thumbFrameVisible),
      web_thumb_image_radius_px: Math.round(thumbImageRadiusPx),
      web_thumb_tile_radius_px: Math.round(thumbTileRadiusPx),
      web_shortcuts: { ...keyboardShortcuts },
    });
    await reload();
    settingsOpen = false;
  };

  function openConfirmDelete(
    title: string,
    detail: string,
    action: () => Promise<void>,
    opts?: {
      confirmLabel?: string;
      bypassEnabled?: boolean;
      bypassLabel?: string;
      bypassSetter?: (enabled: boolean) => void;
    }
  ) {
    confirmDeleteTitle = title;
    confirmDeleteDetail = detail;
    confirmDeleteConfirmLabel = opts?.confirmLabel ?? t("common.delete");
    confirmDeleteBypassEnabled = Boolean(opts?.bypassEnabled);
    confirmDeleteBypassLabel = opts?.bypassLabel ?? t("confirm.bypassOnce");
    confirmDeleteBypassChecked = false;
    confirmDeleteBypassSetter = opts?.bypassSetter ?? null;
    confirmDeleteAction = action;
    confirmDeleteOpen = true;
  }

  function closeConfirmDelete() {
    confirmDeleteOpen = false;
    confirmDeleteAction = null;
    confirmDeleteBypassEnabled = false;
    confirmDeleteBypassChecked = false;
    confirmDeleteBypassSetter = null;
  }

  async function runConfirmDelete() {
    if (!confirmDeleteAction) return;
    if (confirmDeleteBypassEnabled && confirmDeleteBypassChecked && confirmDeleteBypassSetter) {
      confirmDeleteBypassSetter(true);
    }
    const fn = confirmDeleteAction;
    closeConfirmDelete();
    await fn();
  }

  async function deleteSelectedGalleryItems() {
    const selectedPaths = items
      .filter((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected))
      .map((x) => x.path);
    if (selectedPaths.length === 0) return;
    const selectedSet = new Set(selectedPaths);
    items = items.filter((x) => !(isGalleryMediaKind(x.kind) && selectedSet.has(x.path)));
    galleryState = {
      ...galleryState,
      total: Math.max(0, Number(galleryState?.total ?? 0) - selectedPaths.length),
      selectedCount: 0,
      endIndex: Math.max(0, Number(galleryState?.endIndex ?? 0) - selectedPaths.length),
    };
    enqueueDeletePaths(selectedPaths);
    status = t("status.deleteQueued").replace("{n}", String(selectedPaths.length));
  }

  async function deleteCurrentZoomImage() {
    if (!previewZoomPath) return;
    const curPath = previewZoomPath;
    const curIdx = zoomNavItems.findIndex((x) => x.path === curPath);
    const remainingNav = zoomNavItems.filter((x) => x.path !== curPath);
    items = items.filter((x) => !(isGalleryMediaKind(x.kind) && x.path === curPath));
    if (remainingNav.length > 0) {
      const nextIdx = curIdx >= 0 ? Math.min(curIdx, remainingNav.length - 1) : 0;
      const nextItem = remainingNav[nextIdx];
      zoomNavItems = remainingNav;
      if (nextItem) openPreviewZoom(nextItem, { preserveCarousel: true, preserveMode: true, navItems: remainingNav });
    } else {
      previewZoomOpen = false;
    }
    enqueueDeletePaths([curPath]);
    status = t("status.deleteImageQueued");
  }

  const clickItem = async (it: GalleryItem) => {
    if (suppressNextGalleryClick) {
      suppressNextGalleryClick = false;
      return;
    }
    galleryKeyboardNavHintActive = false;
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
      if (it.kind === "section") {
        return;
      }
      if (it.kind === "day_break") {
        return;
      }
      if (it.kind === "folder" || it.kind === "folder_up") {
        await navigateToFolder(it.path, { pushHistory: true });
        return;
      }
      if (destinationsMode) {
        const out = await bridge.galleryToggleSelect(it.path);
        galleryState = out.state;
        items = mergeItemsKeepingBestThumb(items, out.items);
        const row = out.items?.find((x: GalleryItem) => x.path === it.path);
        selectedPreview = {
          path: it.path,
          name: it.name,
          dataUrl: row?.thumbDataUrl ?? null
        };
        const pathRef = it.path;
        requestAnimationFrame(() => {
          bridge
            .galleryPreview(pathRef, 1200, 900)
            .then((pr) => {
              selectedPreview = pr;
            })
            .catch(() => undefined);
        });
        galleryCursorPath = it.path;
      } else {
        if (!previewVisible && isGalleryMediaKind(it.kind)) {
          openZoomFromGallery(it);
          return;
        }
        selectedPreview = {
          path: it.path,
          name: it.name,
          dataUrl: it.thumbDataUrl ?? null
        };
        const pathRef = it.path;
        requestAnimationFrame(() => {
          bridge
            .galleryPreview(pathRef, 1200, 900)
            .then((pr) => {
              selectedPreview = pr;
            })
            .catch(() => undefined);
        });
        galleryCursorPath = it.path;
      }
    } finally {
      galleryActionBusy = false;
    }
  };

  function setSelectedPreviewFromPath(path: string | null | undefined) {
    const p = String(path ?? "").trim();
    if (!p) return;
    const row = items.find((x) => isGalleryMediaKind(x.kind) && x.path === p) as GalleryItem | undefined;
    if (!row) return;
    selectedPreview = {
      path: row.path,
      name: row.name,
      dataUrl: row.thumbDataUrl ?? null,
    };
    requestAnimationFrame(() => {
      bridge
        .galleryPreview(row.path, 1200, 900)
        .then((pr) => {
          selectedPreview = pr;
        })
        .catch(() => undefined);
    });
  }

  function getGalleryNavigablePaths(): string[] {
    return items.filter((x) => isGalleryMediaKind(x.kind)).map((x) => x.path);
  }

  function getOrInitGalleryCursorPath(): string | null {
    const paths = getGalleryNavigablePaths();
    if (paths.length === 0) return null;
    if (galleryCursorPath && paths.includes(galleryCursorPath)) return galleryCursorPath;
    galleryCursorPath = paths[0];
    return galleryCursorPath;
  }

  function getGalleryLayoutRows(): Array<Array<{ path: string; cx: number; top: number }>> {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(".tile[data-item-path]"))
      .map((el) => {
        const path = String(el.dataset?.itemPath ?? "");
        if (!path) return null;
        const it = items.find((x) => x.path === path);
        if (!it || !isGalleryMediaKind(it.kind)) return null;
        const r = el.getBoundingClientRect();
        return { path, cx: r.left + r.width / 2, top: Math.round(r.top) };
      })
      .filter((x): x is { path: string; cx: number; top: number } => Boolean(x));
    if (nodes.length === 0) return [];
    const sorted = [...nodes].sort((a, b) => (a.top - b.top) || (a.cx - b.cx));
    const rows: Array<Array<{ path: string; cx: number; top: number }>> = [];
    const rowThreshold = 8;
    for (const n of sorted) {
      const last = rows[rows.length - 1];
      if (!last) {
        rows.push([n]);
        continue;
      }
      const rowTop = last[0]?.top ?? n.top;
      if (Math.abs(n.top - rowTop) <= rowThreshold) last.push(n);
      else rows.push([n]);
    }
    for (const r of rows) r.sort((a, b) => a.cx - b.cx);
    return rows;
  }

  function moveGalleryCursorByKey(keyLower: string): string | null {
    const paths = getGalleryNavigablePaths();
    if (paths.length === 0) return null;
    const cur = getOrInitGalleryCursorPath();
    if (!cur) return null;
    const idx = Math.max(0, paths.indexOf(cur));
    if (keyLower === "arrowright" || keyLower === "d") return paths[Math.min(paths.length - 1, idx + 1)];
    if (keyLower === "arrowleft" || keyLower === "a") return paths[Math.max(0, idx - 1)];
    const rows = getGalleryLayoutRows();
    if (rows.length === 0) return cur;
    let rIdx = -1;
    let cX = 0;
    for (let r = 0; r < rows.length; r++) {
      const found = rows[r].find((x) => x.path === cur);
      if (found) {
        rIdx = r;
        cX = found.cx;
        break;
      }
    }
    if (rIdx < 0) return cur;
    if (keyLower === "arrowdown" || keyLower === "s") {
      const nextRow = rows[Math.min(rows.length - 1, rIdx + 1)];
      const pick = nextRow.reduce((best, x) =>
        Math.abs(x.cx - cX) < Math.abs(best.cx - cX) ? x : best
      , nextRow[0]);
      return pick?.path ?? cur;
    }
    if (keyLower === "arrowup" || keyLower === "w") {
      const prevRow = rows[Math.max(0, rIdx - 1)];
      const pick = prevRow.reduce((best, x) =>
        Math.abs(x.cx - cX) < Math.abs(best.cx - cX) ? x : best
      , prevRow[0]);
      return pick?.path ?? cur;
    }
    return cur;
  }

  function scrollGalleryCursorIntoView(path: string) {
    requestAnimationFrame(() => {
      const tiles = Array.from(document.querySelectorAll<HTMLElement>(".tile[data-item-path]"));
      const tile = tiles.find((el) => String(el.dataset?.itemPath ?? "") === path);
      tile?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "auto" });
    });
  }

  async function toggleGalleryCursorSelection(path: string) {
    const prevItems = items;
    const out = await bridge.galleryToggleSelect(path);
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
    setSelectedPreviewFromPath(path);
  }

  async function applyGalleryKeyboardRangeSelection(anchorPath: string, toPath: string) {
    const imagePaths = getGalleryNavigablePaths();
    const a = imagePaths.indexOf(anchorPath);
    const b = imagePaths.indexOf(toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const target = new Set<string>();
    for (let i = lo; i <= hi; i++) target.add(imagePaths[i]);
    const current = new Set(items.filter((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected)).map((x) => x.path));
    const addPaths = [...target].filter((p) => !current.has(p));
    if (addPaths.length === 0) return;
    const prevItems = items;
    const out = await bridge.galleryApplySelectionDelta(addPaths, []);
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
  }

  const selectPage = async () => {
    const prevItems = items;
    const out = await bridge.gallerySelectPage();
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
    if (destinationsMode) {
      const last = [...items].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
      setSelectedPreviewFromPath(last?.path);
    }
  };
  const clearSelection = async () => {
    const prevItems = items;
    const out = await bridge.galleryClearSelection();
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
  };
  const invertSelection = async () => {
    const prevItems = items;
    const out = await bridge.galleryInvertSelection();
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
    if (destinationsMode) {
      const last = [...items].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
      setSelectedPreviewFromPath(last?.path);
    }
  };

  async function processGalleryMoveQueue() {
    if (galleryMoveWorkerRunning) return;
    galleryMoveWorkerRunning = true;
    try {
      while (galleryMoveQueue.length > 0) {
        const [job, ...rest] = galleryMoveQueue;
        galleryMoveQueue = rest;
        try {
          const out = await bridge.destinationMovePaths(job.srcPaths, job.destPath);
          galleryState = out.state;
          items = mergeItemsKeepingBestThumb(items, out.items);
          galleryThumbHydrationToken++;
          void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
          status = t("status.moveBatchLine")
            .replace("{moved}", String(out.moveResult?.moved ?? 0))
            .replace("{errors}", String(out.moveResult?.errors ?? 0))
            .replace("{queue}", String(galleryMoveQueue.length));
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : t("status.moveQueueError");
        }
      }
    } finally {
      galleryMoveWorkerRunning = false;
    }
  }

  function getSelectedGalleryPaths(): string[] {
    return items.filter((x) => isGalleryMediaKind(x.kind) && x.selected).map((x) => x.path);
  }

  function askConfirmMoveSelected(destPath: string) {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    openConfirmDelete(
      t("confirm.moveSelectionTitle"),
      t("confirm.moveSelectionDetail").replace("{count}", String(selectedPaths.length)),
      async () => {
        await moveToDest(destPath);
      },
      { confirmLabel: t("common.move") }
    );
  }

  const moveToDest = async (path: string) => {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    const selectedSet = new Set(selectedPaths);
    items = items.map((it) =>
      isGalleryMediaKind(it.kind) && selectedSet.has(it.path) ? { ...it, selected: false } : it
    );
    galleryState = {
      ...galleryState,
      selectedCount: Math.max(0, Number(galleryState?.selectedCount ?? 0) - selectedPaths.length),
    };
    galleryMoveQueue = [...galleryMoveQueue, { srcPaths: selectedPaths, destPath: path }];
    status = t("status.imagesEnqueued")
      .replace("{n}", String(selectedPaths.length))
      .replace("{queue}", String(galleryMoveQueue.length));
    if (!galleryMoveWorkerRunning) {
      void processGalleryMoveQueue();
    }
  };

  const savePreviewRatio = async () => {
    await bridge.settingsPatch({ web_preview_ratio: Number(previewRatio.toFixed(3)) });
  };

  const saveDestPanelRatio = async () => {
    await bridge.settingsPatch({ web_dest_panel_ratio: Number(destPanelRatio.toFixed(3)) });
  };

  function updateDestPanelFromClientY(clientY: number) {
    const el = document.querySelector(".destinos-work");
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const h = rect.height;
    if (h <= 16) return;
    const fromBottom = (rect.bottom - clientY) / h;
    destPanelRatio = Math.min(0.55, Math.max(0.12, fromBottom));
  }

  function beginDestPanelDrag(e: PointerEvent) {
    e.preventDefault();
    destSplitDrag = true;
    const bar = e.currentTarget as HTMLElement;
    bar.setPointerCapture?.(e.pointerId);
    const move = (ev: PointerEvent) => {
      if (!destSplitDrag) return;
      updateDestPanelFromClientY(ev.clientY);
    };
    const up = (ev: PointerEvent) => {
      destSplitDrag = false;
      bar.releasePointerCapture?.(ev.pointerId);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      saveDestPanelRatio().catch(() => undefined);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  }

  /** Números de página estilo resultados (mínimo 5 visibles + extremos). */
  function googlePageItems(page: number, totalPages: number): Array<number | "gap"> {
    if (totalPages <= 1) return totalPages === 1 ? [1] : [];
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    if (page <= 4) return [1, 2, 3, 4, 5, "gap", totalPages];
    if (page >= totalPages - 3) return [1, "gap", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
    return [1, "gap", page - 2, page - 1, page, page + 1, page + 2, "gap", totalPages];
  }

  function formatBytes(size: number): string {
    const n = Math.max(0, Number(size) || 0);
    if (n < 1024) return `${n} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let v = n / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(v >= 100 ? 0 : v >= 10 ? 1 : 2)} ${units[i]}`;
  }

  $: pageLinks = googlePageItems(Number(galleryState.page) || 1, Number(galleryState.totalPages) || 1);

  function updateSplitFromClientX(clientX: number) {
    const el = document.querySelector(".content");
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const w = rect.width;
    if (w <= 1) return;
    let r = (rect.right - clientX) / w;
    r = Math.min(0.68, Math.max(0.14, r));
    previewRatio = Math.round(r * 1000) / 1000;
  }

  function beginSplitDrag(e: PointerEvent) {
    e.preventDefault();
    splitDrag = true;
    const move = (ev: PointerEvent) => {
      if (!splitDrag) return;
      updateSplitFromClientX(ev.clientX);
    };
    const up = () => {
      splitDrag = false;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      savePreviewRatio().catch(() => undefined);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  }

  function scheduleThumbScaleReload() {
    if (thumbScaleDebounce) clearTimeout(thumbScaleDebounce);
    thumbScaleDebounce = setTimeout(() => {
      thumbScaleDebounce = null;
      applyThumbScaleNow();
    }, 160);
  }

  async function applyThumbScaleNow() {
    try {
      await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
      await reload({ silent: true });
    } catch {
      status = t("status.thumbScaleError");
    }
  }

  async function togglePreviewVisible() {
    previewVisible = !previewVisible;
    try {
      await bridge.settingsPatch({ web_preview_visible: Boolean(previewVisible) });
    } catch {
      // ignore persist error; estado local se mantiene
    }
  }

  function flushThumbScaleOnRelease() {
    if (thumbScaleDebounce) {
      clearTimeout(thumbScaleDebounce);
      thumbScaleDebounce = null;
    }
    applyThumbScaleNow();
  }

  function keepRoutePathEndVisible() {
    if (!routePathEl) return;
    if (document.activeElement === routePathEl) return;
    requestAnimationFrame(() => {
      if (!routePathEl) return;
      routePathEl.scrollLeft = routePathEl.scrollWidth;
    });
  }

  function pathTailLabel(path: string, max = 56): string {
    const p = String(path ?? "");
    if (p.length <= max) return p;
    return `…${p.slice(-Math.max(1, max - 1))}`;
  }

  function defaultMarkerNameForPath(path: string): string {
    const s = String(path ?? "").replace(/\\/g, "/").replace(/\/+$/, "");
    const i = s.lastIndexOf("/");
    const base = i >= 0 ? s.slice(i + 1) : s;
    return base || s || t("pinMarker.defaultName");
  }

  function markerLabelForPath(path: string): string {
    const custom = String(pinnedFolderLabels[path] ?? "").trim();
    return custom || defaultMarkerNameForPath(path);
  }

  function openPinMarkerModal(path: string) {
    const p = String(path ?? "").trim();
    if (!p) return;
    pinMarkerPath = p;
    pinMarkerName = markerLabelForPath(p);
    pinMarkerOpen = true;
  }

  function closePinMarkerModal() {
    pinMarkerOpen = false;
  }

  async function savePinMarkerModal() {
    const path = pinMarkerPath.trim();
    if (!path) {
      status = t("status.markerInvalidPath");
      return;
    }
    const label = pinMarkerName.trim() || defaultMarkerNameForPath(path);
    await pinFolder(path);
    const next = { ...pinnedFolderLabels, [path]: label };
    pinnedFolderLabels = next;
    await bridge.settingsPatch({ web_pinned_folder_labels: next });
    pinMarkerOpen = false;
    status = t("pinMarker.saved");
  }

  async function toggleDestinationsModePreserveScroll() {
    const fromDest = destinationsMode;
    const currentScrollTop = fromDest
      ? Number(galleryScrollEl?.scrollTop ?? 0)
      : Number(galleryPlainEl?.scrollTop ?? 0);
    destinationsMode = !fromDest;
    if (fromDest) {
      await clearSelection();
    }
    await tick();
    const apply = () => {
      if (!fromDest) {
        if (galleryScrollEl) {
          galleryScrollEl.scrollTop = currentScrollTop;
          galleryScrollAtTop = galleryScrollEl.scrollTop <= 2;
        }
      } else {
        if (galleryPlainEl) galleryPlainEl.scrollTop = currentScrollTop;
      }
    };
    apply();
    requestAnimationFrame(apply);
  }

  const openDestPreview = async (path: string) => {
    previewDestPath = path;
    previewSelectedPaths = [];
    previewSelectionMode = false;
    previewOpen = true;
    await refreshDestPreview();
  };

  $: {
    const _route = folder;
    void _route;
    keepRoutePathEndVisible();
  }

  const refreshDestPreview = async () => {
    const w = Math.max(320, Math.round(window.innerWidth * DEST_MODAL_FRAC));
    const out = await bridge.destinationPreview(previewDestPath, thumbScale, w);
    previewItems = out.items;
    previewThumbHydrationToken++;
    void hydratePreviewThumbsHq(previewItems, thumbScale, previewThumbHydrationToken);
    const valid = new Set(out.items.map((x: { path: string }) => x.path));
    previewSelectedPaths = previewSelectedPaths.filter((p) => valid.has(p));
  };

  function togglePreviewPick(path: string) {
    const has = previewSelectedPaths.includes(path);
    previewSelectedPaths = has
      ? previewSelectedPaths.filter((p) => p !== path)
      : [...previewSelectedPaths, path];
  }

  function applyPreviewRangeSelection(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const a = previewItems.findIndex((x) => x.path === fromPath);
    const b = previewItems.findIndex((x) => x.path === toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const draft = new Set(previewRangeBaseSelectedPaths);
    for (let i = lo; i <= hi; i++) {
      const p = previewItems[i]?.path;
      if (!p) continue;
      if (mode === "select") draft.add(p);
      else draft.delete(p);
    }
    previewSelectedPaths = [...draft];
  }

  function selectAllPreviewItems() {
    previewSelectedPaths = previewItems.map((x) => x.path);
  }

  function clearPreviewSelection() {
    previewSelectedPaths = [];
  }

  function invertPreviewSelection() {
    const cur = new Set(previewSelectedPaths);
    previewSelectedPaths = previewItems
      .map((x) => x.path)
      .filter((p) => !cur.has(p));
  }

  function enterPreviewSelectionMode(path?: string) {
    previewSelectionMode = true;
    if (path && !previewSelectedPaths.includes(path)) {
      previewSelectedPaths = [...previewSelectedPaths, path];
    }
  }

  function exitPreviewSelectionMode() {
    previewSelectionMode = false;
    previewSelectedPaths = [];
  }

  async function movePreviewSelectionToCurrentRoute() {
    if (previewSelectedPaths.length === 0) {
      status = t("status.selectModalFirst");
      return;
    }
    if (!folder.trim()) {
      status = t("status.loadFolderForDrop");
      return;
    }
    try {
      const out = await trackLoad(bridge.destinationMoveFromPreview(previewSelectedPaths));
      galleryState = out.state ?? galleryState;
      items = out.items ?? items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      const moved = Number(out.moveResult?.moved ?? 0);
      const errors = Number(out.moveResult?.errors ?? 0);
      status =
        t("status.previewMoved").replace("{moved}", String(moved)) +
        (errors ? t("status.previewMovedErrors").replace("{errors}", String(errors)) : "");
      previewSelectedPaths = [];
      await refreshDestPreview();
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.previewMoveError");
    }
  }

  async function deletePreviewSelectedItems() {
    if (previewSelectedPaths.length === 0) return;
    const deleting = [...previewSelectedPaths];
    const delSet = new Set(deleting);
    previewItems = previewItems.filter((x) => !delSet.has(x.path));
    previewSelectedPaths = [];
    enqueueDeletePaths(deleting);
    status = t("status.deleteQueued").replace("{n}", String(deleting.length));
  }

  function enqueueDeletePaths(paths: string[]) {
    const normalized = (paths || []).map((x) => String(x).trim()).filter((x) => x.length > 0);
    if (normalized.length === 0) return;
    galleryDeleteQueue = [...galleryDeleteQueue, { paths: normalized }];
    if (!galleryDeleteWorkerRunning) void processDeleteQueue();
  }

  async function processDeleteQueue() {
    if (galleryDeleteWorkerRunning) return;
    galleryDeleteWorkerRunning = true;
    try {
      while (galleryDeleteQueue.length > 0) {
        const [job, ...rest] = galleryDeleteQueue;
        galleryDeleteQueue = rest;
        try {
          const out = await bridge.galleryDeletePaths(job.paths);
          galleryState = out.state ?? galleryState;
          items = out.items ?? items;
          galleryThumbHydrationToken++;
          void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
          if (previewOpen) {
            const valid = new Set(
              (out.items ?? []).filter((x: GalleryItem) => isGalleryMediaKind(x.kind)).map((x: GalleryItem) => x.path)
            );
            previewItems = previewItems.filter((x) => valid.has(x.path));
            previewSelectedPaths = previewSelectedPaths.filter((p) => valid.has(p));
          }
          const deleted = Number(out.deleteResult?.deleted ?? 0);
          const errors = Number(out.deleteResult?.errors ?? 0);
          status = t("status.deleteBatchLine")
            .replace("{deleted}", String(deleted))
            .replace("{errPart}", errors ? t("status.deleteErrorsPart").replace("{errors}", String(errors)) : "")
            .replace("{queue}", String(galleryDeleteQueue.length));
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : t("status.deleteQueueError");
        }
      }
    } finally {
      galleryDeleteWorkerRunning = false;
    }
  }

  function openPreviewZoom(
    it: {
      path: string;
      name: string;
      thumbDataUrl?: string | null;
      thumbQuality?: "lq" | "hq";
      kind?: GalleryItem["kind"];
    },
    opts?: {
      preserveCarousel?: boolean;
      preserveMode?: boolean;
      navItems?: Array<{
        path: string;
        name: string;
        thumbDataUrl?: string | null;
        thumbQuality?: "lq" | "hq";
        kind?: GalleryItem["kind"];
      }>;
    }
  ) {
    if (opts?.navItems) zoomNavItems = opts.navItems;
    previewZoomPath = it.path;
    previewZoomName = it.name;
    // Importante: no mostrar el thumbnail "cuadrado" (recortado) como si fuera la imagen completa.
    // La vista principal debe venir de `galleryPreview` (contain) para garantizar que en "Completa" se vea 100% sin recortes.
    previewZoomDataUrl = null;
    previewZoomMediaType =
      it.kind === "video" ? "video" : it.path.toLowerCase().endsWith(".svg") ? "svg" : "image";
    previewZoomFileUrl = null;
    previewZoomScale = 1;
    previewPanX = 0;
    previewPanY = 0;
    if (!opts?.preserveMode) previewZoomMode = "fit";
    previewFillWidthAlignPending = previewZoomMode === "fillWidth";
    previewZoomNaturalW = 1;
    previewZoomNaturalH = 1;
    previewZoomCarouselVisible = opts?.preserveCarousel ? previewZoomCarouselVisible : true;
    zoomHudVisible = false;
    zoomEditMode = false;
    zoomCropMode = false;
    zoomCropDrag = false;
    previewZoomOpen = true;
    bridge
      .galleryPreview(it.path, 2200, 1600)
      .then((pr) => {
        if (previewZoomOpen && previewZoomPath === it.path) {
          const mt = String(pr.mediaType ?? "image");
          previewZoomMediaType = mt === "video" ? "video" : mt === "svg" ? "svg" : "image";
          previewZoomFileUrl = pr.fileUrl ?? null;
          previewZoomDataUrl = pr.dataUrl ?? null;
        }
      })
      .catch(() => undefined);
  }

  function applyGalleryRefreshFromMove(state: any, nextItems: GalleryItem[]) {
    galleryState = state;
    items = nextItems;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
  }

  function startPreviewLongPress(path: string) {
    if (previewLongPressTimer) clearTimeout(previewLongPressTimer);
    previewLongPressPath = path;
    previewLongPressTriggered = false;
    previewLongPressTimer = setTimeout(() => {
      previewLongPressTriggered = true;
      enterPreviewSelectionMode(path);
    }, 380);
  }

  function cancelPreviewLongPress() {
    if (previewLongPressTimer) clearTimeout(previewLongPressTimer);
    previewLongPressTimer = null;
    previewLongPressPath = null;
  }

  function endPreviewRangeSelection() {
    if (!previewRangeSelecting) return;
    previewRangeSelecting = false;
    previewRangeAnchorPath = null;
    previewRangeBaseSelectedPaths = [];
    // Evita el click "fantasma" al soltar tras arrastre de selección.
    previewSuppressClick = true;
    setTimeout(() => {
      previewSuppressClick = false;
    }, 0);
  }

  function onPreviewTilePointerDown(
    e: PointerEvent,
    it: { path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }
  ) {
    if (!previewSelectionMode) {
      startPreviewLongPress(it.path);
      return;
    }
    // Con Ctrl sostenido priorizamos arrastre, no rango de selección.
    if (e.ctrlKey) return;
    e.preventDefault();
    cancelPreviewLongPress();
    previewRangeSelecting = true;
    previewRangeAnchorPath = it.path;
    previewRangeBaseSelectedPaths = [...previewSelectedPaths];
    previewRangeMode = previewSelectedPaths.includes(it.path) ? "deselect" : "select";
    applyPreviewRangeSelection(it.path, it.path, previewRangeMode);
  }

  function onPreviewTilePointerEnter(path: string) {
    if (!previewSelectionMode || !previewRangeSelecting || !previewRangeAnchorPath) return;
    applyPreviewRangeSelection(previewRangeAnchorPath, path, previewRangeMode);
  }

  function onPreviewRangePointerMove(e: PointerEvent) {
    if (!previewSelectionMode || !previewRangeSelecting || !previewRangeAnchorPath) return;
    const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
    const tile = el?.closest?.(".tile[data-preview-path]") as HTMLElement | null;
    const path = tile?.dataset?.previewPath;
    if (!path) return;
    applyPreviewRangeSelection(previewRangeAnchorPath, path, previewRangeMode);
  }

  function onPreviewTileClick(e: MouseEvent, it: { path: string; name: string; thumbDataUrl?: string | null }) {
    if (e.ctrlKey) return;
    if (previewSuppressClick) return;
    if (previewLongPressTriggered && previewLongPressPath === it.path) {
      previewLongPressTriggered = false;
      previewLongPressPath = null;
      return;
    }
    if (previewSelectionMode) {
      togglePreviewPick(it.path);
      return;
    }
    openPreviewZoom(it, { navItems: previewItems });
  }

  function onPreviewTileDragStart(e: DragEvent, it: { path: string }) {
    if (!previewSelectionMode) {
      e.preventDefault();
      return;
    }
    // Mantener el mismo patrón que en galería: arrastre solo con Ctrl sostenido.
    if (!(e as DragEvent).ctrlKey) {
      e.preventDefault();
      status = t("status.ctrlDragHint");
      return;
    }
    if (!previewSelectedPaths.includes(it.path)) {
      previewSelectedPaths = [...previewSelectedPaths, it.path];
    }
    previewDragActive = true;
    const dt = e.dataTransfer;
    if (!dt) return;
    dt.effectAllowed = "move";
    dt.setData("application/x-om-preview-paths", JSON.stringify(previewSelectedPaths));
    dt.setData("text/plain", previewSelectedPaths[0] ?? it.path);
  }

  function onPreviewTileDragEnd() {
    previewDragActive = false;
  }

  function getVisibleGalleryMediaPaths(): string[] {
    return items.filter((x) => isGalleryMediaKind(x.kind)).map((x) => x.path);
  }

  function isGalleryTileSelected(it: GalleryItem): boolean {
    if (!destinationsMode || !isGalleryMediaKind(it.kind)) return false;
    return Boolean(it.selected);
  }

  function applyGalleryRangeSelection(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const imagePaths = getVisibleGalleryMediaPaths();
    const a = imagePaths.indexOf(fromPath);
    const b = imagePaths.indexOf(toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const draft = new Set(galleryRangeBaseSelectedSet ?? []);
    for (let i = lo; i <= hi; i++) {
      const p = imagePaths[i];
      if (!p) continue;
      if (mode === "select") draft.add(p);
      else draft.delete(p);
    }
    const next = [...draft];
    galleryRangeDraftSelectedPaths = next;
    galleryRangeDraftSelectedSet = new Set(next);
    galleryRangeCurrentPath = toPath;
    // Reflejo en vivo: actualizar selección visible sin esperar el commit backend.
    items = items.map((it) =>
      isGalleryMediaKind(it.kind)
        ? { ...it, selected: galleryRangeDraftSelectedSet?.has(it.path) ?? Boolean(it.selected) }
        : it
    );
  }

  function scheduleGalleryRangeSelection(path: string) {
    if (!galleryRangeSelecting || !galleryRangeAnchorPath) return;
    if (galleryRangeCurrentPath === path) return;
    galleryRangePendingPath = path;
    if (galleryRangeRaf !== null) return;
    galleryRangeRaf = requestAnimationFrame(() => {
      galleryRangeRaf = null;
      const target = galleryRangePendingPath;
      galleryRangePendingPath = null;
      if (!target || !galleryRangeAnchorPath) return;
      applyGalleryRangeSelection(galleryRangeAnchorPath, target, galleryRangeMode);
    });
  }

  function onGalleryTilePointerDown(e: PointerEvent, it: GalleryItem) {
    if (!destinationsMode || !isGalleryMediaKind(it.kind)) return;
    // Por defecto: selección por rango. Con Ctrl: modo arrastre.
    if (e.ctrlKey) return;
    e.preventDefault();
    const baseSelected = items
      .filter((x) => isGalleryMediaKind(x.kind) && x.selected)
      .map((x) => x.path);
    galleryRangeBaseSelectedPaths = baseSelected;
    galleryRangeBaseSelectedSet = new Set(baseSelected);
    galleryRangeAnchorPath = it.path;
    galleryRangeMode = baseSelected.includes(it.path) ? "deselect" : "select";
    galleryRangeSelecting = true;
    applyGalleryRangeSelection(it.path, it.path, galleryRangeMode);
  }

  function onGalleryRangePointerMove(e: PointerEvent) {
    if (!galleryRangeSelecting || !galleryRangeAnchorPath) return;
    const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
    const tile = el?.closest?.(".tile[data-item-path]") as HTMLElement | null;
    const path = tile?.dataset?.itemPath;
    if (!path) return;
    scheduleGalleryRangeSelection(path);
  }

  function onGalleryTilePointerEnter(path: string) {
    if (!galleryRangeSelecting || !galleryRangeAnchorPath) return;
    scheduleGalleryRangeSelection(path);
  }

  async function endGalleryRangeSelection() {
    if (!galleryRangeSelecting) return;
    const draft = new Set(galleryRangeDraftSelectedPaths ?? galleryRangeBaseSelectedPaths);
    const base = new Set(galleryRangeBaseSelectedPaths);
    const addPaths = [...draft].filter((p) => !base.has(p));
    const removePaths = [...base].filter((p) => !draft.has(p));
    galleryRangeSelecting = false;
    galleryRangeAnchorPath = null;
    galleryRangeBaseSelectedPaths = [];
    galleryRangeBaseSelectedSet = null;
    galleryRangeDraftSelectedPaths = null;
    galleryRangeDraftSelectedSet = null;
    galleryRangeCurrentPath = null;
    galleryRangePendingPath = null;
    if (galleryRangeRaf !== null) {
      cancelAnimationFrame(galleryRangeRaf);
      galleryRangeRaf = null;
    }
    galleryRangeSuppressClick = true;
    setTimeout(() => {
      galleryRangeSuppressClick = false;
    }, 0);
    if (addPaths.length === 0 && removePaths.length === 0) return;
    try {
      const prevItems = items;
      const out = await bridge.galleryApplySelectionDelta(addPaths, removePaths);
      galleryState = out.state;
      items = mergeItemsKeepingBestThumb(prevItems, out.items);
      if (destinationsMode) {
        const preferred = [...addPaths].reverse().find((p) =>
          items.some((x) => isGalleryMediaKind(x.kind) && x.path === p && Boolean(x.selected))
        );
        const fallback = [...items].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected))?.path;
        setSelectedPreviewFromPath(preferred ?? fallback);
      }
    } catch {
      const prevItems = items;
      const out = await bridge.galleryRefreshItems();
      galleryState = out.state;
      items = mergeItemsKeepingBestThumb(prevItems, out.items);
    }
  }


  function zoomStep(delta: number) {
    if (previewZoomMediaType === "video") return;
    // Permite alejar más allá de 100% para que, si el stage efectivo es menor
    // (por carrusel/cabecera), siempre puedas ver la imagen completa.
    previewZoomScale = Math.min(4, Math.max(0.5, Number((previewZoomScale + delta).toFixed(2))));
    touchZoomHud();
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }

  function getPanLimits() {
    const media = previewZoomMediaType === "video" ? zoomVideoEl : zoomImgEl;
    if (!zoomStageEl || !media) return { x: 0, y: 0 };
    const sr = zoomStageEl.getBoundingClientRect();
    const ir = media.getBoundingClientRect();
    const stageW = Math.max(1, sr.width);
    const stageH = Math.max(1, sr.height);
    const overflowX = (ir.width - stageW) / 2;
    const overflowY = (ir.height - stageH) / 2;
    if (previewZoomMode === "fillWidth") {
      return { x: 0, y: Math.max(0, ir.height - stageH) };
    }
    return { x: Math.max(0, overflowX), y: Math.max(0, overflowY) };
  }

  function clampPanToStage() {
    const limits = getPanLimits();
    const nextX = previewZoomMode === "fillWidth" ? 0 : clamp(previewPanX, -limits.x, limits.x);
    const nextY = previewZoomMode === "fillWidth" ? clamp(previewPanY, -limits.y, 0) : clamp(previewPanY, -limits.y, limits.y);
    if (nextX !== previewPanX) previewPanX = nextX;
    if (nextY !== previewPanY) previewPanY = nextY;
  }

  function alignFillWidthToTop() {
    if (previewZoomMode !== "fillWidth") return;
    previewPanX = 0;
    previewPanY = 0;
    previewFillWidthAlignPending = false;
  }

  // Snap a "100%" usando el mismo redondeo que muestra la UI.
  // Así garantizamos que al ver "100%" el `pan` no quede desfasado y no haya recorte.
  $: if (previewZoomMode === "fit" && Math.round(previewZoomScale * 100) === 100) {
    previewZoomScale = 1;
    previewPanX = 0;
    previewPanY = 0;
  }

  // Siempre mantenemos pan dentro de los límites reales del DOM (overflow vs stage).
  $: if (previewZoomOpen && zoomStageEl && (zoomImgEl || zoomVideoEl)) {
    clampPanToStage();
    if (previewFillWidthAlignPending) {
      alignFillWidthToTop();
    }
  }

  $: zoomImgTransform =
    previewZoomMode === "fit" && Math.round(previewZoomScale * 100) === 100
      ? "translate(-50%, -50%)"
      : previewZoomMode === "fillWidth"
        ? `translate(-50%, 0%) translate(0px, ${previewPanY}px) scale(${previewZoomScale})`
      : `translate(-50%, -50%) translate(${previewPanX}px, ${previewPanY}px) scale(${previewZoomScale})`;

  function zoomWithWheel(e: WheelEvent) {
    if (previewZoomMediaType === "video") {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    zoomStep(e.deltaY < 0 ? 0.14 : -0.14);
  }

  function moveZoomBy(step: number) {
    if (!zoomNavItems.length) return;
    const i = zoomNavItems.findIndex((x) => x.path === previewZoomPath);
    const base = i >= 0 ? i : 0;
    const next = (base + step + zoomNavItems.length) % zoomNavItems.length;
    const it = zoomNavItems[next];
    if (!it) return;
    openPreviewZoom(it, { preserveCarousel: true, preserveMode: true, navItems: zoomNavItems });
  }

  /** Desplaza el carrusel solo si el thumb activo queda cortado (sin animación suave en cada flecha). */
  function ensureZoomCarouselActiveVisible() {
    if (!previewZoomOpen || !previewZoomCarouselVisible || !zoomCarouselEl || !previewZoomPath) return;
    const active = zoomCarouselEl.querySelector<HTMLElement>(".zoom-carousel__item--active");
    if (!active) return;
    const cr = zoomCarouselEl.getBoundingClientRect();
    const ar = active.getBoundingClientRect();
    const margin = 8;
    if (ar.left < cr.left + margin || ar.right > cr.right - margin) {
      active.scrollIntoView({ behavior: "auto", block: "nearest", inline: "nearest" });
    }
  }

  function syncZoomNavThumbsFromItems(nextItems: GalleryItem[]) {
    const byPath = new Map(nextItems.filter((x) => isGalleryMediaKind(x.kind)).map((x) => [x.path, x]));
    zoomNavItems = zoomNavItems.map((z) => {
      const row = byPath.get(z.path);
      return row
        ? { ...z, thumbDataUrl: row.thumbDataUrl, thumbQuality: row.thumbQuality }
        : z;
    });
  }

  function normalizedCropFromClientRect(): { l: number; t: number; w: number; h: number } | null {
    if (!zoomImgEl) return null;
    const ir = zoomImgEl.getBoundingClientRect();
    const x1 = Math.min(zoomCropStartX, zoomCropCurX);
    const x2 = Math.max(zoomCropStartX, zoomCropCurX);
    const y1 = Math.min(zoomCropStartY, zoomCropCurY);
    const y2 = Math.max(zoomCropStartY, zoomCropCurY);
    const ix1 = Math.max(x1, ir.left);
    const iy1 = Math.max(y1, ir.top);
    const ix2 = Math.min(x2, ir.right);
    const iy2 = Math.min(y2, ir.bottom);
    const w = ix2 - ix1;
    const h = iy2 - iy1;
    if (w < ir.width * 0.02 || h < ir.height * 0.02) return null;
    return {
      l: (ix1 - ir.left) / ir.width,
      t: (iy1 - ir.top) / ir.height,
      w: w / ir.width,
      h: h / ir.height,
    };
  }

  async function applyZoomRotate(deg: number) {
    if (previewZoomMediaType === "video" || previewZoomMediaType === "svg") return;
    if (!previewZoomPath) return;
    try {
      const out = await trackLoad(bridge.galleryImageRotate(previewZoomPath, deg));
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      syncZoomNavThumbsFromItems(out.items);
      const pr = await trackLoad(bridge.galleryPreview(previewZoomPath, 2200, 1600));
      if (previewZoomOpen && previewZoomPath === pr.path) previewZoomDataUrl = pr.dataUrl ?? null;
      previewPanX = 0;
      previewPanY = 0;
      previewZoomScale = 1;
    } catch {
      status = t("zoom.rotateError");
    }
  }

  async function applyZoomCrop() {
    if (previewZoomMediaType === "video" || previewZoomMediaType === "svg") return;
    if (!previewZoomPath || !zoomImgEl) return;
    const norm = normalizedCropFromClientRect();
    if (!norm) {
      status = t("zoom.cropTooSmall");
      return;
    }
    try {
      const out = await trackLoad(
        bridge.galleryImageCropNormalized(previewZoomPath, norm.l, norm.t, norm.w, norm.h)
      );
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      syncZoomNavThumbsFromItems(out.items);
      zoomCropMode = false;
      const pr = await trackLoad(bridge.galleryPreview(previewZoomPath, 2200, 1600));
      if (previewZoomOpen && previewZoomPath === pr.path) previewZoomDataUrl = pr.dataUrl ?? null;
      previewPanX = 0;
      previewPanY = 0;
      previewZoomScale = 1;
    } catch {
      status = t("zoom.cropError");
    }
  }

  function onCropPointerDown(e: PointerEvent) {
    e.preventDefault();
    e.stopPropagation();
    zoomCropDrag = true;
    zoomCropStartX = zoomCropCurX = e.clientX;
    zoomCropStartY = zoomCropCurY = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
  }

  function onCropPointerMove(e: PointerEvent) {
    if (!zoomCropDrag) return;
    e.preventDefault();
    zoomCropCurX = e.clientX;
    zoomCropCurY = e.clientY;
  }

  function onCropPointerUp(e: PointerEvent) {
    if (!zoomCropDrag) return;
    zoomCropDrag = false;
    (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
  }

  $: zoomCropMarqueeStyle =
    zoomCropMode && zoomStageEl && zoomCropDrag
      ? (() => {
          const r = zoomStageEl!.getBoundingClientRect();
          const x1 = Math.min(zoomCropStartX, zoomCropCurX) - r.left;
          const y1 = Math.min(zoomCropStartY, zoomCropCurY) - r.top;
          const w = Math.abs(zoomCropCurX - zoomCropStartX);
          const h = Math.abs(zoomCropCurY - zoomCropStartY);
          return `left:${x1}px;top:${y1}px;width:${w}px;height:${h}px`;
        })()
      : "";

  function beginPan(e: PointerEvent) {
    if (previewZoomMediaType === "video") return;
    if (zoomCropMode) return;
    // Si la imagen no desborda el stage, no hay nada que “panear”.
    const limits = getPanLimits();
    if (limits.x <= 0.5 && limits.y <= 0.5) return;
    previewPanDrag = true;
    previewPanMoved = false;
    if (previewZoomMode === "fillWidth") {
      previewPanX = 0;
      previewPanStartY = e.clientY - previewPanY;
    } else {
      previewPanStartX = e.clientX - previewPanX;
      previewPanStartY = e.clientY - previewPanY;
    }
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    touchZoomHud();
  }

  function movePan(e: PointerEvent) {
    if (!previewPanDrag) return;
    if (previewZoomMode === "fillWidth") {
      const ny = e.clientY - previewPanStartY;
      if (Math.abs(ny - previewPanY) > 2) previewPanMoved = true;
      previewPanX = 0;
      previewPanY = ny;
    } else {
      const nx = e.clientX - previewPanStartX;
      const ny = e.clientY - previewPanStartY;
      if (Math.abs(nx - previewPanX) > 2 || Math.abs(ny - previewPanY) > 2) previewPanMoved = true;
      previewPanX = nx;
      previewPanY = ny;
    }
    clampPanToStage();
    touchZoomHud();
  }

  function endPan(e: PointerEvent) {
    previewPanDrag = false;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }

  function toggleZoomCarousel() {
    previewZoomCarouselVisible = !previewZoomCarouselVisible;
  }

  function onZoomStageClick(e: MouseEvent) {
    if (zoomCropMode) return;
    if (previewPanMoved) {
      previewPanMoved = false;
      return;
    }
    // Click en fondo del stage (blur): cerrar fullscreen.
    if (e.target === e.currentTarget) {
      if (previewZoomMode === "fillWidth") {
        toggleZoomCarousel();
        return;
      }
      previewZoomOpen = false;
      return;
    }
    toggleZoomCarousel();
  }

  async function moveCurrentZoomToDestination(destPath: string) {
    if (!previewZoomPath) return;
    const currentPath = previewZoomPath;
    const currentIdx = zoomNavItems.findIndex((x) => x.path === currentPath);
    const remainingNav = zoomNavItems.filter((x) => x.path !== currentPath);
    // Fluidez: avanzar de inmediato en fullscreen y procesar move en cola.
    if (remainingNav.length > 0) {
      const nextIdx = currentIdx >= 0 ? Math.min(currentIdx, remainingNav.length - 1) : 0;
      const nextItem = remainingNav[nextIdx];
      zoomNavItems = remainingNav;
      if (nextItem) {
        openPreviewZoom(nextItem, { preserveCarousel: true, preserveMode: true, navItems: remainingNav });
      }
    } else {
      previewZoomOpen = false;
    }
    zoomMoveQueue = [...zoomMoveQueue, { srcPath: currentPath, destPath }];
    status = t("status.zoomMoveQueued").replace("{n}", String(zoomMoveQueue.length));
    if (!zoomMoveWorkerRunning) {
      void processZoomMoveQueue();
    }
  }

  function requestMoveCurrentZoomToDestination(destPath: string) {
    if (!previewZoomPath) return;
    if (previewZoomSkipMoveConfirm) {
      void moveCurrentZoomToDestination(destPath);
      return;
    }
    openConfirmDelete(
      t("confirm.moveImageTitle"),
      t("confirm.moveImageDetail"),
      async () => {
        await moveCurrentZoomToDestination(destPath);
      },
      {
        confirmLabel: t("common.move"),
        bypassEnabled: true,
        bypassLabel: t("confirm.bypassMoveFullscreen"),
        bypassSetter: (enabled: boolean) => {
          previewZoomSkipMoveConfirm = enabled;
        },
      }
    );
  }

  async function processZoomMoveQueue() {
    if (zoomMoveWorkerRunning) return;
    zoomMoveWorkerRunning = true;
    try {
      while (zoomMoveQueue.length > 0) {
        const [job, ...rest] = zoomMoveQueue;
        zoomMoveQueue = rest;
        try {
          const out = await bridge.galleryMovePath(job.srcPath, job.destPath);
          if (previewZoomOpen) {
            // Evita refrescar la grilla detrás del fullscreen en cada movimiento.
            deferredZoomMoveRefresh = { state: out.state, items: out.items };
          } else {
            applyGalleryRefreshFromMove(out.state, out.items);
          }
          const moved = Number(out.moveResult?.moved ?? 0);
          const errors = Number(out.moveResult?.errors ?? 0);
          previewZoomCanUndoMove = moved > 0;
          status = moved > 0
            ? t("status.zoomMoveOk").replace("{queue}", String(zoomMoveQueue.length))
            : t("status.zoomMoveNone") + (errors ? t("status.zoomMoveNoneErrors") : "");
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : t("status.moveQueueError");
        }
      }
    } finally {
      zoomMoveWorkerRunning = false;
    }
  }

  async function undoLastZoomMove() {
    try {
      const out = await trackLoad(bridge.galleryUndoLastMove());
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      const moved = Number(out.moveResult?.moved ?? 0);
      previewZoomCanUndoMove = false;
      status = moved > 0 ? t("status.undoMoved") : t("status.undoNone");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.undoError");
    }
  }

  function onZoomImageLoad() {
    if (!zoomImgEl) return;
    previewZoomNaturalW = Math.max(1, zoomImgEl.naturalWidth || 1);
    previewZoomNaturalH = Math.max(1, zoomImgEl.naturalHeight || 1);
    clampPanToStage();
    alignFillWidthToTop();
  }

  function onZoomVideoMeta() {
    if (!zoomVideoEl) return;
    previewZoomNaturalW = Math.max(1, zoomVideoEl.videoWidth || 1);
    previewZoomNaturalH = Math.max(1, zoomVideoEl.videoHeight || 1);
    clampPanToStage();
    alignFillWidthToTop();
  }

  function openZoomFromGallery(it: GalleryItem) {
    const nav = items
      .filter((x) => isGalleryMediaKind(x.kind))
      .map((x) => ({
        path: x.path,
        name: x.name,
        thumbDataUrl: x.thumbDataUrl,
        thumbQuality: x.thumbQuality,
        kind: x.kind,
      }));
    openPreviewZoom(it, { navItems: nav });
  }

  function touchZoomHud() {
    zoomHudVisible = true;
    if (zoomHudTimer) clearTimeout(zoomHudTimer);
    zoomHudTimer = setTimeout(() => {
      zoomHudVisible = false;
    }, 1200);
  }

  $: zoomMiniRect = (() => {
    // dependencias reactivas explícitas
    const _deps = [previewZoomScale, previewPanX, previewPanY, previewZoomMode, previewZoomPath];
    void _deps;
    if (!zoomStageEl || !zoomImgEl || !zoomMiniEl) return "display:none;";
    const sr = zoomStageEl.getBoundingClientRect();
    const cr = zoomMiniEl.getBoundingClientRect();
    const cw = Math.max(1, cr.width);
    const ch = Math.max(1, cr.height);
    const nW = Math.max(1, previewZoomNaturalW);
    const nH = Math.max(1, previewZoomNaturalH);

    // La miniatura usa object-fit: contain dentro del contenedor.
    const miniScale = Math.min(cw / nW, ch / nH);
    const imgW = nW * miniScale;
    const imgH = nH * miniScale;
    const ox = (cw - imgW) / 2;
    const oy = (ch - imgH) / 2;

    // Fallback general (funciona bien cuando ya hay zoom o pan).
    const ir = zoomImgEl.getBoundingClientRect();
    const iw = Math.max(1, ir.width);
    const ih = Math.max(1, ir.height);
    const x0 = Math.max(0, Math.min(1, (sr.left - ir.left) / iw));
    const y0 = Math.max(0, Math.min(1, (sr.top - ir.top) / ih));
    const x1 = Math.max(0, Math.min(1, (sr.right - ir.left) / iw));
    const y1 = Math.max(0, Math.min(1, (sr.bottom - ir.top) / ih));

    const left = ox + x0 * imgW;
    const top = oy + y0 * imgH;
    const width = Math.max(3, (x1 - x0) * imgW);
    const height = Math.max(3, (y1 - y0) * imgH);
    return `left:${left}px;top:${top}px;width:${width}px;height:${height}px;`;
  })();

  const saveThumbScale = async () => {
    await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
    await reload({ silent: true });
  };

  const startOrganizer = async () => {
    const out = await bridge.organizerStart(orgPath, orgOptions);
    if (!out.ok) {
      status = out.error ?? t("status.organizerStartError");
      return;
    }
    orgRunning = true;
    status = t("status.organizerStarted");
  };

  const cancelOrganizer = async () => {
    await bridge.organizerCancel();
  };

  const pollOrganizer = async () => {
    const out = await bridge.organizerStatus();
    orgRunning = Boolean(out.running);
    orgDetail = out.progress?.detail ?? t("status.orgDetailIdle");
    orgProgress = `${out.progress?.current ?? 0}/${out.progress?.total ?? 0}`;
    if (!orgRunning && out.done) {
      const stats = out.done.stats ?? {};
      status = out.done.error
        ? t("status.organizerDoneError").replace("{msg}", String(out.done.error))
        : t("status.organizerDoneOk")
            .replace("{moved}", String(stats.moved_media ?? 0))
            .replace("{cbz}", String(stats.moved_cbz ?? 0))
            .replace("{other}", String(stats.moved_other ?? 0));
    }
  };

  const dragOpts: AddEventListenerOptions = { capture: true, passive: false };

  /** Tras dragend/drop, el navegador suele disparar un click espurio en la miniatura. */
  let suppressNextGalleryClick = false;
  /** Ignorar clics justo tras soltar en un destino (evita abrir vista previa por el click fantasma). */
  let ignoreDestCardClickUntil = 0;
  /** Destino bajo el cursor durante DnD (resaltado de tarjeta). */
  let dragOverDestPath: string | null = null;

  /** Formulario agregar/editar destino (modal). */
  let destFormOpen = false;
  let destFormMode: "add" | "edit" = "add";
  let destFormIdx: number | null = null;
  let destFormLabel = "";
  let destFormPath = "";
  let routePickerOpen = true;
  let confirmDeleteOpen = false;
  let confirmDeleteTitle = "Confirmar eliminación";
  let confirmDeleteDetail = "";
  let confirmDeleteConfirmLabel = "Eliminar";
  let confirmDeleteBypassEnabled = false;
  let confirmDeleteBypassChecked = false;
  let confirmDeleteBypassLabel = "No volver a preguntar por ahora";
  let confirmDeleteBypassSetter: ((enabled: boolean) => void) | null = null;
  let confirmDeleteAction: (() => Promise<void>) | null = null;

  /** Menú contextual (clic derecho) en un chip de destino. */
  let destCtxMenu: { x: number; y: number; idx: number; source: "gallery" | "fullscreen" } | null = null;
  /** Menú contextual (clic derecho) en marcador anclado del modal de rutas. */
  let pinnedCtxMenu: { x: number; y: number; path: string } | null = null;
  /** Menú contextual en miniaturas de la galería (imagen / vídeo). */
  let galleryItemCtxMenu: {
    x: number;
    y: number;
    path: string;
    name: string;
    thumbDataUrl?: string | null;
  } | null = null;
  let galleryFileInfoModal: { path: string; name: string; sizeBytes: number; mtimeIso: string } | null = null;
  let draggedDestIdx: number | null = null;
  let previewZoomSkipMoveConfirm = false;

  function clearGhostListeners() {
    if (dragWinMove) {
      document.removeEventListener("dragover", dragWinMove, dragOpts);
      dragWinMove = null;
    }
    if (dragWinEnd) {
      document.removeEventListener("dragend", dragWinEnd, dragOpts);
      dragWinEnd = null;
    }
  }

  /** Cierra ghost, listeners y estado de arrastre (WebEngine a veces no emite dragend). */
  function endDragSession() {
    ghostVisible = false;
    dragOverDestPath = null;
    dragOverSectionPath = null;
    document.body.classList.remove("om-dragging");
    clearGhostListeners();
  }

  function endDragSessionAfterGesture() {
    suppressNextGalleryClick = true;
    endDragSession();
  }

  function onTileDragStart(e: DragEvent, it: GalleryItem) {
    if (!destinationsMode || !isGalleryMediaKind(it.kind)) return;
    // Interacción: solo permitir arrastre cuando Ctrl está presionado.
    if (galleryRangeSelecting || !(e as DragEvent).ctrlKey) {
      e.preventDefault();
      return;
    }
    e.stopPropagation();
    endDragSession();
    const dt = e.dataTransfer;
    if (dt) {
      dt.setData("text/plain", it.path);
      dt.effectAllowed = "move";
      const im = new Image();
      im.src = BLANK_DRAG_IMG;
      dt.setDragImage(im, 0, 0);
    }
    ghostCount = Math.max(1, Number(galleryState.selectedCount) || 1);
    ghostThumb = it.thumbDataUrl ?? null;
    ghostCaption = ghostCount > 1 ? `${ghostCount} seleccionadas` : it.name;
    ghostVisible = true;
    ghostX = e.clientX;
    ghostY = e.clientY;
    document.body.classList.add("om-dragging");

    dragWinMove = (ev: DragEvent) => {
      ev.preventDefault();
      if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
      // Coordenadas del ghost: actualizar siempre (CSS transform, no re-render Svelte).
      ghostX = ev.clientX;
      ghostY = ev.clientY;
      // Throttle: las actualizaciones reactivas de Svelte (dragOverDestPath /
      // dragOverSectionPath) se limitan a 1 por frame para evitar re-renders
      // continuos que provocan parpadeo en el Toolbar y la barra de chips.
      if (dragRafPending) return;
      dragRafPending = true;
      const cx = ev.clientX;
      const cy = ev.clientY;
      requestAnimationFrame(() => {
        dragRafPending = false;
        const el = document.elementFromPoint(cx, cy);
        const card = el?.closest?.("[data-dest-path]") as HTMLElement | null;
        dragOverDestPath = card?.dataset?.destPath ?? null;
        const sec = el?.closest?.("[data-section-folder]") as HTMLElement | null;
        dragOverSectionPath = sec?.dataset?.sectionFolder ?? null;
      });
    };
    dragWinEnd = () => {
      endDragSessionAfterGesture();
    };
    document.addEventListener("dragover", dragWinMove, dragOpts);
    document.addEventListener("dragend", dragWinEnd, dragOpts);
  }

  function onSectionFolderDrop(e: DragEvent, folderPath: string) {
    e.preventDefault();
    e.stopPropagation();
    ignoreDestCardClickUntil = Date.now() + 450;
    endDragSessionAfterGesture();
    const fp = String(folderPath ?? "").trim();
    if (!fp) return;
    askConfirmMoveSelected(fp);
  }

  function onDestDrop(e: DragEvent, destPath: string) {
    e.preventDefault();
    e.stopPropagation();
    const fromRaw = e.dataTransfer?.getData("application/x-om-dest-idx") ?? "";
    const fromIdx = Number.parseInt(fromRaw, 10);
    const toIdx = destRows.findIndex((x) => x.path === destPath);
    if (Number.isFinite(fromIdx) && fromIdx >= 0 && toIdx >= 0) {
      void reorderDestinations(fromIdx, toIdx);
      return;
    }
    ignoreDestCardClickUntil = Date.now() + 450;
    endDragSessionAfterGesture();
    askConfirmMoveSelected(destPath);
  }

  function onDestChipDragStart(e: DragEvent, idx: number) {
    e.stopPropagation();
    draggedDestIdx = idx;
    const dt = e.dataTransfer;
    if (!dt) return;
    const asText = String(idx);
    dt.effectAllowed = "move";
    dt.setData("application/x-om-dest-idx", asText);
    dt.setData("text/plain", asText);
  }

  function onDestChipDragEnd() {
    draggedDestIdx = null;
  }

  async function reorderDestinations(fromIdx: number, toIdx: number) {
    if (fromIdx === toIdx) return;
    if (fromIdx < 0 || toIdx < 0 || fromIdx >= destRows.length || toIdx >= destRows.length) return;
    try {
      const out = await trackLoad(bridge.destinationsReorder(fromIdx, toIdx));
      destRows = normalizeDestinationsFromPayload(out);
      status = t("status.destReorderOk");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destReorderError");
    } finally {
      draggedDestIdx = null;
    }
  }

  /** Clic en la tarjeta (sin botón): vista previa de carpeta; el drop sigue moviendo archivos. */
  function onDestCardClick(e: MouseEvent, path: string) {
    if (e.button !== 0) return;
    if (Date.now() < ignoreDestCardClickUntil) return;
    if ((e.target as HTMLElement).closest("button")) return;
    const selectedCount = getSelectedGalleryPaths().length;
    if (selectedCount > 0) {
      askConfirmMoveSelected(path);
      return;
    }
    openDestPreview(path);
  }

  function closeDestCtxMenu() {
    destCtxMenu = null;
  }

  function closePinnedCtxMenu() {
    pinnedCtxMenu = null;
  }

  function closeGalleryItemCtxMenu() {
    galleryItemCtxMenu = null;
  }

  function formatFileSizeBytes(n: number): string {
    const x = Math.max(0, Number(n) || 0);
    if (x < 1024) return `${x} B`;
    if (x < 1024 * 1024) return `${(x / 1024).toFixed(1)} KB`;
    if (x < 1024 * 1024 * 1024) return `${(x / (1024 * 1024)).toFixed(2)} MB`;
    return `${(x / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function onGalleryItemContextMenu(e: MouseEvent, it: GalleryItem) {
    if (!isGalleryMediaKind(it.kind)) return;
    e.preventDefault();
    e.stopPropagation();
    const pad = 8;
    const mw = 240;
    const mh = Math.min(420, 56 + Math.max(0, destRows.length) * 34 + 120);
    let x = e.clientX;
    let y = e.clientY;
    x = Math.min(x, window.innerWidth - mw - pad);
    y = Math.min(y, window.innerHeight - mh - pad);
    x = Math.max(pad, x);
    y = Math.max(pad, y);
    closeDestCtxMenu();
    closePinnedCtxMenu();
    galleryItemCtxMenu = {
      x,
      y,
      path: it.path,
      name: it.name,
      thumbDataUrl: it.thumbDataUrl ?? null,
    };
  }

  async function copyGalleryCtxPath() {
    if (!galleryItemCtxMenu) return;
    const p = galleryItemCtxMenu.path;
    try {
      await navigator.clipboard.writeText(p);
      status = t("contextGallery.copyPathOk");
    } catch {
      status = t("contextGallery.copyError");
    }
    closeGalleryItemCtxMenu();
  }

  async function copyGalleryCtxFullImage() {
    if (!galleryItemCtxMenu) return;
    const path = galleryItemCtxMenu.path;
    status = t("load.loading");
    try {
      const res = await bridge.galleryCopyToClipboard(path);
      if (res.ok) {
        status = t("contextGallery.copyThumbOk");
      } else {
        status = res.error || t("contextGallery.copyError");
      }
    } catch {
      status = t("contextGallery.copyError");
    }
    closeGalleryItemCtxMenu();
  }

  function askDeleteGalleryItemFromCtx() {
    if (!galleryItemCtxMenu) return;
    const p = galleryItemCtxMenu.path;
    const label = galleryItemCtxMenu.name;
    closeGalleryItemCtxMenu();
    openConfirmDelete(
      t("contextGallery.deleteTitle"),
      t("confirm.deleteFileDetail").replace("{name}", label),
      async () => {
        enqueueDeletePaths([p]);
      },
      { confirmLabel: t("contextGallery.confirmDeleteBtn") }
    );
  }

  async function moveGalleryItemFromCtxTo(destPath: string) {
    if (!galleryItemCtxMenu) return;
    const src = galleryItemCtxMenu.path;
    closeGalleryItemCtxMenu();
    try {
      const out = await trackLoad(bridge.galleryMovePath(src, destPath));
      applyGalleryRefreshFromMove(out.state, out.items);
      const moved = Number(out.moveResult?.moved ?? 0);
      status = moved > 0 ? t("contextGallery.movedOk") : t("contextGallery.moveFailed");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("contextGallery.moveFailed");
    }
  }

  async function openGalleryFileInfoFromCtx() {
    if (!galleryItemCtxMenu) return;
    const path = galleryItemCtxMenu.path;
    closeGalleryItemCtxMenu();
    try {
      const st = await trackLoad(bridge.galleryFileStat(path));
      galleryFileInfoModal = {
        path: String(st.path ?? path),
        name: String(st.name ?? ""),
        sizeBytes: Number(st.sizeBytes ?? 0),
        mtimeIso: String(st.mtimeIso ?? ""),
      };
    } catch {
      status = t("contextGallery.metadataError");
    }
  }

  function onDestContextMenu(e: MouseEvent, idx: number, source: "gallery" | "fullscreen" = "gallery") {
    e.preventDefault();
    e.stopPropagation();
    const pad = 8;
    const mw = 200;
    const mh = 88;
    let x = e.clientX;
    let y = e.clientY;
    x = Math.min(x, window.innerWidth - mw - pad);
    y = Math.min(y, window.innerHeight - mh - pad);
    x = Math.max(pad, x);
    y = Math.max(pad, y);
    destCtxMenu = { x, y, idx, source };
  }

  function onPinnedContextMenu(e: MouseEvent, path: string) {
    e.preventDefault();
    e.stopPropagation();
    const p = String(path ?? "").trim();
    if (!p) return;
    const pad = 8;
    const mw = 200;
    const mh = 88;
    let x = e.clientX;
    let y = e.clientY;
    x = Math.min(x, window.innerWidth - mw - pad);
    y = Math.min(y, window.innerHeight - mh - pad);
    x = Math.max(pad, x);
    y = Math.max(pad, y);
    pinnedCtxMenu = { x, y, path: p };
  }

  function openEditPinnedFromCtx() {
    if (!pinnedCtxMenu) return;
    const p = pinnedCtxMenu.path;
    closePinnedCtxMenu();
    openPinMarkerModal(p);
  }

  function askUnpinPinnedFromCtx() {
    if (!pinnedCtxMenu) return;
    const p = pinnedCtxMenu.path;
    const label = markerLabelForPath(p);
    closePinnedCtxMenu();
    openConfirmDelete(
      t("confirm.unpinTitle"),
      t("confirm.unpinDetail").replace("{label}", label),
      async () => {
        await unpinFolder(p);
      },
      { confirmLabel: t("confirm.unpinConfirm") }
    );
  }

  function openAddDestForm() {
    closeDestCtxMenu();
    destFormMode = "add";
    destFormIdx = null;
    destFormLabel = "";
    destFormPath = "";
    destFormOpen = true;
  }

  function closeDestForm() {
    destFormOpen = false;
  }

  async function pickDestFormFolder() {
    try {
      const out = await bridge.dialogPickFolder(destFormPath);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      destFormPath = out.path;
      if (!destFormLabel.trim()) {
        const s = out.path.replace(/\\/g, "/").replace(/\/+$/, "");
        const j = s.lastIndexOf("/");
        destFormLabel = j >= 0 ? s.slice(j + 1) || s : s;
      }
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.folderPickerError");
    }
  }

  async function saveDestForm() {
    const label = destFormLabel.trim();
    const path = destFormPath.trim();
    if (!path) {
      status = t("status.destPathRequired");
      return;
    }
    try {
      if (destFormMode === "add") {
        await trackLoad(bridge.destinationsAdd(label, path));
        await syncDestinationsFromApi();
        status = t("status.destAdded");
      } else if (destFormIdx !== null) {
        await trackLoad(bridge.destinationsEdit(destFormIdx, label, path));
        await syncDestinationsFromApi();
        status = t("status.destUpdated");
      }
      destFormOpen = false;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destSaveError");
    }
  }

  function openEditFromCtx() {
    if (destCtxMenu === null) return;
    const i = destCtxMenu.idx;
    const d = destRows[i];
    closeDestCtxMenu();
    if (!d) return;
    destFormMode = "edit";
    destFormIdx = i;
    destFormLabel = d.label;
    destFormPath = d.path;
    destFormOpen = true;
  }

  function openPreviewFromCtx() {
    if (destCtxMenu === null) return;
    const i = destCtxMenu.idx;
    const d = destRows[i];
    closeDestCtxMenu();
    if (!d) return;
    openDestPreview(d.path);
  }

  async function removeDestFromCtx() {
    if (destCtxMenu === null) return;
    const i = destCtxMenu.idx;
    closeDestCtxMenu();
    try {
      await trackLoad(bridge.destinationsRemove(i));
      await syncDestinationsFromApi();
      status = t("status.destRemoved");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destDeleteError");
    }
  }

  // Tamaño objetivo directo: la grilla flexible (minmax + 1fr) absorbe cambios finos
  // de ancho y evita hueco fijo en el borde derecho.
  $: gridCellTargetPx = galleryGridCellPx(thumbScale);
  $: gridCellPx = Math.max(72, Number(gridCellTargetPx.toFixed(2)));
  /** Umbral de tamaño de celda para mostrar separadores por día (solo vista línea de tiempo). */
  const TIMELINE_DAY_MIN_PX = 130;

  function expandTimelineDayBreaks(raw: GalleryItem[], timeline: boolean, cellPx: number): GalleryItem[] {
    if (!timeline || cellPx < TIMELINE_DAY_MIN_PX) return raw;
    const out: GalleryItem[] = [];
    let lastDay: string | null = null;
    for (const it of raw) {
      if (it.kind === "section") {
        lastDay = null;
        out.push(it);
        continue;
      }
      if (!isGalleryMediaKind(it.kind)) {
        out.push(it);
        continue;
      }
      const iso = it.mtimeIso?.trim();
      if (iso && iso.length >= 10) {
        const day = iso.slice(0, 10);
        if (lastDay !== null && day !== lastDay) {
          const dayNum = iso.slice(8, 10);
          out.push({
            kind: "day_break",
            name: dayNum,
            path: `daybreak:${day}`,
            thumbDataUrl: null,
          });
        }
        lastDay = day;
      }
      out.push(it);
    }
    return out;
  }

  $: galleryGridItems = expandTimelineDayBreaks(items, timelineView, gridCellPx);

  /** Contenedor con scroll: modo Edición (`galleryScrollEl`) o modo base (`galleryPlainEl`). */
  $: galleryScrollContainer = galleryScrollEl ?? galleryPlainEl;

  $: if (galleryScrollContainer && galleryScrollContainer !== galleryGridObservedEl) {
    galleryGridResizeObserver?.disconnect();
    galleryGridObservedEl = galleryScrollContainer;
    galleryGridResizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      // Usar ancho de borde evita saltos por cambios de scroll interno.
      const borderInline =
        Array.isArray((entry as any).borderBoxSize) && (entry as any).borderBoxSize.length > 0
          ? Number((entry as any).borderBoxSize[0]?.inlineSize ?? 0)
          : 0;
      const fallback = Math.max(
        0,
        Math.round(galleryScrollContainer?.getBoundingClientRect().width ?? entry.contentRect.width)
      );
      galleryGridWidth = Math.max(0, Math.round(borderInline || fallback));
    });
    galleryGridResizeObserver.observe(galleryScrollContainer);
  }

  $: if (!destinationsMode && !previewZoomDestMode) {
    destCtxMenu = null;
    if (destFormOpen) destFormOpen = false;
  }

  $: if (!routePickerOpen) {
    pinnedCtxMenu = null;
  }

  $: if (!previewZoomOpen && deferredZoomMoveRefresh) {
    applyGalleryRefreshFromMove(deferredZoomMoveRefresh.state, deferredZoomMoveRefresh.items);
    deferredZoomMoveRefresh = null;
  }

  $: {
    const nav = getGalleryNavigablePaths();
    if (nav.length === 0) {
      galleryCursorPath = null;
      galleryKeyboardRangeAnchorPath = null;
    } else if (!galleryCursorPath || !nav.includes(galleryCursorPath)) {
      galleryCursorPath = nav[0];
    }
  }

  $: if (!previewZoomOpen) {
    previewZoomSkipMoveConfirm = false;
  }

  $: if (previewZoomOpen && previewZoomCarouselVisible && zoomCarouselEl && previewZoomPath) {
    void tick().then(() => ensureZoomCarouselActiveVisible());
  }

  onMount(async () => {
    try {
      await waitForPywebviewApi();
    } catch {
      status = t("status.apiUnavailable");
      return;
    }
    await loadInitial();
    if (folder) {
      try {
        await loadFolder(false);
      } catch {
        status = t("status.restoreFolderError");
      }
    }
    pollTimer = window.setInterval(() => {
      pollOrganizer().catch(() => undefined);
    }, 1100);
  });

  onDestroy(() => {
    endDragSession();
    galleryGridResizeObserver?.disconnect();
    galleryGridResizeObserver = null;
    if (thumbScaleDebounce) clearTimeout(thumbScaleDebounce);
    if (zoomHudTimer) clearTimeout(zoomHudTimer);
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  });
  import Toolbar from './components/Toolbar.svelte';
  import SidebarMarkers from './components/SidebarMarkers.svelte';
  import FullscreenPlayer from './components/FullscreenPlayer.svelte';
  import GalleryGrid from './components/GalleryGrid.svelte';
</script>

<svelte:window
  on:pointermove={(e) => {
    onPreviewRangePointerMove(e);
    onGalleryRangePointerMove(e);
  }}
  on:pointerup={() => {
    endPreviewRangeSelection();
    void endGalleryRangeSelection();
  }}
  on:pointercancel={() => {
    endPreviewRangeSelection();
    void endGalleryRangeSelection();
  }}
  on:keydown={(e) => {
    if (confirmDeleteOpen) {
      if (e.key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        void runConfirmDelete();
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closeConfirmDelete();
        return;
      }
      // Evita que flechas, Supr, espacio u otros atajos actúen sobre la galería/vistas detrás del diálogo.
      return;
    }
    if (pinMarkerOpen) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closePinMarkerModal();
        return;
      }
      // Mismo criterio: no propagar atajos globales mientras el modal de marcador está abierto.
      return;
    }
    if (galleryItemCtxMenu) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closeGalleryItemCtxMenu();
        return;
      }
      return;
    }
    if (galleryFileInfoModal) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        galleryFileInfoModal = null;
        return;
      }
      return;
    }
    const activeEl = (document.activeElement as HTMLElement | null) ?? null;
    const activeInputType = (activeEl as HTMLInputElement | null)?.type?.toLowerCase?.() ?? "";
    const isTypingEl = Boolean(
      activeEl &&
        (activeEl.isContentEditable ||
          (activeEl.tagName === "INPUT" && activeInputType !== "range") ||
          activeEl.tagName === "TEXTAREA" ||
          activeEl.closest('[contenteditable="true"]'))
    );
    if (
      shortcutMatchesSingle(e as KeyboardEvent, keyboardShortcuts.toggleMode) &&
      !e.repeat &&
      !isTypingEl &&
      !e.ctrlKey &&
      !e.altKey &&
      !e.metaKey
    ) {
      e.preventDefault();
      if (previewZoomOpen) {
        previewZoomDestMode = !previewZoomDestMode;
        status = previewZoomDestMode ? t("status.editionOnFs") : t("status.editionOffFs");
      } else if (previewOpen) {
        previewSelectionMode = !previewSelectionMode;
        if (!previewSelectionMode) previewSelectedPaths = [];
        status = previewSelectionMode ? t("status.selectionOnPreview") : t("status.selectionOffPreview");
      } else {
        const nextMode = !destinationsMode;
        void toggleDestinationsModePreserveScroll();
        status = nextMode ? t("status.editionOn") : t("status.editionOff");
      }
      return;
    }
    if (previewZoomOpen) {
      const typingInDestForm = Boolean(activeEl?.closest(".modal--dest-form"));
      if (destFormOpen && isTypingEl && typingInDestForm) return;
      if (shortcutMatchesList(e as KeyboardEvent, keyboardShortcuts.zoomPrev)) {
        e.preventDefault();
        moveZoomBy(-1);
        return;
      }
      if (shortcutMatchesList(e as KeyboardEvent, keyboardShortcuts.zoomNext)) {
        e.preventDefault();
        moveZoomBy(1);
        return;
      }
    }
    const keyLower = String(e.key || "").toLowerCase();
    const isGalleryNavKey = ["arrowleft", "arrowright", "arrowup", "arrowdown", "a", "d", "w", "s"].includes(keyLower);
    if (
      !isTypingEl &&
      !previewOpen &&
      !previewZoomOpen &&
      !viewMenuOpen &&
      !settingsOpen &&
      !orgPanelOpen &&
      !destFormOpen &&
      !routePickerOpen &&
      isGalleryNavKey
    ) {
      e.preventDefault();
      const current = getOrInitGalleryCursorPath();
      const next = moveGalleryCursorByKey(keyLower);
      if (next) {
        galleryCursorPath = next;
        galleryKeyboardNavHintActive = true;
        setSelectedPreviewFromPath(next);
        scrollGalleryCursorIntoView(next);
        if (e.ctrlKey) {
          const anchor = galleryKeyboardRangeAnchorPath ?? current ?? next;
          galleryKeyboardRangeAnchorPath = anchor;
          void applyGalleryKeyboardRangeSelection(anchor, next);
        } else {
          galleryKeyboardRangeAnchorPath = null;
        }
      }
      return;
    }
    if (
      !isTypingEl &&
      !previewOpen &&
      !previewZoomOpen &&
      !viewMenuOpen &&
      !settingsOpen &&
      !orgPanelOpen &&
      !destFormOpen &&
      !routePickerOpen &&
      shortcutMatchesSingle(e as KeyboardEvent, " ")
    ) {
      const cur = getOrInitGalleryCursorPath();
      if (!cur) return;
      e.preventDefault();
      void toggleGalleryCursorSelection(cur);
      return;
    }
    if (!isTypingEl && shortcutMatchesSingle(e as KeyboardEvent, keyboardShortcuts.deleteAction)) {
      const hasPreviewSelectionForDelete = previewOpen && previewSelectedPaths.length > 0;
      const hasGallerySelectionForDelete =
        Number(galleryState?.selectedCount ?? 0) > 0 || items.some((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
      if (previewZoomOpen && previewZoomPath) {
        e.preventDefault();
        openConfirmDelete(t("confirm.deleteImageTitle"), t("confirm.deleteImageDetail"), deleteCurrentZoomImage);
        return;
      }
      if (hasPreviewSelectionForDelete) {
        e.preventDefault();
        openConfirmDelete(
          t("confirm.deleteSelectionTitle"),
          t("confirm.deleteSelectionDetail").replace("{count}", String(previewSelectedPaths.length)),
          deletePreviewSelectedItems
        );
        return;
      }
      if (hasGallerySelectionForDelete) {
        e.preventDefault();
        openConfirmDelete(
          t("confirm.deleteSelectionTitle"),
          t("confirm.deleteSelectionDetail").replace("{count}", String(galleryState.selectedCount)),
          deleteSelectedGalleryItems
        );
        return;
      }
    }
    if (!shortcutMatchesSingle(e as KeyboardEvent, keyboardShortcuts.escape)) return;
    const hasPreviewSelection = previewSelectedPaths.length > 0 || previewRangeSelecting;
    const hasGallerySelection =
      Number(galleryState?.selectedCount ?? 0) > 0 || items.some((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
    if (hasPreviewSelection || hasGallerySelection) {
      e.preventDefault();
      if (hasPreviewSelection) {
        endPreviewRangeSelection();
        previewSelectedPaths = [];
        previewSelectionMode = false;
      }
      if (hasGallerySelection) {
        void clearSelection();
      }
      status = t("status.selectionCleared");
      return;
    }
    if (pinnedCtxMenu) closePinnedCtxMenu();
    else if (galleryItemCtxMenu) closeGalleryItemCtxMenu();
    else if (galleryFileInfoModal) galleryFileInfoModal = null;
    else if (destCtxMenu) closeDestCtxMenu();
    else if (destFormOpen) closeDestForm();
    else if (viewMenuOpen) viewMenuOpen = false;
    else if (settingsOpen) settingsOpen = false;
    else if (previewZoomOpen && zoomCropMode) {
      e.preventDefault();
      zoomCropMode = false;
    } else if (previewZoomOpen && zoomEditMode) {
      e.preventDefault();
      zoomEditMode = false;
      zoomCropMode = false;
    } else if (previewZoomOpen) previewZoomOpen = false;
    else if (previewOpen) previewOpen = false;
    else if (orgPanelOpen) orgPanelOpen = false;
  }}
/>

<main
  class="app"
  class:app--layout-ruta={!destinationsMode}
  class:app--layout-destinos={destinationsMode}
  class:app--tile-flat={thumbCardStyle === "flat"}
  class:app--tile-outlined={thumbCardStyle === "outlined"}
  class:app--tile-no-frame={!thumbFrameVisible}
  style={`--thumb-image-radius:${thumbImageRadiusPx}px;--thumb-tile-radius:${thumbTileRadiusPx}px`}
>
  
  <Toolbar
    bind:destinationsMode
    bind:viewMenuOpen
    bind:includeSubfolders
    bind:groupByFolder
    bind:sectionDominantColor
    bind:timelineView
    bind:gallerySortMode
    bind:orgPath
    bind:folder
    bind:orgPanelOpen
    bind:routePathEl
    bind:routePickerOpen
    bind:folderBackStack
    bind:folderForwardStack
    bind:pinnedFolders
    {toggleDestinationsModePreserveScroll}
    {onIncludeSubfoldersChange}
    {onGroupByFolderChange}
    {onSectionDominantColorChange}
    {onTimelineViewChange}
    {onGallerySortChange}
    {goBackFolder}
    {goForwardFolder}
    {goUpFolder}
    {unpinFolder}
    {openPinMarkerModal}
    {reload}
    {pickGalleryFolder}
    {openSettingsModal}
  />

  

  

  {#if destinationsMode}
    <div
      class="destinos-work"
      class:destinos-work--drag={destSplitDrag}
      style="grid-template-rows:minmax(0,1fr) auto"
    >
      <div class="destinos-work__top">
        <section
          class="content"
          style={previewVisible
            ? `grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`
            : "grid-template-columns:minmax(0,1fr)"}
        >
  <GalleryGrid
    bind:galleryGridItems
    bind:gridCellPx
    bind:thumbGapPx
    bind:dragOverSectionPath
    bind:galleryKeyboardNavHintActive
    bind:galleryCursorPath
    bind:galleryRangeSelecting
    bind:galleryRangeSuppressClick
    bind:showThumbLabels
    bind:galleryScrollAtTop
    bind:galleryState
    bind:destRows
    bind:dragOverDestPath
    bind:draggedDestIdx
    bind:galleryScrollEl
    bind:galleryGridEl
    {onGalleryScroll}
    {onSectionFolderDrop}
    {navigateToFolder}
    {isGalleryTileSelected}
    {isGalleryMediaKind}
    {onGalleryTilePointerDown}
    {onGalleryTilePointerEnter}
    {onTileDragStart}
    {clickItem}
    {openZoomFromGallery}
    {onGalleryItemContextMenu}
    {selectPage}
    {clearSelection}
    {invertSelection}
    {openConfirmDelete}
    {deleteSelectedGalleryItems}
    {openAddDestForm}
    {onDestCardClick}
    {onDestContextMenu}
    {onDestChipDragStart}
    {onDestChipDragEnd}
    {onDestDrop}
      {destinationsMode}
  />

          {#if previewVisible}
            <div
              class="splitter"
              role="separator"
              aria-orientation="vertical"
              aria-label="Arrastrar para repartir galería y vista previa"
              on:pointerdown={beginSplitDrag}
            ></div>

            <aside class="preview om-panel">
              {#if selectedPreview?.mediaType === "video" && selectedPreview?.fileUrl}
                <!-- svelte-ignore a11y_media_has_caption -->
                <video
                  class="preview__img preview__video"
                  src={selectedPreview.fileUrl}
                  controls
                  playsinline
                  preload="metadata"
                ></video>
              {:else if selectedPreview?.mediaType === "svg" && selectedPreview?.fileUrl}
                <img
                  class="preview__img preview__svg"
                  src={selectedPreview.fileUrl}
                  alt={selectedPreview.name}
                />
              {:else if selectedPreview?.dataUrl}
                <img class="preview__img" src={selectedPreview.dataUrl} alt={selectedPreview.name} />
              {:else}
                <div class="preview__empty">{t("preview.emptySelect")}</div>
              {/if}
              <div class="preview__meta">{selectedPreview?.path ?? ""}</div>
            </aside>
          {/if}
        </section>
      </div>
      <div class="dest-float-chips-bar" aria-label={t("selection.destBarAria")}>
        <button type="button" class="om-btn om-btn--ghost om-btn--compact dest-float-add" on:click={openAddDestForm}>
          +
        </button>
        {#if destRows.length === 0}
          <span class="dest-float-empty">{t("selection.noDestFolders")}</span>
        {/if}
        {#each destRows as d, i (d.path + "\0" + i)}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_interactive_supports_focus -->
          <div
            class="dest-float-chip"
            class:dest-float-chip--drop-target={dragOverDestPath === d.path}
            class:dest-float-chip--dragging={draggedDestIdx === i}
            data-dest-path={d.path}
            title={d.path}
            role="button"
            tabindex="0"
            draggable={true}
            on:click={(e) => onDestCardClick(e, d.path)}
            on:keydown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onDestCardClick(e as unknown as MouseEvent, d.path);
              }
            }}
            on:contextmenu={(e) => onDestContextMenu(e, i, "gallery")}
            on:dragstart={(e) => onDestChipDragStart(e, i)}
            on:dragend={onDestChipDragEnd}
            on:dragenter|preventDefault
            on:dragover|preventDefault
            on:drop={(e) => onDestDrop(e, d.path)}
          >
            <span class="dest-float-chip__title">{d.label}</span>
          </div>
        {/each}
      </div>
    </div>
  {:else}
    <section
      class="content"
      style={previewVisible
        ? `grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`
        : "grid-template-columns:minmax(0,1fr)"}
    >
  <GalleryGrid
    bind:galleryGridItems
    bind:gridCellPx
    bind:thumbGapPx
    bind:dragOverSectionPath
    bind:galleryKeyboardNavHintActive
    bind:galleryCursorPath
    bind:galleryRangeSelecting
    bind:galleryRangeSuppressClick
    bind:showThumbLabels
    bind:galleryScrollAtTop
    bind:galleryState
    bind:destRows
    bind:dragOverDestPath
    bind:draggedDestIdx
    bind:galleryScrollEl
    bind:galleryGridEl
    {onGalleryScroll}
    {onSectionFolderDrop}
    {navigateToFolder}
    {isGalleryTileSelected}
    {isGalleryMediaKind}
    {onGalleryTilePointerDown}
    {onGalleryTilePointerEnter}
    {onTileDragStart}
    {clickItem}
    {openZoomFromGallery}
    {onGalleryItemContextMenu}
    {selectPage}
    {clearSelection}
    {invertSelection}
    {openConfirmDelete}
    {deleteSelectedGalleryItems}
    {openAddDestForm}
    {onDestCardClick}
    {onDestContextMenu}
    {onDestChipDragStart}
    {onDestChipDragEnd}
    {onDestDrop}
      {destinationsMode}
  />

      {#if previewVisible}
        <div
          class="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label="Arrastrar para repartir galería y vista previa"
          on:pointerdown={beginSplitDrag}
        ></div>

        <aside class="preview om-panel">
          {#if selectedPreview?.mediaType === "video" && selectedPreview?.fileUrl}
            <!-- svelte-ignore a11y_media_has_caption -->
            <video
              class="preview__img preview__video"
              src={selectedPreview.fileUrl}
              controls
              playsinline
              preload="metadata"
            ></video>
          {:else if selectedPreview?.mediaType === "svg" && selectedPreview?.fileUrl}
            <img
              class="preview__img preview__svg"
              src={selectedPreview.fileUrl}
              alt={selectedPreview.name}
            />
          {:else if selectedPreview?.dataUrl}
            <img class="preview__img" src={selectedPreview.dataUrl} alt={selectedPreview.name} />
          {:else}
            <div class="preview__empty">{t("preview.emptySelect")}</div>
          {/if}
          <div class="preview__meta">{selectedPreview?.path ?? ""}</div>
        </aside>
      {/if}
    </section>
  {/if}

  <footer class="pager om-panel pager--bar" aria-label={t("pager.footerAria")}>
    {#if thumbsPerPage !== 0}
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.firstPage")} on:click={() => goPage(1)}>|«</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.prevPage")} on:click={() => goPage(Math.max(1, galleryState.page - 1))}>‹</button>
      {#each pageLinks as item}
        {#if item === "gap"}
          <span class="pager__gap" aria-hidden="true">…</span>
        {:else}
          <button
            type="button"
            class="om-btn om-btn--ghost pager__num"
            class:om-btn--primary={item === galleryState.page}
            title={t("pager.goPageTitle").replace("{n}", String(item))}
            on:click={() => goPage(item)}>{item}</button>
        {/if}
      {/each}
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.nextPage")} on:click={() => goPage(Math.min(galleryState.totalPages, galleryState.page + 1))}>›</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.lastPage")} on:click={() => goPage(galleryState.totalPages)}>»|</button>
      <span class="pager__google-line"
        >{galleryState.total}
        {t("pager.imagesWord")} · {t("pager.pageWord")}
        {galleryState.page}
        {t("pager.ofWord")}
        {galleryState.totalPages}</span>
      <label class="pager__jump">
        <input
          class="om-input pager__jump-input"
          type="number"
          min="1"
          max={galleryState.totalPages}
          bind:value={pageJumpDraft}
          on:keydown={(e) => e.key === "Enter" && jumpToPageDraft()}
        />
        <span class="pager__jump-total">/ {galleryState.totalPages}</span>
      </label>
      <button type="button" class="om-btn om-btn--primary om-btn--compact" on:click={jumpToPageDraft}>{t("pager.goJump")}</button>
    {:else}
      <span class="pager__google-line">
        {t("pager.loadedPrefix")}
        {Number(galleryState?.endIndex ?? 0)}/{Number(galleryState?.total ?? 0)}
        {t("pager.imagesWord")} ·
        {Number(galleryState?.totalElements ?? Number(galleryState?.total ?? 0) + Number(galleryState?.subfoldersCount ?? 0))}
        {t("pager.elementsWord")} · {t("pager.totalWeight")}
        {Number(galleryState?.totalBytes ?? -1) < 0 ? t("pager.calculating") : formatBytes(Number(galleryState?.totalBytes ?? 0))}
      </span>
    {/if}
    <div class="grow"></div>
    <span class="status-line">{status}</span>
    <span class="webui-build-tag" title={t("pager.buildTagTitle")}>{__WEBUI_BUILD__.slice(0, 10)}</span>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact"
      title={previewVisible ? t("pager.previewHide") : t("pager.previewShow")}
      on:click={togglePreviewVisible}
    >{previewVisible ? t("pager.previewOn") : t("pager.previewOff")}</button>
    <span class="field-label pager__split-label" title={t("pager.splitHint")}
      >{t("preview.panelRight")} ~{Math.round(previewRatio * 100)}%</span>
    <label class="field-label pager__thumb-label" for="route-thumb-scale-footer"
      >{t("pager.thumbsLabel")} {Math.round(thumbScale * 100)}%</label>
    <input
      id="route-thumb-scale-footer"
      class="om-range pager__thumb-range"
      type="range"
      min="0.01"
      max="2.25"
      step="0.01"
      bind:value={thumbScale}
      on:input={scheduleThumbScaleReload}
      on:change={flushThumbScaleOnRelease}
    />
  </footer>

  {#if previewOpen}
    <div
      class="overlay"
      role="button"
      tabindex="-1"
      aria-label={t("preview.closeDestAria")}
      on:dragover|preventDefault
      on:drop={(e) => {
        const t = e.target as HTMLElement | null;
        if (t?.closest(".modal--dest")) return;
        const raw = e.dataTransfer?.getData("application/x-om-preview-paths") ?? "";
        if (!raw) return;
        try {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            previewSelectedPaths = parsed.map((x) => String(x)).filter((x) => x.trim().length > 0);
          }
        } catch {
          // Mantener selección actual si no se pudo parsear.
        }
        previewDragActive = false;
        void movePreviewSelectionToCurrentRoute();
      }}
      on:click={() => (previewOpen = false)}
      on:keydown={(e) => {
        if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          previewOpen = false;
        }
      }}
    >
      <div
        class="modal modal--dest om-panel om-panel--lift"
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="dest-preview-title"
        on:click|stopPropagation
        on:keydown={(e) => e.stopPropagation()}
      >
        <header class="modal__head">
          <strong id="dest-preview-title">{previewDestPath}</strong>
          <div class="modal__head-actions">
            <div class="selection-float preview-selection-float" role="toolbar" aria-label={t("selection.previewToolbarAria")}>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--mini"
                on:click={() => (previewSelectionMode ? exitPreviewSelectionMode() : (previewSelectionMode = true))}
                title={previewSelectionMode ? t("selection.deactivateMode") : t("selection.activateMode")}
              >{previewSelectionMode ? t("selection.deactivate") : t("selection.activate")}</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectAllPreviewItems}
                >{t("selection.selectAll")}</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearPreviewSelection}
                >{t("selection.clearSelection")}</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--mini"
                disabled={previewSelectedPaths.length === 0}
                on:click={() =>
                  openConfirmDelete(
                    t("confirm.deleteSelectionTitle"),
                    t("confirm.deleteSelectionDetail").replace("{count}", String(previewSelectedPaths.length)),
                    deletePreviewSelectedItems
                  )}
              >{t("selection.delete")}</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertPreviewSelection}
                >{t("selection.invert")}</button>
              <span class="selection-float__count" title={t("selection.selectedTitle")}>{previewSelectedPaths.length}</span>
            </div>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--close"
              aria-label={t("common.closeModalAria")}
              title={t("common.close")}
              on:click={() => (previewOpen = false)}>✕</button
            >
          </div>
        </header>
        <div class="modal__scroll">
          <section class="grid" style={`--cell:${gridCellPx}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px`}>
            {#each previewItems as it}
              <div
                class="tile"
                data-preview-path={it.path}
                class:selected={previewSelectedPaths.includes(it.path)}
                role="button"
                tabindex="0"
                draggable={previewSelectionMode}
                on:pointerdown={(e) => onPreviewTilePointerDown(e, it)}
                on:pointerenter={() => onPreviewTilePointerEnter(it.path)}
                on:pointerup={cancelPreviewLongPress}
                on:pointerleave={cancelPreviewLongPress}
                on:pointercancel={cancelPreviewLongPress}
                on:dragstart={(e) => onPreviewTileDragStart(e, it)}
                on:dragend={onPreviewTileDragEnd}
                on:click={(e) => onPreviewTileClick(e, it)}
                on:keydown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onPreviewTileClick(e as unknown as MouseEvent, it);
                  }
                }}
              >
                {#if it.thumbDataUrl}
                  <img src={it.thumbDataUrl} alt="" class:thumb--lq={it.thumbQuality === "lq"} draggable={false} />
                {/if}
                {#if showThumbLabels}<span class="tile__name">{it.name}</span>{/if}
              </div>
            {/each}
          </section>
        </div>
      </div>
    </div>
  {/if}

  

  {#if ghostVisible}
    <div class="drag-ghost" style={`left:${ghostX}px;top:${ghostY}px`} aria-hidden="true">
      <div class="drag-ghost__card">
        {#if ghostThumb}
          <img src={ghostThumb} alt="" class="drag-ghost__img" />
        {:else}
          <div class="drag-ghost__ph">IMG</div>
        {/if}
        {#if ghostCount > 1}
          <span class="drag-ghost__badge">{ghostCount}</span>
        {/if}
      </div>
      <span class="drag-ghost__cap">{ghostCaption}</span>
    </div>
  {/if}

  {#if orgPanelOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="org-float-overlay" role="presentation" on:click|self={() => (orgPanelOpen = false)}>
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <div
        class="organizer-float om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="org-float-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="org-float__head">
          <strong id="org-float-title">{t("organizer.title")}</strong>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("common.closeModalAria")}
            title={t("common.close")}
            on:click={() => (orgPanelOpen = false)}>✕</button
          >
        </header>
        <div class="org-row">
          <label class="field-label" for="org-path-input-float">{t("destinations.pathLabel")}</label>
          <input id="org-path-input-float" class="om-input org-row__input" bind:value={orgPath} placeholder={t("organizer.pathPlaceholder")} />
          <button type="button" class="om-btn om-btn--primary" title={t("organizer.pickFolderTitle")} on:click={pickOrgFolder}
            >{t("destinations.browse")}</button
          >
        </div>
        <div class="checks">
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeOrganized} /> {t("organizer.includeOrganized")}</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeComics} /> {t("organizer.includeComics")}</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includePending} /> {t("organizer.includePending")}</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.removeDuplicates} /> {t("organizer.removeDuplicates")}</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.groupSimilarImages} /> {t("organizer.groupSimilar")}</label>
        </div>
        <div class="org-row org-row--footer">
          <button type="button" class="om-btn om-btn--primary" on:click={startOrganizer} disabled={orgRunning}>{t("organizer.run")}</button>
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelOrganizer} disabled={!orgRunning}>{t("organizer.cancelRun")}</button>
          <span class="org-status">{orgDetail}</span>
          <span class="org-progress">{orgProgress}</span>
        </div>
      </div>
    </div>
  {/if}

  {#if destCtxMenu}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="ctx-menu-backdrop" role="presentation" on:click={closeDestCtxMenu}></div>
    <!-- svelte-ignore a11y-interactive-supports-focus -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="dest-ctx-menu om-panel om-panel--lift"
      role="menu"
      tabindex="-1"
      aria-label={t("menus.destAria")}
      style={`left:${destCtxMenu.x}px;top:${destCtxMenu.y}px`}
      on:click|stopPropagation
    >
      {#if destCtxMenu.source === "gallery"}
        <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openPreviewFromCtx}>{t("menus.viewFolder")}</button>
      {/if}
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openEditFromCtx}>{t("menus.edit")}</button>
      <button type="button" class="dest-ctx-menu__item dest-ctx-menu__item--danger" role="menuitem" on:click={removeDestFromCtx}
        >{t("menus.delete")}</button
      >
    </div>
  {/if}

  {#if pinnedCtxMenu}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="ctx-menu-backdrop" role="presentation" on:click={closePinnedCtxMenu}></div>
    <!-- svelte-ignore a11y-interactive-supports-focus -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="dest-ctx-menu om-panel om-panel--lift"
      role="menu"
      tabindex="-1"
      aria-label={t("menus.pinnedAria")}
      style={`left:${pinnedCtxMenu.x}px;top:${pinnedCtxMenu.y}px`}
      on:click|stopPropagation
    >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openEditPinnedFromCtx}>{t("menus.edit")}</button>
      <button type="button" class="dest-ctx-menu__item dest-ctx-menu__item--danger" role="menuitem" on:click={askUnpinPinnedFromCtx}
        >{t("menus.unpin")}</button
      >
    </div>
  {/if}

  {#if galleryItemCtxMenu}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="ctx-menu-backdrop" role="presentation" on:click={closeGalleryItemCtxMenu}></div>
    <!-- svelte-ignore a11y-interactive-supports-focus -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="dest-ctx-menu gallery-item-ctx-menu om-panel om-panel--lift"
      role="menu"
      tabindex="-1"
      aria-label={t("menus.galleryFileAria")}
      style={`left:${galleryItemCtxMenu.x}px;top:${galleryItemCtxMenu.y}px`}
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={() => void copyGalleryCtxPath()}
        >{t("contextGallery.copyPath")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={!galleryItemCtxMenu.thumbDataUrl || !String(galleryItemCtxMenu.thumbDataUrl).startsWith("data:")}
        on:click={() => void copyGalleryCtxFullImage()}
        >{t("contextGallery.copyThumb")}</button
      >
      <div class="gallery-item-ctx-menu__section" role="presentation">{t("contextGallery.moveSection")}</div>
      {#if destRows.length === 0}
        <div class="gallery-item-ctx-menu__hint">{t("contextGallery.noDestinations")}</div>
      {:else}
        {#each destRows as d, di (d.path + "\0gctx\0" + di)}
          <button
            type="button"
            class="dest-ctx-menu__item dest-ctx-menu__item--sub"
            role="menuitem"
            title={d.path}
            on:click={() => void moveGalleryItemFromCtxTo(d.path)}
            >{d.label}</button
          >
        {/each}
      {/if}
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={() => void openGalleryFileInfoFromCtx()}
        >{t("contextGallery.metadata")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item dest-ctx-menu__item--danger"
        role="menuitem"
        on:click={askDeleteGalleryItemFromCtx}>{t("contextGallery.delete")}</button
      >
    </div>
  {/if}

  {#if galleryFileInfoModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="overlay overlay--dim overlay--confirm"
      role="presentation"
      on:click|self={() => (galleryFileInfoModal = null)}
    >
      <div
        class="modal modal--confirm om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="gallery-file-info-title"
        tabindex="-1"
        on:click|stopPropagation
      >
        <header class="modal__head">
          <strong id="gallery-file-info-title">{t("contextGallery.metadataTitle")}</strong>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("contextGallery.closeInfo")}
            title={t("contextGallery.closeInfo")}
            on:click={() => (galleryFileInfoModal = null)}>✕</button
          >
        </header>
        <p class="settings-hint">{galleryFileInfoModal.name}</p>
        <p class="gallery-file-info__path">{galleryFileInfoModal.path}</p>
        <p class="gallery-file-info__meta">
          <span>{t("contextGallery.sizeLabel")}: {formatFileSizeBytes(galleryFileInfoModal.sizeBytes)}</span>
          ·
          <span>{t("contextGallery.modifiedLabel")}: {galleryFileInfoModal.mtimeIso}</span>
        </p>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--primary" on:click={() => (galleryFileInfoModal = null)}
            >{t("contextGallery.closeInfo")}</button
          >
        </div>
      </div>
    </div>
  {/if}

  {#if destFormOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim overlay--dest-form" role="presentation" on:click|self={closeDestForm}>
      <div
        class="modal modal--dest-form om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dest-form-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="modal__head">
          <strong id="dest-form-title"
            >{destFormMode === "add" ? t("destinations.formAddTitle") : t("destinations.formEditTitle")}</strong
          >
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("common.closeModalAria")}
            title={t("common.close")}
            on:click={closeDestForm}>✕</button
          >
        </header>
        <section class="dest-form-body">
          <label class="field-label" for="dest-form-label">{t("destinations.nameLabel")}</label>
          <input
            id="dest-form-label"
            class="om-input"
            type="text"
            bind:value={destFormLabel}
            placeholder={t("destinations.namePlaceholder")}
          />
          <label class="field-label" for="dest-form-path">{t("destinations.pathLabel")}</label>
          <div class="dest-form-path-row">
            <input
              id="dest-form-path"
              class="om-input"
              type="text"
              bind:value={destFormPath}
              placeholder={t("destinations.pathPlaceholder")}
            />
            <button type="button" class="om-btn om-btn--primary" on:click={pickDestFormFolder}
              >{t("destinations.browse")}</button
            >
          </div>
        </section>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={closeDestForm}>{t("common.cancel")}</button>
          <button type="button" class="om-btn om-btn--primary" on:click={saveDestForm}>{t("common.save")}</button>
        </div>
      </div>
    </div>
  {/if}

  {#if settingsOpen}
    <SettingsModal
      bind:thumbsPerPage
      bind:settingsThumbPresetIdx
      bind:settingsThumbScaleDraft
      bind:thumbGapPx
      bind:thumbImageRadiusPx
      bind:thumbTileRadiusPx
      bind:uiTheme
      bind:showThumbLabels
      bind:thumbFrameVisible
      bind:thumbCardStyle
      bind:keyboardShortcuts
      defaultShortcuts={defaultKeyboardShortcuts}
      themeNameLabel={themeNameLabel}
      onCancel={cancelSettingsModal}
      onSave={saveSettingsModal}
    />
  {/if}

  {#if confirmDeleteOpen}
    <ConfirmDeleteModal
      title={confirmDeleteTitle}
      detail={confirmDeleteDetail}
      confirmLabel={confirmDeleteConfirmLabel}
      bypassEnabled={confirmDeleteBypassEnabled}
      bypassLabel={confirmDeleteBypassLabel}
      bind:bypassChecked={confirmDeleteBypassChecked}
      onClose={closeConfirmDelete}
      onConfirm={runConfirmDelete}
    />
  {/if}

  {#if uiLoading}
    <LoadOverlay />
  {/if}

  <!-- Modal/Overlay Layer -->
  {#if viewMenuOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="view-menu-backdrop" role="presentation" on:click={() => (viewMenuOpen = false)}></div>
  {/if}
  <SidebarMarkers
    bind:routePickerOpen
    bind:pinMarkerOpen
    bind:folder
    bind:pinnedFolders
    bind:recentUnpinnedFolders
    bind:pinMarkerName
    bind:pinMarkerPath
    {pickGalleryFolder}
    {loadFolder}
    {pickRecentFolder}
    {onPinnedContextMenu}
    {markerLabelForPath}
    {pathTailLabel}
    {openPinMarkerModal}
    {closePinMarkerModal}
    {savePinMarkerModal}
  />
  <FullscreenPlayer
    bind:previewZoomOpen
    bind:previewZoomCarouselVisible
    bind:previewZoomName
    bind:previewZoomMode
    bind:previewZoomScale
    bind:previewZoomMediaType
    bind:zoomEditMode
    bind:zoomCropMode
    bind:previewZoomDestMode
    bind:previewZoomFileUrl
    bind:previewZoomDataUrl
    bind:zoomImgTransform
    bind:zoomHudVisible
    bind:zoomMiniRect
    bind:zoomCropMarqueeStyle
    bind:destRows
    bind:draggedDestIdx
    bind:previewZoomCanUndoMove
    bind:zoomNavItems
    bind:previewZoomPath
    bind:previewPanX
    bind:previewPanY
    bind:previewFillWidthAlignPending
    bind:zoomStageEl
    bind:zoomVideoEl
    bind:zoomImgEl
    bind:zoomMiniEl
    bind:zoomCarouselEl
    {moveZoomBy}
    {clampPanToStage}
    {alignFillWidthToTop}
    {zoomStep}
    {applyZoomRotate}
    {applyZoomCrop}
    {openConfirmDelete}
    {deleteCurrentZoomImage}
    {zoomWithWheel}
    {beginPan}
    {movePan}
    {endPan}
    {onZoomStageClick}
    {onZoomVideoMeta}
    {onZoomImageLoad}
    {onCropPointerDown}
    {onCropPointerMove}
    {onCropPointerUp}
    {openAddDestForm}
    {undoLastZoomMove}
    {requestMoveCurrentZoomToDestination}
    {onDestContextMenu}
    {onDestChipDragStart}
    {onDestChipDragEnd}
    {onDestDrop}
    {openPreviewZoom}
  />
</main>

