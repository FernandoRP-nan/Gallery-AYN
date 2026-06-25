"""Transcodificación a H.264/AAC para reproducción en WebView."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from .video_playback_mode import PlaybackMode, normalize_playback_mode, resolve_transcode_plan, transcode_cache_suffix

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_TRANSCODE_SEM = threading.Semaphore(1)
_WARM_TOKENS: set[str] = set()
_WARM_GUARD = threading.Lock()
_ACTIVE_JOBS: dict[str, dict[str, str]] = {}
_ACTIVE_GUARD = threading.Lock()
_RUNNING: dict[str, threading.Thread] = {}
_RUNNING_GUARD = threading.Lock()
_PARTIAL_MIN_BYTES = 196_608
_PROGRESSIVE_MOVFLAGS = ["-movflags", "frag_keyframe+empty_moov+default_base_moof"]


def list_active_transcode_jobs() -> list[dict[str, str]]:
    with _ACTIVE_GUARD:
        return [j for j in _ACTIVE_JOBS.values() if j.get("status") in ("queued", "running")]


def _set_active_job(token: str, source: Path, fmt: str) -> None:
    _register_transcode_job(token, source, fmt, status="running")


def _update_job_progress(token: str, progress: int) -> None:
    with _ACTIVE_GUARD:
        job = _ACTIVE_JOBS.get(token)
        if job is not None:
            job["progress"] = str(min(99, max(0, int(progress))))


def _clear_active_job(token: str) -> None:
    with _ACTIVE_GUARD:
        _ACTIVE_JOBS.pop(token, None)



def _register_transcode_job(token: str, source: Path, fmt: str, *, status: str = "queued") -> None:
    with _ACTIVE_GUARD:
        prev = _ACTIVE_JOBS.get(token)
        if prev and prev.get("status") in ("running", "done"):
            return
        _ACTIVE_JOBS[token] = {
            "id": token,
            "path": str(source),
            "name": source.name,
            "format": fmt,
            "progress": prev.get("progress", "0") if prev else "0",
            "status": status,
        }


def _mark_job_running(token: str) -> None:
    with _ACTIVE_GUARD:
        job = _ACTIVE_JOBS.get(token)
        if job is not None:
            job["status"] = "running"


def _fail_active_job(token: str) -> None:
    _clear_active_job(token)


def _finish_active_job(token: str) -> None:
    _clear_active_job(token)


def _mp4_job_format(source: Path) -> str:
    video, audio = _ffprobe_streams(source.resolve())
    mode = mp4_playback_mode(video, audio)
    return "remux" if mode in ("copy_all", "copy_video_aac") else "mp4"


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


def transcode_output_path(source: Path, *, playback_mode: str = "auto") -> Path:
    mode = normalize_playback_mode(playback_mode)
    suffix = transcode_cache_suffix(mode, source.resolve())
    return transcode_cache_dir() / f"{_media_token(source, suffix=suffix)}.mp4"


def transcode_partial_path(out: Path) -> Path:
    return out.with_suffix(".part.mp4")


def transcode_webm_output_path(source: Path) -> Path:
    from .video_transcode_options import get_transcode_max_height, get_transcode_max_width

    suffix = f"webm-{get_transcode_max_height()}-{get_transcode_max_width()}"
    return transcode_cache_dir() / f"{_media_token(source, suffix=suffix)}.webm"


def invalidate_transcode_cache() -> int:
    """Elimina la caché de transcodificación (p. ej. al cambiar ajustes globales)."""
    from .video_transcode_options import reset_hw_encoder_cache

    reset_hw_encoder_cache()
    removed = 0
    cache = transcode_cache_dir()
    for entry in cache.iterdir():
        if not entry.is_file():
            continue
        try:
            entry.unlink()
            removed += 1
        except OSError:
            pass
    with _RUNNING_GUARD:
        _RUNNING.clear()
    return removed


def _remember_transcode_source(source: Path, *, playback_mode: str = "auto") -> None:
    """Registra el origen en caché (symlink o fichero .path) para rutas legacy /om-transcode."""
    name = transcode_output_path(source, playback_mode=playback_mode).name
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
    from .video_tools import resolve_ffprobe

    ffprobe = resolve_ffprobe()
    if not ffprobe:
        return None, None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_streams", "-of", "json", str(path)],
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


_H264_COMPAT_PIX = frozenset({"yuv420p", "yuvj420p"})


def mp4_playback_mode(video: dict | None, audio: dict | None) -> str:
    """Estrategia MP4: copy_all (remux), copy_video_aac (solo audio) o full_encode."""
    if not video:
        return "full_encode"
    if (video.get("codec_name") or "").lower() != "h264":
        return "full_encode"
    pix = (video.get("pix_fmt") or "").lower()
    if pix and pix not in _H264_COMPAT_PIX:
        return "full_encode"
    if not audio:
        return "copy_all"
    acodec = (audio.get("codec_name") or "").lower()
    if acodec in ("aac", "mp3"):
        return "copy_all"
    return "copy_video_aac"


def is_browser_playable(path: Path) -> bool:
    """True si el MP4/M4V ya es H.264/AAC y suele reproducirse en WebView."""
    if path.suffix.lower() not in (".mp4", ".m4v"):
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
    name = transcode_webm_output_path(source).name
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


def _parse_duration_us(video: dict | None) -> int | None:
    if not video:
        return None
    raw = video.get("duration")
    if raw is None:
        return None
    try:
        return max(1, int(float(raw) * 1_000_000))
    except (TypeError, ValueError):
        return None


def _run_ffmpeg(
    args: list[str],
    *,
    token: str | None = None,
    duration_us: int | None = None,
    timeout: int = 7200,
) -> None:
    from .video_tools import resolve_ffmpeg

    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg no está instalado o no está en el PATH. "
            "En Windows, instala ffmpeg o coloca ffmpeg.exe en tools/ffmpeg/ junto al programa."
        )
    if token and duration_us and duration_us > 0:
        cmd = [ffmpeg, "-hide_banner", "-nostats", "-progress", "pipe:1", "-loglevel", "error", *args]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        out_us = int(line.split("=", 1)[1] or "0")
                        pct = int(out_us * 100 / duration_us)
                        _update_job_progress(token, pct)
                    except ValueError:
                        pass
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise RuntimeError("ffmpeg excedió el tiempo límite") from exc
        if proc.returncode != 0:
            err = (proc.stderr.read() if proc.stderr else "") or "ffmpeg falló"
            raise RuntimeError(err.strip() or "ffmpeg falló")
        return

    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or "ffmpeg falló")


def _transcode_to_mp4(
    source: Path,
    out: Path,
    *,
    token: str | None = None,
    playback_mode: str = "auto",
    progressive: bool = True,
) -> None:
    from .video_tools import resolve_ffmpeg
    from .video_transcode_options import PresetId, build_mp4_encode_options

    tmp = transcode_partial_path(out)
    if tmp.exists():
        tmp.unlink(missing_ok=True)
    video, audio = _ffprobe_streams(source)
    duration_us = _parse_duration_us(video)
    plan, preset_raw = resolve_transcode_plan(source, normalize_playback_mode(playback_mode))
    preset_override: PresetId | None = preset_raw if preset_raw in ("turbo", "fast", "quality") else None
    ffmpeg = resolve_ffmpeg() or "ffmpeg"
    movflags = _PROGRESSIVE_MOVFLAGS if progressive else ["-movflags", "+faststart"]

    if plan == "copy_all":
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
                *movflags,
                str(tmp),
            ],
            token=token,
            duration_us=duration_us,
        )
    elif plan == "copy_video_aac":
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
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                *movflags,
                str(tmp),
            ],
            token=token,
            duration_us=duration_us,
        )
    else:
        enc = build_mp4_encode_options(ffmpeg, preset_override=preset_override)
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
                enc.video_codec,
                *enc.video_args,
                *enc.audio_args,
                *movflags,
                str(tmp),
            ],
            token=token,
            duration_us=duration_us,
        )
    if not tmp.is_file() or tmp.stat().st_size < 512:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("La transcodificación no generó un archivo válido")
    tmp.replace(out)


def _transcode_to_webm(source: Path, out: Path, *, token: str | None = None) -> None:
    from .video_transcode_options import build_scale_filter, get_transcode_max_height, get_transcode_max_width

    tmp = out.with_suffix(".part.webm")
    if tmp.exists():
        tmp.unlink(missing_ok=True)
    video, _audio = _ffprobe_streams(source)
    duration_us = _parse_duration_us(video)
    vf = build_scale_filter(get_transcode_max_width(), get_transcode_max_height())
    args = [
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
    ]
    if vf:
        args.extend(["-vf", vf])
    args.extend(
        [
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
    _run_ffmpeg(args, token=token, duration_us=duration_us)
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
    resolved = source.resolve()
    out = transcode_webm_output_path(resolved)
    token = out.stem
    if _webm_cache_valid(out):
        _clear_active_job(token)
        return out
    _register_transcode_job(token, resolved, "webm", status="queued")
    with _TRANSCODE_SEM:
        _mark_job_running(token)
        with _lock_for(token):
            if _webm_cache_valid(out):
                _finish_active_job(token)
                return out
            try:
                _transcode_to_webm(resolved, out, token=token)
                _finish_active_job(token)
            except Exception:
                _fail_active_job(token)
                raise
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


def publish_mp4_playback_name(source: Path, *, playback_mode: str = "auto") -> str:
    """Registra el origen y devuelve el nombre para /om-transcode/…."""
    _remember_transcode_source(source.resolve(), playback_mode=playback_mode)
    return transcode_output_path(source, playback_mode=playback_mode).name


def _mp4_cache_valid(out: Path) -> bool:
    return out.is_file() and out.stat().st_size > 512 and is_browser_playable(out)


def _start_mp4_transcode_async(source: Path, *, playback_mode: str = "auto") -> None:
    resolved = source.resolve()
    mode = normalize_playback_mode(playback_mode)
    out = transcode_output_path(resolved, playback_mode=mode)
    token = out.stem
    if _mp4_cache_valid(out):
        _clear_active_job(token)
        return

    with _RUNNING_GUARD:
        thread = _RUNNING.get(token)
        if thread is not None and thread.is_alive():
            return

        _remember_transcode_source(resolved, playback_mode=mode)
        _register_transcode_job(token, resolved, _mp4_job_format(resolved), status="queued")

        def _worker() -> None:
            try:
                with _TRANSCODE_SEM:
                    _mark_job_running(token)
                    with _lock_for(token):
                        if _mp4_cache_valid(out):
                            _finish_active_job(token)
                            return
                        try:
                            _transcode_to_mp4(
                                resolved,
                                out,
                                token=token,
                                playback_mode=mode,
                                progressive=True,
                            )
                            _finish_active_job(token)
                        except Exception:
                            _fail_active_job(token)
                            partial = transcode_partial_path(out)
                            partial.unlink(missing_ok=True)
                            raise
            finally:
                with _RUNNING_GUARD:
                    _RUNNING.pop(token, None)

        t = threading.Thread(target=_worker, daemon=True, name=f"om-transcode-{token[:8]}")
        _RUNNING[token] = t
        t.start()


def resolve_mp4_playback_path(source: Path, *, playback_mode: str = "auto", wait_partial: bool = True) -> Path:
    """Ruta servible por HTTP (final o parcial en curso)."""
    resolved = source.resolve()
    mode = normalize_playback_mode(playback_mode)
    out = transcode_output_path(resolved, playback_mode=mode)
    partial = transcode_partial_path(out)

    if _mp4_cache_valid(out):
        _clear_active_job(out.stem)
        return out

    _start_mp4_transcode_async(resolved, playback_mode=mode)

    if not wait_partial:
        if partial.is_file() and partial.stat().st_size >= _PARTIAL_MIN_BYTES:
            return partial
        if out.is_file():
            return out
        raise FileNotFoundError("Transcodificación aún no iniciada")

    deadline = time.time() + 60.0
    while time.time() < deadline:
        if _mp4_cache_valid(out):
            return out
        if partial.is_file() and partial.stat().st_size >= _PARTIAL_MIN_BYTES:
            return partial
        time.sleep(0.12)

    raise TimeoutError("Tiempo de espera agotado para iniciar reproducción progresiva")


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
    _register_transcode_job(token, resolved, "webm", status="queued")

    def _worker() -> None:
        token = out.stem
        try:
            ensure_transcoded_webm(resolved)
        except Exception:
            _fail_active_job(token)
        finally:
            _clear_active_job(token)
            with _WARM_GUARD:
                _WARM_TOKENS.discard(token)

    threading.Thread(target=_worker, daemon=True, name="om-transcode-webm-warm").start()


def ensure_transcoded_mp4(source: Path, *, playback_mode: str = "auto") -> Path:
    """Devuelve el MP4 en caché; transcodifica la primera vez si hace falta (bloqueante)."""
    resolved = source.resolve()
    mode = normalize_playback_mode(playback_mode)
    out = transcode_output_path(resolved, playback_mode=mode)
    token = out.stem
    if _mp4_cache_valid(out):
        _clear_active_job(token)
        return out
    _register_transcode_job(token, resolved, _mp4_job_format(resolved), status="queued")
    with _TRANSCODE_SEM:
        _mark_job_running(token)
        with _lock_for(token):
            if _mp4_cache_valid(out):
                _finish_active_job(token)
                return out
            try:
                _transcode_to_mp4(
                    resolved,
                    out,
                    token=token,
                    playback_mode=mode,
                    progressive=False,
                )
                _finish_active_job(token)
            except Exception:
                _fail_active_job(token)
                raise
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


def warm_transcode_async(source: Path, *, playback_mode: str = "auto") -> None:
    """Precalienta la caché de transcodificación sin bloquear la UI."""
    resolved = source.resolve()
    mode = normalize_playback_mode(playback_mode)
    _remember_transcode_source(resolved, playback_mode=mode)
    out = transcode_output_path(resolved, playback_mode=mode)
    if _mp4_cache_valid(out):
        return
    token = out.stem
    with _WARM_GUARD:
        if token in _WARM_TOKENS:
            return
        _WARM_TOKENS.add(token)

    def _worker() -> None:
        try:
            _start_mp4_transcode_async(resolved, playback_mode=mode)
        finally:
            with _WARM_GUARD:
                _WARM_TOKENS.discard(token)

    threading.Thread(target=_worker, daemon=True, name="om-transcode-warm").start()
