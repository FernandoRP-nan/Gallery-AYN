/** Generación de navegación: invalida respuestas API obsoletas al cambiar de carpeta. */
let galleryNavigationGeneration = 0;

/** Tras un salto (rail/scrollbar), HQ no se difiere por scroll activo. */
let galleryHqJumpGraceUntil = 0;

export function bumpGalleryNavigationGeneration(): number {
  galleryNavigationGeneration++;
  galleryHqJumpGraceUntil = 0;
  return galleryNavigationGeneration;
}

export function getGalleryNavigationGeneration(): number {
  return galleryNavigationGeneration;
}

export function isGalleryNavigationCurrent(generation: number): boolean {
  return generation === galleryNavigationGeneration;
}

/** Activa gracia HQ post-salto (ms desde ahora). Se acumula el máximo si ya hay gracia. */
export function armGalleryHqJumpGrace(durationMs = 5000): void {
  galleryHqJumpGraceUntil = Math.max(galleryHqJumpGraceUntil, Date.now() + durationMs);
}

export function isGalleryHqJumpGraceActive(): boolean {
  return Date.now() < galleryHqJumpGraceUntil;
}
