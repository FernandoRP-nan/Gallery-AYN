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
  export let previewPanDrag = false;
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
  export let togglePreviewZoomMode: () => void;
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
  export let onZoomVideoError: (e: Event) => void;
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
    class:overlay--zoom-interacting={previewPanDrag}
    role="presentation"
    aria-label={t("zoom.fullscreenCloseAria")}
    on:click={(e) => {
      if (e.target === e.currentTarget) previewZoomOpen = false;
    }}
    on:keydown={(e) => {
      if (e.key === "Escape") {
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
          <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.prevNavTitle")} on:click={() => moveZoomBy(-1)}>←</button>
          <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.nextNavTitle")} on:click={() => moveZoomBy(1)}>→</button>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--compact"
            title={t("zoom.toggleFitTitle")}
            on:click={togglePreviewZoomMode}
          >
            {previewZoomMode === "fit" ? t("zoom.modeFit") : t("zoom.modeFillWidth")}
          </button>
          <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.zoomOutTitle")} on:click={() => zoomStep(-0.2)}>−</button>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--compact"
            title={t("zoom.zoomResetTitle")}
            on:click={() => {
              previewZoomScale = 1;
              previewPanX = 0;
              previewPanY = 0;
            }}
          >{Math.round(previewZoomScale * 100)}%</button>
          <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.zoomInTitle")} on:click={() => zoomStep(0.2)}>＋</button>
          {#if previewZoomMediaType === "image"}
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              class:om-btn--active={zoomEditMode}
              title={t("zoom.editToggle")}
              on:click={() => {
                const next = !zoomEditMode;
                zoomEditMode = next;
                if (!next) zoomCropMode = false;
              }}
            >✎</button>
            {#if zoomEditMode}
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact"
                title={t("zoom.rotateLeft")}
                on:click={() => void applyZoomRotate(-90)}
              >↺</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact"
                title={t("zoom.rotateRight")}
                on:click={() => void applyZoomRotate(90)}
              >↻</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact"
                class:om-btn--active={zoomCropMode}
                title={t("zoom.cropToggle")}
                on:click={() => (zoomCropMode = !zoomCropMode)}
              >▢</button>
            {/if}
            {#if zoomCropMode}
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact"
                title={t("zoom.applyCrop")}
                on:click={() => void applyZoomCrop()}
              >{t("zoom.applyCropBtn")}</button>
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact"
                title={t("zoom.cancelCrop")}
                on:click={() => (zoomCropMode = false)}
              >{t("zoom.cancelCropBtn")}</button>
            {/if}
          {/if}
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--compact"
            title={t("zoom.destinationsFullscreenTitle")}
            on:click={() => (previewZoomDestMode = !previewZoomDestMode)}
          >{t("zoom.destinationsBtn")}</button>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--compact zoom-trash-btn"
            title={t("zoom.deleteCurrentTitle")}
            on:click={() =>
              openConfirmDelete(t("confirm.deleteImageTitle"), t("confirm.deleteImageDetail"), deleteCurrentZoomImage)}
          >
            <svg class="trash-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18" />
              <path d="M8 6V4h8v2" />
              <path d="M6 6l1 14h10l1-14" />
              <path d="M10 11v6" />
              <path d="M14 11v6" />
            </svg>
          </button>
          <button
            type="button"
            class="om-btn om-btn--ghost om-btn--close"
            aria-label={t("common.closeModalAria")}
            title={t("common.close")}
            on:click={() => (previewZoomOpen = false)}>✕</button
          >
        </div>
      </header>
      <div class="zoom-modal__body" on:wheel={zoomWithWheel}>
        {#if (previewZoomMediaType === "video" && previewZoomFileUrl) || (previewZoomMediaType === "svg" && previewZoomFileUrl) || previewZoomDataUrl}
          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <div
            class="zoom-modal__stage"
            role="application"
            aria-label={t("zoom.stageAria")}
            bind:this={zoomStageEl}
            on:pointerdown={beginPan}
            on:pointermove={movePan}
            on:pointerup={endPan}
            on:pointercancel={endPan}
            on:click={onZoomStageClick}
          >
            {#if previewZoomMediaType === "video" && previewZoomFileUrl}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video
                class="zoom-modal__img"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                class:zoom-modal__img--interacting={previewPanDrag}
                bind:this={zoomVideoEl}
                src={previewZoomFileUrl}
                controls
                playsinline
                preload="auto"
                on:loadedmetadata={onZoomVideoMeta}
                on:error={onZoomVideoError}
              ></video>
            {:else if previewZoomMediaType === "svg" && previewZoomFileUrl}
              <img
                class="zoom-modal__img"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                class:zoom-modal__img--interacting={previewPanDrag}
                bind:this={zoomImgEl}
                src={previewZoomFileUrl}
                alt={previewZoomName}
                on:click={onZoomImageClick}
                on:load={onZoomImageLoad}
              />
            {:else if previewZoomDataUrl}
              <img
                class="zoom-modal__img"
                class:zoom-modal__img--fill-width={previewZoomMode === "fillWidth"}
                class:zoom-modal__img--pannable={previewZoomScale > 1 || previewZoomMode === "fillWidth"}
                class:zoom-modal__img--interacting={previewPanDrag}
                bind:this={zoomImgEl}
                src={previewZoomDataUrl}
                alt={previewZoomName}
                on:click={onZoomImageClick}
                on:load={onZoomImageLoad}
              />
            {/if}
            {#if zoomHudVisible && !previewPanDrag}
              <div class="zoom-mini" bind:this={zoomMiniEl}>
                <img
                  src={previewZoomMediaType === "svg" ? previewZoomFileUrl : previewZoomDataUrl}
                  alt=""
                />
                <div class="zoom-mini__rect" style={zoomMiniRect}></div>
              </div>
            {/if}
            {#if zoomCropMode && previewZoomDataUrl}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="zoom-crop-layer"
                on:pointerdown={onCropPointerDown}
                on:pointermove={onCropPointerMove}
                on:pointerup={onCropPointerUp}
                on:pointercancel={onCropPointerUp}
                on:click|stopPropagation
              >
                {#if zoomCropMarqueeStyle}
                  <div class="zoom-crop-marquee" style={zoomCropMarqueeStyle} aria-hidden="true"></div>
                {/if}
              </div>
            {/if}
            {#if previewZoomDestMode}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="zoom-dest-chips"
                class:zoom-dest-chips--carousel-hidden={!previewZoomCarouselVisible}
                on:pointerdown|stopPropagation={() => undefined}
                on:click|stopPropagation={() => undefined}
              >
                <button
                  type="button"
                  class="om-btn om-btn--ghost om-btn--compact zoom-dest-add"
                  on:pointerdown|stopPropagation={() => undefined}
                  on:click={openAddDestForm}
                >+</button>
                <button
                  type="button"
                  class="om-btn om-btn--ghost om-btn--compact"
                  disabled={!previewZoomCanUndoMove}
                  on:click={undoLastZoomMove}
                >Deshacer</button>
                {#each destRows as d, i (d.path + "\0zoom\0" + i)}
                  <button
                    type="button"
                    class="zoom-dest-chip"
                    class:zoom-dest-chip--dragging={draggedDestIdx === i}
                    data-dest-path={d.path}
                    title={d.path}
                    draggable={true}
                    on:click={() => requestMoveCurrentZoomToDestination(d.path)}
                    on:contextmenu={(e) => onDestContextMenu(e, i, "fullscreen")}
                    on:dragstart={(e) => onDestChipDragStart(e, i)}
                    on:dragend={onDestChipDragEnd}
                    on:dragenter|preventDefault
                    on:dragover|preventDefault
                    on:drop={(e) => onDestDrop(e, d.path)}
                  >{d.label}</button>
                {/each}
              </div>
            {/if}
          </div>
        {:else}
          <div class="preview__empty">{t("zoom.previewLoading")}</div>
        {/if}
      </div>
      <div
        class="zoom-modal__carousel"
        class:zoom-modal__carousel--hidden={!previewZoomCarouselVisible}
        aria-label={t("zoom.carouselAria")}
        bind:this={zoomCarouselEl}
      >
        {#each zoomNavItems as it}
          <button
            type="button"
            class="zoom-carousel__item"
            class:zoom-carousel__item--active={it.path === previewZoomPath}
            title={it.name}
            on:click={() => openPreviewZoom(it, { preserveCarousel: true, preserveMode: true, navItems: zoomNavItems })}
          >
            {#if it.thumbDataUrl}
              <img src={it.thumbDataUrl} alt={it.name} class:thumb--lq={it.thumbQuality === "lq"} />
            {:else if it.path.toLowerCase().endsWith(".svg")}
              <span class="zoom-carousel__svg-ph" aria-hidden="true">SVG</span>
            {:else if it.kind === "video"}
              <span class="zoom-carousel__video-ph" aria-hidden="true">▶</span>
            {/if}
          </button>
        {/each}
      </div>
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
.zoom-modal {
    width: 100%;
    height: 100%;
    max-width: 100vw;
    max-height: 100vh;
    max-height: 100dvh;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: var(--om-space-1);
    overflow: hidden;
    min-height: 0;
    min-width: 0;
  }
.zoom-modal--carousel-hidden {
    gap: 0;
    grid-template-rows: auto minmax(0, 1fr);
  }
.zoom-modal__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--om-space-2);
    padding: var(--om-space-1) var(--om-space-1);
    color: var(--om-text-primary);
    overflow: visible;
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
    min-width: 0;
    min-height: 0;
    width: 100%;
    height: 100%;
    max-height: 100%;
    display: block;
    overflow: hidden;
    border-radius: 0;
    background: transparent;
    position: relative;
    z-index: 1;
  }
.zoom-modal__stage {
    width: 100%;
    height: 100%;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    cursor: default;
    position: relative;
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
.zoom-dest-chips {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: var(--om-space-3);
    z-index: 7;
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
.zoom-modal__img {
    position: absolute;
    left: 50%;
    top: 50%;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 0;
    box-shadow: none;
    background: transparent;
    transform-origin: center center;
    user-select: none;
    -webkit-user-drag: none;
    touch-action: none;
  }
.zoom-modal__img--interacting {
    transition: none !important;
    will-change: transform;
  }
.zoom-modal__img--fill-width {
    width: 100%;
    height: auto;
    max-width: none;
    max-height: none;
    top: 0;
    transform-origin: top center;
  }
.zoom-modal__img--pannable {
    cursor: grab;
  }
.zoom-modal__img--pannable.zoom-modal__img--interacting {
    cursor: grabbing;
  }
.zoom-modal__carousel {
    display: flex;
    gap: var(--om-space-1);
    overflow-x: auto;
    overflow-y: hidden;
    padding: var(--om-space-1);
    border-radius: 0;
    background: rgb(255 255 255 / 0.04);
    flex: 0 0 auto;
    min-height: 6.75rem;
    position: relative;
    z-index: 5;
  }
.zoom-modal__carousel--hidden {
    display: none;
  }
.zoom-carousel__item {
    border: 1px solid var(--om-border-subtle);
    border-radius: var(--om-radius-sm);
    padding: 0;
    width: 96px;
    height: 96px;
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
