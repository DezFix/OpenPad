"""Точка входа GUI."""

from __future__ import annotations

from .ui_main import MainWindow, create_app


def run() -> int:
    app = create_app()
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
