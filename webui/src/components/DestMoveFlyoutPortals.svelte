<script lang="ts">
  import {
    cancelMoveMenuClose,
    folderFlyoutStack,
    flyoutStyleFor,
    onMoveMenuPointerLeave,
  } from "../lib/destMoveFlyoutState";
  import DestMoveCtxTree from "./DestMoveCtxTree.svelte";

  export let onPick: (path: string) => void;
  export let excludePath = "";

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return { destroy() { node.remove(); } };
  }
</script>

{#each $folderFlyoutStack as entry, i (entry.id + ":" + i)}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    use:portal
    class="dest-move-flyout-fixed om-panel om-panel--lift"
    role="menu"
    tabindex="-1"
    aria-label={entry.node.label}
    style={flyoutStyleFor(entry, i)}
    on:pointerenter={cancelMoveMenuClose}
    on:pointerleave={(e) => onMoveMenuPointerLeave(e, i)}
  >
    <DestMoveCtxTree
      nodes={entry.node.children}
      {onPick}
      {excludePath}
      flyoutDepth={i + 1}
    />
  </div>
{/each}

<style>
  :global(.dest-move-flyout-fixed) {
    position: fixed;
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-width: 15rem;
    overflow-x: hidden;
    overflow-y: auto;
    padding: var(--om-space-2);
    box-sizing: border-box;
    pointer-events: auto;
  }
</style>
