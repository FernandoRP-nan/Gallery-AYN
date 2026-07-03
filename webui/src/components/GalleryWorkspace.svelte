<script lang="ts">
  import { createEventDispatcher, onDestroy, tick } from "svelte";
  import GalleryGrid from "./GalleryGrid.svelte";
  import { bridge, type GalleryItem } from "../lib/api";
  import {
    galleryItems,
    galleryState,
    getGalleryItems,
    getGalleryState,
    mergeGalleryItemsFromApi,
    patchGallerySelection,
    setGalleryItems,
    setGalleryState,
    setGalleryStateFromApi,
    syncSelectedCountFromItems,
    updateGalleryItems,
    applyGalleryWindowItems,
    applyGalleryWindowExpand,
    appendGalleryItemsFromApi,
  } from "../lib/galleryRuntime";
  import { galleryDbg } from "../lib/galleryDebugLog";
  import { getGalleryPerfConfig, effectiveUnlimitedBatchSize, isSmallGalleryTotal } from "../lib/galleryPerfConfig";
  import {
    disposeGalleryThumbs,
    galleryThumbHydrating,
    getGalleryThumbHydrationToken,
    refreshGalleryThumbsForScale,
    requestGalleryThumbHqHydration,
    setGalleryLqLoading,
    setGalleryExpandPending,
    type GalleryThumbHydrateOpts,
  } from "../lib/galleryThumbs";
  import { listGalleryItemsNeedingHq } from "../lib/galleryThumbNeeding";
  import { waitForGalleryTilesReady } from "../lib/galleryThumbDomReady";
  import { setGalleryPointerAnchor } from "../lib/thumbPriority";
  import {
    armGalleryHqJumpGrace,
    getGalleryNavigationGeneration,
    isGalleryNavigationCurrent,
  } from "../lib/gallerySession";
  import { galleryChromeBusy } from "../lib/chromeRemember";
  import { galleryScrolling as galleryScrollingStore } from "../lib/galleryScrollState";
  import {
    countSelectedGalleryItems,
    expandTimelineDayBreaks,
    isGalleryMediaKind,
    isGallerySelectableKind,
  } from "../lib/galleryUtils";
  import { galleryGridCellPx } from "../lib/thumbScale";
  import { t } from "../lib/i18n";

  const dispatch = createEventDispatcher<{
    preview: { path: string };
  }>();

  export let destinationsMode = false;
  export let groupByFolder = false;
  export let galleryTileDragEnabled = false;
  export let timelineView = false;
  export let galleryMasonryView = false;
  export let galleryMasonryTightSpacing = false;
  export let messSuggestionsEnabled = false;
  export let messFolder = "";
  export let galleryFolder = "";
  export let messSuggestionsMasonry = true;
  export let thumbScale = 1;
  export let thumbGapPx = 12;
  export let showThumbLabels = true;
  export let thumbsPerPage = 48;
  export let previewVisible = true;
  export let suppressNextGalleryClick = false;

  export let dragOverSectionPath: string | null = null;
  export let dragOverDestPath: string | null = null;
  export let draggedDestIdx: number | null = null;

  export let navigateToFolder: (path: string, opts?: { pushHistory?: boolean }) => Promise<void>;
  export let openZoomFromGallery: (it: GalleryItem) => void;
  export let onGalleryItemContextMenu: (e: MouseEvent, it: GalleryItem) => void;
  export let onSectionFolderDrop: (e: DragEvent, folder: string) => void;
  export let onFolderTileDrop: (e: DragEvent, folderPath: string) => void = () => {};
  export let onTileDragStart: (e: DragEvent, it: GalleryItem) => void;
  export let openConfirmDelete: (
    title: string,
    msg: string,
    action: () => void,
    opts?: { confirmLabel?: string }
  ) => void;
  export let deleteSelectedGalleryItems: () => void;
  export let openAddDestForm: () => void;
  export let onDestCardClick: (e: MouseEvent, path: string) => void;
  export let onDestContextMenu: (e: MouseEvent, idx: number, mode: string) => void;
  export let onDestChipDragStart: (e: DragEvent, idx: number) => void;
  export let onDestChipDragEnd: () => void;
  export let onDestDrop: (e: DragEvent, path: string, idx: number) => void;
  export let onMessSuggestionMoved: () => void | Promise<void> = () => {};
  export let destToolbarItems: import("../lib/itemTree").DestToolbarItem[] = [];
  export let destToolbarFolderLabel: string | null = null;
  export let destToolbarCanGoBack = false;
  export let onDestToolbarBack: () => void;
  export let onDestToolbarOpenFolder: (folderId: string) => void;
  export let destTree: import("../lib/itemTree").TreeNode[] = [];
  export let destTreeHasTargets = false;
  export let onMoveSectionFolderToDest: (folderPath: string, destPath: string, sectionLabel: string) => void = () => {};
  export let onGroupSelectionInFolder: () => void = () => {};

  export let galleryScrollEl: HTMLDivElement | null = null;
  export let galleryGridEl: HTMLDivElement | null = null;
  let galleryGrid: GalleryGrid | undefined;

  async function snapScrollAfterJump(targetIndex: number) {
    await tick();
    await tick();
    galleryGrid?.scrollToMediaIndex(targetIndex, "center");
  }

  export let galleryRangeSelecting = false;
  export let galleryRangeSuppressClick = false;
  export let galleryCursorPath: string | null = null;
  export let galleryKeyboardNavHintActive = false;

  let galleryScrolling = false;
  let galleryScrollIdleTimer: ReturnType<typeof setTimeout> | null = null;
  export let galleryLoadingMore = false;
  let galleryAutoLoadRunId = 0;
  let galleryActionBusy = false;

  let galleryRangeAnchorPath: string | null = null;
  let galleryRangeMode: "select" | "deselect" = "select";
  let galleryRangeBaseSelectedPaths: string[] = [];
  let galleryRangeBaseSelectedSet: Set<string> | null = null;
  let galleryRangeDraftSelectedPaths: string[] | null = null;
  let galleryRangeDraftSelectedSet: Set<string> | null = null;
  let galleryRangeCurrentPath: string | null = null;
  let galleryRangePendingPath: string | null = null;
  let galleryRangeRaf: number | null = null;

  let gridCellPx = 120;
  let frozenGalleryState = $galleryState;

  let galleryAutoLoadTimer: ReturnType<typeof setTimeout> | null = null;
  let galleryHydratingPrev = false;
  const VIEWPORT_FILL_GUARD = 48;

  function loadedContentFillsViewport(): boolean {
    if (!galleryScrollEl) return true;
    const loaded = Number($galleryState?.endIndex ?? 0);
    const total = Number($galleryState?.total ?? 0);
    if (loaded >= total) return true;
    const innerW = Math.max(0, galleryScrollEl.clientWidth - 16);
    const cols = Math.max(1, Math.floor((innerW + thumbGapPx) / (gridCellPx + thumbGapPx)));
    const rowH = gridCellPx + thumbGapPx;
    const rowsNeeded = Math.ceil(galleryScrollEl.clientHeight / rowH) + 2;
    return loaded >= Math.min(total, rowsNeeded * cols);
  }

  function viewportNeedsMoreContent(): boolean {
    if (!galleryScrollEl) return false;
    if (thumbsPerPage !== 0 || Number($galleryState?.total ?? 0) <= 0) {
      return galleryScrollEl.scrollHeight <= galleryScrollEl.clientHeight + 40;
    }
    return galleryHasMoreNow() && !loadedContentFillsViewport();
  }

  async function fillViewportIfNeeded() {
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    if (!galleryScrollEl) return;
    const runId = ++galleryAutoLoadRunId;
    let guard = 0;
    while (
      runId === galleryAutoLoadRunId &&
      thumbsPerPage === 0 &&
      galleryHasMoreNow() &&
      viewportNeedsMoreContent() &&
      guard < VIEWPORT_FILL_GUARD
    ) {
      guard++;
      const progressed = await loadMoreGalleryBatch();
      if (!progressed) break;
      await tick();
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
  }

  async function maybeAutoLoadMoreForViewport() {
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    if (!galleryScrollEl) return;
    if (viewportNeedsMoreContent()) {
      await loadMoreGalleryBatch();
    }
  }

  async function autoLoadUnlimitedBatches() {
    await fillViewportIfNeeded();
  }

  $: if (
    thumbsPerPage === 0 &&
    galleryHasMoreNow() &&
    !galleryLoadingMore &&
    $galleryItems.length > 0 &&
    galleryScrollEl
  ) {
    if (galleryAutoLoadTimer !== null) clearTimeout(galleryAutoLoadTimer);
    galleryAutoLoadTimer = setTimeout(() => {
      galleryAutoLoadTimer = null;
      void fillViewportIfNeeded();
    }, 120);
  }

  $: if (gridCellPx && galleryScrollEl && thumbsPerPage === 0 && $galleryItems.length > 0) {
    if (galleryAutoLoadTimer !== null) clearTimeout(galleryAutoLoadTimer);
    galleryAutoLoadTimer = setTimeout(() => {
      galleryAutoLoadTimer = null;
      void fillViewportIfNeeded();
    }, 160);
  }

  $: if (galleryMasonryView && galleryScrollEl && thumbsPerPage === 0 && $galleryItems.length > 0) {
    if (galleryAutoLoadTimer !== null) clearTimeout(galleryAutoLoadTimer);
    galleryAutoLoadTimer = setTimeout(() => {
      galleryAutoLoadTimer = null;
      void fillViewportIfNeeded();
    }, 180);
  }

  $: {
    const hydrating = $galleryThumbHydrating;
    if (galleryHydratingPrev && !hydrating) {
      void fillViewportIfNeeded();
    }
    galleryHydratingPrev = hydrating;
  }

  function syncGalleryChromeBusy(scrolling: boolean, loading: boolean, hydrating: boolean) {
    galleryChromeBusy.set(scrolling || loading || hydrating);
  }

  $: syncGalleryChromeBusy(galleryScrolling, galleryLoadingMore, $galleryThumbHydrating);
  $: setGalleryLqLoading(galleryLoadingMore);

  $: gridCellTargetPx = galleryGridCellPx(thumbScale);
  $: gridCellPx = Math.max(72, Number(gridCellTargetPx.toFixed(2)));
  $: useFullVirtualScroll =
    thumbsPerPage === 0 && Number($galleryState?.total ?? 0) > 0;
  $: galleryGridItems = expandTimelineDayBreaks(
    $galleryItems,
    timelineView && !useFullVirtualScroll,
    gridCellPx
  );
  $: liveSelectedCount = countSelectedGalleryItems($galleryItems);

  $: galleryHasSelection = liveSelectedCount > 0;

  $: galleryFloatChromeActive =
    destinationsMode || galleryRangeSelecting || galleryHasSelection;

  $: if (!galleryScrolling) {
    frozenGalleryState = { ...$galleryState, selectedCount: liveSelectedCount };
  }

  function galleryHasMoreNow(): boolean {
    if (thumbsPerPage !== 0) return false;
    return Number($galleryState?.endIndex ?? 0) < Number($galleryState?.total ?? 0);
  }

  function galleryThumbHydrateOpts(): GalleryThumbHydrateOpts {
    return {
      cursorPath: galleryCursorPath,
      scrollContainer: galleryScrollEl,
      pathOrder: getGalleryItems().map((x) => x.path),
    };
  }

  async function hydrateAfterWindowReady() {
    await tick();
    await waitForGalleryTilesReady(galleryScrollEl, 1);
    if (galleryLoadingMore) return;
    void requestGalleryThumbHqHydration(
      thumbScale,
      getGalleryThumbHydrationToken(),
      galleryThumbHydrateOpts()
    );
  }

  function requestHqAfterAppend() {
    armGalleryHqJumpGrace(2500);
    void requestGalleryThumbHqHydration(
      thumbScale,
      getGalleryThumbHydrationToken(),
      galleryThumbHydrateOpts()
    );
  }

  function capLqExpansionTarget(target: number, loadedEnd: number): number {
    const total = Number($galleryState?.total ?? 0);
    const batch = effectiveUnlimitedBatchSize(total);
    const leadMult = isSmallGalleryTotal(total) ? 3 : 2;
    return Math.min(target, loadedEnd + batch * leadMult);
  }

  async function hydrateVisibleThumbsAfterScrollIdle() {
    const needing = listGalleryItemsNeedingHq(getGalleryItems());
    if (needing.length === 0) return;
    await requestGalleryThumbHqHydration(
      thumbScale,
      getGalleryThumbHydrationToken(),
      galleryThumbHydrateOpts()
    );
  }

  function onGalleryScrollPointerMove(e: PointerEvent) {
    setGalleryPointerAnchor(e.clientX, e.clientY);
  }

  async function loadMoreGalleryBatch() {
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return false;
    const navGen = getGalleryNavigationGeneration();
    galleryLoadingMore = true;
    try {
      const beforeEnd = Number($galleryState?.endIndex ?? 0);
      const out = await bridge.galleryLoadMore();
      if (!isGalleryNavigationCurrent(navGen)) return false;
      const extra = Array.isArray(out?.items) ? out.items : [];
      if (out?.replaceWindow) {
        if (extra.length > 0 || out?.state) {
          applyGalleryWindowItems(extra, out?.state);
          void hydrateAfterWindowReady();
        }
      } else if (extra.length > 0) {
        updateGalleryItems((items) => [...items, ...extra]);
        void requestGalleryThumbHqHydration(
          thumbScale,
          getGalleryThumbHydrationToken(),
          galleryThumbHydrateOpts()
        );
      }
      if (out?.state) setGalleryStateFromApi(out.state);
      else if (!out?.replaceWindow) syncSelectedCountFromItems();
      const afterEnd = Number(getGalleryState()?.endIndex ?? 0);
      return afterEnd > beforeEnd || extra.length > 0;
    } finally {
      galleryLoadingMore = false;
    }
  }

  export function cancelBackgroundWork() {
    galleryAutoLoadRunId++;
    loadUntilGeneration++;
    galleryLoadingMore = false;
    setGalleryExpandPending(false);
    loadUntilPending = -1;
    loadUntilCoalesceTarget = -1;
    if (loadUntilDebounceTimer !== null) {
      clearTimeout(loadUntilDebounceTimer);
      loadUntilDebounceTimer = null;
    }
  }

  /** Invalida cargas por scroll en curso (arrastre rápido); no cancela salto por rail. */
  export function cancelScrollLoads() {
    loadUntilGeneration++;
    loadUntilPending = -1;
    loadUntilCoalesceTarget = -1;
    if (loadUntilDebounceTimer !== null) {
      clearTimeout(loadUntilDebounceTimer);
      loadUntilDebounceTimer = null;
    }
  }

  async function expandJumpWindow(
    targetIndex: number,
    navGen: number,
    requestGen: number,
  ) {
    if (!isGalleryNavigationCurrent(navGen)) return;
    if (requestGen !== loadUntilGeneration) return;
    setGalleryExpandPending(true);
    galleryDbg("load_lq", "expansión LQ post-salto", { targetIndex });
    try {
      const out = await bridge.galleryLoadUntilIndex(targetIndex, false, true);
      if (!isGalleryNavigationCurrent(navGen)) return;
      if (requestGen !== loadUntilGeneration) return;
      const prepend = Array.isArray(out?.prependItems) ? out.prependItems : [];
      const append = Array.isArray(out?.appendItems) ? out.appendItems : [];
      const extra = Array.isArray(out?.items) ? out.items : [];
      galleryDbg("load_lq", "expansión LQ recibida", {
        count: extra.length,
        prependCount: prepend.length,
        appendCount: append.length,
        incremental: Boolean(out?.windowExpandIncremental),
        replaceWindow: Boolean(out?.replaceWindow),
        windowStart: out?.state?.windowStart,
        endIndex: out?.state?.endIndex,
        buildMs: out?.timing?.buildMs,
        windowPhase: out?.windowPhase ?? "expand",
      });
      if (out?.windowExpandIncremental && (prepend.length > 0 || append.length > 0)) {
        galleryGrid?.suppressScrollPreserve(1500);
        applyGalleryWindowExpand(prepend, append, out?.state);
        await tick();
        await tick();
        await snapScrollAfterJump(targetIndex);
        armGalleryHqJumpGrace();
        void hydrateAfterWindowReady();
      } else if (out?.replaceWindow && extra.length > 0) {
        applyGalleryWindowItems(extra, out?.state);
        await tick();
        armGalleryHqJumpGrace();
        requestHqAfterAppend();
      } else if (out?.state) {
        setGalleryStateFromApi(out.state);
      }
    } catch {
      /* La ventana núcleo sigue usable */
    } finally {
      setGalleryExpandPending(false);
    }
  }

  async function loadUntilGalleryIndex(
    targetIndex: number,
    opts: { jump?: boolean } = {}
  ) {
    if (thumbsPerPage !== 0) return;
    const jump = Boolean(opts.jump);
    const requestGen = loadUntilGeneration;
    const total = Number($galleryState?.total ?? 0);
    const loaded = Number($galleryState?.endIndex ?? 0);
    const windowStart = Number($galleryState?.windowStart ?? 0);
    const target = Math.max(0, Math.min(total - 1, targetIndex));

    if (total <= 0) return;
    const needsBackward = windowStart > 0 && target < windowStart;
    if (loaded >= total && !jump && !needsBackward) return;
    if (windowStart > 0 && !jump && target >= windowStart && target < loaded) return;
    if (windowStart === 0 && !jump && target < loaded) return;

    let apiTarget = target;
    let apiJump = jump;
    if (jump) {
      apiTarget = target;
      apiJump = true;
    } else if (windowStart > 0 && target < windowStart) {
      // Expansión hacia atrás: pedir el índice visible, no prefetch hacia adelante.
      apiTarget = target;
      apiJump = false;
    } else {
      apiTarget = Math.min(total - 1, Math.max(target, loaded) + 128);
      apiTarget = capLqExpansionTarget(apiTarget, loaded);
      apiJump = false;
    }

    if (!apiJump && galleryLoadingMore) {
      loadUntilPending = Math.max(loadUntilPending, target);
      return;
    }
    const navGen = getGalleryNavigationGeneration();
    galleryLoadingMore = true;
    galleryDbg("load_lq", jump ? "carga LQ (salto)" : "carga LQ (expansión)", {
      targetIndex: target,
      apiTarget,
      apiJump,
      windowStart,
      loadedEnd: loaded,
      total,
    });
    try {
      const out = await bridge.galleryLoadUntilIndex(apiTarget, apiJump);
      if (!isGalleryNavigationCurrent(navGen)) return;
      if (requestGen !== loadUntilGeneration) return;
      const extra = Array.isArray(out?.items) ? out.items : [];
      const prependInc = Array.isArray(out?.prependItems) ? out.prependItems : [];
      const appendInc = Array.isArray(out?.appendItems) ? out.appendItems : [];
      galleryDbg("load_lq", "tanda LQ recibida", {
        count: extra.length,
        prependCount: prependInc.length,
        appendCount: appendInc.length,
        incremental: Boolean(out?.windowExpandIncremental),
        replaceWindow: Boolean(out?.replaceWindow),
        windowStart: out?.state?.windowStart ?? windowStart,
        endIndex: out?.state?.endIndex ?? loaded,
        total: out?.state?.total ?? total,
        buildMs: out?.timing?.buildMs,
        windowPhase: out?.windowPhase ?? (jump ? "core" : "scroll_append"),
        windowExpandPending: Boolean(out?.windowExpandPending),
      });
      if (
        out?.windowExpandIncremental &&
        (prependInc.length > 0 || appendInc.length > 0)
      ) {
        galleryGrid?.suppressScrollPreserve(1500);
        applyGalleryWindowExpand(prependInc, appendInc, out?.state);
        requestHqAfterAppend();
      } else if (out?.replaceWindow) {
        if (extra.length > 0) {
          applyGalleryWindowItems(extra, out?.state);
          if (jump) {
            await snapScrollAfterJump(target);
            armGalleryHqJumpGrace();
            if (out?.windowExpandPending) {
              void expandJumpWindow(target, navGen, requestGen);
            } else {
              void hydrateAfterWindowReady();
            }
          } else {
            requestHqAfterAppend();
          }
        } else if (out?.state) {
          setGalleryStateFromApi(out.state);
        }
      } else if (extra.length > 0) {
        galleryGrid?.suppressScrollPreserve();
        appendGalleryItemsFromApi(extra, out?.state);
        requestHqAfterAppend();
      } else if (out?.state) {
        setGalleryStateFromApi(out.state);
      }
    } catch (err) {
      galleryDbg("load_lq", "error carga LQ", {
        message: err instanceof Error ? err.message : String(err),
      });
    } finally {
      galleryLoadingMore = false;
      if (loadUntilPending >= 0) {
        const retryTarget = loadUntilPending;
        loadUntilPending = -1;
        void loadUntilGalleryIndex(retryTarget, { jump: false });
        return;
      }
      if (loadUntilCoalesceTarget >= 0) {
        const coalesced = loadUntilCoalesceTarget;
        loadUntilCoalesceTarget = -1;
        if (loadUntilDebounceTimer !== null) {
          clearTimeout(loadUntilDebounceTimer);
          loadUntilDebounceTimer = null;
        }
        const loadedNow = Number(getGalleryState()?.endIndex ?? 0);
        if (coalesced >= loadedNow) {
          void loadUntilGalleryIndex(coalesced, { jump: false });
          return;
        }
      }
      if (!jump) {
        void tick().then(() => galleryGrid?.nudgeViewportLoad());
      }
    }
  }

  let loadUntilGeneration = 0;
  let loadUntilPending = -1;
  let loadUntilCoalesceTarget = -1;
  let loadUntilDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  function scheduleLoadUntilGalleryIndex(targetIndex: number, jump = false, urgent = false) {
    if (targetIndex < 0) return;
    if (jump) {
      loadUntilGeneration += 1;
      loadUntilPending = -1;
      loadUntilCoalesceTarget = -1;
      if (loadUntilDebounceTimer !== null) {
        clearTimeout(loadUntilDebounceTimer);
        loadUntilDebounceTimer = null;
      }
      void loadUntilGalleryIndex(targetIndex, { jump: true });
      return;
    }
    loadUntilCoalesceTarget = Math.max(loadUntilCoalesceTarget, targetIndex);
    const loaded = Number(getGalleryState()?.endIndex ?? 0);
    const total = Number(getGalleryState()?.total ?? 0);
    const batch = effectiveUnlimitedBatchSize(total);
    const urgentScroll =
      urgent ||
      (isSmallGalleryTotal(total) && targetIndex >= loaded + Math.max(12, batch >> 1));
    if (urgentScroll) {
      if (loadUntilDebounceTimer !== null) {
        clearTimeout(loadUntilDebounceTimer);
        loadUntilDebounceTimer = null;
      }
      const t = loadUntilCoalesceTarget;
      loadUntilCoalesceTarget = -1;
      if (t >= loaded) void loadUntilGalleryIndex(t, { jump: false });
      return;
    }
    if (loadUntilDebounceTimer !== null) clearTimeout(loadUntilDebounceTimer);
    const debounceMs = isSmallGalleryTotal(total) ? 80 : 220;
    loadUntilDebounceTimer = setTimeout(() => {
      loadUntilDebounceTimer = null;
      const t = loadUntilCoalesceTarget;
      loadUntilCoalesceTarget = -1;
      if (t >= 0) void loadUntilGalleryIndex(t, { jump: false });
    }, debounceMs);
  }

  $: layoutMode = String($galleryState?.layoutMode ?? "flat");
  $: layoutSpans = Array.isArray($galleryState?.layoutSpans)
    ? ($galleryState.layoutSpans as import("../lib/galleryFullVirtualLayout").GalleryLayoutSpan[])
    : [];
  $: totalMediaCount = Number($galleryState?.total ?? 0);
  $: galleryWindowStart = Number($galleryState?.windowStart ?? 0);
  $: unlimitedScroll = thumbsPerPage === 0;

  async function onGalleryScroll(e: Event) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    galleryScrolling = true;
    galleryScrollingStore.set(true);
    if (galleryScrollIdleTimer !== null) clearTimeout(galleryScrollIdleTimer);
    galleryScrollIdleTimer = setTimeout(() => {
      galleryScrolling = false;
      galleryScrollingStore.set(false);
      galleryScrollIdleTimer = null;
      void hydrateVisibleThumbsAfterScrollIdle();
    }, 320);
    if (thumbsPerPage !== 0 || galleryLoadingMore || !galleryHasMoreNow()) return;
    // Con scroll virtual, GalleryGrid dispara loadUntil; evitar loadMore duplicado.
    if (unlimitedScroll && totalMediaCount > 0) return;
    const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 280;
    if (!nearBottom) return;
    await loadMoreGalleryBatch();
  }

  function emitPreview(path: string) {
    dispatch("preview", { path });
  }

  export function resetGalleryInteractionState() {
    if (galleryRangeRaf !== null) {
      cancelAnimationFrame(galleryRangeRaf);
      galleryRangeRaf = null;
    }
    galleryRangeSelecting = false;
    galleryRangeSuppressClick = false;
    galleryRangeAnchorPath = null;
    galleryRangeBaseSelectedPaths = [];
    galleryRangeBaseSelectedSet = null;
    galleryRangeDraftSelectedPaths = null;
    galleryRangeDraftSelectedSet = null;
    galleryRangeCurrentPath = null;
    galleryRangePendingPath = null;
    galleryActionBusy = false;
  }

  async function openFolderTile(it: GalleryItem) {
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
      await navigateToFolder(it.path, { pushHistory: true });
    } finally {
      galleryActionBusy = false;
    }
  }

  async function syncEditSelectionDelta(addPaths: string[], removePaths: string[]) {
    if (!destinationsMode) return;
    if (addPaths.length === 0 && removePaths.length === 0) return;
    try {
      const out = await bridge.galleryApplySelectionDelta(addPaths, removePaths);
      mergeGalleryItemsFromApi(out.items, out.state, { preserveSelection: true });
    } catch {
      /* selección local ya aplicada */
    }
  }

  async function clickGalleryItem(it: GalleryItem) {
    if (galleryRangeSuppressClick) return;
    if (suppressNextGalleryClick) return;
    galleryKeyboardNavHintActive = false;

    if (it.kind === "section" || it.kind === "day_break") return;

    if (it.kind === "folder_up") {
      await openFolderTile(it);
      return;
    }

    if (it.kind === "folder") {
      if (destinationsMode) {
        if (galleryActionBusy) return;
        galleryActionBusy = true;
        try {
          const nextSelected = !it.selected;
          patchGallerySelection(
            (items) => items.map((x) => (x.path === it.path ? { ...x, selected: nextSelected } : x)),
            "selection:click_toggle",
            { path: it.path, selected: nextSelected, kind: it.kind },
          );
          void syncEditSelectionDelta(nextSelected ? [it.path] : [], nextSelected ? [] : [it.path]);
          galleryCursorPath = it.path;
        } finally {
          galleryActionBusy = false;
        }
        return;
      }
      await openFolderTile(it);
      return;
    }

    if (!isGalleryMediaKind(it.kind)) return;
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
      if (destinationsMode) {
        const nextSelected = !it.selected;
        patchGallerySelection(
          (items) => items.map((x) => (x.path === it.path ? { ...x, selected: nextSelected } : x)),
          "selection:click_toggle",
          { path: it.path, selected: nextSelected, kind: it.kind },
        );
        void syncEditSelectionDelta(nextSelected ? [it.path] : [], nextSelected ? [] : [it.path]);
        emitPreview(it.path);
        galleryCursorPath = it.path;
        return;
      }

      if (!previewVisible) {
        openZoomFromGallery(it);
        return;
      }
      emitPreview(it.path);
      galleryCursorPath = it.path;
    } finally {
      galleryActionBusy = false;
    }
  }

  function getVisibleSelectablePaths(): string[] {
    return $galleryItems.filter((x) => isGallerySelectableKind(x.kind)).map((x) => x.path);
  }

  function isGalleryTileSelected(it: GalleryItem): boolean {
    if (!isGallerySelectableKind(it.kind)) return false;
    if (!galleryFloatChromeActive) return false;
    if (galleryRangeSelecting && galleryRangeDraftSelectedSet) {
      return galleryRangeDraftSelectedSet.has(it.path);
    }
    return Boolean(it.selected);
  }

  function applyGalleryRangeSelection(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const selectablePaths = getVisibleSelectablePaths();
    const a = selectablePaths.indexOf(fromPath);
    const b = selectablePaths.indexOf(toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const draft = new Set(galleryRangeBaseSelectedSet ?? []);
    for (let i = lo; i <= hi; i++) {
      const p = selectablePaths[i];
      if (!p) continue;
      if (mode === "select") draft.add(p);
      else draft.delete(p);
    }
    const next = [...draft];
    galleryRangeDraftSelectedPaths = next;
    galleryRangeDraftSelectedSet = new Set(next);
    galleryRangeCurrentPath = toPath;
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
    if (!destinationsMode || !isGallerySelectableKind(it.kind)) return;
    if (e.ctrlKey) return;
    e.preventDefault();
    const baseSelected = $galleryItems
      .filter((x) => isGallerySelectableKind(x.kind) && x.selected)
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
    const previewPath = galleryRangeCurrentPath ?? galleryRangeAnchorPath;
    const draft = new Set(galleryRangeDraftSelectedPaths ?? galleryRangeBaseSelectedPaths);
    const base = new Set(galleryRangeBaseSelectedPaths);
    const addPaths = [...draft].filter((p) => !base.has(p));
    const removePaths = [...base].filter((p) => !draft.has(p));
    if (galleryRangeRaf !== null) {
      cancelAnimationFrame(galleryRangeRaf);
      galleryRangeRaf = null;
    }

    if (addPaths.length > 0 || removePaths.length > 0) {
      patchGallerySelection(
        (items) => items.map((x) => (isGallerySelectableKind(x.kind) ? { ...x, selected: draft.has(x.path) } : x)),
        "selection:range",
        { addCount: addPaths.length, removeCount: removePaths.length },
      );
      void syncEditSelectionDelta(addPaths, removePaths);
    }
    if (destinationsMode && previewPath) {
      emitPreview(previewPath);
    }

    galleryRangeSelecting = false;
    galleryRangeAnchorPath = null;
    galleryRangeBaseSelectedPaths = [];
    galleryRangeBaseSelectedSet = null;
    galleryRangeDraftSelectedPaths = null;
    galleryRangeDraftSelectedSet = null;
    galleryRangeCurrentPath = null;
    galleryRangePendingPath = null;
    galleryRangeSuppressClick = true;
    setTimeout(() => {
      galleryRangeSuppressClick = false;
    }, 0);
  }

  const selectPage = async () => {
    const out = await bridge.gallerySelectPage();
    mergeGalleryItemsFromApi(out.items, out.state, { preserveSelection: false });
    patchGallerySelection(
      (items) => items.map((x) => (x.kind === "folder" ? { ...x, selected: true } : x)),
      "selection:select_page",
    );
    if (destinationsMode) {
      const items = getGalleryItems();
      const last = [...items].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
      if (last?.path) emitPreview(last.path);
    }
  };

  const clearSelection = async () => {
    patchGallerySelection(
      (items) => items.map((x) => (isGallerySelectableKind(x.kind) ? { ...x, selected: false } : x)),
      "selection:clear",
    );
    galleryState.update((s) => ({ ...s, selectedCount: 0 }));
    try {
      await bridge.galleryClearSelection();
    } catch {
      /* local ya limpio */
    }
  };

  const invertSelection = async () => {
    try {
      const out = await bridge.galleryInvertSelection();
      mergeGalleryItemsFromApi(out.items, out.state, { preserveSelection: false });
    } catch {
      patchGallerySelection(
        (items) => items.map((x) => (isGallerySelectableKind(x.kind) ? { ...x, selected: !x.selected } : x)),
        "selection:invert",
      );
    }
    if (destinationsMode) {
      const items = getGalleryItems();
      const last = [...items].reverse().find((x) => isGalleryMediaKind(x.kind) && Boolean(x.selected));
      if (last?.path) emitPreview(last.path);
    }
  };

  export async function refreshThumbsAtScale(scale: number) {
    await refreshGalleryThumbsForScale(scale, galleryThumbHydrateOpts());
  }

  export async function afterGalleryPayloadLoaded(items: GalleryItem[], scale: number) {
    await tick();
    await waitForGalleryTilesReady(galleryScrollEl, 1);
    // Breve pausa para que el bridge/PyWebView esté listo tras cargas LQ pesadas.
    await new Promise<void>((r) => setTimeout(r, 320));
    if (galleryLoadingMore) return;
    await requestGalleryThumbHqHydration(
      scale,
      getGalleryThumbHydrationToken(),
      galleryThumbHydrateOpts()
    );
    if (thumbsPerPage === 0) {
      await tick();
      void maybeAutoLoadMoreForViewport();
      void autoLoadUnlimitedBatches();
    }
  }

  export async function afterGalleryMoveDelta(items: GalleryItem[], scale: number) {
    await tick();
    const needingHq = listGalleryItemsNeedingHq(items);
    if (needingHq.length > 0) {
      void requestGalleryThumbHqHydration(
        scale,
        getGalleryThumbHydrationToken(),
        galleryThumbHydrateOpts()
      );
    }
    if (thumbsPerPage === 0) {
      await tick();
      void maybeAutoLoadMoreForViewport();
    }
  }

  onDestroy(() => {
    if (galleryScrollIdleTimer !== null) clearTimeout(galleryScrollIdleTimer);
    if (galleryAutoLoadTimer !== null) clearTimeout(galleryAutoLoadTimer);
    if (loadUntilDebounceTimer !== null) clearTimeout(loadUntilDebounceTimer);
    loadUntilGeneration++;
    galleryScrollingStore.set(false);
    galleryChromeBusy.set(false);
    disposeGalleryThumbs();
  });
</script>

<svelte:window
  on:pointermove={onGalleryRangePointerMove}
  on:pointerup={() => void endGalleryRangeSelection()}
  on:pointercancel={() => void endGalleryRangeSelection()}
/>

<div class="gallery-workspace">
  <GalleryGrid
    bind:this={galleryGrid}
    {galleryGridItems}
    bind:gridCellPx
    bind:thumbGapPx
    bind:dragOverSectionPath
    bind:galleryKeyboardNavHintActive
    bind:galleryCursorPath
    bind:galleryRangeSelecting
    bind:galleryRangeSuppressClick
    bind:showThumbLabels
    galleryState={frozenGalleryState}
    selectionCount={liveSelectedCount}
    {destToolbarItems}
    {destToolbarFolderLabel}
    {destToolbarCanGoBack}
    {onDestToolbarBack}
    {onDestToolbarOpenFolder}
    bind:dragOverDestPath
    bind:draggedDestIdx
    bind:galleryScrollEl
    bind:galleryGridEl
    {galleryFloatChromeActive}
    galleryBusy={$galleryChromeBusy}
    {galleryScrolling}
    {galleryRangeDraftSelectedSet}
    {onGalleryScroll}
    onGalleryScrollPointerMove={onGalleryScrollPointerMove}
    {onSectionFolderDrop}
    {onFolderTileDrop}
    {navigateToFolder}
    {isGalleryTileSelected}
    {isGalleryMediaKind}
    {onGalleryTilePointerDown}
    {onGalleryTilePointerEnter}
    {onTileDragStart}
    clickItem={clickGalleryItem}
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
    {galleryTileDragEnabled}
    {galleryMasonryView}
    {galleryMasonryTightSpacing}
    {unlimitedScroll}
    {layoutMode}
    {layoutSpans}
    {totalMediaCount}
    {galleryWindowStart}
    galleryLoadedEnd={Number($galleryState?.endIndex ?? 0)}
    onRequestLoadUntilIndex={scheduleLoadUntilGalleryIndex}
    onCancelBackgroundLoad={cancelBackgroundWork}
    onCancelScrollLoads={cancelScrollLoads}
    {messSuggestionsEnabled}
    messFolder={messFolder}
    galleryTargetFolder={galleryFolder}
    messSuggestionsMasonry={messSuggestionsMasonry}
    onMessSuggestionMoved={() => void onMessSuggestionMoved()}
    {destTree}
    {destTreeHasTargets}
    {onMoveSectionFolderToDest}
    {onGroupSelectionInFolder}
  />
</div>

<style>
  .gallery-workspace {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1 1 auto;
    height: 100%;
  }
</style>
