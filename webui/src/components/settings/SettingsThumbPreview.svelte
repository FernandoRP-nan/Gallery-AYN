<script lang="ts">
  import { t } from "../../lib/i18n";

  export let previewCellPx: number;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let showThumbLabels: boolean;
  export let thumbFrameVisible: boolean;
  export let thumbCardStyle: "soft" | "flat" | "outlined";
</script>

<div
  class="settings-thumb-preview"
  class:settings-thumb-preview--no-frame={!thumbFrameVisible}
  class:settings-thumb-preview--flat={thumbCardStyle === "flat"}
  class:settings-thumb-preview--outlined={thumbCardStyle === "outlined"}
  style={`--cell:${previewCellPx}px;--thumb-gap:${thumbGapPx}px;--thumb-image-radius:${thumbImageRadiusPx}px;--thumb-tile-radius:${thumbTileRadiusPx}px`}
>
  <div class="set-tile">
    <div class="set-folder-ph">A</div>{#if showThumbLabels}<span class="set-tile__name">{t("settings.previewSample1")}</span>{/if}
  </div>
  <div class="set-tile">
    <div class="set-folder-ph">B</div>{#if showThumbLabels}<span class="set-tile__name">{t("settings.previewSample2")}</span>{/if}
  </div>
  <div class="set-tile">
    <div class="set-folder-ph">C</div>{#if showThumbLabels}<span class="set-tile__name">{t("settings.previewSample3")}</span>{/if}
  </div>
</div>
