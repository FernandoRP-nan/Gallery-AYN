<script lang="ts">
  import { onDestroy } from "svelte";
  import { bridge } from "../lib/api";
  import { t } from "../lib/i18n";
  import { buildMediaFileUrl, normalizePathForApi } from "../lib/pathUtils";

  export let open = false;
  export let galleryFolder = "";
  export let initialMessFolder = "";
  export let initialSimilarity = 0.82;

  export let onClose: () => void = () => {};
  export let onMoved: () => void | Promise<void> = () => {};

  type MessCluster = {
    id: string;
    count: number;
    paths: string[];
    moreCount?: number;
  };

  let messFolder = "";
  let messDest = "";
  let messSimilarity = 0.82;
  let hideSingletons = true;
  let scanning = false;
  let scanDetail = "";
  let scanProgress = "";
  let clusters: MessCluster[] = [];
  let scanMeta = { truncated: false, totalFiles: 0, multiClusterCount: 0 };
  let movingClusterId: string | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let panelWasOpen = false;

  const PREVIEW_MAX = 12;

  $: visibleClusters = hideSingletons ? clusters.filter((c) => clusterCount(c) > 1) : clusters;

  $: if (open && !panelWasOpen) {
    panelWasOpen = true;
    void refreshMessSettings();
    if (galleryFolder) messDest = galleryFolder;
  }
  $: if (!open) panelWasOpen = false;

  function pathBaseName(p: string): string {
    const n = p.replace(/\\/g, "/").split("/").pop();
    return n || p;
  }

  function clusterCount(c: MessCluster): number {
    return c.count || c.paths?.length || 0;
  }

  function clusterPaths(c: MessCluster): string[] {
    return (c.paths ?? []).filter(Boolean);
  }

  function previewPaths(c: MessCluster): string[] {
    return clusterPaths(c).slice(0, PREVIEW_MAX);
  }

  function thumbSrc(path: string): string {
    return buildMediaFileUrl(normalizePathForApi(path));
  }

  function normalizeCluster(raw: Record<string, unknown>): MessCluster {
    const paths = Array.isArray(raw.paths)
      ? (raw.paths as string[]).map((p) => normalizePathForApi(String(p))).filter(Boolean)
      : [];
    const count = Number(raw.count ?? paths.length);
    return {
      id: String(raw.id ?? `c-${paths[0] ?? "empty"}`),
      count,
      paths,
      moreCount: Math.max(0, paths.length - Math.min(paths.length, PREVIEW_MAX)),
    };
  }

  async function refreshMessSettings() {
    try {
      const st = await bridge.getInitialState();
      messFolder = String(st.settings?.mess_folder_path ?? initialMessFolder ?? "").trim();
      messSimilarity = Number(st.settings?.mess_similarity_min ?? initialSimilarity);
    } catch {
      messFolder = initialMessFolder;
      messSimilarity = initialSimilarity;
    }
  }

  function stopPoll() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function updateScanDetail() {
    scanDetail = t("mess.scanDone")
      .replace("{groups}", String(clusters.length))
      .replace("{multi}", String(scanMeta.multiClusterCount))
      .replace("{visible}", String(visibleClusters.length));
  }

  async function persistSettings() {
    try {
      await bridge.messSaveSettings(messFolder, messSimilarity);
    } catch {
      /* ignore */
    }
  }

  async function pickMessFolder() {
    try {
      const out = await bridge.dialogPickFolder(messFolder);
      if (out?.cancelled || !out?.path) return;
      messFolder = out.path;
      await persistSettings();
    } catch {
      /* ignore */
    }
  }

  async function pickDestFolder() {
    try {
      const out = await bridge.dialogPickFolder(messDest);
      if (out?.cancelled || !out?.path) return;
      messDest = out.path;
    } catch {
      /* ignore */
    }
  }

  async function pollScan() {
    try {
      const out = await bridge.messScanStatus();
      scanning = Boolean(out?.running);
      const prog = out?.progress ?? { current: 0, total: 0, detail: "" };
      if (scanning) scanDetail = String(prog.detail ?? "");
      scanProgress =
        prog.total > 0 ? `${prog.current}/${prog.total}` : scanning ? "…" : "";
      if (!scanning) {
        stopPoll();
        if (out?.error === "cancelled") {
          scanDetail = t("mess.scanCancelled");
        } else if (out?.error) {
          scanDetail = out.error;
        } else if (out?.result) {
          clusters = (Array.isArray(out.result.clusters) ? out.result.clusters : []).map(
            (c: Record<string, unknown>) => normalizeCluster(c)
          );
          scanMeta = {
            truncated: Boolean(out.result.truncated),
            totalFiles: Number(out.result.totalFiles ?? 0),
            multiClusterCount: Number(out.result.multiClusterCount ?? 0),
          };
          updateScanDetail();
        }
      }
    } catch {
      scanning = false;
      stopPoll();
    }
  }

  async function startScan() {
    if (scanning || !messFolder.trim()) return;
    await persistSettings();
    clusters = [];
    scanDetail = t("mess.scanStarting");
    try {
      const out = await bridge.messScanStart(messFolder, messSimilarity);
      if (!out?.ok) {
        scanDetail = out?.error ?? t("mess.scanError");
        return;
      }
      scanning = true;
      stopPoll();
      pollTimer = setInterval(() => void pollScan(), 400);
      void pollScan();
    } catch (e: unknown) {
      scanDetail = e instanceof Error ? e.message : t("mess.scanError");
    }
  }

  async function cancelScan() {
    await bridge.messScanCancel();
    void pollScan();
  }

  async function moveCluster(cluster: MessCluster) {
    if (!messDest.trim() || movingClusterId) return;
    movingClusterId = cluster.id;
    try {
      const out = await bridge.messMoveCluster(clusterPaths(cluster), messDest);
      if ((out?.moved ?? 0) > 0) {
        clusters = clusters.filter((c) => c.id !== cluster.id);
        updateScanDetail();
        await onMoved();
      }
    } finally {
      movingClusterId = null;
    }
  }

  onDestroy(() => stopPoll());
</script>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="org-float-overlay" role="presentation" on:click|self={onClose}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div
      class="organizer-float mess-panel om-panel om-panel--lift"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mess-panel-title"
      tabindex="-1"
      on:click|stopPropagation={() => undefined}
    >
      <header class="org-float__head">
        <strong id="mess-panel-title">{t("mess.title")}</strong>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--close"
          aria-label={t("common.closeModalAria")}
          title={t("common.close")}
          on:click={onClose}>✕</button
        >
      </header>

      <p class="mess-panel__hint">{t("mess.hintClassic")}</p>

      <div class="org-row">
        <label class="field-label" for="mess-folder-input">{t("mess.folderLabel")}</label>
        <input
          id="mess-folder-input"
          class="om-input org-row__input"
          bind:value={messFolder}
          placeholder={t("mess.folderPlaceholder")}
        />
        <button type="button" class="om-btn om-btn--primary" on:click={pickMessFolder}>{t("destinations.browse")}</button>
      </div>

      <div class="org-row mess-panel__sim">
        <label class="field-label" for="mess-sim-range">{t("mess.similarityLabel")}</label>
        <input id="mess-sim-range" type="range" min="0.75" max="0.95" step="0.01" bind:value={messSimilarity} />
        <span class="mess-panel__sim-val">{Math.round(messSimilarity * 100)}%</span>
      </div>

      <div class="org-row">
        <label class="field-label" for="mess-dest-input">{t("mess.destLabel")}</label>
        <input id="mess-dest-input" class="om-input org-row__input" bind:value={messDest} placeholder={t("mess.destPlaceholder")} />
        <button type="button" class="om-btn om-btn--ghost" on:click={pickDestFolder}>{t("destinations.browse")}</button>
      </div>

      <label class="mess-panel__check check">
        <input type="checkbox" bind:checked={hideSingletons} on:change={updateScanDetail} />
        {t("mess.hideSingletons")}
      </label>

      <div class="org-row org-row--footer">
        <button type="button" class="om-btn om-btn--primary" disabled={scanning || !messFolder.trim()} on:click={startScan}
          >{t("mess.scan")}</button
        >
        <button type="button" class="om-btn om-btn--ghost" disabled={!scanning} on:click={cancelScan}>{t("mess.cancelScan")}</button>
        <span class="org-status">{scanDetail}</span>
        <span class="org-progress">{scanProgress}</span>
      </div>

      {#if scanMeta.truncated}
        <p class="mess-panel__warn">{t("mess.truncated")}</p>
      {/if}

      <div class="mess-clusters">
        {#if visibleClusters.length === 0 && !scanning}
          <p class="mess-panel__empty">
            {clusters.length > 0 && hideSingletons ? t("mess.emptyFiltered") : t("mess.empty")}
          </p>
        {:else}
          {#each visibleClusters as cluster (cluster.id)}
            <section class="mess-cluster">
              <header class="mess-cluster__head">
                <span>{t("mess.groupTitle").replace("{n}", String(clusterCount(cluster)))}</span>
                <button
                  type="button"
                  class="om-btn om-btn--primary om-btn--mini"
                  disabled={movingClusterId === cluster.id || !messDest.trim()}
                  on:click={() => moveCluster(cluster)}
                  >{t("mess.moveHere")}</button
                >
              </header>
              <div class="mess-cluster__strip">
                {#each previewPaths(cluster) as p (p)}
                  <div class="mess-cluster__thumb" title={pathBaseName(p)}>
                    <img
                      class="mess-cluster__img"
                      src={thumbSrc(p)}
                      alt={pathBaseName(p)}
                      loading="lazy"
                      decoding="async"
                      draggable={false}
                    />
                  </div>
                {/each}
                {#if (cluster.moreCount ?? 0) > 0}
                  <div class="mess-cluster__more">+{cluster.moreCount}</div>
                {/if}
              </div>
            </section>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  :global(.organizer-float.mess-panel) {
    width: min(920px, 96vw);
    max-height: min(88vh, 900px);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .mess-panel__hint,
  .mess-panel__warn,
  .mess-panel__empty {
    margin: 0 var(--om-space-4);
    font-size: 0.8125rem;
    color: var(--om-text-muted);
    flex-shrink: 0;
  }

  .mess-panel__check {
    margin: 0 var(--om-space-4) var(--om-space-3);
    font-size: 0.8125rem;
    flex-shrink: 0;
  }

  .mess-panel__warn {
    color: var(--om-warn, #fbbf24);
  }

  .mess-panel__sim {
    align-items: center;
    gap: var(--om-space-2);
  }

  .mess-panel__sim-val {
    min-width: 2.5rem;
    font-size: 0.8125rem;
    color: var(--om-text-muted);
  }

  .mess-clusters {
    flex: 1 1 auto;
    min-height: 200px;
    overflow-x: hidden;
    overflow-y: auto;
    padding: var(--om-space-3) var(--om-space-4) var(--om-space-4);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
  }

  .mess-cluster {
    flex-shrink: 0;
    border: 1px solid var(--om-border-subtle, rgba(255, 255, 255, 0.12));
    border-radius: var(--om-radius-md, 10px);
    background: var(--om-surface-2, rgba(0, 0, 0, 0.15));
  }

  .mess-cluster__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--om-space-2);
    padding: var(--om-space-2) var(--om-space-3);
    font-size: 0.8125rem;
    font-weight: 600;
  }

  .mess-cluster__strip {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: stretch;
    gap: var(--om-space-2);
    min-height: 96px;
    padding: 0 var(--om-space-3) var(--om-space-3);
    overflow-x: auto;
    overflow-y: hidden;
  }

  .mess-cluster__thumb {
    flex: 0 0 88px;
    width: 88px;
    height: 88px;
    border-radius: 8px;
    overflow: hidden;
    background: var(--om-surface-3, rgba(0, 0, 0, 0.25));
  }

  .mess-cluster__img {
    width: 88px;
    height: 88px;
    object-fit: cover;
    display: block;
  }

  .mess-cluster__more {
    flex: 0 0 88px;
    display: grid;
    place-items: center;
    width: 88px;
    height: 88px;
    font-size: 0.875rem;
    color: var(--om-text-muted);
    background: var(--om-surface-3, rgba(0, 0, 0, 0.2));
    border-radius: 8px;
  }
</style>
