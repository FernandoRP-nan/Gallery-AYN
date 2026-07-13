<script lang="ts">
  import { t } from "../../lib/i18n";

  export let uiShowProcesses = false;
  export let uiShowScanHint = false;
  export let uiShowBuildTag = false;
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.interfaceLead")}</p>

  <label class="check settings-check">
    <input type="checkbox" bind:checked={uiShowProcesses} />
    {t("settings.uiShowProcesses")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.uiShowProcessesHint")}</p>

  <label class="check settings-check">
    <input type="checkbox" bind:checked={uiShowScanHint} />
    {t("settings.uiShowScanHint")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.uiShowScanHintHint")}</p>

  <label class="check settings-check">
    <input type="checkbox" bind:checked={uiShowBuildTag} />
    {t("settings.uiShowBuildTag")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.uiShowBuildTagHint")}</p>
</div>

<style>
  .settings-check {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    margin-top: var(--om-space-1);
    cursor: pointer;
  }

  .settings-hint--indent {
    margin-left: 1.5rem;
    margin-top: 0.2rem;
  }
</style>
