"""Перечисление аудиоустройств (обёртка над sounddevice)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeviceInfo:
    index: int
    name: str
    is_input: bool
    is_output: bool
    is_default_input: bool = False
    is_default_output: bool = False


def _sd():
    try:
        import sounddevice as sd
        return sd
    except Exception:
        return None


def available() -> bool:
    return _sd() is not None


def list_all() -> list[DeviceInfo]:
    sd = _sd()
    if sd is None:
        return []
    try:
        raw = sd.query_devices()
        try:
            def_idx = sd.default.device  # (input, output)
        except Exception:
            def_idx = (None, None)
        out: list[DeviceInfo] = []
        for i, d in enumerate(raw):
            out.append(DeviceInfo(
                index=i,
                name=str(d.get("name", f"Device {i}")),
                is_input=int(d.get("max_input_channels", 0)) > 0,
                is_output=int(d.get("max_output_channels", 0)) > 0,
                is_default_input=(def_idx[0] == i),
                is_default_output=(def_idx[1] == i),
            ))
        return out
    except Exception:
        return []


def list_outputs() -> list[DeviceInfo]:
    return [d for d in list_all() if d.is_output]


def list_inputs() -> list[DeviceInfo]:
    return [d for d in list_all() if d.is_input]


_VIRTUAL_HINTS = ("cable", "vb-audio", "voicemeeter", "virtual", "banana", "potato")


def find_virtual_cables() -> list[DeviceInfo]:
    found = []
    for d in list_outputs():
        low = d.name.lower()
        if any(h in low for h in _VIRTUAL_HINTS):
            found.append(d)
    return found


_STEREO_HINTS = (
    "stereo mix", "стерео", "смешиван", "what u hear",
    "wave out mix", "stereo-mix", "loopback mix",
)


def is_stereo_mix_name(name: str) -> bool:
    low = (name or "").lower()
    return any(h in low for h in _STEREO_HINTS)


def find_stereo_mix() -> list[DeviceInfo]:
    """Входы типа Stereo Mix (если включены в системе)."""
    return [d for d in list_inputs() if is_stereo_mix_name(d.name)]


def open_sound_control_panel(tab: str = "recording") -> bool:
    """Открыть mmsys.cpl: tab='recording'|'playback'. Только Windows."""
    import subprocess
    try:
        idx = "1" if tab == "recording" else "0"
        subprocess.Popen(["control", f"mmsys.cpl,,{idx}"],
                         shell=True)
        return True
    except Exception:
        return False
