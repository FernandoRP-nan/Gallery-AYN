<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { t } from "../lib/i18n";
  import { buildMediaFileUrl, normalizePathForApi } from "../lib/pathUtils";

  export type SimilarItem = { path: string; similarity: number };

  export let anchorPath = "";
  export let items: SimilarItem[] = [];
  export let loading = false;

  const dispatch = createEventDispatcher<{ close: void; select: { path: string } }>();

  function pathBaseName(p: string): string {
    const n = p.replace(/\\/g, "/").split("/").pop();
    return n || p;
  }

  function thumbSrc(path: string): string {
    return buildMediaFileUrl(normalizePathForApi(path));
  }

  function pct(sim: number): string {
    return `${Math.round(Number(sim) * 100)}%`;
  }
</script>

{#if anchorPath}
  <aside class="mess-more-like om-panel om-panel--lift" aria-label={t("mess.moreLikeTitle")}>
    <header class="mess-more-like__head">
      <strong>{t("mess.moreLikeTitle")}</strong>
      <button type="button" class="om-btn om-btn--ghost om-btn--close" on:click={() => dispatch("close")}>✕</button>
    </header>
    <p class="mess-more-like__anchor" title={anchorPath}>{pathBaseName(anchorPath)}</p>
    {#if loading}
      <p class="mess-more-like__status">{t("mess.moreLikeLoading")}</p>
    {:else if items.length === 0}
      <p class="mess-more-like__status">{t("mess.moreLikeEmpty")}</p>
    {:else}
      <div class="mess-more-like__grid">
        {#each items as item (item.path)}
          <button type="button" class="mess-more-like__item" title={item.path} on:click={() => dispatch("select", { path: item.path })}>
            <img src={thumbSrc(item.path)} alt={pathBaseName(item.path)} loading="lazy" decoding="async" />
            <span class="mess-more-like__pct">{pct(item.similarity)}</span>
          </button>
        {/each}
      </div>
    {/if}
  </aside>
{/if}

<style>
  .mess-more-like {
    position: absolute;
    top: var(--om-space-3);
    right: var(--om-space-3);
    width: min(280px, 42vw);
    max-height: calc(100% - var(--om-space-6));
    overflow: auto;
    z-index: 4;
    padding-bottom: var(--om-space-3);
  }

  .mess-more-like__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--om-space-2);
    padding: var(--om-space-2) var(--om-space-3);
    font-size: 0.8125rem;
  }

  .mess-more-like__anchor {
    margin: 0 var(--om-space-3) var(--om-space-2);
    font-size: 0.75rem;
    color: var(--om-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mess-more-like__status {
    margin: 0 var(--om-space-3);
    font-size: 0.8125rem;
    color: var(--om-text-muted);
  }

  .mess-more-like__grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--om-space-2);
    padding: 0 var(--om-space-3);
  }

  .mess-more-like__item {
    position: relative;
    padding: 0;
    border: none;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    background: var(--om-surface-3, rgba(0, 0, 0, 0.2));
  }

  .mess-more-like__item img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    display: block;
  }

  .mess-more-like__pct {
    position: absolute;
    right: 4px;
    bottom: 4px;
    font-size: 0.625rem;
    padding: 2px 5px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.65);
    color: #fff;
  }
</style>
