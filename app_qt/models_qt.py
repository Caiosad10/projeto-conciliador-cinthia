# app_qt/models_qt.py — QAbstractTableModel virtualizado (sem paginação)
from __future__ import annotations

from typing import List
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from app_qt.theme import STATUS_COLORS
from core.models import ResultadoConcilacao
from utils.text_utils import format_data, format_decimal_br

COLS = ["Recibo?", "Ord", "Data", "Descrição", "Valor", "Status",
        "Comprovante", "Base", "Score"]

FILTROS = ["TODOS", "CONCILIADOS", "PENDÊNCIAS", "ATENCAO", "RECIBO?", "MARCADOS"]


def _status_key(r: ResultadoConcilacao) -> str:
    return r.status.value if hasattr(r.status, "value") else str(r.status)


def passa_filtro(r: ResultadoConcilacao, filtro: str, ordens_recibo: set) -> bool:
    s = _status_key(r)
    if filtro == "TODOS":
        return True
    if filtro == "CONCILIADOS":
        return s == "CONCILIADO"
    if filtro == "PENDÊNCIAS":
        return s != "CONCILIADO"
    if filtro == "ATENCAO":
        return s == "ATENCAO"
    if filtro == "RECIBO?":
        return s == "PRECISA_RECIBO"
    if filtro == "MARCADOS":
        return r.lancamento.ordem in ordens_recibo
    return True


class ResultadosModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._todos: List[ResultadoConcilacao] = []
        self._visiveis: List[ResultadoConcilacao] = []
        self._filtro = "TODOS"
        self._ordens_recibo: set = set()

    def set_dados(self, resultados: List[ResultadoConcilacao],
                  filtro: str, ordens_recibo: set):
        self.beginResetModel()
        self._todos = list(resultados)
        self._filtro = filtro
        self._ordens_recibo = set(ordens_recibo)
        self._visiveis = [r for r in self._todos
                          if passa_filtro(r, filtro, self._ordens_recibo)]
        self.endResetModel()

    def set_filtro(self, filtro: str):
        self.set_dados(self._todos, filtro, self._ordens_recibo)

    def set_marcados(self, ordens: set):
        self.set_dados(self._todos, self._filtro, ordens)

    def rowCount(self, parent=QModelIndex()):
        return len(self._visiveis)

    def columnCount(self, parent=QModelIndex()):
        return len(COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLS[section]
        return None

    def resultado_na_linha(self, row: int) -> ResultadoConcilacao | None:
        if 0 <= row < len(self._visiveis):
            return self._visiveis[row]
        return None

    def flags(self, index: QModelIndex):
        f = super().flags(index) | Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 0:
            f |= Qt.ItemIsUserCheckable
        return f

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self._visiveis[index.row()]
        c = index.column()
        if role == Qt.CheckStateRole and c == 0:
            if r.lancamento.ordem in self._ordens_recibo:
                return Qt.CheckState.Checked
            return Qt.CheckState.Unchecked
        if role == Qt.DisplayRole:
            if c == 1:
                return f"{r.lancamento.ordem:03d}"
            if c == 2:
                return format_data(r.lancamento.data)
            if c == 3:
                return (r.lancamento.descricao or "")[:80]
            if c == 4:
                return format_decimal_br(r.lancamento.valor_absoluto)
            if c == 5:
                return _status_key(r)
            if c == 6:
                return r.comprovante.nome if r.comprovante else "—"
            if c == 7:
                return r.documento_base.nome if r.documento_base else "—"
            if c == 8:
                return f"{r.score_comprovante}/{r.score_base}"
            return ""
        if role == Qt.BackgroundRole and c == 5:
            cor = STATUS_COLORS.get(_status_key(r), "#667085")
            col = QColor(cor)
            col.setAlpha(38)
            return col
        if role == Qt.ForegroundRole and c == 5:
            return QColor(STATUS_COLORS.get(_status_key(r), "#667085"))
        if role == Qt.TextAlignmentRole and c in (1, 2, 4, 8):
            return Qt.AlignCenter
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if index.column() == 0 and role == Qt.CheckStateRole:
            r = self._visiveis[index.row()]
            ord_ = r.lancamento.ordem
            checked = (value == Qt.CheckState.Checked or int(value) == 2)
            if checked:
                self._ordens_recibo.add(ord_)
            else:
                self._ordens_recibo.discard(ord_)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            parent = self.parent()
            if parent is not None and hasattr(parent, "ordens_recibo_changed"):
                parent.ordens_recibo_changed(set(self._ordens_recibo))
            return True
        return False
