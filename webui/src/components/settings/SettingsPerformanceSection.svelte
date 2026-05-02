<script lang="ts">
  import { t } from "../../lib/i18n";

  export let thumbsPerPage: number;
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionPerformance")}</h3>
  <label class="field-label" for="set-thumbs-page">{t("settings.thumbsPerPageLabel")}</label>
  <input
    id="set-thumbs-page"
    class="om-input"
    type="number"
    min="0"
    placeholder={t("settings.thumbsPerPagePlaceholder")}
    bind:value={thumbsPerPage}
  />
  <div class="settings-preset-row">
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 24)}
      >{t("settings.presetHighPerf24")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 48)}
      >{t("settings.presetPerf48")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 96)}
      >{t("settings.presetBalanced96")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 0)}
      >{t("settings.presetUnlimited0")}</button
    >
  </div>
  {#if Number(thumbsPerPage) === 0}
    <p class="settings-hint settings-hint--warn">{t("settings.unlimitedWarn")}</p>
  {/if}
  <p class="settings-hint">{t("settings.perfHint")}</p>
</div>
