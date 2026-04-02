<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  let pollTimer: number | null = null;
  import { bridge, type GalleryItem } from "./lib/api";
  import { galleryGridCellPx, destPreviewGridMinPx } from "./lib/thumbScale";

  const BLANK_DRAG_IMG =
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  let folder = "";
  let galleryState: any = { page: 1, totalPages: 1, total: 0, selectedCount: 0 };
  let items: GalleryItem[] = [];
  /** Carpetas destino (mismo patrón reactivo que `items`: `let` + asignación tras el API). */
  let destRows: Array<{ label: string; path: string }> = [];
  let selectedPreview: { path: string; name: string; dataUrl: string | null } | null = null;
  let status = "Listo";
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
  let zoomHudVisible = false;
  let zoomHudTimer: ReturnType<typeof setTimeout> | null = null;
  let zoomStageEl: HTMLDivElement | null = null;
  let zoomCarouselEl: HTMLDivElement | null = null;
  let zoomImgEl: HTMLImageElement | null = null;
  let previewZoomNaturalW = 1;
  let previewZoomNaturalH = 1;
  let zoomMiniEl: HTMLDivElement | null = null;
  let galleryGridEl: HTMLDivElement | null = null;
  let galleryScrollEl: HTMLDivElement | null = null;
  let galleryPlainEl: HTMLElement | null = null;
  let galleryGridObservedEl: HTMLDivElement | null = null;
  let galleryGridResizeObserver: ResizeObserver | null = null;
  let galleryGridWidth = 0;
  const GALLERY_GRID_EDGE_PAD_PX = 8;
  let zoomNavItems: Array<{ path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }> = [];
  let deferredZoomMoveRefresh: { state: any; items: GalleryItem[] } | null = null;
  let galleryThumbHydrationToken = 0;
  let galleryLoadingMore = false;
  let galleryHasMore = false;
  let galleryAutoLoadRunId = 0;
  let previewThumbHydrationToken = 0;
  let previewScale = 1;
  let previewVisible = true;
  let previewDestPath = "";
  let destinationsMode = false;
  let folderBackStack: string[] = [];
  let folderForwardStack: string[] = [];
  /** Panel organizador en ventana flotante (tarea por lotes). */
  let orgPanelOpen = false;
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
  const thumbScalePresets = [
    { id: "compacto", label: "Compacto", value: 0.62 },
    { id: "medio", label: "Medio", value: 1.0 },
    { id: "comodo", label: "Cómodo", value: 1.18 },
    { id: "grande", label: "Grande", value: 1.45 },
    { id: "xgrande", label: "XL", value: 1.8 }
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
  let orgDetail = "Sin tarea";
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
  $: recentUnpinnedFolders = recentFolders.filter((p) => !pinnedFolders.includes(p));

  let ghostVisible = false;
  let ghostX = 0;
  let ghostY = 0;
  let ghostThumb: string | null = null;
  let ghostCount = 1;
  let ghostCaption = "";
  /** Listeners globales durante HTML5 DnD (Qt WebEngine: document + capture). */
  let dragWinMove: ((ev: DragEvent) => void) | null = null;
  let dragWinEnd: (() => void) | null = null;

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
  let destScaleDebounce: ReturnType<typeof setTimeout> | null = null;

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

  function mergeItemsKeepingBestThumb(prevItems: GalleryItem[], nextItems: GalleryItem[]): GalleryItem[] {
    const prevByPath = new Map(prevItems.map((x) => [x.path, x] as const));
    return nextItems.map((it) => {
      if (it.kind !== "image") return it;
      const prev = prevByPath.get(it.path);
      if (!prev || prev.kind !== "image") return it;
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
    const base = snapshot.filter((x) => x.kind === "image");
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
            x.kind === "image" && x.path === it.path
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
          if (previewZoomOpen && previewZoomPath === it.path) previewZoomDataUrl = out.thumbDataUrl;
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
    previewScale = Number(data.settings?.dest_preview_thumb_scale ?? 1);
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
    const initialPerPage = Number(data.settings?.gallery_thumbs_per_page ?? 48);
    const perPageRaw = Number.isFinite(initialPerPage) ? Math.round(initialPerPage) : 48;
    thumbsPerPage = perPageRaw <= 0 ? 0 : Math.max(12, perPageRaw);
    pageJumpDraft = Number(data.gallery?.page ?? 1);
    await syncDestinationsFromApi();
  };

  async function navigateToFolder(path: string, opts?: { pushHistory?: boolean }) {
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
    status = `Cargada carpeta: ${folder}`;
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
      status = "Ruta anclada";
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo anclar la ruta";
    }
  };

  const unpinFolder = async (path: string) => {
    try {
      const out = await bridge.galleryUnpinFolder(path);
      pinnedFolders = Array.isArray(out.pinnedFolders) ? out.pinnedFolders : pinnedFolders.filter((x) => x !== path);
      status = "Ruta desanclada";
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo quitar el anclaje";
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
      status = e instanceof Error ? e.message : "No se pudo abrir el selector de carpeta";
    }
  };

  const pickOrgFolder = async () => {
    try {
      const out = await bridge.dialogPickFolder(orgPath);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      orgPath = out.path;
      status = `Ruta organizador: ${orgPath}`;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo abrir el selector de carpeta";
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
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
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
    thumbsPerPageBackup = thumbsPerPage;
    thumbGapPxBackup = thumbGapPx;
    showThumbLabelsBackup = showThumbLabels;
    thumbCardStyleBackup = thumbCardStyle;
    thumbFrameVisibleBackup = thumbFrameVisible;
    thumbImageRadiusPxBackup = thumbImageRadiusPx;
    thumbTileRadiusPxBackup = thumbTileRadiusPx;
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
    thumbsPerPage = thumbsPerPageBackup;
    thumbGapPx = thumbGapPxBackup;
    showThumbLabels = showThumbLabelsBackup;
    thumbCardStyle = thumbCardStyleBackup;
    thumbFrameVisible = thumbFrameVisibleBackup;
    thumbImageRadiusPx = thumbImageRadiusPxBackup;
    thumbTileRadiusPx = thumbTileRadiusPxBackup;
    settingsOpen = false;
  };

  const saveSettingsModal = async () => {
    const parsedPerPage = Number(thumbsPerPage);
    const perPageRaw = Number.isFinite(parsedPerPage) ? Math.round(parsedPerPage) : 48;
    const n = perPageRaw <= 0 ? 0 : Math.max(12, perPageRaw);
    thumbsPerPage = n;
    const ts = Math.max(0.01, Math.min(2.25, Number(settingsThumbScaleDraft) || 1));
    thumbScale = ts;
    await bridge.settingsPatch({
      gallery_thumbs_per_page: n, // 0 = sin límite
      gallery_thumb_scale: Number(ts.toFixed(3)),
      web_thumb_gap_px: Math.max(0, Math.round(thumbGapPx)),
      web_show_thumb_labels: Boolean(showThumbLabels),
      web_thumb_card_style: thumbCardStyle,
      web_thumb_frame_visible: Boolean(thumbFrameVisible),
      web_thumb_image_radius_px: Math.round(thumbImageRadiusPx),
      web_thumb_tile_radius_px: Math.round(thumbTileRadiusPx)
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
    confirmDeleteConfirmLabel = opts?.confirmLabel ?? "Eliminar";
    confirmDeleteBypassEnabled = Boolean(opts?.bypassEnabled);
    confirmDeleteBypassLabel = opts?.bypassLabel ?? "No volver a preguntar por ahora";
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
    try {
      const out = await trackLoad(bridge.galleryDeleteSelected());
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      const deleted = Number(out.deleteResult?.deleted ?? 0);
      const errors = Number(out.deleteResult?.errors ?? 0);
      status = `Eliminadas ${deleted} imágenes${errors ? ` · errores ${errors}` : ""}`;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudieron eliminar las imágenes seleccionadas";
    }
  }

  async function deleteCurrentZoomImage() {
    if (!previewZoomPath) return;
    try {
      const out = await trackLoad(bridge.galleryDeletePaths([previewZoomPath]));
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
      const deleted = Number(out.deleteResult?.deleted ?? 0);
      const errors = Number(out.deleteResult?.errors ?? 0);
      status = `Eliminadas ${deleted} imágenes${errors ? ` · errores ${errors}` : ""}`;
      previewZoomOpen = false;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo eliminar la imagen actual";
    }
  }

  const clickItem = async (it: GalleryItem) => {
    if (suppressNextGalleryClick) {
      suppressNextGalleryClick = false;
      return;
    }
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
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
      } else {
        if (!previewVisible && it.kind === "image") {
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
      }
    } finally {
      galleryActionBusy = false;
    }
  };

  const selectPage = async () => {
    const prevItems = items;
    const out = await bridge.gallerySelectPage();
    galleryState = out.state;
    items = mergeItemsKeepingBestThumb(prevItems, out.items);
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
          status = `Movidas ${out.moveResult?.moved ?? 0} · errores ${out.moveResult?.errors ?? 0} · cola ${galleryMoveQueue.length}`;
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : "Error al procesar cola de movimientos";
        }
      }
    } finally {
      galleryMoveWorkerRunning = false;
    }
  }

  function getSelectedGalleryPaths(): string[] {
    return items.filter((x) => x.kind === "image" && x.selected).map((x) => x.path);
  }

  function askConfirmMoveSelected(destPath: string) {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = "No hay imágenes seleccionadas para mover";
      return;
    }
    openConfirmDelete(
      "Mover selección",
      `¿Mover ${selectedPaths.length} imágenes al destino seleccionado?`,
      async () => {
        await moveToDest(destPath);
      },
      { confirmLabel: "Mover" }
    );
  }

  const moveToDest = async (path: string) => {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = "No hay imágenes seleccionadas para mover";
      return;
    }
    const selectedSet = new Set(selectedPaths);
    items = items.map((it) =>
      it.kind === "image" && selectedSet.has(it.path) ? { ...it, selected: false } : it
    );
    galleryState = {
      ...galleryState,
      selectedCount: Math.max(0, Number(galleryState?.selectedCount ?? 0) - selectedPaths.length),
    };
    galleryMoveQueue = [...galleryMoveQueue, { srcPaths: selectedPaths, destPath: path }];
    status = `Encoladas ${selectedPaths.length} imágenes · cola ${galleryMoveQueue.length}`;
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
      status = "No se pudo aplicar el tamaño de miniaturas";
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

  const openDestPreview = async (path: string) => {
    previewDestPath = path;
    previewSelectedPaths = [];
    previewOpen = true;
    await refreshDestPreview();
  };

  const refreshDestPreview = async () => {
    const w = Math.max(320, Math.round(window.innerWidth * DEST_MODAL_FRAC));
    const out = await bridge.destinationPreview(previewDestPath, previewScale, w);
    previewItems = out.items;
    previewThumbHydrationToken++;
    void hydratePreviewThumbsHq(previewItems, previewScale, previewThumbHydrationToken);
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
      status = "Selecciona elementos del modal primero";
      return;
    }
    if (!folder.trim()) {
      status = "Carga una carpeta en Ruta para recibir los archivos";
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
      status = `Movidos ${moved} del modal a la ruta actual${errors ? ` · errores ${errors}` : ""}`;
      previewSelectedPaths = [];
      await refreshDestPreview();
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudieron mover los elementos seleccionados";
    }
  }

  function openPreviewZoom(
    it: { path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" },
    opts?: {
      preserveCarousel?: boolean;
      preserveMode?: boolean;
      navItems?: Array<{ path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }>;
    }
  ) {
    if (opts?.navItems) zoomNavItems = opts.navItems;
    previewZoomPath = it.path;
    previewZoomName = it.name;
    // Importante: no mostrar el thumbnail "cuadrado" (recortado) como si fuera la imagen completa.
    // La vista principal debe venir de `galleryPreview` (contain) para garantizar que en "Completa" se vea 100% sin recortes.
    previewZoomDataUrl = null;
    previewZoomScale = 1;
    previewPanX = 0;
    previewPanY = 0;
    if (!opts?.preserveMode) previewZoomMode = "fit";
    previewFillWidthAlignPending = previewZoomMode === "fillWidth";
    previewZoomNaturalW = 1;
    previewZoomNaturalH = 1;
    previewZoomCarouselVisible = opts?.preserveCarousel ? previewZoomCarouselVisible : true;
    zoomHudVisible = false;
    previewZoomOpen = true;
    bridge
      .galleryPreview(it.path, 2200, 1600)
      .then((pr) => {
        if (previewZoomOpen && previewZoomPath === it.path) previewZoomDataUrl = pr.dataUrl ?? null;
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
    const tile = el?.closest?.(".pv-tile[data-preview-path]") as HTMLElement | null;
    const path = tile?.dataset?.previewPath;
    if (!path) return;
    applyPreviewRangeSelection(previewRangeAnchorPath, path, previewRangeMode);
  }

  function onPreviewTileClick(it: { path: string; name: string; thumbDataUrl?: string | null }) {
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

  function getVisibleGalleryImagePaths(): string[] {
    return items.filter((x) => x.kind === "image").map((x) => x.path);
  }

  function isGalleryTileSelected(it: GalleryItem): boolean {
    if (!destinationsMode || it.kind !== "image") return false;
    return Boolean(it.selected);
  }

  function applyGalleryRangeSelection(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const imagePaths = getVisibleGalleryImagePaths();
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
      it.kind === "image"
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
    if (!destinationsMode || it.kind !== "image") return;
    // Por defecto: selección por rango. Con Ctrl: modo arrastre.
    if (e.ctrlKey) return;
    e.preventDefault();
    const baseSelected = items
      .filter((x) => x.kind === "image" && x.selected)
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
    } catch {
      const prevItems = items;
      const out = await bridge.galleryRefreshItems();
      galleryState = out.state;
      items = mergeItemsKeepingBestThumb(prevItems, out.items);
    }
  }


  function zoomStep(delta: number) {
    // Permite alejar más allá de 100% para que, si el stage efectivo es menor
    // (por carrusel/cabecera), siempre puedas ver la imagen completa.
    previewZoomScale = Math.min(4, Math.max(0.5, Number((previewZoomScale + delta).toFixed(2))));
    touchZoomHud();
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }

  function getPanLimits() {
    if (!zoomStageEl || !zoomImgEl) return { x: 0, y: 0 };
    const sr = zoomStageEl.getBoundingClientRect();
    const ir = zoomImgEl.getBoundingClientRect();
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
  $: if (previewZoomOpen && zoomStageEl && zoomImgEl) {
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

  function beginPan(e: PointerEvent) {
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
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
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
    (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
  }

  function toggleZoomCarousel() {
    previewZoomCarouselVisible = !previewZoomCarouselVisible;
  }

  function onZoomStageClick(e: MouseEvent) {
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
    previewPanX = 0;
    previewPanY = 0;
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
    status = `Imagen en cola de movimiento (${zoomMoveQueue.length})`;
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
      "Mover imagen",
      "¿Mover la imagen actual al destino seleccionado?",
      async () => {
        await moveCurrentZoomToDestination(destPath);
      },
      {
        confirmLabel: "Mover",
        bypassEnabled: true,
        bypassLabel: "No volver a preguntar en esta sesión de fullscreen",
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
            ? `Imagen movida (${zoomMoveQueue.length} en cola)`
            : `No se movió la imagen${errors ? " · con errores" : ""}`;
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : "Error en cola de movimientos";
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
      status = moved > 0 ? "Movimiento revertido" : "No hay movimiento para deshacer";
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo deshacer el movimiento";
    }
  }

  function onZoomImageLoad() {
    if (!zoomImgEl) return;
    previewZoomNaturalW = Math.max(1, zoomImgEl.naturalWidth || 1);
    previewZoomNaturalH = Math.max(1, zoomImgEl.naturalHeight || 1);
    clampPanToStage();
    alignFillWidthToTop();
  }

  function openZoomFromGallery(it: { path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }) {
    const nav = items
      .filter((x) => x.kind === "image")
      .map((x) => ({ path: x.path, name: x.name, thumbDataUrl: x.thumbDataUrl, thumbQuality: x.thumbQuality }));
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

  /** Ancho mínimo de pista en el modal destino: auto-fill sin columna cortada ni scroll horizontal. */
  $: destModalGridMinPx = destPreviewGridMinPx(previewScale);

  const saveThumbScale = async () => {
    await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
    await reload({ silent: true });
  };

  const saveDestScale = async () => {
    await bridge.settingsPatch({ dest_preview_thumb_scale: Number(previewScale.toFixed(3)) });
    await refreshDestPreview();
  };

  function scheduleDestScaleSave() {
    if (destScaleDebounce) clearTimeout(destScaleDebounce);
    destScaleDebounce = setTimeout(() => {
      destScaleDebounce = null;
      saveDestScale().catch(() => undefined);
    }, 280);
  }

  const startOrganizer = async () => {
    const out = await bridge.organizerStart(orgPath, orgOptions);
    if (!out.ok) {
      status = out.error ?? "No se pudo iniciar";
      return;
    }
    orgRunning = true;
    status = "Organizador iniciado";
  };

  const cancelOrganizer = async () => {
    await bridge.organizerCancel();
  };

  const pollOrganizer = async () => {
    const out = await bridge.organizerStatus();
    orgRunning = Boolean(out.running);
    orgDetail = out.progress?.detail ?? "Sin tarea";
    orgProgress = `${out.progress?.current ?? 0}/${out.progress?.total ?? 0}`;
    if (!orgRunning && out.done) {
      const stats = out.done.stats ?? {};
      status = out.done.error
        ? `Error: ${out.done.error}`
        : `Finalizado · movidas ${stats.moved_media ?? 0}, cbz ${stats.moved_cbz ?? 0}, otros ${stats.moved_other ?? 0}`;
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
    document.body.classList.remove("om-dragging");
    clearGhostListeners();
  }

  function endDragSessionAfterGesture() {
    suppressNextGalleryClick = true;
    endDragSession();
  }

  function onTileDragStart(e: DragEvent, it: GalleryItem) {
    if (!destinationsMode || it.kind !== "image") return;
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
      ghostX = ev.clientX;
      ghostY = ev.clientY;
      const el = document.elementFromPoint(ev.clientX, ev.clientY);
      const card = el?.closest?.("[data-dest-path]") as HTMLElement | null;
      dragOverDestPath = card?.dataset?.destPath ?? null;
    };
    dragWinEnd = () => {
      endDragSessionAfterGesture();
    };
    document.addEventListener("dragover", dragWinMove, dragOpts);
    document.addEventListener("dragend", dragWinEnd, dragOpts);
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
      status = "Destinos reordenados";
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudieron reordenar los destinos";
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
      status = e instanceof Error ? e.message : "No se pudo abrir el selector de carpeta";
    }
  }

  async function saveDestForm() {
    const label = destFormLabel.trim();
    const path = destFormPath.trim();
    if (!path) {
      status = "Indica una ruta de carpeta";
      return;
    }
    try {
      if (destFormMode === "add") {
        await trackLoad(bridge.destinationsAdd(label, path));
        await syncDestinationsFromApi();
        status = "Carpeta destino añadida";
      } else if (destFormIdx !== null) {
        await trackLoad(bridge.destinationsEdit(destFormIdx, label, path));
        await syncDestinationsFromApi();
        status = "Destino actualizado";
      }
      destFormOpen = false;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo guardar el destino";
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
      status = "Destino eliminado";
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo eliminar";
    }
  }

  // Tamaño objetivo directo: la grilla flexible (minmax + 1fr) absorbe cambios finos
  // de ancho y evita hueco fijo en el borde derecho.
  $: gridCellTargetPx = galleryGridCellPx(thumbScale);
  $: gridCellPx = Math.max(72, Number(gridCellTargetPx.toFixed(2)));
  $: settingsPreviewCellPx = galleryGridCellPx(settingsThumbScaleDraft);

  $: if (galleryScrollEl && galleryScrollEl !== galleryGridObservedEl) {
    galleryGridResizeObserver?.disconnect();
    galleryGridObservedEl = galleryScrollEl;
    galleryGridResizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      // Usar ancho de borde evita saltos por cambios de scroll interno.
      const borderInline =
        Array.isArray((entry as any).borderBoxSize) && (entry as any).borderBoxSize.length > 0
          ? Number((entry as any).borderBoxSize[0]?.inlineSize ?? 0)
          : 0;
      const fallback = Math.max(0, Math.round(galleryScrollEl?.getBoundingClientRect().width ?? entry.contentRect.width));
      galleryGridWidth = Math.max(0, Math.round(borderInline || fallback));
    });
    galleryGridResizeObserver.observe(galleryScrollEl);
  }

  $: if (!destinationsMode && !previewZoomDestMode) {
    destCtxMenu = null;
    if (destFormOpen) destFormOpen = false;
  }

  $: if (!previewZoomOpen && deferredZoomMoveRefresh) {
    applyGalleryRefreshFromMove(deferredZoomMoveRefresh.state, deferredZoomMoveRefresh.items);
    deferredZoomMoveRefresh = null;
  }

  $: if (!previewZoomOpen) {
    previewZoomSkipMoveConfirm = false;
  }

  $: if (previewZoomOpen && previewZoomCarouselVisible && zoomCarouselEl && previewZoomPath) {
    const active = zoomCarouselEl.querySelector<HTMLElement>(".zoom-carousel__item--active");
    if (active) {
      active.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }

  onMount(async () => {
    try {
      await waitForPywebviewApi();
    } catch {
      status = "API de escritorio no disponible. Reabre la app o usa npm run dev.";
      return;
    }
    await loadInitial();
    if (folder) {
      try {
        await loadFolder(false);
      } catch {
        status = "No se pudo restaurar la última carpeta; revisa la ruta o selecciónala en el modal.";
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
    if (destScaleDebounce) clearTimeout(destScaleDebounce);
    if (zoomHudTimer) clearTimeout(zoomHudTimer);
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  });
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
    if (previewZoomOpen) {
      const activeEl = (document.activeElement as HTMLElement | null) ?? null;
      const isTypingEl = Boolean(
        activeEl &&
          (activeEl.isContentEditable ||
            activeEl.tagName === "INPUT" ||
            activeEl.tagName === "TEXTAREA" ||
            activeEl.closest('[contenteditable="true"]'))
      );
      const typingInDestForm = Boolean(activeEl?.closest(".modal--dest-form"));
      if (destFormOpen && isTypingEl && typingInDestForm) return;
      const key = e.key.toLowerCase();
      if (["arrowleft", "arrowup", "a", "w"].includes(key)) {
        e.preventDefault();
        moveZoomBy(-1);
        return;
      }
      if (["arrowright", "arrowdown", "d", "s"].includes(key)) {
        e.preventDefault();
        moveZoomBy(1);
        return;
      }
    }
    if (e.key !== "Escape") return;
    if (destCtxMenu) closeDestCtxMenu();
    else if (destFormOpen) closeDestForm();
    else if (settingsOpen) settingsOpen = false;
    else if (previewZoomOpen) previewZoomOpen = false;
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
  <header class="tabs-bar om-panel">
    <nav class="tabs__nav">
      <button
        type="button"
        class="om-btn om-btn--tab"
        class:om-btn--active={destinationsMode}
        on:click={() => (destinationsMode = !destinationsMode)}
        title="Activa/desactiva modo selección y panel de destinos"
      >Destinos</button>
      <button
        type="button"
        class="om-btn om-btn--tab"
        on:click={() => {
          orgPath = folder || orgPath;
          orgPanelOpen = true;
        }}
      >Organizar</button>
    </nav>
    <div class="route__row route__row--inline">
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Retroceder" on:click={goBackFolder} disabled={folderBackStack.length === 0}>←</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Avanzar" on:click={goForwardFolder} disabled={folderForwardStack.length === 0}>→</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Carpeta superior" on:click={goUpFolder}>↑</button>
      <div class="route__path-wrap">
        <input
          id="gallery-folder-input"
          class="om-input route__path"
          type="text"
          bind:value={folder}
          placeholder="Ruta de carpeta…"
          title="Pega la ruta o pulsa el icono de carpeta"
          on:focus={() => (routePickerOpen = true)}
        />
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--icon route__path-action"
          title={pinnedFolders.includes(folder.trim()) ? "Quitar anclaje de esta ruta" : "Anclar esta ruta"}
          on:click={() => (pinnedFolders.includes(folder.trim()) ? unpinFolder(folder) : pinFolder(folder))}
        >{pinnedFolders.includes(folder.trim()) ? "★" : "☆"}</button>
        <button type="button" class="om-btn om-btn--ghost om-btn--icon route__path-action" title="Recargar galería" on:click={reload}>↻</button>
        <button type="button" class="om-btn om-btn--ghost om-btn--icon route__path-action" title="Explorar carpeta" on:click={pickGalleryFolder}>
          <svg class="route-folder-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path fill="currentColor" d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z" />
          </svg>
        </button>
      </div>
    </div>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--icon om-btn--settings"
      title="Ajustes"
      aria-label="Ajustes"
      on:click={openSettingsModal}
    >
      <svg class="settings-gear" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    </button>
  </header>

  {#if routePickerOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim" role="presentation" on:click|self={() => (routePickerOpen = false)}>
      <div
        class="modal modal--route-picker om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="route-picker-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="modal__head">
          <strong id="route-picker-title">Elegir ruta de galería</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={() => (routePickerOpen = false)}>✕</button>
        </header>
        <section class="route-picker__body">
          <div class="route-picker__input-row">
            <input class="om-input route-picker__input" bind:value={folder} placeholder="Ruta de carpeta…" />
            <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Explorar carpeta" on:click={pickGalleryFolder}>
              <svg class="route-folder-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="currentColor" d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z" />
              </svg>
            </button>
            <button type="button" class="om-btn om-btn--primary" on:click={loadFolder}>Abrir</button>
          </div>
          {#if pinnedFolders.length > 0}
            <div class="recent-folders__head">
              <span class="field-label">Rutas ancladas</span>
            </div>
            <div class="recent-folders__list">
              {#each pinnedFolders as p}
                <div class="recent-folders__chip-wrap">
                  <button type="button" class="om-btn om-btn--ghost recent-folders__chip" title={p} on:click={() => pickRecentFolder(p)}>
                    {p.length > 56 ? `${p.slice(0, 53)}…` : p}
                  </button>
                  <button type="button" class="om-btn om-btn--ghost recent-folders__pin" title="Quitar anclaje" on:click={() => unpinFolder(p)}>★</button>
                </div>
              {/each}
            </div>
          {/if}
          {#if recentUnpinnedFolders.length > 0}
            <div class="recent-folders__head">
              <span class="field-label">Rutas recientes</span>
            </div>
            <div class="recent-folders__list">
              {#each recentUnpinnedFolders as p}
                <div class="recent-folders__chip-wrap">
                  <button type="button" class="om-btn om-btn--ghost recent-folders__chip" title={p} on:click={() => pickRecentFolder(p)}>
                    {p.length > 56 ? `${p.slice(0, 53)}…` : p}
                  </button>
                  <button type="button" class="om-btn om-btn--ghost recent-folders__pin" title="Anclar ruta" on:click={() => pinFolder(p)}>☆</button>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </div>
    </div>
  {/if}

  

  {#if destinationsMode}
    <div
      class="destinos-work"
      class:destinos-work--drag={destSplitDrag}
      style="grid-template-rows:minmax(0,1fr)"
    >
      <div class="destinos-work__top">
        <section
          class="content"
          style={previewVisible
            ? `grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`
            : "grid-template-columns:minmax(0,1fr)"}
        >
          <article class="gallery om-panel om-panel--lift gallery--with-float">
            <div class="gallery__scroll" bind:this={galleryScrollEl} on:scroll={onGalleryScroll}>
              <div class="grid" bind:this={galleryGridEl} style={`--cell:${gridCellPx}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px`}>
              {#each items as it (it.path)}
                <!-- div: en WebEngine <button>+drag y <img draggable> nativo suelen bloquear el DnD. -->
                <div
                  role="button"
                  tabindex="0"
                  class="tile"
                  data-item-path={it.path}
                  class:selected={isGalleryTileSelected(it)}
                  draggable={it.kind === "image" && !galleryRangeSelecting}
                  on:pointerdown={(e) => onGalleryTilePointerDown(e, it)}
                  on:pointerenter={() => onGalleryTilePointerEnter(it.path)}
                  on:dragstart={(e) => onTileDragStart(e, it)}
                  on:click={() => {
                    if (galleryRangeSuppressClick) return;
                    clickItem(it);
                  }}
                  on:dblclick={() => {
                    if (it.kind === "image") openZoomFromGallery(it);
                  }}
                  on:keydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      clickItem(it);
                    }
                  }}
                >
                  {#if it.thumbDataUrl}
                    <img
                      src={it.thumbDataUrl}
                      alt=""
                      class:thumb--lq={it.thumbQuality === "lq"}
                      draggable={false}
                      loading="lazy"
                      decoding="async"
                    />
                  {:else}
                    <div class="folder-ph" class:folder-ph--folder={it.kind !== "image"}>
                      {#if it.kind === "image"}
                        Sin preview
                      {:else if it.kind === "folder_up"}
                        <span class="folder-ph__icon" aria-hidden="true">↩</span>
                        <span class="folder-ph__label">Subir</span>
                      {:else}
                        <svg class="folder-ph__svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                          <path
                            d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z"
                            fill="currentColor"
                          />
                        </svg>
                      {/if}
                    </div>
                  {/if}
                  {#if showThumbLabels || it.kind !== "image"}<span class="tile__name" class:tile__name--folder={it.kind !== "image"}>{it.name}</span>{/if}
                </div>
              {/each}
              <div class="grid-end-spacer" aria-hidden="true"></div>
              </div>
              <div class="selection-float" role="toolbar" aria-label="Selección">
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectPage}>Pág.</button>
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearSelection}>Quitar</button>
                <button
                  type="button"
                  class="om-btn om-btn--ghost om-btn--mini"
                  disabled={Number(galleryState.selectedCount || 0) === 0}
                  on:click={() =>
                    openConfirmDelete(
                      "Eliminar selección",
                      `¿Eliminar ${galleryState.selectedCount} imágenes seleccionadas? Esta acción no se puede deshacer.`,
                      deleteSelectedGalleryItems
                    )}
                >Eliminar</button>
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertSelection}>Invertir</button>
                <span class="selection-float__count" title="Seleccionadas">{galleryState.selectedCount}</span>
              </div>
              <div class="dest-float-chips" aria-label="Carpetas destino">
                <button type="button" class="om-btn om-btn--ghost om-btn--compact dest-float-add" on:click={openAddDestForm}>
                  + Agregar carpeta
                </button>
                {#if destRows.length === 0}
                  <span class="dest-float-empty">No hay carpetas destino</span>
                {/if}
                {#each destRows as d, i (d.path + "\0" + i)}
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
          </article>

          {#if previewVisible}
            <div
              class="splitter"
              role="separator"
              aria-orientation="vertical"
              aria-label="Arrastrar para repartir galería y vista previa"
              on:pointerdown={beginSplitDrag}
            ></div>

            <aside class="preview om-panel">
              {#if selectedPreview?.dataUrl}
                <img class="preview__img" src={selectedPreview.dataUrl} alt={selectedPreview.name} />
              {:else}
                <div class="preview__empty">Selecciona una miniatura</div>
              {/if}
              <div class="preview__meta">{selectedPreview?.path ?? ""}</div>
            </aside>
          {/if}
        </section>
      </div>
    </div>
  {:else}
    <section
      class="content"
      style={previewVisible
        ? `grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`
        : "grid-template-columns:minmax(0,1fr)"}
    >
      <article class="gallery om-panel om-panel--lift" bind:this={galleryPlainEl} on:scroll={onGalleryScroll}>
        <div class="grid" bind:this={galleryGridEl} style={`--cell:${gridCellPx}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px`}>
          {#each items as it (it.path)}
            <button
              type="button"
              class="tile"
              data-item-path={it.path}
              class:selected={it.selected && destinationsMode}
              draggable={destinationsMode && it.kind === "image"}
              on:dragstart={(e) => onTileDragStart(e, it)}
              on:click={() => clickItem(it)}
              on:dblclick={() => {
                if (it.kind === "image") openZoomFromGallery(it);
              }}
            >
              {#if it.thumbDataUrl}
                <img src={it.thumbDataUrl} alt="" class:thumb--lq={it.thumbQuality === "lq"} loading="lazy" decoding="async" />
              {:else}
                <div class="folder-ph" class:folder-ph--folder={it.kind !== "image"}>
                  {#if it.kind === "image"}
                    Sin preview
                  {:else if it.kind === "folder_up"}
                    <span class="folder-ph__icon" aria-hidden="true">↩</span>
                    <span class="folder-ph__label">Subir</span>
                  {:else}
                    <svg class="folder-ph__svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path
                        d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z"
                        fill="currentColor"
                      />
                    </svg>
                  {/if}
                </div>
              {/if}
              {#if showThumbLabels || it.kind !== "image"}<span class="tile__name" class:tile__name--folder={it.kind !== "image"}>{it.name}</span>{/if}
            </button>
          {/each}
        </div>
      </article>

      {#if previewVisible}
        <div
          class="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label="Arrastrar para repartir galería y vista previa"
          on:pointerdown={beginSplitDrag}
        ></div>

        <aside class="preview om-panel">
          {#if selectedPreview?.dataUrl}
            <img class="preview__img" src={selectedPreview.dataUrl} alt={selectedPreview.name} />
          {:else}
            <div class="preview__empty">Selecciona una miniatura</div>
          {/if}
          <div class="preview__meta">{selectedPreview?.path ?? ""}</div>
        </aside>
      {/if}
    </section>
  {/if}

  <footer class="pager om-panel pager--bar" aria-label="Paginación y estado">
    {#if thumbsPerPage !== 0}
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Primera página" on:click={() => goPage(1)}>|«</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Anterior" on:click={() => goPage(Math.max(1, galleryState.page - 1))}>‹</button>
      {#each pageLinks as item}
        {#if item === "gap"}
          <span class="pager__gap" aria-hidden="true">…</span>
        {:else}
          <button
            type="button"
            class="om-btn om-btn--ghost pager__num"
            class:om-btn--primary={item === galleryState.page}
            title="Ir a la página {item}"
            on:click={() => goPage(item)}>{item}</button>
        {/if}
      {/each}
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Siguiente" on:click={() => goPage(Math.min(galleryState.totalPages, galleryState.page + 1))}>›</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Última página" on:click={() => goPage(galleryState.totalPages)}>»|</button>
      <span class="pager__google-line">{galleryState.total} imágenes · página {galleryState.page} de {galleryState.totalPages}</span>
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
      <button type="button" class="om-btn om-btn--primary om-btn--compact" on:click={jumpToPageDraft}>Ir</button>
    {:else}
      <span class="pager__google-line">
        Cargadas {Number(galleryState?.endIndex ?? 0)}/{Number(galleryState?.total ?? 0)} imágenes · {Number(galleryState?.totalElements ?? Number(galleryState?.total ?? 0) + Number(galleryState?.subfoldersCount ?? 0))} elementos · peso total {Number(galleryState?.totalBytes ?? -1) < 0 ? "calculando…" : formatBytes(Number(galleryState?.totalBytes ?? 0))}
      </span>
    {/if}
    <div class="grow"></div>
    <span class="status-line">{status}</span>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact"
      title={previewVisible ? "Ocultar vista previa" : "Mostrar vista previa"}
      on:click={togglePreviewVisible}
    >{previewVisible ? "👁 Vista previa" : "🙈 Sin preview"}</button>
    <span
      class="field-label pager__split-label"
      title="Arrastra la barra entre galería y vista previa para el ancho del panel"
      >Panel derecho ~{Math.round(previewRatio * 100)}%</span>
    <label class="field-label pager__thumb-label" for="route-thumb-scale-footer">Miniaturas {Math.round(thumbScale * 100)}%</label>
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
      aria-label="Cerrar vista previa del destino"
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
          <strong id="dest-preview-title">Destino: {previewDestPath}</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={() => (previewOpen = false)}>✕</button>
        </header>
        <section class="modal__ctrl">
          <label class="field-label" for="dest-preview-scale">Miniaturas en vista previa {Math.round(previewScale * 100)}%</label>
          <input
            id="dest-preview-scale"
            class="om-range"
            type="range"
            min="0.7"
            max="2.1"
            step="0.01"
            bind:value={previewScale}
            on:input={scheduleDestScaleSave}
          />
          <div class="modal__pick-tools" role="toolbar" aria-label="Selección del modal de destino">
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              on:click={() => (previewSelectionMode ? exitPreviewSelectionMode() : (previewSelectionMode = true))}
              title={previewSelectionMode ? "Salir del modo selección" : "Entrar al modo selección"}
            >
              {previewSelectionMode ? "Salir selección" : "Modo selección"}
            </button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={selectAllPreviewItems}>Seleccionar todo</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={clearPreviewSelection}>Limpiar</button>
            <button
              type="button"
              class="om-btn om-btn--primary om-btn--compact"
              disabled={previewSelectedPaths.length === 0}
              on:click={movePreviewSelectionToCurrentRoute}
              title="Mueve los elementos seleccionados a la carpeta cargada en la pestaña Ruta"
            >
              Mover seleccionados a Ruta ({previewSelectedPaths.length})
            </button>
          </div>
        </section>
        <div class="modal__scroll">
          <section class="dest-grid" style={`--pv-min:${destModalGridMinPx}px`}>
            {#each previewItems as it}
              <div
                class="pv-tile"
                data-preview-path={it.path}
                class:pv-tile--selected={previewSelectedPaths.includes(it.path)}
                role="button"
                tabindex="0"
                on:pointerdown={(e) => onPreviewTilePointerDown(e, it)}
                on:pointerenter={() => onPreviewTilePointerEnter(it.path)}
                on:pointerup={cancelPreviewLongPress}
                on:pointerleave={cancelPreviewLongPress}
                on:pointercancel={cancelPreviewLongPress}
                on:click={() => onPreviewTileClick(it)}
                on:keydown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onPreviewTileClick(it);
                  }
                }}
              >
                {#if previewSelectionMode}
                  <button
                    type="button"
                    class="pv-tile__pick"
                    aria-label="Ver en pantalla completa"
                    title="Ver en pantalla completa"
                    on:click|stopPropagation={() => openPreviewZoom(it)}
                  >
                    ⛶
                  </button>
                {/if}
                {#if it.thumbDataUrl}<img src={it.thumbDataUrl} alt="" class:thumb--lq={it.thumbQuality === "lq"} />{/if}
                <span class="pv-tile__name">{it.name}</span>
              </div>
            {/each}
          </section>
        </div>
      </div>
    </div>
  {/if}

  {#if previewZoomOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="overlay overlay--zoom"
      role="button"
      tabindex="-1"
      aria-label="Cerrar vista previa ampliada"
      on:click={() => (previewZoomOpen = false)}
      on:keydown={(e) => {
        if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          previewZoomOpen = false;
        }
      }}
    >
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div
        class="zoom-modal"
        class:zoom-modal--carousel-hidden={!previewZoomCarouselVisible}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        on:click|stopPropagation
      >
        <header class="zoom-modal__head">
          <strong>{previewZoomName}</strong>
          <div class="zoom-modal__tools">
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" title="Anterior (A/W/←/↑)" on:click={() => moveZoomBy(-1)}>←</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" title="Siguiente (D/S/→/↓)" on:click={() => moveZoomBy(1)}>→</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              title="Alternar entre ver completa y rellenar ancho"
              on:click={() => {
                previewZoomMode = previewZoomMode === "fit" ? "fillWidth" : "fit";
                previewPanX = 0;
                previewPanY = 0;
                clampPanToStage();
                previewFillWidthAlignPending = previewZoomMode === "fillWidth";
                if (previewZoomMode === "fillWidth") alignFillWidthToTop();
              }}
            >
              {previewZoomMode === "fit" ? "Completa" : "Rellenar ancho"}
            </button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" title="Alejar" on:click={() => zoomStep(-0.2)}>−</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              title="Restablecer zoom"
              on:click={() => {
                previewZoomScale = 1;
                if (previewZoomMode === "fit") {
                  previewPanX = 0;
                  previewPanY = 0;
                }
              }}
            >{Math.round(previewZoomScale * 100)}%</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" title="Acercar" on:click={() => zoomStep(0.2)}>＋</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              title="Mostrar destinos en fullscreen"
              on:click={() => (previewZoomDestMode = !previewZoomDestMode)}
            >Destinos</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact zoom-trash-btn"
              title="Eliminar imagen actual"
              on:click={() =>
                openConfirmDelete(
                  "Eliminar imagen",
                  "¿Eliminar la imagen actual? Esta acción no se puede deshacer.",
                  deleteCurrentZoomImage
                )}
            >
              <svg class="trash-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18" />
                <path d="M8 6V4h8v2" />
                <path d="M6 6l1 14h10l1-14" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
              </svg>
            </button>
            <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={() => (previewZoomOpen = false)}>✕</button>
          </div>
        </header>
        <div class="zoom-modal__body" on:wheel={zoomWithWheel}>
          {#if previewZoomDataUrl}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="zoom-modal__stage"
              role="application"
              aria-label="Área de zoom y arrastre"
              bind:this={zoomStageEl}
              on:pointerdown={beginPan}
              on:pointermove={movePan}
              on:pointerup={endPan}
              on:pointercancel={endPan}
              on:click={onZoomStageClick}
            >
              <img
                class="zoom-modal__img"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                bind:this={zoomImgEl}
                src={previewZoomDataUrl}
                alt={previewZoomName}
                style={`transform: ${zoomImgTransform};`}
                on:load={onZoomImageLoad}
              />
              {#if zoomHudVisible}
                <div class="zoom-mini" bind:this={zoomMiniEl}>
                  <img src={previewZoomDataUrl} alt="" />
                  <div class="zoom-mini__rect" style={zoomMiniRect}></div>
                </div>
              {/if}
              {#if previewZoomDestMode}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="zoom-dest-chips"
                  class:zoom-dest-chips--carousel-hidden={!previewZoomCarouselVisible}
                  on:pointerdown|stopPropagation={() => undefined}
                  on:click|stopPropagation={() => undefined}
                >
                  <button
                    type="button"
                    class="om-btn om-btn--ghost om-btn--compact zoom-dest-add"
                    on:pointerdown|stopPropagation={() => undefined}
                    on:click={openAddDestForm}
                  >+</button>
                  <button
                    type="button"
                    class="om-btn om-btn--ghost om-btn--compact"
                    disabled={!previewZoomCanUndoMove}
                    on:click={undoLastZoomMove}
                  >Deshacer</button>
                  {#each destRows as d, i (d.path + "\0zoom\0" + i)}
                    <button
                      type="button"
                      class="zoom-dest-chip"
                      class:zoom-dest-chip--dragging={draggedDestIdx === i}
                      data-dest-path={d.path}
                      title={d.path}
                      draggable={true}
                      on:click={() => requestMoveCurrentZoomToDestination(d.path)}
                      on:contextmenu={(e) => onDestContextMenu(e, i, "fullscreen")}
                      on:dragstart={(e) => onDestChipDragStart(e, i)}
                      on:dragend={onDestChipDragEnd}
                      on:dragenter|preventDefault
                      on:dragover|preventDefault
                      on:drop={(e) => onDestDrop(e, d.path)}
                    >{d.label}</button>
                  {/each}
                </div>
              {/if}
            </div>
          {:else}
            <div class="preview__empty">Cargando imagen…</div>
          {/if}
        </div>
        <div
          class="zoom-modal__carousel"
          class:zoom-modal__carousel--hidden={!previewZoomCarouselVisible}
          aria-label="Carrusel de miniaturas"
          bind:this={zoomCarouselEl}
        >
          {#each zoomNavItems as it}
            <button
              type="button"
              class="zoom-carousel__item"
              class:zoom-carousel__item--active={it.path === previewZoomPath}
              title={it.name}
              on:click={() => openPreviewZoom(it, { preserveCarousel: true, preserveMode: true, navItems: zoomNavItems })}
            >
              {#if it.thumbDataUrl}
                <img src={it.thumbDataUrl} alt={it.name} class:thumb--lq={it.thumbQuality === "lq"} />
              {/if}
            </button>
          {/each}
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
          <strong id="org-float-title">Organizar medios</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={() => (orgPanelOpen = false)}>✕</button>
        </header>
        <div class="org-row">
          <label class="field-label" for="org-path-input-float">Ruta</label>
          <input id="org-path-input-float" class="om-input org-row__input" bind:value={orgPath} placeholder="Carpeta raíz a organizar" />
          <button type="button" class="om-btn om-btn--primary" title="Elegir carpeta" on:click={pickOrgFolder}>Examinar…</button>
        </div>
        <div class="checks">
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeOrganized} /> Incluir Organizado</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeComics} /> Incluir ComicsCBZ</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includePending} /> Incluir PendientesRevisión</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.removeDuplicates} /> Eliminar duplicadas</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.groupSimilarImages} /> Agrupar similares</label>
        </div>
        <div class="org-row org-row--footer">
          <button type="button" class="om-btn om-btn--primary" on:click={startOrganizer} disabled={orgRunning}>Organizar ahora</button>
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelOrganizer} disabled={!orgRunning}>Cancelar</button>
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
      aria-label="Acciones del destino"
      style={`left:${destCtxMenu.x}px;top:${destCtxMenu.y}px`}
      on:click|stopPropagation
    >
      {#if destCtxMenu.source === "gallery"}
        <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openPreviewFromCtx}>Ver carpeta</button>
      {/if}
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openEditFromCtx}>Editar…</button>
      <button type="button" class="dest-ctx-menu__item dest-ctx-menu__item--danger" role="menuitem" on:click={removeDestFromCtx}>Eliminar</button>
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
          <strong id="dest-form-title">{destFormMode === "add" ? "Agregar carpeta destino" : "Editar destino"}</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={closeDestForm}>✕</button>
        </header>
        <section class="dest-form-body">
          <label class="field-label" for="dest-form-label">Nombre</label>
          <input id="dest-form-label" class="om-input" type="text" bind:value={destFormLabel} placeholder="Etiqueta en la lista" />
          <label class="field-label" for="dest-form-path">Ruta</label>
          <div class="dest-form-path-row">
            <input id="dest-form-path" class="om-input" type="text" bind:value={destFormPath} placeholder="Ruta de la carpeta" />
            <button type="button" class="om-btn om-btn--primary" on:click={pickDestFormFolder}>Examinar…</button>
          </div>
        </section>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={closeDestForm}>Cancelar</button>
          <button type="button" class="om-btn om-btn--primary" on:click={saveDestForm}>Guardar</button>
        </div>
      </div>
    </div>
  {/if}

  {#if settingsOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim" role="presentation" on:click|self={cancelSettingsModal}>
      <div
        class="modal modal--settings om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="modal__head">
          <strong id="settings-title">Ajustes</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={cancelSettingsModal}>✕</button>
        </header>
        <section class="settings-body">
          <div class="settings-group">
            <h3 class="settings-group__title">Rendimiento</h3>
            <label class="field-label" for="set-thumbs-page">Imágenes por página (0 = sin límite)</label>
            <input
              id="set-thumbs-page"
              class="om-input"
              type="number"
              min="0"
              placeholder="Ejemplo: 48"
              bind:value={thumbsPerPage}
            />
            <div class="settings-preset-row">
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 24)}>Alto rendimiento (24)</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 48)}>Rendimiento (48)</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 96)}>Equilibrado (96)</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 0)}>Sin límite (0)</button>
            </div>
            {#if Number(thumbsPerPage) === 0}
              <p class="settings-hint settings-hint--warn">Sin límite puede degradar el rendimiento en carpetas grandes.</p>
            {/if}
            <p class="settings-hint">Mientras más bajo, mejor rendimiento.</p>
          </div>

          <div class="settings-group">
            <h3 class="settings-group__title">Miniaturas</h3>
            <label class="field-label" for="set-thumb-preset">Tamaño (preset)</label>
            <input
              id="set-thumb-preset"
              class="om-range"
              type="range"
              min="0"
              max={thumbScalePresets.length - 1}
              step="1"
              bind:value={settingsThumbPresetIdx}
              on:input={() => {
                const p = thumbScalePresets[Math.max(0, Math.min(thumbScalePresets.length - 1, Number(settingsThumbPresetIdx) || 0))];
                settingsThumbScaleDraft = p.value;
              }}
            />
            <div class="settings-preset-row">
              {#each thumbScalePresets as p, i}
                <button
                  type="button"
                  class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
                  class:om-btn--primary={i === settingsThumbPresetIdx}
                  on:click={() => {
                    settingsThumbPresetIdx = i;
                    settingsThumbScaleDraft = p.value;
                  }}
                >{p.label}</button>
              {/each}
            </div>
            <label class="field-label" for="set-thumb-scale">Ajuste fino {Math.round(settingsThumbScaleDraft * 100)}%</label>
            <input
              id="set-thumb-scale"
              class="om-range"
              type="range"
              min="0.01"
              max="2.25"
              step="0.01"
              bind:value={settingsThumbScaleDraft}
            />
            <label class="field-label" for="set-thumb-gap">Separación entre miniaturas {Math.round(thumbGapPx)}px</label>
            <input
              id="set-thumb-gap"
              class="om-range"
              type="range"
              min="0"
              max="20"
              step="1"
              bind:value={thumbGapPx}
            />
            <label class="field-label" for="set-thumb-radius">Redondeado de imagen {Math.round(thumbImageRadiusPx)}px</label>
            <input
              id="set-thumb-radius"
              class="om-range"
              type="range"
              min="0"
              max="18"
              step="1"
              bind:value={thumbImageRadiusPx}
            />
            <label class="field-label" for="set-tile-radius">Redondeado del elemento {Math.round(thumbTileRadiusPx)}px</label>
            <input
              id="set-tile-radius"
              class="om-range"
              type="range"
              min="0"
              max="28"
              step="1"
              bind:value={thumbTileRadiusPx}
            />
            <div class="settings-preset-row">
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 0)}>Sin redondeo</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 6)}>Suave</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 12)}>Medio</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 18)}>Alto</button>
            </div>
          </div>

          <div class="settings-group">
            <h3 class="settings-group__title">Apariencia</h3>
            <div class="settings-preset-row">
              <label class="check"><input type="checkbox" bind:checked={showThumbLabels} /> Mostrar etiquetas en miniaturas</label>
            </div>
            <div class="settings-preset-row">
              <label class="check"><input type="checkbox" bind:checked={thumbFrameVisible} /> Mostrar recuadro de miniaturas</label>
            </div>
            <div class="settings-preset-row">
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
                class:om-btn--primary={thumbCardStyle === "soft"}
                on:click={() => (thumbCardStyle = "soft")}
              >Recuadro suave</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
                class:om-btn--primary={thumbCardStyle === "flat"}
                on:click={() => (thumbCardStyle = "flat")}
              >Recuadro plano</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
                class:om-btn--primary={thumbCardStyle === "outlined"}
                on:click={() => (thumbCardStyle = "outlined")}
              >Solo contorno</button>
            </div>
            <div
              class="settings-thumb-preview"
              class:settings-thumb-preview--no-frame={!thumbFrameVisible}
              style={`--cell:${settingsPreviewCellPx}px;--thumb-gap:${thumbGapPx}px;--thumb-image-radius:${thumbImageRadiusPx}px;--thumb-tile-radius:${thumbTileRadiusPx}px`}
            >
              <div class="tile"><div class="folder-ph">A</div>{#if showThumbLabels}<span class="tile__name">Ejemplo 1</span>{/if}</div>
              <div class="tile"><div class="folder-ph">B</div>{#if showThumbLabels}<span class="tile__name">Ejemplo 2</span>{/if}</div>
              <div class="tile"><div class="folder-ph">C</div>{#if showThumbLabels}<span class="tile__name">Ejemplo 3</span>{/if}</div>
            </div>
          </div>
        </section>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelSettingsModal}>Cancelar</button>
          <button type="button" class="om-btn om-btn--primary" on:click={saveSettingsModal}>Guardar</button>
        </div>
      </div>
    </div>
  {/if}

  {#if confirmDeleteOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim overlay--confirm" role="presentation" on:click|self={closeConfirmDelete}>
      <div
        class="modal modal--confirm om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-delete-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="modal__head">
          <strong id="confirm-delete-title">{confirmDeleteTitle}</strong>
          <button type="button" class="om-btn om-btn--ghost om-btn--close" aria-label="Cerrar modal" title="Cerrar" on:click={closeConfirmDelete}>✕</button>
        </header>
        <p class="settings-hint">{confirmDeleteDetail}</p>
        {#if confirmDeleteBypassEnabled}
          <label class="check">
            <input type="checkbox" bind:checked={confirmDeleteBypassChecked} />
            {confirmDeleteBypassLabel}
          </label>
        {/if}
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={closeConfirmDelete}>Cancelar</button>
          <button type="button" class="om-btn om-btn--primary" on:click={runConfirmDelete}>{confirmDeleteConfirmLabel}</button>
        </div>
      </div>
    </div>
  {/if}

  {#if uiLoading}
    <div class="load-overlay" aria-busy="true" aria-live="polite">
      <div class="load-overlay__spinner"></div>
      <span class="load-overlay__text">Cargando…</span>
    </div>
  {/if}
</main>

<style>
  @import "./styles/design-tokens.css";
  @import "./styles/components.css";

  .app {
    height: 100%;
    display: grid;
    gap: 6px;
    /* tabs · área principal · paginador */
    grid-template-rows: auto 1fr auto;
    padding: 8px 12px;
    font-family: var(--om-font-sans);
    color: var(--om-text-primary);
    background: radial-gradient(120% 80% at 50% -20%, rgb(124 140 255 / 0.12), transparent 50%), var(--om-bg-base);
    box-sizing: border-box;
  }

  /* Barra extra bajo el header cuando no está en modo destinos. */
  .app.app--layout-ruta {
    grid-template-rows: auto 1fr auto;
  }

  .tabs-bar {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
    padding-block: 4px;
    padding-inline: 10px;
  }

  .tabs-bar.om-panel,
  .gallery.om-panel,
  .preview.om-panel,
  .pager.om-panel {
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
  }

  .tabs__nav {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
    align-items: center;
  }

  .route__row {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .route__row--inline {
    flex: 1 1 540px;
    min-width: min(520px, 100%);
  }

  .recent-folders__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .recent-folders__list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
  }

  .recent-folders__chip-wrap {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 100%;
  }

  .recent-folders__chip {
    max-width: 100%;
    text-align: left;
    font-size: 0.7rem;
    line-height: 1.2;
    white-space: normal;
    word-break: break-all;
    padding: 0.2rem 0.55rem;
    min-height: 1.65rem;
  }

  .recent-folders__pin {
    min-width: 1.55rem;
    min-height: 1.55rem;
    padding: 0.1rem 0.3rem;
    font-size: 0.78rem;
    line-height: 1;
    color: var(--om-accent-2);
  }

  .route__path {
    flex: 1;
    min-width: 0;
  }

  .route__path-wrap {
    flex: 1;
    min-width: min(320px, 100%);
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 4px;
    border: 1px solid var(--om-border-default);
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
    background: color-mix(in oklab, var(--om-surface-2) 88%, transparent);
  }

  .route__path-wrap .route__path {
    border: 0;
    background: transparent;
    box-shadow: none;
    padding-inline: 6px;
  }

  .route__path-action {
    min-width: 1.8rem;
    min-height: 1.8rem;
    padding: 0 6px;
  }

  .route-folder-ico {
    width: 1rem;
    height: 1rem;
    display: block;
    color: currentColor;
  }

  .field-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--om-text-secondary);
    white-space: nowrap;
  }

  .om-range {
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgb(124 140 255 / 0.44), rgb(94 228 212 / 0.34));
    border: 1px solid rgb(255 255 255 / 0.18);
    outline: none;
  }

  .om-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 999px;
    background: color-mix(in oklab, var(--om-accent) 72%, #fff);
    border: 1px solid rgb(255 255 255 / 0.76);
    box-shadow: 0 0 0 3px rgb(124 140 255 / 0.2);
    cursor: pointer;
  }

  .om-range::-moz-range-track {
    height: 6px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgb(124 140 255 / 0.44), rgb(94 228 212 / 0.34));
    border: 1px solid rgb(255 255 255 / 0.18);
  }

  .om-range::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 999px;
    background: color-mix(in oklab, var(--om-accent) 72%, #fff);
    border: 1px solid rgb(255 255 255 / 0.76);
    box-shadow: 0 0 0 3px rgb(124 140 255 / 0.2);
    cursor: pointer;
  }

  .content {
    display: grid;
    gap: 0;
    min-height: 0;
    align-items: stretch;
    margin-block: 0;
  }

  .splitter {
    cursor: col-resize;
    width: 10px;
    margin: 0 -2px;
    z-index: 2;
    flex-shrink: 0;
    border-radius: 4px;
    background: linear-gradient(180deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.02));
    border: 1px solid rgb(255 255 255 / 0.08);
    touch-action: none;
  }

  .splitter:hover,
  .splitter:focus-visible {
    background: rgb(124 140 255 / 0.25);
  }

  .destinos-work {
    display: grid;
    gap: 0;
    min-height: 0;
    align-items: stretch;
  }

  .destinos-work__top {
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .destinos-work__top > .content {
    flex: 1;
    min-height: 0;
  }


  /* Scroll interno: la barra de selección va con position:sticky y sigue visible al bajar. */
  .gallery--with-float {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
    position: relative;
  }

  .gallery--with-float.om-panel {
    padding-bottom: 0;
  }

  .gallery--with-float .gallery__scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    scrollbar-gutter: stable;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-content: start;
  }

  .gallery--with-float .gallery__scroll > .grid {
    grid-column: 1;
    grid-row: 1;
  }

  .gallery--with-float .gallery__scroll > .selection-float {
    grid-column: 1;
    grid-row: 1;
    align-self: start;
    justify-self: end;
    position: sticky;
    top: var(--om-space-2);
    margin: var(--om-space-2);
    z-index: 5;
  }

  .selection-float {
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-1);
    flex-wrap: wrap;
    max-width: calc(100% - var(--om-space-4));
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-md);
    background: rgb(8 10 18 / 0.82);
    border: 1px solid rgb(255 255 255 / 0.1);
    box-shadow: var(--om-shadow-md);
    backdrop-filter: blur(8px);
  }

  .dest-float-chips {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: min(820px, calc(100% - var(--om-space-4) * 2));
    bottom: var(--om-space-2);
    z-index: 7;
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: var(--om-space-1);
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-md);
    background: rgb(8 10 18 / 0.78);
    border: 1px solid rgb(255 255 255 / 0.1);
    box-shadow: var(--om-shadow-md);
    backdrop-filter: blur(8px);
    overflow-x: auto;
    overflow-y: hidden;
    box-sizing: border-box;
    scrollbar-width: none;
  }

  .dest-float-chips::-webkit-scrollbar {
    height: 0;
  }

  .dest-float-add {
    border-radius: 999px;
    border: 1px solid rgb(255 255 255 / 0.18);
    background: rgb(255 255 255 / 0.07);
    color: var(--om-text-secondary);
    min-height: 1.95rem;
    padding: 4px 12px;
    font-size: 0.82rem;
  }

  .dest-float-add:hover {
    border-color: rgb(124 140 255 / 0.45);
    background: rgb(124 140 255 / 0.14);
    color: var(--om-text-primary);
  }

  .dest-float-empty {
    font-size: 0.72rem;
    color: var(--om-text-muted);
  }

  .dest-float-chip {
    display: inline-flex;
    align-items: center;
    flex: 0 0 auto;
    min-height: 1.95rem;
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid rgb(255 255 255 / 0.16);
    background: rgb(255 255 255 / 0.06);
    color: var(--om-text-secondary);
    cursor: pointer;
    user-select: none;
    max-width: min(280px, 100%);
  }

  .dest-float-chip:hover {
    border-color: rgb(124 140 255 / 0.45);
    background: rgb(124 140 255 / 0.14);
  }

  .dest-float-chip--drop-target {
    border-color: rgb(124 140 255 / 0.82);
    background: linear-gradient(160deg, rgb(124 140 255 / 0.32), rgb(94 228 212 / 0.18));
    color: var(--om-text-primary);
  }

  .dest-float-chip__title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.82rem;
    line-height: 1.2;
  }

  .selection-float__count {
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 1.25rem;
    text-align: center;
    padding: 0 var(--om-space-1);
    color: var(--om-accent-2);
  }

  :global(.om-btn--mini) {
    padding: var(--om-space-1) var(--om-space-2);
    font-size: 0.7rem;
    min-height: 1.5rem;
    line-height: 1.2;
  }

  .om-btn--settings {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.5rem;
    min-height: 2.5rem;
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
  }

  .settings-gear {
    width: 22px;
    height: 22px;
    display: block;
    flex-shrink: 0;
  }

  .pager__google-line {
    font-size: 0.8125rem;
    color: var(--om-text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .pager__gap {
    padding: 0 var(--om-space-1);
    color: var(--om-text-muted);
    user-select: none;
  }

  .pager__num {
    min-width: 2.25rem;
    padding: var(--om-space-1) var(--om-space-2);
    font-variant-numeric: tabular-nums;
  }

  .gallery {
    min-height: 0;
    min-width: 0;
  }

  .gallery:not(.gallery--with-float) {
    overflow: auto;
  }

  .grid {
    display: grid;
    /* Columnas flexibles: se ajustan con cambios finos de ancho (splitter/vista previa). */
    grid-template-columns: repeat(auto-fill, minmax(var(--cell, 160px), 1fr));
    gap: var(--thumb-gap, var(--om-space-3));
    contain: layout style;
    padding-left: var(--grid-edge-pad, 8px);
    padding-right: var(--grid-edge-pad, 8px);
    box-sizing: border-box;
  }

  .grid-end-spacer {
    grid-column: 1 / -1;
    height: 3.6rem;
    pointer-events: none;
  }

  :global(body.om-dragging) .splitter,
  :global(body.om-dragging) .splitter {
    pointer-events: none;
  }

  .tile {
    touch-action: manipulation;
    position: relative;
    box-sizing: border-box;
    -webkit-user-select: none;
    user-select: none;
    background: linear-gradient(180deg, var(--om-surface-3) 0%, var(--om-surface-2) 100%);
    border: 1px solid var(--om-border-default);
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
    color: var(--om-text-primary);
    text-align: left;
    padding: var(--om-space-2);
    cursor: pointer;
    box-shadow: var(--om-shadow-sm);
    overflow: hidden;
    isolation: isolate;
    transition:
      transform var(--om-transition),
      box-shadow var(--om-transition),
      border-color var(--om-transition);
  }

  .tile > * {
    position: relative;
    z-index: 1;
  }

  .app.app--tile-flat .tile {
    background: var(--om-surface-2);
    box-shadow: none;
    border-color: color-mix(in oklab, var(--om-border-default) 85%, transparent);
  }

  .app.app--tile-outlined .tile {
    background: transparent;
    box-shadow: none;
    border-color: color-mix(in oklab, var(--om-accent) 48%, var(--om-border-default));
  }

  .app.app--tile-no-frame .tile {
    background: transparent;
    border-color: transparent;
    box-shadow: none;
    padding: 0;
  }

  .tile:hover {
    box-shadow: var(--om-shadow-md), 0 0 0 1px rgb(124 140 255 / 0.2);
    border-color: rgb(124 140 255 / 0.25);
  }

  .tile:focus {
    outline: none;
  }

  .tile:focus-visible {
    outline: 2px solid var(--om-accent);
    outline-offset: 2px;
  }

  .tile.selected {
    /* Selección más visible: fondo azul claro con contraste consistente. */
    background: color-mix(in oklab, var(--om-accent) 34%, #add3ff);
    border-color: color-mix(in oklab, var(--om-accent) 90%, #edf4ff);
    color: color-mix(in oklab, var(--om-text-primary) 90%, #ffffff);
    box-shadow:
      0 0 0 2px color-mix(in oklab, var(--om-accent) 78%, #eaf1ff),
      0 0 20px rgb(124 140 255 / 0.34);
  }

  .tile.selected::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background: color-mix(in oklab, var(--om-accent) 24%, #8fc0ff);
    opacity: 0.9;
  }

  .tile.selected img,
  .tile.selected .folder-ph {
    transform: scale(0.9);
    transform-origin: center;
    transition: transform var(--om-transition);
  }

  .tile img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: var(--thumb-image-radius, var(--om-radius-sm));
    display: block;
  }

  .thumb--lq {
    filter: blur(8px) saturate(0.85) contrast(0.92);
    transform: scale(1.04);
    opacity: 0.92;
    transition: filter 0.28s ease, transform 0.28s ease, opacity 0.28s ease;
  }

  .folder-ph {
    width: 100%;
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.25);
    border-radius: var(--thumb-image-radius, var(--om-radius-sm));
    font-size: 0.75rem;
    color: var(--om-text-muted);
  }

  .folder-ph--folder {
    gap: 4px;
    color: var(--om-text-secondary);
    border: 1px dashed color-mix(in oklab, var(--om-accent) 42%, transparent);
    background: linear-gradient(
      160deg,
      color-mix(in oklab, var(--om-accent) 14%, transparent),
      color-mix(in oklab, var(--om-accent-2) 10%, transparent)
    );
  }

  .folder-ph__icon {
    font-size: 1.7rem;
    line-height: 1;
    filter: drop-shadow(0 2px 6px rgb(0 0 0 / 0.35));
  }

  .folder-ph__svg {
    width: 1.85rem;
    height: 1.85rem;
    display: block;
    color: color-mix(in oklab, var(--om-accent) 55%, var(--om-text-primary));
    filter: drop-shadow(0 2px 6px rgb(0 0 0 / 0.35));
  }

  .folder-ph__label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .tile__name {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 20%;
    min-height: 1.6rem;
    max-height: 2.4rem;
    display: flex;
    align-items: center;
    padding: 0 var(--om-space-2);
    font-size: 0.7rem;
    line-height: 1.2;
    color: var(--om-text-primary);
    background: linear-gradient(180deg, rgb(7 8 14 / 0.2) 0%, rgb(7 8 14 / 0.74) 100%);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    box-sizing: border-box;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tile__name--folder {
    background: rgb(7 8 14 / 0.58);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .preview {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }

  .preview__img {
    width: 100%;
    flex: 1 1 0;
    min-height: 0;
    max-height: 100%;
    object-fit: contain;
    object-position: center center;
    background: var(--om-bg-base);
    border-radius: var(--om-radius-md);
    border: 1px solid var(--om-border-subtle);
  }

  .preview__empty {
    flex: 1 1 0;
    min-height: 80px;
    display: grid;
    place-items: center;
    color: var(--om-text-muted);
    font-size: 0.875rem;
    border: 1px dashed var(--om-border-default);
    border-radius: var(--om-radius-md);
  }

  .preview__meta {
    font-size: 0.75rem;
    color: var(--om-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }



  .pager {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
  }

  /* Debe ir después de `.pager` para ganar la cascada. */
  .pager.pager--bar {
    flex-wrap: nowrap;
    min-width: 0;
    overflow-x: hidden;
    overflow-y: visible;
    -webkit-overflow-scrolling: touch;
    gap: var(--om-space-2);
    align-items: center;
    box-sizing: border-box;
  }

  .pager.pager--bar.om-panel {
    padding: 0 11px;
    padding-block: 7px;
    margin-top: 2px;
    min-height: 2.7rem;
  }

  /* Mantiene tamaño visual consistente aunque cambie el contenido del estado. */
  .pager.pager--bar > :not(.grow):not(.status-line) {
    flex-shrink: 0;
  }

  .pager.pager--bar .grow {
    flex: 1 1 48px;
    min-width: 24px;
  }

  .pager.pager--bar .status-line {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: min(26vw, 320px);
  }

  .pager__split-label,
  .pager__thumb-label {
    font-size: 0.68rem;
    white-space: nowrap;
  }

  .pager__thumb-range {
    width: min(160px, 24vw);
    min-width: 110px;
  }

  .pager__jump {
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-1);
    font-size: 0.8125rem;
    color: var(--om-text-secondary);
  }

  .pager__jump-input {
    width: 4.25rem;
    min-height: 1.8rem;
    padding: 3px 7px;
    text-align: center;
  }

  .pager__jump-total {
    font-weight: 600;
    color: var(--om-text-primary);
  }

  .om-btn--compact {
    padding: var(--om-space-1) var(--om-space-3);
    font-size: 0.8125rem;
  }

  .pager.pager--bar .om-btn--compact {
    padding: 3px 10px;
    font-size: 0.76rem;
    min-height: 1.8rem;
    line-height: 1.2;
  }

  .status-line {
    font-size: 0.72rem;
    font-weight: 500;
    color: color-mix(in oklab, var(--om-text-muted) 78%, transparent);
    opacity: 0.9;
  }

  .org-float-overlay {
    position: fixed;
    inset: 0;
    z-index: 35;
    display: grid;
    place-items: center;
    padding: var(--om-space-4);
    background: rgb(4 6 14 / 0.55);
    box-sizing: border-box;
  }

  .organizer-float {
    width: min(720px, 100%);
    max-height: min(88vh, 900px);
    overflow: auto;
    padding: var(--om-space-5);
  }

  .org-float__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--om-space-3);
    margin-bottom: var(--om-space-4);
  }

  .organizer-float .org-row {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    margin-bottom: var(--om-space-4);
    flex-wrap: wrap;
  }

  .org-row__input {
    flex: 1;
    min-width: 200px;
  }

  .org-row--footer {
    margin-bottom: 0;
    margin-top: var(--om-space-2);
  }

  .checks {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: var(--om-space-2);
    margin-bottom: var(--om-space-4);
  }

  .check {
    font-size: 0.875rem;
    color: var(--om-text-secondary);
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }

  .org-status,
  .org-progress {
    font-size: 0.8125rem;
    color: var(--om-text-muted);
  }

  .grow {
    flex: 1;
  }

  .load-overlay {
    position: fixed;
    inset: 0;
    z-index: 150;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--om-space-3);
    background: rgb(4 6 14 / 0.42);
    pointer-events: all;
  }

  .load-overlay__spinner {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 3px solid rgb(255 255 255 / 0.18);
    border-top-color: var(--om-accent);
    animation: om-spin 0.7s linear infinite;
  }

  .load-overlay__text {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }

  @keyframes om-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .overlay {
    position: fixed;
    inset: 0;
    background: rgb(4 6 14 / 0.85);
    display: grid;
    place-items: center;
    z-index: 40;
  }

  .overlay--dim {
    background: rgb(4 6 14 / 0.72);
    z-index: 45;
  }

  .overlay--confirm {
    z-index: 75;
  }

  .modal--settings {
    width: min(760px, 96vw);
    max-height: min(92vh, 780px);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    padding: var(--om-space-4);
    box-sizing: border-box;
    overflow: hidden;
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
  }

  .modal--dest-form {
    width: min(480px, 92vw);
    max-height: min(90vh, 440px);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-4);
    padding: var(--om-space-5);
    box-sizing: border-box;
  }

  .overlay--dest-form {
    z-index: 85;
  }

  .modal--route-picker {
    width: min(840px, 96vw);
    max-height: min(88vh, 760px);
  }

  .route-picker__body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    min-height: 0;
    overflow: auto;
  }

  .route-picker__input-row {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }

  .route-picker__input {
    flex: 1;
    min-width: min(260px, 100%);
  }

  .modal--confirm {
    width: min(520px, 92vw);
    max-height: min(72vh, 340px);
    z-index: 76;
  }

  .dest-form-body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
  }

  .dest-form-path-row {
    display: flex;
    gap: var(--om-space-2);
    flex-wrap: wrap;
    align-items: center;
  }

  .dest-form-path-row .om-input {
    flex: 1;
    min-width: min(220px, 100%);
  }

  .ctx-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 90;
    background: transparent;
  }

  .dest-ctx-menu {
    position: fixed;
    z-index: 91;
    min-width: 11rem;
    padding: var(--om-space-2);
    display: flex;
    flex-direction: column;
    gap: 2px;
    box-sizing: border-box;
  }

  .dest-ctx-menu__item {
    font-family: var(--om-font-sans);
    font-size: 0.8125rem;
    font-weight: 600;
    text-align: left;
    width: 100%;
    padding: var(--om-space-2) var(--om-space-3);
    border: none;
    border-radius: var(--om-radius-sm);
    cursor: pointer;
    color: var(--om-text-primary);
    background: rgb(255 255 255 / 0.06);
  }

  .dest-ctx-menu__item:hover {
    background: rgb(124 140 255 / 0.18);
  }

  .dest-ctx-menu__item--danger {
    color: #f87171;
  }

  .dest-ctx-menu__item--danger:hover {
    background: rgb(248 113 113 / 0.12);
  }

  .settings-body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding-right: 4px;
  }

  .settings-body::-webkit-scrollbar {
    width: 8px;
  }

  .settings-body::-webkit-scrollbar-thumb {
    background: rgb(255 255 255 / 0.22);
    border-radius: 999px;
  }

  .settings-group {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
    padding: var(--om-space-2);
    border: 1px solid color-mix(in oklab, var(--om-border-default) 78%, transparent);
    border-radius: var(--om-radius-md);
    background: color-mix(in oklab, var(--om-surface-2) 86%, transparent);
  }

  .settings-group__title {
    margin: 0;
    font-size: 0.84rem;
    color: var(--om-text-secondary);
    letter-spacing: 0.01em;
  }

  .settings-hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--om-text-muted);
    line-height: 1.4;
  }

  .settings-hint--warn {
    color: color-mix(in oklab, #ffbf66 78%, var(--om-text-primary));
  }

  .settings-preset-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-1);
  }

  .settings-preset-chip {
    min-height: 1.65rem;
  }

  .om-btn--close {
    min-width: 2rem;
    padding-inline: 0.45rem;
    font-size: 1rem;
    line-height: 1;
  }

  .settings-thumb-preview {
    display: grid;
    grid-template-columns: repeat(3, minmax(var(--cell, 140px), var(--cell, 140px)));
    gap: var(--thumb-gap, var(--om-space-2));
    justify-content: start;
    max-width: 100%;
    overflow-x: auto;
    padding: 2px 0;
  }

  .settings-thumb-preview--no-frame .tile {
    background: transparent;
    border-color: transparent;
    box-shadow: none;
    padding: 0;
  }

  .settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--om-space-2);
    flex-wrap: wrap;
  }

  .modal {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    gap: var(--om-space-3);
    padding: var(--om-space-5);
    z-index: 41;
    box-sizing: border-box;
  }

  /* Altura explícita: si solo hay max-height, el cuerpo flex no ocupa espacio y casi no se ve la rejilla. */
  .modal--dest {
    width: min(80vw, min(1100px, 96vw));
    height: clamp(480px, 82vh, 920px);
    max-height: min(94vh, 920px);
  }

  .modal__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--om-space-3);
  }

  .modal__ctrl {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--om-space-3);
    flex-shrink: 0;
  }

  .modal__pick-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--om-space-2);
    margin-left: auto;
  }

  .modal__scroll {
    flex: 1 1 0;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
  }

  .dest-grid {
    flex: 1 1 auto;
    min-height: 0;
    min-width: 0;
    overflow-x: hidden;
    overflow-y: auto;
    display: grid;
    /* auto-fill: solo columnas que caben; min() evita una pista más estrecha que el contenedor. */
    grid-template-columns: repeat(auto-fill, minmax(min(var(--pv-min, 120px), 100%), 1fr));
    gap: var(--om-space-3);
    align-content: start;
  }

  .pv-tile {
    background: var(--om-surface-2);
    border-radius: var(--om-radius-sm);
    padding: var(--om-space-2);
    border: 1px solid var(--om-border-subtle);
    position: relative;
    cursor: pointer;
    transition:
      border-color var(--om-transition),
      box-shadow var(--om-transition),
      background var(--om-transition);
  }

  .pv-tile:hover {
    border-color: rgb(124 140 255 / 0.45);
  }

  .pv-tile.pv-tile--selected {
    border-color: rgb(124 140 255 / 0.78);
    background: linear-gradient(165deg, rgb(124 140 255 / 0.16) 0%, rgb(94 228 212 / 0.08) 100%);
    box-shadow:
      0 0 0 1px rgb(94 228 212 / 0.35),
      0 0 18px rgb(124 140 255 / 0.22);
  }

  .pv-tile img {
    width: 100%;
    height: auto;
    max-height: 240px;
    object-fit: contain;
    object-position: center;
    border-radius: 6px;
    background: rgb(0 0 0 / 0.2);
  }

  .pv-tile__name {
    font-size: 0.65rem;
    color: var(--om-text-muted);
    display: block;
    margin-top: var(--om-space-1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pv-tile__pick {
    position: absolute;
    right: 8px;
    top: 8px;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 999px;
    border: 1px solid rgb(255 255 255 / 0.35);
    background: rgb(7 8 15 / 0.72);
    color: #fff;
    font-weight: 800;
    font-size: 0.9rem;
    cursor: pointer;
    display: grid;
    place-items: center;
    z-index: 2;
  }

  .pv-tile--selected .pv-tile__pick {
    background: linear-gradient(135deg, var(--om-accent), #4f5fd4);
    border-color: rgb(255 255 255 / 0.56);
  }

  .overlay--zoom {
    background: rgb(2 3 8 / 0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    z-index: 60;
  }

  .zoom-modal {
    width: min(96vw, 1320px);
    height: min(94vh, 980px);
    height: min(94dvh, 980px);
    max-height: 94vh;
    max-height: 94dvh;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: var(--om-space-3);
    overflow: hidden;
    min-height: 0;
    min-width: 0;
  }

  .zoom-modal--carousel-hidden {
    gap: var(--om-space-2);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .zoom-modal__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--om-space-3);
    padding: 0 var(--om-space-2);
    color: var(--om-text-primary);
    overflow: visible;
  }

  .zoom-modal__tools {
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
    padding: 2px 5px;
    border-radius: 999px;
    border: 1px solid rgb(255 255 255 / 0.12);
    background: rgb(255 255 255 / 0.05);
    overflow: visible;
  }

  .zoom-modal__tools .om-btn--compact {
    min-height: 2rem;
    padding: 0 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }

  .zoom-modal__tools .om-btn {
    border-color: transparent;
    background: transparent;
    box-shadow: none;
    line-height: 1.2;
    overflow: visible;
  }

  .zoom-trash-btn {
    width: 2.1rem;
    min-width: 2.1rem;
    max-width: 2.1rem;
    padding: 0;
  }

  .zoom-modal__tools .om-btn:hover {
    background: rgb(255 255 255 / 0.1);
    border-color: transparent;
  }

  .trash-ico {
    width: 1.2rem;
    height: 1.2rem;
    display: block;
    color: currentColor;
    overflow: visible;
    flex-shrink: 0;
  }

  .zoom-modal__body {
    min-width: 0;
    min-height: 0;
    width: 100%;
    height: 100%;
    max-height: 100%;
    min-height: 0;
    display: grid;
    place-items: center;
    overflow: hidden;
    border-radius: var(--om-radius-lg);
    background: radial-gradient(130% 100% at 50% 40%, rgb(124 140 255 / 0.08), transparent 65%);
  }

  .zoom-modal__stage {
    width: 100%;
    height: 100%;
    min-height: 0;
    min-width: 0;
    display: grid;
    place-items: center;
    overflow: hidden;
    cursor: default;
    position: relative;
  }

  .zoom-dest-chips {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: var(--om-space-3);
    z-index: 7;
    display: flex;
    gap: var(--om-space-1);
    align-items: center;
    flex-wrap: nowrap;
    overflow-x: auto;
    max-width: min(900px, calc(100% - var(--om-space-4)));
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-md);
    background: rgb(8 10 18 / 0.72);
    border: 1px solid rgb(255 255 255 / 0.12);
    backdrop-filter: blur(8px);
  }

  .zoom-dest-chips--carousel-hidden {
    bottom: var(--om-space-2);
  }

  .zoom-dest-chip {
    border: 1px solid rgb(255 255 255 / 0.18);
    background: rgb(255 255 255 / 0.07);
    color: var(--om-text-secondary);
    border-radius: 999px;
    min-height: 1.9rem;
    padding: 4px 12px;
    cursor: pointer;
    flex: 0 0 auto;
  }

  .dest-float-chip--dragging,
  .zoom-dest-chip--dragging {
    opacity: 0.58;
    transform: scale(0.98);
  }

  .zoom-dest-add {
    flex: 0 0 auto;
    min-height: 1.9rem;
    border-radius: 999px;
  }

  .zoom-dest-chip:hover {
    border-color: rgb(124 140 255 / 0.48);
    background: rgb(124 140 255 / 0.16);
    color: var(--om-text-primary);
  }

  .zoom-modal__img {
    position: absolute;
    left: 50%;
    top: 50%;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: var(--om-radius-md);
    box-shadow: 0 16px 42px rgb(0 0 0 / 0.55);
    background: rgb(0 0 0 / 0.22);
    transform-origin: center center;
    transition: transform 0.08s linear;
    user-select: none;
    -webkit-user-drag: none;
  }

  .zoom-modal__img--fill-width {
    width: 100%;
    height: auto;
    max-width: none;
    max-height: none;
    top: 0;
  }

  .zoom-modal__img--pannable {
    cursor: grab;
  }

  .zoom-modal__img--pannable:active {
    cursor: grabbing;
  }

  .zoom-modal__carousel {
    display: flex;
    gap: var(--om-space-2);
    overflow-x: auto;
    overflow-y: hidden;
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-md);
    background: rgb(255 255 255 / 0.04);
    scrollbar-width: thin;
    scrollbar-color: rgb(124 140 255 / 0.38) transparent;
    flex: 0 0 auto;
    position: relative;
    z-index: 5;
  }

  .zoom-modal__body {
    position: relative;
    z-index: 1;
  }

  .zoom-modal__carousel::-webkit-scrollbar {
    height: 6px;
  }

  .zoom-modal__carousel::-webkit-scrollbar-track {
    background: transparent;
  }

  .zoom-modal__carousel::-webkit-scrollbar-thumb {
    background: linear-gradient(90deg, rgb(124 140 255 / 0.42), rgb(94 228 212 / 0.28));
    border-radius: 999px;
  }

  .zoom-modal__carousel--hidden {
    display: none;
  }

  .zoom-carousel__item {
    border: 1px solid var(--om-border-subtle);
    border-radius: var(--om-radius-sm);
    padding: 0;
    width: 72px;
    height: 72px;
    flex: 0 0 auto;
    overflow: hidden;
    background: var(--om-surface-2);
    cursor: pointer;
  }

  .zoom-carousel__item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .zoom-carousel__item--active {
    border-color: color-mix(in oklab, var(--om-accent) 82%, #ffffff);
    background: color-mix(in oklab, var(--om-accent) 30%, var(--om-surface-2));
    box-shadow:
      0 0 0 2px color-mix(in oklab, var(--om-accent) 70%, #ffffff),
      0 0 14px rgb(124 140 255 / 0.3);
  }

  .zoom-mini {
    position: absolute;
    right: 12px;
    bottom: 12px;
    width: 130px;
    height: 88px;
    border-radius: var(--om-radius-sm);
    overflow: hidden;
    border: 1px solid rgb(255 255 255 / 0.28);
    background: rgb(7 8 15 / 0.72);
    box-shadow: 0 10px 22px rgb(0 0 0 / 0.45);
    pointer-events: none;
  }

  .zoom-mini img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    filter: saturate(0.92);
    background: rgb(0 0 0 / 0.28);
  }

  .zoom-mini__rect {
    position: absolute;
    border: 2px solid rgb(94 228 212 / 0.95);
    box-shadow: 0 0 0 1px rgb(124 140 255 / 0.75), inset 0 0 0 1px rgb(0 0 0 / 0.35);
    border-radius: 4px;
    background: rgb(124 140 255 / 0.12);
    box-sizing: border-box;
  }

  /* Ghost de arrastre */
  .drag-ghost {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    pointer-events: none;
    transform: translate(16px, 16px);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--om-space-2);
    filter: drop-shadow(0 12px 24px rgb(0 0 0 / 0.55));
  }

  .drag-ghost__card {
    position: relative;
    width: 72px;
    height: 72px;
    border-radius: var(--om-radius-md);
    overflow: hidden;
    border: 2px solid rgb(124 140 255 / 0.6);
    background: var(--om-surface-1);
    box-shadow: var(--om-shadow-lg), 0 0 0 1px rgb(255 255 255 / 0.08);
  }

  .drag-ghost__img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .drag-ghost__ph {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--om-text-muted);
  }

  .drag-ghost__badge {
    position: absolute;
    right: -6px;
    top: -6px;
    min-width: 1.35rem;
    height: 1.35rem;
    padding: 0 5px;
    border-radius: 999px;
    background: linear-gradient(135deg, var(--om-accent), #4f5fd4);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 800;
    display: grid;
    place-items: center;
    border: 2px solid var(--om-bg-base);
    box-shadow: var(--om-shadow-sm);
  }

  .drag-ghost__cap {
    max-width: 220px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--om-text-primary);
    text-shadow: 0 2px 8px rgb(0 0 0 / 0.8);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
