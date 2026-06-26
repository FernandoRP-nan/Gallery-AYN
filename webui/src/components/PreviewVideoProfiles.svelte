<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { t } from "../lib/i18n";

  export type VideoProfile = {
    id: string;
    available: boolean;
    recommended?: boolean;
    strategy?: string;
    needsTranscode?: boolean;
  };

  export let profiles: VideoProfile[] = [];
  export let activeMode = "auto";
  export let disabled = false;
  export let autoplayEnabled = false;
  export let autoplayEditMode = false;
  export let autoplayDisabled = false;

  const dispatch = createEventDispatcher<{ change: string; autoplayToggle: void }>();

  function labelFor(id: string): string {
    const mapped: Record<string, string> = {
      auto: t("preview.videoModeAuto"),
      direct: t("preview.videoModeDirect"),
      remux: t("preview.videoModeRemux"),
      turbo: t("preview.videoModeTurbo"),
      fast: t("preview.videoModeFast"),
      quality: t("preview.videoModeQuality"),
    };
    return mapped[id] ?? id;
  }

  function hintFor(p: VideoProfile): string {
    if (!p.available) return t("preview.videoModeUnavailable");
    if (p.recommended) return t("preview.videoModeRecommended");
    return "";
  }
</script>

<div class="preview__video-profiles" role="toolbar" aria-label={t("preview.videoProfilesLabel")}>
  {#each profiles as profile (profile.id)}
    <button
      type="button"
      class="preview__video-profile"
      class:preview__video-profile--active={activeMode === profile.id}
      class:preview__video-profile--disabled={!profile.available}
      disabled={disabled || !profile.available}
      title={hintFor(profile)}
      on:click={() => dispatch("change", profile.id)}
    >
      {labelFor(profile.id)}
    </button>
  {/each}

  <button
    type="button"
    class="preview__video-profile preview__video-profile--autoplay"
    class:preview__video-profile--active={autoplayEnabled}
    class:preview__video-profile--edit={autoplayEditMode}
    disabled={autoplayDisabled || disabled}
    title={autoplayEnabled ? t("preview.videoAutoplayOnHint") : t("preview.videoAutoplayOffHint")}
    aria-label={autoplayEnabled ? t("preview.videoAutoplayOnHint") : t("preview.videoAutoplayOffHint")}
    aria-pressed={autoplayEnabled}
    on:click={() => dispatch("autoplayToggle")}
  >
    <svg class="preview__video-autoplay-icon" viewBox="0 0 24 24" aria-hidden="true">
      {#if autoplayEnabled}
        <circle cx="12" cy="12" r="8.25" fill="none" stroke="currentColor" stroke-width="1.65" />
        <path d="M10.25 9.25v5.5l4.25-2.75-4.25-2.75z" fill="currentColor" />
      {:else}
        <path d="M8.75 7.25v9.5l7.25-4.75-7.25-4.75z" fill="currentColor" />
      {/if}
    </svg>
  </button>
</div>
