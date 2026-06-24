import { bridge } from "./api";

/** Copia texto al portapapeles (PyWebView → backend; navegador → API nativa). */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  const payload = String(text ?? "");
  if (!payload.trim()) return false;

  if (typeof window !== "undefined" && window.pywebview?.api) {
    try {
      const res = await bridge.galleryCopyTextToClipboard(payload);
      return Boolean(res?.ok);
    } catch {
      return false;
    }
  }

  try {
    await navigator.clipboard.writeText(payload);
    return true;
  } catch {
    return execCommandCopy(payload);
  }
}

function execCommandCopy(text: string): boolean {
  if (typeof document === "undefined") return false;
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "true");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    document.body.removeChild(ta);
  }
}
