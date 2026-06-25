<script lang="ts">
  import type { TreeFolder, TreeNode } from "../lib/itemTree";
  import { isDestNode, isFolderNode } from "../lib/itemTree";
  import {
    setFolderFlyoutDepth,
    onMoveMenuPointerLeave,
  } from "../lib/destMoveFlyoutState";

  export let nodes: TreeNode[];
  export let onPick: (path: string) => void;
  export let excludePath = "";
  export let flyoutDepth = 0;

  function folderHasVisibleTargets(node: TreeFolder): boolean {
    for (const child of node.children) {
      if (isDestNode(child) && child.path !== excludePath) return true;
      if (isFolderNode(child) && folderHasVisibleTargets(child)) return true;
    }
    return false;
  }

  function onFolderEnter(node: TreeFolder, e: PointerEvent) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    setFolderFlyoutDepth(flyoutDepth, node, el);
  }
</script>

{#each nodes as node (isFolderNode(node) ? `f:${node.id}` : `d:${node.path}`)}
  {#if isDestNode(node)}
    {#if node.path !== excludePath}
      <button
        type="button"
        class="dest-ctx-menu__item dest-move-tree__dest"
        role="menuitem"
        title={node.path}
        on:click|stopPropagation={() => onPick(node.path)}
      >
        {node.label}
      </button>
    {/if}
  {:else if isFolderNode(node) && folderHasVisibleTargets(node)}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      class="dest-move-tree__folder-row"
      role="presentation"
      on:pointerenter={(e) => onFolderEnter(node, e)}
      on:pointerleave={(e) => onMoveMenuPointerLeave(e, flyoutDepth)}
    >
      <button
        type="button"
        class="dest-ctx-menu__item ctx-menu__submenu-trigger dest-move-tree__folder-trigger"
        role="menuitem"
        aria-haspopup="true"
        tabindex="-1"
      >
        <span class="dest-move-tree__folder-label">{node.label}</span>
        <span class="ctx-menu__submenu-trigger-mark" aria-hidden="true">▸</span>
      </button>
    </div>
  {/if}
{/each}

<style>
  .dest-move-tree__folder-row {
    display: block;
    width: 100%;
  }

  .dest-move-tree__folder-trigger {
    width: 100%;
    text-align: left;
    pointer-events: none;
  }

  .dest-move-tree__folder-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    flex: 1;
    text-align: left;
  }
</style>
