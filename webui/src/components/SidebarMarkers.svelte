<script lang="ts">
  import { t } from '../lib/i18n';

  // Bindings y estado
  export let routePickerOpen: boolean;
  export let pinMarkerOpen: boolean;
  export let folder: string;
  export let pinnedFolders: string[];
  export let recentUnpinnedFolders: string[];
  export let pinMarkerName: string;
  export let pinMarkerPath: string;

  // Funciones
  export let pickGalleryFolder: () => void;
  export let loadFolder: () => void;
  export let pickRecentFolder: (p: string) => void;
  export let onPinnedContextMenu: (e: MouseEvent, p: string) => void;
  export let markerLabelForPath: (p: string) => string;
  export let pathTailLabel: (p: string) => string;
  export let openPinMarkerModal: (p: string) => void;
  export let closePinMarkerModal: () => void;
  export let savePinMarkerModal: () => void;
</script>

{#if routePickerOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="overlay overlay--dim" role="presentation" on:click|self={() => (routePickerOpen = false)}>
    <div
      class="modal modal--route-picker om-panel om-panel--lift"
      role="dialog"
      aria-modal="true"
      aria-labelledby="route-picker-title"
      tabindex="-1"
      on:click|stopPropagation={() => undefined}
    >
      <header class="modal__head">
        <strong id="route-picker-title">{t("routePicker.title")}</strong>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--close"
          aria-label={t("common.closeModalAria")}
          title={t("common.close")}
          on:click={() => (routePickerOpen = false)}>✕</button
        >
      </header>
      <section class="route-picker__body">
        <div class="route-picker__input-row">
          <input
            class="om-input route-picker__input"
            bind:value={folder}
            placeholder={t("route.pathPlaceholder")}
            on:keydown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void loadFolder();
              }
            }}
          />
          <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("route.browseFolder")} on:click={pickGalleryFolder}>
            <svg class="route-folder-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path fill="currentColor" d="M3 7.5a2 2 0 0 1 2-2h5.2l1.8 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9z" />
            </svg>
          </button>
          <button type="button" class="om-btn om-btn--primary" on:click={loadFolder}>{t("routePicker.open")}</button>
        </div>
        {#if pinnedFolders.length > 0}
          <div class="recent-folders__head">
            <span class="field-label">{t("routePicker.pinnedHead")}</span>
          </div>
          <div class="recent-folders__list">
            {#each pinnedFolders as p}
              <button
                type="button"
                class="om-btn om-btn--ghost recent-folders__chip recent-folders__chip--pinned"
                title={p}
                on:click={() => pickRecentFolder(p)}
                on:contextmenu={(e) => onPinnedContextMenu(e, p)}
              >
                {markerLabelForPath(p)}
              </button>
            {/each}
          </div>
        {/if}
        {#if recentUnpinnedFolders.length > 0}
          <div class="recent-folders__head">
            <span class="field-label">{t("routePicker.recentHead")}</span>
          </div>
          <div class="recent-folders__list">
            {#each recentUnpinnedFolders as p}
              <div class="recent-folders__chip-wrap">
                <button type="button" class="om-btn om-btn--ghost recent-folders__chip" title={p} on:click={() => pickRecentFolder(p)}>
                  {pathTailLabel(p)}
                </button>
                <button type="button" class="om-btn om-btn--ghost recent-folders__pin" title={t("routePicker.createMarkerTitle")} on:click={() => openPinMarkerModal(p)}>☆</button>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    </div>
  </div>
{/if}

{#if pinMarkerOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="overlay overlay--dim overlay--dest-form" role="presentation" on:click|self={closePinMarkerModal}>
    <div
      class="modal modal--dest-form om-panel om-panel--lift"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pin-marker-title"
      tabindex="-1"
      on:click|stopPropagation={() => undefined}
    >
      <header class="modal__head">
        <strong id="pin-marker-title">{t("pinMarker.title")}</strong>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--close"
          aria-label={t("common.closeModalAria")}
          title={t("common.close")}
          on:click={closePinMarkerModal}>✕</button
        >
      </header>
      <section class="dest-form-body">
        <label class="field-label" for="pin-marker-name">{t("destinations.nameLabel")}</label>
        <input id="pin-marker-name" class="om-input" type="text" bind:value={pinMarkerName} placeholder={t("pinMarker.namePlaceholder")} />
        <label class="field-label" for="pin-marker-path">{t("destinations.pathLabel")}</label>
        <input id="pin-marker-path" class="om-input" type="text" bind:value={pinMarkerPath} placeholder={t("pinMarker.pathPlaceholder")} />
      </section>
      <div class="settings-actions">
        <button type="button" class="om-btn om-btn--ghost" on:click={closePinMarkerModal}>{t("common.cancel")}</button>
        <button type="button" class="om-btn om-btn--primary" on:click={savePinMarkerModal}>{t("common.save")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
.recent-folders__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }
.recent-folders__list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
  }
.recent-folders__chip-wrap {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 100%;
  }
.recent-folders__chip {
    max-width: 100%;
    text-align: left;
    font-size: 0.7rem;
    line-height: 1.2;
    white-space: normal;
    word-break: break-all;
    padding: 0.2rem 0.55rem;
    min-height: 1.65rem;
  }
.recent-folders__pin {
    min-width: 1.55rem;
    min-height: 1.55rem;
    padding: 0.1rem 0.3rem;
    font-size: 0.78rem;
    line-height: 1;
    color: var(--om-accent-2);
  }
.route-picker__body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    min-height: 0;
    overflow: auto;
  }
.route-picker__input-row {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }
.route-picker__input {
    flex: 1;
    min-width: min(260px, 100%);
  }
.dest-form-body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
  }
</style>
