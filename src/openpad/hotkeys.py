"""Глобальные хоткеи (работают когда окно не в фокусе) через pynput."""

from __future__ import annotations


def normalize_qt_hotkey(qt: str) -> str | None:
    """'Ctrl+Shift+F1' (Qt) -> '<ctrl>+<shift>+<f1>' (pynput). None если пусто."""
    qt = (qt or "").strip()
    if not qt:
        return None
    mods = {
        "ctrl": "<ctrl>", "control": "<ctrl>",
        "alt": "<alt>", "shift": "<shift>",
        "meta": "<cmd>", "win": "<cmd>", "super": "<cmd>",
    }
    specials = {
        "space": "<space>", "esc": "<esc>", "escape": "<esc>",
        "tab": "<tab>", "enter": "<enter>", "return": "<enter>",
        "backspace": "<backspace>", "delete": "<delete>",
        "up": "<up>", "down": "<down>", "left": "<left>", "right": "<right>",
        "home": "<home>", "end": "<end>", "pageup": "<page_up>",
        "pagedown": "<page_down>", "insert": "<insert>",
    }
    parts: list[str] = []
    for raw in qt.replace(",", "+").split("+"):
        p = raw.strip().lower()
        if not p:
            continue
        if p in mods:
            parts.append(mods[p])
        elif p in specials:
            parts.append(specials[p])
        elif p.startswith("f") and p[1:].isdigit():
            parts.append(f"<{p}>")
        elif len(p) == 1:
            parts.append(p)
        else:
            return None  # неизвестно pynput
    return "+".join(parts) if parts else None


class GlobalHotkeyManager:
    """Тонкая обёртка: mapping hotkey(Qt-строка) -> callback."""

    def __init__(self):
        self._hotkeys = None
        self._mapping: dict[str, object] = {}

    @staticmethod
    def available() -> bool:
        try:
            import pynput.keyboard  # noqa: F401
            return True
        except Exception:
            return False

    def refresh(self, qt_mapping: dict[str, object]) -> tuple[int, list[str]]:
        """Перерегистрировать всё. Возвращает (ok_count, errors)."""
        self.stop()
        self._mapping = dict(qt_mapping or {})
        errors: list[str] = []
        converted: dict[str, object] = {}
        for qt_hotkey, cb in self._mapping.items():
            norm = normalize_qt_hotkey(qt_hotkey)
            if norm is None:
                errors.append(f"Не понял хоткей: {qt_hotkey}")
                continue
            if norm in converted:
                errors.append(f"Дубликат: {qt_hotkey}")
                continue
            converted[norm] = cb
        if not converted:
            return 0, errors
        try:
            from pynput import keyboard
            self._hotkeys = keyboard.GlobalHotKeys(converted)
            self._hotkeys.start()
            return len(converted), errors
        except Exception as e:
            errors.append(f"Глобальные хоткеи не завелись: {e}")
            self._hotkeys = None
            return 0, errors

    def stop(self) -> None:
        if self._hotkeys is not None:
            try:
                self._hotkeys.stop()
            except Exception:
                pass
            self._hotkeys = None
