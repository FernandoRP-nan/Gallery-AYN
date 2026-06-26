/** Parámetros de rendimiento de galería (persistidos en ajustes). */
export type GalleryPerfConfig = {
  unlimitedBatchSize: number;
  windowOverscanBefore: number;
  windowOverscanAfter: number;
  jumpCoreOverscanBefore: number;
  jumpCoreOverscanAfter: number;
  slidingWindowEnabled: boolean;
  slidingWindowMaxItems: number;
  thumbBuildWorkers: number;
  thumbHqWorkers: number;
  thumbHqVisibleSequential: number;
};

const DEFAULTS: GalleryPerfConfig = {
  unlimitedBatchSize: 48,
  windowOverscanBefore: 96,
  windowOverscanAfter: 160,
  jumpCoreOverscanBefore: 32,
  jumpCoreOverscanAfter: 48,
  slidingWindowEnabled: true,
  slidingWindowMaxItems: 896,
  thumbBuildWorkers: 8,
  thumbHqWorkers: 4,
  thumbHqVisibleSequential: 16,
};

export const GALLERY_SMALL_FOLDER_MAX = 2000;
export const GALLERY_SMALL_FOLDER_BATCH_CAP = 32;

export function isSmallGalleryTotal(total: number): boolean {
  return total > 0 && total <= GALLERY_SMALL_FOLDER_MAX;
}

/** Tamaño de tanda LQ en scroll/append (carpetas pequeñas → batch corto). */
export function effectiveUnlimitedBatchSize(
  total: number,
  configured = getGalleryPerfConfig().unlimitedBatchSize,
): number {
  if (!isSmallGalleryTotal(total)) return configured;
  return Math.max(24, Math.min(configured, GALLERY_SMALL_FOLDER_BATCH_CAP));
}

/** Batch inicial de apertura: siempre el configurado (no acortar). */
export function initialUnlimitedBatchSize(
  configured = getGalleryPerfConfig().unlimitedBatchSize,
): number {
  return configured;
}

let active: GalleryPerfConfig = { ...DEFAULTS };

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

export function getGalleryPerfConfig(): GalleryPerfConfig {
  return active;
}

export function applyGalleryPerfConfig(raw: Partial<GalleryPerfConfig>) {
  active = {
    unlimitedBatchSize: clamp(
      Number(raw.unlimitedBatchSize ?? active.unlimitedBatchSize) || DEFAULTS.unlimitedBatchSize,
      24,
      256,
    ),
    windowOverscanBefore: clamp(
      Number(raw.windowOverscanBefore ?? active.windowOverscanBefore) || DEFAULTS.windowOverscanBefore,
      32,
      512,
    ),
    windowOverscanAfter: clamp(
      Number(raw.windowOverscanAfter ?? active.windowOverscanAfter) || DEFAULTS.windowOverscanAfter,
      32,
      512,
    ),
    jumpCoreOverscanBefore: clamp(
      Number(raw.jumpCoreOverscanBefore ?? active.jumpCoreOverscanBefore) ||
        DEFAULTS.jumpCoreOverscanBefore,
      16,
      128,
    ),
    jumpCoreOverscanAfter: clamp(
      Number(raw.jumpCoreOverscanAfter ?? active.jumpCoreOverscanAfter) ||
        DEFAULTS.jumpCoreOverscanAfter,
      24,
      160,
    ),
    slidingWindowEnabled: Boolean(
      raw.slidingWindowEnabled ?? active.slidingWindowEnabled ?? DEFAULTS.slidingWindowEnabled,
    ),
    slidingWindowMaxItems: clamp(
      Number(raw.slidingWindowMaxItems ?? active.slidingWindowMaxItems) ||
        DEFAULTS.slidingWindowMaxItems,
      320,
      4096,
    ),
    thumbBuildWorkers: clamp(
      Number(raw.thumbBuildWorkers ?? active.thumbBuildWorkers) || DEFAULTS.thumbBuildWorkers,
      2,
      16,
    ),
    thumbHqWorkers: clamp(
      Number(raw.thumbHqWorkers ?? active.thumbHqWorkers) || DEFAULTS.thumbHqWorkers,
      1,
      16,
    ),
    thumbHqVisibleSequential: clamp(
      Number(raw.thumbHqVisibleSequential ?? active.thumbHqVisibleSequential) ||
        DEFAULTS.thumbHqVisibleSequential,
      4,
      32,
    ),
  };
}

export function galleryPerfFromSettings(settings: Record<string, unknown> | undefined): GalleryPerfConfig {
  return {
    unlimitedBatchSize: Number(settings?.gallery_unlimited_batch_size ?? DEFAULTS.unlimitedBatchSize),
    windowOverscanBefore: Number(settings?.gallery_window_overscan_before ?? DEFAULTS.windowOverscanBefore),
    windowOverscanAfter: Number(settings?.gallery_window_overscan_after ?? DEFAULTS.windowOverscanAfter),
    jumpCoreOverscanBefore: Number(
      settings?.gallery_jump_core_overscan_before ?? DEFAULTS.jumpCoreOverscanBefore,
    ),
    jumpCoreOverscanAfter: Number(
      settings?.gallery_jump_core_overscan_after ?? DEFAULTS.jumpCoreOverscanAfter,
    ),
    slidingWindowEnabled: Boolean(
      settings?.gallery_sliding_window_enabled ?? DEFAULTS.slidingWindowEnabled,
    ),
    slidingWindowMaxItems: Number(
      settings?.gallery_sliding_window_max_items ?? DEFAULTS.slidingWindowMaxItems,
    ),
    thumbBuildWorkers: Number(settings?.gallery_thumb_build_workers ?? DEFAULTS.thumbBuildWorkers),
    thumbHqWorkers: Number(settings?.gallery_thumb_hq_workers ?? DEFAULTS.thumbHqWorkers),
    thumbHqVisibleSequential: Number(
      settings?.gallery_thumb_hq_visible_sequential ?? DEFAULTS.thumbHqVisibleSequential,
    ),
  };
}
