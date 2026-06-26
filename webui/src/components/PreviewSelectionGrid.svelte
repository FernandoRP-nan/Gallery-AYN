<script lang="ts">
  import type { GalleryItem } from "../lib/api";
  import { t } from "../lib/i18n";
  import { videoFormatLabel } from "../lib/galleryUtils";
  import ThumbImage from "./ThumbImage.svelte";

  export let items: GalleryItem[] = [];
  export let activePath: string | null = null;
  export let onSelect: (path: string) => void = () => {};
  export let onRemove: (path: string) => void = () => {};

  function thumbUrl(it: GalleryItem): string {
    return it.thumbDataUrl ?? it.thumbLqDataUrl ?? "";
  }
</script>

<section class="preview-selection-grid" aria-label={t("selection.previewStripAria")}>
  <header class="preview-selection-grid__head">
    <span class="preview-selection-grid__title">{t("selection.previewStripTitle")}</span>
    <span class="preview-selection-grid__count">{items.length}</span>
  </header>
  <div class="preview-selection-grid__items" role="list">
    {#each items as it (it.path)}
      <div class="preview-selection-grid__cell" role="listitem">
        <button
          type="button"
          class="preview-selection-grid__tile"
          class:preview-selection-grid__tile--active={activePath === it.path}
          title={it.name}
          on:click={() => onSelect(it.path)}
        >
          {#if thumbUrl(it)}
            <ThumbImage
              itemPath={it.path}
              thumbDataUrl={thumbUrl(it)}
              thumbQuality={it.thumbQuality}
              thumbLqDataUrl={it.thumbLqDataUrl}
              freezeTransitions={true}
            />
          {:else}
            <span class="preview-selection-grid__ph" aria-hidden="true">{it.name.slice(0, 2)}</span>
          {/if}
          {#if it.kind === "video"}
            <span class="preview-selection-grid__badge">{videoFormatLabel(it.path) ?? "VID"}</span>
          {/if}
        </button>
        <button
          type="button"
          class="preview-selection-grid__remove om-btn om-btn--ghost"
          title={t("selection.previewStripRemove")}
          aria-label={t("selection.previewStripRemove")}
          on:click|stopPropagation={() => onRemove(it.path)}
        >
          ×
        </button>
      </div>
    {/each}
  </div>
</section>

<style>
  .preview-selection-grid {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-top: var(--om-space-2);
    border-top: 1px solid var(--om-border-subtle);
    min-height: 0;
    max-height: min(38vh, 200px);
  }
  .preview-selection-grid__head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 0 2px;
    flex-shrink: 0;
  }
  .preview-selection-grid__title {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }
  .preview-selection-grid__count {
    font-size: 0.68rem;
    color: var(--om-text-muted);
  }
  .preview-selection-grid__items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(56px, 1fr));
    gap: 6px;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 2px;
    min-height: 0;
  }
  .preview-selection-grid__cell {
    position: relative;
    min-width: 0;
  }
  .preview-selection-grid__tile {
    display: block;
    width: 100%;
    aspect-ratio: 1;
    padding: 0;
    margin: 0;
    border: 2px solid transparent;
    border-radius: var(--om-radius-sm);
    overflow: hidden;
    cursor: pointer;
    background: var(--om-surface-2);
    position: relative;
    transition: border-color 0.12s ease, box-shadow 0.12s ease;
  }
  .preview-selection-grid__tile:hover {
    border-color: color-mix(in oklab, var(--om-accent) 45%, var(--om-border-default));
  }
  .preview-selection-grid__tile--active {
    border-color: var(--om-accent);
    box-shadow: 0 0 0 1px color-mix(in oklab, var(--om-accent) 35%, transparent);
  }
  .preview-selection-grid__tile :global(.thumb-stack) {
    width: 100%;
    height: 100%;
  }
  .preview-selection-grid__tile :global(img) {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .preview-selection-grid__ph {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    font-size: 0.65rem;
    color: var(--om-text-muted);
    text-transform: uppercase;
  }
  .preview-selection-grid__badge {
    position: absolute;
    left: 3px;
    bottom: 3px;
    font-size: 0.55rem;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    background: rgb(0 0 0 / 0.55);
    color: #fff;
    pointer-events: none;
  }
  .preview-selection-grid__remove {
    position: absolute;
    top: 2px;
    right: 2px;
    z-index: 2;
    width: 18px;
    min-width: 18px;
    height: 18px;
    padding: 0;
    line-height: 1;
    font-size: 0.85rem;
    font-weight: 700;
    border-radius: 999px;
    background: rgb(8 10 16 / 0.72);
    color: #fff;
    border: 1px solid rgb(255 255 255 / 0.2);
  }
  .preview-selection-grid__remove:hover {
    background: rgb(180 40 40 / 0.92);
    border-color: rgb(255 200 200 / 0.35);
  }
</style>
