<script lang="ts">
  import { t } from "../../lib/i18n";
  import { buildMediaFileUrl } from "../../lib/pathUtils";

  export let uiBgImagePath: string;
  export let uiBgBlur = 0;
  export let galleryFolder: string;
  export let recentFolders: string[] = [];
  export let pinnedFolders: string[] = [];
  export let pinnedFolderLabels: Record<string, string> = {};
  export let onBrowseFolder: (path: string) => void;

  $: previewUrl = uiBgImagePath ? buildMediaFileUrl(uiBgImagePath) : "";
  $: routesOpen = !uiBgImagePath;

  function folderChipLabel(path: string): string {
    const custom = String(pinnedFolderLabels[path] ?? "").trim();
    if (custom) return custom;
    return path.split(/[/\\]/).filter(Boolean).pop() ?? path;
  }

  $: pinnedList = pinnedFolders.map((p) => String(p ?? "").trim()).filter(Boolean);
  $: recentList = recentFolders
    .map((p) => String(p ?? "").trim())
    .filter(Boolean)
    .filter((p) => p !== galleryFolder && !pinnedList.includes(p));
  $: currentFolder = String(galleryFolder ?? "").trim();
  $: hasRouteOptions = Boolean(currentFolder) || pinnedList.length > 0 || recentList.length > 0;
</script>

<div class="settings-bg-picker">
  {#if uiBgImagePath}
    <div class="settings-bg-picker__preview-block">
      <span class="field-label">{t("settings.bgPreviewTitle")}</span>
      <p class="settings-hint">{t("settings.bgPreviewHint")}</p>
      <div
        class="settings-bg-picker__preview-mock"
        style={`--preview-blur:${Math.max(0, Math.min(24, Math.round(uiBgBlur)))}px;--preview-image:url("${previewUrl.replace(/"/g, '\\"')}")`}
        aria-hidden="true"
      >
        <div class="settings-bg-picker__preview-image"></div>
        <div class="settings-bg-picker__preview-scrim"></div>
        <span class="settings-bg-picker__preview-label">{t("settings.bgPreviewSample")}</span>
      </div>
      <label class="field-label" for="set-bg-blur">{t("settings.bgBlur")}</label>
      <div class="settings-range-row">
        <input id="set-bg-blur" type="range" min="0" max="24" step="1" bind:value={uiBgBlur} />
        <span class="settings-range-value">{uiBgBlur}px</span>
      </div>
      <p class="settings-hint">{t("settings.bgBlurHint")}</p>
      <div class="settings-preset-row settings-bg-picker__path-row">
        <p class="settings-hint settings-bg-path" title={uiBgImagePath}>{uiBgImagePath}</p>
        <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => (uiBgImagePath = "")}>
          {t("settings.bgClear")}
        </button>
      </div>
    </div>
  {/if}

  <details class="settings-bg-picker__routes-fold" open={routesOpen}>
    <summary class="settings-bg-picker__routes-summary">{t("settings.bgRoutesFoldTitle")}</summary>
    <div class="settings-bg-picker__routes-body">
      <p class="settings-hint">{t("settings.bgRoutesHint")}</p>

      {#if currentFolder}
        <div class="settings-bg-picker__section">
          <span class="field-label">{t("settings.bgCurrentFolder")}</span>
          <div class="settings-preset-row settings-bg-picker__routes">
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact settings-bg-route"
              title={currentFolder}
              on:click={() => onBrowseFolder(currentFolder)}
            >
              {folderChipLabel(currentFolder)}
            </button>
          </div>
        </div>
      {/if}

      {#if pinnedList.length > 0}
        <div class="settings-bg-picker__section">
          <span class="field-label">{t("settings.bgPinnedFolders")}</span>
          <div class="settings-preset-row settings-bg-picker__routes">
            {#each pinnedList as path (path)}
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact settings-bg-route"
                title={path}
                on:click={() => onBrowseFolder(path)}
              >
                {folderChipLabel(path)}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      {#if recentList.length > 0}
        <div class="settings-bg-picker__section">
          <span class="field-label">{t("settings.bgRecentFolders")}</span>
          <div class="settings-preset-row settings-bg-picker__routes">
            {#each recentList as path (path)}
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--compact settings-bg-route"
                title={path}
                on:click={() => onBrowseFolder(path)}
              >
                {folderChipLabel(path)}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      {#if !hasRouteOptions}
        <p class="settings-example">{t("settings.bgPickerNoFolder")}</p>
      {/if}
    </div>
  </details>
</div>

<style>
  .settings-bg-picker__section {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
  }

  .settings-bg-picker__routes {
    gap: var(--om-space-1);
  }

  .settings-bg-route {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .settings-bg-picker__preview-block {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
    margin-bottom: var(--om-space-2);
  }

  .settings-bg-picker__preview-mock {
    position: relative;
    height: 132px;
    overflow: hidden;
    border-radius: var(--om-radius-sm);
    border: 1px solid var(--om-border-default);
    isolation: isolate;
  }

  .settings-bg-picker__preview-image {
    position: absolute;
    inset: -14px;
    background-image: var(--preview-image);
    background-size: cover;
    background-position: center;
    filter: blur(var(--preview-blur, 0px));
    transform: scale(1.06);
  }

  .settings-bg-picker__preview-scrim {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(120% 80% at 50% -20%, var(--om-bg-spot), transparent 55%),
      linear-gradient(rgb(7 8 15 / 0.18), rgb(7 8 15 / 0.34));
  }

  .settings-bg-picker__preview-label {
    position: absolute;
    left: var(--om-space-2);
    bottom: var(--om-space-2);
    z-index: 1;
    font-size: 0.72rem;
    color: var(--om-text-secondary);
    text-shadow: 0 1px 3px rgb(0 0 0 / 0.65);
  }

  .settings-bg-picker__path-row {
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--om-space-2);
  }

  .settings-bg-picker__routes-fold {
    border: 1px solid var(--om-border-subtle);
    border-radius: var(--om-radius-sm);
    padding: 0 var(--om-space-2) var(--om-space-2);
    background: rgb(255 255 255 / 0.02);
  }

  .settings-bg-picker__routes-summary {
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--om-text-secondary);
    padding: var(--om-space-2) 0;
    list-style: none;
    user-select: none;
  }

  .settings-bg-picker__routes-summary::-webkit-details-marker {
    display: none;
  }

  .settings-bg-picker__routes-body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
    padding-top: var(--om-space-1);
  }
</style>
