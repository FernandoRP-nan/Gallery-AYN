import { derived, writable } from "svelte/store";

export type SectionDestMoveCtx = {
  id: number;
  onPick: (destPath: string) => void;
};

let nextSectionDestMoveId = 1;

export function allocSectionDestMoveId(): number {
  nextSectionDestMoveId += 1;
  return nextSectionDestMoveId;
}

/** Menú «Mover» abierto en un encabezado de sección (un solo handler activo). */
export const sectionDestMoveCtx = writable<SectionDestMoveCtx | null>(null);

export const sectionDestMoveActive = derived(sectionDestMoveCtx, (ctx) => ctx !== null);
