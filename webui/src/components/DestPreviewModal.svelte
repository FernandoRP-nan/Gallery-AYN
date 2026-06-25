<script lang="ts">
  import { createEventDispatcher, onDestroy, tick } from "svelte";
  import { bridge } from "../lib/api";
  import type { GalleryItem } from "../lib/api";
  import {
    bumpDestPreviewThumbToken,
    hydrateDestPreviewThumbs,
    type DestPreviewItem,
  } from "../lib/destPreviewThumbs";
  import {
    applyCachedDestPreviewThumbs,
    clearDestPreviewThumbCache,
    getDestPreviewThumb,
    removeDestPreviewThumbs,
    renameDestPreviewThumb,
  } from "../lib/destPreviewThumbCache";
  import {
    buildGalleryVirtualLayout,
    getVisibleLayoutEntries,
  } from "../lib/galleryVirtualLayout";
  import ThumbImage from "./ThumbImage.svelte";
  import { t } from "../lib/i18n";

  const dispatch = createEventDispatcher<{
    close: void;
    zoom: { item: DestPreviewItem; navItems: DestPreviewItem[] };
    deleteSelected: void;
    dropToRoute: { paths: string[] };
    contextmenu: { item: DestPreviewItem; clientX: number; clientY: number };
  }>();

  export let open = false;
  export let destPath = "";
  export let thumbScale = 1;
  export let thumbGapPx = 12;
  export let showThumbLabels = true;
  export let gridCellPx = 120;

  const EDGE_PAD = 8;
  const DEST_MODAL_FRAC = 0.9;

  let items: DestPreviewItem[] = [];
  let selectedPaths: string[] = [];
  let loading = false;
  let loadError = "";
  let scrollEl: HTMLDivElement | null = null;
  let scrollTop = 0;
  let scrollViewportH = 480;
  let scrollViewportW = 640;
  let resizeObserver: ResizeObserver | null = null;
  let rangeSelecting = false;
  let rangeSuppressClick = false;
  let rangeAnchorPath: string | null = null;
  let rangeMode: "select" | "deselect" = "select";
  let rangeBaseSelected: string[] = [];
  let thumbToken = 0;
  let loadGen = 0;
  let loadedDestPath = "";
  let hoverCursorPath: string | null = null;
  let scrollIdleTimer: ReturnType<typeof setTimeout> | null = null;
  let lastPointer: { x: number; y: number } | null = null;

  function destThumbHydrateOpts() {
    return {
      cursorPath: hoverCursorPath,
      pointer: lastPointer,
    };
  }

  function restoreScrollTop(top: number) {
    queueMicrotask(() => {
      if (scrollEl) scrollEl.scrollTop = top;
    });
  }

  function mergeItemThumbsFromCache(list: DestPreviewItem[]): DestPreviewItem[] {
    return applyCachedDestPreviewThumbs(list);
  }

  function itemsNeedingHydration(list: DestPreviewItem[]): DestPreviewItem[] {
    return list.filter((x) => {
      const cached = getDestPreviewThumb(x.path);
      if (cached?.thumbQuality === "hq") return false;
      if (x.thumbDataUrl && x.thumbQuality === "hq") return false;
      return true;
    });
  }

  async function startThumbHydration(
    snapshot: DestPreviewItem[],
    gen: number,
    opts?: { limitPaths?: string[] }
  ) {
    if (itemsNeedingHydration(snapshot).length === 0) return;
    await tick();
    const token = thumbToken;
    void hydrateDestPreviewThumbs(
      items,
      thumbScale,
      token,
      scrollEl,
      (next) => {
        if (token !== thumbToken || gen !== loadGen) return;
        items = next;
      },
      { ...destThumbHydrateOpts(), limitPaths: opts?.limitPaths }
    );
  }

  function filterVisibleItemsNeedingHydration(list: DestPreviewItem[]): string[] {
    if (!scrollEl) return [];
    const bounds = scrollEl.getBoundingClientRect();
    const visible = new Set<string>();
    for (const tile of scrollEl.querySelectorAll<HTMLElement>(".dest-preview-tile[data-preview-path]")) {
      const r = tile.getBoundingClientRect();
      if (r.bottom > bounds.top + 2 && r.top < bounds.bottom - 2) {
        const p = tile.dataset.previewPath;
        if (p) visible.add(p);
      }
    }
    return list.filter((x) => visible.has(x.path) && itemsNeedingHydration([x]).length > 0).map((x) => x.path);
  }

  async function loadPreview(path: string, opts?: { hardReset?: boolean }) {
    const hardReset = opts?.hardReset ?? loadedDestPath !== path;
    const gen = ++loadGen;
    const savedScroll = scrollEl?.scrollTop ?? scrollTop;
    loadError = "";
    if (hardReset) {
      loading = true;
      items = [];
      selectedPaths = [];
      thumbToken = bumpDestPreviewThumbToken();
    }
    try {
      const w = Math.max(320, Math.round(window.innerWidth * DEST_MODAL_FRAC));
      const out = await bridge.destinationPreview(path, thumbScale, w);
      if (gen !== loadGen || !open) return;
      items = mergeItemThumbsFromCache(Array.isArray(out?.items) ? out.items : []);
      loadedDestPath = path;
      loading = false;
      if (!hardReset) restoreScrollTop(savedScroll);
      await startThumbHydration(items, gen);
    } catch (e: unknown) {
      if (gen !== loadGen) return;
      loading = false;
      loadError = e instanceof Error ? e.message : t("destPreview.loadError");
    }
  }

  $: if (open && destPath) {
    if (loadedDestPath !== destPath) {
      void loadPreview(destPath, { hardReset: true });
    }
  } else if (!open) {
    loadGen++;
    bumpDestPreviewThumbToken();
    loadedDestPath = "";
    items = [];
    selectedPaths = [];
    loading = false;
    loadError = "";
  }
  $: virtualItems = items.map(
    (it): GalleryItem => ({
      kind: "image",
      name: it.name,
      path: it.path,
      thumbDataUrl: it.thumbDataUrl ?? null,
      thumbQuality: it.thumbQuality,
    })
  );

  $: virtualLayout = buildGalleryVirtualLayout(
    virtualItems,
    scrollViewportW,
    gridCellPx,
    thumbGapPx,
    EDGE_PAD
  );
  $: visibleEntries = getVisibleLayoutEntries(virtualLayout.entries, scrollTop, scrollViewportH);
  $: selectedCount = selectedPaths.length;
  $: floatActive = open && items.length > 0;

  function entryStyle(top: number, left: number, width: number, height: number): string {
    return `top:${top}px;left:${left}px;width:${width}px;height:${height}px`;
  }

  function syncScrollMetrics(el: HTMLDivElement | null) {
    if (!el) return;
    scrollTop = el.scrollTop;
    scrollViewportH = el.clientHeight;
    scrollViewportW = el.clientWidth;
  }

  function onScroll(e: Event) {
    syncScrollMetrics(e.currentTarget as HTMLDivElement);
    if (scrollIdleTimer !== null) clearTimeout(scrollIdleTimer);
    scrollIdleTimer = setTimeout(() => {
      scrollIdleTimer = null;
      const visiblePaths = filterVisibleItemsNeedingHydration(items);
      if (visiblePaths.length > 0) {
        void startThumbHydration(items, loadGen, { limitPaths: visiblePaths });
      }
    }, 280);
  }

  function onScrollPointerMove(e: PointerEvent) {
    lastPointer = { x: e.clientX, y: e.clientY };
  }

  function togglePick(path: string) {
    selectedPaths = selectedPaths.includes(path)
      ? selectedPaths.filter((p) => p !== path)
      : [...selectedPaths, path];
  }

  function selectAll() {
    selectedPaths = items.map((x) => x.path);
  }

  function clearSelection() {
    selectedPaths = [];
  }

  function invertSelection() {
    const cur = new Set(selectedPaths);
    selectedPaths = items.map((x) => x.path).filter((p) => !cur.has(p));
  }

  function applyRange(fromPath: string, toPath: string, mode: "select" | "deselect") {
    const paths = items.map((x) => x.path);
    const a = paths.indexOf(fromPath);
    const b = paths.indexOf(toPath);
    if (a < 0 || b < 0) return;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    const draft = new Set(rangeBaseSelected);
    for (let i = lo; i <= hi; i++) {
      const p = paths[i];
      if (!p) continue;
      if (mode === "select") draft.add(p);
      else draft.delete(p);
    }
    selectedPaths = [...draft];
  }

  function onTilePointerDown(e: PointerEvent, it: DestPreviewItem) {
    if (e.ctrlKey) return;
    e.preventDefault();
    rangeBaseSelected = [...selectedPaths];
    rangeAnchorPath = it.path;
    rangeMode = selectedPaths.includes(it.path) ? "deselect" : "select";
    rangeSelecting = true;
    applyRange(it.path, it.path, rangeMode);
  }

  function onTilePointerEnter(path: string) {
    hoverCursorPath = path;
    if (!rangeSelecting || !rangeAnchorPath) return;
    applyRange(rangeAnchorPath, path, rangeMode);
  }

  function endRangeSelection() {
    if (!rangeSelecting) return;
    rangeSelecting = false;
    rangeAnchorPath = null;
    rangeBaseSelected = [];
    rangeSuppressClick = true;
    setTimeout(() => {
      rangeSuppressClick = false;
    }, 0);
  }

  function onTileClick(it: DestPreviewItem) {
    if (rangeSuppressClick) return;
    if (selectedCount > 0) {
      togglePick(it.path);
      return;
    }
    dispatch("zoom", { item: it, navItems: items });
  }

  function onTileContextMenu(e: MouseEvent, it: DestPreviewItem) {
    e.preventDefault();
    e.stopPropagation();
    dispatch("contextmenu", { item: it, clientX: e.clientX, clientY: e.clientY });
  }

  function onTileDragStart(e: DragEvent, it: DestPreviewItem) {
    if (!(e as DragEvent).ctrlKey) {
      e.preventDefault();
      return;
    }
    if (!selectedPaths.includes(it.path)) {
      selectedPaths = [...selectedPaths, it.path];
    }
    const dt = e.dataTransfer;
    if (!dt) return;
    dt.effectAllowed = "move";
    dt.setData("application/x-om-preview-paths", JSON.stringify(selectedPaths));
    dt.setData("text/plain", selectedPaths[0] ?? it.path);
  }

  onDestroy(() => {
    if (scrollIdleTimer !== null) clearTimeout(scrollIdleTimer);
    resizeObserver?.disconnect();
    bumpDestPreviewThumbToken();
    clearDestPreviewThumbCache();
  });

  $: if (scrollEl && open) {
    queueMicrotask(() => syncScrollMetrics(scrollEl));
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver?.disconnect();
      resizeObserver = new ResizeObserver(() => syncScrollMetrics(scrollEl));
      resizeObserver.observe(scrollEl);
    }
  }

  export function reloadPreview() {
    if (destPath) void loadPreview(destPath, { hardReset: true });
  }

  /** Quita ítems movidos/borrados sin recargar ni perder scroll/miniaturas. */
  export function removePaths(paths: string[]) {
    const removed = new Set(paths.map((p) => String(p).trim()).filter(Boolean));
    if (removed.size === 0) return;
    const savedScroll = scrollEl?.scrollTop ?? scrollTop;
    selectedPaths = selectedPaths.filter((p) => !removed.has(p));
    items = items.filter((x) => !removed.has(x.path));
    removeDestPreviewThumbs(removed);
    restoreScrollTop(savedScroll);
  }

  export function updateItemPath(oldPath: string, newPath: string, newName: string) {
    const from = String(oldPath).trim();
    const to = String(newPath).trim();
    if (!from || !to) return;
    const savedScroll = scrollEl?.scrollTop ?? scrollTop;
    renameDestPreviewThumb(from, to);
    const cached = getDestPreviewThumb(to);
    items = items.map((x) => {
      if (x.path !== from) return x;
      return {
        ...x,
        path: to,
        name: newName,
        thumbDataUrl: cached?.thumbDataUrl ?? x.thumbDataUrl ?? null,
        thumbQuality: cached?.thumbQuality ?? x.thumbQuality,
      };
    });
    selectedPaths = selectedPaths.map((p) => (p === from ? to : p));
    restoreScrollTop(savedScroll);
  }

  /** @deprecated Usar removePaths o reloadPreview. */
  export function refresh() {
    reloadPreview();
  }

  export function getSelectedPaths(): string[] {
    return [...selectedPaths];
  }

  export function clearSelectedPaths() {
    selectedPaths = [];
  }
</script>

<svelte:window
  on:pointerup={endRangeSelection}
  on:pointercancel={endRangeSelection}
/>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<div
  class="overlay"
  role="presentation"
  on:dragover|preventDefault
  on:drop|preventDefault={(e) => {
    const t = e.target as HTMLElement | null;
    if (t?.closest(".modal--dest")) return;
    const raw = e.dataTransfer?.getData("application/x-om-preview-paths") ?? "";
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        selectedPaths = parsed.map((x) => String(x)).filter((x) => x.trim().length > 0);
        dispatch("dropToRoute", { paths: selectedPaths });
      }
    } catch {
      /* ignore */
    }
  }}
  on:click|self={() => dispatch("close")}
  on:keydown={(e) => {
    if (e.key === "Escape") dispatch("close");
  }}
>
  <div
    class="modal modal--dest om-panel om-panel--lift"
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-labelledby="dest-preview-title"
    on:click|stopPropagation
    on:keydown|stopPropagation
  >
    <header class="modal__head">
      <strong id="dest-preview-title">{destPath}</strong>
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--close"
        aria-label={t("common.closeModalAria")}
        title={t("common.close")}
        on:click={() => dispatch("close")}>✕</button
      >
    </header>

    <div
      class="modal__scroll dest-preview-scroll"
      bind:this={scrollEl}
      on:scroll={onScroll}
      on:pointermove={onScrollPointerMove}
    >
      {#if floatActive}
        <div class="selection-float-rail">
          <div
            class="selection-float selection-float--gallery-tr app-chrome"
            role="toolbar"
            aria-label={t("selection.previewToolbarAria")}
          >
            <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectAll}
              >{t("selection.page")}</button
            >
            <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearSelection}
              >{t("selection.remove")}</button
            >
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--mini"
              disabled={selectedCount === 0}
              on:click={() => dispatch("deleteSelected")}
              >{t("selection.delete")}</button
            >
            <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertSelection}
              >{t("selection.invert")}</button
            >
            <span class="selection-float__count" title={t("selection.selectedTitle")}>{selectedCount}</span>
          </div>
        </div>
      {/if}

      {#if loading && items.length === 0}
        <p class="dest-preview-status">{t("destPreview.loading")}</p>
      {:else if loadError}
        <p class="dest-preview-status dest-preview-status--error">{loadError}</p>
      {:else if items.length === 0}
        <p class="dest-preview-status">{t("destPreview.empty")}</p>
      {:else}
        <div
          class="grid-virtual dest-preview-grid"
          style={`height:${virtualLayout.totalHeight}px;--cell:${virtualLayout.cellSize}px;--grid-edge-pad:${EDGE_PAD}px;--thumb-gap:${thumbGapPx}px`}
        >
          {#each visibleEntries as entry (entry.item.path)}
            {@const it = items.find((x) => x.path === entry.item.path)}
            {#if it}
              <!-- svelte-ignore a11y_interactive_supports_focus -->
              <div
                role="button"
                tabindex="0"
                class="tile dest-preview-tile gallery-virtual-item"
                class:selected={selectedPaths.includes(it.path)}
                data-preview-path={it.path}
                style={`position:absolute;box-sizing:border-box;${entryStyle(entry.top, entry.left, entry.width, entry.height)}`}
                draggable={selectedCount > 0}
                on:pointerdown={(e) => onTilePointerDown(e, it)}
                on:pointerenter={() => onTilePointerEnter(it.path)}
                on:dragstart={(e) => onTileDragStart(e, it)}
                on:click={() => onTileClick(it)}
                on:contextmenu={(e) => onTileContextMenu(e, it)}
                on:dblclick|stopPropagation={() => dispatch("zoom", { item: it, navItems: items })}
                on:keydown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onTileClick(it);
                  }
                }}
              >
                {#if it.thumbDataUrl}
                  <ThumbImage
                    itemPath={it.path}
                    thumbDataUrl={it.thumbDataUrl}
                    thumbQuality={it.thumbQuality}
                  />
                {:else}
                  <div class="folder-ph">
                    <span class="tile-svg-ph" aria-hidden="true">…</span>
                  </div>
                {/if}
                {#if showThumbLabels}<span class="tile__name">{it.name}</span>{/if}
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .dest-preview-status {
    margin: var(--om-space-4);
    font-size: 0.875rem;
    color: var(--om-text-muted);
    text-align: center;
  }

  .dest-preview-status--error {
    color: var(--om-danger, #f87171);
  }

  .dest-preview-grid {
    position: relative;
    width: 100%;
  }

  .dest-preview-scroll {
    padding-top: var(--om-space-2);
    scrollbar-gutter: stable;
  }

  .selection-float-rail {
    position: sticky;
    top: var(--om-space-2);
    z-index: 8;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    /* Padding derecho extra: evita recorte del chip y respeta la barra de scroll. */
    padding: 0 var(--om-space-3) 0 var(--om-space-2);
    margin-bottom: -2.65rem;
    pointer-events: none;
  }

  .dest-preview-scroll > .selection-float-rail > :global(.selection-float.selection-float--gallery-tr) {
    pointer-events: auto;
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-1);
    flex-wrap: nowrap;
    white-space: nowrap;
    max-width: min(560px, calc(100% - var(--om-space-4)));
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-md);
    background: rgb(8 10 18 / 0.92);
    border: 1px solid rgb(255 255 255 / 0.12);
    box-shadow: 0 10px 28px rgb(0 0 0 / 0.42);
    overflow: visible;
  }

  .dest-preview-scroll > .selection-float-rail > :global(.selection-float.selection-float--gallery-tr .om-btn--mini) {
    flex-shrink: 0;
  }

  .selection-float__count {
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 1.25rem;
    text-align: center;
    padding: 0 var(--om-space-1);
    margin-inline-start: var(--om-space-1);
    color: var(--om-accent-2);
    flex-shrink: 0;
  }
</style>
