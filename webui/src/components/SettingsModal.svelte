<script lang="ts">
  import "./settings/panel.css";
  import { t } from "../lib/i18n";
  import { galleryGridCellPx } from "../lib/thumbScale";
  import type { UiThemeId } from "../lib/uiTheme";
  import type { BgScopeId, CustomTheme, ThemeSelection, UiFontId } from "../lib/uiAppearance";
  import SettingsAppearanceSection from "./settings/SettingsAppearanceSection.svelte";
  import SettingsDestinationsSection from "./settings/SettingsDestinationsSection.svelte";
  import SettingsMarkersSection from "./settings/SettingsMarkersSection.svelte";
  import SettingsPerformanceSection from "./settings/SettingsPerformanceSection.svelte";
  import SettingsVideoSection from "./settings/SettingsVideoSection.svelte";
  import SettingsMessSection from "./settings/SettingsMessSection.svelte";
  import SettingsShortcutsSection from "./settings/SettingsShortcutsSection.svelte";
  import SettingsThumbsSection from "./settings/SettingsThumbsSection.svelte";
  import SettingsDebugSection from "./settings/SettingsDebugSection.svelte";
  import SettingsInterfaceSection from "./settings/SettingsInterfaceSection.svelte";

  import type { TreeNode } from "../lib/itemTree";

  type SettingsTabId =
    | "appearance"
    | "thumbs"
    | "organization"
    | "mess"
    | "video"
    | "performance"
    | "shortcuts"
    | "interface"
    | "debug";

  export let uiShowProcesses = false;
  export let uiShowScanHint = false;
  export let uiShowBuildTag = false;
  export let settingsShowAdvanced = false;

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
  export let galleryCompactIndicesAfterMove = true;
  export let galleryWarmIndexOnStartup = false;
  export let galleryWarmIncludeChildren = true;
  export let galleryWarmMaxDepth = 2;
  export let galleryScanCacheMax = 20;
  export let galleryScanCacheTtlS = 600;
  export let debugLogEnabled = false;
  export let debugLogFilters: import("../lib/galleryDebugLog").GalleryDebugFilters;
  export let videoTranscodePreset: "turbo" | "fast" | "quality" = "fast";
  export let videoTranscodeMaxHeight = 1080;
  export let videoTranscodeHw: "auto" | "off" = "auto";
  export let videoTranscodeMaxJobs = 1;
  export let galleryWarmVideosEnabled = false;
  export let galleryWarmVideosPerFolder = 3;
  export let settingsThumbPresetIdx: number;
  export let settingsThumbScaleDraft: number;
  export let galleryThumbQualityPreset: "balanced" | "sharp" | "hidpi" | "performance" = "balanced";
  export let galleryThumbDiskCacheEnabled = false;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let themeSelection: ThemeSelection;
  export let customThemes: CustomTheme[];
  export let uiFont: UiFontId;
  export let uiBgImagePath: string;
  export let uiBgBlur: number;
  export let uiBgScope: BgScopeId;
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
  export let galleryFolder = "";
  export let recentFolders: string[] = [];
  export let pinnedFolders: string[] = [];
  export let pinnedFolderLabels: Record<string, string> = {};
  export let onBrowseBgFolder: (path: string) => void;

  export let themeNameLabel: (id: UiThemeId) => string;
  export let galleryMasonryTightSpacing = false;
  export let onCancel: () => void;
  export let onSave: () => void;

  let activeTab: SettingsTabId = "appearance";

  const allTabs: { id: SettingsTabId; labelKey: string; advanced?: boolean }[] = [
    { id: "appearance", labelKey: "settings.tabAppearance" },
    { id: "thumbs", labelKey: "settings.tabThumbs" },
    { id: "organization", labelKey: "settings.tabOrganization" },
    { id: "performance", labelKey: "settings.tabPerformance" },
    { id: "video", labelKey: "settings.tabVideo", advanced: true },
    { id: "mess", labelKey: "settings.tabMess", advanced: true },
    { id: "shortcuts", labelKey: "settings.tabShortcuts", advanced: true },
    { id: "interface", labelKey: "settings.tabInterface", advanced: true },
    { id: "debug", labelKey: "settings.tabDebug", advanced: true },
  ];

  $: visibleTabs = settingsShowAdvanced ? allTabs : allTabs.filter((tab) => !tab.advanced);
  $: if (!visibleTabs.some((tab) => tab.id === activeTab)) activeTab = "performance";

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

    <nav class="settings-tabs" role="tablist" aria-label={t("settings.tabsAria")}>
      {#each visibleTabs as tab (tab.id)}
        <button
          type="button"
          role="tab"
          id="settings-tab-{tab.id}"
          class="settings-tabs__btn"
          class:settings-tabs__btn--active={activeTab === tab.id}
          aria-selected={activeTab === tab.id}
          aria-controls="settings-panel-{tab.id}"
          tabindex={activeTab === tab.id ? 0 : -1}
          on:click={() => (activeTab = tab.id)}>{t(tab.labelKey)}</button
        >
      {/each}
    </nav>

    <section
      class="settings-body"
      role="tabpanel"
      id="settings-panel-{activeTab}"
      aria-labelledby="settings-tab-{activeTab}"
    >
      {#if activeTab === "performance"}
        <div class="settings-advanced-bar">
          <label class="check settings-advanced-bar__toggle">
            <input type="checkbox" bind:checked={settingsShowAdvanced} />
            {t("settings.showAdvanced")}
          </label>
          <p class="settings-hint settings-advanced-bar__hint">{t("settings.showAdvancedHint")}</p>
        </div>
        {#if settingsShowAdvanced}
          <SettingsPerformanceSection
            bind:galleryWarmIndexOnStartup
            bind:galleryWarmIncludeChildren
            bind:galleryWarmMaxDepth
            bind:galleryScanCacheMax
            bind:galleryScanCacheTtlS
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
            bind:galleryCompactIndicesAfterMove
          />
        {/if}
      {:else if activeTab === "thumbs"}
        <SettingsThumbsSection
          bind:thumbsPerPage
          bind:settingsThumbPresetIdx
          bind:settingsThumbScaleDraft
          bind:galleryThumbQualityPreset
          bind:galleryThumbDiskCacheEnabled
          bind:thumbGapPx
          bind:thumbImageRadiusPx
          bind:thumbTileRadiusPx
          bind:galleryMasonryTightSpacing
          showAdvanced={settingsShowAdvanced}
        />
      {:else if activeTab === "appearance"}
        <SettingsAppearanceSection
          bind:themeSelection
          bind:customThemes
          bind:uiFont
          bind:uiBgImagePath
          bind:uiBgBlur
          bind:uiBgScope
          {galleryFolder}
          {recentFolders}
          {pinnedFolders}
          {pinnedFolderLabels}
          {onBrowseBgFolder}
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
          bind:videoTranscodeMaxJobs
          bind:galleryWarmVideosEnabled
          bind:galleryWarmVideosPerFolder
          showAdvanced={settingsShowAdvanced}
        />
      {:else if activeTab === "shortcuts"}
        <SettingsShortcutsSection bind:keyboardShortcuts {defaultShortcuts} />
      {:else if activeTab === "mess"}
        <SettingsMessSection
          bind:suggestionsEnabled
          bind:suggestionsMasonry={pinterestMasonry}
          bind:messScanMaxFiles
        />
      {:else if activeTab === "organization"}
        <p class="settings-lead">{t("settings.organizationLead")}</p>
        <SettingsDestinationsSection {destTree} {onDestTreeChange} {onPickDestFolder} />
        <SettingsMarkersSection {markerTree} {onMarkerTreeChange} {onPickMarkerFolder} />
      {:else if activeTab === "interface"}
        <SettingsInterfaceSection
          bind:uiShowProcesses
          bind:uiShowScanHint
          bind:uiShowBuildTag
        />
      {:else if activeTab === "debug"}
        <SettingsDebugSection bind:debugLogEnabled bind:debugLogFilters />
      {/if}
    </section>

    <div class="settings-actions">
      <button type="button" class="om-btn om-btn--ghost" on:click={onCancel}>{t("common.cancel")}</button>
      <button type="button" class="om-btn om-btn--primary" on:click={onSave}>{t("common.save")}</button>
    </div>
  </div>
</div>
