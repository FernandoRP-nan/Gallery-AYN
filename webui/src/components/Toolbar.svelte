<script lang="ts">
  import { t } from "../lib/i18n";
  import {
    formatGallerySortMode,
    gallerySortModesEqual,
    parseGallerySortMode,
    sortPartLabelKey,
    type GallerySortPart,
  } from "../lib/gallerySort";

  export let destinationsMode: boolean;
  export let viewMenuOpen: boolean;
  export let includeSubfolders: boolean;
  export let groupByFolder: boolean;
  export let sectionDominantColor: boolean;
  export let timelineView: boolean;
  export let gallerySortMode: string;
  export let orgPath: string;
  export let folder: string;
  export let orgPanelOpen: boolean;
  export let routePathEl: HTMLInputElement | null;
  export let routePickerOpen: boolean;

  export let folderBackStack: string[];
  export let folderForwardStack: string[];
  export let pinnedFolders: string[];

  export let toggleDestinationsModePreserveScroll: () => void;
  export let onIncludeSubfoldersChange: (val: boolean) => void;
  export let onGroupByFolderChange: (val: boolean) => void;
  export let onSectionDominantColorChange: (val: boolean) => void;
  export let onTimelineViewChange: (val: boolean) => void;
  export let onGallerySortApply: (val: string) => void | Promise<void>;
  export let goBackFolder: () => void;
  export let goForwardFolder: () => void;
  export let goUpFolder: () => void;
  export let unpinFolder: (folder: string) => void;
  export let openPinMarkerModal: (folder: string) => void;
  export let reload: () => void;
  export let pickGalleryFolder: () => void;
  export let loadFolder: () => void | Promise<void>;
  export let openSettingsModal: () => void;

  let sortDraftParts: GallerySortPart[] = parseGallerySortMode(gallerySortMode);

  $: sortDraftDirty = !gallerySortModesEqual(formatGallerySortMode(sortDraftParts), gallerySortMode);

  function resetSortDraft() {
    sortDraftParts = parseGallerySortMode(gallerySortMode);
  }

  function toggleViewMenu() {
    if (!viewMenuOpen) resetSortDraft();
    viewMenuOpen = !viewMenuOpen;
  }

  function setSortDirection(index: number, dir: "asc" | "desc") {
    sortDraftParts = sortDraftParts.map((part, i) => (i === index ? { ...part, dir } : part));
  }

  function moveSortPriority(index: number, delta: number) {
    const next = [...sortDraftParts];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    const temp = next[target];
    next[target] = next[index];
    next[index] = temp;
    sortDraftParts = next;
  }

  function discardSortDraft() {
    resetSortDraft();
  }

  function applySortDraft() {
    void onGallerySortApply(formatGallerySortMode(sortDraftParts));
  }
</script>

<header class="tabs-bar om-panel">
  <nav class="tabs__nav">
    <button
      type="button"
      class="om-btn om-btn--tab"
      class:om-btn--active={destinationsMode}
      on:click={() => void toggleDestinationsModePreserveScroll()}
      title="Activa/desactiva modo selección y panel de destinos"
    >{t("tabs.edition")}</button>
    <div class="view-menu-wrap">
      <button
        type="button"
        class="om-btn om-btn--tab"
        class:om-btn--active={viewMenuOpen}
        aria-expanded={viewMenuOpen}
        aria-haspopup="true"
        on:click={toggleViewMenu}
      >{t("view.title")}</button>
      {#if viewMenuOpen}
        <div
          class="view-menu om-panel om-panel--lift"
          role="menu"
          tabindex="-1"
          on:click|stopPropagation={() => undefined}
          on:keydown|stopPropagation={() => undefined}
        >
          <label class="view-menu__row">
            <input
              type="checkbox"
              checked={includeSubfolders}
              on:change={(e) =>
                void onIncludeSubfoldersChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.includeSubfolders")}</span>
          </label>
          <label class="view-menu__row" title={t("view.groupByFolderHint")}>
            <input
              type="checkbox"
              checked={groupByFolder}
              on:change={(e) => void onGroupByFolderChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.groupByFolder")}</span>
          </label>
          <label class="view-menu__row" title={t("view.sectionDominantColorHint")}>
            <input
              type="checkbox"
              checked={sectionDominantColor}
              on:change={(e) =>
                void onSectionDominantColorChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.sectionDominantColor")}</span>
          </label>
          <label class="view-menu__row" title={t("view.timelineViewHint")}>
            <input
              type="checkbox"
              checked={timelineView}
              on:change={(e) => void onTimelineViewChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.timelineView")}</span>
          </label>
          <fieldset class="view-menu__fieldset view-menu__fieldset--sort">
            <div class="view-menu__legend">{t("view.sortLabel")}</div>
            <p class="view-menu__sort-hint">{t("view.sortPendingHint")}</p>
            <ol class="sort-priority-list">
              {#each sortDraftParts as modeObj, index (modeObj.key)}
                <li class="sort-priority-item">
                  <span class="sort-priority-rank" aria-hidden="true">{index + 1}</span>
                  <div class="sort-priority-main">
                    <span class="sort-priority-label">{t(sortPartLabelKey(modeObj.key))}</span>
                    <span class="sort-priority-rank-label">{t("view.sortPriority").replace("{n}", String(index + 1))}</span>
                  </div>
                  <div class="sort-priority-actions">
                    <button
                      type="button"
                      class="sort-priority-chip"
                      class:sort-priority-chip--active={modeObj.dir === "asc"}
                      title={t("view.sortAsc")}
                      on:click={() => setSortDirection(index, "asc")}
                    >
                      {t("view.sortAsc")}
                    </button>
                    <button
                      type="button"
                      class="sort-priority-chip"
                      class:sort-priority-chip--active={modeObj.dir === "desc"}
                      title={t("view.sortDesc")}
                      on:click={() => setSortDirection(index, "desc")}
                    >
                      {t("view.sortDesc")}
                    </button>
                    <div class="sort-priority-move">
                      <button
                        type="button"
                        class="sort-priority-btn"
                        disabled={index === 0}
                        title="Subir prioridad"
                        aria-label="Subir prioridad"
                        on:click={() => moveSortPriority(index, -1)}
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        class="sort-priority-btn"
                        disabled={index === sortDraftParts.length - 1}
                        title="Bajar prioridad"
                        aria-label="Bajar prioridad"
                        on:click={() => moveSortPriority(index, 1)}
                      >
                        ▼
                      </button>
                    </div>
                  </div>
                </li>
              {/each}
            </ol>
            <div class="sort-priority-footer">
              <button
                type="button"
                class="om-btn om-btn--ghost om-btn--mini"
                disabled={!sortDraftDirty}
                on:click={discardSortDraft}
              >
                {t("view.sortCancel")}
              </button>
              <button
                type="button"
                class="om-btn om-btn--primary om-btn--mini"
                disabled={!sortDraftDirty}
                on:click={applySortDraft}
              >
                {t("view.sortApply")}
              </button>
            </div>
          </fieldset>
          <p class="view-menu__hint">{t("view.timelineHint")}</p>
        </div>
      {/if}
    </div>
    <button
      type="button"
      class="om-btn om-btn--tab"
      on:click={() => {
        orgPath = folder || orgPath;
        orgPanelOpen = true;
      }}
    >{t("tabs.organize")}</button>
  </nav>
  <div class="route__row route__row--inline">
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("route.back")} on:click={goBackFolder} disabled={folderBackStack.length === 0}>←</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("route.forward")} on:click={goForwardFolder} disabled={folderForwardStack.length === 0}>→</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("route.up")} on:click={goUpFolder}>↑</button>
    <div class="route__path-wrap">
      <input
        id="gallery-folder-input"
        class="om-input route__path"
        type="text"
        bind:this={routePathEl}
        bind:value={folder}
        placeholder={t("route.pathPlaceholder")}
        title={t("route.pathInputTitle")}
        on:focus={() => (routePickerOpen = true)}
        on:keydown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void loadFolder();
          }
        }}
      />
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--icon route__path-action"
        title={pinnedFolders.includes(folder.trim()) ? t("route.pinRemove") : t("route.pinAdd")}
        on:click={() => (pinnedFolders.includes(folder.trim()) ? unpinFolder(folder) : openPinMarkerModal(folder))}
      >{pinnedFolders.includes(folder.trim()) ? "★" : "☆"}</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon route__path-action" title={t("route.reloadGallery")} on:click={reload}>↻</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon route__path-action" title={t("route.browseFolder")} on:click={pickGalleryFolder}>
        <svg class="route-folder-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path fill="currentColor" d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z" />
        </svg>
      </button>
    </div>
  </div>
  <button
    type="button"
    class="om-btn om-btn--ghost om-btn--icon om-btn--settings"
    title={t("route.settingsTitle")}
    aria-label={t("route.settingsAria")}
    on:click={openSettingsModal}
  >
    <svg class="settings-gear" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  </button>
</header>

<style>
.tabs-bar {
    display: flex;
    align-items: center;
    gap: var(--om-space-1);
    flex-wrap: wrap;
    padding-block: 4px;
    padding-inline: 8px;
    position: relative;
    z-index: 60;
  }
.view-menu-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
  }
.view-menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 90;
    min-width: min(360px, calc(100vw - 24px));
    padding: var(--om-space-3);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    box-shadow: var(--om-shadow-lg);
  }
.view-menu__row {
    display: flex;
    align-items: flex-start;
    gap: var(--om-space-2);
    font-size: 0.85rem;
    color: var(--om-text-secondary);
    cursor: pointer;
  }
.view-menu__row input:disabled + span {
    opacity: 0.55;
  }
.view-menu__fieldset {
    border: 0;
    padding: 0;
    margin: 0;
  }
.view-menu__fieldset--sort {
    padding: 10px;
    border-radius: var(--om-radius-md, 8px);
    background: color-mix(in oklab, var(--om-surface-2) 72%, transparent);
    border: 1px solid var(--om-border-default);
  }
.view-menu__legend {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--om-text-muted);
    margin-bottom: var(--om-space-2);
  }
.view-menu__sort-hint {
    margin: 0 0 10px;
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--om-text-muted);
  }
.sort-priority-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
.sort-priority-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--om-surface-1, #1a1a1a);
    border: 1px solid var(--om-border-default);
    border-radius: var(--om-radius-sm, 6px);
  }
.sort-priority-rank {
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--om-accent, #007acc);
    background: color-mix(in oklab, var(--om-accent, #007acc) 18%, transparent);
    border: 1px solid color-mix(in oklab, var(--om-accent, #007acc) 35%, transparent);
  }
.sort-priority-main {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
.sort-priority-label {
    font-size: 0.88rem;
    color: var(--om-text-primary);
    font-weight: 500;
  }
.sort-priority-rank-label {
    font-size: 0.68rem;
    color: var(--om-text-muted);
  }
.sort-priority-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
.sort-priority-chip {
    min-height: 1.7rem;
    padding: 0 8px;
    border-radius: 999px;
    border: 1px solid var(--om-border-default);
    background: transparent;
    color: var(--om-text-secondary);
    font-size: 0.68rem;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }
.sort-priority-chip--active {
    background: color-mix(in oklab, var(--om-accent, #007acc) 22%, transparent);
    border-color: color-mix(in oklab, var(--om-accent, #007acc) 45%, transparent);
    color: var(--om-text-primary);
  }
.sort-priority-move {
    display: inline-flex;
    gap: 4px;
    margin-left: 2px;
  }
.sort-priority-btn {
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--om-surface-3, #2a2a2a);
    border: 1px solid var(--om-border-default);
    border-radius: 4px;
    color: var(--om-text-secondary);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    transition: all 0.15s ease;
  }
.sort-priority-btn:hover:not(:disabled) {
    background: var(--om-accent, #007acc);
    color: #fff;
    border-color: var(--om-accent);
  }
.sort-priority-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
.sort-priority-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--om-border-default);
  }
.view-menu__hint {
    margin: 0;
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--om-text-muted);
  }
.tabs__nav {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
    align-items: center;
    flex: 0 0 auto;
  }
.route__row {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
  }
.route__row--inline {
    flex: 1 1 680px;
    min-width: min(420px, 100%);
  }
.route__path {
    flex: 1;
    min-width: 0;
  }
.route__path-wrap {
    flex: 1;
    min-width: min(320px, 100%);
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 4px;
    border: 1px solid var(--om-border-default);
    border-radius: var(--thumb-tile-radius, var(--om-radius-md));
    background: color-mix(in oklab, var(--om-surface-2) 88%, transparent);
  }
.route__path-wrap .route__path {
    border: 0;
    background: transparent;
    box-shadow: none;
    padding-inline: 6px;
  }
.route__path-action {
    min-width: 1.8rem;
    min-height: 1.8rem;
    padding: 0 6px;
  }
.route-folder-ico {
    width: 1rem;
    height: 1rem;
    display: block;
    color: currentColor;
  }
.settings-gear {
    width: 22px;
    height: 22px;
    display: block;
    flex-shrink: 0;
  }
</style>
