<script lang="ts">
  import { t } from "../lib/i18n";
  import {
    formatGallerySortMode,
    gallerySortModesEqual,
    parseGallerySortMode,
    sortPartLabelKey,
    SORT_KEYS,
    type GallerySortPart,
  } from "../lib/gallerySort";

  export let destinationsMode: boolean;
  export let viewMenuOpen: boolean;
  export let includeSubfolders: boolean;
  export let showOtherFiles: boolean;
  export let groupByFolder: boolean;
  export let groupByAlpha: boolean;
  export let sectionDominantColor: boolean;
  export let timelineView: boolean;
  export let galleryMasonryView: boolean;
  export let gallerySortMode: string;
  export let dynamicNameRegex: boolean;
  export let orgPath: string;
  export let folder: string;
  export let orgPanelOpen: boolean;
  export let messPanelOpen: boolean;
  export let routePathEl: HTMLInputElement | null;
  export let routePickerOpen: boolean;

  export let folderBackStack: string[];
  export let folderForwardStack: string[];
  export let pinnedFolders: string[];

  export let toggleDestinationsModePreserveScroll: () => void;
  export let onIncludeSubfoldersChange: (val: boolean) => void;
  export let onShowOtherFilesChange: (val: boolean) => void;
  export let onGroupByFolderChange: (val: boolean) => void;
  export let onGroupByAlphaChange: (val: boolean) => void;
  export let onSectionDominantColorChange: (val: boolean) => void;
  export let onTimelineViewChange: (val: boolean) => void;
  export let onGalleryMasonryViewChange: (val: boolean) => void;
  export let onGallerySortApply: (val: string) => void | Promise<void>;
  export let onDynamicNameRegexChange: (val: boolean) => void | Promise<void>;
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

  function toggleSortKeyActive(key: GallerySortPart["key"]) {
    const isCurrentlyActive = sortDraftParts.some((p) => p.key === key);
    if (isCurrentlyActive) {
      sortDraftParts = sortDraftParts.filter((p) => p.key !== key);
    } else {
      const defaultDir = (key === "exif_month" || key === "mtime" || key === "ctime" || key === "exif") ? "desc" : "asc";
      sortDraftParts = [...sortDraftParts, { key, dir: defaultDir }];
    }
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
          <label class="view-menu__row">
            <input
              type="checkbox"
              checked={showOtherFiles}
              on:change={(e) =>
                void onShowOtherFilesChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.showOtherFiles")}</span>
          </label>
          <label class="view-menu__row" title={t("view.groupByFolderHint")}>
            <input
              type="checkbox"
              checked={groupByFolder}
              on:change={(e) => void onGroupByFolderChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.groupByFolder")}</span>
          </label>
          <label class="view-menu__row" title={t("view.groupByAlphaHint")}>
            <input
              type="checkbox"
              checked={groupByAlpha}
              on:change={(e) => void onGroupByAlphaChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.groupByAlpha")}</span>
          </label>
          <label class="view-menu__row" title={t("view.sectionDominantColorHint")}>
            <input
              type="checkbox"
              checked={sectionDominantColor}
              disabled={!groupByFolder}
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
          <label class="view-menu__row" title={t("view.masonryViewHint")}>
            <input
              type="checkbox"
              checked={galleryMasonryView}
              on:change={(e) =>
                void onGalleryMasonryViewChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.masonryView")}</span>
          </label>
          <div class="view-menu__divider" aria-hidden="true"></div>
          <div class="view-menu__sort-head">
            <span class="view-menu__legend">{t("view.sortLabel")}</span>
            {#if sortDraftDirty}
              <span class="view-menu__sort-badge">{t("view.sortPendingHint")}</span>
            {/if}
          </div>
          <label class="view-menu__row" title={t("view.dynamicNameRegexHint")}>
            <input
              type="checkbox"
              checked={dynamicNameRegex}
              on:change={(e) =>
                void onDynamicNameRegexChange((e.currentTarget as HTMLInputElement).checked)}
            />
            <span>{t("view.dynamicNameRegex")}</span>
          </label>
          <ol class="sort-priority-list">
            {#each sortDraftParts as modeObj, index (modeObj.key)}
              <li class="sort-priority-item">
                <span class="sort-priority-rank" aria-hidden="true">{index + 1}</span>
                <span class="sort-priority-label">{t(sortPartLabelKey(modeObj.key))}</span>
                <div class="sort-priority-actions">
                  <button
                    type="button"
                    class="sort-priority-chip"
                    class:sort-priority-chip--active={modeObj.dir === "asc"}
                    title={t("view.sortAsc")}
                    on:click={() => setSortDirection(index, "asc")}
                  >↑</button>
                  <button
                    type="button"
                    class="sort-priority-chip"
                    class:sort-priority-chip--active={modeObj.dir === "desc"}
                    title={t("view.sortDesc")}
                    on:click={() => setSortDirection(index, "desc")}
                  >↓</button>
                  <button
                    type="button"
                    class="sort-priority-btn"
                    disabled={index === 0}
                    title="Subir prioridad"
                    aria-label="Subir prioridad"
                    on:click={() => moveSortPriority(index, -1)}
                  >▲</button>
                  <button
                    type="button"
                    class="sort-priority-btn"
                    disabled={index === sortDraftParts.length - 1}
                    title="Bajar prioridad"
                    aria-label="Bajar prioridad"
                    on:click={() => moveSortPriority(index, 1)}
                  >▼</button>
                  <button
                    type="button"
                    class="sort-deactivate-btn"
                    title="Desactivar criterio"
                    aria-label="Desactivar criterio"
                    on:click={() => toggleSortKeyActive(modeObj.key)}
                  >×</button>
                </div>
              </li>
            {/each}
          </ol>
          {#if SORT_KEYS.some((k) => !sortDraftParts.some((p) => p.key === k))}
            <div class="view-menu__sort-head view-menu__sort-head--inactive">
              <span class="view-menu__legend">Añadir criterio</span>
            </div>
            <div class="sort-inactive-wrap">
              {#each SORT_KEYS as key}
                {#if !sortDraftParts.some((p) => p.key === key)}
                  <button
                    type="button"
                    class="sort-inactive-chip"
                    on:click={() => toggleSortKeyActive(key)}
                  >
                    + {t(sortPartLabelKey(key))}
                  </button>
                {/if}
              {/each}
            </div>
          {/if}
          <div class="sort-priority-footer">
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--mini"
              disabled={!sortDraftDirty}
              on:click={discardSortDraft}
            >{t("view.sortCancel")}</button>
            <button
              type="button"
              class="om-btn om-btn--primary om-btn--mini"
              disabled={!sortDraftDirty}
              on:click={applySortDraft}
            >{t("view.sortApply")}</button>
          </div>
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
    <button
      type="button"
      class="om-btn om-btn--tab"
      on:click={() => {
        messPanelOpen = true;
      }}
    >{t("tabs.mess")}</button>
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
    z-index: 2;
    min-width: min(320px, calc(100vw - 24px));
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    box-shadow: var(--om-shadow-lg);
  }
.view-menu__row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: var(--om-text-secondary);
    cursor: pointer;
    min-height: 1.6rem;
    padding: 2px 0;
  }
.view-menu__row input:disabled + span {
    opacity: 0.45;
  }
.view-menu__divider {
    height: 1px;
    margin: 4px 0;
    background: var(--om-border-default);
    opacity: 0.65;
  }
.view-menu__sort-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    padding-top: 2px;
  }
  .view-menu__legend {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--om-text-muted);
  }
  .view-menu__sort-badge {
    font-size: 0.65rem;
    color: var(--om-accent, #007acc);
    opacity: 0.9;
  }
.sort-priority-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
.sort-priority-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 8px;
    padding: 4px 2px;
    border-bottom: 1px solid color-mix(in oklab, var(--om-border-default) 55%, transparent);
  }
.sort-priority-item:last-child {
    border-bottom: 0;
  }
.sort-priority-rank {
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--om-text-muted);
    background: transparent;
    border: 1px solid var(--om-border-default);
  }
.sort-priority-label {
    font-size: 0.82rem;
    color: var(--om-text-primary);
    min-width: 0;
}
.sort-priority-actions {
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
.sort-priority-chip {
    width: 1.5rem;
    height: 1.5rem;
    padding: 0;
    border-radius: 4px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--om-text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    transition: color 0.12s ease, background 0.12s ease;
  }
.sort-priority-chip--active {
    background: color-mix(in oklab, var(--om-accent, #007acc) 18%, transparent);
    border-color: color-mix(in oklab, var(--om-accent, #007acc) 35%, transparent);
    color: var(--om-text-primary);
  }
.sort-priority-btn {
    width: 1.35rem;
    height: 1.35rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    border-radius: 3px;
    color: var(--om-text-muted);
    font-size: 0.62rem;
    cursor: pointer;
    padding: 0;
  }
.sort-priority-btn:hover:not(:disabled) {
    color: var(--om-text-primary);
    background: color-mix(in oklab, var(--om-surface-3) 80%, transparent);
  }
.sort-deactivate-btn {
    width: 1.35rem;
    height: 1.35rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    border-radius: 3px;
    color: var(--om-text-muted);
    font-size: 0.85rem;
    font-weight: bold;
    cursor: pointer;
    padding: 0;
    transition: color 0.12s ease, background 0.12s ease;
  }
.sort-deactivate-btn:hover {
    color: #ff4d4d;
    background: color-mix(in oklab, #ff4d4d 12%, transparent);
  }
.sort-inactive-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 4px 2px;
  }
.sort-inactive-chip {
    padding: 3px 8px;
    border: 1px solid var(--om-border-default);
    background: color-mix(in oklab, var(--om-surface-2) 65%, transparent);
    color: var(--om-text-secondary);
    border-radius: 99px;
    font-size: 0.72rem;
    cursor: pointer;
    transition: all 0.12s ease;
  }
.sort-inactive-chip:hover {
    background: color-mix(in oklab, var(--om-accent, #007acc) 12%, transparent);
    border-color: color-mix(in oklab, var(--om-accent, #007acc) 45%, transparent);
    color: var(--om-text-primary);
  }
.view-menu__sort-head--inactive {
    margin-top: 6px;
    border-top: 1px dashed color-mix(in oklab, var(--om-border-default) 45%, transparent);
    padding-top: 8px;
  }
.sort-priority-btn:disabled {
    opacity: 0.25;
    cursor: not-allowed;
  }
.sort-priority-footer {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    margin-top: 4px;
    padding-top: 6px;
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
