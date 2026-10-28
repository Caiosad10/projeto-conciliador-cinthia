# tests/test_pacote_lote.py — empacotador em lote (porte do Tk).
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.models import (DocumentoFinanceiro, LancamentoExtrato,
                         ResultadoConcilacao, StatusConciliacao, TipoDocumento)
from utils.pdf_utils import empacotar_lote


def _pdf(path: Path) -> Path:
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(100, 100)
    with open(path, "wb") as f:
        w.write(f)
    return path


def _R(o, dia, comp=None, base=None, status=StatusConciliacao.CONCILIADO):
    L = LancamentoExtrato(ordem=o, data=date(2026, 9, dia),
                          descricao=f"LANC {o}", valor=Decimal("-100"))
    return ResultadoConcilacao(lancamento=L, comprovante=comp,
                               documento_base=base, status=status)


def test_lote_mescla_comp_e_base_em_ordem(tmp_path):
    c1 = DocumentoFinanceiro(arquivo=_pdf(tmp_path / "c1.pdf"),
                             tipo=TipoDocumento.COMPROVANTE)
    b1 = DocumentoFinanceiro(arquivo=_pdf(tmp_path / "b1.pdf"),
                             tipo=TipoDocumento.PC)
    c2 = DocumentoFinanceiro(arquivo=_pdf(tmp_path / "c2.pdf"),
                             tipo=TipoDocumento.COMPROVANTE)
    res = empacotar_lote([_R(2, 11, comp=c2),
                          _R(1, 10, comp=c1, base=b1),
                          _R(3, 12)], tmp_path / "dest")
    assert res["dir"].name == "Pacote_Final_Ordenado"
    assert [p.name for p in res["pdfs"]] == ["0001_20260910.pdf",
                                             "0002_20260911.pdf"]
    assert res["pulados"] == 1 and not res["erros"]
    from pypdf import PdfReader
    assert len(PdfReader(str(res["pdfs"][0])).pages) == 2  # base + comp


def test_lote_docx_vai_em_pasta_sem_converter(tmp_path):
    c = DocumentoFinanceiro(arquivo=_pdf(tmp_path / "c.pdf"),
                            tipo=TipoDocumento.COMPROVANTE)
    dx = tmp_path / "RECIBO_001.docx"
    dx.write_bytes(b"fake-docx")
    b = DocumentoFinanceiro(arquivo=dx, tipo=TipoDocumento.RECIBO)
    res = empacotar_lote([_R(1, 10, comp=c, base=b)], tmp_path / "dest")
    assert not res["pdfs"] and len(res["pastas"]) == 1
    nomes = sorted(p.name for p in res["pastas"][0].iterdir())
    assert nomes == ["01_RECIBO_001.docx", "02_c.pdf"]  # base primeiro


def test_lote_pula_sem_arquivo_e_inexistente(tmp_path):
    fant = DocumentoFinanceiro(arquivo=tmp_path / "sumiu.pdf",
                               tipo=TipoDocumento.COMPROVANTE)
    res = empacotar_lote([_R(1, 10, comp=fant), _R(2, 11)], tmp_path / "d")
    assert not res["pdfs"] and not res["pastas"] and res["pulados"] == 2
