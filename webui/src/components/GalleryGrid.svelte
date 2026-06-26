<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { t } from "../lib/i18n";
  import {
    buildGalleryVirtualLayout,
    getVisibleLayoutEntries,
    type VirtualLayoutEntry,
  } from "../lib/galleryVirtualLayout";
  import {
    buildGalleryFullVirtualLayout,
    buildMediaIndexMap,
    estimateTargetMediaIndex,
    virtualLoadedBottomY,
    virtualLoadedTopY,
    type GalleryLayoutMode,
    type GalleryLayoutSpan,
    type GalleryFullVirtualLayout,
  } from "../lib/galleryFullVirtualLayout";
  import { buildGalleryFullMasonryVirtualLayout } from "../lib/galleryFullMasonryVirtualLayout";
  import { seedMasonryHeightsFromItems } from "../lib/galleryMasonryHeightCache";
  import { masonryMaxHeightPx } from "../lib/galleryMasonryLayoutMetrics";
  import GalleryScrollGutter from "./GalleryScrollGutter.svelte";
  import {
    buildMasonrySegments,
    computeMasonryColumnCount,
  } from "../lib/galleryMasonryLayout";
  import GalleryGridItem from "./GalleryGridItem.svelte";
  import GalleryMessSuggestions from "./GalleryMessSuggestions.svelte";
  import DestToolbar from "./DestToolbar.svelte";
  import type { DestToolbarItem } from "../lib/itemTree";
  import { galleryDbg } from "../lib/galleryDebugLog";
  import { getGalleryPerfConfig } from "../lib/galleryPerfConfig";

  export let galleryGridItems: any[];
  export let gridCellPx: number;
  export let thumbGapPx: number;
  export let dragOverSectionPath: string | null;
  export let galleryKeyboardNavHintActive: boolean;
  export let galleryCursorPath: string | null;
  export let galleryRangeSelecting: boolean;
  export let galleryRangeSuppressClick: boolean;
  export let showThumbLabels: boolean;
  export let selectionCount = 0;
  export let destToolbarItems: DestToolbarItem[] = [];
  export let destToolbarFolderLabel: string | null = null;
  export let destToolbarCanGoBack = false;
  export let dragOverDestPath: string | null;
  export let draggedDestIdx: number | null = null;
  export let destinationsMode: boolean;
  export let galleryFloatChromeActive = false;
  export let galleryBusy = false;
  export let galleryScrolling = false;
  export let galleryRangeDraftSelectedSet: Set<string> | null = null;
  export let galleryScrollEl: HTMLDivElement | null = null;
  export let galleryGridEl: HTMLDivElement | null = null;

  let scrollGutter: GalleryScrollGutter | null = null;
  const GALLERY_GRID_EDGE_PAD_PX = 8;
  const SCROLL_RAIL_HIT_PX = 72;
  const SCROLLBAR_DRAG_ZONE_PX = 18;
  const DEST_BAR_RESERVE_PX = 56;

  export let onGalleryScroll: (e: UIEvent) => void;
  export let onGalleryScrollPointerMove: (e: PointerEvent) => void = () => {};
  export let onSectionFolderDrop: (e: DragEvent, folder: string) => void;
  export let navigateToFolder: (path: string, opts: any) => void;
  export let isGalleryMediaKind: (kind: string) => boolean;
  export let onGalleryTilePointerDown: (e: PointerEvent, it: any) => void;
  export let onGalleryTilePointerEnter: (path: string) => void;
  export let onTileDragStart: (e: DragEvent, it: any) => void;
  export let clickItem: (it: any) => void;
  export let openZoomFromGallery: (it: any) => void;
  export let onGalleryItemContextMenu: (e: MouseEvent, it: any) => void;
  export let selectPage: () => void;
  export let clearSelection: () => void;
  export let invertSelection: () => void;
  export let openConfirmDelete: (title: string, msg: string, action: () => void) => void;
  export let deleteSelectedGalleryItems: () => void;
  export let onDestToolbarBack: () => void;
  export let onDestToolbarOpenFolder: (folderId: string) => void;
  export let openAddDestForm: () => void;
  export let onDestCardClick: (e: MouseEvent, path: string) => void;
  export let onDestContextMenu: (e: MouseEvent, idx: number, mode: string) => void;
  export let onDestChipDragStart: (e: DragEvent, idx: number) => void;
  export let onDestChipDragEnd: () => void;
  export let onDestDrop: (e: DragEvent, path: string, idx: number) => void;

  export let messSuggestionsEnabled = false;
  export let messFolder = "";
  export let galleryTargetFolder = "";
  export let messSuggestionsMasonry = true;
  export let galleryMasonryView = false;
  export let unlimitedScroll = false;
  export let layoutMode: GalleryLayoutMode = "flat";
  export let layoutSpans: GalleryLayoutSpan[] = [];
  export let totalMediaCount = 0;
  export let galleryWindowStart = 0;
  export let galleryLoadedEnd = 0;
  export let onRequestLoadUntilIndex: (targetIndex: number, jump?: boolean) => void = () => {};
  export let onCancelBackgroundLoad: () => void = () => {};
  export let onCancelScrollLoads: () => void = () => {};
  export let onMessSuggestionMoved: () => void = () => {};

  const SCROLL_LOAD_IDLE_MS = 400;
  const SCROLL_STABLE_MS = 280;
  const WINDOW_JUMP_MARGIN = 128;
  /** Precarga hacia adelante mientras bajas por miniaturas ya cargadas (~1.5 pantallas antes del borde). */
  const PREFETCH_LEAD_VIEWPORTS = 1.5;
  const PREFETCH_THROTTLE_MS = 280;

  let messSuggestionsRefresh = 0;
  function handleMessSuggestionMoved() {
    messSuggestionsRefresh += 1;
    onMessSuggestionMoved();
  }

  let scrollTop = 0;
  let scrollViewportH = 640;
  let scrollViewportW = 640;
  let scrollPreserveSuppressUntil = 0;
  let prevVirtualLayout: GalleryFullVirtualLayout | null = null;
  let scrollTopBeforeLayout = 0;
  let resizeObserver: ResizeObserver | null = null;
  let masonryInnerEl: HTMLDivElement | null = null;
  let masonryInnerH = 0;
  let masonryInnerObserver: ResizeObserver | null = null;
  let viewportLoadTimer: ReturnType<typeof setTimeout> | null = null;
  let viewportStableTimer: ReturnType<typeof setTimeout> | null = null;
  let viewportLoadAnchorTop = -1;
  let lastPrefetchTs = 0;
  let lastScrollTopForPrefetch = 0;
  let railJumpSuppressUntil = 0;
  let lastScrollCancelTop = 0;
  let lastScrollCancelTs = 0;
  let prevGalleryScrolling = false;
  let scrollDragActive = false;
  let lastScrollLogTs = 0;

  function clearViewportLoadTimers() {
    if (viewportLoadTimer !== null) {
      clearTimeout(viewportLoadTimer);
      viewportLoadTimer = null;
    }
    if (viewportStableTimer !== null) {
      clearTimeout(viewportStableTimer);
      viewportStableTimer = null;
    }
  }

  function isScrollbarMouseEvent(e: MouseEvent): boolean {
    if (!galleryScrollEl) return false;
    const rect = galleryScrollEl.getBoundingClientRect();
    return e.clientX >= rect.right - SCROLLBAR_DRAG_ZONE_PX;
  }

  function beginScrollbarDrag() {
    if (scrollDragActive) return;
    scrollDragActive = true;
    clearViewportLoadTimers();
    onCancelScrollLoads();
    galleryDbg("scroll_drag", "inicio arrastre scrollbar", {
      scrollTop,
      windowStart: galleryWindowStart,
      loadedEnd: galleryLoadedEnd,
    });
  }

  /** Índice de medio en la posición actual del scroll (para salto al soltar el scrollbar). */
  function scrollAnchorMediaIndex(): number {
    if (!fullVirtualLayout || totalMediaCount <= 0) return 0;

    const vis = getVisibleLayoutEntries(
      fullVirtualLayout.entries,
      scrollTop,
      scrollViewportH,
      720,
    );
    let anchor = -1;
    for (const e of vis) {
      if (e.mediaIndex != null) anchor = Math.max(anchor, e.mediaIndex);
    }
    if (anchor >= 0) return anchor;

    const est = estimateTargetMediaIndex(
      fullVirtualLayout.entries,
      scrollTop,
      scrollViewportH,
      720,
    );
    if (est >= 0) return est;

    const scrollMax = Math.max(0, fullVirtualLayout.totalHeight - scrollViewportH);
    const ratio = scrollMax > 0 ? Math.min(1, Math.max(0, scrollTop / scrollMax)) : 0;
    return Math.min(
      totalMediaCount - 1,
      Math.max(0, Math.floor(ratio * totalMediaCount)),
    );
  }

  function endScrollbarDrag() {
    if (!scrollDragActive) return;
    scrollDragActive = false;
    if (!fullVirtualEnabled) return;

    clearViewportLoadTimers();
    onCancelBackgroundLoad();
    railJumpSuppressUntil = Date.now() + 3000;

    const target = scrollAnchorMediaIndex();
    if (target >= galleryWindowStart && target < galleryLoadedEnd) {
      scheduleViewportLoadAfterScrollIdle();
      return;
    }
    const far =
      target < galleryWindowStart - WINDOW_JUMP_MARGIN ||
      target >= galleryLoadedEnd + WINDOW_JUMP_MARGIN;
    galleryDbg("scroll_drag", "fin arrastre scrollbar", {
      targetIndex: target,
      jump: far,
      scrollTop,
      windowStart: galleryWindowStart,
      loadedEnd: galleryLoadedEnd,
    });
    onRequestLoadUntilIndex(target, far);
  }

  function handleScrollMouseDown(e: MouseEvent) {
    if (!fullVirtualEnabled || scrollMarkers.length === 0) return;
    if (!isScrollbarMouseEvent(e)) return;
    beginScrollbarDrag();
    window.addEventListener("mouseup", handleScrollMouseUp, true);
  }

  function handleScrollMouseUp() {
    window.removeEventListener("mouseup", handleScrollMouseUp, true);
    endScrollbarDrag();
  }

  $: masonryFullyLoaded =
    masonryVirtualEnabled &&
    totalMediaCount > 0 &&
    mediaByIndex.size >= totalMediaCount;
  $: masonryVirtualShellActive = masonryVirtualEnabled && !masonryFullyLoaded;

  $: extraBottomPx = destinationsMode ? DEST_BAR_RESERVE_PX : 0;
  $: folderItems = galleryGridItems.filter((it) => it.kind === "folder" || it.kind === "folder_up");
  $: mediaByIndex = buildMediaIndexMap(galleryGridItems);
  $: masonrySeedColWidth = (() => {
    const inner = Math.max(0, scrollViewportW - GALLERY_GRID_EDGE_PAD_PX * 2);
    const columnCount = Math.max(1, Math.floor((inner + thumbGapPx) / (gridCellPx + thumbGapPx)));
    return columnCount > 0
      ? (inner - (columnCount - 1) * thumbGapPx) / columnCount
      : gridCellPx;
  })();
  $: if (galleryMasonryView && galleryGridItems.length > 0) {
    seedMasonryHeightsFromItems(
      galleryGridItems,
      masonrySeedColWidth,
      masonryMaxHeightPx(gridCellPx),
    );
  }
  $: fullVirtualEnabled = unlimitedScroll && totalMediaCount > 0;
  $: fullVirtualLayout = fullVirtualEnabled
    ? galleryMasonryView
      ? buildGalleryFullMasonryVirtualLayout({
          folderItems,
          mediaByIndex,
          totalMediaCount,
          layoutMode,
          layoutSpans,
          containerWidth: scrollViewportW,
          cellTargetPx: gridCellPx,
          gapPx: thumbGapPx,
          edgePadPx: GALLERY_GRID_EDGE_PAD_PX,
          extraBottomPx,
        })
      : buildGalleryFullVirtualLayout({
          folderItems,
          mediaByIndex,
          totalMediaCount,
          layoutMode,
          layoutSpans,
          containerWidth: scrollViewportW,
          cellTargetPx: gridCellPx,
          gapPx: thumbGapPx,
          edgePadPx: GALLERY_GRID_EDGE_PAD_PX,
          extraBottomPx,
        })
    : null;
  $: virtualLayout = fullVirtualLayout ?? buildGalleryVirtualLayout(
    galleryGridItems,
    scrollViewportW,
    gridCellPx,
    thumbGapPx,
    GALLERY_GRID_EDGE_PAD_PX,
    extraBottomPx
  );
  $: visibleEntries = getVisibleLayoutEntries(
    virtualLayout.entries,
    scrollTop,
    scrollViewportH
  );

  function mediaIndexAtLayoutY(entries: VirtualLayoutEntry[], anchorY: number): number {
    for (const e of entries) {
      if (e.mediaIndex == null) continue;
      if (anchorY >= e.top && anchorY < e.top + e.height) return e.mediaIndex;
    }
    let best = -1;
    let bestTop = -1;
    for (const e of entries) {
      if (e.mediaIndex == null) continue;
      if (e.top <= anchorY && e.top >= bestTop) {
        bestTop = e.top;
        best = e.mediaIndex;
      }
    }
    return best;
  }

  function scrollTopPreservingAnchor(
    oldLayout: GalleryFullVirtualLayout,
    newLayout: GalleryFullVirtualLayout,
    oldScrollTop: number,
    viewportH: number,
  ): number {
    const anchorY = oldScrollTop + viewportH * 0.28;
    const idx = mediaIndexAtLayoutY(oldLayout.entries, anchorY);
    if (idx < 0) return oldScrollTop;
    const oldEntry = oldLayout.entries.find((e) => e.mediaIndex === idx);
    const newEntry = newLayout.entries.find((e) => e.mediaIndex === idx);
    if (!oldEntry || !newEntry) return oldScrollTop;
    const delta = newEntry.top - oldEntry.top;
    if (Math.abs(delta) < 1) return oldScrollTop;
    return Math.max(0, oldScrollTop + delta);
  }

  $: if (fullVirtualEnabled && fullVirtualLayout && galleryScrollEl) {
    if (
      Date.now() >= scrollPreserveSuppressUntil &&
      prevVirtualLayout &&
      prevVirtualLayout !== fullVirtualLayout &&
      !scrollDragActive
    ) {
      const nextTop = scrollTopPreservingAnchor(
        prevVirtualLayout,
        fullVirtualLayout,
        scrollTopBeforeLayout,
        scrollViewportH,
      );
      if (Math.abs(nextTop - scrollTop) > 1) {
        galleryScrollEl.scrollTop = nextTop;
        scrollTop = nextTop;
        galleryDbg("window", "scroll compensado tras reflow", {
          delta: Math.round(nextTop - scrollTopBeforeLayout),
          scrollTop: nextTop,
        });
      }
    }
    prevVirtualLayout = fullVirtualLayout;
    scrollTopBeforeLayout = scrollTop;
  }

  $: scrollMarkers =
    fullVirtualLayout && fullVirtualLayout.markers.length > 0 ? fullVirtualLayout.markers : [];
  $: masonryCellPx = Math.max(72, Math.round(gridCellPx));
  $: masonryStyle = `--cell:${masonryCellPx}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px;--masonry-max-h:${Math.round(masonryCellPx * 2.4)}px`;
  $: masonryVirtualEnabled = fullVirtualEnabled && galleryMasonryView;
  $: masonryColumnCount = computeMasonryColumnCount(
    scrollViewportW,
    masonryCellPx,
    thumbGapPx,
    GALLERY_GRID_EDGE_PAD_PX
  );
  $: masonryDisplayItems =
    masonryVirtualEnabled && galleryWindowStart > 0
      ? galleryGridItems.filter((it) => it.kind !== "folder" && it.kind !== "folder_up")
      : galleryGridItems;
  $: masonrySegments = galleryMasonryView
    ? buildMasonrySegments(masonryDisplayItems, masonryColumnCount)
    : [];

  /** Limita prefetch LQ a una extensión por tanda (evita pedir índice 31626 de golpe). */
  function capPrefetchIndex(index: number): number {
    const batch = getGalleryPerfConfig().unlimitedBatchSize;
    return Math.min(index, galleryLoadedEnd + batch * 2);
  }

  /** Índice destino para extender hacia adelante según scroll y borde cargado. */
  function computeForwardPrefetchTarget(
    layout: NonNullable<typeof fullVirtualLayout>,
  ): number {
    if (galleryLoadedEnd >= totalMediaCount) return -1;

    const viewBottom = scrollTop + scrollViewportH;
    const leadPx = scrollViewportH * PREFETCH_LEAD_VIEWPORTS;
    let target = -1;

    const loadedBottom = virtualLoadedBottomY(layout.entries, galleryLoadedEnd);
    if (loadedBottom > 0 && viewBottom >= loadedBottom - leadPx) {
      target = galleryLoadedEnd;
    }

    const est = estimateTargetMediaIndex(
      layout.entries,
      scrollTop + scrollViewportH * 0.35,
      scrollViewportH,
    );
    if (est >= galleryLoadedEnd) target = Math.max(target, est);

    if (target < 0 && galleryLoadedEnd < totalMediaCount && scrollTop > 0 && loadedBottom > 0) {
      if (viewBottom >= loadedBottom - leadPx) target = galleryLoadedEnd;
    }

    return target >= 0 ? capPrefetchIndex(target) : -1;
  }

  /** Índice destino para extender hacia arriba (ventana deslizante). */
  function computeBackwardPrefetchTarget(
    layout: NonNullable<typeof fullVirtualLayout>,
  ): number {
    if (galleryWindowStart <= 0) return -1;

    const viewTop = scrollTop;
    const leadPx = scrollViewportH * PREFETCH_LEAD_VIEWPORTS;
    let target = -1;

    const loadedTop = virtualLoadedTopY(layout.entries, galleryWindowStart);
    if (loadedTop > 0 && viewTop <= loadedTop + leadPx) {
      target = Math.max(0, galleryWindowStart - 1);
    }

    const est = estimateTargetMediaIndex(
      layout.entries,
      scrollTop - scrollViewportH * 0.15,
      scrollViewportH,
    );
    if (est >= 0 && est < galleryWindowStart) target = Math.max(target, est);

    const vis = getVisibleLayoutEntries(layout.entries, scrollTop, scrollViewportH, 720);
    for (const e of vis) {
      if (e.item.kind !== "placeholder" || e.mediaIndex == null) continue;
      if (e.mediaIndex < galleryWindowStart) {
        target = Math.max(target, e.mediaIndex);
      }
    }

    return target;
  }

  /** Precarga en caliente según dirección del scroll (rueda arriba o abajo). */
  function maybePrefetchDuringScroll() {
    if (scrollDragActive) return;
    if (!fullVirtualEnabled) return;
    if (Date.now() < railJumpSuppressUntil) return;

    const layout = fullVirtualLayout;
    if (!layout) return;

    const now = Date.now();
    if (now - lastPrefetchTs < PREFETCH_THROTTLE_MS) return;

    const prevTop = lastScrollTopForPrefetch;
    const delta = scrollTop - prevTop;
    lastScrollTopForPrefetch = scrollTop;
    if (Math.abs(delta) < 2) return;

    let target = -1;
    let jump = false;

    if (delta > 0) {
      if (galleryLoadedEnd >= totalMediaCount) return;
      target = computeForwardPrefetchTarget(layout);
    } else {
      target = computeBackwardPrefetchTarget(layout);
      if (target >= 0 && target < galleryWindowStart - WINDOW_JUMP_MARGIN) {
        jump = true;
      }
    }

    if (target < 0) return;

    lastPrefetchTs = now;
    onRequestLoadUntilIndex(target, jump);
  }

  function scheduleViewportLoadAfterScrollIdle() {
    if (scrollDragActive) return;
    if (viewportLoadTimer !== null) clearTimeout(viewportLoadTimer);
    if (viewportStableTimer !== null) clearTimeout(viewportStableTimer);
    viewportLoadTimer = setTimeout(() => {
      viewportLoadTimer = null;
      const top = scrollTop;
      if (viewportLoadAnchorTop >= 0 && Math.abs(top - viewportLoadAnchorTop) > 12) {
        viewportLoadAnchorTop = top;
        scheduleViewportLoadAfterScrollIdle();
        return;
      }
      viewportLoadAnchorTop = top;
      viewportStableTimer = setTimeout(() => {
        viewportStableTimer = null;
        if (Math.abs(scrollTop - viewportLoadAnchorTop) > 12) {
          scheduleViewportLoadAfterScrollIdle();
          return;
        }
        requestLoadForViewport();
      }, SCROLL_STABLE_MS);
    }, SCROLL_LOAD_IDLE_MS);
  }

  /** Pide más ítems según scroll y huecos visibles (no durante salto por rail). */
  function requestLoadForViewport() {
    if (!fullVirtualEnabled) return;
    if (galleryLoadedEnd >= totalMediaCount && galleryWindowStart <= 0) return;
    if (Date.now() < railJumpSuppressUntil) return;

    const layout = fullVirtualLayout;
    if (!layout) return;

    let target = -1;
    let jump = false;
    const viewBottom = scrollTop + scrollViewportH;

    const vis = getVisibleLayoutEntries(layout.entries, scrollTop, scrollViewportH, 720);
    for (const e of vis) {
      if (e.item.kind !== "placeholder" || e.mediaIndex == null) continue;
      if (e.mediaIndex < galleryWindowStart - WINDOW_JUMP_MARGIN) {
        target = Math.max(target, e.mediaIndex);
        jump = true;
      } else if (e.mediaIndex < galleryWindowStart) {
        target = Math.max(target, e.mediaIndex);
        jump = false;
      } else if (e.mediaIndex >= galleryLoadedEnd) {
        target = Math.max(target, e.mediaIndex);
        jump = false;
      }
    }

    if (galleryWindowStart > 0) {
      const forwardPrefetch = computeForwardPrefetchTarget(layout);
      const backPrefetch = computeBackwardPrefetchTarget(layout);
      if (forwardPrefetch >= 0 && (target < 0 || target >= galleryWindowStart)) {
        target = Math.max(target, forwardPrefetch);
      }
      if (backPrefetch >= 0 && backPrefetch < galleryWindowStart) {
        if (target < 0 || target < galleryWindowStart) {
          target = Math.max(target, backPrefetch);
        }
      }

      if (target >= 0) {
        onRequestLoadUntilIndex(target, jump);
        return;
      }
      const loadedBottom = virtualLoadedBottomY(layout.entries, galleryLoadedEnd);
      if (loadedBottom > 0 && viewBottom > loadedBottom + 16) {
        onRequestLoadUntilIndex(galleryLoadedEnd, false);
      }
      return;
    }

    const forwardPrefetch = computeForwardPrefetchTarget(layout);
    const backPrefetch = computeBackwardPrefetchTarget(layout);
    if (forwardPrefetch >= 0 && (target < 0 || target >= galleryWindowStart)) {
      target = Math.max(target, forwardPrefetch);
    }
    if (backPrefetch >= 0 && backPrefetch < galleryWindowStart) {
      if (target < 0 || target < galleryWindowStart) {
        target = Math.max(target, backPrefetch);
      }
    }

    const virtualEnd = virtualLoadedBottomY(layout.entries, galleryLoadedEnd);
    if (virtualEnd > 0 && viewBottom > virtualEnd + 16) {
      target = Math.max(target, galleryLoadedEnd);
    }

    const est = estimateTargetMediaIndex(layout.entries, scrollTop, scrollViewportH);
    if (est >= galleryLoadedEnd) target = Math.max(target, est);

    if (target >= 0) onRequestLoadUntilIndex(target, jump);
  }

  $: {
    if (prevGalleryScrolling && !galleryScrolling && fullVirtualEnabled && !scrollDragActive) {
      scheduleViewportLoadAfterScrollIdle();
    }
    prevGalleryScrolling = galleryScrolling;
  }

  function entryStyle(entry: VirtualLayoutEntry): string {
    return `top:${entry.top}px;left:${entry.left}px;width:${entry.width}px;height:${entry.height}px`;
  }

  /** Ancla el scroll al índice de medio tras un salto (layout virtual estable). */
  export function scrollToMediaIndex(index: number, align: "start" | "center" = "start"): boolean {
    if (!fullVirtualEnabled || !galleryScrollEl) return false;
    const layout = fullVirtualLayout;
    if (!layout) return false;
    const idx = Math.max(0, Math.min(totalMediaCount - 1, Math.floor(index)));
    const entry = layout.entries.find((e) => e.mediaIndex === idx);
    let top: number;
    if (entry) {
      top = Math.max(0, entry.top - (align === "center" ? scrollViewportH * 0.35 : 12));
    } else {
      const maxScroll = Math.max(0, layout.totalHeight - scrollViewportH);
      const ratio = idx / Math.max(1, totalMediaCount - 1);
      top = ratio * maxScroll;
    }
    galleryScrollEl.scrollTop = top;
    scrollTop = top;
    scrollPreserveSuppressUntil = Date.now() + 600;
    galleryDbg("window", "scroll anclado tras salto", {
      targetIndex: idx,
      scrollTop: top,
      foundEntry: Boolean(entry),
    });
    return true;
  }

  function syncMasonryInnerHeight(el: HTMLDivElement | null) {
    masonryInnerH = el?.offsetHeight ?? 0;
  }

  $: if (masonryInnerEl && typeof ResizeObserver !== "undefined") {
    masonryInnerObserver?.disconnect();
    masonryInnerObserver = new ResizeObserver(() => syncMasonryInnerHeight(masonryInnerEl));
    masonryInnerObserver.observe(masonryInnerEl);
  }

  function handleGalleryScroll(e: UIEvent) {
    const el = e.currentTarget as HTMLDivElement | null;
    if (!el) return;
    const now = Date.now();
    const newTop = el.scrollTop;
    scrollTop = newTop;
    scrollViewportH = el.clientHeight;

    if (now >= railJumpSuppressUntil) {
      if (!scrollDragActive) {
        const dt = now - lastScrollCancelTs;
        const delta = Math.abs(newTop - lastScrollCancelTop);
        // Solo invalidar cargas en curso en arrastre muy rápido, no en scroll ligero.
        if (dt > 0 && dt < 180 && delta > 320) {
          onCancelScrollLoads();
          galleryDbg("scroll", "scroll rápido — cancelar cargas", { scrollTop: newTop, delta });
        }
        lastScrollCancelTop = newTop;
        lastScrollCancelTs = now;
        maybePrefetchDuringScroll();
        scheduleViewportLoadAfterScrollIdle();
        if (now - lastScrollLogTs > 450) {
          lastScrollLogTs = now;
          galleryDbg("scroll", "posición viewport", {
            scrollTop: newTop,
            viewportH: scrollViewportH,
            windowStart: galleryWindowStart,
            loadedEnd: galleryLoadedEnd,
          });
        }
      } else {
        lastScrollCancelTop = newTop;
        lastScrollCancelTs = now;
      }
    }
    onGalleryScroll(e);
  }

  function handleScrollPointerMove(e: PointerEvent) {
    onGalleryScrollPointerMove(e);
    if (!galleryScrollEl || scrollMarkers.length === 0) {
      scrollGutter?.clearRailHover();
      return;
    }
    const rect = galleryScrollEl.getBoundingClientRect();
    if (e.clientX < rect.right - SCROLL_RAIL_HIT_PX) {
      scrollGutter?.clearRailHover();
      return;
    }
    scrollGutter?.pointerOnRail(e.clientY, rect.top, rect.height);
  }

  function handleScrollPointerLeave() {
    scrollGutter?.clearRailHover();
  }

  function jumpToScrollMarker(marker: import("../lib/galleryFullVirtualLayout").GalleryScrollMarker) {
    if (!galleryScrollEl) return;
    if (viewportLoadTimer !== null) {
      clearTimeout(viewportLoadTimer);
      viewportLoadTimer = null;
    }
    onCancelBackgroundLoad();
    railJumpSuppressUntil = Date.now() + 4000;
    const idx = marker.startIndex;
    if (idx >= galleryWindowStart && idx < galleryLoadedEnd) {
      galleryDbg("rail_jump", "salto en ventana (solo scroll)", {
        targetIndex: idx,
        label: marker.label,
        markerTop: marker.top,
        windowStart: galleryWindowStart,
        loadedEnd: galleryLoadedEnd,
      });
      requestAnimationFrame(() => {
        galleryScrollEl?.scrollTo({ top: Math.max(0, marker.top - 12), behavior: "auto" });
      });
      return;
    }
    const far =
      idx < galleryWindowStart - WINDOW_JUMP_MARGIN ||
      idx >= galleryLoadedEnd + WINDOW_JUMP_MARGIN;
    galleryDbg("rail_jump", "salto a fecha / marca", {
      targetIndex: idx,
      jump: far,
      label: marker.label,
      markerTop: marker.top,
      windowStart: galleryWindowStart,
      loadedEnd: galleryLoadedEnd,
    });
    onRequestLoadUntilIndex(idx, far);
    requestAnimationFrame(() => {
      galleryScrollEl?.scrollTo({ top: Math.max(0, marker.top - 12), behavior: "auto" });
    });
  }

  function syncScrollMetrics(el: HTMLDivElement | null) {
    if (!el) return;
    scrollTop = el.scrollTop;
    scrollViewportH = el.clientHeight;
    scrollViewportW = el.clientWidth;
  }

  onMount(() => {
    syncScrollMetrics(galleryScrollEl);
    syncMasonryInnerHeight(masonryInnerEl);
    scheduleViewportLoadAfterScrollIdle();
    if (galleryScrollEl && typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        syncScrollMetrics(galleryScrollEl);
        if (!galleryScrolling) scheduleViewportLoadAfterScrollIdle();
      });
      resizeObserver.observe(galleryScrollEl);
    }
    if (masonryInnerEl && typeof ResizeObserver !== "undefined") {
      masonryInnerObserver = new ResizeObserver(() => syncMasonryInnerHeight(masonryInnerEl));
      masonryInnerObserver.observe(masonryInnerEl);
    }
  });

  onDestroy(() => {
    window.removeEventListener("mouseup", handleScrollMouseUp, true);
    if (viewportLoadTimer !== null) clearTimeout(viewportLoadTimer);
    viewportLoadTimer = null;
    resizeObserver?.disconnect();
    resizeObserver = null;
    masonryInnerObserver?.disconnect();
    masonryInnerObserver = null;
  });
</script>

<article
  class="gallery om-panel om-panel--lift"
  class:gallery--with-float={galleryFloatChromeActive}
  class:gallery--with-dest={destinationsMode}
  class:gallery--masonry={galleryMasonryView}
  class:gallery--range-selecting={galleryRangeSelecting}
  class:gallery--scrolling={galleryScrolling}
  class:gallery--busy={galleryBusy}
>
  <div class="gallery__scroll-row">
    <div
      class="gallery__scroll"
      class:gallery__scroll--dest={destinationsMode}
      class:gallery__scroll--with-gutter={scrollMarkers.length > 0}
      bind:this={galleryScrollEl}
      on:scroll={handleGalleryScroll}
      on:mousedown={handleScrollMouseDown}
      on:pointermove={handleScrollPointerMove}
      on:pointerleave={handleScrollPointerLeave}
    >
    {#if galleryFloatChromeActive}
      <div class="selection-float-rail">
        <div class="selection-float selection-float--gallery-tr app-chrome" role="toolbar" aria-label={t("selection.toolbarGalleryAria")}>
          <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectPage}>{t("selection.page")}</button>
          <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearSelection}>{t("selection.remove")}</button>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--mini"
            disabled={selectionCount === 0}
            on:click={() =>
              openConfirmDelete(
                t("confirm.deleteSelectionTitle"),
                t("confirm.deleteSelectionDetail").replace("{count}", String(selectionCount)),
                deleteSelectedGalleryItems
              )}
          >{t("selection.delete")}</button>
          <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertSelection}>{t("selection.invert")}</button>
          <span class="selection-float__count" title={t("selection.selectedTitle")}>{selectionCount}</span>
        </div>
      </div>
    {/if}
    {#if galleryMasonryView}
      <div
        class="grid-masonry"
        class:grid-masonry--virtual-shell={masonryVirtualShellActive}
        bind:this={galleryGridEl}
        style={masonryVirtualShellActive
          ? `${masonryStyle};height:${virtualLayout.totalHeight}px;position:relative;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px`
          : masonryStyle}
      >
        {#if masonryVirtualShellActive}
          {#each visibleEntries as entry (entry.item.path)}
            <GalleryGridItem
              it={entry.item}
              style={`position:absolute;box-sizing:border-box;${entryStyle(entry)}`}
              masonrySpan={entry.item.kind === "section" || entry.item.kind === "day_break"}
              masonryLayout={isGalleryMediaKind(entry.item.kind)}
              {dragOverSectionPath}
              {galleryKeyboardNavHintActive}
              {galleryCursorPath}
              {galleryFloatChromeActive}
              {galleryRangeSelecting}
              {galleryRangeSuppressClick}
              {galleryRangeDraftSelectedSet}
              {showThumbLabels}
              {galleryScrolling}
              {galleryBusy}
              {navigateToFolder}
              {onSectionFolderDrop}
              {isGalleryMediaKind}
              {onGalleryTilePointerDown}
              {onGalleryTilePointerEnter}
              {onTileDragStart}
              {clickItem}
              {openZoomFromGallery}
              {onGalleryItemContextMenu}
            />
          {/each}
        {:else}
        <div class="grid-masonry__body" bind:this={masonryInnerEl}>
          {#each masonrySegments as segment, segIdx (`${segment.kind}:${segment.kind === "span" ? segment.item.path : segIdx}`)}
            {#if segment.kind === "span"}
              <GalleryGridItem
                it={segment.item}
                masonrySpan={true}
                masonryLayout={false}
                {dragOverSectionPath}
                {galleryKeyboardNavHintActive}
                {galleryCursorPath}
                {galleryFloatChromeActive}
                {galleryRangeSelecting}
                {galleryRangeSuppressClick}
                {galleryRangeDraftSelectedSet}
                {showThumbLabels}
                {galleryScrolling}
                {galleryBusy}
                {navigateToFolder}
                {onSectionFolderDrop}
                {isGalleryMediaKind}
                {onGalleryTilePointerDown}
                {onGalleryTilePointerEnter}
                {onTileDragStart}
                {clickItem}
                {openZoomFromGallery}
                {onGalleryItemContextMenu}
              />
            {:else}
              <div class="grid-masonry-cols">
                {#each segment.columns as colItems, colIdx (colIdx)}
                  <div class="grid-masonry-col">
                    {#each colItems as it (it.path)}
                      <GalleryGridItem
                        {it}
                        masonrySpan={false}
                        masonryLayout={isGalleryMediaKind(it.kind)}
                        {dragOverSectionPath}
                        {galleryKeyboardNavHintActive}
                        {galleryCursorPath}
                        {galleryFloatChromeActive}
                        {galleryRangeSelecting}
                        {galleryRangeSuppressClick}
                        {galleryRangeDraftSelectedSet}
                        {showThumbLabels}
                        {galleryScrolling}
                        {galleryBusy}
                        {navigateToFolder}
                        {onSectionFolderDrop}
                        {isGalleryMediaKind}
                        {onGalleryTilePointerDown}
                        {onGalleryTilePointerEnter}
                        {onTileDragStart}
                        {clickItem}
                        {openZoomFromGallery}
                        {onGalleryItemContextMenu}
                      />
                    {/each}
                  </div>
                {/each}
              </div>
            {/if}
          {/each}
        </div>
        {/if}
      </div>
    {:else}
      <div
        class="grid-virtual"
        bind:this={galleryGridEl}
        style={`height:${virtualLayout.totalHeight}px;--cell:${virtualLayout.cellSize}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px`}
      >
        {#each visibleEntries as entry (entry.item.path)}
          <GalleryGridItem
            it={entry.item}
            style={`position:absolute;box-sizing:border-box;${entryStyle(entry)}`}
            {dragOverSectionPath}
            {galleryKeyboardNavHintActive}
            {galleryCursorPath}
            {galleryFloatChromeActive}
            {galleryRangeSelecting}
            {galleryRangeSuppressClick}
            {galleryRangeDraftSelectedSet}
            {showThumbLabels}
            {galleryScrolling}
            {galleryBusy}
            {navigateToFolder}
            {onSectionFolderDrop}
            {isGalleryMediaKind}
            {onGalleryTilePointerDown}
            {onGalleryTilePointerEnter}
            {onTileDragStart}
            {clickItem}
            {openZoomFromGallery}
            {onGalleryItemContextMenu}
          />
        {/each}
      </div>
    {/if}

    {#key `${messSuggestionsRefresh}:${messFolder}:${gridCellPx}:${messSuggestionsEnabled}`}
      <GalleryMessSuggestions
        enabled={messSuggestionsEnabled}
        {messFolder}
        targetFolder={galleryTargetFolder}
        masonry={messSuggestionsMasonry}
        {gridCellPx}
        {thumbGapPx}
        on:moved={handleMessSuggestionMoved}
      />
    {/key}
    </div>
    {#if scrollMarkers.length > 0 && fullVirtualLayout}
      <GalleryScrollGutter
        bind:this={scrollGutter}
        markers={scrollMarkers}
        totalHeight={fullVirtualLayout.totalHeight}
        cellSize={fullVirtualLayout.cellSize}
        {scrollTop}
        scrollViewportH={scrollViewportH}
        onJumpToMarker={jumpToScrollMarker}
      />
    {/if}
  </div>

  {#if destinationsMode}
    <DestToolbar
      toolbarItems={destToolbarItems}
      folderLabel={destToolbarFolderLabel}
      canGoBack={destToolbarCanGoBack}
      {dragOverDestPath}
      {draggedDestIdx}
      onBack={onDestToolbarBack}
      onOpenFolder={onDestToolbarOpenFolder}
      onAddDest={openAddDestForm}
      onDestClick={onDestCardClick}
      onDestContextMenu={(e, idx) => onDestContextMenu(e, idx, "gallery")}
      {onDestChipDragStart}
      {onDestChipDragEnd}
      {onDestDrop}
    />
  {/if}
</article>

<style>
  .gallery.om-panel {
    padding: 0;
  }

  .gallery.om-panel.om-panel--lift {
    box-shadow: 0 14px 42px rgb(0 0 0 / 0.52) !important;
    border-color: rgb(255 255 255 / 0.07) !important;
  }

  .gallery {
    min-height: 0;
    min-width: 0;
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: 100%;
  }

  .gallery__scroll-row {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .gallery .gallery__scroll {
    overflow: auto;
    display: block;
    min-height: 0;
    flex: 1;
    padding-top: var(--om-space-2);
    border-radius: inherit;
    background: transparent;
    scrollbar-color: rgb(124 140 255 / 0.18) transparent;
  }

  .gallery .gallery__scroll--with-gutter::-webkit-scrollbar-track {
    margin-block: var(--om-space-2);
  }

  .gallery__scroll--dest {
    padding-bottom: max(3.75rem, calc(env(safe-area-inset-bottom, 0px) + 3.25rem));
  }

  .selection-float-rail {
    position: sticky;
    top: var(--om-space-2);
    z-index: 8;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    padding: 0 var(--om-space-2);
    margin-bottom: -2.65rem;
    pointer-events: none;
  }

  .gallery__scroll > .selection-float-rail > .selection-float.selection-float--gallery-tr {
    pointer-events: auto;
    flex-wrap: nowrap;
    white-space: nowrap;
    max-width: min(560px, calc(100% - var(--om-space-4)));
    background: rgb(8 10 18 / 0.92);
    border: 1px solid rgb(255 255 255 / 0.12);
    box-shadow: 0 10px 28px rgb(0 0 0 / 0.42);
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
  }

  .selection-float__count {
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 1.25rem;
    text-align: center;
    padding: 0 var(--om-space-1);
    color: var(--om-accent-2);
  }

  .gallery--scrolling .selection-float-rail,
  .gallery--busy .selection-float-rail,
  .gallery--scrolling .selection-float,
  .gallery--busy .selection-float {
    transform: none;
  }

  .gallery--scrolling .gallery__scroll,
  .gallery--busy .gallery__scroll {
    will-change: scroll-position;
  }

  .gallery:not(.gallery--scrolling):not(.gallery--busy) .gallery__scroll {
    will-change: auto;
  }

  .gallery .gallery__scroll::-webkit-scrollbar {
    width: 8px;
  }

  .gallery .gallery__scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgb(124 140 255 / 0.28), rgb(94 228 212 / 0.16));
    border: 4px solid transparent;
    background-clip: padding-box;
    border-radius: 999px;
  }

  .gallery .gallery__scroll::-webkit-scrollbar-track {
    margin-block: var(--om-space-2);
    background: transparent;
  }

  .grid-virtual {
    position: relative;
    width: 100%;
    box-sizing: border-box;
  }

  .grid-masonry {
    width: 100%;
    box-sizing: border-box;
    padding: 0 var(--grid-edge-pad);
  }

  .grid-masonry--virtual-shell {
    box-sizing: border-box;
    position: relative;
  }

  .grid-masonry__virtual-ph {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
  }

  .masonry-virtual-spacer {
    width: 100%;
    flex-shrink: 0;
    pointer-events: none;
  }

  .grid-masonry__body {
    width: 100%;
  }

  .grid-masonry-cols {
    display: flex;
    align-items: flex-start;
    gap: var(--thumb-gap);
    width: 100%;
    margin-bottom: var(--thumb-gap);
  }

  .grid-masonry-col {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: var(--thumb-gap);
  }

  :global(.gallery-virtual-item.tile) {
    height: 100%;
    width: 100%;
  }
</style>
