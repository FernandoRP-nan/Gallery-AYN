/** Números de página estilo resultados (mínimo 5 visibles + extremos). */
export function googlePageItems(page: number, totalPages: number): Array<number | "gap"> {
  if (totalPages <= 1) return totalPages === 1 ? [1] : [];
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  if (page <= 4) return [1, 2, 3, 4, 5, "gap", totalPages];
  if (page >= totalPages - 3) {
    return [1, "gap", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, "gap", page - 2, page - 1, page, page + 1, page + 2, "gap", totalPages];
}

export function formatBytes(size: number): string {
  const n = Math.max(0, Number(size) || 0);
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 100 ? 0 : v >= 10 ? 1 : 2)} ${units[i]}`;
}
