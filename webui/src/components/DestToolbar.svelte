<script lang="ts">
  import { t } from "../lib/i18n";
  import type { DestToolbarItem } from "../lib/itemTree";

  export let toolbarItems: DestToolbarItem[] = [];
  export let folderLabel: string | null = null;
  export let canGoBack = false;
  export let dragOverDestPath: string | null = null;
  export let draggedDestIdx: number | null = null;

  export let onBack: () => void;
  export let onOpenFolder: (folderId: string) => void;
  export let onAddDest: () => void;
  export let onDestClick: (e: MouseEvent, path: string) => void;
  export let onDestContextMenu: (e: MouseEvent, idx: number) => void;
  export let onDestChipDragStart: (e: DragEvent, idx: number) => void;
  export let onDestChipDragEnd: () => void;
  export let onDestDrop: (e: DragEvent, path: string, idx: number) => void;
</script>

<div class="gallery-dest-rail">
  <div class="selection-float selection-float--dest-bar app-chrome" role="toolbar" aria-label={t("selection.destBarAria")}>
    {#if canGoBack}
      <button type="button" class="om-btn om-btn--ghost om-btn--mini dest-chip-btn dest-chip-btn--back" title={t("treeManager.back")} on:click={onBack}>←</button>
    {/if}
    <button type="button" class="om-btn om-btn--ghost om-btn--mini" title={t("treeManager.addDest")} on:click={onAddDest}>+</button>
    {#if folderLabel}
      <span class="selection-float__hint dest-toolbar-folder-label">{folderLabel}</span>
    {/if}
    {#if toolbarItems.length === 0}
      <span class="selection-float__hint">{t("selection.noDestFolders")}</span>
    {/if}
    {#each toolbarItems as item (item.kind === "folder" ? item.id : item.path)}
      {#if item.kind === "folder"}
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--mini dest-chip-btn dest-chip-btn--folder"
          title={item.label}
          on:click={() => onOpenFolder(item.id)}
        >
          <span class="dest-chip-btn__title">📁 {item.label}</span>
        </button>
      {:else}
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--mini dest-chip-btn"
          class:dest-chip-btn--drop-target={dragOverDestPath === item.path}
          class:dest-chip-btn--dragging={draggedDestIdx === item.index}
          data-dest-path={item.path}
          title={item.path}
          draggable={true}
          on:click={(e) => onDestClick(e, item.path)}
          on:contextmenu={(e) => onDestContextMenu(e, item.index)}
          on:dragstart={(e) => onDestChipDragStart(e, item.index)}
          on:dragend={onDestChipDragEnd}
          on:dragenter|preventDefault
          on:dragover|preventDefault
          on:drop={(e) => onDestDrop(e, item.path, item.index)}
        >
          <span class="dest-chip-btn__title">{item.label}</span>
        </button>
      {/if}
    {/each}
    <span class="dest-toolbar-trail" aria-hidden="true"></span>
  </div>
</div>

<style>
  .gallery-dest-rail {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9;
    box-sizing: border-box;
    padding-inline: var(--om-space-3);
    padding-top: var(--om-space-3);
    padding-bottom: max(var(--om-space-3), env(safe-area-inset-bottom, 0px));
    pointer-events: none;
  }

  .gallery-dest-rail :global(.selection-float--dest-bar) {
    pointer-events: auto;
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: var(--om-space-1);
    overflow-x: auto;
    overflow-y: hidden;
    box-sizing: border-box;
    width: 100%;
    max-width: 100%;
    padding: var(--om-space-1) var(--om-space-2);
    scroll-padding-inline: var(--om-space-3);
    scrollbar-width: thin;
    scrollbar-color: rgb(124 140 255 / 0.38) transparent;
    background: rgb(8 10 18 / 0.92);
    border: 1px solid rgb(255 255 255 / 0.12);
    border-radius: var(--om-radius-md);
    box-shadow: 0 10px 28px rgb(0 0 0 / 0.42);
    white-space: nowrap;
  }

  :global(.dest-toolbar-trail) {
    flex: 0 0 var(--om-space-3);
    width: var(--om-space-3);
    min-height: 1px;
    pointer-events: none;
  }

  .gallery-dest-rail :global(.selection-float--dest-bar::-webkit-scrollbar) {
    height: 6px;
  }

  .gallery-dest-rail :global(.selection-float--dest-bar::-webkit-scrollbar-thumb) {
    background: linear-gradient(90deg, rgb(124 140 255 / 0.42), rgb(94 228 212 / 0.28));
    border-radius: 999px;
  }

  .selection-float__hint {
    font-size: 0.72rem;
    color: var(--om-text-muted);
    white-space: nowrap;
  }

  :global(.dest-chip-btn) {
    flex-shrink: 0;
    max-width: min(12rem, 42vw);
  }

  :global(.dest-chip-btn__title) {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
  }

  :global(.dest-chip-btn.dest-chip-btn--drop-target) {
    border-color: rgb(124 140 255 / 0.82);
    background: rgb(124 140 255 / 0.14);
    color: var(--om-text-primary);
    box-shadow: 0 0 0 1px rgb(124 140 255 / 0.35);
  }

  :global(.dest-chip-btn.dest-chip-btn--dragging) {
    opacity: 0.45;
  }

  :global(.dest-chip-btn--folder) {
    border-color: color-mix(in oklab, var(--om-accent) 45%, var(--om-border-default));
  }

  :global(.dest-chip-btn--back) {
    color: var(--om-accent-2);
  }

  .dest-toolbar-folder-label {
    flex-shrink: 0;
    font-size: 0.68rem;
    opacity: 0.85;
    max-width: 8rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
