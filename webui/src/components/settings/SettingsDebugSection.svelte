<script lang="ts">
  import { t } from "../../lib/i18n";

  export let debugLogEnabled = false;
</script>

<div class="settings-group settings-group--debug">
  <p class="settings-lead">{t("settings.debugLead")}</p>
  <label class="check">
    <input type="checkbox" bind:checked={debugLogEnabled} />
    {t("settings.debugLogEnabled")}
  </label>
  <p class="settings-hint">{t("settings.debugLogHint")}</p>
  <ul class="settings-debug-list">
    <li>{t("settings.debugLogItemScroll")}</li>
    <li>{t("settings.debugLogItemDrag")}</li>
    <li>{t("settings.debugLogItemRail")}</li>
    <li>{t("settings.debugLogItemLq")}</li>
    <li>{t("settings.debugLogItemHq")}</li>
  </ul>
</div>

<style>
  .settings-debug-list {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.75rem;
    color: var(--om-text-muted);
    line-height: 1.45;
  }
</style>
