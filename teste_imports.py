# teste_imports.py — smoke de imports (marcadores ASCII: console cp1252 quebra em emoji)
# Nota: valida o app PySide6 (app_qt) offscreen — o Tk antigo foi removido (out/2026).
import os
import sys

print("=== TESTANDO IMPORTS ===\n")

_OK = "[OK]  "
_FAIL = "[FALHA]"

try:
    from core.models import LancamentoExtrato, DocumentoFinanceiro
    print(f"{_OK}core.models OK")
except ImportError as e:
    print(f"{_FAIL}core.models: {e}")

try:
    from core.extrato_parser import parse_extrato
    print(f"{_OK}core.extrato_parser OK")
except ImportError as e:
    print(f"{_FAIL}core.extrato_parser: {e}")

try:
    from core.documento_parser import parse_documento
    print(f"{_OK}core.documento_parser OK")
except ImportError as e:
    print(f"{_FAIL}core.documento_parser: {e}")

try:
    from core.conciliador import Conciliador
    print(f"{_OK}core.conciliador OK")
except ImportError as e:
    print(f"{_FAIL}core.conciliador: {e}")

try:
    from utils.pdf_utils import extrair_texto_pdf
    print(f"{_OK}utils.pdf_utils OK")
except ImportError as e:
    print(f"{_FAIL}utils.pdf_utils: {e}")

try:
    from utils.text_utils import normalizar_texto
    print(f"{_OK}utils.text_utils OK")
except ImportError as e:
    print(f"{_FAIL}utils.text_utils: {e}")

try:
    from app_qt.main_window import MainWindow
    from app_qt.qss import QSS
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.close()
    print(f"{_OK}app_qt.main_window OK (janela abre/fecha)")
except Exception as e:  # noqa: BLE001
    print(f"{_FAIL}app_qt.main_window: {e}")

print("\n=== FIM ===")