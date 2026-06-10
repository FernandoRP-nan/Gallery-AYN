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
        {:else if it.kind === "folder" && it.folderPreviewUrls && it.folderPreviewUrls.length > 0}
          <!-- Mosaico de miniaturas del contenido de la carpeta -->
          <div
            class="folder-mosaic"
            class:folder-mosaic--1={it.folderPreviewUrls.length === 1}
            class:folder-mosaic--2={it.folderPreviewUrls.length === 2}
            class:folder-mosaic--3={it.folderPreviewUrls.length === 3}
          >
            {#each it.folderPreviewUrls.slice(0, 4) as url}
              <div class="folder-mosaic__cell">
                {#if url}
                  <img src={url} alt="" draggable={false} />
                {/if}
              </div>
            {/each}
          </div>
          <!-- Ícono de carpeta flotante sobre el mosaico -->
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
    /* Capa GPU propia: aísla el repaint del fondo para reducir parpadeo. */
    will-change: transform;
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
    /* Capa GPU propia: aísla el repaint del fondo para reducir parpadeo. */
    will-change: transform;
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
/* Mosaico de miniaturas del contenido de carpeta */
.folder-mosaic {
    width: 100%;
    aspect-ratio: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 2px;
    border-radius: var(--thumb-image-radius, var(--om-radius-sm));
    overflow: hidden;
    background: color-mix(in oklab, var(--om-surface-1) 60%, transparent);
    position: relative;
  }
/* 1 imagen: ocupa toda la celda */
.folder-mosaic.folder-mosaic--1 {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr;
  }
/* 2 imágenes: dos columnas, una fila */
.folder-mosaic.folder-mosaic--2 {
    grid-template-rows: 1fr;
  }
/* 3 imágenes: última celda vacía se muestra con fondo */
.folder-mosaic.folder-mosaic--3 .folder-mosaic__cell:last-child {
    background: color-mix(in oklab, var(--om-surface-2) 70%, transparent);
  }
.folder-mosaic__cell {
    background: color-mix(in oklab, var(--om-bg-base) 55%, transparent);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    min-height: 0;
  }
.folder-mosaic__cell img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
/* Overlay: icono de carpeta superpuesto en la esquina inferior izquierda */
.folder-mosaic__overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    justify-content: flex-start;
    padding: 6px;
    pointer-events: none;
    /* Sombra de fondo muy sutil para que el icono sea visible sobre las fotos */
    background: linear-gradient(
      to top,
      rgb(0 0 0 / 0.45) 0%,
      transparent 50%
    );
  }
.folder-mosaic__icon {
    width: 1.1rem;
    height: 1.1rem;
    opacity: 0.85;
    color: #fff;
    filter: drop-shadow(0 1px 3px rgb(0 0 0 / 0.7));
    flex-shrink: 0;
  }
</style>

