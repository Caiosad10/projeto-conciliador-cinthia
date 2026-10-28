# app_qt/pdf_view.py — Quick View nítido: render alta DPI + fit-to-width
from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QDialog, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

try:
    import fitz
except ImportError:
    fitz = None

from utils.pdf_utils import abrir_arquivo_externo

# DPI base do render: 260 ≈ 3.6x. Texto pequeno de comprovante
# continua legível mesmo após downscale p/ tela 125%/150%.
BASE_DPI = 260.0


def render_pdf_page(path: Path, page: int = 0, dpi: float = BASE_DPI) -> Optional[QPixmap]:
    if fitz is None:
        return None
    try:
        doc = fitz.open(str(path))
        if not (0 <= page < len(doc)):
            doc.close()
            return None
        pg = doc[page]
        z = max(1.5, min(5.0, float(dpi) / 72.0))
        pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pm = QPixmap.fromImage(img.copy())
        doc.close()
        return pm
    except Exception:
        return None


class QuickViewDialog(QDialog):
    def __init__(self, parent, caminho: Path | None, titulo: str = "Visualização"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(900, 700)
        self.setModal(True)
        self.caminho = Path(caminho) if caminho else None
        self.page = 0
        self.view_zoom = 1.0  # zoom de visualizacao (escala da view, sem re-render)
        self.n_pages = 0
        self._pm: QPixmap | None = None
        self._item: QGraphicsPixmapItem | None = None
        if self.caminho and self.caminho.suffix.lower() == ".pdf" and fitz:
            try:
                d = fitz.open(str(self.caminho))
                self.n_pages = len(d)
                d.close()
            except Exception:
                pass
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.lbl_nome = QLabel(self.caminho.name if self.caminho else "—")
        self.lbl_nome.setObjectName("SectionTitle")
        b_fechar = QPushButton("Fechar  (Esc)")
        b_fechar.setObjectName("PrimaryBtn")
        b_fechar.clicked.connect(self.close)
        b_abrir = QPushButton("Abrir no app")
        b_abrir.clicked.connect(self._abrir)
        b_menos = QPushButton("−")
        b_menos.setObjectName("MiniBtn")
        b_menos.clicked.connect(lambda: self._zoom(0.85))
        b_mais = QPushButton("+")
        b_mais.setObjectName("MiniBtn")
        b_mais.clicked.connect(lambda: self._zoom(1.2))
        b_fit = QPushButton("Ajustar")
        b_fit.setObjectName("MiniBtn")
        b_fit.setToolTip("Encaixa a largura da página na janela")
        b_fit.clicked.connect(self._fit_width)
        self.b_ant = QPushButton("◀ Anterior")
        self.b_ant.clicked.connect(lambda: self._pag(-1))
        self.b_prox = QPushButton("Próxima ▶")
        self.b_prox.clicked.connect(lambda: self._pag(1))
        self.lbl_pag = QLabel("Página 0/0")
        self.lbl_pag.setObjectName("MutedLabel")
        for w in (self.lbl_nome,):
            top.addWidget(w)
        top.addStretch(1)
        for w in (b_menos, b_mais, b_fit, self.b_ant, self.lbl_pag, self.b_prox,
                  b_abrir, b_fechar):
            top.addWidget(w)
        lay.addLayout(top)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("background:#2b2b2b; border-radius:8px;")
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        lay.addWidget(self.view, 1)
        self.lbl_status = QLabel("Esc fecha · ← → páginas · Ctrl+scroll zoom · arraste p/ mover")
        self.lbl_status.setObjectName("MutedLabel")
        lay.addWidget(self.lbl_status)
        self._render_page()
        self._fit_width()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        elif e.key() == Qt.Key_Left:
            self._pag(-1)
        elif e.key() == Qt.Key_Right:
            self._pag(1)
        else:
            super().keyPressEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self._zoom(1.2 if e.angleDelta().y() > 0 else 0.85)
            e.accept()
        else:
            super().wheelEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        # Garante fit correto após o layout final (largura real da viewport)
        self._fit_width()

    def _zoom(self, factor: float):
        if self._pm is None:
            return
        self.view_zoom = max(0.2, min(6.0, self.view_zoom * factor))
        self._apply_view()

    def _pag(self, d: int):
        if self.n_pages:
            self.page = max(0, min(self.n_pages - 1, self.page + d))
            self._render_page()
            self._fit_width()

    def _abrir(self):
        if self.caminho:
            abrir_arquivo_externo(self.caminho)

    def _apply_view(self):
        self.view.resetTransform()
        # view_zoom JÁ compensa o dpr no _fit_width ((vw-24)*ratio/width);
        # dividir de novo aqui encolhia a página p/ ~80% da viewport em 125%.
        self.view.scale(self.view_zoom, self.view_zoom)
        total = self.n_pages or 1
        self.lbl_pag.setText(f"Página {self.page+1}/{total} · {int(self.view_zoom*100)}%")

    def _fit_width(self):
        """Encaixa a largura da página na viewport (sem 'zoom gigante')."""
        if self._pm is None or self._pm.isNull():
            return
        try:
            vw = self.view.viewport().width() or self.view.width() or 860
            ratio = self.view.devicePixelRatioF() or 1.0
        except Exception:
            vw, ratio = 860, 1.0
        target = max(200, vw - 24) * max(0.5, ratio)
        self.view_zoom = max(0.2, min(4.0, target / max(1, self._pm.width())))
        self._apply_view()

    def _render_page(self):
        self.scene.clear()
        self._item = None
        if not self.caminho or not self.caminho.exists():
            self.lbl_pag.setText("Sem arquivo")
            self._pm = None
            return
        if self.caminho.suffix.lower() in (".docx", ".doc"):
            self.lbl_pag.setText("Recibo DOCX — use 'Abrir no app'")
            t = self.scene.addText(f"{self.caminho.name}\nDOCX — clique em 'Abrir no app'")
            t.setDefaultTextColor(Qt.white)
            self._pm = None
            return
        # HiDPI: renderiza com DPI extra p/ não interpolar em 125%/150%
        try:
            ratio = self.view.devicePixelRatioF() or 1.0
        except Exception:
            ratio = 1.0
        pm = render_pdf_page(self.caminho, self.page, BASE_DPI * max(1.0, ratio))
        if pm is None:
            t = self.scene.addText("Não foi possível renderizar (instale PyMuPDF).")
            t.setDefaultTextColor(Qt.white)
            self._pm = None
            return
        try:
            pm.setDevicePixelRatio(max(1.0, ratio))
        except Exception:
            pass
        self._pm = pm
        self._item = QGraphicsPixmapItem(pm)
        self.scene.addItem(self._item)
        self.scene.setSceneRect(self._item.boundingRect())

    # Compat: código antigo chamava _render()
    def _render(self):
        self._render_page()
        self._fit_width()
