<script lang="ts">
  import "./settings/panel.css";
  import { t } from "../lib/i18n";
  import { galleryGridCellPx } from "../lib/thumbScale";
  import type { UiThemeId } from "../lib/uiTheme";
  import SettingsAppearanceSection from "./settings/SettingsAppearanceSection.svelte";
  import SettingsDestinationsSection from "./settings/SettingsDestinationsSection.svelte";
  import SettingsMarkersSection from "./settings/SettingsMarkersSection.svelte";
  import SettingsPerformanceSection from "./settings/SettingsPerformanceSection.svelte";
  import SettingsVideoSection from "./settings/SettingsVideoSection.svelte";
  import SettingsMessSection from "./settings/SettingsMessSection.svelte";
  import SettingsShortcutsSection from "./settings/SettingsShortcutsSection.svelte";
  import SettingsThumbsSection from "./settings/SettingsThumbsSection.svelte";
  import SettingsDebugSection from "./settings/SettingsDebugSection.svelte";

  import type { TreeNode } from "../lib/itemTree";

  type SettingsTabId =
    | "performance"
    | "thumbs"
    | "appearance"
    | "video"
    | "shortcuts"
    | "mess"
    | "destinations"
    | "markers"
    | "debug";

  export let thumbsPerPage: number;
  export let galleryUnlimitedBatchSize: number;
  export let galleryWindowOverscanBefore: number;
  export let galleryWindowOverscanAfter: number;
  export let galleryJumpCoreOverscanBefore: number;
  export let galleryJumpCoreOverscanAfter: number;
  export let gallerySlidingWindowEnabled: boolean;
  export let gallerySlidingWindowMaxItems: number;
  export let galleryThumbBuildWorkers: number;
  export let galleryThumbHqWorkers: number;
  export let galleryThumbHqVisibleSequential: number;
  export let debugLogEnabled = false;
  export let videoTranscodePreset: "turbo" | "fast" | "quality" = "fast";
  export let videoTranscodeMaxHeight = 1080;
  export let videoTranscodeHw: "auto" | "off" = "auto";
  export let settingsThumbPresetIdx: number;
  export let settingsThumbScaleDraft: number;
  export let galleryThumbQualityPreset: "balanced" | "sharp" | "hidpi" | "performance" = "balanced";
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let uiTheme: UiThemeId;
  export let showThumbLabels: boolean;
  export let thumbFrameVisible: boolean;
  export let thumbCardStyle: "soft" | "flat" | "outlined";
  export let keyboardShortcuts: Record<string, string>;
  export let defaultShortcuts: Record<string, string>;
  export let pinterestMasonry = false;
  export let suggestionsEnabled = false;
  export let messScanMaxFiles = 400;
  export let destTree: TreeNode[];
  export let markerTree: TreeNode[];
  export let onDestTreeChange: (next: TreeNode[]) => void;
  export let onMarkerTreeChange: (next: TreeNode[]) => void;
  export let onPickDestFolder: () => Promise<string | null>;
  export let onPickMarkerFolder: () => Promise<string | null>;

  export let themeNameLabel: (id: UiThemeId) => string;
  export let onCancel: () => void;
  export let onSave: () => void;

  let activeTab: SettingsTabId = "performance";

  const tabs: { id: SettingsTabId; labelKey: string }[] = [
    { id: "performance", labelKey: "settings.tabPerformance" },
    { id: "thumbs", labelKey: "settings.tabThumbs" },
    { id: "appearance", labelKey: "settings.tabAppearance" },
    { id: "video", labelKey: "settings.tabVideo" },
    { id: "shortcuts", labelKey: "settings.tabShortcuts" },
    { id: "mess", labelKey: "settings.tabMess" },
    { id: "destinations", labelKey: "settings.tabDestinations" },
    { id: "markers", labelKey: "settings.tabMarkers" },
    { id: "debug", labelKey: "settings.tabDebug" },
  ];

  $: previewCellPx = galleryGridCellPx(settingsThumbScaleDraft);
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<div class="sm-backdrop" role="presentation" on:click|self={onCancel}>
  <div
    class="modal modal--settings om-panel om-panel--lift sm-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="settings-title"
    tabindex="-1"
    on:click|stopPropagation={() => undefined}
  >
    <header class="modal__head">
      <strong id="settings-title">{t("settings.modalTitle")}</strong>
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--close"
        aria-label={t("common.closeModalAria")}
        title={t("common.close")}
        on:click={onCancel}>✕</button
      >
    </header>

    <nav class="settings-tabs" aria-label={t("settings.tabsAria")}>
      {#each tabs as tab (tab.id)}
        <button
          type="button"
          class="settings-tabs__btn"
          class:settings-tabs__btn--active={activeTab === tab.id}
          aria-selected={activeTab === tab.id}
          on:click={() => (activeTab = tab.id)}>{t(tab.labelKey)}</button
        >
      {/each}
    </nav>

    <section class="settings-body">
      {#if activeTab === "performance"}
        <SettingsPerformanceSection
          bind:thumbsPerPage
          bind:galleryUnlimitedBatchSize
          bind:galleryWindowOverscanBefore
          bind:galleryWindowOverscanAfter
          bind:galleryJumpCoreOverscanBefore
          bind:galleryJumpCoreOverscanAfter
          bind:gallerySlidingWindowEnabled
          bind:gallerySlidingWindowMaxItems
          bind:galleryThumbBuildWorkers
          bind:galleryThumbHqWorkers
          bind:galleryThumbHqVisibleSequential
        />
      {:else if activeTab === "thumbs"}
        <SettingsThumbsSection
          bind:settingsThumbPresetIdx
          bind:settingsThumbScaleDraft
          bind:galleryThumbQualityPreset
          bind:thumbGapPx
          bind:thumbImageRadiusPx
          bind:thumbTileRadiusPx
        />
      {:else if activeTab === "appearance"}
        <SettingsAppearanceSection
          bind:uiTheme
          bind:showThumbLabels
          bind:thumbFrameVisible
          bind:thumbCardStyle
          {previewCellPx}
          {thumbGapPx}
          {thumbImageRadiusPx}
          {thumbTileRadiusPx}
          {themeNameLabel}
        />
      {:else if activeTab === "video"}
        <SettingsVideoSection
          bind:videoTranscodePreset
          bind:videoTranscodeMaxHeight
          bind:videoTranscodeHw
        />
      {:else if activeTab === "shortcuts"}
        <SettingsShortcutsSection bind:keyboardShortcuts {defaultShortcuts} />
      {:else if activeTab === "mess"}
        <SettingsMessSection
          bind:suggestionsEnabled
          bind:suggestionsMasonry={pinterestMasonry}
          bind:messScanMaxFiles
        />
      {:else if activeTab === "destinations"}
        <SettingsDestinationsSection {destTree} {onDestTreeChange} {onPickDestFolder} />
      {:else if activeTab === "markers"}
        <SettingsMarkersSection {markerTree} {onMarkerTreeChange} {onPickMarkerFolder} />
      {:else if activeTab === "debug"}
        <SettingsDebugSection bind:debugLogEnabled />
      {/if}
    </section>

    <div class="settings-actions">
      <button type="button" class="om-btn om-btn--ghost" on:click={onCancel}>{t("common.cancel")}</button>
      <button type="button" class="om-btn om-btn--primary" on:click={onSave}>{t("common.save")}</button>
    </div>
  </div>
</div>
