<script lang="ts">
  import { t } from '../lib/i18n';

  export let galleryGridItems: any[];
  export let gridCellPx: number;
  export let thumbGapPx: number;
  export let dragOverSectionPath: string | null;
  export let galleryKeyboardNavHintActive: boolean;
  export let galleryCursorPath: string | null;
  export let galleryRangeSelecting: boolean;
  export let galleryRangeSuppressClick: boolean;
  export let showThumbLabels: boolean;
  export let galleryScrollAtTop: boolean;
  export let galleryState: any;
  export let destRows: any[];
  export let dragOverDestPath: string | null;
  export let destinationsMode: boolean;
  export let galleryScrollEl: HTMLDivElement | null;
  export let galleryGridEl: HTMLDivElement | null;

  const GALLERY_GRID_EDGE_PAD_PX = 8;

  export let onGalleryScroll: (e: UIEvent) => void;
  export let onSectionFolderDrop: (e: DragEvent, folder: string) => void;
  export let navigateToFolder: (path: string, opts: any) => void;
  export let isGalleryTileSelected: (it: any) => boolean;
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
  export let openAddDestForm: () => void;
  export let onDestCardClick: (e: MouseEvent, path: string) => void;
  export let onDestContextMenu: (e: MouseEvent, idx: number, mode: string) => void;
  export let onDestChipDragStart: (e: DragEvent, idx: number) => void;
  export let onDestChipDragEnd: () => void;
  export let onDestDrop: (e: DragEvent, path: string) => void;
</script>

<article class="gallery om-panel om-panel--lift gallery--with-float">
  <div class="gallery__scroll" bind:this={galleryScrollEl} on:scroll={onGalleryScroll}>
    <div class="grid" bind:this={galleryGridEl} style={`--cell:${gridCellPx}px;--grid-edge-pad:${GALLERY_GRID_EDGE_PAD_PX}px;--thumb-gap:${thumbGapPx}px`}>
    {#each galleryGridItems as it (it.path)}
      {#if it.kind === "section"}
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <div
          class="gallery-section-head"
          class:gallery-section-head--timeline={it.path.includes("section:timeline:")}
          class:gallery-section-head--tinted={Boolean(it.sectionTintHex)}
          class:gallery-section-head--drop={Boolean(it.sectionFolder) && dragOverSectionPath === it.sectionFolder}
          role="separator"
          data-section-folder={it.sectionFolder ?? ""}
          data-item-path={it.path}
          style={it.sectionTintHex ? `--section-tint: ${it.sectionTintHex}` : ""}
          on:dragover|preventDefault={(e) => {
            if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
          }}
          on:drop={(e) => onSectionFolderDrop(e, it.sectionFolder ?? "")}
          on:dblclick|stopPropagation={() => {
            const p = String(it.sectionFolder ?? "").trim();
            if (p) void navigateToFolder(p, { pushHistory: true });
          }}
        >
          <span class="gallery-section-head__title">{it.name}</span>
          {#if it.sectionFolder}
            <span class="gallery-section-head__path">{it.sectionFolder}</span>
          {/if}
        </div>
      {:else if it.kind === "day_break"}
        <div class="timeline-day-break" aria-hidden="true">
          <span class="timeline-day-break__n">{it.name}</span>
        </div>
      {:else}
      <!-- div: en WebEngine <button>+drag y <img draggable> nativo suelen bloquear el DnD. -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_interactive_supports_focus -->
      <div
        role="button"
        tabindex="0"
        class="tile"
        class:tile--active={galleryKeyboardNavHintActive && galleryCursorPath === it.path}
        data-item-path={it.path}
        class:selected={isGalleryTileSelected(it)}
        draggable={isGalleryMediaKind(it.kind) && !galleryRangeSelecting}
        on:pointerdown={(e) => onGalleryTilePointerDown(e, it)}
        on:pointerenter={() => onGalleryTilePointerEnter(it.path)}
        on:dragstart={(e) => onTileDragStart(e, it)}
        on:click={() => {
          if (galleryRangeSuppressClick) return;
          clickItem(it);
        }}
        on:dblclick={() => {
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
        {#if showThumbLabels || !isGalleryMediaKind(it.kind)}<span class="tile__name" class:tile__name--folder={!isGalleryMediaKind(it.kind)}>{it.name}</span>{/if}
      </div>
      {/if}
    {/each}
    <div class="grid-end-spacer" aria-hidden="true"></div>
    </div>
    {#if destinationsMode && galleryScrollAtTop}
      <div class="selection-float selection-float--gallery-tr" role="toolbar" aria-label={t("selection.toolbarGalleryAria")}>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={selectPage}>{t("selection.page")}</button>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={clearSelection}>{t("selection.remove")}</button>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--mini"
          disabled={Number(galleryState.selectedCount || 0) === 0}
          on:click={() =>
            openConfirmDelete(
              t("confirm.deleteSelectionTitle"),
              t("confirm.deleteSelectionDetail").replace("{count}", String(galleryState.selectedCount)),
              deleteSelectedGalleryItems
            )}
        >{t("selection.delete")}</button>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={invertSelection}>{t("selection.invert")}</button>
        <span class="selection-float__count" title={t("selection.selectedTitle")}>{galleryState.selectedCount}</span>
      </div>
    {/if}
  </div>
</article>

<style>
.gallery-section-head {
    grid-column: 1 / -1;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--om-space-2) var(--om-space-4);
    padding: var(--om-space-2) var(--om-space-3);
    margin-top: var(--om-space-2);
    border-radius: var(--om-radius-sm);
    border: 1px dashed var(--om-border-default);
    background: color-mix(in oklab, var(--om-surface-2) 90%, transparent);
    transition: border-color 0.12s ease, background 0.12s ease;
  }
.gallery-section-head--drop {
    border-color: var(--om-accent);
    background: color-mix(in oklab, var(--om-accent-soft) 55%, var(--om-surface-2));
  }
.gallery-section-head--timeline {
    border-style: solid;
    border-color: color-mix(in oklab, var(--om-accent-2) 35%, var(--om-border-default));
  }
.gallery-section-head--tinted {
    background: color-mix(in oklab, var(--section-tint) 28%, var(--om-surface-2));
    border-color: color-mix(in oklab, var(--section-tint) 40%, var(--om-border-default));
  }
.timeline-day-break {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    padding: 2px 4px 0;
    min-height: 1.1rem;
  }
.timeline-day-break__n {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--om-text-muted);
    text-transform: uppercase;
  }
.gallery-section-head__title {
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--om-text-primary);
  }
.gallery-section-head__path {
    font-size: 0.72rem;
    color: var(--om-text-muted);
    word-break: break-all;
  }
/* Misma caja en modo base y Edición: sin padding del panel; el aire va en .gallery__scroll. */
  .gallery.om-panel {
    padding: 0;
  }
.gallery.om-panel.om-panel--lift {
    box-shadow: 0 14px 42px rgb(0 0 0 / 0.52) !important;
    border-color: rgb(255 255 255 / 0.07) !important;
  }
.gallery:not(.gallery--with-float) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
/* Scroll interno: modo Edición (barra selección + destinos) y modo base comparten estilo. */
  .gallery--with-float {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
    position: relative;
  }
.gallery .gallery__scroll {
    overflow: auto;
    display: block;
    min-height: 0;
    padding-top: var(--om-space-2);
    border-radius: inherit;
    background: transparent;
    scrollbar-color: rgb(124 140 255 / 0.18) transparent;
  }
.gallery:not(.gallery--with-float) .gallery__scroll {
    flex: 1;
    padding-bottom: var(--om-space-2);
  }
.gallery--with-float .gallery__scroll {
    flex: 1;
    padding-bottom: max(3.75rem, calc(env(safe-area-inset-bottom, 0px) + 3.25rem));
    position: relative;
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
/* Chip de herramientas: esquina superior derecha sobre la cuadrícula (mismo criterio visual que antes). */
  .gallery--with-float .gallery__scroll > .selection-float.selection-float--gallery-tr {
    position: absolute;
    top: var(--om-space-2);
    right: var(--om-space-2);
    left: auto;
    margin: 0;
    z-index: 6;
    flex-wrap: nowrap;
    white-space: nowrap;
    max-width: min(560px, calc(100% - var(--om-space-4)));
    background: linear-gradient(180deg, rgb(8 10 18 / 0.72), rgb(8 10 18 / 0.48));
    border: 1px solid rgb(255 255 255 / 0.1);
    border-top-color: transparent;
    border-left-color: transparent;
    border-right-color: transparent;
    box-shadow: 0 10px 28px rgb(0 0 0 / 0.42);
    backdrop-filter: blur(10px);
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
/* Fuera del área con scroll: no provoca artefactos ni cortes raros al desplazar. */
  .gallery--with-float > .dest-float-chips {
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
    background: linear-gradient(180deg, rgb(8 10 18 / 0.55), rgb(8 10 18 / 0.88));
    border: 1px solid rgb(255 255 255 / 0.1);
    border-top-color: transparent;
    border-left-color: transparent;
    border-right-color: transparent;
    box-shadow: 0 10px 28px rgb(0 0 0 / 0.42);
    backdrop-filter: blur(10px);
    overflow-x: auto;
    overflow-y: hidden;
    box-sizing: border-box;
  }

.selection-float__count {
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 1.25rem;
    text-align: center;
    padding: 0 var(--om-space-1);
    color: var(--om-accent-2);
  }
.gallery {
    min-height: 0;
    min-width: 0;
    position: relative;
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
/* En modo Edición evita líneas raras en bordes al redimensionar / scroll. */
  .gallery--with-float .grid {
    contain: none;
  }
.grid-end-spacer {
    grid-column: 1 / -1;
    height: 3.6rem;
    pointer-events: none;
  }
.gallery--with-float .grid-end-spacer {
    height: 0;
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
:global(.app.app--tile-flat) .tile {
    background: var(--om-surface-2);
    box-shadow: none;
    border-color: color-mix(in oklab, var(--om-border-default) 85%, transparent);
  }
:global(.app.app--tile-outlined) .tile {
    background: transparent;
    box-shadow: none;
    border-color: color-mix(in oklab, var(--om-accent) 48%, var(--om-border-default));
  }
:global(.app.app--tile-no-frame) .tile {
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
.tile.tile--active {
    box-shadow:
      0 0 0 4px color-mix(in oklab, var(--om-accent) 88%, #ffffff),
      0 0 28px rgb(124 140 255 / 0.62),
      var(--om-shadow-md);
    border-color: color-mix(in oklab, var(--om-accent) 88%, #ffffff);
  }
.tile.tile--active::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    border-radius: inherit;
    background: rgb(70 132 255 / 0.25);
    opacity: 1;
  }
.tile.tile--active img,
  .tile.tile--active .folder-ph {
    /* Tinte azul real sobre el contenido (funciona igual en LQ/HQ). */
    filter: sepia(0.38) hue-rotate(168deg) saturate(1.85) contrast(1.1) brightness(1.04);
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
    border: none;
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
.tile-video-ph {
    font-size: 1.35rem;
    line-height: 1;
    opacity: 0.88;
  }
.tile-svg-ph {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    opacity: 0.9;
  }
.gallery-item-ctx-menu {
    min-width: 12rem;
  }
.gallery-item-ctx-menu__section {
    font-size: 0.6875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--om-text-muted);
    padding: var(--om-space-1) var(--om-space-3) var(--om-space-1);
    margin-top: var(--om-space-1);
  }
.gallery-item-ctx-menu__hint {
    font-size: 0.6875rem;
    color: var(--om-text-muted);
    padding: 0 var(--om-space-3) var(--om-space-2);
  }
.gallery-file-info__path {
    font-size: 0.75rem;
    word-break: break-all;
    color: var(--om-text-secondary);
    margin: 0 0 var(--om-space-3);
    line-height: 1.4;
  }
.gallery-file-info__meta {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
    font-size: 0.8125rem;
  }
</style>
