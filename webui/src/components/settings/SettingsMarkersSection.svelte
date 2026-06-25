<script lang="ts">
  import { t } from "../../lib/i18n";
  import type { TreeNode } from "../../lib/itemTree";
  import SettingsTreeManager from "./SettingsTreeManager.svelte";

  export let markerTree: TreeNode[];
  export let onMarkerTreeChange: (next: TreeNode[]) => void;
  export let onPickMarkerFolder: () => Promise<string | null>;
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionMarkers")}</h3>
  <p class="settings-hint">{t("settings.markersHint")}</p>
  <SettingsTreeManager
    tree={markerTree}
    leafKind="marker"
    onTreeChange={onMarkerTreeChange}
    onPickFolder={onPickMarkerFolder}
  />
</div>
