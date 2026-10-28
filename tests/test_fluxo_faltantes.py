# tests/test_fluxo_faltantes.py — regressão do cenário real do usuário:
# restaurar -> adicionar pasta nova -> Round 2 -> gerar recibos -> fechar -> reabrir.
# Nada além do esperado pode mudar; arquivo ausente nunca fica verde.
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import date
from decimal import Decimal
from pathlib import Path

from app_qt.session_store import montar_payload
from core.models import (DocumentoFinanceiro, LancamentoExtrato,
                         ResultadoConcilacao, StatusConciliacao, TipoDocumento)


def _L(o, dia, v="-200"):
    return LancamentoExtrato(ordem=o, data=date(2026, 9, dia),
                             descricao=f"PIX FORN {dia}/09 {o}", valor=Decimal(v))


def _D(tmp: Path, nome: str, dia: int, tipo=TipoDocumento.COMPROVANTE):
    p = tmp / nome
    p.write_bytes(b"%PDF-1.4 fake")
    return DocumentoFinanceiro(arquivo=p, tipo=tipo, valor=Decimal("200"),
                               data=date(2026, 9, dia), favorecido="FORN")


def _nova_janela_com_sessao(tmp: Path):
    """MainWindow com sessão: L1 manual CONCILIADO (comp+PC externo),
    L2 auto PRECISA_RECIBO sem base, L3 vazio."""
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    pc_ext = tmp / "externo" / "PC_0001_FORN.pdf"
    pc_ext.parent.mkdir(parents=True, exist_ok=True)
    pc_ext.write_bytes(b"%PDF-1.4 fake")
    comp1 = _D(tmp, "comp01.pdf", 10)
    base1 = DocumentoFinanceiro(arquivo=pc_ext, tipo=TipoDocumento.PC,
                                valor=Decimal("200"), data=date(2026, 9, 10))
    r1 = ResultadoConcilacao(lancamento=_L(1, 10), comprovante=comp1,
                             documento_base=base1, status=StatusConciliacao.CONCILIADO,
                             score_comprovante=100, score_base=100, ajustado_manual=True)
    comp2 = _D(tmp, "comp02.pdf", 11)
    r2 = ResultadoConcilacao(lancamento=_L(2, 11), comprovante=comp2,
                             status=StatusConciliacao.PRECISA_RECIBO,
                             score_comprovante=100, faltantes=["Documento Base (PC/Boleto/Fatura)"])
    r3 = ResultadoConcilacao(lancamento=_L(3, 12),
                             status=StatusConciliacao.SEM_COMPROVANTE,
                             faltantes=["Comprovante", "Comprovante e Documento Base"])
    ext = tmp / "EXTRATO.PDF"
    ext.write_bytes(b"%PDF-1.4 fake")
    w.state.extrato_path = ext
    w.state.extrato_carregado = True
    w.state.documentos_carregados = True
    w.state.pastas_docs = [tmp]
    w.state.conciliador.documentos = [comp1, base1, comp2]
    w.state.reset_resultados([r1, r2, r3])
    w.state.conciliador.resultados = list(w.state.resultados)
    w.state.ordens_recibo = {2}
    return w, ext


def test_fluxo_r2_nao_mexe_manual(tmp_path):
    """Adicionar pasta + Round 2: manual intacto; só vazios preenchem."""
    from core.conciliador import Conciliador
    w, _ = _nova_janela_com_sessao(tmp_path)
    novo = _D(tmp_path, "comp03_novo.pdf", 12)  # faltante que chegou
    c = Conciliador()
    c.lancamentos = [r.lancamento for r in w.state.resultados]
    c.documentos = list(w.state.conciliador.documentos) + [novo]
    antes = {r.lancamento.ordem: (r.comprovante, r.documento_base, r.status)
             for r in w.state.resultados}
    novos = c.reconciliar_pendentes(list(w.state.resultados))
    dep = {r.lancamento.ordem: r for r in novos}
    assert dep[1] is w.state.resultados[0]  # manual: mesmo objeto
    assert (dep[1].comprovante, dep[1].documento_base, dep[1].status) == antes[1]
    assert dep[2].comprovante is antes[2][0]  # auto: comp mantido
    assert dep[3].comprovante is not None  # vazio: preencheu
    assert dep[3].comprovante.arquivo.name == "comp03_novo.pdf"
    w.close()


def test_restore_arquivo_ausente_nao_fica_verde(tmp_path):
    """PC externo apagado: restore marca ausente E derruba o verde."""
    w, ext = _nova_janela_com_sessao(tmp_path)
    (tmp_path / "externo" / "PC_0001_FORN.pdf").unlink()
    dados = montar_payload(w.state)
    w.close()
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w2 = MainWindow()
    from unittest.mock import patch
    lancs = [r.lancamento for r in w.state.resultados]
    with patch("app_qt.main_window.parse_extrato", return_value=lancs):
        out = w2._restaurar_sessao(ext, dados)
    r1 = next(r for r in out["resultados"] if r.lancamento.ordem == 1)
    assert r1.documento_base is None
    assert any("Arquivo ausente" in f for f in r1.faltantes)
    assert r1.status != StatusConciliacao.CONCILIADO, r1.status
    w2.close()


def test_recibo_gerado_sobrevive_reopen(tmp_path):
    """Gerar recibo -> fechar -> reabrir: base religa, sem 'Arquivo ausente'."""
    w, ext = _nova_janela_com_sessao(tmp_path)
    dest = tmp_path / "recibos_out"
    from core.recibo_generator import gerar_recibos_para_faltantes
    marc = [r for r in w.state.resultados if r.lancamento.ordem in w.state.ordens_recibo]
    arqs = gerar_recibos_para_faltantes(marc, dest)
    assert len(arqs) == 1 and arqs[0].exists()
    r2 = next(r for r in w.state.resultados if r.lancamento.ordem == 2)
    assert r2.status == StatusConciliacao.CONCILIADO and r2.documento_base is not None
    dados = montar_payload(w.state)
    base_ref = dados["resultados"][1]["base"]
    assert base_ref and Path(base_ref).exists()  # arquivo existe em disco
    w.close()
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w2 = MainWindow()
    from unittest.mock import patch
    lancs = [r.lancamento for r in w.state.resultados]
    with patch("app_qt.main_window.parse_extrato", return_value=lancs):
        out = w2._restaurar_sessao(ext, dados)
    r2b = next(r for r in out["resultados"] if r.lancamento.ordem == 2)
    assert r2b.documento_base is not None, "recibo deveria religar"
    assert not any("Arquivo ausente" in f for f in r2b.faltantes)
    assert r2b.status == StatusConciliacao.CONCILIADO
    w2.close()

