# tests/test_smoke_core.py — smoke sem UI (nao quebra Tkinter atual)
from pathlib import Path
from core.conciliador import Conciliador
from core.models import StatusConciliacao

def test_imports():
    c = Conciliador()
    assert c is not None

def test_status_enum():
    assert StatusConciliacao.CONCILIADO.value == "CONCILIADO"
    assert StatusConciliacao.PRECISA_RECIBO.value == "PRECISA_RECIBO"
