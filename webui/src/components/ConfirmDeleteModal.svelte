<script lang="ts">
  import { t } from "../lib/i18n";

  /** Título del diálogo */
  export let title: string;
  /** Texto descriptivo */
  export let detail: string;
  /** Etiqueta del botón de acción principal */
  export let confirmLabel: string;
  export let bypassEnabled = false;
  export let bypassLabel = "";
  /** Enlace bidireccional con el estado del checkbox en el padre */
  export let bypassChecked = false;

  export let onClose: () => void;
  export let onConfirm: () => void | Promise<void>;
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<div class="cdb-backdrop" role="presentation" on:click|self={onClose}>
  <div
    class="modal modal--confirm om-panel om-panel--lift cdb-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="confirm-delete-title"
    tabindex="-1"
    on:click|stopPropagation={() => undefined}
    on:keydown={(e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        void onConfirm();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }}
  >
    <header class="modal__head">
      <strong id="confirm-delete-title">{title}</strong>
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--close"
        aria-label={t("common.closeModalAria")}
        title={t("common.close")}
        on:click={onClose}>✕</button
      >
    </header>
    <p class="settings-hint">{detail}</p>
    {#if bypassEnabled}
      <label class="check">
        <input type="checkbox" bind:checked={bypassChecked} />
        {bypassLabel}
      </label>
    {/if}
    <div class="settings-actions">
      <button type="button" class="om-btn om-btn--ghost" on:click={onClose}>{t("common.cancel")}</button>
      <button type="button" class="om-btn om-btn--primary" on:click={() => void onConfirm()}>{confirmLabel}</button>
    </div>
  </div>
</div>

<style>
  /* om-btn / om-panel vienen del CSS global cargado por App.svelte */

  /* Réplica acotada de .overlay / .modal--confirm del shell para que el modal siga igual fuera de App.svelte */
  .cdb-backdrop {
    position: fixed;
    inset: 0;
    background: rgb(4 6 14 / 0.72);
    display: grid;
    place-items: center;
    z-index: 140;
  }

  .cdb-dialog.modal {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    gap: var(--om-space-3);
    padding: var(--om-space-5);
    z-index: 141;
    box-sizing: border-box;
    width: min(520px, 92vw);
    max-height: min(72vh, 340px);
  }

  .modal__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--om-space-3);
  }

  .settings-hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--om-text-muted);
    line-height: 1.4;
  }

  .settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--om-space-2);
    flex-wrap: wrap;
  }

  .check {
    font-size: 0.875rem;
    color: var(--om-text-secondary);
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }

  .om-btn--close {
    min-width: 2rem;
    padding-inline: 0.45rem;
    font-size: 1rem;
    line-height: 1;
  }
</style>
