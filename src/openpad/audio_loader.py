"""Загрузка аудиофайлов в PCM float32 stereo 44100 Гц.

Стратегия:
1. Пробуем soundfile (wav/mp3/ogg/flac — зависит от libsndfile).
2. Если не вышло и в системе есть ffmpeg — декодируем через него
   (покрывает m4a/aac/wma/opus/mp4).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np

TARGET_SR = 44100
TARGET_CHANNELS = 2

SUPPORTED_EXTS = frozenset({
    ".wav", ".mp3", ".ogg", ".flac",
    ".m4a", ".aac", ".opus", ".wma", ".mp4",
})


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTS


def _to_stereo_44100(samples: np.ndarray, sr: int) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples[:, None]
    # mono/stereo/... -> stereo
    if samples.shape[1] == 1:
        samples = np.repeat(samples, 2, axis=1)
    elif samples.shape[1] > 2:
        samples = samples[:, :2]
    # resample (линейный, достаточно для мемных звуков)
    if sr != TARGET_SR and len(samples) > 1:
        old_idx = np.linspace(0, 1, len(samples))
        new_len = max(1, int(len(samples) * TARGET_SR / sr))
        new_idx = np.linspace(0, 1, new_len)
        resampled = np.empty((new_len, 2), dtype=np.float32)
        for ch in range(2):
            resampled[:, ch] = np.interp(new_idx, old_idx, samples[:, ch])
        samples = resampled
    return np.ascontiguousarray(samples, dtype=np.float32)


def _load_with_soundfile(path: str) -> tuple[np.ndarray, int]:
    import soundfile as sf
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return _to_stereo_44100(data, int(sr)), TARGET_SR


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # опционально
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _load_with_ffmpeg(path: str, ffmpeg: str) -> tuple[np.ndarray, int]:
    cmd = [
        ffmpeg, "-v", "error", "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", str(TARGET_CHANNELS), "-ar", str(TARGET_SR),
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(proc.stderr.decode(errors="ignore")[-500:])
    raw = np.frombuffer(proc.stdout, dtype=np.float32)
    if raw.size % TARGET_CHANNELS != 0:
        raw = raw[: raw.size - (raw.size % TARGET_CHANNELS)]
    return raw.reshape(-1, TARGET_CHANNELS), TARGET_SR


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Вернуть (samples [N,2] float32, 44100). Бросает исключение при ошибке."""
    p = str(path)
    try:
        return _load_with_soundfile(p)
    except Exception as sf_err:
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError(f"Не supported/no ffmpeg: {sf_err}") from sf_err
        return _load_with_ffmpeg(p, ffmpeg)


def get_duration_str(path: str | Path) -> str:
    try:
        import soundfile as sf
        info = sf.info(str(path))
        secs = int(info.frames / float(info.samplerate or TARGET_SR))
        return f"{secs // 60}:{secs % 60:02d}"
    except Exception:
        pass
    # fallback: ffmpeg probe невозможен без парсинга — возвращаем заглушку
    return "?:??"
