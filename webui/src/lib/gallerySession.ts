/** Generación de navegación: invalida respuestas API obsoletas al cambiar de carpeta. */
let galleryNavigationGeneration = 0;

export function bumpGalleryNavigationGeneration(): number {
  galleryNavigationGeneration++;
  return galleryNavigationGeneration;
}

export function getGalleryNavigationGeneration(): number {
  return galleryNavigationGeneration;
}

export function isGalleryNavigationCurrent(generation: number): boolean {
  return generation === galleryNavigationGeneration;
}
