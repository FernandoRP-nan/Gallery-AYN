import { normalizePathForApi } from "./pathUtils";

export type TranscodeJobRow = {
  id: string;
  path: string;
  name: string;
  format: string;
  progress?: string;
  status?: string;
  queuePosition?: string;
};

export function isActiveTranscodeJob(job: TranscodeJobRow): boolean {
  const st = String(job.status ?? "running").toLowerCase();
  return st === "queued" || st === "running";
}

/** Porcentaje 0–99 de un job activo para la ruta; null si no hay job en curso. */
export function transcodeProgressForPath(path: string, jobs: TranscodeJobRow[]): number | null {
  const key = normalizePathForApi(path);
  if (!key) return null;
  const job = jobs.find(
    (j) => isActiveTranscodeJob(j) && normalizePathForApi(j.path) === key
  );
  if (!job) return null;
  if (job.status === "queued") return 0;
  const p = parseInt(String(job.progress ?? "0"), 10);
  return Number.isFinite(p) ? Math.min(99, Math.max(0, p)) : 0;
}
