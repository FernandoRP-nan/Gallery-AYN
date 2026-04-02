<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  let pollTimer: number | null = null;
  import { bridge, type GalleryItem } from "./lib/api";
  import { galleryGridCellPx, destPreviewGridMinPx } from "./lib/thumbScale";

  const BLANK_DRAG_IMG =
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  let folder = "";
  let state: any = { page: 1, totalPages: 1, total: 0, selectedCount: 0 };
  let items: GalleryItem[] = [];
  let destinations: Array<{ label: string; path: string }> = [];
  let selectedPreview: { path: string; name: string; dataUrl: string | null } | null = null;
  let status = "Listo";
  let thumbScale = 1;
  let previewOpen = false;
  let previewItems: Array<{ name: string; path: string; thumbDataUrl?: string | null }> = [];
  let previewScale = 1;
  let previewDestPath = "";
  let activeTab: "ruta" | "destinos" | "organizar" = "ruta";
  /** Panel organizador en ventana flotante (tarea por lotes). */
  let orgPanelOpen = false;
  let settingsOpen = false;
  let thumbsPerPage = 48;
  let thumbsPerPageBackup = 48;
  let pageJumpDraft = 1;
  let previewRatio = 0.4;
  /** Modal “ver carpeta destino”: ~80 % del viewport (sin sliders). */
  const DEST_MODAL_FRAC = 0.8;
  let orgPath = "";
  let orgRunning = false;
  let orgDetail = "Sin tarea";
  let orgProgress = "0/0";
  let orgOptions = {
    includeOrganized: false,
    includeComics: false,
    includePending: false,
    removeDuplicates: false,
    groupSimilarImages: false
  };

  /** Rutas recientes (persistidas en settings) para acceso rápido si el campo está vacío. */
  let recentFolders: string[] = [];

  let ghostVisible = false;
  let ghostX = 0;
  let ghostY = 0;
  let ghostThumb: string | null = null;
  let ghostCount = 1;
  let ghostCaption = "";
  /** Listeners en window (captura): Qt WebEngine a veces no dispara dragover en document). */
  let dragWinMove: ((ev: DragEvent) => void) | null = null;
  let dragWinEnd: (() => void) | null = null;

  let splitDrag = false;
  /** Contador para overlay de carga (carpetas, API, etc.). */
  let loadCount = 0;
  $: uiLoading = loadCount > 0;

  function trackLoad<T>(promise: Promise<T>): Promise<T> {
    loadCount++;
    return promise.finally(() => {
      loadCount--;
    });
  }

  /** Evita clics encolados mientras corre una operación de galería (Qt WebEngine + Python). */
  let galleryActionBusy = false;
  let thumbScaleDebounce: ReturnType<typeof setTimeout> | null = null;
  let destScaleDebounce: ReturnType<typeof setTimeout> | null = null;

  const isDevMock = () =>
    typeof import.meta !== "undefined" && Boolean((import.meta as any).env?.DEV) && !window.pywebview?.api;

  /** Qt/WebEngine inyecta la API un poco después del load; evita error get_initial_state. */
  async function waitForPywebviewApi(): Promise<void> {
    if (isDevMock()) return;
    const hasApi = () =>
      Boolean(
        (window as any).pywebview?.api &&
          typeof (window as any).pywebview.api.get_initial_state === "function"
      );
    if (hasApi()) return;
    await new Promise<void>((resolve, reject) => {
      const t0 = Date.now();
      const tryResolve = () => {
        if (hasApi()) {
          clearInterval(iv);
          window.removeEventListener("pywebviewready", onReady);
          resolve();
        } else if (Date.now() - t0 > 25000) {
          clearInterval(iv);
          window.removeEventListener("pywebviewready", onReady);
          reject(new Error("pywebview API no disponible a tiempo"));
        }
      };
      const onReady = () => tryResolve();
      window.addEventListener("pywebviewready", onReady);
      const iv = setInterval(tryResolve, 50);
    });
  }

  const loadInitial = async () => {
    const data = await trackLoad(bridge.getInitialState());
    destinations = data.destinations ?? [];
    thumbScale = Number(data.settings?.gallery_thumb_scale ?? 1);
    previewScale = Number(data.settings?.dest_preview_thumb_scale ?? 1);
    previewRatio = Math.min(0.68, Math.max(0.14, Number(data.settings?.web_preview_ratio ?? 0.4)));
    const last = (data.settings?.gallery_last_folder ?? "").trim();
    folder = (data.gallery?.folder ?? last) || "";
    orgPath = folder || orgPath;
    state = data.gallery ?? state;
    recentFolders = Array.isArray(data.settings?.gallery_recent_folders)
      ? (data.settings.gallery_recent_folders as string[])
      : [];
    thumbsPerPage = Math.min(120, Math.max(12, Number(data.settings?.gallery_thumbs_per_page ?? 48)));
    pageJumpDraft = Number(data.gallery?.page ?? 1);
  };

  const loadFolder = async () => {
    const out = await trackLoad(bridge.galleryLoadFolder(folder));
    state = out.state;
    items = out.items;
    if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
    pageJumpDraft = out.state.page;
    status = `Cargada carpeta: ${folder}`;
  };

  const pickRecentFolder = async (path: string) => {
    folder = path;
    await loadFolder();
  };

  const pickGalleryFolder = async () => {
    try {
      const out = await bridge.dialogPickFolder(folder);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      folder = out.path;
      await loadFolder();
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo abrir el selector de carpeta";
    }
  };

  const pickOrgFolder = async () => {
    try {
      const out = await bridge.dialogPickFolder(orgPath);
      if (out.hint) status = String(out.hint);
      if (out.cancelled || !out.path) return;
      orgPath = out.path;
      status = `Ruta organizador: ${orgPath}`;
    } catch (e: unknown) {
      status = e instanceof Error ? e.message : "No se pudo abrir el selector de carpeta";
    }
  };

  /** Recarga ítems de la galería. `silent`: no muestra overlay (p. ej. tras mover el slider de miniaturas). */
  const reload = async (opts?: { silent?: boolean }) => {
    const p = bridge.galleryReload();
    const out = opts?.silent ? await p : await trackLoad(p);
    state = out.state;
    items = out.items;
  };

  const goPage = async (page: number) => {
    const out = await trackLoad(bridge.galleryGoPage(page));
    state = out.state;
    items = out.items;
    pageJumpDraft = out.state.page;
  };

  const jumpToPageDraft = async () => {
    const n = Math.min(state.totalPages, Math.max(1, Math.round(Number(pageJumpDraft)) || 1));
    pageJumpDraft = n;
    await goPage(n);
  };

  const openSettingsModal = () => {
    thumbsPerPageBackup = thumbsPerPage;
    settingsOpen = true;
  };

  const cancelSettingsModal = () => {
    thumbsPerPage = thumbsPerPageBackup;
    settingsOpen = false;
  };

  const saveSettingsModal = async () => {
    const n = Math.min(120, Math.max(12, Math.round(Number(thumbsPerPage)) || 48));
    thumbsPerPage = n;
    await bridge.settingsPatch({ gallery_thumbs_per_page: n });
    await reload();
    settingsOpen = false;
  };

  const clickItem = async (it: GalleryItem) => {
    if (galleryActionBusy) return;
    galleryActionBusy = true;
    try {
      if (it.kind === "folder" || it.kind === "folder_up") {
        const out = await trackLoad(bridge.galleryOpenFolderTile(it.path));
        state = out.state;
        items = out.items;
        folder = state.folder;
        if (Array.isArray(out.recentFolders)) recentFolders = out.recentFolders;
        pageJumpDraft = out.state.page;
        return;
      }
      if (activeTab === "destinos") {
        const out = await bridge.galleryToggleSelect(it.path);
        state = out.state;
        items = out.items;
        const row = out.items?.find((x: GalleryItem) => x.path === it.path);
        selectedPreview = {
          path: it.path,
          name: it.name,
          dataUrl: row?.thumbDataUrl ?? null
        };
        const pathRef = it.path;
        requestAnimationFrame(() => {
          bridge
            .galleryPreview(pathRef, 1200, 900)
            .then((pr) => {
              selectedPreview = pr;
            })
            .catch(() => undefined);
        });
      } else {
        selectedPreview = {
          path: it.path,
          name: it.name,
          dataUrl: it.thumbDataUrl ?? null
        };
        const pathRef = it.path;
        requestAnimationFrame(() => {
          bridge
            .galleryPreview(pathRef, 1200, 900)
            .then((pr) => {
              selectedPreview = pr;
            })
            .catch(() => undefined);
        });
      }
    } finally {
      galleryActionBusy = false;
    }
  };

  const selectPage = async () => {
    const out = await bridge.gallerySelectPage();
    state = out.state;
    items = out.items;
  };
  const clearSelection = async () => {
    const out = await bridge.galleryClearSelection();
    state = out.state;
    items = out.items;
  };
  const invertSelection = async () => {
    const out = await bridge.galleryInvertSelection();
    state = out.state;
    items = out.items;
  };

  const moveToDest = async (path: string) => {
    const out = await trackLoad(bridge.destinationMoveSelected(path));
    state = out.state;
    items = out.items;
    status = `Movidas ${out.moveResult?.moved ?? 0} · errores ${out.moveResult?.errors ?? 0}`;
  };

  const savePreviewRatio = async () => {
    await bridge.settingsPatch({ web_preview_ratio: Number(previewRatio.toFixed(3)) });
  };

  function updateSplitFromClientX(clientX: number) {
    const el = document.querySelector(".content");
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const w = rect.width;
    if (w <= 1) return;
    let r = (rect.right - clientX) / w;
    r = Math.min(0.68, Math.max(0.14, r));
    previewRatio = Math.round(r * 1000) / 1000;
  }

  function beginSplitDrag(e: PointerEvent) {
    e.preventDefault();
    splitDrag = true;
    const move = (ev: PointerEvent) => {
      if (!splitDrag) return;
      updateSplitFromClientX(ev.clientX);
    };
    const up = () => {
      splitDrag = false;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      savePreviewRatio().catch(() => undefined);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  }

  function scheduleThumbScaleReload() {
    if (thumbScaleDebounce) clearTimeout(thumbScaleDebounce);
    thumbScaleDebounce = setTimeout(() => {
      thumbScaleDebounce = null;
      applyThumbScaleNow();
    }, 160);
  }

  async function applyThumbScaleNow() {
    try {
      await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
      await reload({ silent: true });
    } catch {
      status = "No se pudo aplicar el tamaño de miniaturas";
    }
  }

  function flushThumbScaleOnRelease() {
    if (thumbScaleDebounce) {
      clearTimeout(thumbScaleDebounce);
      thumbScaleDebounce = null;
    }
    applyThumbScaleNow();
  }

  const openDestPreview = async (path: string) => {
    previewDestPath = path;
    previewOpen = true;
    await refreshDestPreview();
  };

  const refreshDestPreview = async () => {
    const w = Math.max(320, Math.round(window.innerWidth * DEST_MODAL_FRAC));
    const out = await bridge.destinationPreview(previewDestPath, previewScale, w);
    previewItems = out.items;
  };

  /** Ancho mínimo de pista en el modal destino: auto-fill sin columna cortada ni scroll horizontal. */
  $: destModalGridMinPx = destPreviewGridMinPx(previewScale);

  const saveThumbScale = async () => {
    await bridge.settingsPatch({ gallery_thumb_scale: Number(thumbScale.toFixed(3)) });
    await reload({ silent: true });
  };

  const saveDestScale = async () => {
    await bridge.settingsPatch({ dest_preview_thumb_scale: Number(previewScale.toFixed(3)) });
    await refreshDestPreview();
  };

  function scheduleDestScaleSave() {
    if (destScaleDebounce) clearTimeout(destScaleDebounce);
    destScaleDebounce = setTimeout(() => {
      destScaleDebounce = null;
      saveDestScale().catch(() => undefined);
    }, 280);
  }

  const startOrganizer = async () => {
    const out = await bridge.organizerStart(orgPath, orgOptions);
    if (!out.ok) {
      status = out.error ?? "No se pudo iniciar";
      return;
    }
    orgRunning = true;
    status = "Organizador iniciado";
  };

  const cancelOrganizer = async () => {
    await bridge.organizerCancel();
  };

  const pollOrganizer = async () => {
    const out = await bridge.organizerStatus();
    orgRunning = Boolean(out.running);
    orgDetail = out.progress?.detail ?? "Sin tarea";
    orgProgress = `${out.progress?.current ?? 0}/${out.progress?.total ?? 0}`;
    if (!orgRunning && out.done) {
      const stats = out.done.stats ?? {};
      status = out.done.error
        ? `Error: ${out.done.error}`
        : `Finalizado · movidas ${stats.moved_media ?? 0}, cbz ${stats.moved_cbz ?? 0}, otros ${stats.moved_other ?? 0}`;
    }
  };

  function clearGhostListeners() {
    if (dragWinMove) {
      window.removeEventListener("dragover", dragWinMove, true);
      dragWinMove = null;
    }
    if (dragWinEnd) {
      window.removeEventListener("dragend", dragWinEnd, true);
      dragWinEnd = null;
    }
  }

  function onTileDragStart(e: DragEvent, it: GalleryItem) {
    if (activeTab !== "destinos" || it.kind !== "image") return;
    clearGhostListeners();
    const dt = e.dataTransfer;
    if (dt) {
      dt.setData("text/plain", it.path);
      dt.effectAllowed = "move";
      const im = new Image();
      im.src = BLANK_DRAG_IMG;
      dt.setDragImage(im, 0, 0);
    }
    ghostCount = Math.max(1, Number(state.selectedCount) || 1);
    ghostThumb = it.thumbDataUrl ?? null;
    ghostCaption = ghostCount > 1 ? `${ghostCount} seleccionadas` : it.name;
    ghostVisible = true;
    ghostX = e.clientX;
    ghostY = e.clientY;

    dragWinMove = (ev: DragEvent) => {
      ev.preventDefault();
      if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
      ghostX = ev.clientX;
      ghostY = ev.clientY;
    };
    dragWinEnd = () => {
      ghostVisible = false;
      clearGhostListeners();
    };
    window.addEventListener("dragover", dragWinMove, true);
    window.addEventListener("dragend", dragWinEnd, true);
  }

  /** Celdas de ancho fijo (sin 1fr) para que cada paso del slider se note al cambiar columnas. */
  $: gridCellPx = galleryGridCellPx(thumbScale);

  onMount(async () => {
    try {
      await waitForPywebviewApi();
    } catch {
      status = "API de escritorio no disponible. Reabre la app o usa npm run dev.";
      return;
    }
    await loadInitial();
    if (folder) {
      try {
        await loadFolder();
      } catch {
        status = "No se pudo restaurar la última carpeta; revisa la ruta o pulsa Cargar.";
      }
    }
    pollTimer = window.setInterval(() => {
      pollOrganizer().catch(() => undefined);
    }, 1100);
  });

  onDestroy(() => {
    clearGhostListeners();
    if (thumbScaleDebounce) clearTimeout(thumbScaleDebounce);
    if (destScaleDebounce) clearTimeout(destScaleDebounce);
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  });
</script>

<svelte:window
  on:keydown={(e) => {
    if (e.key !== "Escape") return;
    if (settingsOpen) settingsOpen = false;
    else if (previewOpen) previewOpen = false;
    else if (orgPanelOpen) orgPanelOpen = false;
  }}
/>

<main class="app" class:app--extra-row={activeTab === "destinos" || activeTab === "organizar"}>
  <header class="tabs-bar om-panel">
    <nav class="tabs__nav">
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "ruta"} on:click={() => (activeTab = "ruta")}>Ruta</button>
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "destinos"} on:click={() => (activeTab = "destinos")}>Destinos</button>
      <button type="button" class="om-btn om-btn--tab" class:om-btn--active={activeTab === "organizar"} on:click={() => (activeTab = "organizar")}>Organizar</button>
    </nav>
    <div class="grow"></div>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--icon"
      title="Ajustes"
      aria-label="Ajustes"
      on:click={openSettingsModal}>⚙</button>
  </header>

  <section class="route om-panel">
    <div class="route__row">
      <input
        id="gallery-folder-input"
        class="om-input route__path"
        type="text"
        bind:value={folder}
        placeholder="Ruta de carpeta…"
        title="Pega la ruta o pulsa Examinar (app de escritorio)"
      />
      <button type="button" class="om-btn om-btn--primary" title="Explorador del sistema" on:click={pickGalleryFolder}>Examinar…</button>
      <button type="button" class="om-btn om-btn--ghost om-btn--icon" title="Recargar galería" on:click={reload}>↻</button>
      <button type="button" class="om-btn om-btn--primary" on:click={loadFolder}>Cargar</button>
      <div class="grow"></div>
      <span
        class="field-label"
        title="Arrastra la barra entre galería y vista previa para el ancho del panel"
        >Panel derecho ~{Math.round(previewRatio * 100)}%</span>
      <label class="field-label" for="route-thumb-scale">Miniaturas {Math.round(thumbScale * 100)}%</label>
      <input
        id="route-thumb-scale"
        class="om-range"
        type="range"
        min="0.75"
        max="2.25"
        step="0.01"
        bind:value={thumbScale}
        on:input={scheduleThumbScaleReload}
        on:change={flushThumbScaleOnRelease}
      />
    </div>
    {#if !folder.trim() && recentFolders.length > 0}
      <div class="recent-folders" aria-label="Rutas recientes">
        <div class="recent-folders__head">
          <span class="field-label">Rutas recientes</span>
          <span class="recent-folders__hint">Pulsa para cargar</span>
        </div>
        <div class="recent-folders__list">
          {#each recentFolders as p}
            <button type="button" class="om-btn om-btn--ghost recent-folders__chip" title={p} on:click={() => pickRecentFolder(p)}>
              {p.length > 56 ? `${p.slice(0, 53)}…` : p}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </section>

  {#if activeTab === "destinos"}
    <section class="om-panel actions">
      <button type="button" class="om-btn om-btn--ghost" on:click={selectPage}>Seleccionar página</button>
      <button type="button" class="om-btn om-btn--ghost" on:click={clearSelection}>Quitar selección</button>
      <button type="button" class="om-btn om-btn--ghost" on:click={invertSelection}>Invertir</button>
      <span class="pill">{state.selectedCount} seleccionadas</span>
    </section>
    <section class="dest-panel om-panel" aria-label="Carpetas destino">
      <span class="field-label dest-panel__title">Carpetas destino</span>
      <div class="dest-grid-wrap dest-grid-wrap--embedded">
        {#each destinations as d}
          <div
            class="dest-card"
            role="group"
            aria-label="Destino {d.label}"
            on:dragover|preventDefault
            on:drop|preventDefault={() => moveToDest(d.path)}
          >
            <div class="dest-card__head">
              <span class="dest-card__title">{d.label}</span>
              <span class="dest-card__path">{d.path}</span>
            </div>
            <div class="dest-card__actions">
              <button type="button" class="om-btn om-btn--primary" on:click={() => moveToDest(d.path)}>Mover aquí</button>
              <button type="button" class="om-btn om-btn--ghost" on:click={() => openDestPreview(d.path)}>Ver carpeta</button>
            </div>
          </div>
        {/each}
      </div>
    </section>
  {:else if activeTab === "organizar"}
    <section class="om-panel org-tab-bar">
      <p class="org-tab-bar__text">Organización por lotes (comics, duplicados, etc.) en una ventana aparte.</p>
      <button type="button" class="om-btn om-btn--primary" on:click={() => (orgPanelOpen = true)}>Abrir panel de organización…</button>
    </section>
  {/if}

  <section
    class="content"
    style={`grid-template-columns:minmax(0,${(1 - previewRatio).toFixed(4)}fr) 10px minmax(0,${previewRatio.toFixed(4)}fr)`}
  >
    <article class="gallery om-panel om-panel--lift">
      <div class="grid" style={`--cell:${gridCellPx}px`}>
        {#each items as it (it.path)}
          <button
            type="button"
            class="tile"
            class:selected={it.selected && activeTab === "destinos"}
            draggable={activeTab === "destinos" && it.kind === "image"}
            on:dragstart={(e) => onTileDragStart(e, it)}
            on:click={() => clickItem(it)}
          >
            {#if it.thumbDataUrl}
              <img src={it.thumbDataUrl} alt="" loading="lazy" decoding="async" />
            {:else}
              <div class="folder-ph">{it.kind === "image" ? "Sin preview" : "📁"}</div>
            {/if}
            <span class="tile__name">{it.name}</span>
          </button>
        {/each}
      </div>
    </article>

    <div
      class="splitter"
      role="separator"
      aria-orientation="vertical"
      aria-label="Arrastrar para repartir galería y vista previa"
      on:pointerdown={beginSplitDrag}
    ></div>

    <aside class="preview om-panel">
      {#if selectedPreview?.dataUrl}
        <img class="preview__img" src={selectedPreview.dataUrl} alt={selectedPreview.name} />
      {:else}
        <div class="preview__empty">Selecciona una miniatura</div>
      {/if}
      <div class="preview__meta">{selectedPreview?.path ?? ""}</div>
    </aside>
  </section>

  <footer class="pager om-panel">
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" on:click={() => goPage(1)}>|«</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" on:click={() => goPage(Math.max(1, state.page - 1))}>‹</button>
    <span class="pager__info">{state.total} imágenes · página</span>
    <label class="pager__jump">
      <input
        class="om-input pager__jump-input"
        type="number"
        min="1"
        max={state.totalPages}
        bind:value={pageJumpDraft}
        on:keydown={(e) => e.key === "Enter" && jumpToPageDraft()}
      />
      <span class="pager__jump-total">/ {state.totalPages}</span>
    </label>
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" on:click={() => goPage(Math.min(state.totalPages, state.page + 1))}>›</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" on:click={() => goPage(state.totalPages)}>»|</button>
    <button type="button" class="om-btn om-btn--primary om-btn--compact" on:click={jumpToPageDraft}>Ir</button>
    <div class="grow"></div>
    <span class="status-line">{status}</span>
  </footer>

  {#if previewOpen}
    <div
      class="overlay"
      role="button"
      tabindex="-1"
      aria-label="Cerrar vista previa del destino"
      on:click={() => (previewOpen = false)}
      on:keydown={(e) => {
        if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          previewOpen = false;
        }
      }}
    >
      <div
        class="modal modal--dest om-panel om-panel--lift"
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="dest-preview-title"
        on:click|stopPropagation
        on:keydown={(e) => e.stopPropagation()}
      >
        <header class="modal__head">
          <strong id="dest-preview-title">Destino: {previewDestPath}</strong>
          <button type="button" class="om-btn om-btn--ghost" on:click={() => (previewOpen = false)}>Cerrar</button>
        </header>
        <section class="modal__ctrl">
          <label class="field-label" for="dest-preview-scale">Miniaturas en vista previa {Math.round(previewScale * 100)}%</label>
          <input
            id="dest-preview-scale"
            class="om-range"
            type="range"
            min="0.7"
            max="2.1"
            step="0.01"
            bind:value={previewScale}
            on:input={scheduleDestScaleSave}
          />
        </section>
        <div class="modal__scroll">
          <section class="dest-grid" style={`--pv-min:${destModalGridMinPx}px`}>
            {#each previewItems as it}
              <div class="pv-tile">
                {#if it.thumbDataUrl}<img src={it.thumbDataUrl} alt="" />{/if}
                <span class="pv-tile__name">{it.name}</span>
              </div>
            {/each}
          </section>
        </div>
      </div>
    </div>
  {/if}

  {#if ghostVisible}
    <div class="drag-ghost" style={`left:${ghostX}px;top:${ghostY}px`} aria-hidden="true">
      <div class="drag-ghost__card">
        {#if ghostThumb}
          <img src={ghostThumb} alt="" class="drag-ghost__img" />
        {:else}
          <div class="drag-ghost__ph">IMG</div>
        {/if}
        {#if ghostCount > 1}
          <span class="drag-ghost__badge">{ghostCount}</span>
        {/if}
      </div>
      <span class="drag-ghost__cap">{ghostCaption}</span>
    </div>
  {/if}

  {#if orgPanelOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="org-float-overlay" role="presentation" on:click|self={() => (orgPanelOpen = false)}>
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <div
        class="organizer-float om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="org-float-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="org-float__head">
          <strong id="org-float-title">Organizar medios</strong>
          <button type="button" class="om-btn om-btn--ghost" on:click={() => (orgPanelOpen = false)}>Cerrar</button>
        </header>
        <div class="org-row">
          <label class="field-label" for="org-path-input-float">Ruta</label>
          <input id="org-path-input-float" class="om-input org-row__input" bind:value={orgPath} placeholder="Carpeta raíz a organizar" />
          <button type="button" class="om-btn om-btn--primary" title="Elegir carpeta" on:click={pickOrgFolder}>Examinar…</button>
        </div>
        <div class="checks">
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeOrganized} /> Incluir Organizado</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includeComics} /> Incluir ComicsCBZ</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.includePending} /> Incluir PendientesRevisión</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.removeDuplicates} /> Eliminar duplicadas</label>
          <label class="check"><input type="checkbox" bind:checked={orgOptions.groupSimilarImages} /> Agrupar similares</label>
        </div>
        <div class="org-row org-row--footer">
          <button type="button" class="om-btn om-btn--primary" on:click={startOrganizer} disabled={orgRunning}>Organizar ahora</button>
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelOrganizer} disabled={!orgRunning}>Cancelar</button>
          <span class="org-status">{orgDetail}</span>
          <span class="org-progress">{orgProgress}</span>
        </div>
      </div>
    </div>
  {/if}

  {#if settingsOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="overlay overlay--dim" role="presentation" on:click|self={cancelSettingsModal}>
      <div
        class="modal modal--settings om-panel om-panel--lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabindex="-1"
        on:click|stopPropagation={() => undefined}
      >
        <header class="modal__head">
          <strong id="settings-title">Ajustes</strong>
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelSettingsModal}>Cerrar</button>
        </header>
        <section class="settings-body">
          <label class="field-label" for="set-thumbs-page">Imágenes por página</label>
          <input
            id="set-thumbs-page"
            class="om-input"
            type="number"
            min="12"
            max="120"
            bind:value={thumbsPerPage}
          />
          <p class="settings-hint">Valores más bajos (p. ej. 24–48) aceleran el cambio de página; el máximo es 120.</p>
        </section>
        <div class="settings-actions">
          <button type="button" class="om-btn om-btn--ghost" on:click={cancelSettingsModal}>Cancelar</button>
          <button type="button" class="om-btn om-btn--primary" on:click={saveSettingsModal}>Guardar</button>
        </div>
      </div>
    </div>
  {/if}

  {#if uiLoading}
    <div class="load-overlay" aria-busy="true" aria-live="polite">
      <div class="load-overlay__spinner"></div>
      <span class="load-overlay__text">Cargando…</span>
    </div>
  {/if}
</main>

<style>
  @import "./styles/design-tokens.css";
  @import "./styles/components.css";

  .app {
    height: 100%;
    display: grid;
    gap: var(--om-space-4);
    /* tabs · ruta · [opcional] · galería · paginador */
    grid-template-rows: auto auto 1fr auto;
    padding: var(--om-space-4) var(--om-space-5);
    font-family: var(--om-font-sans);
    color: var(--om-text-primary);
    background: radial-gradient(120% 80% at 50% -20%, rgb(124 140 255 / 0.12), transparent 50%), var(--om-bg-base);
    box-sizing: border-box;
  }

  .app.app--extra-row {
    /* Barra bajo ruta: acciones Destinos o panel Organizar */
    grid-template-rows: auto auto auto 1fr auto;
  }

  .tabs-bar {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .tabs__nav {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
    align-items: center;
  }

  .route {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--om-space-3);
  }

  .route__row {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .recent-folders__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--om-space-3);
    flex-wrap: wrap;
  }

  .recent-folders__hint {
    font-size: 0.7rem;
    color: var(--om-text-muted);
  }

  .recent-folders__list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
  }

  .recent-folders__chip {
    max-width: 100%;
    text-align: left;
    font-size: 0.75rem;
    line-height: 1.3;
    white-space: normal;
    word-break: break-all;
  }

  .route__path {
    flex: 1;
    min-width: min(280px, 100%);
  }

  .field-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--om-text-secondary);
    white-space: nowrap;
  }

  .actions {
    display: flex;
    gap: var(--om-space-3);
    align-items: center;
    flex-wrap: wrap;
  }

  .pill {
    font-size: 0.8125rem;
    font-weight: 600;
    padding: var(--om-space-2) var(--om-space-4);
    border-radius: 999px;
    background: var(--om-accent-soft);
    border: 1px solid rgb(124 140 255 / 0.25);
    color: var(--om-text-primary);
  }

  .content {
    display: grid;
    gap: 0;
    min-height: 0;
    align-items: stretch;
  }

  .splitter {
    cursor: col-resize;
    width: 10px;
    margin: 0 -2px;
    z-index: 2;
    flex-shrink: 0;
    border-radius: 4px;
    background: linear-gradient(180deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.02));
    border: 1px solid rgb(255 255 255 / 0.08);
    touch-action: none;
  }

  .splitter:hover,
  .splitter:focus-visible {
    background: rgb(124 140 255 / 0.25);
  }

  .gallery {
    overflow: auto;
    min-height: 0;
    min-width: 0;
  }

  .grid {
    display: grid;
    /* Ancho fijo por celda (sin 1fr): el slider recorre muchos tamaños sin quedar atrapado en 2–3 columnas. */
    grid-template-columns: repeat(auto-fill, minmax(var(--cell, 160px), var(--cell, 160px)));
    gap: var(--om-space-3);
    contain: layout style;
  }

  .tile {
    touch-action: manipulation;
    position: relative;
    background: linear-gradient(180deg, var(--om-surface-3) 0%, var(--om-surface-2) 100%);
    border: 1px solid var(--om-border-default);
    border-radius: var(--om-radius-md);
    color: var(--om-text-primary);
    text-align: left;
    padding: var(--om-space-2);
    cursor: pointer;
    box-shadow: var(--om-shadow-sm);
    transition:
      transform var(--om-transition),
      box-shadow var(--om-transition),
      border-color var(--om-transition);
  }

  .tile:hover {
    box-shadow: var(--om-shadow-md), 0 0 0 1px rgb(124 140 255 / 0.2);
    border-color: rgb(124 140 255 / 0.25);
  }

  .tile.selected {
    outline: 2px solid var(--om-accent);
    outline-offset: 2px;
    box-shadow: 0 0 20px var(--om-accent-glow);
  }

  .tile img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: var(--om-radius-sm);
    display: block;
  }

  .folder-ph {
    width: 100%;
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.25);
    border-radius: var(--om-radius-sm);
    font-size: 0.75rem;
    color: var(--om-text-muted);
  }

  .tile__name {
    display: block;
    margin-top: var(--om-space-2);
    font-size: 0.7rem;
    line-height: 1.25;
    color: var(--om-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preview {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-3);
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }

  .preview__img {
    width: 100%;
    flex: 1 1 0;
    min-height: 0;
    max-height: 100%;
    object-fit: contain;
    object-position: center center;
    background: var(--om-bg-base);
    border-radius: var(--om-radius-md);
    border: 1px solid var(--om-border-subtle);
  }

  .preview__empty {
    flex: 1 1 0;
    min-height: 80px;
    display: grid;
    place-items: center;
    color: var(--om-text-muted);
    font-size: 0.875rem;
    border: 1px dashed var(--om-border-default);
    border-radius: var(--om-radius-md);
  }

  .preview__meta {
    font-size: 0.75rem;
    color: var(--om-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dest-panel__title {
    display: block;
    margin-bottom: var(--om-space-3);
  }

  .org-tab-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--om-space-4);
    justify-content: space-between;
  }

  .org-tab-bar__text {
    margin: 0;
    font-size: 0.875rem;
    color: var(--om-text-secondary);
    max-width: min(520px, 100%);
    line-height: 1.45;
  }

  .dest-grid-wrap {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--om-space-4);
  }

  .dest-grid-wrap--embedded {
    margin: 0;
  }

  .dest-card {
    background: linear-gradient(165deg, var(--om-surface-2) 0%, var(--om-surface-1) 100%);
    border: 1px solid var(--om-border-default);
    border-radius: var(--om-radius-lg);
    padding: var(--om-space-4);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-4);
    box-shadow: var(--om-shadow-md);
    transition: box-shadow var(--om-transition), border-color var(--om-transition);
  }

  .dest-card:hover {
    border-color: rgb(124 140 255 / 0.3);
    box-shadow: var(--om-shadow-lg);
  }

  .dest-card__head {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
  }

  .dest-card__title {
    font-weight: 700;
    font-size: 0.95rem;
  }

  .dest-card__path {
    font-size: 0.75rem;
    color: var(--om-text-muted);
    word-break: break-all;
  }

  .dest-card__actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-2);
  }

  .pager {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    flex-wrap: wrap;
  }

  .pager__jump {
    display: inline-flex;
    align-items: center;
    gap: var(--om-space-1);
    font-size: 0.8125rem;
    color: var(--om-text-secondary);
  }

  .pager__jump-input {
    width: 4.25rem;
    min-height: 2rem;
    padding: var(--om-space-1) var(--om-space-2);
    text-align: center;
  }

  .pager__jump-total {
    font-weight: 600;
    color: var(--om-text-primary);
  }

  .om-btn--compact {
    padding: var(--om-space-1) var(--om-space-3);
    font-size: 0.8125rem;
  }

  .pager__info,
  .status-line {
    font-size: 0.8125rem;
    color: var(--om-text-secondary);
  }

  .status-line {
    font-weight: 500;
    color: var(--om-accent-2);
  }

  .org-float-overlay {
    position: fixed;
    inset: 0;
    z-index: 35;
    display: grid;
    place-items: center;
    padding: var(--om-space-4);
    background: rgb(4 6 14 / 0.55);
    box-sizing: border-box;
  }

  .organizer-float {
    width: min(720px, 100%);
    max-height: min(88vh, 900px);
    overflow: auto;
    padding: var(--om-space-5);
  }

  .org-float__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--om-space-3);
    margin-bottom: var(--om-space-4);
  }

  .organizer-float .org-row {
    display: flex;
    align-items: center;
    gap: var(--om-space-3);
    margin-bottom: var(--om-space-4);
    flex-wrap: wrap;
  }

  .org-row__input {
    flex: 1;
    min-width: 200px;
  }

  .org-row--footer {
    margin-bottom: 0;
    margin-top: var(--om-space-2);
  }

  .checks {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: var(--om-space-2);
    margin-bottom: var(--om-space-4);
  }

  .check {
    font-size: 0.875rem;
    color: var(--om-text-secondary);
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
  }

  .org-status,
  .org-progress {
    font-size: 0.8125rem;
    color: var(--om-text-muted);
  }

  .grow {
    flex: 1;
  }

  .load-overlay {
    position: fixed;
    inset: 0;
    z-index: 150;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--om-space-3);
    background: rgb(4 6 14 / 0.42);
    pointer-events: all;
  }

  .load-overlay__spinner {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 3px solid rgb(255 255 255 / 0.18);
    border-top-color: var(--om-accent);
    animation: om-spin 0.7s linear infinite;
  }

  .load-overlay__text {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }

  @keyframes om-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .overlay {
    position: fixed;
    inset: 0;
    background: rgb(4 6 14 / 0.85);
    display: grid;
    place-items: center;
    z-index: 40;
  }

  .overlay--dim {
    background: rgb(4 6 14 / 0.72);
    z-index: 45;
  }

  .modal--settings {
    width: min(420px, 92vw);
    max-height: min(90vh, 560px);
    display: flex;
    flex-direction: column;
    gap: var(--om-space-4);
    padding: var(--om-space-5);
    box-sizing: border-box;
  }

  .settings-body {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
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

  .modal {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    gap: var(--om-space-3);
    padding: var(--om-space-5);
    z-index: 41;
    box-sizing: border-box;
  }

  /* Altura explícita: si solo hay max-height, el cuerpo flex no ocupa espacio y casi no se ve la rejilla. */
  .modal--dest {
    width: min(80vw, min(1100px, 96vw));
    height: clamp(480px, 82vh, 920px);
    max-height: min(94vh, 920px);
  }

  .modal__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--om-space-3);
  }

  .modal__ctrl {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--om-space-3);
    flex-shrink: 0;
  }

  .modal__scroll {
    flex: 1 1 0;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
  }

  .dest-grid {
    flex: 1 1 auto;
    min-height: 0;
    min-width: 0;
    overflow-x: hidden;
    overflow-y: auto;
    display: grid;
    /* auto-fill: solo columnas que caben; min() evita una pista más estrecha que el contenedor. */
    grid-template-columns: repeat(auto-fill, minmax(min(var(--pv-min, 120px), 100%), 1fr));
    gap: var(--om-space-3);
    align-content: start;
  }

  .pv-tile {
    background: var(--om-surface-2);
    border-radius: var(--om-radius-sm);
    padding: var(--om-space-2);
    border: 1px solid var(--om-border-subtle);
  }

  .pv-tile img {
    width: 100%;
    height: auto;
    max-height: 240px;
    object-fit: contain;
    object-position: center;
    border-radius: 6px;
    background: rgb(0 0 0 / 0.2);
  }

  .pv-tile__name {
    font-size: 0.65rem;
    color: var(--om-text-muted);
    display: block;
    margin-top: var(--om-space-1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Ghost de arrastre */
  .drag-ghost {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    pointer-events: none;
    transform: translate(16px, 16px);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--om-space-2);
    filter: drop-shadow(0 12px 24px rgb(0 0 0 / 0.55));
  }

  .drag-ghost__card {
    position: relative;
    width: 72px;
    height: 72px;
    border-radius: var(--om-radius-md);
    overflow: hidden;
    border: 2px solid rgb(124 140 255 / 0.6);
    background: var(--om-surface-1);
    box-shadow: var(--om-shadow-lg), 0 0 0 1px rgb(255 255 255 / 0.08);
  }

  .drag-ghost__img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .drag-ghost__ph {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--om-text-muted);
  }

  .drag-ghost__badge {
    position: absolute;
    right: -6px;
    top: -6px;
    min-width: 1.35rem;
    height: 1.35rem;
    padding: 0 5px;
    border-radius: 999px;
    background: linear-gradient(135deg, var(--om-accent), #4f5fd4);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 800;
    display: grid;
    place-items: center;
    border: 2px solid var(--om-bg-base);
    box-shadow: var(--om-shadow-sm);
  }

  .drag-ghost__cap {
    max-width: 220px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--om-text-primary);
    text-shadow: 0 2px 8px rgb(0 0 0 / 0.8);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
