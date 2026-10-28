from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional, Set, List

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos, caracteres especiais e espaços extras.
    Exemplo: "João da Silva" -> "joao da silva"
    """
    if not texto:
        return ""
    
    # Remove acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    
    # Minúsculas
    texto = texto.lower()
    
    # Remove caracteres especiais mantendo letras, números e espaços
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    
    # Remove espaços extras
    texto = re.sub(r"\s+", " ", texto)
    
    return texto.strip()

def parse_data(texto: str) -> Optional[date]:
    """
    Extrai data de um texto em formatos comuns.
    Suporta: DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY, YYYY-MM-DD
    """
    if not texto:
        return None
    
    # Tenta DD/MM/YYYY ou DD/MM/YY
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto)
    if match:
        dia, mes, ano = (int(x) for x in match.groups())
        if ano < 100:
            ano += 2000
        try:
            return date(ano, mes, dia)
        except ValueError:
            pass
    
    # Tenta YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", texto)
    if match:
        ano, mes, dia = (int(x) for x in match.groups())
        try:
            return date(ano, mes, dia)
        except ValueError:
            pass
    
    return None

def parse_decimal_br(valor: str) -> Optional[Decimal]:
    """
    Converte string com formato brasileiro (1.234,56) para Decimal.
    Também aceita formato americano (1234.56)
    """
    if not valor:
        return None
    
    # Remove caracteres não numéricos exceto vírgula e ponto
    limpo = re.sub(r"[^\d,.-]", "", valor).strip()
    if not limpo:
        return None
    
    # Se tem vírgula, é formato brasileiro
    if "," in limpo:
        # Remove pontos de milhar e troca vírgula por ponto
        limpo = limpo.replace(".", "").replace(",", ".")
    
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return None

def format_decimal_br(valor: Optional[Decimal]) -> str:
    """Formata Decimal para string no formato brasileiro (1.234,56)"""
    if valor is None:
        return ""
    
    # Formata com 2 casas decimais
    formatado = f"{valor:.2f}"
    
    # Separa parte inteira e decimal
    if "." in formatado:
        inteiro, decimal = formatado.split(".")
        
        # Adiciona pontos de milhar
        inteiro_formatado = ""
        for i, char in enumerate(reversed(inteiro)):
            if i > 0 and i % 3 == 0:
                inteiro_formatado = "." + inteiro_formatado
            inteiro_formatado = char + inteiro_formatado
        
        return f"{inteiro_formatado},{decimal}"
    
    return formatado

def format_data(data: Optional[date]) -> str:
    """Formata data para DD/MM/YYYY"""
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")

def similaridade_texto(texto1: str, texto2: str) -> float:
    """
    Calcula similaridade entre dois textos usando Jaccard.
    Retorna valor entre 0 e 1.
    """
    if not texto1 or not texto2:
        return 0.0
    
    palavras1 = set(normalizar_texto(texto1).split())
    palavras2 = set(normalizar_texto(texto2).split())
    
    if not palavras1 or not palavras2:
        return 0.0
    
    intersecao = len(palavras1 & palavras2)
    uniao = len(palavras1 | palavras2)
    
    return intersecao / uniao if uniao > 0 else 0.0

def extrair_palavras_chave(texto: str) -> Set[str]:
    """Extrai palavras-chave relevantes de um texto"""
    texto_norm = normalizar_texto(texto)
    palavras = texto_norm.split()
    
    # Filtra palavras com mais de 3 caracteres e que não são comuns
    stopwords = {
        "para", "com", "sem", "por", "uma", "dos", "das", "pelo", "pela",
        "entre", "sobre", "apos", "antes", "durante", "mediante"
    }
    
    return {p for p in palavras if len(p) >= 4 and p not in stopwords}