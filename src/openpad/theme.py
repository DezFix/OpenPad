"""Светлая/тёмная/системная темы OpenPad.

Без своего QSS Qt6 подхватывает палитру Windows (у многих — тёмная).
Режимы: system (как было из коробки, палитра ОС), light, dark.
По умолчанию — system.
"""

from __future__ import annotations

LIGHT_QSS = """
QMainWindow, QDialog, QWidget {
    background: #f5f5f5;
    font-size: 13px;
    color: #333333;
}
QMenuBar { background: #ffffff; border-bottom: 1px solid #dddddd; }
QMenuBar::item { padding: 6px 12px; color: #333333; }
QMenuBar::item:selected { background: #e0e0e0; color: #000000; }
QMenu { background: #ffffff; border: 1px solid #cccccc; color: #333333; }
QMenu::item { padding: 6px 28px 6px 12px; color: #333333; }
QMenu::item:selected { background: #e0e0e0; color: #000000; }
QToolBar { background: #ffffff; border-bottom: 1px solid #dddddd;
    spacing: 4px; padding: 4px 6px; }
QPushButton { background: #f0f0f0; border: 1px solid #cccccc;
    border-radius: 4px; padding: 5px 12px; color: #333333; }
QPushButton:hover { background: #e8e8e8; border-color: #bbbbbb; color: #000000; }
QPushButton:pressed { background: #d8d8d8; }
QPushButton:checked { background: #e6f3ff; border-color: #4a90d9; color: #1a5a9e; }
QLineEdit, QComboBox { background: #ffffff; color: #333333;
    border: 1px solid #aaaaaa; border-radius: 4px; padding: 4px 8px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #4a90d9; }
QComboBox QAbstractItemView { background: #ffffff; color: #333333;
    selection-background-color: #4a90d9; selection-color: #ffffff; }
QTableWidget { background: #ffffff; alternate-background-color: #f8f8f8;
    gridline-color: #e8e8e8; border: 1px solid #dddddd;
    selection-background-color: #4a90d9; selection-color: #ffffff; outline: none; }
QTableWidget::item { padding: 4px 8px; color: #333333; }
QHeaderView::section { background: #f0f0f0; border: none;
    border-right: 1px solid #dddddd; border-bottom: 2px solid #cccccc;
    padding: 6px 8px; font-weight: 600; color: #333333; }
QStatusBar { background: #f0f0f0; border-top: 1px solid #dddddd; color: #555555; }
QLabel { color: #333333; }
QCheckBox { color: #333333; }
QListWidget { background: #ffffff; color: #333333; border: 1px solid #dddddd;
    selection-background-color: #4a90d9; selection-color: #ffffff; outline: none; }
QSlider::groove:horizontal { height: 6px; background: #dddddd;
    border: 1px solid #bbbbbb; border-radius: 3px; }
QSlider::handle:horizontal { background: #4a90d9; width: 14px; height: 14px;
    margin: -4px 0; border-radius: 7px; border: 1px solid #357abd; }
QSlider::sub-page:horizontal { background: #4a90d9; border-radius: 3px; }
"""

DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background: #2b2b2b;
    font-size: 13px;
    color: #e0e0e0;
}
QMenuBar { background: #333333; border-bottom: 1px solid #111111; }
QMenuBar::item { padding: 6px 12px; color: #e0e0e0; }
QMenuBar::item:selected { background: #4a4a4a; color: #ffffff; }
QMenu { background: #333333; border: 1px solid #111111; color: #e0e0e0; }
QMenu::item { padding: 6px 28px 6px 12px; color: #e0e0e0; }
QMenu::item:selected { background: #4a90d9; color: #ffffff; }
QToolBar { background: #333333; border-bottom: 1px solid #111111;
    spacing: 4px; padding: 4px 6px; }
QPushButton { background: #3d3d3d; border: 1px solid #555555;
    border-radius: 4px; padding: 5px 12px; color: #e0e0e0; }
QPushButton:hover { background: #4a4a4a; border-color: #777777; }
QPushButton:pressed { background: #555555; }
QPushButton:checked { background: #1a4a7a; border-color: #4a90d9; color: #ffffff; }
QLineEdit, QComboBox { background: #3d3d3d; color: #e0e0e0;
    border: 1px solid #555555; border-radius: 4px; padding: 4px 8px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #4a90d9; }
QComboBox QAbstractItemView { background: #3d3d3d; color: #e0e0e0;
    selection-background-color: #4a90d9; selection-color: #ffffff; }
QTableWidget { background: #333333; alternate-background-color: #383838;
    gridline-color: #222222; border: 1px solid #111111;
    selection-background-color: #4a90d9; selection-color: #ffffff; outline: none; }
QTableWidget::item { padding: 4px 8px; color: #e0e0e0; }
QHeaderView::section { background: #3d3d3d; border: none;
    border-right: 1px solid #222222; border-bottom: 2px solid #111111;
    padding: 6px 8px; font-weight: 600; color: #e0e0e0; }
QStatusBar { background: #333333; border-top: 1px solid #111111; color: #aaaaaa; }
QLabel { color: #e0e0e0; }
QCheckBox { color: #e0e0e0; }
QListWidget { background: #333333; color: #e0e0e0; border: 1px solid #111111;
    selection-background-color: #4a90d9; selection-color: #ffffff; outline: none; }
QSlider::groove:horizontal { height: 6px; background: #555555;
    border: 1px solid #222222; border-radius: 3px; }
QSlider::handle:horizontal { background: #4a90d9; width: 14px; height: 14px;
    margin: -4px 0; border-radius: 7px; border: 1px solid #357abd; }
QSlider::sub-page:horizontal { background: #4a90d9; border-radius: 3px; }
"""

THEMES = {"light": LIGHT_QSS, "dark": DARK_QSS}


def apply_theme(app, name: str = "system") -> str:
    """Применить тему к QApplication. Возвращает фактическое имя."""
    if name not in ("system", "light", "dark"):
        name = "system"
    app.setStyle("Fusion")
    app.setStyleSheet("" if name == "system" else THEMES[name])
    return name
