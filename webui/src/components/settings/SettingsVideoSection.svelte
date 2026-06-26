<script lang="ts">
  import { t } from "../../lib/i18n";

  export let videoTranscodePreset: "turbo" | "fast" | "quality" = "fast";
  export let videoTranscodeMaxHeight = 1080;
  export let videoTranscodeHw: "auto" | "off" = "auto";
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.videoLead")}</p>
  <label class="field-label" for="set-video-preset">{t("settings.videoPresetLabel")}</label>
  <select id="set-video-preset" class="om-input" bind:value={videoTranscodePreset}>
    <option value="turbo">{t("settings.videoPresetTurbo")}</option>
    <option value="fast">{t("settings.videoPresetFast")}</option>
    <option value="quality">{t("settings.videoPresetQuality")}</option>
  </select>
  <p class="settings-hint">{t("settings.videoPresetHint")}</p>

  <label class="field-label" for="set-video-max-h">{t("settings.videoMaxHeightLabel")}</label>
  <select id="set-video-max-h" class="om-input" bind:value={videoTranscodeMaxHeight}>
    <option value={720}>720p</option>
    <option value={1080}>1080p</option>
    <option value={1440}>1440p</option>
    <option value={2160}>2160p</option>
    <option value={0}>{t("settings.videoMaxHeightNative")}</option>
  </select>

  <label class="field-label" for="set-video-hw">{t("settings.videoHwLabel")}</label>
  <select id="set-video-hw" class="om-input" bind:value={videoTranscodeHw}>
    <option value="auto">{t("settings.videoHwAuto")}</option>
    <option value="off">{t("settings.videoHwOff")}</option>
  </select>
  <p class="settings-hint">{t("settings.videoSectionHint")}</p>
  <p class="settings-hint">{t("settings.videoNoTranscodeHint")}</p>
</div>
