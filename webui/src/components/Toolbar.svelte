<script lang="ts">
  import { t } from '../lib/i18n';

  // Bindings y estado
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
  
  // Arreglos
  export let folderBackStack: string[];
  export let folderForwardStack: string[];
  export let pinnedFolders: string[];

  // Funciones
  export let toggleDestinationsModePreserveScroll: () => void;
  export let onIncludeSubfoldersChange: (val: boolean) => void;
  export let onGroupByFolderChange: (val: boolean) => void;
  export let onSectionDominantColorChange: (val: boolean) => void;
  export let onTimelineViewChange: (val: boolean) => void;
  export let onGallerySortChange: (val: string) => void;
  export let goBackFolder: () => void;
  export let goForwardFolder: () => void;
  export let goUpFolder: () => void;
  export let unpinFolder: (folder: string) => void;
  export let openPinMarkerModal: (folder: string) => void;
  export let reload: () => void;
  export let pickGalleryFolder: () => void;
  export let openSettingsModal: () => void;

  // Lista de prioridad de ordenamiento reactiva
  $: sortPriorityParts = (() => {
    const parts = (gallerySortMode || "name,mtime,type").split(',').map(x => x.trim()).filter(Boolean);
    const allModes = ['name', 'mtime', 'type'];
    for (const m of allModes) {
      if (!parts.includes(m)) {
        parts.push(m);
      }
    }
    return parts;
  })();
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
        on:click={() => (viewMenuOpen = !viewMenuOpen)}
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
          <fieldset class="view-menu__fieldset">
            <div class="view-menu__legend">{t("view.sortLabel")}</div>
            <div class="sort-priority-list">
              {#each sortPriorityParts as modeKey, index}
                <div class="sort-priority-item">
                  <span class="sort-priority-label">
                    {#if modeKey === 'name'}
                      {t("view.sortName")}
                    {:else if modeKey === 'mtime'}
                      {t("view.sortDate")}
                    {:else if modeKey === 'type'}
                      {t("view.sortType")}
                    {/if}
                  </span>
                  <div class="sort-priority-actions">
                    <button
                      type="button"
                      class="sort-priority-btn"
                      disabled={index === 0}
                      title="Subir prioridad"
                      on:click={() => {
                        const nextParts = [...sortPriorityParts];
                        const temp = nextParts[index - 1];
                        nextParts[index - 1] = nextParts[index];
                        nextParts[index] = temp;
                        onGallerySortChange(nextParts.join(','));
                      }}
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      class="sort-priority-btn"
                      disabled={index === sortPriorityParts.length - 1}
                      title="Bajar prioridad"
                      on:click={() => {
                        const nextParts = [...sortPriorityParts];
                        const temp = nextParts[index + 1];
                        nextParts[index + 1] = nextParts[index];
                        nextParts[index] = temp;
                        onGallerySortChange(nextParts.join(','));
                      }}
                    >
                      ▼
                    </button>
                  </div>
                </div>
              {/each}
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
.view-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 80;
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
    min-width: min(320px, calc(100vw - 24px));
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
.view-menu__legend {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--om-text-muted);
    margin-bottom: var(--om-space-2);
  }
.sort-priority-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-block: 4px;
  }
.sort-priority-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    background: color-mix(in oklab, var(--om-surface-2) 60%, transparent);
    border: 1px solid var(--om-border-default);
    border-radius: var(--om-radius-sm, 4px);
    font-size: 0.85rem;
    color: var(--om-text-primary);
  }
.sort-priority-label {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
.sort-priority-actions {
    display: flex;
    gap: 4px;
    margin-left: 8px;
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
