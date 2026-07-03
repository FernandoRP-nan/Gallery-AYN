<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  let pollTimer: number | null = null;
  import { bridge, type GalleryItem } from "./lib/api";
  import ConfirmDeleteModal from "./components/ConfirmDeleteModal.svelte";
  import LoadOverlay from "./components/LoadOverlay.svelte";
  import SettingsModal from "./components/SettingsModal.svelte";
  import DebugLogPanel from "./components/DebugLogPanel.svelte";
  import { applyGalleryPerfConfig, galleryPerfFromSettings, getGalleryPerfConfig } from "./lib/galleryPerfConfig";
  import { setGalleryDebugLogEnabled, galleryDbg, setGalleryDebugFilters, normalizeGalleryDebugFilters, DEFAULT_GALLERY_DEBUG_FILTERS, logGallerySelectionDelta, type GalleryDebugFilters } from "./lib/galleryDebugLog";
  import { logGallerySortLayout } from "./lib/gallerySortLayoutLog";
  import { t } from "./lib/i18n";
  import { normalizePathForApi, buildMediaFileUrl, isValidFolderName } from "./lib/pathUtils";
  import { copyTextToClipboard } from "./lib/clipboardText";
  import { mergePreviewApiResult } from "./lib/previewUtils";
  import {
    computeMiniMapImageLayout,
    computeMiniMapRectStyle,
    computeMiniMapSize,
    computeViewportNorm,
    miniMapHasOverflow,
    miniMapPointToNorm,
    panFromMiniMapNorm,
  } from "./lib/zoomMiniMap";
  import { resolveMediaPlaybackInfo, pickInitialPlaybackUrl, sameMediaUrl, mediaUrlKey, isDataPlaybackUrl, playbackPrepareMessage, type MediaPlaybackInfo, type VideoPlaybackMode } from "./lib/mediaUrl";
  import { canTranscodeVideo, tryAutoplayVideo, waitForTranscodeCache } from "./lib/videoPlayback";
  import { transcodeProgressForPath } from "./lib/videoTranscodeUi";
  import { scheduleNextZoomVideoWarm, cancelZoomVideoWarm } from "./lib/videoCarouselWarm";
  import {
    formatVideoDiagnosticReport,
    isQtPlayerCreationError,
    mediaErrorLabel,
    probeVideoHttpUrl,
    type VideoBackendDiagnostics,
  } from "./lib/videoDiagnostics";
  import { galleryGridCellPx, thumbQualityRefreshNeeded, galleryThumbPx } from "./lib/thumbScale";
  import GalleryWorkspace from "./components/GalleryWorkspace.svelte";
  import DestPreviewModal from "./components/DestPreviewModal.svelte";
  import MessPanel from "./components/MessPanel.svelte";
  import DestMoveCtxTree from "./components/DestMoveCtxTree.svelte";
  import DestMoveFlyoutPortals from "./components/DestMoveFlyoutPortals.svelte";
  import { sectionDestMoveActive, sectionDestMoveCtx } from "./lib/sectionDestMoveState";
  import {
    cancelMoveMenuClose,
    moveDestPanelOpen,
    moveRootHovered,
    onMoveRootPointerLeave,
    resetMoveFlyoutState,
  } from "./lib/destMoveFlyoutState";
  import PagerBar from "./components/PagerBar.svelte";
  import PreviewZoomPanel from "./components/PreviewZoomPanel.svelte";
  import PreviewVideoIdle from "./components/PreviewVideoIdle.svelte";
  import PreviewVideoProfiles from "./components/PreviewVideoProfiles.svelte";
  import PreviewSelectionGrid from "./components/PreviewSelectionGrid.svelte";
  import {
    applyGalleryMutationResponse,
    galleryItems,
    getGalleryItems,
    getGalleryState,
    mergeGalleryItemsFromApi,
    patchGallerySelection,
    setGalleryPayload,
    setGalleryState,
    setGalleryItems,
    syncSelectedCountFromItems,
    updateGalleryItems,
    type GalleryMutationResponse,
    type GalleryState,
  } from "./lib/galleryRuntime";
  import { clearVisitedGalleryCache } from "./lib/galleryVisitedCache";
  import { clearMasonryHeightCache } from "./lib/galleryMasonryHeightCache";
  import {
    bumpGalleryThumbHydrationToken,
    disposeGalleryThumbs,
    galleryThumbHydrating,
    invalidateGalleryThumbHqForScale,
    refreshGalleryThumbsForScale,
  } from "./lib/galleryThumbs";
  import { cancelZoomCarouselHydration, hydrateZoomCarouselThumbs } from "./lib/zoomCarouselThumbs";
  import {
    formatGallerySortMode,
    isTimelineDateSortKey,
    parseGallerySortMode,
    primaryGallerySortKey,
  } from "./lib/gallerySort";
  import type { ActiveProcess } from "./components/PagerBar.svelte";
  import { removeGalleryThumbHq, seedGalleryThumbHqFromItems, stripHqFromGalleryItems, hasGalleryThumbHq, getGalleryThumbHqValidPx } from "./lib/galleryThumbHqCache";
  import {
    bumpGalleryNavigationGeneration,
    getGalleryNavigationGeneration,
    isGalleryNavigationCurrent,
  } from "./lib/gallerySession";
  import { commitChromePagerState } from "./lib/chromeRemember";
  import {
    collectRemovedMediaIndices,
    isGalleryMediaKind,
    isGallerySelectableKind,
    mergeItemsKeepingBestThumb,
    shiftGalleryMediaIndicesAfterRemoval,
  } from "./lib/galleryUtils";
  import {
    applyUiThemeToDocument,
    normalizeUiTheme,
    readCachedUiTheme,
    type UiThemeId,
  } from "./lib/uiTheme";
  import type { TreeNode } from "./lib/itemTree";
  import {
    cloneTree,
    destToolbarItems as buildDestToolbarItems,
    findParentFolderId,
    isDestNode,
    isFolderNode,
    flattenMarkerPaths,
    folderLabelAt,
    getChildrenAt,
    markerToolbarItems as buildMarkerToolbarItems,
    normalizeTreeNodes,
    parentIdOrEmpty,
  } from "./lib/itemTree";

  const BLANK_DRAG_IMG =
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  let folder = "";
  let galleryWorkspace: GalleryWorkspace | null = null;
  /** Árbol de carpetas destino y carpeta activa en la barra inferior. */
  let destTree: TreeNode[] = [];
  let destToolbarFolderId: string | null = null;
  let markerTree: TreeNode[] = [];
  let markerToolbarFolderId: string | null = null;
  let destTreeSettingsDraft: TreeNode[] = [];
  let markerTreeSettingsDraft: TreeNode[] = [];
  $: destToolbarVisibleItems = buildDestToolbarItems(destTree, destToolbarFolderId);
  $: destToolbarFolderLabel = folderLabelAt(destTree, destToolbarFolderId);
  $: destToolbarCanGoBack = Boolean(destToolbarFolderId);
  function destTreeHasMoveTargets(nodes: TreeNode[]): boolean {
    for (const n of nodes) {
      if (isDestNode(n)) return true;
      if (isFolderNode(n) && destTreeHasMoveTargets(n.children)) return true;
    }
    return false;
  }

  $: destTreeHasTargets = destTreeHasMoveTargets(destTree);
  $: markerToolbarVisibleItems = buildMarkerToolbarItems(markerTree, markerToolbarFolderId);
  $: markerToolbarCanGoBack = Boolean(markerToolbarFolderId);
  let selectedPreview: {
    path: string;
    name: string;
    dataUrl: string | null;
    placeholderUrl?: string | null;
    mediaType?: "image" | "video" | "svg";
    fileUrl?: string | null;
  } | null = null;
  let status = t("status.ready");
  let thumbScale = 1;
  /** Escala ya aplicada en servidor/caché HQ (detecta saltos de tamaño en px). */
  let appliedThumbScale = 1;
  let previewOpen = false;
  let previewDestPath = "";
  let destPreviewModal: DestPreviewModal | null = null;
  let galleryRangeSelecting = false;
  let galleryRangeSuppressClick = false;
  let galleryCursorPath: string | null = null;
  let galleryKeyboardRangeAnchorPath: string | null = null;
  let galleryKeyboardNavHintActive = false;
  let previewZoomOpen = false;
  let previewZoomPath = "";
  let previewZoomName = "";
  let previewZoomDataUrl: string | null = null;
  /** Miniatura estable para el minimapa (no cambia al alternar resolución nativa). */
  let previewZoomMiniSrc: string | null = null;
  let miniMapDrag = false;
  let previewZoomScale = 1;
  let previewZoomMode: "fit" | "fillWidth" = "fit";
  let previewFillWidthAlignPending = false;
  let previewPanX = 0;
  let previewPanY = 0;
  let previewPanDrag = false;
  let previewPanMoved = false;
  let previewPanPointerDown = false;
  let previewPanDownX = 0;
  let previewPanDownY = 0;
  let previewPanStartX = 0;
  let previewPanStartY = 0;
  const PAN_DRAG_THRESHOLD_PX = 5;
  let previewZoomCarouselVisible = true;
  let previewZoomDestMode = false;
  let previewZoomCanUndoMove = false;
  let zoomMoveQueue: Array<{ srcPath: string; destPath: string }> = [];
  let zoomMoveWorkerRunning = false;
  let galleryMoveQueue: GalleryMoveJob[] = [];
  let galleryMoveWorkerRunning = false;
  let galleryDeleteQueue: GalleryDeleteJob[] = [];
  let galleryDeleteWorkerRunning = false;
  let galleryLoadingMore = false;
  let zoomHudVisible = false;
  let zoomHudTimer: ReturnType<typeof setTimeout> | null = null;
  let zoomStageEl: HTMLDivElement | null = null;
  let zoomCarouselEl: HTMLDivElement | null = null;
  let zoomImgEl: HTMLImageElement | null = null;
  let zoomVideoEl: HTMLVideoElement | null = null;
  let previewZoomMediaType: "image" | "video" | "svg" = "image";
  let previewZoomFileUrl: string | null = null;
  let previewVideoSrc = "";
  let previewVideoError = "";
  let previewVideoErrorDetails = "";
  let previewVideoLastErrorDetail = "";
  let previewVideoDiagLoading = false;
  let previewVideoTriedUrls: string[] = [];
  let previewVideoPlayback: MediaPlaybackInfo | null = null;
  let previewZoomPlayback: MediaPlaybackInfo | null = null;
  let previewVideoPreparing = false;
  let previewVideoPrepareMsg = "";
  /** true tras pulsar reproducir; evita precargar al seleccionar o saltar entre vídeos. */
  let previewVideoEl: HTMLVideoElement | null = null;
  let previewVideoArmed = false;
  let previewVideoLaunching = false;
  let previewVideoPlayLocked = false;
  let previewVideoSession = 0;
  /** Evita que respuestas tardías de galleryPreview sobrescriban otro elemento. */
  let previewLoadGeneration = 0;
  let previewZoomVideoArmed = false;
  let previewZoomVideoLaunching = false;
  let previewZoomVideoPlayLocked = false;
  let previewZoomVideoStatus = "";
  let previewZoomVideoSession = 0;
  let previewZoomVideoPreparing = false;
  let previewZoomThumbUrl: string | null = null;
  let videoTranscodeJobs: Array<{ id: string; path: string; name: string; format: string; progress?: string; status?: string }> = [];
  let videoPreparePollTimer: number | null = null;
  let previewVideoMode: VideoPlaybackMode = "auto";
  let previewVideoAutoplay = true;
  let previewVideoAutoplayEdit = false;
  let previewVideoProfiles: Array<{ id: string; available: boolean; recommended?: boolean; strategy?: string }> = [];
  let previewVideoPreparePath = "";
  let videoTranscodePreset: "turbo" | "fast" | "quality" = "fast";
  let videoTranscodeMaxHeight = 1080;
  let videoTranscodeHw: "auto" | "off" = "auto";
  let videoTranscodePresetBackup: "turbo" | "fast" | "quality" = "fast";
  let videoTranscodeMaxHeightBackup = 1080;
  let videoTranscodeHwBackup: "auto" | "off" = "auto";
  let previewZoomNaturalW = 1;
  let previewZoomNaturalH = 1;
  let zoomMiniEl: HTMLDivElement | null = null;
  let galleryScrollEl: HTMLDivElement | null = null;
  let routePathEl: HTMLInputElement | null = null;
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
  let deferredZoomMoveRefresh: GalleryMutationResponse | null = null;
  let galleryScrollAtTop = true;
  let previewVisible = true;
  /** Vista previa visible antes de abrir fullscreen; null = no había zoom abierto. */
  let previewVisibleBeforeZoom: boolean | null = null;
  let prevPreviewZoomOpen = false;
  let destinationsMode = false;
  let folderBackStack: string[] = [];
  let folderForwardStack: string[] = [];
  /** Panel organizador en ventana flotante (tarea por lotes). */
  let orgPanelOpen = false;
  let messPanelOpen = false;
  let messFolderSetting = "";
  let messSimilaritySetting = 0.82;
  let messSuggestionsEnabled = false;
  let messPinterestMasonry = false;
  let messScanMaxFiles = 400;
  let messSuggestionsEnabledBackup = false;
  let messPinterestMasonryBackup = false;
  let messScanMaxFilesBackup = 400;
  /** Menú Vista (subcarpetas, orden, futuro agrupar). */
  let viewMenuOpen = false;
  let includeSubfolders = false;
  let groupByFolder = false;
  let groupByAlpha = false;
  /** Tinte de cabecera según color medio de imágenes (solo vista agrupada por carpeta). */
  let sectionDominantColor = true;
  /** Vista calendario: secciones por mes; marcas por día según zoom (solo cliente). */
  let timelineView = false;
  let galleryMasonryView = false;
  let galleryMasonryTightSpacing = false;
  let gallerySortMode = "name,mtime,type";
  let dynamicNameRegex = false;
  $: galleryTileDragEnabled = destinationsMode || (groupByFolder && !galleryMasonryView);
  let dragOverSectionPath: string | null = null;
  let settingsOpen = false;
  let thumbsPerPage = 48;
  let thumbsPerPageBackup = 48;
  let galleryUnlimitedBatchSize = 48;
  let galleryWindowOverscanBefore = 96;
  let galleryWindowOverscanAfter = 160;
  let galleryJumpCoreOverscanBefore = 32;
  let galleryJumpCoreOverscanAfter = 48;
  let gallerySlidingWindowEnabled = false;
  let gallerySlidingWindowMaxItems = 896;
  let galleryThumbBuildWorkers = 8;
  let galleryThumbHqWorkers = 4;
  let galleryThumbHqVisibleSequential = 16;
  let galleryCompactIndicesAfterMove = true;
  let galleryUnlimitedBatchSizeBackup = 48;
  let galleryWindowOverscanBeforeBackup = 96;
  let galleryWindowOverscanAfterBackup = 160;
  let galleryJumpCoreOverscanBeforeBackup = 32;
  let galleryJumpCoreOverscanAfterBackup = 48;
  let gallerySlidingWindowEnabledBackup = false;
  let gallerySlidingWindowMaxItemsBackup = 896;
  let galleryThumbBuildWorkersBackup = 8;
  let galleryThumbHqWorkersBackup = 4;
  let galleryThumbHqVisibleSequentialBackup = 16;
  let galleryCompactIndicesAfterMoveBackup = true;
  let debugLogEnabled = false;
  let debugLogEnabledBackup = false;
  let debugLogFilters: GalleryDebugFilters = { ...DEFAULT_GALLERY_DEBUG_FILTERS };
  let debugLogFiltersBackup: GalleryDebugFilters = { ...DEFAULT_GALLERY_DEBUG_FILTERS };
  let settingsThumbScaleDraft = 1;
  let thumbGapPx = 12;
  let showThumbLabels = true;
  let thumbCardStyle: "soft" | "flat" | "outlined" = "soft";
  let thumbFrameVisible = true;
  let thumbImageRadiusPx = 6;
  let thumbTileRadiusPx = 12;
  let thumbGapPxBackup = 12;
  let galleryMasonryTightSpacingBackup = false;
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
  let galleryThumbQualityPreset: "balanced" | "sharp" | "hidpi" | "performance" = "balanced";
  let galleryThumbQualityPresetBackup: "balanced" | "sharp" | "hidpi" | "performance" = "balanced";
  let pageJumpDraft = 1;
  let previewRatio = 0.4;
  /** Fracción de altura para el panel inferior de destinos (solo pestaña Destinos). */
  let destPanelRatio = 0.26;
  let destSplitDrag = false;
  /** Modal “ver carpeta destino”: ~80 % del viewport (sin sliders). */
  let orgPath = "";
  let orgRunning = false;
  let orgDetail = t("status.orgDetailIdle");
  let orgProgress = "0/0";
  let orgOptions = {
    includeOrganized: false,
    includeComics: false,
    includePending: false,
    removeDuplicates: false,
    groupSimilarImages: false,
    groupSimilarVisual: false
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
  let uiLoading = false;
  let uiLoadingMessage = "";
  let loadingTimeout: ReturnType<typeof setTimeout> | null = null;
  function trackLoad<T>(promise: Promise<T>, message = ""): Promise<T> {
    loadCount++;
    if (loadCount === 1) {
      uiLoadingMessage = message;
      if (loadingTimeout) clearTimeout(loadingTimeout);
      // Solo activa el spinner si la operación tarda más de 180ms (evita parpadeos en clics rápidos)
      loadingTimeout = setTimeout(() => {
        if (loadCount > 0) {
          uiLoading = true;
        }
      }, 180);
    }
    return promise.finally(() => {
      loadCount--;
      if (loadCount <= 0) {
        loadCount = 0;
        uiLoadingMessage = "";
        if (loadingTimeout) {
          clearTimeout(loadingTimeout);
          loadingTimeout = null;
        }
        uiLoading = false;
      }
    });
  }

  $: activeProcesses = (() => {
    const list: ActiveProcess[] = [];
    if (loadCount > 0) {
      list.push({
        id: "load",
        label: uiLoadingMessage ? `${t("pager.processLoading")}: ${uiLoadingMessage}` : t("pager.processLoading"),
      });
    }
    if ($galleryThumbHydrating) {
      list.push({ id: "thumbs-hq", label: t("pager.processThumbsHq") });
    }
    if (galleryLoadingMore) {
      list.push({ id: "load-more", label: t("pager.processLoadMore") });
    }
    if (galleryMoveWorkerRunning || galleryMoveQueue.length > 0) {
      list.push({
        id: "move",
        label: t("pager.processMoveQueue").replace("{n}", String(galleryMoveQueue.length)),
      });
    }
    if (galleryDeleteWorkerRunning || galleryDeleteQueue.length > 0) {
      list.push({
        id: "delete",
        label: t("pager.processDeleteQueue").replace("{n}", String(galleryDeleteQueue.length)),
      });
    }
    if (zoomMoveWorkerRunning || zoomMoveQueue.length > 0) {
      list.push({
        id: "zoom-move",
        label: t("pager.processZoomMove").replace("{n}", String(zoomMoveQueue.length)),
      });
    }
    if (orgRunning) {
      list.push({
        id: "organizer",
        label: orgDetail ? `${t("pager.processOrganizer")}: ${orgDetail}` : t("pager.processOrganizer"),
      });
    }
    for (const job of videoTranscodeJobs.filter(isActiveTranscodeJob)) {
      const pct =
        job.status === "running" && job.progress && job.progress !== "100" ? ` · ${job.progress}%` : "";
      const queued = job.status === "queued" ? ` (${t("pager.processQueued")})` : "";
      const base =
        job.format === "remux" ? t("pager.processVideoRemux") : t("pager.processVideoTranscode");
      list.push({
        id: `transcode-${job.id}`,
        label: `${base}${queued}: ${job.name}${pct}`,
      });
    }
    return list;
  })();

  $: previewZoomTranscodeProgress = (() => {
    if (!previewZoomVideoPreparing) return null;
    const jobPct = transcodeProgressForPath(previewZoomPath, videoTranscodeJobs);
    if (jobPct !== null) return jobPct;
    if (previewZoomFileUrl) return 100;
    return 0;
  })();

  function stopZoomVideoElement() {
    const el = zoomVideoEl;
    if (!el) return;
    try {
      el.pause();
      el.removeAttribute("src");
      el.load();
    } catch {
      /* ignore */
    }
  }

  async function teardownPreviewZoom() {
    const path = String(previewZoomPath ?? "").trim();
    previewZoomVideoSession += 1;
    stopVideoPreparePoll();
    cancelZoomVideoWarm();
    cancelZoomCarouselHydration();
    stopZoomVideoElement();
    previewZoomVideoArmed = false;
    previewZoomVideoLaunching = false;
    previewZoomVideoPlayLocked = false;
    previewZoomVideoPreparing = false;
    previewZoomFileUrl = null;
    previewPanPointerDown = false;
    previewPanDrag = false;
    previewPanMoved = false;
    if (confirmDeleteOpen) closeConfirmDelete();
    if (path) {
      try {
        await bridge.galleryTranscodeCancel(normalizePathForApi(path));
      } catch {
        /* ignore */
      }
      void pollVideoTranscodeJobs();
    }
  }

  /** Evita clics encolados mientras corre una operación de galería (Qt WebEngine + Python). */
  let galleryActionBusy = false;
  let thumbScaleDebounce: ReturnType<typeof setTimeout> | null = null;
  let prevThumbScaleForHq = thumbScale;

  $: {
    if (thumbScale !== prevThumbScaleForHq) {
      prevThumbScaleForHq = thumbScale;
      if (invalidateGalleryThumbHqForScale(thumbScale)) {
        void galleryWorkspace?.refreshThumbsAtScale(thumbScale);
      }
    }
  }

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

  /** Destinos: la API devuelve árbol + carpeta activa de la barra. */
  function applyDestinationsPayload(data: any) {
    const raw = data?.destinations ?? data?.settings?.destinations ?? data;
    destTree = normalizeTreeNodes(raw, "dest");
    const fid = String(data?.toolbarFolderId ?? "").trim();
    destToolbarFolderId = fid || null;
  }

  function applyMarkersPayload(data: any) {
    const raw = data?.markers ?? data?.settings?.marker_tree ?? data;
    markerTree = normalizeTreeNodes(raw, "marker");
    const fid = String(data?.toolbarFolderId ?? "").trim();
    markerToolbarFolderId = fid || null;
    pinnedFolders = flattenMarkerPaths(markerTree);
    const labels: Record<string, string> = {};
    for (const p of pinnedFolders) labels[p] = markerLabelFromTree(markerTree, p) ?? defaultMarkerNameForPath(p);
    pinnedFolderLabels = labels;
  }

  function markerLabelFromTree(nodes: TreeNode[], path: string): string | null {
    const target = String(path ?? "").trim();
    for (const node of nodes) {
      if (node.kind === "marker" && node.path === target) return node.label;
      if (node.kind === "folder") {
        const nested = markerLabelFromTree(node.children, target);
        if (nested) return nested;
      }
    }
    return null;
  }

  async function persistDestToolbarFolder(folderId: string | null) {
    destToolbarFolderId = folderId;
    try {
      await bridge.destinationsSetToolbarFolder(parentIdOrEmpty(folderId));
    } catch {
      /* conservar estado local si falla el bridge */
    }
  }

  async function navigateDestToolbarFolder(folderId: string) {
    await persistDestToolbarFolder(folderId);
  }

  async function destToolbarBack() {
    if (!destToolbarFolderId) return;
    const parent = findParentFolderId(destTree, destToolbarFolderId);
    await persistDestToolbarFolder(parent);
  }

  async function persistMarkerToolbarFolder(folderId: string | null) {
    markerToolbarFolderId = folderId;
    try {
      await bridge.markersSetToolbarFolder(parentIdOrEmpty(folderId));
    } catch {
      /* conservar estado local */
    }
  }

  async function navigateMarkerToolbarFolder(folderId: string) {
    await persistMarkerToolbarFolder(folderId);
  }

  async function markerToolbarBack() {
    if (!markerToolbarFolderId) return;
    const parent = findParentFolderId(markerTree, markerToolbarFolderId);
    await persistMarkerToolbarFolder(parent);
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

  /** Prioriza destinations_get (payload pequeño); get_initial_state a veces falla el parse en Qt. */
  async function syncDestinationsFromApi() {
    try {
      const d = await bridge.destinationsGet();
      applyDestinationsPayload(d);
    } catch {
      try {
        const data = await bridge.getInitialState();
        applyDestinationsPayload({
          destinations: data?.destinations,
          toolbarFolderId: data?.destToolbarFolderId ?? data?.settings?.web_dest_toolbar_folder_id,
        });
      } catch {
        destTree = [];
        destToolbarFolderId = null;
      }
    }
  }

  async function syncMarkersFromApi() {
    try {
      const m = await bridge.markersGet();
      applyMarkersPayload(m);
    } catch {
      try {
        const data = await bridge.getInitialState();
        applyMarkersPayload({
          markers: data?.markers ?? data?.settings?.marker_tree,
          toolbarFolderId: data?.markerToolbarFolderId ?? data?.settings?.web_marker_toolbar_folder_id,
          pinnedFolders: data?.pinnedFolders ?? data?.settings?.gallery_pinned_folders,
        });
      } catch {
        markerTree = [];
        markerToolbarFolderId = null;
      }
    }
  }

  async function refreshDestinationsFromServer() {
    await syncDestinationsFromApi();
  }

  const loadInitial = async () => {
    const data = await trackLoad(bridge.getInitialState());
    thumbScale = Number(data.settings?.gallery_thumb_scale ?? 1);
    appliedThumbScale = thumbScale;
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
    const last = normalizePathForApi(String(data.settings?.gallery_last_folder ?? ""));
    folder = normalizePathForApi(String(data.gallery?.folder ?? last) || "");
    orgPath = folder || orgPath;
    messFolderSetting = String(data.settings?.mess_folder_path ?? "").trim();
    messSimilaritySetting = Number(data.settings?.mess_similarity_min ?? 0.82);
    messSuggestionsEnabled = Boolean(data.settings?.mess_suggestions_enabled ?? false);
    messPinterestMasonry = Boolean(data.settings?.mess_pinterest_masonry ?? false);
    messScanMaxFiles = Math.max(50, Math.min(2000, Number(data.settings?.mess_scan_max_files ?? 400) || 400));
    if (data.gallery) setGalleryState(data.gallery);
    recentFolders = Array.isArray(data.settings?.gallery_recent_folders)
      ? (data.settings.gallery_recent_folders as string[]).map((p) => normalizePathForApi(String(p))).filter(Boolean)
      : [];
    pinnedFolders = Array.isArray(data.settings?.gallery_pinned_folders)
      ? (data.settings.gallery_pinned_folders as string[]).map((p) => normalizePathForApi(String(p))).filter(Boolean)
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
    groupByAlpha = Boolean(data.settings?.gallery_group_by_alpha ?? false);
    sectionDominantColor = Boolean(data.settings?.gallery_section_dominant_color ?? true);
    timelineView = Boolean(data.settings?.gallery_timeline_view ?? false);
    galleryMasonryView = Boolean(data.settings?.gallery_masonry_view ?? false);
    galleryMasonryTightSpacing = Boolean(data.settings?.gallery_masonry_tight_spacing ?? false);
    gallerySortMode = String(data.settings?.gallery_sort_mode ?? "name,mtime,type");
    dynamicNameRegex = Boolean(data.settings?.gallery_dynamic_name_regex ?? false);
    {
      const vp = String(data.settings?.video_transcode_preset ?? "fast").toLowerCase();
      videoTranscodePreset =
        vp === "quality" ? "quality" : vp === "turbo" ? "turbo" : "fast";
    }
    {
      const h = Number(data.settings?.video_transcode_max_height ?? 1080);
      videoTranscodeMaxHeight = Number.isFinite(h) ? (h <= 0 ? 0 : Math.max(480, Math.min(2160, Math.round(h)))) : 1080;
    }
    {
      const hw = String(data.settings?.video_transcode_hw ?? "auto").toLowerCase();
      videoTranscodeHw = hw === "off" ? "off" : "auto";
    }
    previewVideoAutoplay = Boolean(data.settings?.preview_video_autoplay ?? true);
    previewVideoAutoplayEdit = Boolean(data.settings?.preview_video_autoplay_edit ?? false);
    {
      const tq = String(data.settings?.gallery_thumb_quality_preset ?? "balanced").toLowerCase();
      galleryThumbQualityPreset =
        tq === "sharp" ? "sharp" : tq === "hidpi" ? "hidpi" : tq === "performance" ? "performance" : "balanced";
    }
    applyGalleryPerfConfig(galleryPerfFromSettings(data.settings as Record<string, unknown> | undefined));
    const perfCfg = getGalleryPerfConfig();
    galleryUnlimitedBatchSize = perfCfg.unlimitedBatchSize;
    galleryWindowOverscanBefore = perfCfg.windowOverscanBefore;
    galleryWindowOverscanAfter = perfCfg.windowOverscanAfter;
    galleryJumpCoreOverscanBefore = perfCfg.jumpCoreOverscanBefore;
    galleryJumpCoreOverscanAfter = perfCfg.jumpCoreOverscanAfter;
    gallerySlidingWindowEnabled = perfCfg.slidingWindowEnabled;
    gallerySlidingWindowMaxItems = perfCfg.slidingWindowMaxItems;
    galleryThumbBuildWorkers = perfCfg.thumbBuildWorkers;
    galleryThumbHqWorkers = perfCfg.thumbHqWorkers;
    galleryThumbHqVisibleSequential = perfCfg.thumbHqVisibleSequential;
    galleryCompactIndicesAfterMove = perfCfg.compactIndicesAfterMove;
    debugLogEnabled = Boolean(data.settings?.web_debug_log_enabled ?? false);
    setGalleryDebugLogEnabled(debugLogEnabled);
    debugLogFilters = normalizeGalleryDebugFilters(data.settings?.web_debug_log_filters);
    setGalleryDebugFilters(debugLogFilters);
    await syncDestinationsFromApi();
    await syncMarkersFromApi();
  };

  $: applyUiThemeToDocument(uiTheme);

  async function persistViewAndReload() {
    try {
      await trackLoad(
        bridge.settingsPatch({
          gallery_include_subfolders: includeSubfolders,
          gallery_sort_mode: gallerySortMode,
          gallery_dynamic_name_regex: dynamicNameRegex,
          gallery_group_by_folder: groupByFolder,
          gallery_group_by_alpha: groupByAlpha,
          gallery_timeline_view: timelineView,
          gallery_section_dominant_color: sectionDominantColor,
        })
      );
      await reload({ silent: false });
      status = t("status.viewUpdated");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.viewApplyError");
    }
  }

  async function onIncludeSubfoldersChange(checked: boolean) {
    includeSubfolders = checked;
    if (checked) {
      groupByFolder = false;
      groupByAlpha = false;
    }
    await persistViewAndReload();
  }

  async function onGroupByAlphaChange(checked: boolean) {
    groupByAlpha = checked;
    if (checked) {
      groupByFolder = false;
      timelineView = false;
    }
    await persistViewAndReload();
  }

  async function onGroupByFolderChange(checked: boolean) {
    groupByFolder = checked;
    if (checked) {
      includeSubfolders = false;
      timelineView = false;
      groupByAlpha = false;
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
      groupByAlpha = false;
      const parts = parseGallerySortMode(gallerySortMode);
      const datePart = parts.find((p) => isTimelineDateSortKey(p.key));
      if (datePart) {
        const rest = parts.filter((p) => p.key !== datePart.key);
        gallerySortMode = formatGallerySortMode([datePart, ...rest]);
      } else {
        gallerySortMode = formatGallerySortMode([{ key: "exif_month", dir: "desc" }, ...parts]);
      }
    }
    await persistViewAndReload();
  }

  async function onDynamicNameRegexChange(checked: boolean) {
    dynamicNameRegex = checked;
    await persistViewAndReload();
  }

  async function onGalleryMasonryViewChange(checked: boolean) {
    galleryMasonryView = checked;
    try {
      await trackLoad(bridge.settingsPatch({ gallery_masonry_view: checked }));
      bumpGalleryThumbHydrationToken(true);
      await reload({ silent: false });
      status = t("status.viewUpdated");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.viewApplyError");
    }
  }

  async function onGallerySortApply(mode: string) {
    gallerySortMode = mode;
    const primary = primaryGallerySortKey(mode);
    if (!isTimelineDateSortKey(primary) && timelineView) {
      timelineView = false;
    }
    viewMenuOpen = false;
    await persistViewAndReload();
  }

  async function onMessSuggestionMoved() {
    await reload({ silent: true });
    status = t("suggestions.movedOk");
  }

  /** Cancela trabajo en curso de la carpeta anterior (miniaturas HQ, colas, scroll infinito). */
  function beginGalleryNavigation(): number {
    const navGen = bumpGalleryNavigationGeneration();
    bumpGalleryThumbHydrationToken(true);
    galleryMoveQueue = [];
    galleryDeleteQueue = [];
    galleryWorkspace?.cancelBackgroundWork();
    return navGen;
  }

  /** Recarga o cambio de página en la misma carpeta: conserva caché HQ del cliente. */
  function beginGalleryRefresh(invalidateThumbCache = false): number {
    const navGen = bumpGalleryNavigationGeneration();
    bumpGalleryThumbHydrationToken(invalidateThumbCache);
    galleryMoveQueue = [];
    galleryDeleteQueue = [];
    galleryWorkspace?.cancelBackgroundWork();
    return navGen;
  }

  /** Tras cargar ítems: hidrata miniaturas HQ en GalleryWorkspace (aislado de la rejilla). */
  async function afterGalleryDataLoaded() {
    try {
      await tick();
      await galleryWorkspace?.afterGalleryPayloadLoaded(getGalleryItems(), thumbScale);
    } catch {
      /* La rejilla sigue mostrando LQ si falla la hidratación */
    }
    void logGallerySortLayout(() => bridge.galleryLayoutReport());
  }

  type GalleryScrollAnchor = {
    scrollTop: number;
    path: string | null;
    viewportOffsetPx: number;
  };

  type GalleryMutationSnapshot = {
    srcPaths: string[];
    scrollAnchor: GalleryScrollAnchor;
    prevItems: GalleryItem[];
    prevState: GalleryState;
    navGen: number;
  };

  type GalleryMoveJob = GalleryMutationSnapshot & {
    destPath: string;
    /** Si está definido, crea subcarpeta única bajo destPath (ruta padre). */
    newFolderName?: string;
  };

  type GalleryDeleteJob = GalleryMutationSnapshot;

  function findGalleryTileByPath(path: string): HTMLElement | null {
    if (!galleryScrollEl || !path) return null;
    for (const tile of galleryScrollEl.querySelectorAll<HTMLElement>("[data-item-path]")) {
      if (tile.dataset.itemPath === path) return tile;
    }
    return null;
  }

  function captureGalleryScrollAnchor(): GalleryScrollAnchor {
    const el = galleryScrollEl;
    if (!el) return { scrollTop: 0, path: null, viewportOffsetPx: 0 };
    const bounds = el.getBoundingClientRect();
    const scrollTop = el.scrollTop;
    for (const tile of el.querySelectorAll<HTMLElement>("[data-item-path]")) {
      const r = tile.getBoundingClientRect();
      if (r.bottom <= bounds.top + 4) continue;
      if (r.top >= bounds.bottom - 4) continue;
      const path = String(tile.dataset.itemPath ?? "").trim();
      if (!path) continue;
      return { scrollTop, path, viewportOffsetPx: r.top - bounds.top };
    }
    return { scrollTop, path: null, viewportOffsetPx: 0 };
  }

  async function restoreGalleryScrollAnchor(anchor: GalleryScrollAnchor) {
    const apply = () => {
      const el = galleryScrollEl;
      if (!el) return;
      if (anchor.path) {
        const tile = findGalleryTileByPath(anchor.path);
        if (tile) {
          const bounds = el.getBoundingClientRect();
          const r = tile.getBoundingClientRect();
          const delta = r.top - bounds.top - anchor.viewportOffsetPx;
          if (Math.abs(delta) > 0.5) {
            el.scrollTop = Math.max(0, el.scrollTop + delta);
          }
          return;
        }
      }
      const maxScroll = Math.max(0, el.scrollHeight - el.clientHeight);
      el.scrollTop = Math.min(anchor.scrollTop, maxScroll);
    };
    await tick();
    apply();
    requestAnimationFrame(apply);
  }

  /** Tras mover/eliminar: merge o delta sin recarga total de miniaturas ni salto de scroll. */
  async function applyGalleryItemsDelta(out: GalleryMutationResponse) {
    const anchor = captureGalleryScrollAnchor();
    if (Array.isArray(out.items)) {
      mergeGalleryItemsFromApi(out.items, out.state, { preserveSelection: true });
    } else {
      applyGalleryMutationResponse(out);
    }
    try {
      await tick();
      await galleryWorkspace?.afterGalleryMoveDelta(getGalleryItems(), thumbScale);
    } catch {
      /* merge ya aplicado */
    }
    await restoreGalleryScrollAnchor(anchor);
  }

  async function reconcileGalleryMoveSuccess(out: GalleryMutationResponse) {
    applyGalleryMutationResponse(out);
    await tick();
    void galleryWorkspace?.afterGalleryMoveDelta(getGalleryItems(), thumbScale);
  }

  function createGalleryMoveJobSnapshot(srcPaths: string[]): GalleryMutationSnapshot {
    return {
      srcPaths,
      scrollAnchor: captureGalleryScrollAnchor(),
      prevItems: getGalleryItems(),
      prevState: { ...getGalleryState() },
      navGen: getGalleryNavigationGeneration(),
    };
  }

  function syncGalleryUiAfterRemoval(removedPaths: Set<string>) {
    const nav = getGalleryNavigablePaths();
    if (galleryCursorPath && removedPaths.has(galleryCursorPath)) {
      galleryCursorPath = nav[0] ?? null;
    }
    if (destinationsMode) {
      const last = [...getGalleryItems()].reverse().find((x) => isGalleryMediaKind(x.kind));
      setSelectedPreviewFromPath(last?.path ?? null);
    }
  }

  async function applyOptimisticGalleryRemove(snapshot: GalleryMutationSnapshot) {
    const pathSet = new Set(snapshot.srcPaths);
    const removedMedia = snapshot.prevItems.filter(
      (x) => isGalleryMediaKind(x.kind) && pathSet.has(x.path)
    ).length;
    removeGalleryThumbHq(pathSet);
    const prevItems = getGalleryItems();
    const removedMediaIndices = collectRemovedMediaIndices(prevItems, pathSet);
    const compactAfterMove = getGalleryPerfConfig().compactIndicesAfterMove;
    updateGalleryItems((items) => {
      const filtered = items.filter((x) => !pathSet.has(x.path));
      return compactAfterMove
        ? shiftGalleryMediaIndicesAfterRemoval(filtered, removedMediaIndices)
        : filtered;
    });
    if (compactAfterMove) clearMasonryHeightCache();
    syncSelectedCountFromItems();
    logGallerySelectionDelta("optimistic:remove", prevItems, getGalleryItems(), {
      removedMedia,
      paths: snapshot.srcPaths.length,
    });
    const s = snapshot.prevState;
    setGalleryState({
      ...s,
      selectedCount: getGalleryState().selectedCount,
      total: Math.max(0, Number(s.total ?? 0) - removedMedia),
      endIndex: Math.max(0, Number(s.endIndex ?? 0) - removedMedia),
      totalElements: Math.max(0, Number(s.totalElements ?? s.total ?? 0) - removedMedia),
    });
    syncGalleryUiAfterRemoval(pathSet);
    await tick();
    await restoreGalleryScrollAnchor(snapshot.scrollAnchor);
  }

  async function rollbackOptimisticGalleryMutation(job: GalleryMutationSnapshot) {
    seedGalleryThumbHqFromItems(job.prevItems);
    setGalleryItems(stripHqFromGalleryItems(job.prevItems));
    setGalleryState(job.prevState);
    syncGalleryUiAfterRemoval(new Set(job.srcPaths));
    await restoreGalleryScrollAnchor(job.scrollAnchor);
  }

  async function rollbackOptimisticGalleryMove(job: GalleryMoveJob) {
    await rollbackOptimisticGalleryMutation(job);
  }

  async function navigateToFolder(path: string, opts?: { pushHistory?: boolean }) {
    closeGalleryItemCtxMenu();
    const target = normalizePathForApi(path);
    if (!target) return;
    const current = String(getGalleryState()?.folder ?? folder ?? "").trim();
    if (opts?.pushHistory !== false && current && current !== target) {
      folderBackStack = [...folderBackStack, current];
      folderForwardStack = [];
    }
    const navGen = beginGalleryNavigation();
    const t0 = performance.now();
    galleryDbg("user", "abriendo carpeta", { path: target });
    try {
      const out = await trackLoad(bridge.galleryLoadFolder(target), t("load.openingFolder"));
      galleryDbg("user", "carpeta cargada", {
        ms: Math.round(performance.now() - t0),
        items: Array.isArray(out.items) ? out.items.length : 0,
        total: out.state?.total ?? 0,
        scanMs: out.timing?.scanMs,
        buildMs: out.timing?.buildMs,
        fromCache: Boolean(out.timing?.fromCache),
        scanSource: out.timing?.scanSource ?? "fresh",
      });
      if (!isGalleryNavigationCurrent(navGen)) return;
      clearVisitedGalleryCache();
      clearMasonryHeightCache();
      setGalleryPayload(out.state, out.items);
      const mediaItems = getGalleryItems().filter((x) => x.kind === "image" || x.kind === "video");
      const withLq = mediaItems.filter((x) => Boolean(x.thumbDataUrl || x.thumbLqDataUrl)).length;
      galleryDbg("user", "miniaturas LQ en payload", {
        media: mediaItems.length,
        withLq,
        withoutLq: mediaItems.length - withLq,
      });
      await afterGalleryDataLoaded();
      if (!isGalleryNavigationCurrent(navGen)) return;
      if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
      pageJumpDraft = out.state.page;
      folder = out.state?.folder ?? target;
      orgPath = folder || orgPath;
      routePickerOpen = false;
      commitChromePagerState();
      status = t("status.folderLoaded").replace("{path}", folder);
    } catch (e: unknown) {
      if (!isGalleryNavigationCurrent(navGen)) return;
      status = e instanceof Error ? e.message : t("status.viewApplyError");
    }
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
    const current = String(getGalleryState()?.folder ?? folder ?? "").trim();
    const target = folderBackStack[folderBackStack.length - 1];
    folderBackStack = folderBackStack.slice(0, -1);
    if (current && current !== target) folderForwardStack = [...folderForwardStack, current];
    await navigateToFolder(target, { pushHistory: false });
  }

  async function goForwardFolder() {
    if (folderForwardStack.length === 0) return;
    const current = String(getGalleryState()?.folder ?? folder ?? "").trim();
    const target = folderForwardStack[folderForwardStack.length - 1];
    folderForwardStack = folderForwardStack.slice(0, -1);
    if (current && current !== target) folderBackStack = [...folderBackStack, current];
    await navigateToFolder(target, { pushHistory: false });
  }

  async function goUpFolder() {
    const current = String(getGalleryState()?.folder ?? folder ?? "").trim();
    if (!current) return;
    const parent = getParentFolder(current);
    if (!parent || parent === current) return;
    await navigateToFolder(parent, { pushHistory: true });
  }

  const pinFolder = async (path: string) => {
    try {
      const out = await bridge.galleryPinFolder(path);
      applyMarkersPayload(out);
      status = t("status.routePinned");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.routePinError");
    }
  };

  const unpinFolder = async (path: string) => {
    try {
      const out = await bridge.galleryUnpinFolder(path);
      applyMarkersPayload(out);
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

  /** Recarga ítems de la galería. Por defecto sin overlay global (la rejilla ya da feedback). */
  const reload = async (opts?: {
    silent?: boolean;
    loadingMessage?: string;
    invalidateThumbCache?: boolean;
  }) => {
    const brokenThumbs = getGalleryItems().some(
      (x) =>
        (x.kind === "image" || x.kind === "video") &&
        !x.thumbDataUrl &&
        !hasGalleryThumbHq(x.path)
    );
    const thumbPxStale = getGalleryThumbHqValidPx() !== galleryThumbPx(thumbScale);
    const navGen = beginGalleryRefresh(
      Boolean(opts?.invalidateThumbCache || brokenThumbs || thumbPxStale)
    );
    const p = bridge.galleryReload();
    const silent = opts?.silent !== false;
    const out = silent ? await p : await trackLoad(p, opts?.loadingMessage ?? t("load.loading"));
    if (!isGalleryNavigationCurrent(navGen)) return;
    setGalleryPayload(out.state, out.items ?? []);
    await afterGalleryDataLoaded();
  };

  const reloadGalleryFresh = () => reload({ invalidateThumbCache: true, silent: false });

  const goPage = async (page: number) => {
    const navGen = beginGalleryRefresh();
    const out = await trackLoad(bridge.galleryGoPage(page));
    if (!isGalleryNavigationCurrent(navGen)) return;
    setGalleryPayload(out.state, out.items);
    await afterGalleryDataLoaded();
    pageJumpDraft = out.state.page;
    commitChromePagerState();
  };

  const jumpToPageDraft = async () => {
    const n = Math.min(getGalleryState().totalPages, Math.max(1, Math.round(Number(pageJumpDraft)) || 1));
    pageJumpDraft = n;
    await goPage(n);
  };

  const openSettingsModal = () => {
    uiThemeBackup = uiTheme;
    thumbsPerPageBackup = thumbsPerPage;
    thumbGapPxBackup = thumbGapPx;
    galleryMasonryTightSpacingBackup = galleryMasonryTightSpacing;
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
    destTreeSettingsDraft = cloneTree(destTree);
    markerTreeSettingsDraft = cloneTree(markerTree);
    videoTranscodePresetBackup = videoTranscodePreset;
    videoTranscodeMaxHeightBackup = videoTranscodeMaxHeight;
    videoTranscodeHwBackup = videoTranscodeHw;
    galleryThumbQualityPresetBackup = galleryThumbQualityPreset;
    messPinterestMasonryBackup = messPinterestMasonry;
    messSuggestionsEnabledBackup = messSuggestionsEnabled;
    messScanMaxFilesBackup = messScanMaxFiles;
    galleryUnlimitedBatchSizeBackup = galleryUnlimitedBatchSize;
    galleryWindowOverscanBeforeBackup = galleryWindowOverscanBefore;
    galleryWindowOverscanAfterBackup = galleryWindowOverscanAfter;
    galleryJumpCoreOverscanBeforeBackup = galleryJumpCoreOverscanBefore;
    galleryJumpCoreOverscanAfterBackup = galleryJumpCoreOverscanAfter;
    gallerySlidingWindowEnabledBackup = gallerySlidingWindowEnabled;
    gallerySlidingWindowMaxItemsBackup = gallerySlidingWindowMaxItems;
    galleryThumbBuildWorkersBackup = galleryThumbBuildWorkers;
    galleryThumbHqWorkersBackup = galleryThumbHqWorkers;
    galleryThumbHqVisibleSequentialBackup = galleryThumbHqVisibleSequential;
    galleryCompactIndicesAfterMoveBackup = galleryCompactIndicesAfterMove;
    debugLogEnabledBackup = debugLogEnabled;
    debugLogFiltersBackup = { ...debugLogFilters };
    settingsOpen = true;
  };

  const cancelSettingsModal = () => {
    uiTheme = uiThemeBackup;
    thumbsPerPage = thumbsPerPageBackup;
    thumbGapPx = thumbGapPxBackup;
    galleryMasonryTightSpacing = galleryMasonryTightSpacingBackup;
    showThumbLabels = showThumbLabelsBackup;
    thumbCardStyle = thumbCardStyleBackup;
    thumbFrameVisible = thumbFrameVisibleBackup;
    thumbImageRadiusPx = thumbImageRadiusPxBackup;
    thumbTileRadiusPx = thumbTileRadiusPxBackup;
    keyboardShortcuts = { ...keyboardShortcutsBackup };
    destTreeSettingsDraft = cloneTree(destTree);
    markerTreeSettingsDraft = cloneTree(markerTree);
    videoTranscodePreset = videoTranscodePresetBackup;
    videoTranscodeMaxHeight = videoTranscodeMaxHeightBackup;
    videoTranscodeHw = videoTranscodeHwBackup;
    galleryThumbQualityPreset = galleryThumbQualityPresetBackup;
    messPinterestMasonry = messPinterestMasonryBackup;
    messSuggestionsEnabled = messSuggestionsEnabledBackup;
    messScanMaxFiles = messScanMaxFilesBackup;
    galleryUnlimitedBatchSize = galleryUnlimitedBatchSizeBackup;
    galleryWindowOverscanBefore = galleryWindowOverscanBeforeBackup;
    galleryWindowOverscanAfter = galleryWindowOverscanAfterBackup;
    galleryJumpCoreOverscanBefore = galleryJumpCoreOverscanBeforeBackup;
    galleryJumpCoreOverscanAfter = galleryJumpCoreOverscanAfterBackup;
    gallerySlidingWindowEnabled = gallerySlidingWindowEnabledBackup;
    gallerySlidingWindowMaxItems = gallerySlidingWindowMaxItemsBackup;
    galleryThumbBuildWorkers = galleryThumbBuildWorkersBackup;
    galleryThumbHqWorkers = galleryThumbHqWorkersBackup;
    galleryThumbHqVisibleSequential = galleryThumbHqVisibleSequentialBackup;
    galleryCompactIndicesAfterMove = galleryCompactIndicesAfterMoveBackup;
    debugLogEnabled = debugLogEnabledBackup;
    debugLogFilters = { ...debugLogFiltersBackup };
    setGalleryDebugLogEnabled(debugLogEnabled);
    setGalleryDebugFilters(debugLogFilters);
    settingsOpen = false;
  };

  async function pickSettingsDestFolder(): Promise<string | null> {
    try {
      const out = await bridge.dialogPickFolder("");
      if (out.cancelled || !out.path) return null;
      return out.path;
    } catch {
      return null;
    }
  }

  async function pickSettingsMarkerFolder(): Promise<string | null> {
    return pickSettingsDestFolder();
  }

  function clampSettingInt(raw: unknown, lo: number, hi: number, fallback: number): number {
    const n = Number(raw);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(lo, Math.min(hi, Math.round(n)));
  }

  const saveSettingsModal = async () => {
    const parsedPerPage = Number(thumbsPerPage);
    const perPageRaw = Number.isFinite(parsedPerPage) ? Math.round(parsedPerPage) : 48;
    const n = perPageRaw <= 0 ? 0 : Math.max(12, perPageRaw);
    const prevScale = appliedThumbScale;
    const prevThumbQuality = galleryThumbQualityPresetBackup;
    const ts = Math.max(0.01, Math.min(2.25, Number(settingsThumbScaleDraft) || 1));
    const thumbConfigChanged =
      thumbQualityRefreshNeeded(prevScale, ts) || galleryThumbQualityPreset !== prevThumbQuality;
    const needsGalleryReload = n !== thumbsPerPageBackup || thumbConfigChanged;

    galleryUnlimitedBatchSize = clampSettingInt(galleryUnlimitedBatchSize, 24, 256, 48);
    galleryWindowOverscanBefore = clampSettingInt(galleryWindowOverscanBefore, 32, 512, 96);
    galleryWindowOverscanAfter = clampSettingInt(galleryWindowOverscanAfter, 32, 512, 160);
    galleryJumpCoreOverscanBefore = clampSettingInt(galleryJumpCoreOverscanBefore, 16, 128, 32);
    galleryJumpCoreOverscanAfter = clampSettingInt(galleryJumpCoreOverscanAfter, 24, 160, 48);
    gallerySlidingWindowMaxItems = clampSettingInt(gallerySlidingWindowMaxItems, 320, 4096, 896);
    galleryThumbBuildWorkers = clampSettingInt(galleryThumbBuildWorkers, 2, 16, 8);
    galleryThumbHqWorkers = clampSettingInt(galleryThumbHqWorkers, 1, 16, 4);
    galleryThumbHqVisibleSequential = clampSettingInt(galleryThumbHqVisibleSequential, 4, 32, 16);

    thumbsPerPage = n;
    thumbScale = ts;
    keyboardShortcuts = {
      toggleMode: normalizeShortcutValue(keyboardShortcuts.toggleMode, defaultKeyboardShortcuts.toggleMode),
      deleteAction: normalizeShortcutValue(keyboardShortcuts.deleteAction, defaultKeyboardShortcuts.deleteAction),
      zoomPrev: normalizeShortcutValue(keyboardShortcuts.zoomPrev, defaultKeyboardShortcuts.zoomPrev),
      zoomNext: normalizeShortcutValue(keyboardShortcuts.zoomNext, defaultKeyboardShortcuts.zoomNext),
      escape: normalizeShortcutValue(keyboardShortcuts.escape, defaultKeyboardShortcuts.escape),
    };

    uiLoading = true;
    uiLoadingMessage = t("settings.saving");
    try {
      await bridge.settingsPatch({
        gallery_thumbs_per_page: n, // 0 = sin límite
        gallery_unlimited_batch_size: galleryUnlimitedBatchSize,
        gallery_window_overscan_before: galleryWindowOverscanBefore,
        gallery_window_overscan_after: galleryWindowOverscanAfter,
        gallery_jump_core_overscan_before: galleryJumpCoreOverscanBefore,
        gallery_jump_core_overscan_after: galleryJumpCoreOverscanAfter,
        gallery_sliding_window_enabled: Boolean(gallerySlidingWindowEnabled),
        gallery_sliding_window_max_items: gallerySlidingWindowMaxItems,
        gallery_thumb_build_workers: galleryThumbBuildWorkers,
        gallery_thumb_hq_workers: galleryThumbHqWorkers,
        gallery_thumb_hq_visible_sequential: galleryThumbHqVisibleSequential,
        gallery_compact_indices_after_move: Boolean(galleryCompactIndicesAfterMove),
        web_debug_log_enabled: Boolean(debugLogEnabled),
        web_debug_log_filters: { ...debugLogFilters },
        gallery_thumb_scale: Number(ts.toFixed(3)),
        gallery_thumb_quality_preset: galleryThumbQualityPreset,
        web_ui_theme: uiTheme,
        web_thumb_gap_px: Math.max(0, Math.round(thumbGapPx)),
        web_show_thumb_labels: Boolean(showThumbLabels),
        web_thumb_card_style: thumbCardStyle,
        web_thumb_frame_visible: Boolean(thumbFrameVisible),
        web_thumb_image_radius_px: Math.round(thumbImageRadiusPx),
        web_thumb_tile_radius_px: Math.round(thumbTileRadiusPx),
        web_shortcuts: { ...keyboardShortcuts },
        video_transcode_preset: videoTranscodePreset,
        video_transcode_max_height: Math.max(0, Math.min(2160, Math.round(Number(videoTranscodeMaxHeight) || 1080))),
        video_transcode_hw: videoTranscodeHw,
        mess_suggestions_enabled: Boolean(messSuggestionsEnabled),
        mess_pinterest_masonry: Boolean(messPinterestMasonry),
        mess_scan_max_files: Math.max(50, Math.min(2000, Math.round(Number(messScanMaxFiles) || 400))),
        gallery_masonry_tight_spacing: Boolean(galleryMasonryTightSpacing),
      });
      if (selectedPreview?.mediaType === "video" && selectedPreview.path) {
        previewVideoMode = "auto";
        void loadPreviewVideoProfiles(selectedPreview.path);
        resetPreviewVideoPlaybackUi({ keepPath: true });
        requestPreviewVideoPlay();
      }
      await trackLoad(bridge.destinationsSaveTree(destTreeSettingsDraft));
      await trackLoad(bridge.markersSaveTree(markerTreeSettingsDraft));
      await syncDestinationsFromApi();
      await syncMarkersFromApi();
      applyGalleryPerfConfig({
        unlimitedBatchSize: galleryUnlimitedBatchSize,
        windowOverscanBefore: galleryWindowOverscanBefore,
        windowOverscanAfter: galleryWindowOverscanAfter,
        jumpCoreOverscanBefore: galleryJumpCoreOverscanBefore,
        jumpCoreOverscanAfter: galleryJumpCoreOverscanAfter,
        slidingWindowEnabled: gallerySlidingWindowEnabled,
        slidingWindowMaxItems: gallerySlidingWindowMaxItems,
        thumbBuildWorkers: galleryThumbBuildWorkers,
        thumbHqWorkers: galleryThumbHqWorkers,
        thumbHqVisibleSequential: galleryThumbHqVisibleSequential,
        compactIndicesAfterMove: galleryCompactIndicesAfterMove,
      });
      setGalleryDebugLogEnabled(debugLogEnabled);
      setGalleryDebugFilters(debugLogFilters);
      appliedThumbScale = ts;
      settingsOpen = false;
      uiLoading = false;

      if (needsGalleryReload) {
        uiLoading = true;
        uiLoadingMessage = t("settings.applyingGallery");
        await reload({ silent: false, invalidateThumbCache: thumbConfigChanged });
        uiLoading = false;
      }
      status = needsGalleryReload ? t("settings.savedReloaded") : t("settings.savedInstant");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("settings.saveError");
    } finally {
      uiLoading = false;
    }
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
      secondaryLabel?: string;
      secondaryAction?: () => void | Promise<void>;
    }
  ) {
    confirmDeleteTitle = title;
    confirmDeleteDetail = detail;
    confirmDeleteConfirmLabel = opts?.confirmLabel ?? t("common.delete");
    confirmDeleteBypassEnabled = Boolean(opts?.bypassEnabled);
    confirmDeleteBypassLabel = opts?.bypassLabel ?? t("confirm.bypassOnce");
    confirmDeleteBypassChecked = false;
    confirmDeleteBypassSetter = opts?.bypassSetter ?? null;
    confirmDeleteSecondaryLabel = opts?.secondaryLabel ?? "";
    confirmDeleteSecondaryAction = opts?.secondaryAction ?? null;
    confirmDeleteAction = action;
    confirmDeleteOpen = true;
  }

  function closeConfirmDelete() {
    confirmDeleteOpen = false;
    confirmDeleteAction = null;
    confirmDeleteBypassEnabled = false;
    confirmDeleteBypassChecked = false;
    confirmDeleteBypassSetter = null;
    confirmDeleteSecondaryLabel = "";
    confirmDeleteSecondaryAction = null;
  }

  async function runConfirmSecondary() {
    if (!confirmDeleteSecondaryAction) return;
    const fn = confirmDeleteSecondaryAction;
    closeConfirmDelete();
    await fn();
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
    const selected = getGalleryItems().filter(
      (x) => isGallerySelectableKind(x.kind) && Boolean(x.selected)
    );
    if (selected.length === 0) return;
    const paths = selected.map((x) => x.path);
    const hasFolders = selected.some((x) => x.kind === "folder");

    if (hasFolders) {
      try {
        const out = await trackLoad(bridge.galleryDeletePaths(paths));
        setGalleryPayload(out.state, out.items ?? []);
        await afterGalleryDataLoaded();
        resetGalleryInteractionLocks();
        const deleted = Number(out.deleteResult?.deleted ?? 0);
        const errors = Number(out.deleteResult?.errors ?? 0);
        status = t("status.deleteBatchLine")
          .replace("{deleted}", String(deleted))
          .replace("{errPart}", errors ? t("status.deleteErrorsPart").replace("{errors}", String(errors)) : "")
          .replace("{queue}", "0");
      } catch (e: unknown) {
        status = e instanceof Error ? e.message : t("status.deleteQueueError");
      }
      return;
    }

    const snapshot = createGalleryMoveJobSnapshot(paths);
    await applyOptimisticGalleryRemove(snapshot);
    galleryDeleteQueue = [...galleryDeleteQueue, snapshot];
    status = t("status.deleteQueued").replace("{n}", String(paths.length));
    if (!galleryDeleteWorkerRunning) void processDeleteQueue();
  }

  async function deleteCurrentZoomImage() {
    if (!previewZoomPath) return;
    const curPath = previewZoomPath;
    const curIdx = zoomNavItems.findIndex((x) => x.path === curPath);
    const remainingNav = zoomNavItems.filter((x) => x.path !== curPath);
    const snapshot = createGalleryMoveJobSnapshot([curPath]);
    await applyOptimisticGalleryRemove(snapshot);
    if (remainingNav.length > 0) {
      const nextIdx = curIdx >= 0 ? Math.min(curIdx, remainingNav.length - 1) : 0;
      const nextItem = remainingNav[nextIdx];
      zoomNavItems = remainingNav;
      if (nextItem) openPreviewZoom(nextItem, { preserveCarousel: true, preserveMode: true, navItems: remainingNav });
    } else {
      previewZoomOpen = false;
    }
    galleryDeleteQueue = [...galleryDeleteQueue, snapshot];
    status = t("status.deleteImageQueued");
    if (!galleryDeleteWorkerRunning) void processDeleteQueue();
  }

  function rememberPreviewVideoUrl(url: string) {
    const u = String(url ?? "").trim();
    if (!u || previewVideoTriedUrls.includes(u)) return;
    previewVideoTriedUrls = [...previewVideoTriedUrls, u];
  }

  function previewVideoUrlKind(url: string): "direct" | "transcode" | "webm" | "unknown" {
    if (isDataPlaybackUrl(url)) return "webm";
    const key = mediaUrlKey(url);
    if (key.startsWith("/om-webm/") || key.includes("format=webm")) return "webm";
    if (key.startsWith("/om-transcode/") || key.includes("transcode=1")) return "transcode";
    const playback = previewVideoPlayback;
    if (!playback) return "unknown";
    if (url && sameMediaUrl(url, playback.transcodeUrl)) {
      return playback.playbackFormat === "webm" ? "webm" : "transcode";
    }
    if (url && sameMediaUrl(url, playback.fileUrl)) return "direct";
    return "unknown";
  }

  function previewVideoErrorSummary(code: number, detail = ""): string {
    if (isQtPlayerCreationError(detail)) return t("preview.videoDiagSummaryQtPlayer");
    if (code === 4) return t("preview.videoDiagSummaryCodec");
    if (code === 2) return t("preview.videoDiagSummaryNetwork");
    if (code === 3) return t("preview.videoDiagSummaryDecode");
    return t("preview.videoDiagSummaryGeneric");
  }

  async function collectPreviewVideoDiagnostics(el: HTMLVideoElement | null, code: number) {
    const path = String(selectedPreview?.path ?? "").trim();
    const videoUrl = String(previewVideoSrc || selectedPreview?.fileUrl || "").trim();
    if (!path || !videoUrl) return;

    previewVideoDiagLoading = true;
    previewVideoErrorDetails = t("preview.videoDiagLoading");
    try {
      const [httpProbe, backend] = await Promise.all([
        probeVideoHttpUrl(videoUrl),
        bridge
          .galleryVideoDiagnostics(path, true)
          .catch((err: unknown) => ({ apiError: err instanceof Error ? err.message : String(err) }) as VideoBackendDiagnostics),
      ]);
      previewVideoErrorDetails = formatVideoDiagnosticReport({
        mediaErrorCode: code,
        mediaErrorMessage: String(el?.error?.message ?? "").trim(),
        videoUrl,
        urlKind: previewVideoUrlKind(videoUrl),
        networkState: el?.networkState ?? 0,
        readyState: el?.readyState ?? 0,
        httpProbe,
        backend: backend as VideoBackendDiagnostics,
        triedUrls: previewVideoTriedUrls,
      });
    } catch (err) {
      previewVideoErrorDetails = `${t("preview.videoDiagApiError")}: ${err instanceof Error ? err.message : String(err)}`;
    } finally {
      previewVideoDiagLoading = false;
    }
  }

  async function tryBlobPreviewVideoUrl(): Promise<boolean> {
    const path = String(selectedPreview?.path ?? "").trim();
    if (!path || typeof window === "undefined" || !window.pywebview?.api) return false;
    const current = String(previewVideoSrc || selectedPreview?.fileUrl || "").trim();
    if (isDataPlaybackUrl(current)) return false;
    if (previewVideoTriedUrls.some((u) => isDataPlaybackUrl(u))) return false;
    try {
      const blob = await bridge.galleryVideoPlaybackBlob(path);
      if (!blob?.ok || !blob.dataUrl) return false;
      const dataUrl = String(blob.dataUrl);
      previewVideoSrc = dataUrl;
      rememberPreviewVideoUrl(dataUrl);
      if (previewVideoPlayback) {
        previewVideoPlayback = { ...previewVideoPlayback, transcodeUrl: dataUrl, playbackViaBlob: true };
      }
      selectedPreview = selectedPreview
        ? { ...selectedPreview, fileUrl: dataUrl, transcodeUrl: dataUrl }
        : selectedPreview;
      previewVideoPreparing = false;
      previewVideoError = "";
      previewVideoErrorDetails = "";
      return true;
    } catch {
      return false;
    }
  }

  function tryAlternatePreviewVideoUrl(): boolean {
    const playback = previewVideoPlayback;
    if (!playback) return false;
    const current = previewVideoSrc || selectedPreview?.fileUrl || "";
    rememberPreviewVideoUrl(current);

    // Con WebM obligatorio: no volver al MP4 directo (provoca bucle infinito en Qt).
    if (playback.needsTranscode) {
      if (
        playback.transcodeUrl &&
        !sameMediaUrl(current, playback.transcodeUrl) &&
        !previewVideoTriedUrls.some((u) => sameMediaUrl(u, playback.transcodeUrl))
      ) {
        previewVideoSrc = playback.transcodeUrl;
        rememberPreviewVideoUrl(playback.transcodeUrl);
        previewVideoPreparing = true;
        previewVideoError = "";
        previewVideoErrorDetails = "";
        return true;
      }
      return false;
    }

    for (const url of [playback.transcodeUrl, playback.fileUrl]) {
      if (!url) continue;
      if (sameMediaUrl(current, url)) continue;
      if (previewVideoTriedUrls.some((u) => sameMediaUrl(u, url))) continue;
      previewVideoSrc = url;
      rememberPreviewVideoUrl(url);
      previewVideoPreparing = sameMediaUrl(url, playback.transcodeUrl);
      previewVideoError = "";
      previewVideoErrorDetails = "";
      return true;
    }
    return false;
  }

  function resetPreviewVideoPlaybackUi(opts?: { keepPath?: boolean }) {
    previewVideoPlayLocked = false;
    previewVideoLaunching = false;
    previewVideoArmed = false;
    previewVideoPreparing = false;
    previewVideoSrc = "";
    if (!opts?.keepPath) previewVideoPreparePath = "";
    stopVideoPreparePoll();
  }

  $: editModeSelectedMedia = destinationsMode
    ? $galleryItems.filter((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected))
    : [];

  async function deselectGalleryPath(path: string) {
    const p = String(path ?? "").trim();
    if (!p) return;
    patchGallerySelection(
      (items) => items.map((x) => (x.path === p ? { ...x, selected: false } : x)),
      "selection:preview_strip_remove",
      { path: p },
    );
    try {
      await bridge.galleryApplySelectionDelta([], [p]);
    } catch {
      /* selección local ya aplicada */
    }
    if (selectedPreview?.path === p) {
      const remaining = getGalleryItems().filter((x) => isGalleryMediaKind(x.kind) && x.selected);
      setSelectedPreviewFromPath(remaining[0]?.path ?? null);
    }
  }

  function previewStripSelectPath(path: string) {
    galleryCursorPath = path;
    setSelectedPreviewFromPath(path);
  }

  function setSelectedPreviewFromPath(path: string | null | undefined) {
    const p = String(path ?? "").trim();
    if (!p) {
      selectedPreview = null;
      resetPreviewVideoPlaybackUi();
      return;
    }
    const row = getGalleryItems().find((x) => isGalleryMediaKind(x.kind) && x.path === p) as GalleryItem | undefined;
    if (!row) return;
    const isSameVideo =
      p === selectedPreview?.path &&
      selectedPreview?.mediaType === "video" &&
      row.kind === "video";
    if (isSameVideo && (previewVideoPlayLocked || previewVideoLaunching || previewVideoPreparing)) {
      return;
    }
    const isVideo = row.kind === "video";
    const isSvg = row.path.toLowerCase().endsWith(".svg");
    const fallbackUrl = isVideo ? null : buildMediaFileUrl(row.path);
    const thumbPlaceholder = row.thumbDataUrl ?? null;
    previewLoadGeneration += 1;
    const loadGeneration = previewLoadGeneration;
    previewVideoSession += 1;
    resetPreviewVideoPlaybackUi();
    selectedPreview = {
      path: row.path,
      name: row.name,
      dataUrl: null,
      placeholderUrl: thumbPlaceholder,
      mediaType: isVideo ? "video" : isSvg ? "svg" : "image",
      fileUrl: isVideo ? null : fallbackUrl,
    };
    previewVideoError = "";
    previewVideoErrorDetails = "";
    previewVideoLastErrorDetail = "";
    previewVideoTriedUrls = [];
    previewVideoSrc = isVideo ? "" : fallbackUrl ?? "";
    previewVideoPlayback = null;
    previewVideoDiagLoading = false;
    if (isVideo) {
      previewVideoMode = "auto";
      previewVideoProfiles = [];
      void loadPreviewVideoProfiles(row.path);
    }
    if (isSvg) {
      void resolveMediaPlaybackInfo(row.path)
        .then((info) => {
          if (loadGeneration !== previewLoadGeneration || !selectedPreview || selectedPreview.path !== row.path) return;
          previewVideoPlayback = info;
          const url = pickInitialPlaybackUrl(info);
          if (!url) return;
          if (!sameMediaUrl(previewVideoSrc, url)) previewVideoSrc = url;
          rememberPreviewVideoUrl(url);
          selectedPreview = {
            ...selectedPreview,
            fileUrl: url,
            mediaType: "svg",
          };
        })
        .catch(() => {
          if (loadGeneration !== previewLoadGeneration || !selectedPreview || selectedPreview.path !== row.path || !fallbackUrl) return;
          previewVideoSrc = fallbackUrl;
          selectedPreview = { ...selectedPreview, fileUrl: fallbackUrl };
        });
    }
    if (!isVideo) {
      requestAnimationFrame(() => {
        bridge
          .galleryPreview(row.path, 1200, 900)
          .then((pr) => {
            if (loadGeneration !== previewLoadGeneration || selectedPreview?.path !== row.path) return;
            selectedPreview = mergePreviewApiResult(selectedPreview ?? {}, pr, row.path, row.kind);
          })
          .catch(() => undefined);
      });
    }
    if (isVideo && isPreviewVideoAutoplayEnabled()) {
      requestPreviewVideoPlay();
    }
  }

  function transcodeJobStatusLabel(job: (typeof videoTranscodeJobs)[number]): string {
    const pct =
      job.status === "running" && job.progress && job.progress !== "100" ? ` · ${job.progress}%` : "";
    const queued = job.status === "queued" ? ` (${t("pager.processQueued")})` : "";
    const base =
      job.format === "remux" ? t("pager.processVideoRemux") : t("pager.processVideoTranscode");
    return `${base}${queued}${pct}`;
  }

  function stopVideoPreparePoll() {
    if (videoPreparePollTimer !== null) {
      window.clearInterval(videoPreparePollTimer);
      videoPreparePollTimer = null;
    }
  }

  function startVideoPreparePoll() {
    stopVideoPreparePoll();
    void pollVideoTranscodeJobs();
    videoPreparePollTimer = window.setInterval(() => {
      void pollVideoTranscodeJobs();
    }, 450);
  }

  async function loadPreviewVideoProfiles(path: string) {
    try {
      const out = await bridge.galleryVideoProfiles(normalizePathForApi(path));
      if (selectedPreview?.path !== path) return;
      previewVideoProfiles = out?.profiles ?? [];
    } catch {
      previewVideoProfiles = [];
    }
  }

  function isPreviewVideoAutoplayEnabled(): boolean {
    return destinationsMode ? previewVideoAutoplayEdit : previewVideoAutoplay;
  }

  /** Reactivo: el template no invalida bien llamadas a funciones locales. */
  $: previewVideoAutoplayOn =
    destinationsMode ? previewVideoAutoplayEdit : previewVideoAutoplay;

  function maybeAutoplayPreviewVideo(el: HTMLVideoElement | null | undefined) {
    if (!isPreviewVideoAutoplayEnabled()) return;
    tryAutoplayVideo(el);
  }

  async function togglePreviewVideoAutoplay() {
    if (destinationsMode) {
      previewVideoAutoplayEdit = !previewVideoAutoplayEdit;
      await bridge.settingsPatch({ preview_video_autoplay_edit: previewVideoAutoplayEdit });
    } else {
      previewVideoAutoplay = !previewVideoAutoplay;
      await bridge.settingsPatch({ preview_video_autoplay: previewVideoAutoplay });
    }
  }

  async function setPreviewVideoMode(mode: string) {
    const next = (mode || "auto") as VideoPlaybackMode;
    if (next === previewVideoMode) return;
    previewVideoMode = next;
    const path = String(selectedPreview?.path ?? "").trim();
    if (!path || selectedPreview?.mediaType !== "video") return;
    resetPreviewVideoPlaybackUi({ keepPath: true });
    requestPreviewVideoPlay();
  }

  function requestPreviewVideoPlay() {
    const path = String(selectedPreview?.path ?? "").trim();
    if (!path || selectedPreview?.mediaType !== "video") return;
    if (previewVideoPlayLocked && previewVideoPreparePath === path) return;
    if (previewVideoArmed && previewVideoSrc && previewVideoPreparePath === path && !previewVideoError) return;

    previewVideoPlayLocked = true;
    previewVideoPreparePath = path;
    previewVideoLaunching = true;
    previewVideoArmed = true;
    previewVideoPreparing = true;
    previewVideoPrepareMsg = t("preview.videoStarting");
    previewVideoError = "";
    previewVideoErrorDetails = "";
    previewVideoSrc = "";

    void runPreviewVideoPlayback(path);
  }

  async function runPreviewVideoPlayback(pathAtStart: string) {
    try {
      const info = await resolveMediaPlaybackInfo(pathAtStart, {
        warm: true,
        tryBlob: false,
        playbackMode: previewVideoMode,
      });
      if (selectedPreview?.path !== pathAtStart) {
        previewVideoPlayLocked = false;
        return;
      }

      previewVideoPrepareMsg = playbackPrepareMessage(info);
      previewVideoPlayback = info;

      if (!canTranscodeVideo(info)) {
        resetPreviewVideoPlaybackUi({ keepPath: true });
        previewVideoError = t("preview.videoFfmpegMissing");
        void collectPreviewVideoDiagnostics(null, 4);
        return;
      }

      const url = pickInitialPlaybackUrl(info);
      if (!url) {
        resetPreviewVideoPlaybackUi({ keepPath: true });
        previewVideoError = t("preview.videoPlaybackError");
        return;
      }

      previewVideoLaunching = false;
      previewVideoSrc = url;
      rememberPreviewVideoUrl(url);
      previewVideoPreparing = Boolean(info.needsTranscode && !info.transcodeCached);
      selectedPreview = { ...selectedPreview, fileUrl: url };

      void pollVideoTranscodeJobs();
      if (previewVideoPreparing) startVideoPreparePoll();
      else {
        stopVideoPreparePoll();
        previewVideoPlayLocked = false;
      }
      void tick().then(() => maybeAutoplayPreviewVideo(previewVideoEl));
    } catch {
      if (selectedPreview?.path !== pathAtStart) return;
      resetPreviewVideoPlaybackUi({ keepPath: true });
      previewVideoError = t("preview.videoPlaybackError");
    }
  }

  function isActiveTranscodeJob(job: (typeof videoTranscodeJobs)[number]): boolean {
    const st = String(job.status ?? "running").toLowerCase();
    return st === "queued" || st === "running";
  }

  async function pollVideoTranscodeJobs() {
    try {
      const out = await bridge.galleryTranscodeActive();
      const jobs = (out?.jobs ?? []).filter(isActiveTranscodeJob);
      videoTranscodeJobs = jobs;
      if (jobs.length === 0) stopVideoPreparePoll();
    } catch {
      videoTranscodeJobs = [];
      stopVideoPreparePoll();
    }
  }

  function buildPreviewVideoErrorCopyText(): string {
    const lines: string[] = [];
    if (previewVideoError) lines.push(previewVideoError);
    if (previewVideoLastErrorDetail) lines.push(previewVideoLastErrorDetail);
    if (previewVideoErrorDetails) {
      if (lines.length) lines.push("");
      lines.push(previewVideoErrorDetails);
    }
    const path = String(selectedPreview?.path ?? "").trim();
    if (path) {
      if (lines.length) lines.push("");
      lines.push(`${t("preview.videoDiagFileSection")}\n${path}`);
    }
    return lines.join("\n").trim();
  }

  async function copyPreviewVideoError() {
    const text = buildPreviewVideoErrorCopyText();
    if (!text) return;
    const ok = await copyTextToClipboard(text);
    status = ok ? t("preview.videoCopyErrorOk") : t("preview.videoCopyErrorFail");
  }

  async function onPreviewVideoError(e: Event) {
    const el = e.currentTarget as HTMLVideoElement | null;
    const code = el?.error?.code ?? 0;
    previewVideoLastErrorDetail = String(el?.error?.message ?? "").trim();
    rememberPreviewVideoUrl(previewVideoSrc || selectedPreview?.fileUrl || "");
    if ((code === 4 || code === 3) && tryAlternatePreviewVideoUrl()) return;
    if ((code === 4 || code === 3 || code === 2) && (await tryBlobPreviewVideoUrl())) return;
    previewVideoPreparing = false;
    previewVideoPlayLocked = false;
    previewVideoError = previewVideoErrorSummary(code, String(el?.error?.message ?? ""));
    previewVideoErrorDetails = "";
    status = `${previewVideoError} · ${mediaErrorLabel(code)}`;
    void collectPreviewVideoDiagnostics(el, code);
  }

  function onPreviewVideoCanPlay() {
    previewVideoPreparing = false;
    previewVideoPlayLocked = false;
    previewVideoLaunching = false;
    previewVideoError = "";
    previewVideoErrorDetails = "";
    previewVideoLastErrorDetail = "";
    previewVideoDiagLoading = false;
    stopVideoPreparePoll();
    maybeAutoplayPreviewVideo(previewVideoEl);
  }

  function onPreviewVideoLoadStart() {
    const playback = previewVideoPlayback;
    const current = previewVideoSrc || selectedPreview?.fileUrl || "";
    if (playback?.needsTranscode && playback.transcodeUrl && sameMediaUrl(current, playback.transcodeUrl)) {
      previewVideoPreparing = !playback.playbackViaBlob && !isDataPlaybackUrl(current);
    }
  }

  async function openGalleryVideoExternal(path?: string) {
    const p = String(path ?? selectedPreview?.path ?? "").trim();
    if (!p) return;
    try {
      const res = await bridge.galleryOpenExternal(p);
      if (res?.ok) {
        status = t("preview.videoOpenExternalOk");
        previewVideoError = "";
      } else {
        status = String(res?.error ?? t("preview.videoOpenExternalError"));
      }
    } catch {
      status = t("preview.videoOpenExternalError");
    }
  }

  async function openGalleryExternalFromCtx() {
    if (!galleryItemCtxMenu) return;
    const p = galleryItemCtxMenu.path;
    closeGalleryItemCtxMenu();
    await openGalleryVideoExternal(p);
  }

  function getGalleryNavigablePaths(): string[] {
    return getGalleryItems().filter((x) => isGalleryMediaKind(x.kind)).map((x) => x.path);
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
        const it = getGalleryItems().find((x) => x.path === path);
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

  function toggleGalleryCursorSelection(path: string) {
    const it = getGalleryItems().find((x) => x.path === path);
    if (!it) return;

    const nextSelected = !it.selected;
    patchGallerySelection(
      (items) => items.map((x) => (x.path === path ? { ...x, selected: nextSelected } : x)),
      "selection:ctrl_toggle",
      { path, selected: nextSelected },
    );
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
    
    patchGallerySelection(
      (items) =>
        items.map((it) => {
          if (!isGalleryMediaKind(it.kind)) return it;
          const isTarget = target.has(it.path);
          return { ...it, selected: isTarget ? true : it.selected };
        }),
      "selection:keyboard_range",
      { from: anchorPath, to: toPath, count: target.size },
    );
  };

  const clearSelection = async () => {
    patchGallerySelection(
      (items) => items.map((x) => (isGallerySelectableKind(x.kind) ? { ...x, selected: false } : x)),
      "selection:clear",
    );
    setGalleryState({ ...getGalleryState(), selectedCount: 0 });
    try {
      await bridge.galleryClearSelection();
    } catch {
      /* local ya limpio */
    }
  };
  const invertSelection = async () => {
    patchGallerySelection(
      (items) => items.map((x) => (isGalleryMediaKind(x.kind) ? { ...x, selected: !x.selected } : x)),
      "selection:invert",
    );
    if (destinationsMode) {
      const last = [...getGalleryItems()].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
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
          const out = job.newFolderName
            ? await bridge.destinationMovePathsNewFolder(job.srcPaths, job.destPath, job.newFolderName)
            : await bridge.destinationMovePaths(job.srcPaths, job.destPath);
          if (!isGalleryNavigationCurrent(job.navGen)) continue;
          const moved = Number(out.moveResult?.moved ?? 0);
          const errors = Number(out.moveResult?.errors ?? 0);
          if (errors > 0 || moved < job.srcPaths.length) {
            await applyGalleryItemsDelta(out);
          } else {
            await reconcileGalleryMoveSuccess(out);
          }
          status = t("status.moveBatchLine")
            .replace("{moved}", String(out.moveResult?.moved ?? 0))
            .replace("{errors}", String(out.moveResult?.errors ?? 0))
            .replace("{queue}", String(galleryMoveQueue.length));
        } catch (e: unknown) {
          if (!isGalleryNavigationCurrent(job.navGen)) continue;
          await rollbackOptimisticGalleryMove(job);
          status = e instanceof Error ? e.message : t("status.moveQueueError");
        }
      }
    } finally {
      galleryMoveWorkerRunning = false;
    }
  }

  function getSelectedGalleryPaths(): string[] {
    return getGalleryItems().filter((x) => isGallerySelectableKind(x.kind) && x.selected).map((x) => x.path);
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
      {
        confirmLabel: t("common.move"),
        secondaryLabel: t("confirm.moveAsFolder"),
        secondaryAction: () => openMoveAsFolderModal(destPath),
      }
    );
  }

  let moveAsFolderModalOpen = false;
  let moveAsFolderDestPath = "";
  let moveAsFolderDraft = "";

  function openMoveAsFolderModal(parentPath: string) {
    moveAsFolderDestPath = parentPath;
    moveAsFolderDraft = "";
    moveAsFolderModalOpen = true;
  }

  function askGroupSelectionInFolder() {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    if (!folder.trim()) {
      status = t("status.loadFolderForDrop");
      return;
    }
    openMoveAsFolderModal(folder);
  }

  function closeMoveAsFolderModal() {
    moveAsFolderModalOpen = false;
    moveAsFolderDestPath = "";
    moveAsFolderDraft = "";
  }

  async function confirmMoveAsFolder() {
    const name = moveAsFolderDraft.trim();
    if (!isValidFolderName(name)) {
      status = t("confirm.moveAsFolderInvalidName");
      return;
    }
    const parent = moveAsFolderDestPath;
    closeMoveAsFolderModal();
    await moveSelectionToNewFolder(parent, name);
  }

  function sectionFolderMoveLabel(folderPath: string): string {
    const fp = normalizePathForApi(folderPath);
    const parts = fp.split("/").filter(Boolean);
    return parts[parts.length - 1] || fp;
  }

  function formatSectionMoveConfirmLabel(sectionLabel: string, folderPath: string): string {
    const rel = String(sectionLabel ?? "").trim();
    if (rel && rel !== "(esta carpeta)") return rel;
    return sectionFolderMoveLabel(folderPath);
  }

  function askConfirmMoveSectionFolder(folderPath: string, destPath: string, sectionLabel = "") {
    const fp = normalizePathForApi(folderPath);
    if (!fp) return;
    openConfirmDelete(
      t("confirm.moveFolderTitle"),
      t("confirm.moveFolderDetail").replace("{folder}", formatSectionMoveConfirmLabel(sectionLabel, fp)),
      async () => {
        await moveSectionFolderToDest(fp, destPath);
      },
      { confirmLabel: t("common.move") }
    );
  }

  async function moveSectionFolderToDest(folderPath: string, destPath: string) {
    try {
      const navGen = beginGalleryRefresh(true);
      const out = await trackLoad(bridge.destinationMoveFolder(folderPath, destPath));
      if (!isGalleryNavigationCurrent(navGen)) return;
      const moved = Number(out.moveResult?.moved ?? 0);
      if (moved > 0 && out.state) {
        clearMasonryHeightCache();
        setGalleryPayload(out.state, out.items ?? []);
        await afterGalleryDataLoaded();
        status = t("status.moveFolderOk");
        return;
      }
      applyGalleryMutationResponse(out);
      status = t("status.moveFolderError");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.moveFolderError");
    }
  }

  const moveToDest = async (path: string) => {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    const snapshot = createGalleryMoveJobSnapshot(selectedPaths);
    await applyOptimisticGalleryRemove(snapshot);
    const job: GalleryMoveJob = { ...snapshot, destPath: path };
    galleryMoveQueue = [...galleryMoveQueue, job];
    status = t("status.imagesMoving")
      .replace("{n}", String(selectedPaths.length))
      .replace("{queue}", String(galleryMoveQueue.length));
    if (!galleryMoveWorkerRunning) {
      void processGalleryMoveQueue();
    }
  };

  const moveSelectionToNewFolder = async (parentPath: string, folderName: string) => {
    const selectedPaths = getSelectedGalleryPaths();
    if (selectedPaths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    const snapshot = createGalleryMoveJobSnapshot(selectedPaths);
    await applyOptimisticGalleryRemove(snapshot);
    const job: GalleryMoveJob = { ...snapshot, destPath: parentPath, newFolderName: folderName };
    galleryMoveQueue = [...galleryMoveQueue, job];
    status = t("status.imagesMoving")
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

  $: gridCellTargetPx = galleryGridCellPx(thumbScale);
  $: gridCellPx = Math.max(72, Number(gridCellTargetPx.toFixed(2)));

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
    const prevScale = appliedThumbScale;
    const nextScale = thumbScale;
    try {
      await bridge.settingsPatch({ gallery_thumb_scale: Number(nextScale.toFixed(3)) });
      appliedThumbScale = nextScale;
      if (thumbQualityRefreshNeeded(prevScale, nextScale)) {
        invalidateGalleryThumbHqForScale(nextScale);
        await reload({ silent: true, invalidateThumbCache: true });
        return;
      }
      if (invalidateGalleryThumbHqForScale(nextScale)) {
        await galleryWorkspace?.refreshThumbsAtScale(nextScale);
      }
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
    await trackLoad(bridge.markersAdd(path, label, parentIdOrEmpty(markerToolbarFolderId)));
    await syncMarkersFromApi();
    pinMarkerOpen = false;
    status = t("pinMarker.saved");
  }

  async function toggleDestinationsModePreserveScroll() {
    const fromDest = destinationsMode;
    const currentScrollTop = Number(galleryScrollEl?.scrollTop ?? 0);
    destinationsMode = !fromDest;
    if (fromDest) {
      await clearSelection();
    }
    await tick();
    const apply = () => {
      if (galleryScrollEl) {
        galleryScrollEl.scrollTop = currentScrollTop;
        galleryScrollAtTop = galleryScrollEl.scrollTop <= 2; // solo para restaurar scroll al cambiar modo
      }
    };
    apply();
    requestAnimationFrame(apply);
  }

  const openDestPreview = (path: string) => {
    previewDestPath = path;
    previewOpen = true;
  };

  $: {
    const _route = folder;
    void _route;
    keepRoutePathEndVisible();
  }

  async function movePreviewPathsToCurrentRoute(paths: string[]) {
    if (paths.length === 0) {
      status = t("status.selectModalFirst");
      return;
    }
    if (!folder.trim()) {
      status = t("status.loadFolderForDrop");
      return;
    }
    destPreviewModal?.removePaths(paths);
    destPreviewModal?.clearSelectedPaths();
    try {
      const out = await trackLoad(bridge.destinationMoveFromPreview(paths));
      setGalleryState(out.state ?? getGalleryState());
      mergeGalleryItemsFromApi(out.items ?? getGalleryItems(), out.state, { preserveSelection: true });
      void afterGalleryDataLoaded();
      const moved = Number(out.moveResult?.moved ?? 0);
      const errors = Number(out.moveResult?.errors ?? 0);
      status =
        t("status.previewMoved").replace("{moved}", String(moved)) +
        (errors ? t("status.previewMovedErrors").replace("{errors}", String(errors)) : "");
      if (errors > 0 || moved < paths.length) destPreviewModal?.reloadPreview();
    } catch (e: unknown) {
      destPreviewModal?.reloadPreview();
      status = e instanceof Error ? e.message : t("status.previewMoveError");
    }
  }

  async function deleteDestPreviewPaths(paths: string[]) {
    if (paths.length === 0) return;
    destPreviewModal?.removePaths(paths);
    destPreviewModal?.clearSelectedPaths();
    const snapshot = createGalleryMoveJobSnapshot(paths);
    await applyOptimisticGalleryRemove(snapshot);
    galleryDeleteQueue = [...galleryDeleteQueue, snapshot];
    status = t("status.deleteQueued").replace("{n}", String(paths.length));
    if (!galleryDeleteWorkerRunning) void processDeleteQueue();
  }

  async function deletePreviewSelectedItems() {
    const paths = destPreviewModal?.getSelectedPaths() ?? [];
    await deleteDestPreviewPaths(paths);
  }

  function enqueueDeletePaths(paths: string[]) {
    const normalized = (paths || []).map((x) => String(x).trim()).filter((x) => x.length > 0);
    if (normalized.length === 0) return;
    void (async () => {
      const snapshot = createGalleryMoveJobSnapshot(normalized);
      await applyOptimisticGalleryRemove(snapshot);
      galleryDeleteQueue = [...galleryDeleteQueue, snapshot];
      if (!galleryDeleteWorkerRunning) void processDeleteQueue();
    })();
  }

  async function processDeleteQueue() {
    if (galleryDeleteWorkerRunning) return;
    galleryDeleteWorkerRunning = true;
    try {
      while (galleryDeleteQueue.length > 0) {
        const [job, ...rest] = galleryDeleteQueue;
        galleryDeleteQueue = rest;
        try {
          const out = await bridge.galleryDeletePaths(job.srcPaths);
          if (!isGalleryNavigationCurrent(job.navGen)) continue;
          const deleted = Number(out.deleteResult?.deleted ?? 0);
          const errors = Number(out.deleteResult?.errors ?? 0);
          if (errors > 0 || deleted < job.srcPaths.length) {
            await applyGalleryItemsDelta(out);
          } else {
            await reconcileGalleryMoveSuccess(out);
          }
          resetGalleryInteractionLocks();
          status = t("status.deleteBatchLine")
            .replace("{deleted}", String(deleted))
            .replace("{errPart}", errors ? t("status.deleteErrorsPart").replace("{errors}", String(errors)) : "")
            .replace("{queue}", String(galleryDeleteQueue.length));
        } catch (e: unknown) {
          if (!isGalleryNavigationCurrent(job.navGen)) continue;
          await rollbackOptimisticGalleryMutation(job);
          if (previewOpen) destPreviewModal?.reloadPreview();
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
    previewZoomMiniSrc = it.thumbDataUrl ?? null;
    previewZoomMediaType =
      it.kind === "video" ? "video" : it.path.toLowerCase().endsWith(".svg") ? "svg" : "image";
    previewZoomThumbUrl = it.thumbDataUrl ?? null;
    previewZoomVideoArmed = false;
    previewZoomVideoLaunching = false;
    previewZoomVideoPlayLocked = false;
    previewZoomVideoPreparing = false;
    previewZoomVideoSession += 1;
    const zoomFallbackUrl = buildMediaFileUrl(it.path);
    previewZoomFileUrl = previewZoomMediaType === "svg" ? zoomFallbackUrl : null;
    previewZoomPlayback = null;
    if (previewZoomMediaType === "svg") {
      void resolveMediaPlaybackInfo(it.path)
        .then((info) => {
          if (previewZoomOpen && previewZoomPath === it.path) {
            previewZoomPlayback = info;
            const url = pickInitialPlaybackUrl(info);
            if (url) previewZoomFileUrl = url;
          }
        })
        .catch(() => {
          if (previewZoomOpen && previewZoomPath === it.path && zoomFallbackUrl) {
            previewZoomFileUrl = zoomFallbackUrl;
          }
        });
    }
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
    void hydrateZoomCarouselThumbs(zoomNavItems, thumbScale, it.path, (path, thumbDataUrl) => {
      zoomNavItems = zoomNavItems.map((z) =>
        z.path === path ? { ...z, thumbDataUrl, thumbQuality: "hq" as const } : z
      );
    });
    if (previewZoomMediaType !== "video") {
      bridge
        .galleryPreview(it.path, 2200, 1600)
        .then((pr) => {
          if (previewZoomOpen && previewZoomPath === it.path) {
            const merged = mergePreviewApiResult(
              {
                path: it.path,
                name: it.name,
                mediaType: previewZoomMediaType,
                fileUrl: previewZoomFileUrl,
                dataUrl: previewZoomDataUrl,
              },
              pr,
              it.path,
              it.kind
            );
            previewZoomMediaType = merged.mediaType ?? previewZoomMediaType;
            const nextUrl = merged.fileUrl ?? previewZoomFileUrl;
            if (nextUrl) {
              if (!isDataPlaybackUrl(previewZoomFileUrl) || isDataPlaybackUrl(nextUrl)) {
                previewZoomFileUrl = nextUrl;
              }
            }
            previewZoomDataUrl = merged.dataUrl ?? previewZoomDataUrl;
            if (merged.dataUrl) previewZoomMiniSrc = merged.dataUrl;
          }
        })
        .catch(() => undefined);
    }
    scheduleNextZoomVideoWarm(zoomNavItems, it.path);
    if (previewZoomMediaType === "video" && !destinationsMode && !previewZoomDestMode) {
      requestZoomVideoPlay();
    }
  }

  function requestZoomVideoPlay() {
    const path = String(previewZoomPath ?? "").trim();
    if (!path || previewZoomMediaType !== "video" || !previewZoomOpen) return;
    if (previewZoomVideoPlayLocked && previewZoomPath === path) return;
    if (previewZoomVideoArmed && previewZoomFileUrl) return;

    previewZoomVideoPlayLocked = true;
    previewZoomVideoLaunching = true;
    previewZoomVideoArmed = true;
    previewZoomVideoPreparing = true;
    previewZoomVideoStatus = t("preview.videoStarting");
    previewZoomFileUrl = null;

    void runZoomVideoPlayback(path, previewZoomVideoSession);
  }

  async function runZoomVideoPlayback(pathAtStart: string, sessionAtStart: number) {
    const isZoomVideoActive = () =>
      previewZoomOpen &&
      previewZoomPath === pathAtStart &&
      previewZoomVideoSession === sessionAtStart;

    try {
      const info = await resolveMediaPlaybackInfo(pathAtStart, { warm: true, tryBlob: false });
      if (!isZoomVideoActive()) return;

      if (!canTranscodeVideo(info)) {
        previewZoomVideoPlayLocked = false;
        previewZoomVideoLaunching = false;
        previewZoomVideoArmed = false;
        previewZoomVideoPreparing = false;
        status = t("preview.videoFfmpegMissing");
        return;
      }

      previewZoomPlayback = info;
      previewZoomVideoLaunching = false;
      const needsTranscodeWait = Boolean(info.needsTranscode && !info.transcodeCached);

      if (needsTranscodeWait) {
        previewZoomVideoPreparing = true;
        previewZoomFileUrl = null;
        void pollVideoTranscodeJobs();
        startVideoPreparePoll();

        const ready = await waitForTranscodeCache(
          pathAtStart,
          () => !isZoomVideoActive()
        );
        if (!isZoomVideoActive()) return;
        if (!ready) {
          stopVideoPreparePoll();
          previewZoomVideoPlayLocked = false;
          previewZoomVideoLaunching = false;
          previewZoomVideoArmed = false;
          previewZoomVideoPreparing = false;
          status = t("preview.videoTranscodeTimeout");
          return;
        }
        stopVideoPreparePoll();
        void pollVideoTranscodeJobs();
      }

      const url = pickInitialPlaybackUrl(info);
      if (!url) {
        previewZoomVideoPlayLocked = false;
        previewZoomVideoLaunching = false;
        previewZoomVideoArmed = false;
        previewZoomVideoPreparing = false;
        return;
      }

      previewZoomFileUrl = url;
      if (!needsTranscodeWait) {
        previewZoomVideoPreparing = false;
        previewZoomVideoPlayLocked = false;
      }
      void tick().then(() => {
        if (!isZoomVideoActive()) return;
        tryAutoplayVideo(zoomVideoEl);
      });
    } catch {
      if (!isZoomVideoActive()) return;
      previewZoomVideoPlayLocked = false;
      previewZoomVideoLaunching = false;
      previewZoomVideoArmed = false;
      previewZoomFileUrl = null;
      previewZoomVideoPreparing = false;
    }
  }

  function onZoomVideoCanPlay() {
    previewZoomVideoPreparing = false;
    previewZoomVideoPlayLocked = false;
    previewZoomVideoLaunching = false;
    stopVideoPreparePoll();
    tryAutoplayVideo(zoomVideoEl);
  }

  function applyGalleryRefreshFromMove(out: GalleryMutationResponse) {
    void applyGalleryItemsDelta(out);
  }

  function getZoomStageSize(): { w: number; h: number } | null {
    if (!zoomStageEl) return null;
    const sr = zoomStageEl.getBoundingClientRect();
    return { w: Math.max(1, sr.width), h: Math.max(1, sr.height) };
  }

  function getFillWidthPanLimitY(): number {
    const stage = getZoomStageSize();
    const nw = Math.max(1, previewZoomNaturalW);
    const nh = Math.max(1, previewZoomNaturalH);
    if (!stage) return 0;
    const layoutH = stage.w * (nh / nw);
    const scaledH = layoutH * previewZoomScale;
    return Math.max(0, scaledH - stage.h);
  }

  function getFitPanLimits(): { x: number; y: number } {
    const stage = getZoomStageSize();
    if (!stage) return { x: 0, y: 0 };
    const nw = Math.max(1, previewZoomNaturalW);
    const nh = Math.max(1, previewZoomNaturalH);
    let layoutW = stage.w;
    let layoutH = (stage.w * nh) / nw;
    if (layoutH > stage.h) {
      layoutH = stage.h;
      layoutW = (stage.h * nw) / nh;
    }
    const scaledW = layoutW * previewZoomScale;
    const scaledH = layoutH * previewZoomScale;
    return {
      x: Math.max(0, (scaledW - stage.w) / 2),
      y: Math.max(0, (scaledH - stage.h) / 2),
    };
  }

  function buildZoomImgTransform(): string {
    if (previewZoomMode === "fit" && Math.round(previewZoomScale * 100) === 100) {
      return "translate(-50%, -50%)";
    }
    if (previewZoomMode === "fillWidth") {
      return `translate(-50%, 0%) translate(0px, ${previewPanY}px) scale(${previewZoomScale})`;
    }
    return `translate(-50%, -50%) translate(${previewPanX}px, ${previewPanY}px) scale(${previewZoomScale})`;
  }

  /** Aplica transform directo al DOM durante pan (evita re-render de Svelte por frame). */
  function syncZoomMediaTransform() {
    const tf = buildZoomImgTransform();
    if (zoomImgEl) zoomImgEl.style.transform = tf;
    if (zoomVideoEl && previewZoomMediaType === "video") {
      if (previewZoomMode === "fit" && previewZoomScale === 1 && previewPanX === 0 && previewPanY === 0) {
        zoomVideoEl.style.transform = "translate(-50%, -50%)";
      } else {
        zoomVideoEl.style.transform = tf;
      }
    }
  }

  function zoomStep(delta: number) {
    if (previewZoomMediaType === "video") return;
    previewZoomScale = Math.min(4, Math.max(0.5, Number((previewZoomScale + delta).toFixed(2))));
    clampPanToStage();
    syncZoomMediaTransform();
    touchZoomHud();
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }

  function getPanLimits() {
    if (previewZoomMode === "fillWidth") {
      return { x: 0, y: getFillWidthPanLimitY() };
    }
    return getFitPanLimits();
  }

  function clampPanToStage() {
    const limits = getPanLimits();
    const nextX = previewZoomMode === "fillWidth" ? 0 : clamp(previewPanX, -limits.x, limits.x);
    // fillWidth: 0 = borde superior; negativo = desplazar hacia arriba para ver la parte inferior.
    const nextY =
      previewZoomMode === "fillWidth" ? clamp(previewPanY, -limits.y, 0) : clamp(previewPanY, -limits.y, limits.y);
    if (nextX !== previewPanX) previewPanX = nextX;
    if (nextY !== previewPanY) previewPanY = nextY;
  }

  function alignFillWidthToTop() {
    if (previewZoomMode !== "fillWidth") return;
    previewPanX = 0;
    previewPanY = 0;
    previewFillWidthAlignPending = false;
    syncZoomMediaTransform();
  }

  function togglePreviewZoomMode() {
    const next: "fit" | "fillWidth" = previewZoomMode === "fit" ? "fillWidth" : "fit";
    previewZoomMode = next;
    previewPanX = 0;
    previewPanY = 0;
    previewZoomScale = 1;
    previewFillWidthAlignPending = next === "fillWidth";
    clampPanToStage();
    syncZoomMediaTransform();
    touchZoomHud();
  }

  // Snap a "100%" usando el mismo redondeo que muestra la UI.
  // Así garantizamos que al ver "100%" el `pan` no quede desfasado y no haya recorte.
  $: if (previewZoomMode === "fit" && Math.round(previewZoomScale * 100) === 100) {
    previewZoomScale = 1;
    previewPanX = 0;
    previewPanY = 0;
  }

  // Siempre mantenemos pan dentro de los límites reales del DOM (overflow vs stage).
  $: if (previewZoomOpen && !previewPanDrag && zoomStageEl && zoomImgEl) {
    clampPanToStage();
    if (previewFillWidthAlignPending) {
      alignFillWidthToTop();
    }
  }

  $: zoomImgTransform = buildZoomImgTransform();

  // Aplica transform al DOM cuando cambia escala/pan (excepto durante drag activo).
  $: if (previewZoomOpen && !previewPanDrag && zoomImgEl) {
    syncZoomMediaTransform();
  }

  // Vídeo en modo fit: sin transform reactivo (evita parpadeos con controles nativos).
  $: if (
    previewZoomOpen &&
    !previewPanDrag &&
    zoomVideoEl &&
    previewZoomMediaType === "video" &&
    previewZoomMode === "fillWidth"
  ) {
    clampPanToStage();
    syncZoomMediaTransform();
  }

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
      setGalleryState(out.state);
      setGalleryItems(out.items);
      void afterGalleryDataLoaded();
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
      setGalleryState(out.state);
      setGalleryItems(out.items);
      void afterGalleryDataLoaded();
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
    const el = e.target as HTMLElement;
    if (el.closest("button, a, video, .zoom-modal__dest-bar, .zoom-mini")) return;
    // Si la imagen no desborda el stage, no hay nada que “panear”.
    const limits = getPanLimits();
    if (limits.x <= 0.5 && limits.y <= 0.5) return;
    previewPanPointerDown = true;
    previewPanDrag = false;
    previewPanMoved = false;
    previewPanDownX = e.clientX;
    previewPanDownY = e.clientY;
    if (previewZoomMode === "fillWidth") {
      previewPanStartY = e.clientY - previewPanY;
    } else {
      previewPanStartX = e.clientX - previewPanX;
      previewPanStartY = e.clientY - previewPanY;
    }
  }

  function movePan(e: PointerEvent) {
    if (!previewPanPointerDown) return;
    if (!previewPanDrag) {
      const dx = e.clientX - previewPanDownX;
      const dy = e.clientY - previewPanDownY;
      if (Math.hypot(dx, dy) < PAN_DRAG_THRESHOLD_PX) return;
      previewPanDrag = true;
      zoomStageEl?.setPointerCapture?.(e.pointerId);
    }
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
    syncZoomMediaTransform();
  }

  function endPan(e: PointerEvent) {
    const wasDragging = previewPanDrag;
    previewPanPointerDown = false;
    previewPanDrag = false;
    if (wasDragging) {
      (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
    }
    syncZoomMediaTransform();
    touchZoomHud();
  }

  function toggleZoomCarousel() {
    previewZoomCarouselVisible = !previewZoomCarouselVisible;
  }

  function onZoomImageClick(e: MouseEvent) {
    e.stopPropagation();
    if (zoomCropMode) return;
    if (previewPanMoved) {
      previewPanMoved = false;
      return;
    }
    toggleZoomCarousel();
  }

  /** Clic en el área del vídeo (no en la banda de controles nativos) alterna el carrusel. */
  function onZoomVideoClick(e: MouseEvent) {
    e.stopPropagation();
    if (zoomCropMode) return;
    if (previewPanMoved) {
      previewPanMoved = false;
      return;
    }
    const video = e.currentTarget as HTMLVideoElement;
    const rect = video.getBoundingClientRect();
    const controlsBandPx = 56;
    if (e.clientY > rect.bottom - controlsBandPx) return;
    toggleZoomCarousel();
  }

  function onZoomStageClick(e: MouseEvent) {
    if (zoomCropMode) return;
    if (previewPanMoved) {
      previewPanMoved = false;
      return;
    }
    // Solo el fondo negro del stage (no la imagen): cerrar visor.
    if (e.target !== e.currentTarget) return;
    previewZoomOpen = false;
  }

  async function moveCurrentZoomToDestination(destPath: string) {
    if (!previewZoomPath) return;
    const currentPath = previewZoomPath;
    stopZoomVideoElement();
    previewZoomVideoSession += 1;
    previewZoomVideoArmed = false;
    previewZoomVideoLaunching = false;
    previewZoomVideoPlayLocked = false;
    previewZoomVideoPreparing = false;
    previewZoomFileUrl = null;
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
            deferredZoomMoveRefresh = {
              state: out.state,
              items: out.items,
              removedPaths: out.removedPaths,
              delta: out.delta,
            };
          } else {
            applyGalleryRefreshFromMove(out);
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
      setGalleryState(out.state);
      setGalleryItems(out.items);
      void afterGalleryDataLoaded();
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
    if (previewZoomMode === "fillWidth") {
      previewPanX = 0;
      previewPanY = 0;
      previewFillWidthAlignPending = false;
    }
    clampPanToStage();
    syncZoomMediaTransform();
    if (previewZoomMode === "fillWidth" && zoomStageEl) {
      const sr = zoomStageEl.getBoundingClientRect();
      if (
        miniMapHasOverflow(
          previewZoomMode,
          previewZoomScale,
          sr.width,
          sr.height,
          previewZoomNaturalW,
          previewZoomNaturalH
        )
      ) {
        touchZoomHud();
      }
    }
  }

  function onZoomVideoMeta() {
    if (!zoomVideoEl) return;
    previewZoomNaturalW = Math.max(1, zoomVideoEl.videoWidth || 1);
    previewZoomNaturalH = Math.max(1, zoomVideoEl.videoHeight || 1);
    if (previewZoomMode === "fillWidth") {
      previewPanX = 0;
      previewPanY = 0;
      previewFillWidthAlignPending = false;
    }
    clampPanToStage();
    syncZoomMediaTransform();
  }

  async function onZoomVideoError(e: Event) {
    const el = e.currentTarget as HTMLVideoElement | null;
    const code = el?.error?.code ?? 0;
    const playback = previewZoomPlayback;
    if (!playback) return;
    const current = previewZoomFileUrl || "";
    if ((code === 4 || code === 3) && playback.transcodeUrl && !sameMediaUrl(current, playback.transcodeUrl)) {
      previewZoomFileUrl = playback.transcodeUrl;
      status = t("preview.videoTranscoding");
      return;
    }
    if ((code === 4 || code === 3 || code === 2) && !isDataPlaybackUrl(current)) {
      const path = String(previewZoomPath ?? "").trim();
      if (path && window.pywebview?.api) {
        try {
          const blob = await bridge.galleryVideoPlaybackBlob(path);
          if (blob?.ok && blob.dataUrl) {
            previewZoomFileUrl = String(blob.dataUrl);
            previewZoomPlayback = { ...playback, transcodeUrl: previewZoomFileUrl, playbackViaBlob: true };
            status = "";
            return;
          }
        } catch {
          /* continuar con fallback MP4 */
        }
      }
    }
    if ((code === 4 || code === 3) && playback.fileUrl && !sameMediaUrl(current, playback.fileUrl)) {
      previewZoomFileUrl = playback.fileUrl;
      status = t("preview.videoCodecError");
    }
  }

  function openZoomFromGallery(it: GalleryItem) {
    const nav = getGalleryItems()
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
      if (!previewPanPointerDown && !previewPanDrag && !miniMapDrag) {
        zoomHudVisible = false;
      }
    }, 2600);
  }

  function navigateFromMiniMap(e: PointerEvent) {
    if (previewZoomMediaType !== "image" || !zoomStageEl || !zoomMiniEl) return;
    e.preventDefault();
    e.stopPropagation();
    const sr = zoomStageEl.getBoundingClientRect();
    const mr = zoomMiniEl.getBoundingClientRect();
    const { width, height } = computeMiniMapSize(
      previewZoomNaturalW,
      previewZoomNaturalH,
      sr.width,
      sr.height
    );
    const layout = computeMiniMapImageLayout(width, height, previewZoomNaturalW, previewZoomNaturalH);
    const norm = miniMapPointToNorm(layout, e.clientX - mr.left, e.clientY - mr.top);
    if (!norm) return;
    const next = panFromMiniMapNorm(
      previewZoomMode,
      previewZoomScale,
      previewPanX,
      previewPanY,
      sr.width,
      sr.height,
      previewZoomNaturalW,
      previewZoomNaturalH,
      norm.normX,
      norm.normY
    );
    previewPanX = next.panX;
    previewPanY = next.panY;
    syncZoomMediaTransform();
    touchZoomHud();
  }

  function beginMiniMapPan(e: PointerEvent) {
    if (previewZoomMediaType !== "image") return;
    miniMapDrag = true;
    navigateFromMiniMap(e);
    zoomMiniEl?.setPointerCapture?.(e.pointerId);
  }

  function moveMiniMapPan(e: PointerEvent) {
    if (!miniMapDrag) return;
    navigateFromMiniMap(e);
  }

  function endMiniMapPan(e: PointerEvent) {
    if (!miniMapDrag) return;
    miniMapDrag = false;
    zoomMiniEl?.releasePointerCapture?.(e.pointerId);
    touchZoomHud();
  }

  $: zoomMiniMapStyle = (() => {
    const _deps = [previewZoomNaturalW, previewZoomNaturalH, previewZoomPath];
    void _deps;
    if (!zoomStageEl || previewZoomNaturalW <= 1) {
      return "width:130px;height:88px;";
    }
    const sr = zoomStageEl.getBoundingClientRect();
    const { width, height } = computeMiniMapSize(
      previewZoomNaturalW,
      previewZoomNaturalH,
      sr.width,
      sr.height
    );
    return `width:${width}px;height:${height}px;`;
  })();

  $: zoomMiniActive =
    previewZoomMediaType === "image" &&
    previewZoomNaturalW > 1 &&
    Boolean(zoomStageEl) &&
    (() => {
      const sr = zoomStageEl!.getBoundingClientRect();
      return miniMapHasOverflow(
        previewZoomMode,
        previewZoomScale,
        sr.width,
        sr.height,
        previewZoomNaturalW,
        previewZoomNaturalH
      );
    })() &&
    (zoomHudVisible || previewPanDrag || previewPanPointerDown || miniMapDrag);

  $: zoomMiniRect = (() => {
    const _deps = [
      previewZoomScale,
      previewPanX,
      previewPanY,
      previewZoomMode,
      previewZoomPath,
      previewZoomNaturalW,
      previewZoomNaturalH,
      zoomMiniMapStyle,
    ];
    void _deps;
    if (!zoomStageEl || previewZoomNaturalW <= 1) return "display:none;";
    const sr = zoomStageEl.getBoundingClientRect();
    const { width, height } = computeMiniMapSize(
      previewZoomNaturalW,
      previewZoomNaturalH,
      sr.width,
      sr.height
    );
    const layout = computeMiniMapImageLayout(width, height, previewZoomNaturalW, previewZoomNaturalH);
    const viewport = computeViewportNorm(
      previewZoomMode,
      previewZoomScale,
      previewPanX,
      previewPanY,
      sr.width,
      sr.height,
      previewZoomNaturalW,
      previewZoomNaturalH
    );
    return computeMiniMapRectStyle(layout, viewport);
  })();

  const saveThumbScale = async () => {
    await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
    await reload({ silent: true });
  };

  const startOrganizer = async () => {
    const out = await bridge.organizerStart(orgPath, {
      ...orgOptions,
      visualSimilarityMin: messSimilaritySetting
    });
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
            .replace("{other}", String(stats.moved_other ?? 0))
            .replace("{grouped}", String(stats.grouped_similar_images ?? 0));
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
  let confirmDeleteSecondaryLabel = "";
  let confirmDeleteSecondaryAction: (() => void | Promise<void>) | null = null;

  /** Menú contextual (clic derecho) en un chip de destino. */
  let destCtxMenu: { x: number; y: number; idx: number; source: "gallery" | "fullscreen" } | null = null;
  /** Menú contextual (clic derecho) en marcador anclado del modal de rutas. */
  let pinnedCtxMenu: { x: number; y: number; path: string } | null = null;
  /** Menú contextual en miniaturas de la galería (imagen / vídeo / carpeta). */
  let galleryItemCtxMenu: {
    x: number;
    y: number;
    path: string;
    name: string;
    kind: string;
    thumbDataUrl?: string | null;
    submenuLeft: boolean;
  } | null = null;
  /** Menú contextual en vista previa de carpeta destino. */
  let destPreviewCtxMenu: {
    x: number;
    y: number;
    paths: string[];
    primaryPath: string;
    primaryName: string;
    thumbDataUrl?: string | null;
    submenuLeft: boolean;
  } | null = null;
  let renameModalOpen = false;
  let renameModalPath = "";
  let renameModalKind: "file" | "folder" = "file";
  let renameModalDraft = "";
  let renameModalTitle = "";
  let galleryFileInfoModal: {
    path: string;
    name: string;
    sizeBytes: number;
    mtimeIso: string;
    mediaType: string;
    extension: string;
    mimeType: string;
  } | null = null;
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
    endDragSession();
    suppressNextGalleryClick = true;
    queueMicrotask(() => {
      suppressNextGalleryClick = false;
    });
  }

  function resetGalleryInteractionLocks() {
    suppressNextGalleryClick = false;
    endDragSession();
    galleryWorkspace?.resetGalleryInteractionState?.();
  }

  function onTileDragStart(e: DragEvent, it: GalleryItem) {
    const groupedRouteDrag = groupByFolder && !galleryMasonryView && !destinationsMode;
    if ((!destinationsMode && !groupedRouteDrag) || !isGallerySelectableKind(it.kind)) return;
    if (galleryRangeSelecting) {
      e.preventDefault();
      return;
    }
    // Modo edición: arrastre con Ctrl. Agrupar por carpeta (vista normal): arrastre directo.
    if (destinationsMode && !(e as DragEvent).ctrlKey) {
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
    ghostCount = Math.max(1, Number(getGalleryState().selectedCount) || 1);
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

  function resolveDragOrSelectedPaths(e: DragEvent): string[] {
    const selected = getSelectedGalleryPaths();
    if (selected.length > 0) return selected;
    const raw = String(e.dataTransfer?.getData("text/plain") ?? "").trim();
    return raw ? [raw] : [];
  }

  async function movePathsToRouteFolder(folderPath: string, paths: string[]) {
    const fp = normalizePathForApi(folderPath);
    if (!fp || paths.length === 0) {
      status = t("status.noImagesToMove");
      return;
    }
    const snapshot = createGalleryMoveJobSnapshot(paths);
    await applyOptimisticGalleryRemove(snapshot);
    const job: GalleryMoveJob = { ...snapshot, destPath: fp };
    galleryMoveQueue = [...galleryMoveQueue, job];
    status = t("status.imagesMoving")
      .replace("{n}", String(paths.length))
      .replace("{queue}", String(galleryMoveQueue.length));
    if (!galleryMoveWorkerRunning) {
      void processGalleryMoveQueue();
    }
  }

  function onSectionFolderDrop(e: DragEvent, folderPath: string) {
    e.preventDefault();
    e.stopPropagation();
    ignoreDestCardClickUntil = Date.now() + 450;
    endDragSessionAfterGesture();
    const fp = String(folderPath ?? "").trim();
    if (!fp) return;
    if (groupByFolder && !galleryMasonryView) {
      const paths = resolveDragOrSelectedPaths(e);
      void movePathsToRouteFolder(fp, paths);
      return;
    }
    askConfirmMoveSelected(fp);
  }

  // Maneja cuando se suelta un arrastre sobre una carpeta de la rejilla
  async function onFolderTileDrop(e: DragEvent, folderPath: string) {
    e.preventDefault();
    e.stopPropagation();
    ignoreDestCardClickUntil = Date.now() + 450;
    endDragSessionAfterGesture();
    const fp = String(folderPath ?? "").trim();
    if (!fp) return;
    const paths = resolveDragOrSelectedPaths(e);
    if (paths.length === 0) return;

    // Solo mover si e.ctrlKey está presionado (para mover elementos a carpetas con Ctrl)
    if (e.ctrlKey) {
      await movePathsToFolderTile(fp, paths);
    }
  }

  // Mueve una lista de rutas (archivos o carpetas) a la carpeta destino especificada
  async function movePathsToFolderTile(folderPath: string, paths: string[]) {
    const fp = normalizePathForApi(folderPath);
    if (!fp || paths.length === 0) return;

    // Evita mover una carpeta dentro de sí misma o de un descendiente
    const validPaths = paths.filter((p) => {
      const pNorm = normalizePathForApi(p);
      return pNorm !== fp && !fp.startsWith(pNorm + "/");
    });

    if (validPaths.length === 0) {
      status = "No hay elementos válidos para mover";
      return;
    }

    const snapshot = createGalleryMoveJobSnapshot(validPaths);
    await applyOptimisticGalleryRemove(snapshot);
    const job: GalleryMoveJob = { ...snapshot, destPath: fp };
    galleryMoveQueue = [...galleryMoveQueue, job];
    status = t("status.imagesMoving")
      .replace("{n}", String(validPaths.length))
      .replace("{queue}", String(galleryMoveQueue.length));
    if (!galleryMoveWorkerRunning) {
      void processGalleryMoveQueue();
    }
  }

  function onDestDrop(e: DragEvent, destPath: string, destIdx: number) {
    e.preventDefault();
    e.stopPropagation();
    const fromRaw = e.dataTransfer?.getData("application/x-om-dest-idx") ?? "";
    const fromIdx = Number.parseInt(fromRaw, 10);
    if (Number.isFinite(fromIdx) && fromIdx >= 0 && fromIdx !== destIdx) {
      void reorderDestinations(fromIdx, destIdx);
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
    const parentId = parentIdOrEmpty(destToolbarFolderId);
    const siblingCount = getChildrenAt(destTree, destToolbarFolderId).length;
    if (fromIdx < 0 || toIdx < 0 || fromIdx >= siblingCount || toIdx >= siblingCount) return;
    try {
      const out = await trackLoad(bridge.destinationsReorder(parentId, fromIdx, toIdx));
      applyDestinationsPayload(out);
      status = t("status.destReorderOk");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destReorderError");
    } finally {
      draggedDestIdx = null;
    }
  }

  /** Clic en chip de destino: mover selección o abrir vista previa de carpeta. */
  function onDestCardClick(e: MouseEvent, path: string) {
    if (e.button !== 0) return;
    if (Date.now() < ignoreDestCardClickUntil) return;
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
    resetMoveFlyoutState();
  }

  function closeDestPreviewCtxMenu() {
    destPreviewCtxMenu = null;
    resetMoveFlyoutState();
  }

  function onMoveDestRootEnter() {
    cancelMoveMenuClose();
    moveRootHovered.set(true);
  }

  function onMoveDestRootLeave(e: PointerEvent) {
    onMoveRootPointerLeave(e);
  }

  function formatFileSizeBytes(n: number): string {
    const x = Math.max(0, Number(n) || 0);
    if (x < 1024) return `${x} B`;
    if (x < 1024 * 1024) return `${(x / 1024).toFixed(1)} KB`;
    if (x < 1024 * 1024 * 1024) return `${(x / (1024 * 1024)).toFixed(2)} MB`;
    return `${(x / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function formatGalleryMediaTypeLabel(mediaType: string, extension: string): string {
    const base =
      mediaType === "video"
        ? t("contextGallery.mediaTypeVideo")
        : mediaType === "image"
          ? t("contextGallery.mediaTypeImage")
          : t("contextGallery.mediaTypeOther");
    const ext = String(extension ?? "").trim().replace(/^\./, "");
    return ext ? `${base} (.${ext})` : base;
  }

  function onGalleryItemContextMenu(e: MouseEvent, it: GalleryItem) {
    if (it.kind !== "image" && it.kind !== "video" && it.kind !== "folder") return;
    e.preventDefault();
    e.stopPropagation();
    const pad = 8;
    const menuW = 220;
    const submenuW = 200;
    const menuH = it.kind === "folder" ? 120 : 320;
    let x = e.clientX;
    let y = e.clientY;
    x = Math.min(x, window.innerWidth - menuW - pad);
    y = Math.min(y, window.innerHeight - menuH - pad);
    x = Math.max(pad, x);
    y = Math.max(pad, y);
    const submenuLeft = it.kind !== "folder" && x + menuW + submenuW > window.innerWidth - pad;
    closeDestCtxMenu();
    closePinnedCtxMenu();
    closeDestPreviewCtxMenu();
    galleryItemCtxMenu = {
      x,
      y,
      path: it.path,
      name: it.name,
      kind: it.kind,
      thumbDataUrl: it.thumbDataUrl ?? null,
      submenuLeft,
    };
  }

  function onDestPreviewItemContextMenu(
    e: CustomEvent<{ item: { path: string; name: string; thumbDataUrl?: string | null }; clientX: number; clientY: number }>
  ) {
    const { item, clientX, clientY } = e.detail;
    const selected = destPreviewModal?.getSelectedPaths() ?? [];
    const paths =
      selected.length > 0 && selected.includes(item.path) ? [...selected] : [item.path];
    const pad = 8;
    const menuW = 220;
    const submenuW = 200;
    const menuH = 360;
    let x = clientX;
    let y = clientY;
    x = Math.min(x, window.innerWidth - menuW - pad);
    y = Math.min(y, window.innerHeight - menuH - pad);
    x = Math.max(pad, x);
    y = Math.max(pad, y);
    const submenuLeft = x + menuW + submenuW > window.innerWidth - pad;
    closeGalleryItemCtxMenu();
    closeDestCtxMenu();
    closePinnedCtxMenu();
    destPreviewCtxMenu = {
      x,
      y,
      paths,
      primaryPath: item.path,
      primaryName: item.name,
      thumbDataUrl: item.thumbDataUrl ?? null,
      submenuLeft,
    };
  }

  async function copyDestPreviewCtxPath() {
    if (!destPreviewCtxMenu) return;
    const text = destPreviewCtxMenu.paths.join("\n");
    const ok = await copyTextToClipboard(text);
    status = ok ? t("contextGallery.copyPathOk") : t("contextGallery.copyError");
    closeDestPreviewCtxMenu();
  }

  async function showDestPreviewItemInExplorer() {
    if (!destPreviewCtxMenu || destPreviewCtxMenu.paths.length === 0) return;
    const path = destPreviewCtxMenu.primaryPath || destPreviewCtxMenu.paths[0];
    closeDestPreviewCtxMenu();
    try {
      const res = await bridge.galleryShowInExplorer(path);
      if (!res.ok) {
        status = res.error || "No se pudo mostrar en el explorador";
      }
    } catch (e) {
      status = e instanceof Error ? e.message : "Error al abrir explorador";
    }
  }

  async function copyDestPreviewCtxFullImage() {
    if (!destPreviewCtxMenu) return;
    const path = destPreviewCtxMenu.primaryPath;
    status = t("load.loading");
    try {
      const res = await bridge.galleryCopyToClipboard(path);
      status = res.ok ? t("contextGallery.copyThumbOk") : res.error || t("contextGallery.copyError");
    } catch {
      status = t("contextGallery.copyError");
    }
    closeDestPreviewCtxMenu();
  }

  async function moveDestPreviewCtxToRoute() {
    if (!destPreviewCtxMenu) return;
    const paths = [...destPreviewCtxMenu.paths];
    closeDestPreviewCtxMenu();
    await movePreviewPathsToCurrentRoute(paths);
  }

  async function moveDestPreviewCtxToDest(destPath: string) {
    if (!destPreviewCtxMenu) return;
    const paths = [...destPreviewCtxMenu.paths];
    closeDestPreviewCtxMenu();
    destPreviewModal?.removePaths(paths);
    destPreviewModal?.clearSelectedPaths();
    try {
      const out = await trackLoad(bridge.destinationMovePaths(paths, destPath));
      const moved = Number(out.moveResult?.moved ?? 0);
      const errors = Number(out.moveResult?.errors ?? 0);
      status =
        t("contextDestPreview.movedOk").replace("{moved}", String(moved)) +
        (errors ? t("status.previewMovedErrors").replace("{errors}", String(errors)) : "");
      if (errors > 0 || moved < paths.length) destPreviewModal?.reloadPreview();
    } catch (e: unknown) {
      destPreviewModal?.reloadPreview();
      status = e instanceof Error ? e.message : t("contextGallery.moveFailed");
    }
  }

  function openRenameFromDestPreviewCtx() {
    if (!destPreviewCtxMenu || destPreviewCtxMenu.paths.length !== 1) return;
    renameModalPath = destPreviewCtxMenu.primaryPath;
    renameModalKind = "file";
    renameModalDraft = destPreviewCtxMenu.primaryName;
    renameModalTitle = t("contextGallery.renameFileTitle");
    closeDestPreviewCtxMenu();
    renameModalOpen = true;
  }

  async function openDestPreviewFileInfoFromCtx() {
    if (!destPreviewCtxMenu || destPreviewCtxMenu.paths.length !== 1) return;
    const path = destPreviewCtxMenu.primaryPath;
    closeDestPreviewCtxMenu();
    try {
      const st = await trackLoad(bridge.galleryFileStat(path));
      galleryFileInfoModal = {
        path: String(st.path ?? path),
        name: String(st.name ?? ""),
        sizeBytes: Number(st.sizeBytes ?? 0),
        mtimeIso: String(st.mtimeIso ?? ""),
        mediaType: String(st.mediaType ?? "other"),
        extension: String(st.extension ?? ""),
        mimeType: String(st.mimeType ?? ""),
      };
    } catch {
      status = t("contextGallery.propertiesError");
    }
  }

  function askDeleteDestPreviewFromCtx() {
    if (!destPreviewCtxMenu) return;
    const paths = [...destPreviewCtxMenu.paths];
    const primaryName = destPreviewCtxMenu.primaryName;
    const count = paths.length;
    closeDestPreviewCtxMenu();
    openConfirmDelete(
      count > 1 ? t("confirm.deleteSelectionTitle") : t("contextGallery.deleteTitle"),
      count > 1
        ? t("confirm.deleteSelectionDetail").replace("{count}", String(count))
        : t("confirm.deleteFileDetail").replace("{name}", primaryName),
      async () => {
        await deleteDestPreviewPaths(paths);
      },
      { confirmLabel: t("contextGallery.confirmDeleteBtn") }
    );
  }

  function openRenameFromCtx() {
    if (!galleryItemCtxMenu) return;
    renameModalPath = galleryItemCtxMenu.path;
    renameModalKind = galleryItemCtxMenu.kind === "folder" ? "folder" : "file";
    renameModalDraft = galleryItemCtxMenu.name;
    renameModalTitle =
      renameModalKind === "folder" ? t("contextGallery.renameFolderTitle") : t("contextGallery.renameFileTitle");
    closeGalleryItemCtxMenu();
    renameModalOpen = true;
  }

  function closeRenameModal() {
    renameModalOpen = false;
    renameModalPath = "";
    renameModalDraft = "";
  }

  async function saveRenameModal() {
    const path = renameModalPath.trim();
    const newName = renameModalDraft.trim();
    if (!path || !newName) return;
    try {
      const out = await trackLoad(bridge.galleryRenamePath(path, newName));
      setGalleryPayload(out.state, out.items);
      await afterGalleryDataLoaded();
      const newPath = String(out.renameResult?.newPath ?? "").trim();
      const finalName = String(out.renameResult?.newName ?? newName).trim();
      if (previewZoomOpen && previewZoomPath === path && newPath) {
        previewZoomPath = newPath;
        previewZoomName = finalName;
      }
      if (newPath) {
        zoomNavItems = zoomNavItems.map((z) =>
          z.path === path ? { ...z, path: newPath, name: finalName } : z
        );
      }
      status = t("contextGallery.renameOk");
      if (previewOpen && newPath) {
        destPreviewModal?.updateItemPath(path, newPath, finalName);
      }
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("contextGallery.renameError");
    } finally {
      closeRenameModal();
    }
  }

  function askDeleteFolderFromCtx() {
    if (!galleryItemCtxMenu || galleryItemCtxMenu.kind !== "folder") return;
    const p = galleryItemCtxMenu.path;
    const label = galleryItemCtxMenu.name;
    closeGalleryItemCtxMenu();
    openConfirmDelete(
      t("contextFolder.deleteTitle"),
      t("contextFolder.deleteDetail").replace("{name}", label),
      async () => {
        try {
          const out = await trackLoad(bridge.galleryDeleteFolder(p));
          setGalleryPayload(out.state, out.items ?? []);
          await afterGalleryDataLoaded();
          resetGalleryInteractionLocks();
          status = t("status.deleteBatchLine")
            .replace("{deleted}", "1")
            .replace("{errPart}", "")
            .replace("{queue}", "0");
        } catch (e: unknown) {
          status = e instanceof Error ? e.message : t("status.deleteQueueError");
        }
      },
      { confirmLabel: t("contextGallery.confirmDeleteBtn") }
    );
  }

  async function copyGalleryCtxPath() {
    if (!galleryItemCtxMenu) return;
    const p = galleryItemCtxMenu.path;
    const ok = await copyTextToClipboard(p);
    status = ok ? t("contextGallery.copyPathOk") : t("contextGallery.copyError");
    closeGalleryItemCtxMenu();
  }

  async function showGalleryItemInExplorer() {
    if (!galleryItemCtxMenu) return;
    const path = galleryItemCtxMenu.path;
    closeGalleryItemCtxMenu();
    try {
      const res = await bridge.galleryShowInExplorer(path);
      if (!res.ok) {
        status = res.error || "No se pudo mostrar en el explorador";
      }
    } catch (e) {
      status = e instanceof Error ? e.message : "Error al abrir explorador";
    }
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
    const snapshot = createGalleryMoveJobSnapshot([src]);
    await applyOptimisticGalleryRemove(snapshot);
    const job: GalleryMoveJob = { ...snapshot, destPath };
    try {
      const out = await trackLoad(bridge.galleryMovePath(src, destPath));
      if (!isGalleryNavigationCurrent(job.navGen)) return;
      const moved = Number(out.moveResult?.moved ?? 0);
      if (moved > 0) {
        await reconcileGalleryMoveSuccess(out);
        status = t("contextGallery.movedOk");
      } else {
        await rollbackOptimisticGalleryMove(job);
        status = t("contextGallery.moveFailed");
      }
    } catch (e: unknown) {
      await rollbackOptimisticGalleryMove(job);
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
        mediaType: String(st.mediaType ?? "other"),
        extension: String(st.extension ?? ""),
        mimeType: String(st.mimeType ?? ""),
      };
    } catch {
      status = t("contextGallery.propertiesError");
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

  // Muestra el marcador anclado en el explorador de archivos del sistema
  async function showPinnedInExplorer() {
    if (!pinnedCtxMenu) return;
    const path = pinnedCtxMenu.path;
    closePinnedCtxMenu();
    try {
      const res = await bridge.galleryShowInExplorer(path);
      if (!res.ok) {
        status = res.error || "No se pudo mostrar en el explorador";
      }
    } catch (e) {
      status = e instanceof Error ? e.message : "Error al abrir explorador";
    }
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
        await trackLoad(bridge.destinationsAdd(label, path, parentIdOrEmpty(destToolbarFolderId)));
        await syncDestinationsFromApi();
        status = t("status.destAdded");
      } else if (destFormIdx !== null) {
        await trackLoad(
          bridge.destinationsEdit(parentIdOrEmpty(destToolbarFolderId), destFormIdx, label, path)
        );
        await syncDestinationsFromApi();
        status = t("status.destUpdated");
      }
      destFormOpen = false;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destSaveError");
    }
  }

  function destNodeAtToolbarIdx(idx: number) {
    return getChildrenAt(destTree, destToolbarFolderId)[idx] ?? null;
  }

  function openEditFromCtx() {
    if (destCtxMenu === null) return;
    const idx = destCtxMenu.idx;
    const node = destNodeAtToolbarIdx(idx);
    closeDestCtxMenu();
    if (!node || !isDestNode(node)) return;
    destFormMode = "edit";
    destFormIdx = idx;
    destFormLabel = node.label;
    destFormPath = node.path;
    destFormOpen = true;
  }

  function openPreviewFromCtx() {
    if (destCtxMenu === null) return;
    const node = destNodeAtToolbarIdx(destCtxMenu.idx);
    closeDestCtxMenu();
    if (!node || !isDestNode(node)) return;
    openDestPreview(node.path);
  }

  // Muestra el destino en el explorador de archivos del sistema
  async function showDestInExplorer() {
    if (destCtxMenu === null) return;
    const node = destNodeAtToolbarIdx(destCtxMenu.idx);
    closeDestCtxMenu();
    if (!node || !isDestNode(node)) return;
    try {
      const res = await bridge.galleryShowInExplorer(node.path);
      if (!res.ok) {
        status = res.error || "No se pudo mostrar en el explorador";
      }
    } catch (e) {
      status = e instanceof Error ? e.message : "Error al abrir explorador";
    }
  }

  async function removeDestFromCtx() {
    if (destCtxMenu === null) return;
    const i = destCtxMenu.idx;
    closeDestCtxMenu();
    try {
      await trackLoad(bridge.destinationsRemove(parentIdOrEmpty(destToolbarFolderId), i));
      await syncDestinationsFromApi();
      status = t("status.destRemoved");
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : t("status.destDeleteError");
    }
  }

  $: if (!destinationsMode && !previewZoomDestMode) {
    destCtxMenu = null;
    if (destFormOpen) destFormOpen = false;
  }

  $: if (!routePickerOpen) {
    pinnedCtxMenu = null;
  }

  $: if (!previewZoomOpen && deferredZoomMoveRefresh) {
    void applyGalleryItemsDelta(deferredZoomMoveRefresh);
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

  $: {
    if (previewZoomOpen && !prevPreviewZoomOpen) {
      previewVisibleBeforeZoom = previewVisible;
      if (previewVisible) previewVisible = false;
    } else if (!previewZoomOpen && prevPreviewZoomOpen) {
      if (previewVisibleBeforeZoom) previewVisible = true;
      previewVisibleBeforeZoom = null;
      void teardownPreviewZoom();
    }
    prevPreviewZoomOpen = previewZoomOpen;
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
        await loadFolder(true);
      } catch {
        status = t("status.restoreFolderError");
      }
    }
    pollTimer = window.setInterval(() => {
      pollOrganizer().catch(() => undefined);
      if (
        videoTranscodeJobs.length > 0 ||
        previewVideoPreparing ||
        previewVideoLaunching ||
        previewVideoArmed
      ) {
        pollVideoTranscodeJobs().catch(() => undefined);
      }
    }, 1100);
  });

  onDestroy(() => {
    endDragSession();
    cancelPendingGalleryThumbFlush();
    if (thumbScaleDebounce) clearTimeout(thumbScaleDebounce);
    if (zoomHudTimer) clearTimeout(zoomHudTimer);
    stopVideoPreparePoll();
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  });
  import Toolbar from './components/Toolbar.svelte';
  import SidebarMarkers from './components/SidebarMarkers.svelte';
  import FullscreenPlayer from './components/FullscreenPlayer.svelte';
</script>

<svelte:window
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
    if (moveAsFolderModalOpen) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closeMoveAsFolderModal();
        return;
      }
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
    if (destPreviewCtxMenu) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closeDestPreviewCtxMenu();
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
        destPreviewModal?.clearSelectedPaths();
        status = t("status.selectionCleared");
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
      !messPanelOpen &&
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
      !messPanelOpen &&
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
      const previewSelCount = previewOpen ? (destPreviewModal?.getSelectedPaths()?.length ?? 0) : 0;
      const hasPreviewSelectionForDelete = previewOpen && previewSelCount > 0;
      const hasGallerySelectionForDelete =
        Number(getGalleryState()?.selectedCount ?? 0) > 0 ||
        getGalleryItems().some((x) => isGallerySelectableKind(x.kind) && Boolean(x.selected));
      if (previewZoomOpen && previewZoomPath) {
        e.preventDefault();
        openConfirmDelete(t("confirm.deleteImageTitle"), t("confirm.deleteImageDetail"), deleteCurrentZoomImage);
        return;
      }
      if (hasPreviewSelectionForDelete) {
        e.preventDefault();
        openConfirmDelete(
          t("confirm.deleteSelectionTitle"),
          t("confirm.deleteSelectionDetail").replace("{count}", String(previewSelCount)),
          deletePreviewSelectedItems
        );
        return;
      }
      if (hasGallerySelectionForDelete) {
        e.preventDefault();
        openConfirmDelete(
          t("confirm.deleteSelectionTitle"),
          t("confirm.deleteSelectionDetail").replace("{count}", String(getGalleryState().selectedCount)),
          deleteSelectedGalleryItems
        );
        return;
      }
    }
    if (!shortcutMatchesSingle(e as KeyboardEvent, keyboardShortcuts.escape)) return;
    const previewSelCount = previewOpen ? (destPreviewModal?.getSelectedPaths()?.length ?? 0) : 0;
    const hasPreviewSelection = previewOpen && previewSelCount > 0;
    const hasGallerySelection =
      Number(getGalleryState()?.selectedCount ?? 0) > 0 ||
        getGalleryItems().some((x) => isGallerySelectableKind(x.kind) && Boolean(x.selected));
    if (hasPreviewSelection || hasGallerySelection) {
      e.preventDefault();
      if (hasPreviewSelection) {
        destPreviewModal?.clearSelectedPaths();
      }
      if (hasGallerySelection) {
        void clearSelection();
      }
      status = t("status.selectionCleared");
      return;
    }
    if (pinnedCtxMenu) closePinnedCtxMenu();
    else if (galleryItemCtxMenu) closeGalleryItemCtxMenu();
    else if (destPreviewCtxMenu) closeDestPreviewCtxMenu();
    else if (renameModalOpen) closeRenameModal();
    else if (moveAsFolderModalOpen) closeMoveAsFolderModal();
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
    else if (routePickerOpen) routePickerOpen = false;
    else if (orgPanelOpen) orgPanelOpen = false;
    else if (messPanelOpen) messPanelOpen = false;
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
  
  <div class="app-chrome app-chrome--header">
  <Toolbar
    bind:destinationsMode
    bind:viewMenuOpen
    bind:includeSubfolders
    bind:groupByFolder
    bind:groupByAlpha
    onGroupByAlphaChange={(checked) => void onGroupByAlphaChange(checked)}
    bind:sectionDominantColor
    bind:timelineView
    bind:galleryMasonryView
    bind:gallerySortMode
    bind:dynamicNameRegex
    bind:orgPath
    bind:folder
    bind:orgPanelOpen
    bind:messPanelOpen
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
    {onGalleryMasonryViewChange}
    {onGallerySortApply}
    onDynamicNameRegexChange={(checked) => void onDynamicNameRegexChange(checked)}
    {goBackFolder}
    {goForwardFolder}
    {goUpFolder}
    {unpinFolder}
    {openPinMarkerModal}
    reload={reloadGalleryFresh}
    {pickGalleryFolder}
    {loadFolder}
    {openSettingsModal}
  />
  </div>

  

  

  <div
    class="destinos-work"
    class:destinos-work--drag={destinationsMode && destSplitDrag}
  >
    <div class="destinos-work__top">
      <section
        class="content content--gallery-shell"
        style={previewVisible
          ? `grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`
          : "grid-template-columns:minmax(0,1fr)"}
      >
        <GalleryWorkspace
          bind:this={galleryWorkspace}
          bind:galleryScrollEl
          bind:galleryLoadingMore
          bind:galleryRangeSelecting
          bind:galleryRangeSuppressClick
          bind:galleryCursorPath
          bind:galleryKeyboardNavHintActive
          bind:dragOverSectionPath
          bind:dragOverDestPath
          bind:draggedDestIdx
          bind:thumbGapPx
          bind:showThumbLabels
          {destinationsMode}
          {groupByFolder}
          {galleryTileDragEnabled}
          {timelineView}
          {galleryMasonryView}
          {galleryMasonryTightSpacing}
          messSuggestionsEnabled={messSuggestionsEnabled}
          messFolder={messFolderSetting}
          galleryFolder={folder}
          messSuggestionsMasonry={galleryMasonryView || messPinterestMasonry}
          {thumbScale}
          {thumbsPerPage}
          {previewVisible}
          {suppressNextGalleryClick}
          {navigateToFolder}
          {openZoomFromGallery}
          {onGalleryItemContextMenu}
          {onSectionFolderDrop}
          {onFolderTileDrop}
          {onTileDragStart}
          {openConfirmDelete}
          {deleteSelectedGalleryItems}
          {openAddDestForm}
          {onDestCardClick}
          {onDestContextMenu}
          {onDestChipDragStart}
          {onDestChipDragEnd}
          {onDestDrop}
          destToolbarItems={destToolbarVisibleItems}
          {destToolbarFolderLabel}
          {destToolbarCanGoBack}
          onDestToolbarBack={() => void destToolbarBack()}
          onDestToolbarOpenFolder={(id) => void navigateDestToolbarFolder(id)}
          onMessSuggestionMoved={onMessSuggestionMoved}
          on:preview={(e) => setSelectedPreviewFromPath(e.detail.path)}
          {destTree}
          {destTreeHasTargets}
          onMoveSectionFolderToDest={askConfirmMoveSectionFolder}
          onGroupSelectionInFolder={askGroupSelectionInFolder}
        />

        {#if previewVisible}
          <div
            class="splitter"
            role="separator"
            aria-orientation="vertical"
            aria-label="Arrastrar para repartir galería y vista previa"
            on:pointerdown={beginSplitDrag}
          ></div>

          <aside class="preview om-panel app-chrome app-chrome--preview">
            <div class="preview__main">
            {#if selectedPreview?.mediaType === "video"}
              <div class="preview__video-toolbar">
                <PreviewVideoProfiles
                  profiles={previewVideoProfiles}
                  activeMode={previewVideoMode}
                  disabled={previewVideoPlayLocked && previewVideoLaunching}
                  autoplayEnabled={previewVideoAutoplayOn}
                  autoplayEditMode={destinationsMode}
                  autoplayDisabled={previewVideoPlayLocked && previewVideoLaunching}
                  on:change={(e) => void setPreviewVideoMode(e.detail)}
                  on:autoplayToggle={() => void togglePreviewVideoAutoplay()}
                />
              </div>
              {#if previewVideoArmed || previewVideoLaunching || previewVideoPlayLocked}
                <div class="preview__video-shell">
                  <!-- svelte-ignore a11y_media_has_caption -->
                  {#key mediaUrlKey(previewVideoSrc || selectedPreview?.fileUrl || "pending")}
                    <video
                      bind:this={previewVideoEl}
                      class="preview__img preview__video"
                      src={previewVideoSrc || selectedPreview?.fileUrl || undefined}
                      poster={selectedPreview.placeholderUrl ?? undefined}
                      controls={Boolean(previewVideoSrc || selectedPreview?.fileUrl)}
                      playsinline
                      preload="auto"
                      on:loadstart={onPreviewVideoLoadStart}
                      on:error={onPreviewVideoError}
                      on:canplay={onPreviewVideoCanPlay}
                    ></video>
                  {/key}
                  {#if previewVideoPreparing}
                    <div class="preview__video-busy" aria-live="polite">
                      <div class="preview__video-busy__spinner" aria-hidden="true"></div>
                      <p>{previewVideoPrepareMsg || t("preview.videoStarting")}</p>
                      {#each videoTranscodeJobs.filter((j) => isActiveTranscodeJob(j) && normalizePathForApi(j.path) === normalizePathForApi(selectedPreview?.path ?? "")) as job (job.id)}
                        <p class="preview__video-busy__hint">{transcodeJobStatusLabel(job)}</p>
                      {/each}
                    </div>
                  {/if}
                </div>
              {:else}
                {#key selectedPreview.path}
                  <PreviewVideoIdle
                    posterUrl={selectedPreview.placeholderUrl ?? null}
                    name={selectedPreview.name}
                    playLocked={previewVideoPlayLocked}
                    preparing={previewVideoPreparing || previewVideoLaunching}
                    statusMessage={previewVideoPrepareMsg}
                    onPlay={requestPreviewVideoPlay}
                  />
                {/key}
              {/if}
              {#if previewVideoError}
                <div class="preview__video-error">
                  <p>{previewVideoError}</p>
                  {#if previewVideoErrorDetails}
                    <pre class="preview__video-diag" class:preview__video-diag--loading={previewVideoDiagLoading}>{previewVideoErrorDetails}</pre>
                  {/if}
                  <div class="preview__video-actions">
                    {#if previewVideoError || previewVideoErrorDetails || previewVideoLastErrorDetail}
                      <button
                        type="button"
                        class="om-btn preview__video-copy"
                        on:click={() => void copyPreviewVideoError()}
                      >
                        {t("preview.videoCopyError")}
                      </button>
                    {/if}
                    {#if selectedPreview?.path}
                      <button
                        type="button"
                        class="om-btn preview__video-external"
                        on:click={() => void openGalleryVideoExternal()}
                      >
                        {t("preview.videoOpenExternal")}
                      </button>
                    {/if}
                  </div>
                </div>
              {/if}
            {:else if selectedPreview?.mediaType === "svg" && selectedPreview?.fileUrl}
              <img
                class="preview__img preview__svg"
                src={selectedPreview.fileUrl}
                alt={selectedPreview.name}
              />
            {:else if selectedPreview?.dataUrl || selectedPreview?.fileUrl || selectedPreview?.placeholderUrl}
              {#key selectedPreview.path}
                <PreviewZoomPanel
                  path={selectedPreview.path}
                  name={selectedPreview.name}
                  fileUrl={selectedPreview.fileUrl ?? null}
                  dataUrl={selectedPreview.dataUrl ?? null}
                  placeholderUrl={selectedPreview.placeholderUrl ?? selectedPreview.dataUrl ?? null}
                />
              {/key}
            {:else}
              <div class="preview__empty">{t("preview.emptySelect")}</div>
            {/if}
            </div>
            {#if destinationsMode && editModeSelectedMedia.length > 0}
              <PreviewSelectionGrid
                items={editModeSelectedMedia}
                activePath={selectedPreview?.path ?? null}
                onSelect={previewStripSelectPath}
                onRemove={(path) => void deselectGalleryPath(path)}
              />
            {/if}
            <div class="preview__meta">{selectedPreview?.name ?? ""}</div>
          </aside>
        {/if}
      </section>
    </div>
  </div>

  <PagerBar
    {thumbsPerPage}
    bind:pageJumpDraft
    {status}
    {previewVisible}
    {previewRatio}
    bind:thumbScale
    {activeProcesses}
    {goPage}
    {jumpToPageDraft}
    {togglePreviewVisible}
    {scheduleThumbScaleReload}
    {flushThumbScaleOnRelease}
  />

  {#if previewOpen}
    <DestPreviewModal
      bind:this={destPreviewModal}
      bind:open={previewOpen}
      destPath={previewDestPath}
      {thumbScale}
      {thumbGapPx}
      {showThumbLabels}
      {gridCellPx}
      on:close={() => (previewOpen = false)}
      on:zoom={(e) => openPreviewZoom(e.detail.item, { navItems: e.detail.navItems })}
      on:deleteSelected={() =>
        openConfirmDelete(
          t("confirm.deleteSelectionTitle"),
          t("confirm.deleteSelectionDetail").replace(
            "{count}",
            String(destPreviewModal?.getSelectedPaths()?.length ?? 0)
          ),
          deletePreviewSelectedItems
        )}
      on:dropToRoute={(e) => void movePreviewPathsToCurrentRoute(e.detail.paths)}
      on:contextmenu={onDestPreviewItemContextMenu}
    />
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
          <label class="check"><input type="checkbox" bind:checked={orgOptions.groupSimilarVisual} /> {t("organizer.groupSimilarVisual")}</label>
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

  <MessPanel
    open={messPanelOpen}
    galleryFolder={folder}
    initialMessFolder={messFolderSetting}
    initialSimilarity={messSimilaritySetting}
    onClose={() => (messPanelOpen = false)}
    onMoved={async () => {
      await reload({ silent: true });
    }}
  />

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
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={showDestInExplorer}
        >{t("contextGallery.showInExplorer")}</button
      >
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
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={showPinnedInExplorer}
        >{t("contextGallery.showInExplorer")}</button
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
      aria-label={galleryItemCtxMenu.kind === "folder" ? t("menus.galleryFolderAria") : t("menus.galleryFileAria")}
      style={`left:${galleryItemCtxMenu.x}px;top:${galleryItemCtxMenu.y}px`}
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      {#if galleryItemCtxMenu.kind === "folder"}
        <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openRenameFromCtx}
          >{t("contextFolder.rename")}</button
        >
        <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={showGalleryItemInExplorer}
          >{t("contextGallery.showInExplorer")}</button
        >
        <button
          type="button"
          class="dest-ctx-menu__item dest-ctx-menu__item--danger"
          role="menuitem"
          on:click={askDeleteFolderFromCtx}>{t("contextFolder.delete")}</button
        >
      {:else}
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={() => void copyGalleryCtxPath()}
        >{t("contextGallery.copyPath")}</button
      >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={showGalleryItemInExplorer}
        >{t("contextGallery.showInExplorer")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={!galleryItemCtxMenu.thumbDataUrl || !String(galleryItemCtxMenu.thumbDataUrl).startsWith("data:")}
        on:click={() => void copyGalleryCtxFullImage()}
        >{t("contextGallery.copyThumb")}</button
      >
      <div
        class="ctx-menu__submenu-wrap"
        class:ctx-menu__submenu-wrap--left={galleryItemCtxMenu.submenuLeft}
        class:ctx-menu__submenu-wrap--open={$moveDestPanelOpen}
        on:pointerenter={onMoveDestRootEnter}
        on:pointerleave={onMoveDestRootLeave}
      >
        <button
          type="button"
          class="dest-ctx-menu__item ctx-menu__submenu-trigger"
          role="menuitem"
          aria-haspopup="true"
          aria-expanded="false"
          disabled={!destTreeHasTargets}
          title={!destTreeHasTargets ? t("contextGallery.noDestinations") : undefined}
        >
          <span>{t("contextGallery.moveTo")}</span>
          <span class="ctx-menu__submenu-trigger-mark" aria-hidden="true">{galleryItemCtxMenu.submenuLeft ? "◂" : "▸"}</span>
        </button>
        <div
          class="ctx-menu__submenu ctx-menu__submenu--dest-tree om-panel om-panel--lift"
          role="menu"
          aria-label={t("contextGallery.moveTo")}
        >
          {#if !destTreeHasTargets}
            <div class="ctx-menu__submenu-empty">{t("contextGallery.noDestinations")}</div>
          {:else}
            <div class="dest-move-tree__scroll">
              <DestMoveCtxTree
                nodes={destTree}
                onPick={(p) => void moveGalleryItemFromCtxTo(p)}
              />
            </div>
          {/if}
        </div>
      </div>
      {#if galleryItemCtxMenu.kind === "video"}
        <button
          type="button"
          class="dest-ctx-menu__item"
          role="menuitem"
          on:click={() => void openGalleryExternalFromCtx()}
          >{t("contextGallery.openExternal")}</button
        >
      {/if}
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={openRenameFromCtx}
        >{t("contextGallery.rename")}</button
      >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={() => void openGalleryFileInfoFromCtx()}
        >{t("contextGallery.properties")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item dest-ctx-menu__item--danger"
        role="menuitem"
        on:click={askDeleteGalleryItemFromCtx}>{t("contextGallery.delete")}</button
      >
      {/if}
    </div>
  {/if}

  {#if destPreviewCtxMenu}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="ctx-menu-backdrop" role="presentation" on:click={closeDestPreviewCtxMenu}></div>
    <!-- svelte-ignore a11y-interactive-supports-focus -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="dest-ctx-menu gallery-item-ctx-menu om-panel om-panel--lift"
      role="menu"
      tabindex="-1"
      aria-label={t("menus.destPreviewFileAria")}
      style={`left:${destPreviewCtxMenu.x}px;top:${destPreviewCtxMenu.y}px`}
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={() => void copyDestPreviewCtxPath()}
        >{t("contextGallery.copyPath")}</button
      >
      <button type="button" class="dest-ctx-menu__item" role="menuitem" on:click={showDestPreviewItemInExplorer}
        >{t("contextGallery.showInExplorer")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={destPreviewCtxMenu.paths.length !== 1 ||
          !destPreviewCtxMenu.thumbDataUrl ||
          !String(destPreviewCtxMenu.thumbDataUrl).startsWith("data:")}
        on:click={() => void copyDestPreviewCtxFullImage()}
        >{t("contextGallery.copyThumb")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={!folder.trim()}
        title={!folder.trim() ? t("contextDestPreview.moveToRouteDisabled") : undefined}
        on:click={() => void moveDestPreviewCtxToRoute()}
        >{t("contextDestPreview.moveToRoute")}{destPreviewCtxMenu.paths.length > 1
          ? ` (${destPreviewCtxMenu.paths.length})`
          : ""}</button
      >
      <div
        class="ctx-menu__submenu-wrap"
        class:ctx-menu__submenu-wrap--left={destPreviewCtxMenu.submenuLeft}
        class:ctx-menu__submenu-wrap--open={$moveDestPanelOpen}
        on:pointerenter={onMoveDestRootEnter}
        on:pointerleave={onMoveDestRootLeave}
      >
        <button
          type="button"
          class="dest-ctx-menu__item ctx-menu__submenu-trigger"
          role="menuitem"
          aria-haspopup="true"
          aria-expanded="false"
          disabled={!destTreeHasTargets}
          title={!destTreeHasTargets ? t("contextGallery.noDestinations") : undefined}
        >
          <span>{t("contextGallery.moveTo")}{destPreviewCtxMenu.paths.length > 1
            ? ` (${destPreviewCtxMenu.paths.length})`
            : ""}</span>
          <span class="ctx-menu__submenu-trigger-mark" aria-hidden="true">{destPreviewCtxMenu.submenuLeft ? "◂" : "▸"}</span>
        </button>
        <div
          class="ctx-menu__submenu ctx-menu__submenu--dest-tree om-panel om-panel--lift"
          role="menu"
          aria-label={t("contextGallery.moveTo")}
        >
          {#if !destTreeHasTargets}
            <div class="ctx-menu__submenu-empty">{t("contextGallery.noDestinations")}</div>
          {:else}
            <div class="dest-move-tree__scroll">
              <DestMoveCtxTree
                nodes={destTree}
                excludePath={previewDestPath}
                onPick={(p) => void moveDestPreviewCtxToDest(p)}
              />
            </div>
          {/if}
        </div>
      </div>
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={destPreviewCtxMenu.paths.length !== 1}
        on:click={openRenameFromDestPreviewCtx}
        >{t("contextGallery.rename")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item"
        role="menuitem"
        disabled={destPreviewCtxMenu.paths.length !== 1}
        on:click={() => void openDestPreviewFileInfoFromCtx()}
        >{t("contextGallery.properties")}</button
      >
      <button
        type="button"
        class="dest-ctx-menu__item dest-ctx-menu__item--danger"
        role="menuitem"
        on:click={askDeleteDestPreviewFromCtx}
        >{t("contextGallery.delete")}{destPreviewCtxMenu.paths.length > 1
          ? ` (${destPreviewCtxMenu.paths.length})`
          : ""}</button
      >
    </div>
  {/if}

  {#if galleryItemCtxMenu || destPreviewCtxMenu || $sectionDestMoveActive}
    <DestMoveFlyoutPortals
      excludePath={destPreviewCtxMenu ? previewDestPath : ""}
      onPick={(p) => {
        const sectionCtx = $sectionDestMoveCtx;
        if (sectionCtx) {
          sectionCtx.onPick(p);
          return;
        }
        if (destPreviewCtxMenu) void moveDestPreviewCtxToDest(p);
        else void moveGalleryItemFromCtxTo(p);
      }}
    />
  {/if}

  {#if moveAsFolderModalOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim overlay--confirm" role="presentation" on:click|self={closeMoveAsFolderModal}>
      <div
        class="modal modal--confirm om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="move-as-folder-title"
        tabindex="-1"
        on:click|stopPropagation
      >
        <header class="modal__head">
          <strong id="move-as-folder-title">{t("confirm.moveAsFolderTitle")}</strong>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("common.close")}
            title={t("common.close")}
            on:click={closeMoveAsFolderModal}>✕</button
          >
        </header>
        <p class="settings-hint">{t("confirm.moveAsFolderDetail")}</p>
        <label class="field-label" for="move-as-folder-input">{t("confirm.moveAsFolderPlaceholder")}</label>
        <input
          id="move-as-folder-input"
          class="om-input"
          type="text"
          bind:value={moveAsFolderDraft}
          on:keydown={(e) => {
            if (e.key === "Enter") void confirmMoveAsFolder();
            if (e.key === "Escape") closeMoveAsFolderModal();
          }}
        />
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={closeMoveAsFolderModal}>{t("common.cancel")}</button>
          <button type="button" class="om-btn om-btn--primary" on:click={() => void confirmMoveAsFolder()}>{t("common.move")}</button>
        </div>
      </div>
    </div>
  {/if}

  {#if renameModalOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim overlay--confirm" role="presentation" on:click|self={closeRenameModal}>
      <div
        class="modal modal--confirm om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-modal-title"
        tabindex="-1"
        on:click|stopPropagation
      >
        <header class="modal__head">
          <strong id="rename-modal-title">{renameModalTitle}</strong>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("common.close")}
            title={t("common.close")}
            on:click={closeRenameModal}>✕</button
          >
        </header>
        <label class="field-label" for="rename-modal-input">{t("contextGallery.renamePlaceholder")}</label>
        <input
          id="rename-modal-input"
          class="om-input"
          type="text"
          bind:value={renameModalDraft}
          on:keydown={(e) => {
            if (e.key === "Enter") void saveRenameModal();
            if (e.key === "Escape") closeRenameModal();
          }}
        />
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={closeRenameModal}>{t("common.cancel")}</button>
          <button type="button" class="om-btn om-btn--primary" on:click={() => void saveRenameModal()}>{t("common.save")}</button>
        </div>
      </div>
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
          <strong id="gallery-file-info-title">{t("contextGallery.propertiesTitle")}</strong>
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
        <div class="gallery-file-info__meta">
          <span
            >{t("contextGallery.typeLabel")}: {formatGalleryMediaTypeLabel(
              galleryFileInfoModal.mediaType,
              galleryFileInfoModal.extension
            )}</span
          >
          {#if galleryFileInfoModal.mimeType}
            <span>{t("contextGallery.mimeLabel")}: {galleryFileInfoModal.mimeType}</span>
          {/if}
          <span>{t("contextGallery.sizeLabel")}: {formatFileSizeBytes(galleryFileInfoModal.sizeBytes)}</span>
          <span>{t("contextGallery.modifiedLabel")}: {galleryFileInfoModal.mtimeIso}</span>
        </div>
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
      bind:galleryUnlimitedBatchSize
      bind:galleryWindowOverscanBefore
      bind:galleryWindowOverscanAfter
      bind:galleryJumpCoreOverscanBefore
      bind:galleryJumpCoreOverscanAfter
      bind:gallerySlidingWindowEnabled
      bind:gallerySlidingWindowMaxItems
      bind:galleryThumbBuildWorkers
      bind:galleryThumbHqWorkers
      bind:galleryThumbHqVisibleSequential
      bind:galleryCompactIndicesAfterMove
      bind:debugLogEnabled
      bind:debugLogFilters
      bind:videoTranscodePreset
      bind:videoTranscodeMaxHeight
      bind:videoTranscodeHw
      bind:settingsThumbPresetIdx
      bind:settingsThumbScaleDraft
      bind:galleryThumbQualityPreset
      bind:thumbGapPx
      bind:thumbImageRadiusPx
      bind:thumbTileRadiusPx
      bind:galleryMasonryTightSpacing
      bind:uiTheme
      bind:showThumbLabels
      bind:thumbFrameVisible
      bind:thumbCardStyle
      bind:keyboardShortcuts
      bind:pinterestMasonry={messPinterestMasonry}
      bind:suggestionsEnabled={messSuggestionsEnabled}
      bind:messScanMaxFiles
      defaultShortcuts={defaultKeyboardShortcuts}
      destTree={destTreeSettingsDraft}
      markerTree={markerTreeSettingsDraft}
      onDestTreeChange={(next) => (destTreeSettingsDraft = next)}
      onMarkerTreeChange={(next) => (markerTreeSettingsDraft = next)}
      onPickDestFolder={pickSettingsDestFolder}
      onPickMarkerFolder={pickSettingsMarkerFolder}
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
      secondaryLabel={confirmDeleteSecondaryLabel}
      onSecondary={confirmDeleteSecondaryAction ? runConfirmSecondary : null}
      onClose={closeConfirmDelete}
      onConfirm={runConfirmDelete}
    />
  {/if}

  {#if uiLoading}
    <LoadOverlay message={uiLoadingMessage || t("load.loading")} />
  {/if}

  <DebugLogPanel />

  <!-- Modal/Overlay Layer -->
  {#if viewMenuOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="view-menu-backdrop" role="presentation" on:click={() => (viewMenuOpen = false)}></div>
  {/if}
  <SidebarMarkers
    bind:routePickerOpen
    bind:pinMarkerOpen
    bind:folder
    markerToolbarItems={markerToolbarVisibleItems}
    {markerToolbarCanGoBack}
    bind:recentUnpinnedFolders
    bind:pinMarkerName
    bind:pinMarkerPath
    {pickGalleryFolder}
    {loadFolder}
    {pickRecentFolder}
    {onPinnedContextMenu}
    onMarkerToolbarBack={() => void markerToolbarBack()}
    onMarkerToolbarOpenFolder={(id) => void navigateMarkerToolbarFolder(id)}
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
    {zoomMiniMapStyle}
    {zoomMiniActive}
    {previewZoomMiniSrc}
    {beginMiniMapPan}
    {moveMiniMapPan}
    {endMiniMapPan}
    bind:zoomCropMarqueeStyle
    bind:destToolbarItems={destToolbarVisibleItems}
    {destToolbarCanGoBack}
    onDestToolbarBack={() => void destToolbarBack()}
    onDestToolbarOpenFolder={(id) => void navigateDestToolbarFolder(id)}
    bind:draggedDestIdx
    bind:previewZoomCanUndoMove
    bind:zoomNavItems
    bind:previewZoomPath
    bind:previewPanX
    bind:previewPanY
    previewPanDrag={previewPanDrag}
    bind:previewFillWidthAlignPending
    bind:zoomStageEl
    bind:zoomVideoEl
    bind:zoomImgEl
    bind:zoomMiniEl
    bind:zoomCarouselEl
    {moveZoomBy}
    {clampPanToStage}
    {alignFillWidthToTop}
    {togglePreviewZoomMode}
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
    {onZoomImageClick}
    {onZoomVideoClick}
    {onZoomVideoMeta}
    {onZoomVideoError}
    onZoomVideoCanPlay={onZoomVideoCanPlay}
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
    previewZoomVideoArmed={previewZoomVideoArmed}
    previewZoomVideoLaunching={previewZoomVideoLaunching}
    previewZoomVideoPlayLocked={previewZoomVideoPlayLocked}
    previewZoomThumbUrl={previewZoomThumbUrl}
    previewZoomVideoPreparing={previewZoomVideoPreparing}
    previewZoomTranscodeProgress={previewZoomTranscodeProgress}
    onZoomVideoPlay={requestZoomVideoPlay}
  />
</main>

