<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { t } from "../lib/i18n";
  import { buildMediaFileUrl, normalizePathForApi } from "../lib/pathUtils";

  export type MessCluster = {
    id: string;
    count: number;
    paths: string[];
    moreCount?: number;
  };

  export let cluster: MessCluster;
  export let masonry = false;
  export let dragGroups = false;
  export let moreLike = false;
  export let moving = false;
  export let canMove = false;
  export let dropHighlight = false;

  const dispatch = createEventDispatcher<{
    move: void;
    thumbClick: { path: string };
    dragStart: { path: string; clusterId: string };
    dragEnd: void;
    dragOver: void;
    drop: void;
  }>();

  const PREVIEW_MAX = 12;

  function pathBaseName(p: string): string {
    const n = p.replace(/\\/g, "/").split("/").pop();
    return n || p;
  }

  function clusterPaths(c: MessCluster): string[] {
    return (c.paths ?? []).filter(Boolean);
  }

  function clusterCount(c: MessCluster): number {
    return c.count || clusterPaths(c).length;
  }

  function thumbSrc(path: string): string {
    return buildMediaFileUrl(normalizePathForApi(path));
  }

  $: paths = clusterPaths(cluster);
  $: preview = masonry ? paths : paths.slice(0, PREVIEW_MAX);
  $: moreCount = masonry ? 0 : Math.max(0, paths.length - preview.length);

  let dragDidMove = false;

  function onThumbClick(path: string) {
    if (dragDidMove || !moreLike) return;
    dispatch("thumbClick", { path });
  }

  function onDragStart(path: string, e: DragEvent) {
    if (!dragGroups) return;
    dragDidMove = false;
    e.dataTransfer?.setData("text/plain", path);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
    dispatch("dragStart", { path, clusterId: cluster.id });
  }

  function onDragEnd() {
    dragDidMove = true;
    dispatch("dragEnd");
  }
</script>

<section
  class="mess-cluster"
  class:mess-cluster--drop={dropHighlight}
  on:dragover|preventDefault={() => dragGroups && dispatch("dragOver")}
  on:drop|preventDefault={() => dragGroups && dispatch("drop")}
>
  <header class="mess-cluster__head">
    <span>{t("mess.groupTitle").replace("{n}", String(clusterCount(cluster)))}</span>
    <button
      type="button"
      class="om-btn om-btn--primary om-btn--mini"
      disabled={moving || !canMove}
      on:click={() => dispatch("move")}
      >{t("mess.moveHere")}</button
    >
  </header>

  {#if masonry}
    <div class="mess-cluster__masonry">
      {#each preview as p (p)}
        <button
          type="button"
          class="mess-cluster__masonry-item"
          class:mess-cluster__masonry-item--clickable={moreLike}
          title={pathBaseName(p)}
          draggable={dragGroups}
          on:dragstart={(e) => onDragStart(p, e)}
          on:dragend={onDragEnd}
          on:click={() => onThumbClick(p)}
        >
          <img src={thumbSrc(p)} alt={pathBaseName(p)} loading="lazy" decoding="async" draggable={false} />
        </button>
      {/each}
    </div>
  {:else}
    <div class="mess-cluster__strip">
      {#each preview as p (p)}
        <div
          class="mess-cluster__thumb"
          class:mess-cluster__thumb--clickable={moreLike}
          title={pathBaseName(p)}
          role={moreLike ? "button" : undefined}
          tabindex={moreLike ? 0 : undefined}
          draggable={dragGroups}
          on:keydown={(e) => moreLike && (e.key === "Enter" || e.key === " ") && onThumbClick(p)}
          on:dragstart={(e) => onDragStart(p, e)}
          on:dragend={onDragEnd}
          on:click={() => onThumbClick(p)}
        >
          <img src={thumbSrc(p)} alt={pathBaseName(p)} loading="lazy" decoding="async" draggable={false} />
        </div>
      {/each}
      {#if moreCount > 0}
        <div class="mess-cluster__more">+{moreCount}</div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .mess-cluster--drop {
    outline: 2px dashed var(--om-accent, #60a5fa);
    outline-offset: 2px;
  }

  .mess-cluster__masonry {
    column-count: 4;
    column-gap: var(--om-space-2);
    padding: 0 var(--om-space-3) var(--om-space-3);
  }

  @media (max-width: 720px) {
    .mess-cluster__masonry {
      column-count: 3;
    }
  }

  .mess-cluster__masonry-item {
    display: block;
    width: 100%;
    margin: 0 0 var(--om-space-2);
    break-inside: avoid;
    padding: 0;
    border: none;
    background: transparent;
    border-radius: 8px;
    overflow: hidden;
    cursor: default;
  }

  .mess-cluster__masonry-item--clickable {
    cursor: pointer;
  }

  .mess-cluster__masonry-item img {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 8px;
    background: var(--om-surface-3, rgba(0, 0, 0, 0.25));
  }

  .mess-cluster__thumb--clickable {
    cursor: pointer;
  }

  .mess-cluster__thumb--clickable:focus-visible {
    outline: 2px solid var(--om-accent, #60a5fa);
    outline-offset: 2px;
  }
</style>
