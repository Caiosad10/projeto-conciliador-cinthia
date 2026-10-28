# app_qt/widgets.py — componentes da identidade "Claro Moderno"
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout


class _Celula(QFrame):
    """Uma métrica clicável dentro do KpiPanel (métrica = filtro)."""
    clicada = Signal(str)

    def __init__(self, rotulo: str, filtro: str, parent=None):
        super().__init__(parent)
        self.filtro = filtro
        self.setObjectName("KpiCel")
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(0)
        self.lbl_valor = QLabel("0")
        self.lbl_valor.setObjectName("KpiValue")
        self.lbl_rotulo = QLabel(rotulo.upper())
        self.lbl_rotulo.setObjectName("KpiLabel")
        lay.addWidget(self.lbl_valor)
        lay.addWidget(self.lbl_rotulo)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_valor(self, v) -> None:
        self.lbl_valor.setText(str(v))

    def set_ativo(self, on: bool) -> None:
        self.setProperty("ativo", bool(on))
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicada.emit(self.filtro)
        super().mousePressEvent(e)


class KpiPanel(QFrame):
    """Painel único de métricas com divisórias; clique = filtro, repetir = limpa.

    Emite `filtro_solicitado` (toggle já resolvido: clicar na célula ativa
    emite "TODOS"). O dono aplica o filtro e devolve com `set_ativo`.
    """
    filtro_solicitado = Signal(str)

    def __init__(self, celulas, parent=None):
        super().__init__(parent)
        self.setObjectName("KpiPanel")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)
        self._celulas = {}
        self._ativo = "TODOS"
        for i, (rotulo, filtro) in enumerate(celulas):
            if i:
                div = QFrame()
                div.setObjectName("KpiDiv")
                div.setFixedWidth(1)
                lay.addWidget(div)
            c = _Celula(rotulo, filtro)
            c.clicada.connect(self._celula_clicada)
            lay.addWidget(c, 1)
            self._celulas[filtro] = c
        self.set_ativo("TODOS")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _celula_clicada(self, filtro: str) -> None:
        self.filtro_solicitado.emit("TODOS" if filtro == self._ativo else filtro)

    def set_ativo(self, filtro: str) -> None:
        self._ativo = filtro
        for f, c in self._celulas.items():
            c.set_ativo(f == filtro)

    def atualizar(self, valores: dict) -> None:
        for f, c in self._celulas.items():
            if f in valores:
                c.set_valor(valores[f])


class Toast(QFrame):
    """Notificação efêmera não-modal (sucesso pontual); auto-dismiss via QTimer."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        self.lbl = QLabel("")
        self.lbl.setObjectName("ToastLabel")
        self.lbl.setWordWrap(True)
        self.lbl.setMaximumWidth(360)
        lay.addWidget(self.lbl)

    def mostrar(self, texto: str, ms: int = 3500) -> None:
        self.lbl.setText(texto)
        self.adjustSize()
        self.reposicionar()
        self.show()
        self.raise_()
        self._timer.start(ms)

    def reposicionar(self) -> None:
        self._posicionar()

    def _posicionar(self) -> None:
        p = self.parentWidget()
        if p is None:
            return
        margem = 44
        self.move(max(8, p.width() - self.width() - 16),
                  max(8, p.height() - self.height() - margem))

    def resizeEvent(self, e):
        if self.isVisible():
            self._posicionar()
        super().resizeEvent(e)