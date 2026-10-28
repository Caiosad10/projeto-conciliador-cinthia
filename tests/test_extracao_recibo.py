# tests/test_extracao_recibo.py — regressão dos 2 casos reais (Bradesco net
# empresa): Marcelo (Descrição colada + \n) e Claudia (TED sem "Descrição:").
from core.documento_parser import _extrair_descricao, _extrair_favorecido
from core.models import (DocumentoFinanceiro, LancamentoExtrato,
                         TipoDocumento)
from core.recibo_generator import ReciboGenerator
from datetime import date
from decimal import Decimal
from pathlib import Path

# Textos REAIS extraídos (pypdf) dos comprovantes de setembro/2026.
MARCELO = (
    "SAC - Serviço de\nApoio ao Cliente\nTX COND RIVELAREDescrição:\n"
    "10/09/2026Data de débito:\nR$ 3.000,00Valor\n"
    "MARCELO ALVES FERREIRANome do favorecido:\n"
    "Agência: 938 | Conta: 115304-8 | Tipo: Conta-CorrenteConta de crédito:\n"
    "INCA LTDA | CNPJ: 008.655.605/0001-22Empresa:\n"
    "Comprovante de Transação Bancária\nAutenticação\n"
)
CLAUDIA = (
    "SAC - Serviço de\nApoio ao Cliente\n09/09/2026Data de débito:\n"
    "R$ 1.000,00Valor total:\nIsentoTarifa:\nR$ 1.000,00Valor\n"
    "7 - PAGTO ALUGUEIS E TX CONDOMINIOMotivo da TED:\n"
    "CONTA-CORRENTE INDIVIDUALTipo de conta:\n"
    "Banco: 341 - ITAU UNIBANCO S.A. | Agência: 7162 | Conta: 256254Conta de crédito:\n"
    "423.808.202-87CPF:\nCLAUDIA LILIA BEGOT LINONome do favorecido:\n"
    "INCA LTDA | CNPJ: 008.655.605/0001-22Empresa:\n"
    "N° de controle: 406619755578214837 |  1786114Documento:\nAutenticação\n"
)


def test_marcelo_descricao_nao_vira_data_debito():
    assert _extrair_descricao(MARCELO, "") == "TX COND RIVELARE"


def test_marcelo_favorecido():
    assert _extrair_favorecido(MARCELO) == "MARCELO ALVES FERREIRA"


def test_claudia_ted_usa_motivo_da_ted():
    assert _extrair_descricao(CLAUDIA, "") == "PAGTO ALUGUEIS E TX CONDOMINIO"


def test_claudia_favorecido():
    assert _extrair_favorecido(CLAUDIA) == "CLAUDIA LILIA BEGOT LINO"


def test_nunca_autenticacao_nem_rotulos():
    for texto in (MARCELO, CLAUDIA):
        desc = _extrair_descricao(texto, "")
        assert "Autenticação" not in desc
        assert "débito" not in desc.lower()
        assert not desc.endswith(":")


def _doc(texto, fav="FABRICA XYZ"):
    return DocumentoFinanceiro(
        arquivo=Path("/tmp/x.pdf"), tipo=TipoDocumento.COMPROVANTE,
        valor=Decimal("1000"), data=date(2026, 9, 9),
        favorecido=fav, texto_extraido=texto)


def test_recibo_gerado_marcelo():
    g = ReciboGenerator()
    L = LancamentoExtrato(ordem=68, data=date(2026, 9, 10),
                          descricao="", valor=Decimal("-3000"))
    desc = g._extrair_descricao(_doc(MARCELO), L, "MARCELO ALVES FERREIRA")
    assert desc == "TX COND RIVELARE"


def test_recibo_gerado_claudia_sem_favorecido_parseado():
    # sem favorecido pré-parseado (docx avulso) → still extrai direto do texto
    g = ReciboGenerator()
    L = LancamentoExtrato(ordem=49, data=date(2026, 9, 9),
                          descricao="", valor=Decimal("-1000"))
    doc = _doc(CLAUDIA, fav="")
    favor = g._extrair_favorecido(doc, L)
    assert "CLAUDIA" in favor.upper()
    assert ":" not in favor


def test_divergencia_data_apenas_aviso():
    # aviso ignorável no manual: >2 dias gera divergência, status NÃO muda
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app_qt.main_window import MainWindow
    from core.models import ResultadoConcilacao, StatusConciliacao
    QApplication.instance() or QApplication([])
    w = MainWindow()
    L = LancamentoExtrato(ordem=5, data=date(2026, 9, 5),
                          descricao="PIX X", valor=Decimal("-100"))
    comp = DocumentoFinanceiro(arquivo=Path("/tmp/c.pdf"),
                               tipo=TipoDocumento.COMPROVANTE,
                               valor=Decimal("100"), data=date(2026, 9, 20))
    r = ResultadoConcilacao(lancamento=L)
    w.state.reset_resultados([r])
    w.state.conciliador.resultados = [r]
    w._apply_manual(r, {"comprovante": comp, "base": None})
    assert r.status == StatusConciliacao.PRECISA_RECIBO  # aviso, não bloqueio
    assert any("Data:" in d for d in r.divergencias)
    assert any("15 dias" in d for d in r.divergencias)
    # <=2 dias: sem aviso
    comp.data = date(2026, 9, 6)
    r2 = ResultadoConcilacao(lancamento=L)
    w.state.reset_resultados([r2])
    w._apply_manual(r2, {"comprovante": comp, "base": None})
    assert not any("Data:" in d for d in r2.divergencias)
    w.close()
