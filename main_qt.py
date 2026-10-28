# main_qt.py — bootstrap PySide6 (identidade em app_qt/theme.py + app_qt/qss.py)
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from app_qt.main_window import MainWindow
from app_qt.qss import QSS

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Conciliador INCA")
    app.setApplicationVersion("2.0.0")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.showMaximized()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
