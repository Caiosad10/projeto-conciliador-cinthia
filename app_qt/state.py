# app_qt/state.py — estado compartilhado (acumula pastas como o Tk)
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from core.conciliador import Conciliador
from core.models import ResultadoConcilacao


@dataclass
class AppState:
    conciliador: Conciliador = field(default_factory=Conciliador)
    pastas_docs: List[Path] = field(default_factory=list)
    extrato_path: Optional[Path] = None
    extrato_carregado: bool = False
    documentos_carregados: bool = False
    resultados: List[ResultadoConcilacao] = field(default_factory=list)
    ordens_recibo: Set[int] = field(default_factory=set)
    filtro: str = "TODOS"

    @property
    def pasta_atual(self) -> Optional[Path]:
        return self.pastas_docs[-1] if self.pastas_docs else None

    @pasta_atual.setter
    def pasta_atual(self, value: Optional[Path]) -> None:
        if value is None:
            self.pastas_docs = []
        elif value not in self.pastas_docs:
            self.pastas_docs.append(Path(value))

    def reset_resultados(self, resultados: List[ResultadoConcilacao]) -> None:
        self.resultados = resultados

