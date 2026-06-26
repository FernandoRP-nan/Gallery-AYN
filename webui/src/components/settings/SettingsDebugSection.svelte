<script lang="ts">
  import { t } from "../../lib/i18n";
  import {
    GALLERY_DEBUG_KINDS,
    type GalleryDebugFilters,
    type GalleryDebugKind,
    setGalleryDebugFilters,
  } from "../../lib/galleryDebugLog";

  export let debugLogEnabled = false;
  export let debugLogFilters: GalleryDebugFilters;

  const filterLabelKey = (kind: GalleryDebugKind): string => `settings.debugFilter.${kind}`;

  function toggleFilter(kind: GalleryDebugKind, checked: boolean) {
    debugLogFilters = { ...debugLogFilters, [kind]: checked };
    setGalleryDebugFilters(debugLogFilters);
  }
</script>

<div class="settings-group settings-group--debug">
  <p class="settings-lead">{t("settings.debugLead")}</p>
  <label class="check">
    <input type="checkbox" bind:checked={debugLogEnabled} />
    {t("settings.debugLogEnabled")}
  </label>
  <p class="settings-hint">{t("settings.debugLogHint")}</p>

  {#if debugLogEnabled}
    <fieldset class="debug-filters">
      <legend>{t("settings.debugFiltersLegend")}</legend>
      <p class="settings-hint settings-hint--tight">{t("settings.debugFiltersHint")}</p>
      <div class="debug-filters__grid">
        {#each GALLERY_DEBUG_KINDS as kind (kind)}
          <label class="check check--compact">
            <input
              type="checkbox"
              checked={debugLogFilters[kind] !== false}
              on:change={(e) => toggleFilter(kind, (e.currentTarget as HTMLInputElement).checked)}
            />
            {t(filterLabelKey(kind))}
          </label>
        {/each}
      </div>
    </fieldset>
  {/if}
</div>

<style>
  .debug-filters {
    margin: 10px 0 0;
    padding: 10px 12px;
    border: 1px solid var(--om-border-subtle);
    border-radius: var(--om-radius-sm);
  }
  .debug-filters legend {
    padding: 0 4px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }
  .settings-hint--tight {
    margin-top: 4px;
    margin-bottom: 8px;
  }
  .debug-filters__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
    gap: 6px 10px;
  }
  .check--compact {
    font-size: 0.75rem;
    gap: 6px;
  }
</style>
