<script lang="ts">
  import { t } from '../lib/i18n';

  // Bindings y estado
  export let previewZoomOpen: boolean;
  export let previewZoomCarouselVisible: boolean;
  export let previewZoomName: string;
  export let previewZoomMode: string;
  export let previewZoomScale: number;
  export let previewZoomMediaType: string;
  export let zoomEditMode: boolean;
  export let zoomCropMode: boolean;
  export let previewZoomDestMode: boolean;
  export let previewZoomFileUrl: string | null;
  export let previewZoomDataUrl: string | null;
  export let zoomImgTransform: string;
  export let zoomHudVisible: boolean;
  export let zoomMiniRect: string;
  export let zoomCropMarqueeStyle: string | null;
  export let destRows: any[];
  export let draggedDestIdx: number;
  export let previewZoomCanUndoMove: boolean;
  export let zoomNavItems: any[];
  export let previewZoomPath: string;
  export let previewPanX: number;
  export let previewPanY: number;
  export let previewFillWidthAlignPending: boolean;

  // Referencias a elementos DOM
  export let zoomStageEl: HTMLDivElement | null;
  export let zoomVideoEl: HTMLVideoElement | null;
  export let zoomImgEl: HTMLImageElement | null;
  export let zoomMiniEl: HTMLDivElement | null;
  export let zoomCarouselEl: HTMLDivElement | null;

  // Funciones de control
  export let moveZoomBy: (dir: number) => void;
  export let clampPanToStage: () => void;
  export let alignFillWidthToTop: () => void;
  export let zoomStep: (step: number) => void;
  export let applyZoomRotate: (deg: number) => void;
  export let applyZoomCrop: () => void;
  export let openConfirmDelete: (title: string, msg: string, action: () => void) => void;
  export let deleteCurrentZoomImage: () => void;
  export let zoomWithWheel: (e: WheelEvent) => void;
  export let beginPan: (e: PointerEvent) => void;
  export let movePan: (e: PointerEvent) => void;
  export let endPan: (e: PointerEvent) => void;
  export let onZoomStageClick: (e: MouseEvent) => void;
  export let onZoomImageClick: (e: MouseEvent) => void;
  export let onZoomVideoMeta: () => void;
  export let onZoomImageLoad: () => void;
  export let onCropPointerDown: (e: PointerEvent) => void;
  export let onCropPointerMove: (e: PointerEvent) => void;
  export let onCropPointerUp: (e: PointerEvent) => void;
  export let openAddDestForm: () => void;
  export let undoLastZoomMove: () => void;
  export let requestMoveCurrentZoomToDestination: (path: string) => void;
  export let onDestContextMenu: (e: MouseEvent, idx: number, mode: string) => void;
  export let onDestChipDragStart: (e: DragEvent, idx: number) => void;
  export let onDestChipDragEnd: () => void;
  export let onDestDrop: (e: DragEvent, path: string) => void;
  export let openPreviewZoom: (it: any, opts: any) => void;
</script>

{#if previewZoomOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div
    class="overlay overlay--zoom"
    role="button"
    tabindex="-1"
    aria-label={t("zoom.fullscreenCloseAria")}
    on:click|self={() => (previewZoomOpen = false)}
    on:keydown={(e) => {
      if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        previewZoomOpen = false;
      }
    }}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="zoom-fullscreen-root">
      <!-- Capa 1: Backdrop (Clic para cerrar) -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div 
        class="zoom-backdrop" 
        on:click={onZoomStageClick}
      ></div>

      <!-- Capa 2: Contenido (Imagen/Video centrados) -->
      <div class="zoom-content-layer" style="position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important; display: flex !important; justify-content: center !important; align-items: center !important; pointer-events: none !important; z-index: 105 !important; background: transparent !important;" on:wheel={zoomWithWheel}>
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div 
          class="zoom-transform-wrapper"
          style={`transform: ${zoomImgTransform}; transform-origin: center center !important; display: flex !important; justify-content: center !important; align-items: center !important; pointer-events: auto !important; will-change: transform;`}
          on:click|stopPropagation={onZoomImageClick}
        >
          {#if (previewZoomMediaType === "video" && previewZoomFileUrl) || (previewZoomMediaType === "svg" && previewZoomFileUrl) || previewZoomDataUrl}
            {#if previewZoomMediaType === "video" && previewZoomFileUrl}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video
                class="zoom-modal__img"
                style="flex: 0 0 auto !important; max-width: 95vw !important; max-height: 95vh !important; width: auto !important; height: auto !important; object-fit: contain !important;"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                bind:this={zoomVideoEl}
                src={previewZoomFileUrl}
                controls
                playsinline
                preload="metadata"
                on:loadedmetadata={onZoomVideoMeta}
              ></video>
            {:else if previewZoomMediaType === "svg" && previewZoomFileUrl}
              <img
                class="zoom-modal__img"
                style="flex: 0 0 auto !important; max-width: 95vw !important; max-height: 95vh !important; width: auto !important; height: auto !important; object-fit: contain !important;"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                bind:this={zoomImgEl}
                src={previewZoomFileUrl}
                alt={previewZoomName}
                on:load={onZoomImageLoad}
              />
            {:else if previewZoomDataUrl}
              <img
                class="zoom-modal__img"
                style="flex: 0 0 auto !important; max-width: 95vw !important; max-height: 95vh !important; width: auto !important; height: auto !important; object-fit: contain !important;"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                bind:this={zoomImgEl}
                src={previewZoomDataUrl}
                alt={previewZoomName}
                on:load={onZoomImageLoad}
              />
            {/if}
          {/if}
        </div>
      </div>

      <!-- Capa 3: Interfaz (HUD) -->
      {#if zoomHudVisible}
        <header class="zoom-modal__head">
          <div class="zoom-modal__info">
            <strong>{previewZoomName}</strong>
          </div>
          <div class="zoom-modal__tools">
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => moveZoomBy(-1)}>←</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => moveZoomBy(1)}>→</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              on:click={() => {
                previewZoomMode = previewZoomMode === "fit" ? "fillWidth" : "fit";
                previewPanX = 0;
                previewPanY = 0;
                clampPanToStage();
                if (previewZoomMode === "fillWidth") alignFillWidthToTop();
              }}
            >
              {previewZoomMode === "fit" ? t("zoom.modeFit") : t("zoom.modeFillWidth")}
            </button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => zoomStep(-0.2)}>−</button>
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              on:click={() => (previewZoomScale = 1)}
            >{Math.round(previewZoomScale * 100)}%</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => zoomStep(0.2)}>＋</button>
            <button type="button" class="om-btn om-btn--ghost om-btn--compact zoom-trash-btn" on:click={() => openConfirmDelete(t("confirm.deleteImageTitle"), t("confirm.deleteImageDetail"), deleteCurrentZoomImage)}>
              <i class="codicon codicon-trash"></i>
            </button>
            <button type="button" class="om-btn om-btn--ghost om-btn--close" on:click={() => (previewZoomOpen = false)}>✕</button>
          </div>
        </header>

        {#if previewZoomCarouselVisible}
          <div class="zoom-modal__carousel" bind:this={zoomCarouselEl}>
            {#each zoomNavItems as it}
              <button
                type="button"
                class="zoom-carousel__item"
                class:zoom-carousel__item--active={it.path === previewZoomPath}
                on:click={() => openPreviewZoom(it, { preserveCarousel: true, preserveMode: true, navItems: zoomNavItems })}
              >
                {#if it.thumbDataUrl}
                  <img src={it.thumbDataUrl} alt={it.name} />
                {/if}
              </button>
            {/each}
          </div>
        {/if}

        <div class="zoom-mini" bind:this={zoomMiniEl}>
          <img
            src={previewZoomMediaType === "svg" ? previewZoomFileUrl : previewZoomDataUrl}
            alt="Mini"
            loading="lazy"
          />
          <div class="zoom-mini__rect" style={zoomMiniRect}></div>
        </div>

        {#if previewZoomDestMode}
          <div class="zoom-dest-chips" class:zoom-dest-chips--carousel-hidden={!previewZoomCarouselVisible}>
            {#each destRows as dest}
              <button class="zoom-dest-chip" on:click={() => requestMoveCurrentZoomToDestination(dest.path)}>
                {dest.label}
              </button>
            {/each}
            <button class="zoom-dest-chip zoom-dest-chip--add" on:click={openAddDestForm}>+</button>
          </div>
        {/if}
      {/if}
    </div>
  </div>
{/if}

<style>
.zoom-carousel__svg-ph {
    display: grid;
    place-items: center;
    width: 100%;
    min-height: 2.25rem;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--om-text-secondary);
    background: rgb(124 140 255 / 0.12);
    border-radius: var(--om-radius-sm);
  }
.zoom-carousel__video-ph {
    display: grid;
    place-items: center;
    width: 100%;
    min-height: 2.25rem;
    font-size: 0.95rem;
    color: var(--om-text-secondary);
    background: rgb(0 0 0 / 0.28);
    border-radius: var(--om-radius-sm);
  }
.zoom-fullscreen-root {
    position: absolute;
    inset: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
  }
  .zoom-backdrop {
    position: absolute;
    inset: 0;
    z-index: 100;
    cursor: zoom-out;
  }
  .zoom-fullscreen-root {
    position: fixed;
    inset: 0;
    z-index: 100;
    overflow: hidden;
  }
  .zoom-backdrop {
    position: absolute;
    inset: 0;
    z-index: 101;
    background: transparent;
    cursor: zoom-out;
  }
  .zoom-content-layer {
    position: absolute;
    inset: 0;
    z-index: 105;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
  }
  .zoom-transform-wrapper {
    pointer-events: auto;
    display: flex;
    justify-content: center;
    align-items: center;
    will-change: transform;
  }
  .zoom-modal__head {
    position: absolute;
    top: var(--om-space-4);
    left: var(--om-space-4);
    right: var(--om-space-4);
    z-index: 130;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--om-space-2) var(--om-space-4);
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .zoom-modal__carousel {
    position: absolute;
    bottom: var(--om-space-4);
    left: 50%;
    transform: translateX(-50%);
    z-index: 130;
    width: min(90vw, 1000px);
    display: flex;
    gap: var(--om-space-2);
    padding: var(--om-space-2);
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
    border-radius: var(--om-radius-lg);
    border: 1px solid rgba(255, 255, 255, 0.1);
    overflow-x: auto;
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
.zoom-modal__body {
    position: absolute;
    inset: 0;
    z-index: 110; /* Capa 2: Imagen */
    display: block;
    background: radial-gradient(circle at 50% 50%, rgba(124, 140, 255, 0.1), transparent 80%);
  }
.zoom-modal__stage {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    position: relative;
    background: transparent;
  }
.zoom-crop-layer {
    position: absolute;
    inset: 0;
    z-index: 5;
    cursor: crosshair;
    touch-action: none;
  }
.zoom-crop-marquee {
    position: absolute;
    box-sizing: border-box;
    border: 2px solid rgb(255 255 255 / 0.95);
    box-shadow: 0 0 0 1px rgb(0 0 0 / 0.45) inset;
    pointer-events: none;
  }
  .zoom-fullscreen-root {
    position: fixed;
    inset: 0;
    z-index: 100;
    overflow: hidden;
    background: transparent;
  }
  .zoom-backdrop {
    position: absolute;
    inset: 0;
    z-index: 101;
    background: transparent;
    cursor: zoom-out;
  }
  .zoom-content-layer {
    position: absolute;
    inset: 0;
    z-index: 105;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
  }
  .zoom-transform-wrapper {
    pointer-events: auto;
    display: flex;
    justify-content: center;
    align-items: center;
    will-change: transform;
    transform-origin: center center;
  }
  .zoom-modal__img {
    flex: 0 0 auto;
    max-width: 95vw;
    max-height: 95vh;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: var(--om-radius-md);
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
    background: rgba(0, 0, 0, 0.2);
  }
  .zoom-modal__img--fill-width {
    max-width: none;
    max-height: none;
    width: 100vw;
    height: auto;
  }
  .zoom-modal__img--pannable {
    cursor: grab;
  }
  .zoom-modal__img--pannable:active {
    cursor: grabbing;
  }
.zoom-dest-chips {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: var(--om-space-3);
    z-index: 120;
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
.zoom-modal__carousel {
    position: absolute;
    bottom: var(--om-space-4);
    left: 50%;
    transform: translateX(-50%);
    z-index: 120; /* Capa 3: Interfaz */
    width: min(90vw, 1000px);
    display: flex;
    gap: var(--om-space-2);
    overflow-x: auto;
    overflow-y: hidden;
    padding: var(--om-space-2);
    border-radius: var(--om-radius-lg);
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
.zoom-modal__body {
    position: relative;
    z-index: 1;
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
    border-color: color-mix(in oklab, var(--om-accent) 82%, var(--om-bg-elevated));
    background: color-mix(in oklab, var(--om-accent) 28%, var(--om-surface-2));
    box-shadow:
      0 0 0 2px color-mix(in oklab, var(--om-accent) 65%, transparent),
      0 0 12px var(--om-accent-glow);
  }
.zoom-mini {
    position: absolute;
    right: 12px;
    bottom: 12px;
    z-index: 120; /* Capa 3: Interfaz */
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
</style>
