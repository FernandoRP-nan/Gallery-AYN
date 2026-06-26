<script lang="ts">
  import { t } from "../lib/i18n";
  import { videoFormatLabel, isGalleryMediaKind, isGallerySelectableKind } from "../lib/galleryUtils";
  import { hasGalleryThumbHq } from "../lib/galleryThumbHqCache";
  import ThumbImage from "./ThumbImage.svelte";

  export let it: any;
  export let style = "";
  export let masonryLayout = false;
  export let masonrySpan = false;
  export let dragOverSectionPath: string | null;
  export let galleryKeyboardNavHintActive: boolean;
  export let galleryCursorPath: string | null;
  export let galleryFloatChromeActive: boolean;
  export let galleryRangeSelecting: boolean;
  export let galleryRangeSuppressClick: boolean;
  export let galleryRangeDraftSelectedSet: Set<string> | null = null;
  export let showThumbLabels: boolean;
  export let galleryScrolling: boolean;
  export let galleryBusy: boolean;

  export let navigateToFolder: (path: string, opts: any) => void;
  export let onSectionFolderDrop: (e: DragEvent, folder: string) => void;
  export let onGalleryTilePointerDown: (e: PointerEvent, it: any) => void;
  export let onGalleryTilePointerEnter: (path: string) => void;
  export let onTileDragStart: (e: DragEvent, it: any) => void;
  export let clickItem: (it: any) => void;
  export let openZoomFromGallery: (it: any) => void;
  export let onGalleryItemContextMenu: (e: MouseEvent, it: any) => void;
</script>

{#if it.kind === "section"}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="gallery-section-head gallery-virtual-item"
    class:gallery-masonry-span={masonrySpan}
    class:gallery-section-head--timeline={it.path.includes("section:timeline:")}
    class:gallery-section-head--tinted={Boolean(it.sectionTintHex) && !it.path.includes("section:timeline:")}
    class:gallery-section-head--drop={Boolean(it.sectionFolder) && dragOverSectionPath === it.sectionFolder}
    role="separator"
    data-section-folder={it.sectionFolder ?? ""}
    data-item-path={it.path}
    style={it.sectionTintHex && !it.path.includes("section:timeline:") ? `${style};--section-tint: ${it.sectionTintHex}` : style}
    on:dragover|preventDefault={(e) => {
      if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    }}
    on:drop={(e) => onSectionFolderDrop(e, it.sectionFolder ?? "")}
    on:dblclick|stopPropagation={() => {
      const p = String(it.sectionFolder ?? "").trim();
      if (p) void navigateToFolder(p, { pushHistory: true });
    }}
  >
    {#if it.path.includes("section:timeline:")}
      <h3 class="gallery-section-head__title gallery-section-head__title--timeline">{it.name}</h3>
    {:else}
      <span class="gallery-section-head__title">{it.name}</span>
      {#if it.sectionFolder}
        <span class="gallery-section-head__path">{it.sectionFolder}</span>
      {/if}
    {/if}
  </div>
{:else if it.kind === "day_break"}
  <div class="timeline-day-break gallery-virtual-item" class:gallery-masonry-span={masonrySpan} role="separator" aria-label={it.name} {style}>
    <span class="timeline-day-break__n">{it.name}</span>
  </div>
{:else if it.kind === "placeholder"}
  <div
    class="tile tile--placeholder gallery-virtual-item"
    class:tile--masonry={masonryLayout}
    aria-hidden="true"
    {style}
  >
    <span class="tile-placeholder__shimmer"></span>
  </div>
{:else}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_interactive_supports_focus -->
  <div
    role="button"
    tabindex="0"
    class="tile gallery-virtual-item"
    class:tile--masonry={masonryLayout}
    class:tile--active={galleryKeyboardNavHintActive && galleryCursorPath === it.path}
    data-item-path={it.path}
    class:selected={
      galleryFloatChromeActive &&
      isGallerySelectableKind(it.kind) &&
      (galleryRangeSelecting && galleryRangeDraftSelectedSet
        ? galleryRangeDraftSelectedSet.has(it.path)
        : Boolean(it.selected))
    }
    {style}
    draggable={isGalleryMediaKind(it.kind) && !galleryRangeSelecting}
    on:pointerdown={(e) => onGalleryTilePointerDown(e, it)}
    on:pointerenter={() => onGalleryTilePointerEnter(it.path)}
    on:dragstart={(e) => onTileDragStart(e, it)}
    on:click={() => {
      if (galleryRangeSuppressClick) return;
      clickItem(it);
    }}
    on:dblclick|stopPropagation={() => {
      if (it.kind === "folder" || it.kind === "folder_up") {
        void navigateToFolder(it.path, { pushHistory: true });
        return;
      }
      if (isGalleryMediaKind(it.kind)) openZoomFromGallery(it);
    }}
    on:keydown={(e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        clickItem(it);
      }
    }}
    on:contextmenu={(e) => onGalleryItemContextMenu(e, it)}
  >
    {#if it.thumbDataUrl || (isGalleryMediaKind(it.kind) && hasGalleryThumbHq(it.path))}
      <ThumbImage
        itemPath={it.path}
        thumbDataUrl={it.thumbDataUrl ?? ""}
        thumbQuality={it.thumbQuality}
        thumbLqDataUrl={it.thumbLqDataUrl}
        freezeTransitions={galleryScrolling || galleryBusy}
      />
    {:else if it.kind === "folder" && it.folderPreviewUrls && it.folderPreviewUrls.length > 0}
      <div
        class="folder-mosaic"
        class:folder-mosaic--1={it.folderPreviewUrls.length === 1}
        class:folder-mosaic--2={it.folderPreviewUrls.length === 2}
        class:folder-mosaic--3={it.folderPreviewUrls.length === 3}
      >
        {#each it.folderPreviewUrls.slice(0, 4) as url}
          <div class="folder-mosaic__cell">
            {#if url}
              <img src={url} alt="" draggable={false} loading="lazy" decoding="async" />
            {/if}
          </div>
        {/each}
      </div>
      <div class="folder-mosaic__overlay" aria-hidden="true">
        <svg class="folder-ph__svg folder-mosaic__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z" fill="currentColor" />
        </svg>
      </div>
    {:else}
      <div class="folder-ph" class:folder-ph--folder={!isGalleryMediaKind(it.kind)}>
        {#if it.kind === "image" && it.path.toLowerCase().endsWith(".svg")}
          <span class="tile-svg-ph" aria-hidden="true">SVG</span>
        {:else if it.kind === "image"}
          Sin preview
        {:else if it.kind === "video"}
          <span class="tile-video-ph" aria-hidden="true">▶</span>
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
    {#if it.kind === "video"}
      {@const videoFmt = videoFormatLabel(it.path || it.name)}
      {#if videoFmt}
        <span class="tile-video-format" aria-hidden="true">{videoFmt}</span>
      {/if}
    {/if}
    {#if showThumbLabels || !isGalleryMediaKind(it.kind)}
      <span class="tile__name" class:tile__name--folder={!isGalleryMediaKind(it.kind)}>{it.name}</span>
    {/if}
  </div>
{/if}
