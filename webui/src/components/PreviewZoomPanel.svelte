<script lang="ts">
  import { t } from "../lib/i18n";
  import {
    buildImageZoomTransform,
    clampPan,
    getPanLimits,
    pickImageDisplaySrc,
    type ImageZoomMode,
  } from "../lib/imageZoomView";

  export let path = "";
  export let name = "";
  export let fileUrl: string | null = null;
  export let dataUrl: string | null = null;
  export let placeholderUrl: string | null = null;

  const PAN_DRAG_THRESHOLD_PX = 5;

  let mode: ImageZoomMode = "fit";
  let scale = 1;
  let panX = 0;
  let panY = 0;
  let naturalW = 1;
  let naturalH = 1;
  let stageEl: HTMLDivElement | null = null;
  let imgEl: HTMLImageElement | null = null;
  let panPointerDown = false;
  let panDrag = false;
  let panDownX = 0;
  let panDownY = 0;
  let panStartX = 0;
  let panStartY = 0;
  let fillWidthAlignPending = false;
  let trackedPath = "";

  $: if (path !== trackedPath) {
    trackedPath = path;
    mode = "fit";
    scale = 1;
    panX = 0;
    panY = 0;
    naturalW = 1;
    naturalH = 1;
    fillWidthAlignPending = false;
  }

  $: displaySrc = pickImageDisplaySrc(mode, scale, fileUrl, dataUrl);
  $: imgTransform = buildImageZoomTransform(mode, scale, panX, panY);
  $: pannable = scale > 1 || mode === "fillWidth";

  $: if (mode === "fit" && Math.round(scale * 100) === 100) {
    scale = 1;
    panX = 0;
    panY = 0;
  }

  function getStageSize(): { w: number; h: number } | null {
    if (!stageEl) return null;
    const sr = stageEl.getBoundingClientRect();
    return { w: Math.max(1, sr.width), h: Math.max(1, sr.height) };
  }

  function clampPanToStage() {
    const stage = getStageSize();
    if (!stage) return;
    const limits = getPanLimits(mode, stage.w, stage.h, naturalW, naturalH, scale);
    if (limits.x <= 0.5 && limits.y <= 0.5) {
      panX = 0;
      panY = 0;
      return;
    }
    const next = clampPan(mode, panX, panY, limits);
    panX = next.panX;
    panY = next.panY;
  }

  function syncTransform() {
    if (imgEl) imgEl.style.transform = imgTransform;
  }

  function onImageLoad() {
    if (!imgEl) return;
    naturalW = Math.max(1, imgEl.naturalWidth || 1);
    naturalH = Math.max(1, imgEl.naturalHeight || 1);
    if (mode === "fillWidth") {
      panX = 0;
      panY = 0;
      fillWidthAlignPending = false;
    }
    clampPanToStage();
    syncTransform();
  }

  function toggleMode() {
    const next: ImageZoomMode = mode === "fit" ? "fillWidth" : "fit";
    mode = next;
    panX = 0;
    panY = 0;
    scale = 1;
    fillWidthAlignPending = next === "fillWidth";
    clampPanToStage();
    syncTransform();
  }

  function zoomStep(delta: number) {
    scale = Math.min(4, Math.max(0.5, Number((scale + delta).toFixed(2))));
    clampPanToStage();
    syncTransform();
  }

  function zoomWithWheel(e: WheelEvent) {
    e.preventDefault();
    zoomStep(e.deltaY < 0 ? 0.14 : -0.14);
  }

  function beginPan(e: PointerEvent) {
    const el = e.target as HTMLElement;
    if (el.closest("button")) return;
    const stage = getStageSize();
    if (!stage) return;
    const limits = getPanLimits(mode, stage.w, stage.h, naturalW, naturalH, scale);
    if (limits.x <= 0.5 && limits.y <= 0.5) return;
    panPointerDown = true;
    panDrag = false;
    panDownX = e.clientX;
    panDownY = e.clientY;
    if (mode === "fillWidth") {
      panStartY = e.clientY - panY;
    } else {
      panStartX = e.clientX - panX;
      panStartY = e.clientY - panY;
    }
  }

  function movePan(e: PointerEvent) {
    if (!panPointerDown) return;
    if (!panDrag) {
      const dx = e.clientX - panDownX;
      const dy = e.clientY - panDownY;
      if (Math.hypot(dx, dy) < PAN_DRAG_THRESHOLD_PX) return;
      panDrag = true;
      stageEl?.setPointerCapture?.(e.pointerId);
    }
    if (mode === "fillWidth") {
      panX = 0;
      panY = e.clientY - panStartY;
    } else {
      panX = e.clientX - panStartX;
      panY = e.clientY - panStartY;
    }
    clampPanToStage();
    syncTransform();
  }

  function endPan(e: PointerEvent) {
    if (panDrag) stageEl?.releasePointerCapture?.(e.pointerId);
    panPointerDown = false;
    panDrag = false;
    syncTransform();
  }

  $: if (!panDrag && stageEl && imgEl) {
    clampPanToStage();
    if (fillWidthAlignPending && mode === "fillWidth") {
      panX = 0;
      panY = 0;
      fillWidthAlignPending = false;
    }
    syncTransform();
  }
</script>

<div class="preview-zoom-panel">
  <div class="preview-zoom-panel__toolbar">
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact"
      title={t("zoom.toggleFitTitle")}
      on:click={toggleMode}
    >
      {mode === "fit" ? t("zoom.modeFit") : t("zoom.modeFillWidth")}
    </button>
    <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.zoomOutTitle")} on:click={() => zoomStep(-0.2)}>−</button>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact"
      title={t("zoom.zoomResetTitle")}
      on:click={() => {
        scale = 1;
        panX = 0;
        panY = 0;
        clampPanToStage();
        syncTransform();
      }}
    >{Math.round(scale * 100)}%</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--compact" title={t("zoom.zoomInTitle")} on:click={() => zoomStep(0.2)}>＋</button>
  </div>
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="preview-zoom-panel__stage"
    role="application"
    aria-label={t("zoom.stageAria")}
    bind:this={stageEl}
    on:wheel={zoomWithWheel}
    on:pointerdown={beginPan}
    on:pointermove={movePan}
    on:pointerup={endPan}
    on:pointercancel={endPan}
  >
    {#if placeholderUrl && displaySrc && placeholderUrl !== displaySrc}
      <img class="preview-zoom-panel__ph" src={placeholderUrl} alt="" decoding="async" />
    {/if}
    {#if displaySrc}
      <img
        class="preview-zoom-panel__img"
        class:preview-zoom-panel__img--fill-width={mode === "fillWidth"}
        class:preview-zoom-panel__img--pannable={pannable}
        class:preview-zoom-panel__img--interacting={panDrag}
        src={displaySrc}
        alt={name}
        decoding="async"
        bind:this={imgEl}
        on:load={onImageLoad}
        style:transform={imgTransform}
      />
    {/if}
  </div>
</div>

<style>
  .preview-zoom-panel {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
    flex: 1;
    min-height: 0;
    min-width: 0;
  }

  .preview-zoom-panel__toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-1);
    flex: 0 0 auto;
  }

  .preview-zoom-panel__stage {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    border-radius: var(--om-radius-md);
    border: 1px solid var(--om-border-subtle);
    background: var(--om-bg-base);
    touch-action: none;
  }

  .preview-zoom-panel__ph {
    position: absolute;
    inset: 0;
    margin: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    opacity: 0.55;
    pointer-events: none;
  }

  .preview-zoom-panel__img {
    position: absolute;
    left: 50%;
    top: 50%;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transform-origin: center center;
    user-select: none;
    -webkit-user-drag: none;
  }

  .preview-zoom-panel__img--fill-width {
    width: 100%;
    height: auto;
    max-width: none;
    max-height: none;
    top: 0;
    transform-origin: top center;
  }

  .preview-zoom-panel__img--pannable {
    cursor: grab;
  }

  .preview-zoom-panel__img--pannable.preview-zoom-panel__img--interacting {
    cursor: grabbing;
  }

  .preview-zoom-panel__img--interacting {
    transition: none !important;
    will-change: transform;
  }
</style>
