# tests/test_gate_data.py — gate anti-roubo de data (caso Almany R$200 dia 16 x comp 29/30).
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.conciliador import Conciliador
from core.models import (DocumentoFinanceiro, LancamentoExtrato, StatusConciliacao,
                         TipoDocumento)


def _lanc(dia: int, descricao: str = "PIX ENVIADO DES: ALMANY BEZERRA DE MEL") -> LancamentoExtrato:
    return LancamentoExtrato(ordem=1, data=date(2026, 9, dia), descricao=descricao,
                             valor=Decimal("-200.00"))


def _doc(nome: str, dia: int | None, tipo=TipoDocumento.COMPROVANTE,
         favorecido: str = "ALMANY BEZERRA DE MELO") -> DocumentoFinanceiro:
    return DocumentoFinanceiro(
        arquivo=Path(f"/tmp/{nome}"), tipo=tipo, valor=Decimal("200.00"),
        data=date(2026, 9, dia) if dia else None, favorecido=favorecido)


def test_gate_rejeita_comp_13_dias_futuro():
    c = Conciliador()
    assert c._calcular_score(_lanc(16), _doc("comp29.pdf", 29)) == 0


def test_gate_aceita_mesmo_dia():
    c = Conciliador()
    assert c._calcular_score(_lanc(16), _doc("comp16.pdf", 16)) >= 100


def test_gate_tolera_2_dias_futuro_e_7_passado():
    c = Conciliador()
    assert c._calcular_score(_lanc(16), _doc("a.pdf", 18)) > 0
    assert c._calcular_score(_lanc(16), _doc("b.pdf", 9)) > 0
    assert c._calcular_score(_lanc(16), _doc("c.pdf", 8)) == 0


def test_gate_doc_sem_data_neutro():
    c = Conciliador()
    assert c._calcular_score(_lanc(16), _doc("sdata.pdf", None)) > 0


def test_gate_nao_afeta_bases_antigas():
    c = Conciliador()
    fatura = _doc("FATURA_MES08.pdf", None, tipo=TipoDocumento.FATURA)
    fatura.data = date(2026, 8, 5)
    assert c._calcular_score(_lanc(16), fatura) > 0


def test_gate_id_forte_escapa():
    c = Conciliador()
    d = _doc("PAGTO PC_290_ALMANY.PDF", 29)
    L = _lanc(16, "PAGTO PC_290 ALMANY")
    assert c._calcular_score(L, d) > 0


def test_match_nao_rouba_comps_futuros():
    c = Conciliador()
    docs = [_doc("comp29.pdf", 29), _doc("comp30.pdf", 30),
            _doc("comp16a.pdf", 16), _doc("comp16b.pdf", 16)]
    L16a = LancamentoExtrato(ordem=1, data=date(2026, 9, 16),
                             descricao="PIX ALMANY 16/09 1305156", valor=Decimal("-200"))
    L16b = LancamentoExtrato(ordem=2, data=date(2026, 9, 16),
                             descricao="PIX ALMANY 16/09 1306373", valor=Decimal("-200"))
    L29 = LancamentoExtrato(ordem=3, data=date(2026, 9, 29),
                            descricao="PIX ALMANY 29/09 1810599", valor=Decimal("-200"))
    c.lancamentos = [L16a, L16b, L29]
    c.documentos = docs
    res = c.conciliar()
    por_ordem = {r.lancamento.ordem: r for r in res}
    # dia 16 casa com comps do dia 16, nunca com 29/30
    for o in (1, 2):
        comp = por_ordem[o].comprovante
        assert comp is not None and comp.data.day == 16, comp
    # comp 29 sobra para o L29
    assert por_ordem[3].comprovante is not None
    assert por_ordem[3].comprovante.data.day == 29


def test_divergencia_data_em_precisa_recibo():
    c = Conciliador()
    L = _lanc(16)
    d = _doc("manual.pdf", 29)
    r = c._criar_resultado(L, d, None, 100, 0)
    assert r.status == StatusConciliacao.PRECISA_RECIBO
    assert any(str(D).startswith("Data:") for D in r.divergencias), r.divergencias
