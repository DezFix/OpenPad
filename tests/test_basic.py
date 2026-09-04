import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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


if __name__ == "__main__":
    unittest.main()
