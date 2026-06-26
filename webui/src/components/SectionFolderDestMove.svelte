<script lang="ts">
  import { onDestroy } from "svelte";
  import type { TreeNode } from "../lib/itemTree";
  import { t } from "../lib/i18n";
  import { resetMoveFlyoutState } from "../lib/destMoveFlyoutState";
  import {
    allocSectionDestMoveId,
    sectionDestMoveCtx,
  } from "../lib/sectionDestMoveState";
  import DestMoveCtxTree from "./DestMoveCtxTree.svelte";

  export let destTree: TreeNode[] = [];
  export let disabled = false;
  export let onPickDest: (destPath: string) => void = () => {};

  const instanceId = allocSectionDestMoveId();
  let open = false;
  let rootEl: HTMLDivElement | null = null;

  function closeMenu() {
    open = false;
    sectionDestMoveCtx.update((ctx) => (ctx?.id === instanceId ? null : ctx));
    resetMoveFlyoutState();
  }

  function pick(destPath: string) {
    closeMenu();
    onPickDest(destPath);
  }

  function toggleMenu(e: MouseEvent) {
    e.stopPropagation();
    e.preventDefault();
    if (disabled) return;
    if (open) {
      closeMenu();
      return;
    }
    sectionDestMoveCtx.set({ id: instanceId, onPick: pick });
    open = true;
  }

  function onDocPointerDown(e: PointerEvent) {
    if (!open) return;
    const target = e.target as Node | null;
    if (!target) return;
    if (rootEl?.contains(target)) return;
    if ((target as Element).closest?.(".dest-move-flyout-fixed")) return;
    closeMenu();
  }

  $: if ($sectionDestMoveCtx && $sectionDestMoveCtx.id !== instanceId && open) {
    closeMenu();
  }

  $: if (open) {
    document.addEventListener("pointerdown", onDocPointerDown, true);
  } else {
    document.removeEventListener("pointerdown", onDocPointerDown, true);
  }

  onDestroy(() => {
    document.removeEventListener("pointerdown", onDocPointerDown, true);
    if (open) closeMenu();
  });
</script>

<div class="section-dest-move" bind:this={rootEl}>
  <button
    type="button"
    class="section-dest-move__btn om-btn om-btn--ghost om-btn--mini"
    aria-haspopup="menu"
    aria-expanded={open}
    {disabled}
    title={disabled ? t("contextGallery.noDestinations") : t("gallery.sectionMoveTo")}
    on:click={toggleMenu}
  >
    {t("gallery.sectionMoveTo")}
    <span class="section-dest-move__caret" aria-hidden="true">▾</span>
  </button>
  {#if open}
    <div
      class="section-dest-move__menu om-panel om-panel--lift"
      aria-label={t("gallery.sectionMoveToAria")}
      on:click|stopPropagation
    >
      <div class="section-dest-move__scroll">
        <DestMoveCtxTree nodes={destTree} onPick={pick} />
      </div>
    </div>
  {/if}
</div>

<style>
  .section-dest-move {
    position: relative;
    flex-shrink: 0;
    margin-left: auto;
  }
  .section-dest-move__btn {
    white-space: nowrap;
    font-size: 0.68rem;
    padding: 2px 8px;
    gap: 4px;
  }
  .section-dest-move__caret {
    font-size: 0.62rem;
    opacity: 0.75;
  }
  .section-dest-move__menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 30;
    min-width: 11rem;
    max-width: 15rem;
    padding: var(--om-space-2);
    box-sizing: border-box;
  }
  .section-dest-move__scroll {
    max-height: 14rem;
    overflow-x: hidden;
    overflow-y: auto;
  }
</style>
