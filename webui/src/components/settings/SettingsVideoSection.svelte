<script lang="ts">
  import { onMount } from "svelte";
  import { bridge } from "../../lib/api";
  import { t } from "../../lib/i18n";

  export let videoTranscodePreset: "turbo" | "fast" | "quality" = "fast";
  export let videoTranscodeMaxHeight = 1080;
  export let videoTranscodeHw: "auto" | "off" = "auto";
  export let videoTranscodeMaxJobs = 1;
  export let galleryWarmVideosEnabled = false;
  export let galleryWarmVideosPerFolder = 3;

  type VideoDiag = {
    engine?: string;
    prefersWebm?: boolean;
    qtFreeworld?: boolean;
    ffmpegAvailable?: boolean;
    ffmpegPath?: string | null;
    ffprobeAvailable?: boolean;
    hwEncodersAvailable?: string[];
    webmHwEncodersAvailable?: string[];
    hwEncoderSelected?: string | null;
    transcodeMaxJobs?: number;
    transcodeCacheDir?: string;
    transcodeCacheFiles?: number;
    transcodeCacheBytes?: number;
    activeTranscodeJobs?: number;
    transcodeQueued?: number;
    transcodeRunning?: number;
    transcodeWarmQueued?: number;
    transcodeWorkers?: number;
    hwProbed?: boolean;
    freeworldInstallHint?: string | null;
  };

  let videoDiag: VideoDiag | null = null;
  let videoDiagLoading = false;
  let videoDiagError = "";
  let videoDiagDrainMsg = "";

  function formatBytes(n: number): string {
    if (!Number.isFinite(n) || n < 0) return "—";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
    if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MiB`;
    return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GiB`;
  }

  function joinList(items: string[] | undefined): string {
    if (!items?.length) return t("settings.videoDiagNone");
    return items.join(", ");
  }

  async function refreshVideoDiagnostics() {
    videoDiagLoading = true;
    videoDiagError = "";
    videoDiagDrainMsg = "";
    const timeoutMs = 8_000;
    try {
      videoDiag = await Promise.race([
        bridge.galleryVideoSystemDiagnostics(),
        new Promise<never>((_, reject) => {
          window.setTimeout(() => reject(new Error("timeout")), timeoutMs);
        }),
      ]);
    } catch (err) {
      videoDiag = null;
      videoDiagError =
        err instanceof Error && err.message === "timeout"
          ? t("settings.videoDiagTimeout")
          : err instanceof Error
            ? err.message
            : String(err);
    } finally {
      videoDiagLoading = false;
    }
  }

  async function drainWarmQueue() {
    videoDiagDrainMsg = "";
    try {
      const out = await bridge.galleryTranscodeDrainWarm();
      videoDiagDrainMsg = t("settings.videoDiagDrainWarmOk")
        .replace("{removed}", String(out?.removed ?? 0))
        .replace("{preempted}", String(out?.preempted ?? 0))
        .replace("{workers}", String(out?.workers ?? 0));
      await refreshVideoDiagnostics();
    } catch (err) {
      videoDiagDrainMsg = err instanceof Error ? err.message : String(err);
    }
  }

  onMount(() => {
    void refreshVideoDiagnostics();
  });
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

  <label class="field-label" for="set-video-max-jobs">{t("settings.videoMaxJobsLabel")}</label>
  <select id="set-video-max-jobs" class="om-input" bind:value={videoTranscodeMaxJobs}>
    <option value={1}>1</option>
    <option value={2}>2</option>
    <option value={3}>3</option>
  </select>
  <p class="settings-hint">{t("settings.videoMaxJobsHint")}</p>

  <p class="settings-subtitle">{t("settings.videoWarmTitle")}</p>
  <p class="settings-hint">{t("settings.videoWarmLead")}</p>
  <label class="om-check">
    <input type="checkbox" bind:checked={galleryWarmVideosEnabled} />
    {t("settings.videoWarmEnabled")}
  </label>
  <label class="field-label" for="set-video-warm-n">{t("settings.videoWarmPerFolder")}</label>
  <select
    id="set-video-warm-n"
    class="om-input"
    bind:value={galleryWarmVideosPerFolder}
    disabled={!galleryWarmVideosEnabled}
  >
    <option value={1}>1</option>
    <option value={2}>2</option>
    <option value={3}>3</option>
    <option value={5}>5</option>
    <option value={10}>10</option>
  </select>
  <p class="settings-hint">{t("settings.videoWarmHint")}</p>

  <p class="settings-hint">{t("settings.videoSectionHint")}</p>
  <p class="settings-hint">{t("settings.videoNoTranscodeHint")}</p>

  <div class="settings-subsection">
    <div class="settings-subsection-head">
      <p class="settings-subtitle">{t("settings.videoDiagTitle")}</p>
      <div class="settings-subsection-actions">
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--sm"
          disabled={videoDiagLoading}
          on:click={refreshVideoDiagnostics}
        >
          {videoDiagLoading ? t("settings.videoDiagLoading") : t("settings.videoDiagRefresh")}
        </button>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--sm"
          disabled={videoDiagLoading}
          on:click={drainWarmQueue}
        >
          {t("settings.videoDiagDrainWarm")}
        </button>
      </div>
    </div>
    {#if videoDiagError}
      <p class="settings-hint settings-hint--warn">{videoDiagError}</p>
    {:else if videoDiag}
      <dl class="video-diag-dl">
        <dt>{t("settings.videoDiagEngine")}</dt>
        <dd>{videoDiag.engine ?? "—"}</dd>
        <dt>{t("settings.videoDiagQtFreeworld")}</dt>
        <dd>{videoDiag.qtFreeworld == null ? "—" : videoDiag.qtFreeworld ? t("settings.yes") : t("settings.no")}</dd>
        <dt>{t("settings.videoDiagPrefersWebm")}</dt>
        <dd>{videoDiag.prefersWebm ? t("settings.yes") : t("settings.no")}</dd>
        <dt>ffmpeg</dt>
        <dd>{videoDiag.ffmpegAvailable ? (videoDiag.ffmpegPath ?? t("settings.yes")) : t("settings.no")}</dd>
        <dt>ffprobe</dt>
        <dd>{videoDiag.ffprobeAvailable ? t("settings.yes") : t("settings.no")}</dd>
        <dt>{t("settings.videoDiagHwAvailable")}</dt>
        <dd>{joinList(videoDiag.hwEncodersAvailable)}</dd>
        <dt>{t("settings.videoDiagWebmHw")}</dt>
        <dd>{joinList(videoDiag.webmHwEncodersAvailable)}</dd>
        <dt>{t("settings.videoDiagHwSelected")}</dt>
        <dd>{videoDiag.hwEncoderSelected ?? t("settings.videoDiagCpu")}</dd>
        <dt>{t("settings.videoDiagCache")}</dt>
        <dd>
          {videoDiag.transcodeCacheFiles ?? 0}
          {t("settings.videoDiagFiles")}
          {#if (videoDiag.transcodeCacheBytes ?? -1) >= 0}
            · {formatBytes(videoDiag.transcodeCacheBytes ?? 0)}
          {/if}
        </dd>
        <dt>{t("settings.videoDiagActiveJobs")}</dt>
        <dd>{videoDiag.activeTranscodeJobs ?? 0}</dd>
        <dt>{t("settings.videoDiagQueued")}</dt>
        <dd>{videoDiag.transcodeQueued ?? 0}</dd>
        <dt>{t("settings.videoDiagRunning")}</dt>
        <dd>{videoDiag.transcodeRunning ?? 0}</dd>
        <dt>{t("settings.videoDiagWarmQueued")}</dt>
        <dd>{videoDiag.transcodeWarmQueued ?? 0}</dd>
        <dt>workers</dt>
        <dd>{videoDiag.transcodeWorkers ?? 0}</dd>
      </dl>
      {#if videoDiag.prefersWebm && videoDiag.qtFreeworld === false}
        <p class="settings-hint settings-hint--warn">{t("settings.videoDiagFreeworldHint")}</p>
        <p class="settings-hint settings-hint--mono">
          {videoDiag.freeworldInstallHint ?? t("settings.videoDiagFreeworldCmd")}
        </p>
      {/if}
      {#if (videoDiag.transcodeWorkers ?? 0) <= 0}
        <p class="settings-hint settings-hint--warn">{t("settings.videoDiagWorkersZero")}</p>
      {:else if videoDiag.hwProbed === false}
        <p class="settings-hint">{t("settings.videoDiagHwPending")}</p>
      {/if}
      {#if videoDiagDrainMsg}
        <p class="settings-hint">{videoDiagDrainMsg}</p>
      {/if}
      {#if videoDiag.transcodeCacheDir}
        <p class="settings-hint settings-hint--mono">{videoDiag.transcodeCacheDir}</p>
      {/if}
    {:else if !videoDiagLoading}
      <p class="settings-hint">{t("settings.videoDiagEmpty")}</p>
    {/if}
  </div>
</div>

<style>
  .settings-subsection {
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--om-border-subtle, rgba(128, 128, 128, 0.25));
  }
  .settings-subsection-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }
  .settings-subsection-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .video-diag-dl {
    display: grid;
    grid-template-columns: minmax(8rem, 38%) 1fr;
    gap: 0.35rem 0.75rem;
    margin: 0;
    font-size: 0.9rem;
  }
  .video-diag-dl dt {
    margin: 0;
    opacity: 0.75;
  }
  .video-diag-dl dd {
    margin: 0;
    word-break: break-word;
  }
  .settings-hint--mono {
    font-family: ui-monospace, monospace;
    font-size: 0.8rem;
  }
  .settings-hint--warn {
    color: var(--om-danger, #c44);
  }
</style>
