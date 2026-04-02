<script lang="ts">
  import { onDestroy, onMount } from "svelte";
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
  let galleryRangeDraftSelectedPaths: string[] | null = null;
  let galleryRangeSuppressClick = false;
  let previewZoomOpen = false;
  let previewZoomPath = "";
  let previewZoomName = "";
  let previewZoomDataUrl: string | null = null;
  let previewZoomScale = 1;
  let previewZoomMode: "fit" | "fillWidth" = "fit";
  let previewPanX = 0;
  let previewPanY = 0;
  let previewPanDrag = false;
  let previewPanMoved = false;
  let previewPanStartX = 0;
  let previewPanStartY = 0;
  let previewZoomCarouselVisible = true;
  let zoomHudVisible = false;
  let zoomHudTimer: ReturnType<typeof setTimeout> | null = null;
  let zoomStageEl: HTMLDivElement | null = null;
  let zoomImgEl: HTMLImageElement | null = null;
  let previewZoomNaturalW = 1;
  let previewZoomNaturalH = 1;
  let zoomMiniEl: HTMLDivElement | null = null;
  let zoomNavItems: Array<{ path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }> = [];
  let galleryThumbHydrationToken = 0;
  let previewThumbHydrationToken = 0;
  let previewScale = 1;
  let previewDestPath = "";
  let activeTab: "ruta" | "destinos" | "organizar" = "ruta";
  /** Panel organizador en ventana flotante (tarea por lotes). */
  let orgPanelOpen = false;
  let settingsOpen = false;
  let thumbsPerPage = 48;
  let thumbsPerPageBackup = 48;
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

  function trackLoad<T>(promise: Promise<T>): Promise<T> {
    loadCount++;
    return promise.finally(() => {
      loadCount--;
    });
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
    previewScale = Number(data.settings?.dest_preview_thumb_scale ?? 1);
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
    thumbsPerPage = Math.min(120, Math.max(12, Number(data.settings?.gallery_thumbs_per_page ?? 48)));
    pageJumpDraft = Number(data.gallery?.page ?? 1);
    await syncDestinationsFromApi();
  };

  const loadFolder = async () => {
    const out = await trackLoad(bridge.galleryLoadFolder(folder));
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
    pageJumpDraft = out.state.page;
    status = `Cargada carpeta: ${folder}`;
  };

  const pickRecentFolder = async (path: string) => {
    folder = path;
    await loadFolder();
  };

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
  };

  const goPage = async (page: number) => {
    const out = await trackLoad(bridge.galleryGoPage(page));
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    pageJumpDraft = out.state.page;
  };

  const jumpToPageDraft = async () => {
    const n = Math.min(galleryState.totalPages, Math.max(1, Math.round(Number(pageJumpDraft)) || 1));
    pageJumpDraft = n;
    await goPage(n);
  };

  const openSettingsModal = () => {
    thumbsPerPageBackup = thumbsPerPage;
    settingsOpen = true;
  };

  const cancelSettingsModal = () => {
    thumbsPerPage = thumbsPerPageBackup;
    settingsOpen = false;
  };

  const saveSettingsModal = async () => {
    const n = Math.min(120, Math.max(12, Math.round(Number(thumbsPerPage)) || 48));
    thumbsPerPage = n;
    await bridge.settingsPatch({ gallery_thumbs_per_page: n });
    await reload();
    settingsOpen = false;
  };

  const clickItem = async (it: GalleryItem) => {
    if (suppressNextGalleryClick) {
      suppressNextGalleryClick = false;
      return;
    }
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
      if (it.kind === "folder" || it.kind === "folder_up") {
        const out = await trackLoad(bridge.galleryOpenFolderTile(it.path));
        galleryState = out.state;
        items = out.items;
        galleryThumbHydrationToken++;
        void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
        folder = galleryState.folder;
        if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
        pageJumpDraft = out.state.page;
        return;
      }
      if (activeTab === "destinos") {
        const out = await bridge.galleryToggleSelect(it.path);
        galleryState = out.state;
        items = out.items;
        galleryThumbHydrationToken++;
        void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
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
    const out = await bridge.gallerySelectPage();
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
  };
  const clearSelection = async () => {
    const out = await bridge.galleryClearSelection();
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
  };
  const invertSelection = async () => {
    const out = await bridge.galleryInvertSelection();
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
  };

  const moveToDest = async (path: string) => {
    const out = await trackLoad(bridge.destinationMoveSelected(path));
    galleryState = out.state;
    items = out.items;
    galleryThumbHydrationToken++;
    void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    status = `Movidas ${out.moveResult?.moved ?? 0} · errores ${out.moveResult?.errors ?? 0}`;
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
    opts?: { preserveCarousel?: boolean; navItems?: Array<{ path: string; name: string; thumbDataUrl?: string | null; thumbQuality?: "lq" | "hq" }> }
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
    previewZoomMode = "fit";
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
    if (activeTab !== "destinos" || it.kind !== "image") return false;
    if (galleryRangeDraftSelectedPaths) return galleryRangeDraftSelectedPaths.includes(it.path);
    return Boolean(it.selected);
  }

  function applyGalleryRangeSelection(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const imagePaths = getVisibleGalleryImagePaths();
    const a = imagePaths.indexOf(fromPath);
    const b = imagePaths.indexOf(toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const draft = new Set(galleryRangeBaseSelectedPaths);
    for (let i = lo; i <= hi; i++) {
      const p = imagePaths[i];
      if (!p) continue;
      if (mode === "select") draft.add(p);
      else draft.delete(p);
    }
    galleryRangeDraftSelectedPaths = [...draft];
  }

  function onGalleryTilePointerDown(e: PointerEvent, it: GalleryItem) {
    if (activeTab !== "destinos" || it.kind !== "image") return;
    // Solo activa selección por rango con Ctrl para no interferir con DnD normal.
    if (!e.ctrlKey) return;
    e.preventDefault();
    const baseSelected = items
      .filter((x) => x.kind === "image" && x.selected)
      .map((x) => x.path);
    galleryRangeBaseSelectedPaths = baseSelected;
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
    applyGalleryRangeSelection(galleryRangeAnchorPath, path, galleryRangeMode);
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
    galleryRangeDraftSelectedPaths = null;
    galleryRangeSuppressClick = true;
    setTimeout(() => {
      galleryRangeSuppressClick = false;
    }, 0);
    if (addPaths.length === 0 && removePaths.length === 0) return;
    try {
      const out = await bridge.galleryApplySelectionDelta(addPaths, removePaths);
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
    } catch {
      const out = await bridge.galleryRefreshItems();
      galleryState = out.state;
      items = out.items;
      galleryThumbHydrationToken++;
      void hydrateGalleryThumbsHq(items, thumbScale, galleryThumbHydrationToken);
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
      return { x: 0, y: Math.max(0, overflowY) };
    }
    return { x: Math.max(0, overflowX), y: Math.max(0, overflowY) };
  }

  function clampPanToStage() {
    const limits = getPanLimits();
    const nextX = previewZoomMode === "fillWidth" ? 0 : clamp(previewPanX, -limits.x, limits.x);
    const nextY = clamp(previewPanY, -limits.y, limits.y);
    if (nextX !== previewPanX) previewPanX = nextX;
    if (nextY !== previewPanY) previewPanY = nextY;
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
  }

  $: zoomImgTransform =
    previewZoomMode === "fit" && Math.round(previewZoomScale * 100) === 100
      ? "translate(-50%, -50%)"
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
    openPreviewZoom(it, { preserveCarousel: true, navItems: zoomNavItems });
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
    previewPanX = 0;
    previewPanY = 0;
    toggleZoomCarousel();
  }

  function onZoomImageLoad() {
    if (!zoomImgEl) return;
    previewZoomNaturalW = Math.max(1, zoomImgEl.naturalWidth || 1);
    previewZoomNaturalH = Math.max(1, zoomImgEl.naturalHeight || 1);
    clampPanToStage();
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

  /** Menú contextual (clic derecho) en un chip de destino. */
  let destCtxMenu: { x: number; y: number; idx: number } | null = null;

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
    if (activeTab !== "destinos" || it.kind !== "image") return;
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
    ignoreDestCardClickUntil = Date.now() + 450;
    endDragSessionAfterGesture();
    moveToDest(destPath);
  }

  /** Clic en la tarjeta (sin botón): vista previa de carpeta; el drop sigue moviendo archivos. */
  function onDestCardClick(e: MouseEvent, path: string) {
    if (e.button !== 0) return;
    if (Date.now() < ignoreDestCardClickUntil) return;
    if ((e.target as HTMLElement).closest("button")) return;
    openDestPreview(path);
  }

  function closeDestCtxMenu() {
    destCtxMenu = null;
  }

  function onDestContextMenu(e: MouseEvent, idx: number) {
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
    destCtxMenu = { x, y, idx };
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

  /** Celdas de ancho fijo (sin 1fr) para que cada paso del slider se note al cambiar columnas. */
  $: gridCellPx = galleryGridCellPx(thumbScale);

  $: if (activeTab !== "destinos") {
    destCtxMenu = null;
    if (destFormOpen) destFormOpen = false;
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
        await loadFolder();
      } catch {
        status = "No se pudo restaurar la última carpeta; revisa la ruta o pulsa Cargar.";
      }
    }
    pollTimer = window.setInterval(() => {
      pollOrganizer().catch(() => undefined);
    }, 1100);
  });

  onDestroy(() => {
    endDragSession();
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
  class:app--layout-ruta={activeTab === "ruta"}
  class:app--layout-destinos={activeTab === "destinos"}
  class:app--layout-org={activeTab === "organizar"}
>
  <header class="tabs-bar om-panel">
    <nav class="tabs__nav">
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "ruta"} on:click={() => (activeTab = "ruta")}>Ruta</button>
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "destinos"} on:click={() => (activeTab = "destinos")}>Destinos</button>
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "organizar"} on:click={() => (activeTab = "organizar")}>Organizar</button>
    </nav>
    <div class="grow"></div>
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

  {#if activeTab !== "destinos"}
  <section class="route om-panel">
    <div class="route__row">
      <input
        id="gallery-folder-input"
        class="om-input route__path"
        type="text"
        bind:value={folder}
        placeholder="Ruta de carpeta…"
        title="Pega la ruta o pulsa Examinar (app de escritorio)"
      />
      <button type="button" class="om-btn om-btn--primary" title="Explorador del sistema" on:click={pickGalleryFolder}>Examinar…</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Recargar galería" on:click={reload}>↻</button>
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--icon"
        title={pinnedFolders.includes(folder.trim()) ? "Quitar anclaje de esta ruta" : "Anclar esta ruta"}
        on:click={() => (pinnedFolders.includes(folder.trim()) ? unpinFolder(folder) : pinFolder(folder))}
      >
        {pinnedFolders.includes(folder.trim()) ? "★" : "☆"}
      </button>
      <button type="button" class="om-btn om-btn--primary" on:click={loadFolder}>Cargar</button>
      <div class="grow"></div>
      <span
        class="field-label"
        title="Arrastra la barra entre galería y vista previa para el ancho del panel"
        >Panel derecho ~{Math.round(previewRatio * 100)}%</span>
      <label class="field-label" for="route-thumb-scale">Miniaturas {Math.round(thumbScale * 100)}%</label>
      <input
        id="route-thumb-scale"
        class="om-range"
        type="range"
        min="0.75"
        max="2.25"
        step="0.01"
        bind:value={thumbScale}
        on:input={scheduleThumbScaleReload}
        on:change={flushThumbScaleOnRelease}
      />
    </div>
    {#if !folder.trim() && (pinnedFolders.length > 0 || recentFolders.length > 0)}
      <div class="recent-folders" aria-label="Rutas recientes">
        {#if pinnedFolders.length > 0}
          <div class="recent-folders__head">
            <span class="field-label">Rutas ancladas</span>
            <span class="recent-folders__hint">No se pierden del historial</span>
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
            <span class="recent-folders__hint">Pulsa para cargar y usa ☆ para anclar</span>
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
      </div>
    {/if}
  </section>
  {/if}

  {#if activeTab === "organizar"}
    <section class="om-panel org-tab-bar">
      <p class="org-tab-bar__text">Organización por lotes (comics, duplicados, etc.) en una ventana aparte.</p>
      <button type="button" class="om-btn om-btn--primary" on:click={() => (orgPanelOpen = true)}>Abrir panel de organización…</button>
    </section>
  {/if}

  {#if activeTab === "destinos"}
    <div
      class="destinos-work"
      class:destinos-work--drag={destSplitDrag}
      style={`grid-template-rows: minmax(0,${(1 - destPanelRatio).toFixed(4)}fr) 10px minmax(0,${destPanelRatio.toFixed(4)}fr)`}
    >
      <div class="destinos-work__top">
        <section
          class="content"
          style={`grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`}
        >
          <article class="gallery om-panel om-panel--lift gallery--with-float">
            <div class="gallery__scroll">
              <div class="grid" style={`--cell:${gridCellPx}px`}>
              {#each items as it (it.path)}
                <!-- div: en WebEngine <button>+drag y <img draggable> nativo suelen bloquear el DnD. -->
                <div
                  role="button"
                  tabindex="0"
                  class="tile"
                  data-item-path={it.path}
                  class:selected={isGalleryTileSelected(it)}
                  draggable={it.kind === "image"}
                  on:pointerdown={(e) => onGalleryTilePointerDown(e, it)}
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
                  <span class="tile__name">{it.name}</span>
                </div>
              {/each}
              </div>
              <div class="selection-float" role="toolbar" aria-label="Selección">
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectPage}>Pág.</button>
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearSelection}>Quitar</button>
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertSelection}>Invertir</button>
                <span class="selection-float__count" title="Seleccionadas">{galleryState.selectedCount}</span>
              </div>
            </div>
          </article>

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
        </section>
      </div>

      <div
        class="splitter splitter--h"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Arrastrar para tamaño del panel de destinos"
        on:pointerdown={beginDestPanelDrag}
      ></div>

      <section class="dest-panel om-panel dest-panel--bottom" aria-label="Carpetas destino">
        <span class="field-label dest-panel__title">Carpetas destino</span>
        <div class="dest-panel__main">
          <div class="dest-panel__toolbar">
            <button type="button" class="om-btn om-btn--primary om-btn--compact" on:click={openAddDestForm}>
              + Agregar carpeta
            </button>
          </div>
          <div class="dest-grid-wrap dest-grid-wrap--embedded dest-grid-wrap--scroll">
          {#if destRows.length === 0}
            <p class="dest-empty-hint">No hay carpetas destino. Pulsa «+ Agregar carpeta» o revisa que la ruta tenga permisos.</p>
          {/if}
          {#each destRows as d, i (d.path + "\0" + i)}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <div
              class="dest-card"
              class:dest-card--drop-target={dragOverDestPath === d.path}
              data-dest-path={d.path}
              role="group"
              aria-label="Destino {d.label}"
              title={d.path}
              on:click={(e) => onDestCardClick(e, d.path)}
              on:contextmenu={(e) => onDestContextMenu(e, i)}
              on:dragenter|preventDefault
              on:dragover|preventDefault
              on:drop={(e) => onDestDrop(e, d.path)}
            >
              <div class="dest-card__head">
                <span class="dest-card__title">{d.label}</span>
                <span class="dest-card__path">{d.path}</span>
              </div>
              <div class="dest-card__actions">
                <button type="button" class="om-btn om-btn--primary" on:click|stopPropagation={() => moveToDest(d.path)}>Mover aquí</button>
                <button type="button" class="om-btn om-btn--ghost" on:click|stopPropagation={() => openDestPreview(d.path)}>Ver carpeta</button>
              </div>
            </div>
          {/each}
          </div>
        </div>
      </section>
    </div>
  {:else}
    <section
      class="content"
      style={`grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`}
    >
      <article class="gallery om-panel om-panel--lift">
        <div class="grid" style={`--cell:${gridCellPx}px`}>
          {#each items as it (it.path)}
            <button
              type="button"
              class="tile"
              data-item-path={it.path}
              class:selected={it.selected && activeTab === "destinos"}
              draggable={activeTab === "destinos" && it.kind === "image"}
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
              <span class="tile__name">{it.name}</span>
            </button>
          {/each}
        </div>
      </article>

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
    </section>
  {/if}

  <footer class="pager om-panel pager--bar" aria-label="Paginación y estado">
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
    <div class="grow"></div>
    <span class="status-line">{status}</span>
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
          <button type="button" class="om-btn om-btn--ghost" on:click={() => (previewOpen = false)}>Cerrar</button>
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
            <button type="button" class="om-btn om-btn--ghost" on:click={() => (previewZoomOpen = false)}>Cerrar</button>
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
            </div>
          {:else}
            <div class="preview__empty">Cargando imagen…</div>
          {/if}
        </div>
        <div class="zoom-modal__carousel" class:zoom-modal__carousel--hidden={!previewZoomCarouselVisible} aria-label="Carrusel de miniaturas">
          {#each zoomNavItems as it}
            <button
              type="button"
              class="zoom-carousel__item"
              class:zoom-carousel__item--active={it.path === previewZoomPath}
              title={it.name}
              on:click={() => openPreviewZoom(it, { preserveCarousel: true, navItems: zoomNavItems })}
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
          <button type="button" class="om-btn om-btn--ghost" on:click={() => (orgPanelOpen = false)}>Cerrar</button>
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
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openEditFromCtx}>Editar…</button>
      <button type="button" class="dest-ctx-menu__item dest-ctx-menu__item--danger" role="menuitem" on:click={removeDestFromCtx}>Eliminar</button>
    </div>
  {/if}

  {#if destFormOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim" role="presentation" on:click|self={closeDestForm}>
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
          <button type="button" class="om-btn om-btn--ghost" on:click={closeDestForm}>Cerrar</button>
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
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelSettingsModal}>Cerrar</button>
        </header>
        <section class="settings-body">
          <label class="field-label" for="set-thumbs-page">Imágenes por página</label>
          <input
            id="set-thumbs-page"
            class="om-input"
            type="number"
            min="12"
            max="120"
            bind:value={thumbsPerPage}
          />
          <p class="settings-hint">Valores más bajos (p. ej. 24–48) aceleran el cambio de página; el máximo es 120.</p>
        </section>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelSettingsModal}>Cancelar</button>
          <button type="button" class="om-btn om-btn--primary" on:click={saveSettingsModal}>Guardar</button>
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
    gap: var(--om-space-4);
    /* tabs · área principal · paginador */
    grid-template-rows: auto 1fr auto;
    padding: var(--om-space-4) var(--om-space-5);
    font-family: var(--om-font-sans);
    color: var(--om-text-primary);
    background: radial-gradient(120% 80% at 50% -20%, rgb(124 140 255 / 0.12), transparent 50%), var(--om-bg-base);
    box-sizing: border-box;
  }

  /* Ruta u Organizar: barra extra bajo pestañas (ruta u org). */
  .app.app--layout-ruta,
  .app.app--layout-org {
    grid-template-rows: auto auto 1fr auto;
  }

  .tabs-bar {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .tabs__nav {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
    align-items: center;
  }

  .route {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--om-space-3);
  }

  .route__row {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .recent-folders__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .recent-folders__hint {
    font-size: 0.7rem;
    color: var(--om-text-muted);
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
    min-width: min(280px, 100%);
  }

  .field-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--om-text-secondary);
    white-space: nowrap;
  }

  .content {
    display: grid;
    gap: 0;
    min-height: 0;
    align-items: stretch;
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

  .splitter--h {
    cursor: row-resize;
    height: 10px;
    width: auto;
    margin: -2px 0;
    touch-action: none;
    background: linear-gradient(90deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.02));
  }

  .destinos-work {
    display: grid;
    gap: 0;
    min-height: 0;
    align-items: stretch;
  }

  .destinos-work--drag .splitter--h {
    background: rgb(124 140 255 / 0.35);
  }

  .destinos-work__top {
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .destinos-work__top > .content {
    flex: 1;
    min-height: 0;
  }

  .dest-panel--bottom {
    min-height: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: var(--om-space-2);
    overflow: visible;
    container-type: size;
    container-name: dest-panel;
  }

  /* Botón en la misma fila que las tarjetas; grid evita colapso de altura del flex + min-height:0. */
  .dest-panel__main {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: start;
    gap: var(--om-space-3);
    min-height: 0;
    flex: 1;
  }

  /* Sobrescribe el padding de .om-panel (16px) para ganar área útil a las chips. */
  .dest-panel.dest-panel--bottom.om-panel {
    padding: var(--om-space-2) var(--om-space-3);
  }

  @container dest-panel (max-height: 200px) {
    .dest-panel__title {
      font-size: 0.65rem;
    }
  }

  /* Sin container-type aquí: con size + flex/grid anidado la caja puede quedar a altura 0 (tarjetas invisibles). */
  .dest-grid-wrap--scroll {
    min-width: 0;
    min-height: 0;
    overflow: auto;
    overflow-x: auto;
  }

  /* Scroll interno: la barra de selección va con position:sticky y sigue visible al bajar. */
  .gallery--with-float {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }

  .gallery--with-float .gallery__scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
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
    /* Ancho fijo por celda (sin 1fr): el slider recorre muchos tamaños sin quedar atrapado en 2–3 columnas. */
    grid-template-columns: repeat(auto-fill, minmax(var(--cell, 160px), var(--cell, 160px)));
    gap: var(--om-space-3);
    contain: layout style;
  }

  /* Durante DnD, los botones de la tarjeta capturan eventos; el área de drop es la tarjeta. */
  :global(body.om-dragging) .dest-card .om-btn {
    pointer-events: none;
  }

  :global(body.om-dragging) .splitter,
  :global(body.om-dragging) .splitter--h {
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
    border-radius: var(--om-radius-md);
    color: var(--om-text-primary);
    text-align: left;
    padding: var(--om-space-2);
    cursor: pointer;
    box-shadow: var(--om-shadow-sm);
    transition:
      transform var(--om-transition),
      box-shadow var(--om-transition),
      border-color var(--om-transition);
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
    outline: 2px solid var(--om-accent);
    outline-offset: 2px;
    box-shadow: 0 0 20px var(--om-accent-glow);
  }

  .tile img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: var(--om-radius-sm);
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
    border-radius: var(--om-radius-sm);
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
    display: block;
    margin-top: var(--om-space-2);
    font-size: 0.7rem;
    line-height: 1.25;
    color: var(--om-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  .dest-panel__title {
    display: block;
    flex-shrink: 0;
    margin-bottom: 0;
  }

  .dest-panel--bottom .dest-panel__title {
    margin-bottom: 0;
  }

  .dest-panel__toolbar {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    margin-bottom: 0;
    /* Alinea el botón con el borde superior de las tarjetas (padding de .dest-card). */
    padding-top: var(--om-space-1);
  }

  .dest-panel__toolbar .om-btn {
    min-height: 2rem;
    padding: 0.45rem 0.85rem;
    font-size: 0.8rem;
    line-height: 1.2;
    white-space: normal;
    text-wrap: balance;
    text-align: center;
  }

  .org-tab-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--om-space-4);
    justify-content: space-between;
  }

  .org-tab-bar__text {
    margin: 0;
    font-size: 0.875rem;
    color: var(--om-text-secondary);
    max-width: min(520px, 100%);
    line-height: 1.45;
  }

  .dest-grid-wrap {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--om-space-4);
  }

  .dest-grid-wrap--embedded {
    margin: 0;
  }

  .dest-empty-hint {
    margin: 0;
    grid-column: 1 / -1;
    padding: var(--om-space-2);
    font-size: 0.8125rem;
    line-height: 1.45;
    color: var(--om-text-muted);
  }

  .dest-card {
    background: linear-gradient(165deg, var(--om-surface-2) 0%, var(--om-surface-1) 100%);
    border: 1px solid var(--om-border-default);
    border-radius: var(--om-radius-lg);
    padding: var(--om-space-4);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-4);
    box-shadow: var(--om-shadow-md);
    transition: box-shadow var(--om-transition), border-color var(--om-transition);
    cursor: pointer;
  }

  .dest-card:hover {
    border-color: rgb(124 140 255 / 0.3);
    box-shadow: var(--om-shadow-lg);
  }

  /* Carpeta destino activa mientras el arrastre está encima (soltar aquí). */
  .dest-card.dest-card--drop-target {
    border-color: rgb(124 140 255 / 0.8);
    background: linear-gradient(
      165deg,
      rgb(124 140 255 / 0.18) 0%,
      rgb(94 228 212 / 0.08) 45%,
      var(--om-surface-1) 100%
    );
    box-shadow: var(--om-shadow-md);
    position: relative;
    z-index: 0;
    isolation: isolate; /* permite que el pseudo-elemento “halo” quede detrás sin romper stacking */
    transition:
      border-color 0.12s ease,
      background 0.12s ease,
      box-shadow 0.12s ease;
  }

  /* Glow difuminado (no rectangular) para drop target. */
  .dest-card.dest-card--drop-target::after {
    content: "";
    position: absolute;
    inset: -4px;
    border-radius: inherit;
    z-index: -1;
    pointer-events: none;
    opacity: 1;
    background:
      radial-gradient(
        circle at 22% 18%,
        rgb(94 228 212 / 0.55) 0%,
        transparent 55%
      ),
      radial-gradient(
        circle at 78% 82%,
        rgb(124 140 255 / 0.45) 0%,
        transparent 58%
      ),
      linear-gradient(
        180deg,
        rgb(124 140 255 / 0.18) 0%,
        rgb(94 228 212 / 0.10) 100%
      );
    filter: blur(12px) saturate(1.15);
    transform: translateZ(0);
  }

  .dest-card__head {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
  }

  .dest-card__title {
    font-weight: 700;
    font-size: 0.95rem;
  }

  .dest-card__path {
    font-size: 0.75rem;
    color: var(--om-text-muted);
    word-break: break-all;
  }

  .dest-card__actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
  }

  /* Vista chip: panel bajo bajo — usa dest-panel (altura real), no el scroll (antes rompía con container-type:size). */
  @container dest-panel (max-height: 140px) {
    .dest-panel__toolbar .om-btn {
      min-height: 1.65rem;
      padding: 0.28rem 0.62rem;
      font-size: 0.72rem;
    }

    .dest-grid-wrap--scroll {
      display: flex;
      flex-wrap: wrap;
      align-content: flex-start;
      align-items: flex-start;
      gap: 8px;
      row-gap: 8px;
    }

    /* Ancho al texto (hasta un máximo); sin flex-grow que deja hueco vacío. */
    .dest-grid-wrap--scroll > .dest-card {
      flex: 0 0 auto;
      align-self: flex-start;
      width: fit-content;
      max-width: min(22rem, 100%);
      min-width: 0;
      box-sizing: border-box;
      padding: 6px 12px;
      gap: 0;
      box-shadow: var(--om-shadow-sm);
      border-radius: var(--om-radius-sm);
      cursor: pointer;
    }

    .dest-grid-wrap--scroll > .dest-card.dest-card--drop-target {
      box-shadow: var(--om-shadow-sm);
      border-color: rgb(124 140 255 / 0.85);
    }

    .dest-card__head {
      gap: 0;
      min-width: 0;
      flex: 0 0 auto;
      width: fit-content;
      max-width: 100%;
    }

    .dest-card__path {
      display: none;
    }

    .dest-card__actions {
      display: none;
    }

    .dest-card__title {
      font-size: 0.875rem;
      font-weight: 600;
      line-height: 1.35;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
    }
  }

  @container dest-panel (min-height: 240px) {
    .dest-panel__toolbar .om-btn {
      min-height: 2.5rem;
      padding: 0.65rem 1.1rem;
      font-size: 0.9rem;
      line-height: 1.25;
    }
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
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-gutter: stable;
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
    max-width: min(42vw, 520px);
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
    min-height: 2rem;
    padding: var(--om-space-1) var(--om-space-2);
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

  .status-line {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--om-accent-2);
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

  .modal--settings {
    width: min(420px, 92vw);
    max-height: min(90vh, 560px);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-4);
    padding: var(--om-space-5);
    box-sizing: border-box;
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
    gap: var(--om-space-2);
  }

  .settings-hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--om-text-muted);
    line-height: 1.4;
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
  }

  .zoom-modal__tools {
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
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
    width: auto;
    height: 100%;
    max-height: none;
    max-width: none;
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
    border-color: rgb(124 140 255 / 0.85);
    box-shadow: 0 0 0 1px rgb(94 228 212 / 0.35), 0 0 14px rgb(124 140 255 / 0.3);
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
