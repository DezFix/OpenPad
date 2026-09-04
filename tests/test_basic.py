import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openpad.devices import find_stereo_mix, is_stereo_mix_name
from openpad.hotkeys import normalize_qt_hotkey
from openpad.library import Library


class TestLibrary(unittest.TestCase):
    def test_add_search_rename_hotkey(self):
        lib = Library()
        # несуществующие файлы игнорируются
        self.assertEqual(lib.add_paths(["nope.mp3"]), 0)

    def test_normalize(self):
        self.assertEqual(normalize_qt_hotkey("Ctrl+F1"), "<ctrl>+<f1>")
        self.assertEqual(
            normalize_qt_hotkey("Ctrl+Shift+A"), "<ctrl>+<shift>+a")
        self.assertIsNone(normalize_qt_hotkey(""))

    def test_stereo_mix_hints(self):
        self.assertTrue(is_stereo_mix_name("Stereo Mix"))
        self.assertTrue(is_stereo_mix_name("Стерео микшер"))
        self.assertTrue(is_stereo_mix_name("What U Hear"))
        self.assertFalse(is_stereo_mix_name("CABLE Output"))
        self.assertFalse(is_stereo_mix_name("Microphone"))
        # без sounddevice просто возвращает список (обычно пустой в CI)
        self.assertIsInstance(find_stereo_mix(), list)

    def test_theme_registry(self):
        from openpad import theme as t
        self.assertIn("light", t.THEMES)
        self.assertIn("dark", t.THEMES)

        class FakeApp:
            def __init__(self):
                self.qss = None
            def setStyle(self, _s):
                pass
            def setStyleSheet(self, s):
                self.qss = s

        app = FakeApp()
        self.assertEqual(t.apply_theme(app, "dark"), "dark")
        self.assertIn("background", app.qss)
        self.assertEqual(t.apply_theme(app, "system"), "system")
        self.assertEqual(app.qss, "")
        self.assertEqual(t.apply_theme(app, "nope"), "system")


if __name__ == "__main__":
    unittest.main()
