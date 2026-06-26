<script lang="ts">
  import { onDestroy } from "svelte";
  import {
    buildScrollRailLabels,
    contentYFromGutterRatio,
    gutterRatioFromClientY,
    scrollMarkerAtContentY,
    type GalleryScrollRailLabel,
  } from "../lib/galleryScrollRail";
  import type { GalleryScrollMarker } from "../lib/galleryFullVirtualLayout";

  export let markers: GalleryScrollMarker[] = [];
  export let totalHeight = 0;
  export let scrollTop = 0;
  export let scrollViewportH = 0;
  export let cellSize = 96;

  export let onJumpToMarker: (marker: GalleryScrollMarker) => void = () => {};

  let gutterEl: HTMLDivElement | null = null;
  let gutterHeightPx = 0;
  let hoverMarker: GalleryScrollMarker | null = null;
  let hoverPercent = -1;
  let gutterHover = false;
  let gutterObserver: ResizeObserver | null = null;

  $: railHeightPx = gutterHeightPx > 0 ? gutterHeightPx : scrollViewportH;
  $: railLabels = buildScrollRailLabels(markers, cellSize, totalHeight, railHeightPx);
  $: activeMarker = scrollMarkerAtContentY(
    markers,
    scrollTop + Math.min(96, scrollViewportH * 0.18),
  );

  function syncGutterObserver(el: HTMLDivElement | null) {
    gutterObserver?.disconnect();
    gutterObserver = null;
    if (!el || typeof ResizeObserver === "undefined") return;
    gutterHeightPx = el.clientHeight;
    gutterObserver = new ResizeObserver(() => {
      gutterHeightPx = el.clientHeight;
    });
    gutterObserver.observe(el);
  }

  $: syncGutterObserver(gutterEl);

  onDestroy(() => {
    gutterObserver?.disconnect();
    gutterObserver = null;
  });

  /** Hover sobre el rail o la barra de scroll nativa (desde GalleryGrid). */
  export function pointerOnRail(clientY: number, trackTop: number, trackHeight: number) {
    if (totalHeight <= 0 || trackHeight <= 0) return;
    gutterHover = true;
    const ratio = gutterRatioFromClientY(clientY, trackTop, trackHeight);
    hoverPercent = Math.round(ratio * 1000) / 10;
    hoverMarker = scrollMarkerAtContentY(markers, contentYFromGutterRatio(ratio, totalHeight));
  }

  export function clearRailHover() {
    gutterHover = false;
    hoverMarker = null;
    hoverPercent = -1;
  }

  function markerAtTrackY(clientY: number, trackTop: number, trackHeight: number): GalleryScrollMarker | null {
    if (totalHeight <= 0 || trackHeight <= 0) return null;
    const ratio = gutterRatioFromClientY(clientY, trackTop, trackHeight);
    return scrollMarkerAtContentY(markers, contentYFromGutterRatio(ratio, totalHeight));
  }

  function handleGutterMove(e: MouseEvent) {
    if (!gutterEl) return;
    const rect = gutterEl.getBoundingClientRect();
    pointerOnRail(e.clientY, rect.top, rect.height);
  }

  function handleGutterLeave() {
    clearRailHover();
  }

  function handleGutterClick(e: MouseEvent) {
    if (!gutterEl) return;
    const rect = gutterEl.getBoundingClientRect();
    const marker = markerAtTrackY(e.clientY, rect.top, rect.height);
    if (marker) onJumpToMarker(marker);
  }

  function handleLabelClick(label: GalleryScrollRailLabel) {
    onJumpToMarker(label.marker);
  }

  function labelTopPercent(top: number): number {
    if (totalHeight <= 0) return 0;
    return Math.round((top / totalHeight) * 1000) / 10;
  }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div
  class="gallery-scroll-gutter"
  class:gallery-scroll-gutter--hover={gutterHover}
  aria-hidden={markers.length === 0}
  bind:this={gutterEl}
  on:mousemove={handleGutterMove}
  on:mouseleave={handleGutterLeave}
  on:click={handleGutterClick}
>
  {#each railLabels as label (`${label.startIndex}-${label.top}`)}
    <button
      type="button"
      class="gallery-scroll-gutter__label"
      class:gallery-scroll-gutter__label--active={activeMarker?.startIndex === label.startIndex}
      style={`top:${labelTopPercent(label.top)}%`}
      title={label.marker.label}
      aria-label={label.marker.label}
      on:click|stopPropagation={() => handleLabelClick(label)}
    >
      {label.label}
    </button>
  {/each}

  {#if gutterHover && hoverMarker && hoverPercent >= 0}
    <div class="gallery-scroll-gutter__hint" style={`top:${hoverPercent}%`}>
      {hoverMarker.label}
    </div>
  {/if}
</div>

<style>
  .gallery-scroll-gutter {
    position: absolute;
    top: var(--om-space-2);
    right: 0;
    bottom: 0;
    width: 76px;
    z-index: 4;
    pointer-events: auto;
    cursor: pointer;
    overflow: visible;
  }

  .gallery-scroll-gutter__label {
    position: absolute;
    right: 18px;
    margin: 0;
    padding: 2px 5px;
    border: 1px solid rgb(255 255 255 / 0.1);
    border-radius: var(--om-radius-sm);
    background: rgb(8 10 18 / 0.74);
    box-shadow: 0 1px 4px rgb(0 0 0 / 0.28);
    transform: translateY(-50%);
    font-size: 0.6rem;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
    letter-spacing: 0;
    color: rgb(218 223 235 / 0.94);
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.55);
    text-align: right;
    white-space: nowrap;
    overflow: visible;
    cursor: pointer;
    pointer-events: auto;
    transition:
      color 0.15s ease,
      opacity 0.15s ease,
      background 0.15s ease,
      border-color 0.15s ease;
    z-index: 1;
  }

  .gallery-scroll-gutter__label:hover,
  .gallery-scroll-gutter__label:focus-visible {
    color: rgb(180 248 232 / 0.98);
    background: rgb(8 10 18 / 0.86);
    border-color: rgb(94 228 212 / 0.26);
    outline: none;
    z-index: 3;
  }

  .gallery-scroll-gutter__label--active,
  .gallery-scroll-gutter--hover .gallery-scroll-gutter__label--active {
    color: rgb(196 205 255 / 0.98);
    background: rgb(8 10 18 / 0.84);
    border-color: rgb(124 140 255 / 0.32);
    z-index: 2;
  }

  .gallery-scroll-gutter--hover .gallery-scroll-gutter__label:not(.gallery-scroll-gutter__label--active) {
    opacity: 0.78;
  }

  .gallery-scroll-gutter__hint {
    position: absolute;
    right: calc(100% + 8px);
    transform: translateY(-50%);
    padding: 5px 10px;
    border-radius: var(--om-radius-sm);
    background: rgb(8 10 18 / 0.96);
    border: 1px solid rgb(255 255 255 / 0.16);
    box-shadow: 0 4px 16px rgb(0 0 0 / 0.4);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--om-accent-2);
    white-space: nowrap;
    pointer-events: none;
    z-index: 6;
  }
</style>
