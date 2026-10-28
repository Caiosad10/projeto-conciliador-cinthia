# core/models.py - VERSÃO COMPLETA

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from enum import Enum
from typing import Optional, List, Set


class TipoDocumento(Enum):
    EXTRATO = "extrato"
    COMPROVANTE = "comprovante"
    PC = "pc"
    BOLETO = "boleto"
    FATURA = "fatura"
    GUIA = "guia"
    RECIBO = "recibo"
    OUTRO = "outro"


class StatusConciliacao(Enum):
    CONCILIADO = "CONCILIADO"
    ATENCAO = "ATENCAO"
    DIVERGENTE = "DIVERGENTE"
    SEM_COMPROVANTE = "SEM_COMPROVANTE"
    PRECISA_RECIBO = "PRECISA_RECIBO"
    FALTANDO = "FALTANDO"


@dataclass
class LancamentoExtrato:
    """Representa um lançamento do extrato bancário"""
    ordem: int
    data: date
    descricao: str
    valor: Decimal
    saldo: Optional[Decimal] = None
    documento: str = ""
    arquivo_origem: Optional[Path] = None
    
    @property
    def valor_absoluto(self) -> Decimal:
        return abs(self.valor)
    
    @property
    def eh_entrada(self) -> bool:
        return self.valor > 0
    
    @property
    def eh_saida(self) -> bool:
        return self.valor < 0


@dataclass
class DocumentoFinanceiro:
    """Representa um documento financeiro (PC, boleto, comprovante, etc)"""
    arquivo: Path
    tipo: TipoDocumento = TipoDocumento.OUTRO
    valor: Optional[Decimal] = None
    data: Optional[date] = None
    identificadores: List[str] = field(default_factory=list)
    favorecido: str = ""
    descricao: str = ""
    texto_extraido: str = ""
    
    @property
    def nome(self) -> str:
        return self.arquivo.name
    
    @property
    def stem(self) -> str:
        return self.arquivo.stem

    def chave_duplicata(self) -> str:
        """
        Identificador forte para detectar cópia do mesmo documento.
        Só retorna chave quando há evidência segura (código/ID).
        """
        import re
        texto = (self.texto_extraido or "") + " " + " ".join(self.identificadores or [])
        # Linha digitável / código de barras (44–48 dígitos com ou sem espaços)
        m = re.search(r"\b(\d[\d\s.]{42,52}\d)\b", texto)
        if m:
            digits = re.sub(r"\D", "", m.group(1))
            if 44 <= len(digits) <= 48:
                return f"barras:{digits}"
        # Nosso número comum em boletos
        m = re.search(r"(?:Nosso\s*n[uú]mero|Nosso\s*Numero)\s*:?\s*([\d.\-/]{5,})", texto, re.I)
        if m:
            return f"nosso:{re.sub(r'\D', '', m.group(1))}"
        # ID de transação Bradesco (E + muitos dígitos/letras)
        # ID Bradesco colado a "Identificação:" no extract
        m = re.search(r"(E\d{12,}[A-Za-z0-9]*?)(?:Identifica|\s|$)", texto, re.I)
        if m:
            return f"txid:{m.group(1).upper()}"
        # Número do documento + valor + data (quando ambos existem)
        m = re.search(r"(?:N[uú]mero\s+do\s+[Dd]ocumento|N[uú]m\.?\s*[Dd]oc)\s*:?\s*([\w.\-/]{4,})", texto)
        if m and self.valor is not None and self.data is not None:
            return f"doc:{m.group(1).upper()}|{self.valor}|{self.data.isoformat()}"
        return ""


@dataclass
class ResultadoConcilacao:
    """Resultado da conciliação de um lançamento"""
    lancamento: LancamentoExtrato
    comprovante: Optional[DocumentoFinanceiro] = None
    documento_base: Optional[DocumentoFinanceiro] = None
    status: StatusConciliacao = StatusConciliacao.FALTANDO
    score_comprovante: int = 0
    score_base: int = 0
    divergencias: List[str] = field(default_factory=list)
    faltantes: List[str] = field(default_factory=list)
    ajustado_manual: bool = False
    
    @property
    def conciliado(self) -> bool:
        return self.status == StatusConciliacao.CONCILIADO
    
    @property
    def tem_comprovante(self) -> bool:
        return self.comprovante is not None
    
    @property
    def tem_documento_base(self) -> bool:
        return self.documento_base is not None


@dataclass
class Recibo:
    """Modelo para geração de recibos (metadados; formatação fica no ReciboGenerator)."""
    numero: str
    data: date
    valor: Decimal
    favorecido: str
    descricao: str
    referencia: str = ""
    arquivo_origem: Optional[Path] = None
