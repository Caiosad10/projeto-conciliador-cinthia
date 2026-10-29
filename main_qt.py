# main_qt.py — bootstrap PySide6 (identidade em app_qt/theme.py + app_qt/qss.py)
from __future__ import annotations
import io
import sys
from pathlib import Path

# PyInstaller --windowed: stdout pode ser None no .exe sem console → print quebraria
if sys.stdout is None:
    sys.stdout = sys.stderr = io.StringIO()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication
from app_qt.main_window import MainWindow
from app_qt.qss import QSS


def _base_dir() -> Path:
    """Pasta-base de recursos: projeto (dev) ou extração do .exe (frozen)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Conciliador INCA")
    app.setApplicationVersion("2.0.0")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(QSS)
    icone = _base_dir() / "assets" / "inca.ico"
    if icone.exists():
        app.setWindowIcon(QIcon(str(icone)))
    win = MainWindow()
    if icone.exists():
        win.setWindowIcon(QIcon(str(icone)))
    win.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
