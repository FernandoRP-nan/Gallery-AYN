<script lang="ts">
  import { t } from "../../lib/i18n";

  export let suggestionsEnabled = false;
  export let suggestionsMasonry = true;
  export let messScanMaxFiles = 400;
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.messLead")}</p>
  <p class="settings-hint">{t("settings.messHint")}</p>

  <label class="check settings-check">
    <input type="checkbox" bind:checked={suggestionsEnabled} />
    {t("settings.messSuggestionsEnabled")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.messSuggestionsEnabledHint")}</p>

  <label class="check settings-check">
    <input type="checkbox" bind:checked={suggestionsMasonry} />
    {t("settings.messMasonry")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.messMasonryHint")}</p>

  <label class="field-label" for="set-mess-max-files">{t("settings.messMaxFilesLabel")}</label>
  <input
    id="set-mess-max-files"
    class="om-input"
    type="number"
    min="50"
    max="2000"
    step="50"
    bind:value={messScanMaxFiles}
  />
  <p class="settings-hint">{t("settings.messMaxFilesHint")}</p>
</div>

<style>
  .settings-check {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    margin-top: var(--om-space-2);
  }

  .settings-hint--indent {
    margin-left: 1.5rem;
    margin-top: 0.25rem;
  }
</style>
