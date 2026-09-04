import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openpad.devices import (find_stereo_mix, find_virtual_cables,
                           is_stereo_mix_name, is_virtual_cable_name)
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
        self.assertIsInstance(find_virtual_cables(), list)

    def test_virtual_cable_hints(self):
        self.assertTrue(is_virtual_cable_name("CABLE Input (VB-Audio)"))
        self.assertTrue(is_virtual_cable_name("OpenPad Virtual Mic"))
        self.assertFalse(is_virtual_cable_name("Microphone (Realtek)"))
        self.assertFalse(is_virtual_cable_name("Stereo Mix"))

    def test_engine_position_unknown(self):
        from openpad.audio_engine import DualOutputEngine
        eng = DualOutputEngine()
        self.assertFalse(eng.is_playing("x"))
        self.assertEqual(eng.get_position("x"), (0, 0, 44100))
        eng.stop_all()  # не падает на пустом

    def test_engine_voice_finishes(self):
        import time
        import numpy as np
        from openpad.audio_engine import DualOutputEngine
        eng = DualOutputEngine()
        eng._dummy = True  # без железа: таймер вместо стрима
        samples = np.zeros((4410, 2), dtype=np.float32)  # 0.1 c
        self.assertEqual(eng.play("t1", samples, 44100), "started")
        self.assertTrue(eng.is_playing("t1"))
        time.sleep(0.4)
        self.assertFalse(eng.is_playing("t1"))
        self.assertFalse(eng.any_playing())

    def test_cable_setup_helpers(self):
        import tempfile
        from pathlib import Path
        from openpad import cable_setup as cs
        self.assertTrue(cs.CABLE_URL.startswith("https://"))
        self.assertTrue(cs.installer_candidates())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "nested").mkdir()
            exe_name = cs.installer_candidates()[0]
            (root / "nested" / exe_name).write_bytes(b"fake")
            found = cs.find_installer(root)
            self.assertIsNotNone(found)
            self.assertTrue(str(found).endswith(exe_name))
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(cs.find_installer(Path(td)))
        self.assertIsInstance(cs.is_admin(), bool)

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
