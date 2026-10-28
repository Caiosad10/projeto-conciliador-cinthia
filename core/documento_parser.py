# core/documento_parser.py - VERSÃO CORRIGIDA

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Set, List
from datetime import date
from decimal import Decimal

from .models import DocumentoFinanceiro, TipoDocumento
from utils.pdf_utils import extrair_texto_pdf
from utils.text_utils import normalizar_texto, parse_data, parse_decimal_br


def identificar_tipo_pdf(caminho: Path) -> TipoDocumento:
    """Identifica o tipo de documento baseado no nome do arquivo e conteúdo."""
    nome = normalizar_texto(caminho.name)
    texto = _texto_seguro(caminho)[:3000]
    texto_norm = normalizar_texto(texto)
    
    # Comprovante de pagamento
    if any(p in nome for p in ["pagto", "pagamento", "pago", "comprovante", "pix"]):
        return TipoDocumento.COMPROVANTE
    
    # Extrato
    if "extrato" in nome:
        return TipoDocumento.EXTRATO
    
    # PC (Pedido de Compra)
    if re.search(r"pc[\s_\-._]*\d", nome):
        return TipoDocumento.PC
    
    # Boleto
    if "boleto" in nome:
        return TipoDocumento.BOLETO
    
    # Fatura
    if any(p in nome for p in ["fatura", "conta", "energia"]):
        return TipoDocumento.FATURA
    
    # Guia/Taxa
    if any(p in nome for p in ["taxa", "dua", "darf", "gru", "guia", "publicacao", "dou"]):
        return TipoDocumento.GUIA
    
    # Recibo
    if any(p in nome for p in ["recibo", "recebi", "recebemos"]):
        return TipoDocumento.RECIBO
    
    # Verifica pelo conteúdo
    if any(p in texto_norm for p in ["extrato mensal", "saldo anterior", "data lancamento"]):
        return TipoDocumento.EXTRATO
    
    if any(p in texto_norm for p in ["comprovante", "pagamento efetuado", "transferencia", "ted", "doc"]):
        return TipoDocumento.COMPROVANTE
    
    if any(p in texto_norm for p in ["pedido de compra", "ordem de compra"]):
        return TipoDocumento.PC
    
    if any(p in texto_norm for p in ["linha digitavel", "codigo de barras", "ficha de compensacao"]):
        return TipoDocumento.BOLETO
    
    if any(p in texto_norm for p in ["fatura", "conta de energia", "grupo de tensao"]):
        return TipoDocumento.FATURA
    
    if any(p in texto_norm for p in ["guia de recolhimento", "documento unico de arrecadacao"]):
        return TipoDocumento.GUIA
    
    if any(p in texto_norm for p in ["recibo", "recebi", "recebemos"]):
        return TipoDocumento.RECIBO
    
    return TipoDocumento.OUTRO


def parse_documento(caminho: Path) -> DocumentoFinanceiro:
    """Extrai todas as informações relevantes de um documento PDF."""
    tipo = identificar_tipo_pdf(caminho)
    texto = _texto_seguro(caminho)
    
    return DocumentoFinanceiro(
        arquivo=caminho,
        tipo=tipo,
        valor=_extrair_valor(texto, caminho.name),
        data=_extrair_data(texto, caminho.name),
        identificadores=_extrair_identificadores(texto, caminho.name),
        favorecido=_extrair_favorecido(texto),  # <-- CORRIGIDO: _extrair_favorecido
        descricao=_extrair_descricao(texto, caminho.name),
        texto_extraido=texto
    )


def _texto_seguro(caminho: Path) -> str:
    """Extrai texto de forma segura, retornando string vazia em caso de erro"""
    try:
        return extrair_texto_pdf(caminho)
    except Exception:
        return ""


def _extrair_valor(texto: str, nome: str) -> Optional[Decimal]:
    """Extrai o valor monetário do documento."""
    padroes = [
        r"R\$\s*[\d.\s]+,\d{2}",
        r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b",
        r"\b\d+,\d{2}\b"
    ]
    
    for padrao in padroes:
        matches = re.findall(padrao, texto)
        for match in matches:
            valor = parse_decimal_br(match)
            if valor is not None:
                return valor
    
    for padrao in [r"\b\d+,\d{2}\b", r"\b\d+\.\d{2}\b"]:
        matches = re.findall(padrao, nome)
        for match in matches:
            valor = parse_decimal_br(match)
            if valor is not None:
                return valor
    
    return None


def _extrair_data(texto: str, nome: str) -> Optional[date]:
    """Extrai a data do documento."""
    padroes_contexto = [
        r"(?:data\s+de\s+debito|data\s+do\s+pagamento|pagamento|vencimento|pagar\s+ate)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:data\s+de\s+debito|data\s+do\s+pagamento|pagamento|vencimento)"
    ]
    
    for padrao in padroes_contexto:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            data = parse_data(match.group(1))
            if data:
                return data
    
    padrao_data = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    matches = re.findall(padrao_data, texto)
    for match in matches:
        data = parse_data(match)
        if data:
            return data
    
    match = re.search(padrao_data, nome)
    if match:
        data = parse_data(match.group(0))
        if data:
            return data
    
    return None


def _extrair_identificadores(texto: str, nome: str) -> List[str]:
    """Extrai identificadores como números de PC, pedido, NF, etc."""
    fonte = f"{nome}\n{texto}".upper()
    identificadores = set()
    
    padroes = [
        (r"PC\s*[:#._ -]?\s*(\d{2,})", "PC"),
        (r"PED(?:IDO)?\s*[:#._ -]?\s*(\d{3,})", "PEDIDO"),
        (r"NF\s*[:#._ -]?\s*(\d{3,})", "NF"),
        (r"BOLETO\s*[:#._ -]?\s*(\d{3,})", "BOLETO"),
        (r"DOCUMENTO\s*[:#._ -]?\s*(\d{3,})", "DOC"),
        (r"NOTA\s+FISCAL\s*[:#._ -]?\s*(\d{3,})", "NF"),
        (r"PC[_\s.]*(\d+)", "PC"),
        (r"CSLR(\d+)", "CSLR"),
        (r"AMX(\d+)", "AMX"),
        (r"NLSQRM(\d+)", "NLSQRM"),
        (r"STER(\d+)", "STER"),
        (r"MSDOS[_\s]*(\d+)", "MSDOS"),
    ]
    
    for padrao, prefixo in padroes:
        for match in re.findall(padrao, fonte, re.IGNORECASE):
            id_normalizado = _normalizar_identificador(f"{prefixo}{match}")
            if id_normalizado:
                identificadores.add(id_normalizado)
    
    for match in re.findall(r"(?<![A-Z0-9])([A-Z]{2,}\d+[A-Z0-9]*)(?![A-Z0-9])", fonte):
        identificadores.add(match)
    
    return sorted(identificadores)


def _normalizar_identificador(valor: str) -> str:
    """Normaliza identificadores para comparação."""
    valor = valor.strip().upper()
    if valor.isdigit():
        return str(int(valor))
    return valor


def _extrair_favorecido(texto: str) -> str:
    """Extrai o nome do favorecido/beneficiário."""
    texto = texto or ""

    # Valor ANTES do rótulo (extract Bradesco: "PAULO CESAR CANDIDONome:")
    # e "MARCELO ALVES FERREIRANome do favorecido:" (sem \s: não atravessa linha)
    for padrao in [
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\-]{4,60}?)\s*Nome\s+do\s+favorecido\s*:",
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\-]{4,60}?)\s*Nome\s*:",
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\-]{4,60}?)\s*Benefici[aá]rio\s*:",
    ]:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r"\s+", " ", nome)
            if _nome_favorecido_ok(nome):
                return nome[:120]

    # DEPOIS do rótulo: [^\S\n]* não atravessa quebra de linha (senão
    # "Nome do favorecido:\nAgência: 938..." virava "favorecido")
    padroes = [
        r"(?:Dados de quem recebeu\s*Nome:|Nome do favorecido):[^\S\n]*([^\n]{5,})",
        r"(?:Nome|FAVORECIDO|Benefici[aá]rio)\s*:[^\S\n]*([^\n]{5,})",
        r"(?:favorecido|beneficiario|recebedor|fornecedor)\s*:[^\S\n]*([^\n]{5,})",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r"^Nome:\s*", "", nome, flags=re.IGNORECASE)
            nome = re.sub(r"\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", nome)
            nome = re.sub(r"\s+", " ", nome).strip()
            if _nome_favorecido_ok(nome):
                return nome[:120]

    return ""


def _nome_favorecido_ok(nome: str) -> bool:
    if not nome or len(nome) < 5:
        return False
    if re.match(r"^[\d./-]+$", nome):
        return False
    # Fragmento de rótulo nunca é nome ("do favorecido:", "Empresa: INCA...")
    if ":" in nome:
        return False
    baixo = nome.lower()
    if baixo.startswith("dados de quem") or baixo in {"nome", "cnpj/cpf", "instituição destino"}:
        return False
    if "bradesco" in baixo or "telefone" in baixo:
        return False
    if any(p in baixo for p in ("agência", "agencia", "conta", "cnpj", "cpf", "empresa")):
        return False
    return True



def _limpar_descricao_capturada(desc: str) -> str:
    """Remove ruído comum colado ao valor da descrição (extração PDF)."""
    desc = desc.strip()
    desc = re.split(
        r"(?:M[íi]dia|Valor(?:\s*total)?|Tarifa|Identifica[çc][ãa]o|Documento|"
        r"Institui[çc][ãa]o|Nome|CNPJ|CPF|Motivo\s+da\s+TED|Data\s+de\s+d[ée]bito|"
        r"Autenta[çc][ãa]o)\s*:",
        desc,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    # Numeração de motivo de TED: "7 - PAGTO ALUGUEIS..." -> "PAGTO ALUGUEIS..."
    desc = re.sub(r"^\d+\s*[-–—]\s*", "", desc)
    desc = re.sub(r"\s+", " ", desc)
    return desc[:240]


def _descricao_parece_util(desc: str) -> bool:
    if not desc or len(desc.strip()) < 3:
        return False
    bruto = desc.strip()
    baixo = bruto.lower()
    if re.match(r"^e\d+", baixo):
        return False
    if re.fullmatch(r"[A-Z0-9]{20,}", bruto, flags=re.IGNORECASE):
        return False
    if re.fullmatch(r"E\d{10,}[A-Z0-9]*", bruto, flags=re.IGNORECASE):
        return False
    if re.fullmatch(r"R\$\s*[\d.,]+", bruto, flags=re.IGNORECASE):
        return False
    if re.fullmatch(r"[\d.,]+", bruto):
        return False
    if baixo in {"descrição", "descricao", "descrição:", "descricao:", "identificação", "identificacao"}:
        return False
    # Fragmento de rótulo nunca é descrição ("Autenticação", "Data de débito:")
    if bruto.endswith(":"):
        return False
    ruido = [
        "telefone", "sac", "ouvidoria", "bradesco net", "fale conosco",
        "comprovante de", "pagamento efetuado", "dados da transferência",
        "dados de quem",
        "consulte o site",
        "demais telefones",
        "cancelamentos", "autenticação", "autenticacao",
        "data de débito", "data de debito", "tarifa", "favorecido",
    ]
    return not any(p in baixo for p in ruido)


def _extrair_descricao(texto: str, nome: str) -> str:
    """
    Extrai a descrição real do comprovante/PDF.
    NÃO usa o nome do arquivo como descrição (isso quebrava os recibos).
    """
    texto = texto or ""

    # 1. Valor ANTES do rótulo (ordem comum no extract do Bradesco)
    #    Ex.: "ALUGUEL 7NLCECN04_MES 07Descrição:"
    #    TED para outro banco não tem "Descrição:" — tem "Motivo da TED:".
    for padrao in [
        r"([A-Za-z0-9][^\n]{2,100}?)\s*Descri[cç][aã]o\s*:",
        r"([A-Za-z0-9][^\n]{2,100}?)\s*Motivo\s+da\s+TED\s*:",
    ]:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            desc = _limpar_descricao_capturada(match.group(1))
            if _descricao_parece_util(desc):
                return desc

    # 2. Valor DEPOIS do rótulo ([^\S\n]* não atravessa quebra de linha —
    #    senão "Descrição:\n10/09/2026Data de débito:" virava "descrição")
    for padrao in [
        r"Descri[cç][aã]o\s*:[^\S\n]*([^\n]{3,120})",
        r"Motivo\s+da\s+TED\s*:[^\S\n]*([^\n]{3,120})",
        r"(?:Documento|DOCUMENTO)\s*:[^\S\n]*([^\n]{5,120})",
    ]:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            desc = _limpar_descricao_capturada(match.group(1))
            if _descricao_parece_util(desc):
                return desc

    # Sem descrição no campo do comprovante → vazio (recibo usará DIVIDENDO)
    return ""
