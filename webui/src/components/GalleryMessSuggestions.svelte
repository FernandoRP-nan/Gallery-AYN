<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from "svelte";
  import { bridge } from "../lib/api";
  import { computeMasonryColumnCount, packIntoColumns } from "../lib/galleryMasonryLayout";
  import { t } from "../lib/i18n";
  import { buildMediaFileUrl, normalizePathForApi } from "../lib/pathUtils";

  export let enabled = false;
  export let messFolder = "";
  export let targetFolder = "";
  export let masonry = true;
  /** Mismo tamaño de celda que la galería (escala de miniaturas). */
  export let gridCellPx = 120;
  export let thumbGapPx = 12;

  const dispatch = createEventDispatcher<{ moved: { count: number } }>();

  let paths: string[] = [];
  let loading = false;
  let movingPath: string | null = null;
  let error = "";
  let truncated = false;
  let total = 0;
  let dropActive = false;

  $: colPx = Math.max(72, Math.round(gridCellPx));
  $: maxThumbH = Math.round(colPx * 2.4);
  $: masonryStyle = `--mess-col-w:${colPx}px;--mess-gap:${thumbGapPx}px;--mess-radius:var(--thumb-image-radius,6px);--mess-max-h:${maxThumbH}px`;
  $: masonryColumnCount = computeMasonryColumnCount(masonryWidth, colPx, thumbGapPx, 0);
  $: pathColumns = masonry ? packIntoColumns(paths, masonryColumnCount) : [];

  let masonryWidth = 640;
  let masonryEl: HTMLDivElement | null = null;
  let masonryResizeObserver: ResizeObserver | null = null;

  function syncMasonryWidth() {
    if (masonryEl) masonryWidth = masonryEl.clientWidth;
  }

  onMount(() => {
    syncMasonryWidth();
    if (!masonryEl || typeof ResizeObserver === "undefined") return;
    masonryResizeObserver = new ResizeObserver(() => syncMasonryWidth());
    masonryResizeObserver.observe(masonryEl);
  });

  onDestroy(() => {
    masonryResizeObserver?.disconnect();
    masonryResizeObserver = null;
  });

  function pathBaseName(p: string): string {
    return p.replace(/\\/g, "/").split("/").pop() || p;
  }

  function thumbSrc(path: string): string {
    return buildMediaFileUrl(normalizePathForApi(path));
  }

  function targetLabel(): string {
    const n = targetFolder.replace(/\\/g, "/").split("/").pop();
    return n || targetFolder || "…";
  }

  async function loadPaths() {
    if (!enabled || !messFolder.trim()) {
      paths = [];
      return;
    }
    loading = true;
    error = "";
    try {
      const out = await bridge.messListImages(messFolder);
      if (!out?.ok) {
        error = out?.error ?? t("suggestions.loadError");
        paths = [];
        return;
      }
      paths = Array.isArray(out.paths) ? out.paths.filter(Boolean) : [];
      truncated = Boolean(out.truncated);
      total = Number(out.total ?? paths.length);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : t("suggestions.loadError");
      paths = [];
    } finally {
      loading = false;
    }
  }

  async function movePath(path: string) {
    const dest = targetFolder.trim();
    if (!dest || movingPath) return;
    movingPath = path;
    try {
      const out = await bridge.messMoveCluster([path], dest);
      const moved = Number(out?.moved ?? 0);
      if (moved > 0) {
        paths = paths.filter((p) => p !== path);
        total = Math.max(0, total - moved);
        dispatch("moved", { count: moved });
      }
    } finally {
      movingPath = null;
    }
  }

  function onDragStart(path: string, e: DragEvent) {
    const dt = e.dataTransfer;
    if (!dt) return;
    dt.setData("text/plain", path);
    dt.setData("application/x-om-mess-suggestion", "1");
    dt.effectAllowed = "move";
  }

  function onDropZone(e: DragEvent) {
    e.preventDefault();
    dropActive = false;
    const path = String(e.dataTransfer?.getData("text/plain") ?? "").trim();
    if (!path || e.dataTransfer?.getData("application/x-om-mess-suggestion") !== "1") return;
    void movePath(path);
  }

  let lastLoadKey = "";
  $: {
    const key = `${enabled}|${messFolder.trim()}`;
    if (key !== lastLoadKey) {
      lastLoadKey = key;
      if (enabled && messFolder.trim()) void loadPaths();
      else if (!enabled) paths = [];
    }
  }
</script>

{#if enabled && messFolder.trim()}
  <section class="mess-suggestions" style={masonryStyle} bind:this={masonryEl} aria-label={t("suggestions.title")}>
    <header class="mess-suggestions__head">
      <div class="mess-suggestions__titles">
        <h3 class="mess-suggestions__title">{t("suggestions.title")}</h3>
        <p class="mess-suggestions__sub" title={messFolder}>{messFolder}</p>
      </div>
      <div class="mess-suggestions__actions">
        <span class="mess-suggestions__count">
          {loading ? "…" : t("suggestions.count").replace("{n}", String(paths.length))}
        </span>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" disabled={loading} on:click={() => loadPaths()}
          >{t("suggestions.refresh")}</button
        >
      </div>
    </header>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="mess-suggestions__drop"
      class:mess-suggestions__drop--active={dropActive}
      on:dragover|preventDefault={() => (dropActive = true)}
      on:dragleave={() => (dropActive = false)}
      on:drop={onDropZone}
    >
      {t("suggestions.dropHint").replace("{folder}", targetLabel())}
    </div>

    {#if error}
      <p class="mess-suggestions__msg mess-suggestions__msg--err">{error}</p>
    {:else if loading && paths.length === 0}
      <p class="mess-suggestions__msg">{t("suggestions.loading")}</p>
    {:else if paths.length === 0}
      <p class="mess-suggestions__msg">{t("suggestions.empty")}</p>
    {:else if masonry}
      <div class="mess-suggestions__masonry">
        <div class="mess-suggestions__masonry-cols">
          {#each pathColumns as colPaths, colIdx (colIdx)}
            <div class="mess-suggestions__masonry-col">
              {#each colPaths as p (p)}
                <figure class="mess-suggestions__cell">
                  <img src={thumbSrc(p)} alt={pathBaseName(p)} loading="lazy" decoding="async" draggable={false} />
                  <button
                    type="button"
                    class="mess-suggestions__add"
                    disabled={movingPath === p || !targetFolder.trim()}
                    draggable={true}
                    on:dragstart={(e) => onDragStart(p, e)}
                    on:click={() => movePath(p)}
                    aria-label={t("suggestions.moveHereTitle").replace("{folder}", targetLabel())}
                    title={t("suggestions.moveHereTitle").replace("{folder}", targetLabel())}
                  >+</button>
                </figure>
              {/each}
            </div>
          {/each}
        </div>
      </div>
    {:else}
      <div class="mess-suggestions__strip">
        {#each paths as p (p)}
          <figure class="mess-suggestions__strip-item" style={`width:${colPx}px;height:${colPx}px`}>
            <img src={thumbSrc(p)} alt={pathBaseName(p)} loading="lazy" decoding="async" draggable={false} />
            <button
              type="button"
              class="mess-suggestions__add"
              disabled={movingPath === p || !targetFolder.trim()}
              on:click={() => movePath(p)}
              aria-label={t("suggestions.moveHereTitle").replace("{folder}", targetLabel())}
              title={t("suggestions.moveHereTitle").replace("{folder}", targetLabel())}
            >+</button>
          </figure>
        {/each}
      </div>
    {/if}

    {#if truncated}
      <p class="mess-suggestions__msg">{t("suggestions.truncated")}</p>
    {/if}
  </section>
{/if}

<style>
  .mess-suggestions {
    margin: var(--om-space-4) var(--om-space-2) var(--om-space-6);
    padding: var(--om-space-3);
    border-radius: var(--om-radius-md, 10px);
    border: 1px solid var(--om-border-subtle, rgb(255 255 255 / 0.1));
    background: var(--om-surface-2, rgb(0 0 0 / 0.18));
  }

  .mess-suggestions__head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--om-space-2);
    margin-bottom: var(--om-space-3);
  }

  .mess-suggestions__title {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 700;
  }

  .mess-suggestions__sub {
    margin: 0.15rem 0 0;
    font-size: 0.72rem;
    color: var(--om-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: min(520px, 70vw);
  }

  .mess-suggestions__actions {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }

  .mess-suggestions__count {
    font-size: 0.75rem;
    color: var(--om-text-muted);
  }

  .mess-suggestions__drop {
    margin-bottom: var(--om-space-3);
    padding: var(--om-space-2) var(--om-space-3);
    border-radius: var(--om-radius-sm, 8px);
    border: 1px dashed var(--om-border-subtle, rgb(255 255 255 / 0.18));
    font-size: 0.75rem;
    color: var(--om-text-muted);
    text-align: center;
    transition: border-color 0.15s, background 0.15s;
  }

  .mess-suggestions__drop--active {
    border-color: var(--om-accent, #60a5fa);
    background: rgb(96 165 250 / 0.08);
    color: var(--om-text, inherit);
  }

  .mess-suggestions__msg {
    margin: var(--om-space-2) 0 0;
    font-size: 0.8125rem;
    color: var(--om-text-muted);
  }

  .mess-suggestions__msg--err {
    color: var(--om-warn, #fbbf24);
  }

  .mess-suggestions__masonry {
    width: 100%;
  }

  .mess-suggestions__masonry-cols {
    display: flex;
    align-items: flex-start;
    gap: var(--mess-gap);
    width: 100%;
  }

  .mess-suggestions__masonry-col {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: var(--mess-gap);
  }

  .mess-suggestions__cell {
    position: relative;
    margin: 0;
    break-inside: avoid;
    border-radius: var(--mess-radius);
    overflow: hidden;
    background: var(--om-surface-3, rgb(0 0 0 / 0.25));
  }

  .mess-suggestions__cell img {
    width: 100%;
    height: auto;
    max-height: var(--mess-max-h);
    object-fit: cover;
    display: block;
    vertical-align: bottom;
  }

  .mess-suggestions__add {
    position: absolute;
    top: 5px;
    right: 5px;
    z-index: 2;
    width: 1.35rem;
    height: 1.35rem;
    padding: 0;
    border: 1px solid rgb(255 255 255 / 0.42);
    border-radius: 999px;
    background: rgb(8 10 18 / 0.38);
    color: rgb(255 255 255 / 0.92);
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s ease, background 0.15s ease, border-color 0.15s ease;
    backdrop-filter: blur(4px);
  }

  .mess-suggestions__add:hover:not(:disabled),
  .mess-suggestions__add:focus-visible:not(:disabled) {
    background: rgb(8 10 18 / 0.55);
    border-color: rgb(255 255 255 / 0.65);
  }

  .mess-suggestions__add:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .mess-suggestions__cell:hover .mess-suggestions__add,
  .mess-suggestions__cell:focus-within .mess-suggestions__add,
  .mess-suggestions__strip-item:hover .mess-suggestions__add,
  .mess-suggestions__strip-item:focus-within .mess-suggestions__add {
    opacity: 1;
  }

  .mess-suggestions__strip {
    display: flex;
    flex-direction: row;
    gap: var(--mess-gap);
    overflow-x: auto;
    padding-bottom: var(--om-space-1);
  }

  .mess-suggestions__strip-item {
    position: relative;
    flex: 0 0 auto;
    margin: 0;
    border-radius: var(--mess-radius);
    overflow: hidden;
    background: var(--om-surface-3, rgb(0 0 0 / 0.25));
  }

  .mess-suggestions__strip-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .mess-suggestions__strip-item .mess-suggestions__add {
    top: 4px;
    right: 4px;
  }
</style>
