<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { t } from "../lib/i18n";
  import {
    buildGalleryVirtualLayout,
    getVisibleLayoutEntries,
    type VirtualLayoutEntry,
  } from "../lib/galleryVirtualLayout";
  import GalleryGridItem from "./GalleryGridItem.svelte";
  import DestToolbar from "./DestToolbar.svelte";
  import type { DestToolbarItem } from "../lib/itemTree";

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

  const GALLERY_GRID_EDGE_PAD_PX = 8;
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

  let scrollTop = 0;
  let scrollViewportH = 640;
  let scrollViewportW = 640;
  let resizeObserver: ResizeObserver | null = null;

  $: extraBottomPx = destinationsMode ? DEST_BAR_RESERVE_PX : 0;
  $: virtualLayout = buildGalleryVirtualLayout(
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

  function entryStyle(entry: VirtualLayoutEntry): string {
    return `top:${entry.top}px;left:${entry.left}px;width:${entry.width}px;height:${entry.height}px`;
  }

  function handleGalleryScroll(e: UIEvent) {
    const el = e.currentTarget as HTMLDivElement | null;
    if (el) {
      scrollTop = el.scrollTop;
      scrollViewportH = el.clientHeight;
    }
    onGalleryScroll(e);
  }

  function syncScrollMetrics(el: HTMLDivElement | null) {
    if (!el) return;
    scrollTop = el.scrollTop;
    scrollViewportH = el.clientHeight;
    scrollViewportW = el.clientWidth;
  }

  onMount(() => {
    syncScrollMetrics(galleryScrollEl);
    if (!galleryScrollEl || typeof ResizeObserver === "undefined") return;
    resizeObserver = new ResizeObserver(() => syncScrollMetrics(galleryScrollEl));
    resizeObserver.observe(galleryScrollEl);
  });

  onDestroy(() => {
    resizeObserver?.disconnect();
    resizeObserver = null;
  });
</script>

<article
  class="gallery om-panel om-panel--lift"
  class:gallery--with-float={galleryFloatChromeActive}
  class:gallery--with-dest={destinationsMode}
  class:gallery--range-selecting={galleryRangeSelecting}
  class:gallery--scrolling={galleryScrolling}
  class:gallery--busy={galleryBusy}
>
  <div
    class="gallery__scroll"
    class:gallery__scroll--dest={destinationsMode}
    bind:this={galleryScrollEl}
    on:scroll={handleGalleryScroll}
    on:pointermove={onGalleryScrollPointerMove}
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

  :global(.gallery-virtual-item.tile) {
    height: 100%;
    width: 100%;
  }
</style>
