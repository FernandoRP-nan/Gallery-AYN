/** Parámetros de rendimiento de galería (persistidos en ajustes). */
export type GalleryPerfConfig = {
  unlimitedBatchSize: number;
  windowOverscanBefore: number;
  windowOverscanAfter: number;
  thumbBuildWorkers: number;
  thumbHqWorkers: number;
  thumbHqVisibleSequential: number;
};

const DEFAULTS: GalleryPerfConfig = {
  unlimitedBatchSize: 48,
  windowOverscanBefore: 96,
  windowOverscanAfter: 160,
  thumbBuildWorkers: 8,
  thumbHqWorkers: 4,
  thumbHqVisibleSequential: 16,
};

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
    thumbBuildWorkers: Number(settings?.gallery_thumb_build_workers ?? DEFAULTS.thumbBuildWorkers),
    thumbHqWorkers: Number(settings?.gallery_thumb_hq_workers ?? DEFAULTS.thumbHqWorkers),
    thumbHqVisibleSequential: Number(
      settings?.gallery_thumb_hq_visible_sequential ?? DEFAULTS.thumbHqVisibleSequential,
    ),
  };
}
