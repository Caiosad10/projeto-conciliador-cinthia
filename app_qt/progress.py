# app_qt/progress.py — overlay modal de progresso (porta o ProgressDialog do Tk)
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressOverlay(QWidget):
    """Véu semitransparente sobre a janela + card central com barra e %.

    Bloqueia cliques (modal de aplicação, sem executar loop próprio) e dá
    feedback contínuo: título da etapa + nome do arquivo atual + porcentagem.
    Uso: mostrar() → atualizar(pct, texto) → fechar(). Para etapas sem %,
    modo_indeterminado().
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("ProgressOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Transparente: só o card aparece; os cliques fora dele são engolidos
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QWidget#ProgressOverlay { background: transparent; }")
        # Cobre a janela inteira e come os cliques
        self.setWindowFlags(Qt.Widget)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.StrongFocus)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("StatusBar")
        card.setFixedWidth(480)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 22, 28, 22)
        cl.setSpacing(10)
        self.lbl_titulo = QLabel("Processando…")
        self.lbl_titulo.setObjectName("SectionTitle")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_sub = QLabel("Aguarde…")
        self.lbl_sub.setObjectName("MutedLabel")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setMinimum(0)
        self.bar.setMaximum(100)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setObjectName("MutedLabel")
        self.lbl_pct.setAlignment(Qt.AlignCenter)
        for w in (self.lbl_titulo, self.lbl_sub, self.bar, self.lbl_pct):
            cl.addWidget(w)
        lay.addWidget(card)
        self._card = card
        self.hide()

    def mostrar(self, titulo: str = "Processando…") -> None:
        self.lbl_titulo.setText(titulo)
        self.lbl_sub.setText("Aguarde…")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.lbl_pct.setText("0%")
        self._cobre_tudo()
        self.show()
        self.raise_()
        self.setFocus()

    def modo_indeterminado(self, titulo: str = "Processando…") -> None:
        self.lbl_titulo.setText(titulo)
        self.lbl_sub.setText("Aguarde…")
        self.bar.setRange(0, 0)  # animação contínua do estilo
        self.lbl_pct.setText("…")
        self._cobre_tudo()
        self.show()
        self.raise_()
        self.setFocus()

    def atualizar(self, pct: int, texto: str = "") -> None:
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 100)
        try:
            pct = max(0, min(100, int(pct)))
        except (TypeError, ValueError):
            return
        self.bar.setValue(pct)
        self.lbl_pct.setText(f"{pct}%")
        if texto:
            # Nome de arquivo longo: mostra só o essencial
            self.lbl_sub.setText(texto if len(texto) <= 90 else "…" + texto[-89:])

    def fechar(self) -> None:
        self.hide()

    def _cobre_tudo(self) -> None:
        p = self.parentWidget()
        if p is not None:
            self.setGeometry(p.rect())

    def resizeEvent(self, e):
        self._cobre_tudo()
        super().resizeEvent(e)

    def mousePressEvent(self, e):
        e.accept()  # engole o clique: nada passa para baixo

    def keyPressEvent(self, e):
        e.accept()  # Esc e afins não furam o overlay
