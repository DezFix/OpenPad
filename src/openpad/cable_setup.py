"""Установка VB-Cable в 1 клик (официальный пак с vb-audio.com).

VB-Cable — donationware от VB-Audio (vb-audio.com/Cable). Вендор явно
разрешает распространять пак вместе с приложением при указании origin
и donationware-модели, поэтому мы качаем пак с официального сайта
и запускаем тихую установку (ключи -i -h). Диалог согласия Windows
на установку драйвера скрыть нельзя — это системный промпт.
"""

from __future__ import annotations

import os
import platform
import urllib.request
import zipfile
from pathlib import Path

CABLE_URL = ("https://download.vb-audio.com/Download_CABLE/"
             "VBCABLE_Driver_Pack45.zip")
CABLE_HOMEPAGE = "https://vb-audio.com/Cable/"


def installer_candidates() -> list[str]:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return ["VBCABLE_Setup_arm64.exe", "VBCABLE_Setup_x64.exe"]
    if machine in ("amd64", "x86_64", "em64t"):
        return ["VBCABLE_Setup_x64.exe"]
    return ["VBCABLE_Setup.exe"]


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def download_pack(dest: Path, progress=None) -> Path:
    """Скачать zip-пак. progress(done_bytes, total_bytes) — опционально."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    def hook(blocks: int, block_size: int, total: int):
        if progress is not None:
            progress(blocks * block_size, total)

    urllib.request.urlretrieve(CABLE_URL, str(dest),
                               reporthook=hook if progress else None)
    return dest


def extract_pack(zip_path: str | Path, target_dir: str | Path) -> Path:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target)
    return target


def find_installer(root: str | Path) -> Path | None:
    """Найти подходящий setup-exe в распакованном паке."""
    root = Path(root)
    for name in installer_candidates():
        hit = next(root.rglob(name), None)
        if hit is not None:
            return hit
    return None


def run_installer_elevated(exe: str | Path) -> bool:
    """Тихая установка (-i -h). False — только если не вышло даже запустить."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        import subprocess
        if is_admin():
            subprocess.run([str(exe), "-i", "-h"], check=False)
            return True
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(exe), "-i -h", None, 1)
        return int(rc) > 32
    except Exception:
        return False
