"""Библиотека звуков: модель + персистентность (без Qt, тестируемо)."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .audio_loader import get_duration_str, is_supported


@dataclass
class Track:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    path: str = ""
    hotkey: str = ""
    volume: int = 100
    category: str = "Основная"
    duration: str = "?:??"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Track":
        return Track(
            id=str(d.get("id") or uuid.uuid4().hex[:8]),
            name=str(d.get("name", "")),
            path=str(d.get("path", "")),
            hotkey=str(d.get("hotkey", "")),
            volume=int(d.get("volume", 100)),
            category=str(d.get("category", "Основная")),
            duration=str(d.get("duration", "?:??")),
        )


def default_data_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        return base / "OpenPad" / "library.json"
    return Path.home() / ".config" / "openpad" / "library.json"


class Library:
    def __init__(self):
        self.tracks: list[Track] = []

    # -- запросы ---------------------------------------------------------
    @property
    def categories(self) -> list[str]:
        cats = sorted({t.category or "Основная" for t in self.tracks})
        return cats or ["Основная"]

    def search(self, query: str, category: str | None = None) -> list[Track]:
        q = (query or "").strip().lower()
        out = []
        for t in self.tracks:
            if category and category != "Все" and t.category != category:
                continue
            if q and q not in t.name.lower() and q not in Path(t.path).name.lower():
                continue
            out.append(t)
        return out

    def by_id(self, track_id: str) -> Track | None:
        for t in self.tracks:
            if t.id == track_id:
                return t
        return None

    def hotkey_map(self) -> dict[str, str]:
        """hotkey -> track_id (только непустые, первые wins)."""
        m: dict[str, str] = {}
        for t in self.tracks:
            if t.hotkey and t.hotkey not in m:
                m[t.hotkey] = t.id
        return m

    # -- мутации ----------------------------------------------------------
    def add_paths(self, paths: list[str | Path],
                  category: str = "Основная") -> int:
        existing = {Path(t.path).resolve().__str__().lower()
                    for t in self.tracks}
        added = 0
        for p in paths:
            pp = Path(p)
            if not pp.is_file() or not is_supported(pp):
                continue
            key = pp.resolve().__str__().lower()
            if key in existing:
                continue
            self.tracks.append(Track(
                name=pp.stem,
                path=str(pp),
                category=category or "Основная",
                duration=get_duration_str(pp),
            ))
            existing.add(key)
            added += 1
        return added

    def add_folder(self, folder: str | Path,
                   category: str | None = None) -> int:
        folder = Path(folder)
        cat = category or folder.name or "Основная"
        files: list[Path] = []
        for root, _, fnames in os.walk(folder):
            for fn in sorted(fnames):
                fp = Path(root) / fn
                if is_supported(fp):
                    files.append(fp)
        return self.add_paths(files, category=cat)

    def rename(self, track_id: str, name: str) -> bool:
        t = self.by_id(track_id)
        if t and name.strip():
            t.name = name.strip()
            return True
        return False

    def set_hotkey(self, track_id: str, hotkey: str) -> bool:
        t = self.by_id(track_id)
        if not t:
            return False
        t.hotkey = hotkey.strip()
        return True

    def set_volume(self, track_id: str, volume: int) -> bool:
        t = self.by_id(track_id)
        if not t:
            return False
        t.volume = max(0, min(100, int(volume)))
        return True

    def set_category(self, track_id: str, category: str) -> bool:
        t = self.by_id(track_id)
        if not t or not category.strip():
            return False
        t.category = category.strip()
        return True

    def remove_ids(self, ids: list[str]) -> int:
        before = len(self.tracks)
        dead = set(ids)
        self.tracks = [t for t in self.tracks if t.id not in dead]
        return before - len(self.tracks)

    def prune_missing(self) -> int:
        before = len(self.tracks)
        self.tracks = [t for t in self.tracks if Path(t.path).is_file()]
        return before - len(self.tracks)

    # -- persistence -------------------------------------------------------
    def to_list(self) -> list[dict]:
        return [t.to_dict() for t in self.tracks]

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else default_data_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_list(), ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return p

    def load(self, path: str | Path | None = None) -> int:
        p = Path(path) if path else default_data_path()
        if not p.is_file():
            return 0
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return 0
        tracks = []
        for d in data if isinstance(data, list) else []:
            try:
                t = Track.from_dict(d)
                if Path(t.path).is_file():
                    tracks.append(t)
            except Exception:
                continue
        self.tracks = tracks
        return len(self.tracks)
