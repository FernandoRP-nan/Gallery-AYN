import { writable } from "svelte/store";

/** True mientras el usuario desplaza la rejilla (para diferir hidratación HQ). */
export const galleryScrolling = writable(false);
