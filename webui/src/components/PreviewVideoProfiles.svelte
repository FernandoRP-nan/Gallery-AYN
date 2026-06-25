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

  const dispatch = createEventDispatcher<{ change: string }>();

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

{#if profiles.length > 0}
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
  </div>
{/if}
