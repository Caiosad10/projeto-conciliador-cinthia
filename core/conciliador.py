from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Set
from collections import defaultdict
import re

# CORRIGIDO: imports relativos
from .models import (
    LancamentoExtrato, DocumentoFinanceiro, ResultadoConcilacao,
    StatusConciliacao, TipoDocumento
)
from .documento_parser import parse_documento, identificar_tipo_pdf
from utils.text_utils import normalizar_texto, format_data

class Conciliador:
    """Classe principal para conciliação"""
    
    def __init__(self):
        self.lancamentos: List[LancamentoExtrato] = []
        self.documentos: List[DocumentoFinanceiro] = []
        self.resultados: List[ResultadoConcilacao] = []
        
        # Controle de documentos usados
        self.comprovantes_usados: Set[Path] = set()
        self.bases_usadas: Set[Path] = set()

    def conciliar(self) -> List[ResultadoConcilacao]:
        """Executa a conciliação principal (Round 1 — do zero)."""
        self.comprovantes_usados = set()
        self.bases_usadas = set()
        self._preparar_documentos()
        self.resultados = []
        
        for lancamento in self.lancamentos:
            # Busca comprovante
            comprovante, score_comp = self._encontrar_melhor_documento(
                lancamento, 
                self.comprovantes_disponiveis,
                self.comprovantes_usados
            )
            
            # Busca documento base (PC, boleto, fatura, etc)
            if lancamento.eh_saida:
                base, score_base = self._encontrar_melhor_documento(
                    lancamento,
                    self.bases_disponiveis,
                    self.bases_usadas
                )
            else:
                base, score_base = None, 0
            
            # Marca documentos como usados
            if comprovante and score_comp >= 50:
                self.comprovantes_usados.add(comprovante.arquivo)
            else:
                comprovante = None
                score_comp = 0
            
            if base and score_base >= 50:
                self.bases_usadas.add(base.arquivo)
            else:
                base = None
                score_base = 0
            
            # Cria resultado
            resultado = self._criar_resultado(
                lancamento, comprovante, base, score_comp, score_base
            )
            self.resultados.append(resultado)
        
        return self.resultados

    def reconciliar_pendentes(
        self,
        resultados_anteriores: List[ResultadoConcilacao],
    ) -> List[ResultadoConcilacao]:
        """
        Round 2+: NÃO desfaz trabalho anterior.

        - Linhas ajustadas manualmente: intocáveis
        - Linhas com comprovante/base já vinculados: mantém os vínculos
        - Só tenta preencher o que ainda está VAZIO (comprovante ou base)
        - Documentos já usados não são reatribuídos a outros lançamentos
        """
        self._preparar_documentos()

        self.comprovantes_usados = set()
        self.bases_usadas = set()

        # 1) Reserva tudo que já está vinculado
        por_ordem: Dict[int, ResultadoConcilacao] = {
            r.lancamento.ordem: r for r in resultados_anteriores
        }
        for r in resultados_anteriores:
            if r.comprovante:
                self.comprovantes_usados.add(r.comprovante.arquivo)
            if r.documento_base:
                self.bases_usadas.add(r.documento_base.arquivo)

        novos: List[ResultadoConcilacao] = []
        for lancamento in self.lancamentos:
            anterior = por_ordem.get(lancamento.ordem)

            # Sem histórico → trata como pendente total
            if anterior is None:
                comprovante, score_comp = self._encontrar_melhor_documento(
                    lancamento, self.comprovantes_disponiveis, self.comprovantes_usados
                )
                if lancamento.eh_saida:
                    base, score_base = self._encontrar_melhor_documento(
                        lancamento, self.bases_disponiveis, self.bases_usadas
                    )
                else:
                    base, score_base = None, 0

                if comprovante and score_comp >= 50:
                    self.comprovantes_usados.add(comprovante.arquivo)
                else:
                    comprovante, score_comp = None, 0
                if base and score_base >= 50:
                    self.bases_usadas.add(base.arquivo)
                else:
                    base, score_base = None, 0

                novos.append(
                    self._criar_resultado(
                        lancamento, comprovante, base, score_comp, score_base
                    )
                )
                continue

            # Ajuste manual: não mexe em nada
            if getattr(anterior, "ajustado_manual", False):
                novos.append(anterior)
                continue

            # Partir do que já existe
            comprovante = anterior.comprovante
            base = anterior.documento_base
            score_comp = anterior.score_comprovante or (100 if comprovante else 0)
            score_base = anterior.score_base or (100 if base else 0)

            # Só busca comprovante se estiver vazio
            if comprovante is None:
                doc, sc = self._encontrar_melhor_documento(
                    lancamento, self.comprovantes_disponiveis, self.comprovantes_usados
                )
                if doc and sc >= 50:
                    comprovante = doc
                    score_comp = sc
                    self.comprovantes_usados.add(doc.arquivo)

            # Só busca base se saída e estiver vazia
            if lancamento.eh_saida and base is None:
                doc, sc = self._encontrar_melhor_documento(
                    lancamento, self.bases_disponiveis, self.bases_usadas
                )
                if doc and sc >= 50:
                    base = doc
                    score_base = sc
                    self.bases_usadas.add(doc.arquivo)

            resultado = self._criar_resultado(
                lancamento, comprovante, base, score_comp, score_base
            )
            # preserva flag se houver
            resultado.ajustado_manual = getattr(anterior, "ajustado_manual", False)
            novos.append(resultado)

        self.resultados = novos
        return self.resultados

    def _preparar_documentos(self) -> None:
        """Separa documentos por tipo e remove duplicatas seguras."""
        unicos = self._filtrar_duplicatas(self.documentos)
        self.comprovantes_disponiveis = []
        self.bases_disponiveis = []
        for doc in unicos:
            if doc.tipo == TipoDocumento.COMPROVANTE:
                self.comprovantes_disponiveis.append(doc)
            elif doc.tipo in [
                TipoDocumento.PC, TipoDocumento.BOLETO,
                TipoDocumento.FATURA, TipoDocumento.GUIA,
                TipoDocumento.RECIBO,
            ]:
                self.bases_disponiveis.append(doc)

    def _filtrar_duplicatas(self, docs: List[DocumentoFinanceiro]) -> List[DocumentoFinanceiro]:
        """
        Mantém apenas 1 documento por chave forte (barras/txid/nosso número).
        Sem chave forte, todos permanecem (não arrisca descartar documento único).
        """
        vistos: Dict[str, DocumentoFinanceiro] = {}
        resultado: List[DocumentoFinanceiro] = []
        self.duplicatas_ignoradas = []
        for doc in docs:
            chave = ""
            try:
                chave = doc.chave_duplicata() or ""
            except Exception:
                chave = ""
            if not chave:
                resultado.append(doc)
                continue
            if chave in vistos:
                self.duplicatas_ignoradas.append(doc)
                continue
            vistos[chave] = doc
            resultado.append(doc)
        if self.duplicatas_ignoradas:
            print(f"Duplicatas ignoradas (ID forte): {len(self.duplicatas_ignoradas)}")
        return resultado
    
    def _encontrar_melhor_documento(
        self, 
        lancamento: LancamentoExtrato,
        documentos: List[DocumentoFinanceiro],
        usados: Set[Path]
    ) -> Tuple[Optional[DocumentoFinanceiro], int]:
        """Encontra o melhor documento para um lançamento"""
        candidatos = []
        
        for doc in documentos:
            if doc.arquivo in usados:
                continue
            
            score = self._calcular_score(lancamento, doc)
            if score >= 45:  # Valor+algo de data/nome
                candidatos.append((doc, score))
        
        if not candidatos:
            return None, 0
        
        # Ordena por score
        candidatos.sort(key=lambda x: x[1], reverse=True)
        
        # Verifica se há empate
        melhor_score = candidatos[0][1]
        empatados = [c for c in candidatos if c[1] >= melhor_score - 5]
        
        # Se há empate, pode ser um falso positivo
        if len(empatados) > 1:
            # Tenta resolver com critérios adicionais
            return self._resolver_empate(candidatos, lancamento)
        
        return candidatos[0]
    
    def _calcular_score(self, lancamento: LancamentoExtrato, doc: DocumentoFinanceiro) -> int:
        """
        Score de conciliação: VALOR + DATA + FAVORECIDO (+ IDs fortes).
        A descrição do campo do comprovante NÃO entra no match (só serve para recibo).
        """
        score = 0

        # --- 1. VALOR (obrigatório para match sério) ---
        if doc.valor is not None:
            diff = abs(doc.valor - lancamento.valor_absoluto)
            if diff < Decimal("0.01"):
                score += 50
            elif diff <= Decimal("1.00"):
                score += 20
            else:
                # Valor diferente: quase nunca é o documento certo
                return 0
        else:
            # Sem valor no PDF: só aceita se houver ID forte depois
            score += 0

        # --- 2. DATA (gate anti-roubo) ---
        # Bases (PC/boleto/fatura/guia/recibo) podem ser legitimamente
        # anteriores ao pagamento: mantem a regra antiga (bonus suave).
        # Comprovantes (PIX/transferencia) sao do dia: data divergente alem
        # da tolerancia REJEITA o candidato (score 0). Excecao: ID forte
        # (PC_xxx/AMXxxx) no nome do arquivo — o humano nomeou certo.
        # Doc sem data: neutro (nao trava nada a toa).
        eh_comp = getattr(doc, "tipo", None) not in (
            TipoDocumento.PC, TipoDocumento.BOLETO, TipoDocumento.FATURA,
            TipoDocumento.GUIA, TipoDocumento.RECIBO)
        id_forte = self._score_ids_arquivo(lancamento, doc) > 0
        if doc.data:
            dias = (doc.data - lancamento.data).days  # + = documento posterior
            if dias == 0:
                score += 25
            elif eh_comp and not id_forte and (dias > 2 or dias < -7):
                # Comprovante de outro dia (ex.: comp 29/09 num lanc 16/09).
                # Tolerancia: +2 dias (compensacao D+1) e -7 dias.
                return 0
            elif abs(dias) <= 2:
                score += 15
            elif abs(dias) <= 5:
                score += 8
            elif abs(dias) > 15:
                score -= 25
        # sem data no doc: neutro

        # --- 3. FAVORECIDO (nome) ---
        score += self._score_favorecido(lancamento, doc)

        # --- 4. IDs fortes (PC_0220, AMX040, etc.) no extrato vs NOME DO ARQUIVO ---
        score += self._score_ids_arquivo(lancamento, doc)

        return score

    def _extrair_nome_extrato(self, descricao: str) -> str:
        """Extrai nome do favorecido a partir da descrição do extrato (DES:/DEST.)."""
        if not descricao:
            return ""
        d = descricao
        for padrao in [
            r"(?:PIX\s+ENVIADO\s+)?DES:\s*(.+)$",
            r"DEST\.?\s*(.+)$",
            r"TED\s+.*?DEST\.?\s*(.+)$",
            r"TRANSF.*?(?:PARA|DEST\.?)\s*(.+)$",
        ]:
            m = re.search(padrao, d, re.IGNORECASE)
            if m:
                nome = m.group(1).strip()
                # corta códigos no fim (números longos de controle)
                nome = re.sub(r"\s+\d{5,}$", "", nome).strip()
                if len(nome) >= 5:
                    return nome
        return ""

    def _tokens_nome(self, nome: str) -> set:
        if not nome:
            return set()
        n = normalizar_texto(nome)
        # remove ruído comum
        stop = {
            "de", "da", "do", "das", "dos", "e", "ltda", "eireli", "me", "sa", "s/a",
            "pix", "enviado", "des", "dest", "ted", "pagto", "pagamento",
        }
        return {t for t in n.split() if len(t) >= 3 and t not in stop}

    def _score_favorecido(self, lancamento: LancamentoExtrato, doc: DocumentoFinanceiro) -> int:
        """Compara nome do extrato com favorecido do PDF e com o nome do arquivo."""
        nome_ext = self._extrair_nome_extrato(lancamento.descricao)
        tokens_ext = self._tokens_nome(nome_ext)
        if not tokens_ext:
            # Extrato sem nome claro — não pontua nem penaliza por favorecido
            return 0

        # Lados do documento: favorecido parseado + stem do arquivo (onde costuma estar o nome certo)
        tokens_doc = set()
        tokens_doc |= self._tokens_nome(doc.favorecido or "")
        tokens_doc |= self._tokens_nome((doc.arquivo.stem if doc.arquivo else "").replace("_", " "))

        if not tokens_doc:
            # Extrato tem nome, documento não — incerto, leve penalidade
            return -10

        comuns = tokens_ext & tokens_doc
        if not comuns:
            # Nomes claramente diferentes → penalidade forte (evita R$ 350 embaralhado)
            return -40

        # Quanto mais tokens de nome em comum, melhor
        if len(comuns) >= 2:
            return 40
        return 25

    def _score_ids_arquivo(self, lancamento: LancamentoExtrato, doc: DocumentoFinanceiro) -> int:
        """IDs tipo PC_0220 / AMX040 no extrato vs nome do arquivo (não vs descrição do PDF)."""
        ids_lanc = self._extrair_ids(lancamento.descricao)
        nome_arq = (doc.arquivo.stem if doc.arquivo else "").upper().replace(" ", "_")
        ids_arq = self._extrair_ids(nome_arq)
        # também pega códigos tipo AMX040 do stem
        for m in re.findall(r"[A-Z]{2,}\d{2,}[A-Z0-9]*", nome_arq):
            ids_arq.add(m)

        if not ids_lanc:
            return 0
        inter = ids_lanc & ids_arq
        if inter:
            return 35 + 5 * min(len(inter), 3)
        # extrato tem PC/AMX e arquivo tem outro código diferente → leve penalidade
        if ids_arq and ids_lanc:
            return -5
        return 0

    def _extrair_ids(self, texto: str) -> Set[str]:
        """Extrai identificadores de um texto"""
        texto = (texto or "").upper()
        ids: Set[str] = set()

        padroes = [
            r"PC\s*[:_#.\s-]*(\d+)",
            r"PEDIDO\s*[:_#.\s-]*(\d+)",
            r"NF\s*[:_#.\s-]*(\d+)",
            r"DOCUMENTO\s*[:_#.\s-]*(\d+)",
            r"BOLETO\s*[:_#.\s-]*(\d+)",
            r"\b(AMX\d+)\b",
            r"\b([A-Z]{2,}\d{2,}[A-Z0-9]*)\b",
        ]
        for padrao in padroes:
            for match in re.findall(padrao, texto):
                ids.add(str(match).lstrip("0") if str(match).isdigit() else str(match))

        return ids

    def _resolver_empate(
        self,
        candidatos: List[Tuple[DocumentoFinanceiro, int]],
        lancamento: LancamentoExtrato,
    ) -> Tuple[Optional[DocumentoFinanceiro], int]:
        """Desempate: favorecido > data > score."""
        def chave(item):
            doc, score = item[0], item[1]
            fav = self._score_favorecido(lancamento, doc)
            dias = 999
            if doc.data:
                dias = abs((doc.data - lancamento.data).days)
            return (-fav, dias, -score)

        ordenados = sorted(candidatos, key=chave)
        melhor = ordenados[0]
        # Se o melhor ainda tem favorecido conflitante e só empatou por valor, não forçar
        if self._score_favorecido(lancamento, melhor[0]) < 0 and melhor[1] < 70:
            return None, 0
        return melhor[0], melhor[1]

    def _criar_resultado(
        self,
        lancamento: LancamentoExtrato,
        comprovante: Optional[DocumentoFinanceiro],
        base: Optional[DocumentoFinanceiro],
        score_comp: int,
        score_base: int
    ) -> ResultadoConcilacao:
        """Cria resultado da conciliação"""
        faltantes = []
        divergencias = []
        status = StatusConciliacao.FALTANDO
        
        # Verifica documentos faltantes
        if not comprovante:
            faltantes.append("Comprovante")
        
        if lancamento.eh_saida and not base:
            if comprovante:
                faltantes.append("Documento Base (PC/Boleto/Fatura)")
            else:
                faltantes.append("Comprovante e Documento Base")
        
        # Se não tem comprovante, status é SEM_COMPROVANTE
        if not comprovante:
            status = StatusConciliacao.SEM_COMPROVANTE
        
        # Se tem comprovante mas não tem base
        elif comprovante and lancamento.eh_saida and not base:
            status = StatusConciliacao.PRECISA_RECIBO
        
        # Se tem tudo, verifica divergências
        elif comprovante and (not lancamento.eh_saida or base):
            status = StatusConciliacao.CONCILIADO
            
        # Divergencias visiveis em QUALQUER status com comprovante
        # (antes so no branch CONCILIADO: PRECISA_RECIBO escondia "Data: ...").
        if comprovante and comprovante.valor:
            if abs(comprovante.valor - lancamento.valor_absoluto) >= Decimal("0.01"):
                divergencias.append(f"Valor: {lancamento.valor_absoluto} vs {comprovante.valor}")
                if status == StatusConciliacao.CONCILIADO:
                    status = StatusConciliacao.DIVERGENTE

        if comprovante and comprovante.data:
            dias = abs((comprovante.data - lancamento.data).days)
            if dias > 2:
                divergencias.append(f"Data: {lancamento.data} vs {comprovante.data}")
                if status == StatusConciliacao.CONCILIADO:
                    status = StatusConciliacao.ATENCAO

        if base and score_base < 50:
            divergencias.append("Documento base com baixa confiança")
            if status == StatusConciliacao.CONCILIADO:
                status = StatusConciliacao.ATENCAO
        
        return ResultadoConcilacao(
            lancamento=lancamento,
            comprovante=comprovante,
            documento_base=base,
            status=status,
            score_comprovante=score_comp,
            score_base=score_base,
            divergencias=divergencias,
            faltantes=faltantes
        )
    
    def obter_faltantes(self) -> List[ResultadoConcilacao]:
        """Retorna resultados com documentos faltantes"""
        return [r for r in self.resultados if r.faltantes]
    
    def obter_nao_conciliados(self) -> List[ResultadoConcilacao]:
        """Retorna resultados não conciliados"""
        return [r for r in self.resultados if r.status != StatusConciliacao.CONCILIADO]

