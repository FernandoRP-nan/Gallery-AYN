"""Transcodificación a H.264/AAC para reproducción en WebView."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
from pathlib import Path

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_TRANSCODE_SEM = threading.Semaphore(1)
_WARM_TOKENS: set[str] = set()
_WARM_GUARD = threading.Lock()
_ACTIVE_JOBS: dict[str, dict[str, str]] = {}
_ACTIVE_GUARD = threading.Lock()


def list_active_transcode_jobs() -> list[dict[str, str]]:
    with _ACTIVE_GUARD:
        return list(_ACTIVE_JOBS.values())


def _set_active_job(token: str, source: Path, fmt: str) -> None:
    with _ACTIVE_GUARD:
        _ACTIVE_JOBS[token] = {
            "id": token,
            "path": str(source),
            "name": source.name,
            "format": fmt,
        }


def _clear_active_job(token: str) -> None:
    with _ACTIVE_GUARD:
        _ACTIVE_JOBS.pop(token, None)


def transcode_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    d = Path(base) / "organizador-ayn" / "om-transcode"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _media_token(source: Path, *, suffix: str) -> str:
    resolved = source.resolve()
    st = resolved.stat()
    raw = f"{resolved}:{st.st_mtime_ns}:{st.st_size}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def transcode_output_path(source: Path) -> Path:
    return transcode_cache_dir() / f"{_media_token(source, suffix='transcode-h264')}.mp4"


def transcode_webm_output_path(source: Path) -> Path:
    return transcode_cache_dir() / f"{_media_token(source, suffix='transcode-webm')}.webm"


def _remember_transcode_source(source: Path) -> None:
    """Registra el origen en caché (symlink o fichero .path) para rutas legacy /om-transcode."""
    name = f"{_media_token(source, suffix='transcode-h264')}.mp4"
    link = transcode_cache_dir() / f"{name}.link"
    path_file = transcode_cache_dir() / f"{name}.path"
    resolved = source.resolve()
    try:
        if link.is_symlink():
            if link.resolve() != resolved:
                link.unlink()
                link.symlink_to(resolved)
        elif not link.exists():
            link.symlink_to(resolved)
    except OSError:
        try:
            path_file.write_text(str(resolved), encoding="utf-8")
        except OSError:
            pass
    else:
        path_file.unlink(missing_ok=True)


def _lock_for(token: str) -> threading.Lock:
    with _LOCKS_GUARD:
        if token not in _LOCKS:
            _LOCKS[token] = threading.Lock()
        return _LOCKS[token]


def _ffprobe_streams(path: Path) -> tuple[dict | None, dict | None]:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            return None, None
        streams = json.loads(result.stdout or "{}").get("streams") or []
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        return video, audio
    except Exception:
        return None, None


def is_browser_playable(path: Path) -> bool:
    """True si el MP4 ya es H.264/AAC y suele reproducirse en WebView."""
    if path.suffix.lower() != ".mp4":
        return False
    video, audio = _ffprobe_streams(path)
    if not video:
        return False
    if (video.get("codec_name") or "").lower() != "h264":
        return False
    pix = (video.get("pix_fmt") or "").lower()
    if pix and pix not in ("yuv420p", "yuvj420p"):
        return False
    if audio:
        if (audio.get("codec_name") or "").lower() not in ("aac", "mp3"):
            return False
    return True


def is_webm_playable(path: Path) -> bool:
    """True si el WebM usa VP8/VP9 + Opus/Vorbis (abierto, suele ir en Qt WebEngine)."""
    if path.suffix.lower() != ".webm":
        return False
    video, audio = _ffprobe_streams(path)
    if not video:
        return False
    if (video.get("codec_name") or "").lower() not in ("vp8", "vp9"):
        return False
    if audio and (audio.get("codec_name") or "").lower() not in ("opus", "vorbis"):
        return False
    return True


def _remember_webm_source(source: Path) -> None:
    name = f"{_media_token(source, suffix='transcode-webm')}.webm"
    link = transcode_cache_dir() / f"{name}.link"
    path_file = transcode_cache_dir() / f"{name}.path"
    resolved = source.resolve()
    try:
        if link.is_symlink():
            if link.resolve() != resolved:
                link.unlink()
                link.symlink_to(resolved)
        elif not link.exists():
            link.symlink_to(resolved)
    except OSError:
        try:
            path_file.write_text(str(resolved), encoding="utf-8")
        except OSError:
            pass
    else:
        path_file.unlink(missing_ok=True)


def _run_ffmpeg(args: list[str], *, timeout: int = 7200) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or "ffmpeg falló")


def _transcode_to_mp4(source: Path, out: Path) -> None:
    tmp = out.with_suffix(".part.mp4")
    if tmp.exists():
        tmp.unlink(missing_ok=True)
    video, audio = _ffprobe_streams(source)
    vcodec = (video or {}).get("codec_name", "").lower()
    acodec = (audio or {}).get("codec_name", "").lower() if audio else ""
    can_remux = (
        source.suffix.lower() == ".mp4"
        and vcodec == "h264"
        and (not audio or acodec in ("aac", "mp3"))
    )
    if can_remux:
        _run_ffmpeg(
            [
                "-y",
                "-i",
                str(source),
                "-map",
                "0:v:0?",
                "-map",
                "0:a:0?",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(tmp),
            ]
        )
    else:
        _run_ffmpeg(
            [
                "-y",
                "-i",
                str(source),
                "-map",
                "0:v:0?",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(tmp),
            ]
        )
    if not tmp.is_file() or tmp.stat().st_size < 512:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("La transcodificación no generó un archivo válido")
    tmp.replace(out)


def _transcode_to_webm(source: Path, out: Path) -> None:
    tmp = out.with_suffix(".part.webm")
    if tmp.exists():
        tmp.unlink(missing_ok=True)
    _run_ffmpeg(
        [
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0?",
            "-map",
            "0:a:0?",
            "-c:v",
            "libvpx",
            "-b:v",
            "1M",
            "-deadline",
            "realtime",
            "-cpu-used",
            "5",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            "-f",
            "webm",
            str(tmp),
        ]
    )
    if not tmp.is_file() or tmp.stat().st_size < 512:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("La transcodificación WebM no generó un archivo válido")
    tmp.replace(out)


def _webm_cache_valid(out: Path) -> bool:
    """Caché WebM válida: VP8/VP9 + Opus (Qt WebEngine)."""
    if not out.is_file() or out.stat().st_size <= 512 or not is_webm_playable(out):
        return False
    _, audio = _ffprobe_streams(out)
    return not audio or (audio.get("codec_name") or "").lower() == "opus"


def ensure_transcoded_webm(source: Path) -> Path:
    """Devuelve WebM en caché para visores sin H.264 (Qt en Fedora)."""
    out = transcode_webm_output_path(source)
    if _webm_cache_valid(out):
        return out
    token = out.stem
    with _TRANSCODE_SEM:
        with _lock_for(token):
            if _webm_cache_valid(out):
                return out
            _set_active_job(token, source.resolve(), "webm")
            try:
                _transcode_to_webm(source.resolve(), out)
            finally:
                _clear_active_job(token)
    return out


def resolve_webm_source(filename: str) -> Path | None:
    name = Path(filename).name
    if not name.endswith(".webm") or ".." in name:
        return None
    base = transcode_cache_dir()
    link = base / f"{name}.link"
    if link.is_symlink():
        try:
            p = link.resolve()
        except OSError:
            return None
        return p if p.is_file() else None
    path_file = base / f"{name}.path"
    if path_file.is_file():
        try:
            p = Path(path_file.read_text(encoding="utf-8").strip())
        except OSError:
            return None
        return p if p.is_file() else None
    return None


def publish_webm_playback_name(source: Path) -> str:
    """Registra el origen y devuelve el nombre para /om-webm/…."""
    _remember_webm_source(source.resolve())
    return transcode_webm_output_path(source).name


def publish_mp4_playback_name(source: Path) -> str:
    """Registra el origen y devuelve el nombre para /om-transcode/…."""
    _remember_transcode_source(source.resolve())
    return transcode_output_path(source).name


def warm_webm_transcode_async(source: Path) -> None:
    resolved = source.resolve()
    _remember_webm_source(resolved)
    out = transcode_webm_output_path(resolved)
    if _webm_cache_valid(out):
        return
    token = out.stem
    with _WARM_GUARD:
        if token in _WARM_TOKENS:
            return
        _WARM_TOKENS.add(token)

    def _worker() -> None:
        try:
            ensure_transcoded_webm(resolved)
        except Exception:
            pass
        finally:
            with _WARM_GUARD:
                _WARM_TOKENS.discard(token)

    threading.Thread(target=_worker, daemon=True, name="om-transcode-webm-warm").start()


def ensure_transcoded_mp4(source: Path) -> Path:
    """Devuelve el MP4 en caché; transcodifica la primera vez si hace falta."""
    out = transcode_output_path(source)
    if out.is_file() and out.stat().st_size > 512:
        return out
    token = out.stem
    with _TRANSCODE_SEM:
        with _lock_for(token):
            if out.is_file() and out.stat().st_size > 512:
                return out
            _set_active_job(token, source.resolve(), "mp4")
            try:
                _transcode_to_mp4(source.resolve(), out)
            finally:
                _clear_active_job(token)
    return out


def resolve_transcode_source(filename: str) -> Path | None:
    name = Path(filename).name
    if not name.endswith(".mp4") or ".." in name:
        return None
    base = transcode_cache_dir()
    link = base / f"{name}.link"
    if link.is_symlink():
        try:
            p = link.resolve()
        except OSError:
            return None
        return p if p.is_file() else None
    path_file = base / f"{name}.path"
    if path_file.is_file():
        try:
            p = Path(path_file.read_text(encoding="utf-8").strip())
        except OSError:
            return None
        return p if p.is_file() else None
    return None


def warm_transcode_async(source: Path) -> None:
    """Precalienta la caché de transcodificación sin bloquear la UI."""
    resolved = source.resolve()
    _remember_transcode_source(resolved)
    out = transcode_output_path(resolved)
    if out.is_file() and out.stat().st_size > 512:
        return
    token = out.stem
    with _WARM_GUARD:
        if token in _WARM_TOKENS:
            return
        _WARM_TOKENS.add(token)

    def _worker() -> None:
        try:
            ensure_transcoded_mp4(resolved)
        except Exception:
            pass
        finally:
            with _WARM_GUARD:
                _WARM_TOKENS.discard(token)

    threading.Thread(target=_worker, daemon=True, name="om-transcode-warm").start()
