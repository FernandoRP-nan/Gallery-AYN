<script lang="ts">
  import { t } from "../../lib/i18n";
  import type { TreeNode } from "../../lib/itemTree";
  import SettingsTreeManager from "./SettingsTreeManager.svelte";

  export let destTree: TreeNode[];
  export let onDestTreeChange: (next: TreeNode[]) => void;
  export let onPickDestFolder: () => Promise<string | null>;
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionDestinations")}</h3>
  <p class="settings-hint">{t("settings.destinationsHint")}</p>
  <SettingsTreeManager
    tree={destTree}
    leafKind="dest"
    onTreeChange={onDestTreeChange}
    onPickFolder={onPickDestFolder}
  />
</div>
