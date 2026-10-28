# tests/test_manual_remocao.py — remover só o comprovante preserva a base (Fase B).
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.models import (DocumentoFinanceiro, LancamentoExtrato,
                         ResultadoConcilacao, StatusConciliacao, TipoDocumento)


def _resultado(tmp_path):
    comp = DocumentoFinanceiro(arquivo=tmp_path / "c.pdf",
                               tipo=TipoDocumento.COMPROVANTE)
    base = DocumentoFinanceiro(arquivo=tmp_path / "PC_1.pdf",
                               tipo=TipoDocumento.PC)
    L = LancamentoExtrato(ordem=7, data=date(2026, 9, 10),
                          descricao="PIX FORN", valor=Decimal("-100"))
    return ResultadoConcilacao(
        lancamento=L, comprovante=comp, documento_base=base,
        status=StatusConciliacao.CONCILIADO,
        score_comprovante=100, score_base=100)


def test_remover_comp_preserva_base(tmp_path):
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    r = _resultado(tmp_path)
    w.state.reset_resultados([r])
    w.state.conciliador.resultados = [r]
    w._apply_manual(r, {"comprovante": None, "base": r.documento_base})
    assert r.comprovante is None
    assert r.documento_base is not None, "base não pode sumir junto"
    assert r.status == StatusConciliacao.SEM_COMPROVANTE
    assert r.faltantes == ["Comprovante"]
    assert r.ajustado_manual is True
    w.close()


def test_remover_comp_e_base_fica_sem_nada(tmp_path):
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    r = _resultado(tmp_path)
    w.state.reset_resultados([r])
    w.state.conciliador.resultados = [r]
    w._apply_manual(r, {"comprovante": None, "base": None})
    assert r.comprovante is None and r.documento_base is None
    assert r.status == StatusConciliacao.SEM_COMPROVANTE
    assert r.faltantes == ["Comprovante e Documento Base"]
    w.close()
