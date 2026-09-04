"""Двухвыходной аудио-движок: динамики + виртуальный микрофон.

Честная архитектура (как у оригинального Soundpad, но открыто):
- Оригинальный Soundpad ставит свой драйвер "Soundpad Virtual Audio Device".
  Это и есть "то самое левое" — просто оно bundled и подписано.
- Open-source проект не может бесплатно шиппить подписанный kernel-драйвер
  (нужен EV-сертификат + attestation Microsoft), поэтому OpenPad:
  1. из коробки играет в динамики/наушники (ничего ставить не надо);
  2. при желании играет ВТОРОЙ копией в виртуальный кабель
     (VB-Cable / Voicemeeter — ставится за минуту, бесплатно).
     В Discord/игре выбираете микрофоном "CABLE Output",
     а свой живой голос пробрасываете галкой "сквозной микрофон".

Технически: sounddevice (PortAudio/WASAPI), каждый голос — свой поток,
чанки по 2048 фреймов, независимые гейны speakers/mic.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Voice:
    track_id: str
    stop_event: threading.Event = field(default_factory=threading.Event)
    threads: list = field(default_factory=list)
    timer: object = None  # для dummy-режима без sounddevice
    total_frames: int = 0
    sr: int = 44100
    pos_frames: int = 0  # только для индикации прогресса
    remaining: int = 0  # сколько потоков вывода ещё не завершились


class DualOutputEngine:
    def __init__(self,
                 speaker_device=None,
                 mic_device=None,
                 speaker_gain: float = 1.0,
                 mic_gain: float = 1.0,
                 allow_overlap: bool = False,
                 stop_on_repress: bool = True):
        self.speaker_device = speaker_device  # None=int|str|None
        self.mic_device = mic_device
        self.speaker_gain = max(0.0, min(1.0, speaker_gain))
        self.mic_gain = max(0.0, min(1.0, mic_gain))
        self.allow_overlap = allow_overlap
        self.stop_on_repress = stop_on_repress
        self._lock = threading.Lock()
        self._voices: dict[str, list[Voice]] = {}
        self.last_error: str | None = None
        try:
            import sounddevice  # noqa: F401
            self._dummy = False
        except Exception:
            self._dummy = True

    # -- настройки ------------------------------------------------------
    def configure(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    # -- состояние ------------------------------------------------------
    def is_playing(self, track_id: str) -> bool:
        with self._lock:
            voices = self._voices.get(track_id, [])
            return any(not v.stop_event.is_set() for v in voices)

    def any_playing(self) -> bool:
        with self._lock:
            return any(not v.stop_event.is_set()
                       for voices in self._voices.values() for v in voices)

    # -- управление -----------------------------------------------------
    def play(self, track_id: str, samples: np.ndarray,
             sr: int = 44100, volume: float = 1.0) -> str:
        """'started' | 'stopped' (toggle при stop_on_repress)."""
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = np.column_stack([samples, samples])
        gain_vol = max(0.0, min(1.0, volume))

        with self._lock:
            playing = [v for v in self._voices.get(track_id, [])
                       if not v.stop_event.is_set()]
            if playing and self.stop_on_repress and not self.allow_overlap:
                for v in playing:
                    v.stop_event.set()
                return "stopped"
            if playing and not self.allow_overlap:
                for v in self._voices.get(track_id, []):
                    v.stop_event.set()
                self._voices[track_id] = []

            voice = Voice(track_id=track_id,
                            total_frames=len(samples),
                            sr=int(sr or 44100))
            self._voices.setdefault(track_id, []).append(voice)

        jobs = []
        if self.speaker_gain > 0:
            jobs.append((self.speaker_device,
                         self.speaker_gain * gain_vol))
        if self.mic_device is not None and self.mic_gain > 0:
            jobs.append((self.mic_device, self.mic_gain * gain_vol))
        if not jobs:  # всё замьючено — всё равно считаем что "сыграло"
            jobs.append((self.speaker_device, gain_vol))
        voice.remaining = len(jobs)

        if self._dummy:
            dur = len(samples) / float(sr or 44100)
            t = threading.Timer(min(dur, 600.0), voice.stop_event.set)
            t.daemon = True
            voice.timer = t
            t.start()
            return "started"

        for device, gain in jobs:
            th = threading.Thread(
                target=self._play_on_device,
                args=(samples, sr, device, gain, voice),
                daemon=True,
            )
            voice.threads.append(th)
            th.start()
        return "started"

    def get_position(self, track_id: str) -> tuple[int, int, int]:
        """(проиграно фреймов, всего фреймов, sr) для индикации."""
        with self._lock:
            for v in self._voices.get(track_id, []):
                if not v.stop_event.is_set():
                    return v.pos_frames, v.total_frames, v.sr
        return 0, 0, 44100

    def _play_on_device(self, samples: np.ndarray, sr: int,
                        device, gain: float, voice: Voice) -> None:
        stop_event = voice.stop_event
        try:
            try:
                import sounddevice as sd
            except Exception as e:
                self.last_error = f"sounddevice: {e}"
                stop_event.wait(0.5)
                return
            data = (samples * gain).astype(np.float32, copy=False)
            block = 2048
            try:
                dev_arg = self._resolve_device(device)
                with sd.OutputStream(samplerate=sr,
                                     channels=data.shape[1],
                                     device=dev_arg,
                                     dtype="float32",
                                     blocksize=block) as stream:
                    pos = 0
                    n = len(data)
                    while pos < n and not stop_event.is_set():
                        chunk = data[pos:pos + block]
                        try:
                            stream.write(chunk)
                        except Exception as e:
                            self.last_error = f"write: {e}"
                            break
                        pos += len(chunk)
                        voice.pos_frames = pos
            except Exception as e:
                self.last_error = f"output: {e}"
        finally:
            # все потоки голоса завершились — голос больше не "играет"
            with self._lock:
                voice.remaining -= 1
                if voice.remaining <= 0:
                    stop_event.set()

    @staticmethod
    def _resolve_device(device):
        if device is None or isinstance(device, int):
            return device
        # строка: ищем по подстроке имени
        try:
            import sounddevice as sd
            name_low = str(device).lower()
            for i, d in enumerate(sd.query_devices()):
                if name_low in str(d.get("name", "")).lower():
                    return i
        except Exception:
            pass
        return None

    def stop_track(self, track_id: str) -> None:
        with self._lock:
            for v in self._voices.get(track_id, []):
                v.stop_event.set()

    def stop_all(self) -> None:
        with self._lock:
            for voices in self._voices.values():
                for v in voices:
                    v.stop_event.set()

    def cleanup(self) -> None:
        with self._lock:
            for tid in list(self._voices):
                self._voices[tid] = [v for v in self._voices[tid]
                                     if not v.stop_event.is_set()]


class MicPassthrough:
    """Сквозной прогон живой микрофон -> виртуальный кабель.

    Чтобы друзья в Discord слышали И вас, И мемы: вход=ваш микрофон,
    выход=тот же CABLE Input, куда OpenPad шлёт звуки.
    """

    def __init__(self):
        self._stream = None
        self._lock = threading.Lock()
        self.running = False
        self.error: str | None = None

    def start(self, input_device=None, output_device=None,
              gain: float = 1.0) -> bool:
        self.stop()
        try:
            import sounddevice as sd
        except Exception as e:
            self.error = f"sounddevice нет: {e}"
            return False
        try:
            in_arg = DualOutputEngine._resolve_device(input_device)
            out_arg = DualOutputEngine._resolve_device(output_device)

            def cb(indata, outdata, frames, t, status):
                outdata[:] = (indata * gain).astype(
                    outdata.dtype, copy=False)

            stream = sd.Stream(device=(in_arg, out_arg),
                               channels=2, dtype="float32",
                               callback=cb)
            stream.start()
            with self._lock:
                self._stream = stream
                self.running = True
                self.error = None
            return True
        except Exception as e:
            self.error = str(e)
            return False

    def stop(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self.running = False
