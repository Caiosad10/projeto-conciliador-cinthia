from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod

# CORRIGIDO
from .models import LancamentoExtrato
from utils.pdf_utils import extrair_texto_pdf
from utils.text_utils import parse_data, parse_decimal_br, normalizar_texto

class ExtratoParser(ABC):
    """Classe base para parsers de extrato"""
    
    @abstractmethod
    def parse(self, texto: str, arquivo: Path) -> List[LancamentoExtrato]:
        pass
    
    @classmethod
    def identificar_banco(cls, texto: str) -> Optional[str]:
        """Identifica o banco pelo texto do extrato"""
        texto = texto[:500].upper()
        if "BRADESCO" in texto:
            return "bradesco"
        elif "ITAU" in texto or "ITAÚ" in texto:
            return "itau"
        elif "SANTANDER" in texto:
            return "santander"
        elif "BB" in texto or "BANCO DO BRASIL" in texto:
            return "bb"
        return None

class BradescoParser(ExtratoParser):
    """Parser específico para extrato Bradesco"""

    def _parse_linha_completa(self, linha: str, data_atual: date) -> Optional[LancamentoExtrato]:
        """Parse de linha completa do extrato Bradesco"""
        
        # Padrões identificados
        padrao = re.compile(
            r'(\d{2}/\d{2}/\d{4})?\s*'  # Data (opcional)
            r'([A-Z\s]+?)'  # Tipo/Descrição
            r'(?:DES:\s*)?'  # Pode ter DES:
            r'([^\d]+?)?'  # Descrição adicional
            r'(\d{1,3}(?:\.\d{3})*,\d{2})?'  # Crédito (opcional)
            r'(\d{1,3}(?:\.\d{3})*,\d{2})?'  # Débito (opcional)
            r'(\d{1,3}(?:\.\d{3})*,\d{2})'  # Saldo
        )
        
        # Extrai identificadores como PC_0086, CSLR43, AMX040
        ids = re.findall(r'([A-Z]{2,}\d+[A-Z0-9]*)', linha)

    
    # Padrões de reconhecimento
    VALOR_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")
    DATA_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
    
    def parse(self, texto: str, arquivo: Path) -> List[LancamentoExtrato]:
        linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        lancamentos = []
        data_atual: Optional[date] = None
        pendentes: List[str] = []
        ordem = 1
        
        periodo = self._extrair_periodo(texto)
        
        for linha in linhas:
            if self._linha_ignorada(linha):
                continue
            
            data_linha, resto = self._extrair_data(linha)
            if data_linha:
                data_atual = data_linha
                linha = resto.strip()
                pendentes.clear()
                if not linha:
                    continue
            
            if not data_atual:
                continue
            
            valores = self._extrair_valores(linha)
            if len(valores) >= 2:
                movimento = valores[-2]
                saldo = valores[-1]
                descricao = self._montar_descricao(pendentes, linha)
                
                # Verifica se está dentro do período
                if periodo and not (periodo[0] <= data_atual <= periodo[1]):
                    pendentes.clear()
                    continue
                
                lancamento = LancamentoExtrato(
                    ordem=ordem,
                    data=data_atual,
                    descricao=descricao,
                    valor=movimento,
                    saldo=saldo,
                    documento=self._extrair_documento(linha),
                    arquivo_origem=arquivo
                )
                
                # Ignora lançamentos que não são relevantes
                if not self._ignorar_lancamento(lancamento):
                    lancamentos.append(lancamento)
                    ordem += 1
                
                pendentes.clear()
                continue
            
            if self._parece_descricao(linha):
                pendentes.append(linha)
        
        # Reordena os lançamentos
        for i, lanc in enumerate(lancamentos, 1):
            lanc.ordem = i
        
        return lancamentos
    
    def _linha_ignorada(self, linha: str) -> bool:
        termos = [
            "Folha ", "Extrato Mensal", "INCA LTDA", "Nome do usuario",
            "Data da oper", "Os dados acima", "Agencia", "Conta Total",
            "Data Lanc", "Saldo Invest", "Total ", "SALDO ANTERIOR"
        ]
        return any(t.lower() in linha.lower() for t in termos)
    
    def _extrair_periodo(self, texto: str) -> Optional[Tuple[date, date]]:
        datas = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", texto[:500])
        if len(datas) < 2:
            return None
        inicio = parse_data(datas[0])
        fim = parse_data(datas[1])
        if inicio and fim and inicio <= fim:
            return inicio, fim
        return None
    
    def _extrair_data(self, linha: str) -> Tuple[Optional[date], str]:
        match = re.match(r"^(\d{1,2}/\d{1,2}/\d{4})(?:\s+|$)(.*)$", linha)
        if not match:
            return None, linha
        return parse_data(match.group(1)), match.group(2)
    
    def _extrair_valores(self, linha: str) -> List[Decimal]:
        valores = []
        for item in self.VALOR_RE.findall(linha):
            valor = parse_decimal_br(item)
            if valor is not None:
                valores.append(valor)
        return valores
    
    def _montar_descricao(self, pendentes: List[str], linha: str) -> str:
        linha_sem_saldo = linha
        for valor in self.VALOR_RE.findall(linha)[-2:]:
            linha_sem_saldo = linha_sem_saldo.replace(valor, " ")
        
        partes = [*pendentes, linha_sem_saldo]
        descricao = " ".join(p.strip() for p in partes if p.strip())
        descricao = re.sub(r"\s+", " ", descricao)
        return descricao[:240]
    
    def _extrair_documento(self, linha: str) -> str:
        sem_valores = linha
        for valor in self.VALOR_RE.findall(linha):
            sem_valores = sem_valores.replace(valor, " ")
        numeros = re.findall(r"\b\d{4,}\b", sem_valores)
        return numeros[-1] if numeros else ""
    
    def _ignorar_lancamento(self, lancamento: LancamentoExtrato) -> bool:
        desc = lancamento.descricao.upper()
        ignore_patterns = [
            "RENTAB.INVEST", "SALDO INVEST", "TARIFA BANCARIA",
            "TRANSF PGTO PIX", "DOC/TED INTERNET"
        ]
        return any(p in desc for p in ignore_patterns)
    
    def _parece_descricao(self, linha: str) -> bool:
        if self.VALOR_RE.search(linha):
            return False
        return len(linha) > 2

def parse_extrato(caminho: str | Path) -> List[LancamentoExtrato]:
    """Função principal para parse de extrato"""
    arquivo = Path(caminho)
    texto = extrair_texto_pdf(arquivo)
    
    # Tenta identificar o banco
    banco = BradescoParser.identificar_banco(texto)
    
    if banco == "bradesco":
        parser = BradescoParser()
    else:
        # Fallback para Bradesco (formato mais comum)
        parser = BradescoParser()
    
    return parser.parse(texto, arquivo)