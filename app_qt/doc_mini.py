# app_qt/doc_mini.py — miniatura clicável nítida (render 2x + reload no resize)
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

try:
    import fitz
except ImportError:
    fitz = None
from PySide6.QtGui import QImage, QPixmap


def _reduz(pix: QPixmap, alvo_w: int, alvo_h: int) -> QPixmap:
    """Downscale de alta qualidade: metades sucessivas (efeito box-filter) até
    ~2.4x do alvo, depois ajuste final suave. Bilinear direto de 8x borrava o
    texto de comprovante."""
    p = pix
    for _ in range(8):
        if p.width() <= alvo_w * 2.4 or p.height() <= alvo_h * 2.4:
            break
        p = p.scaled(max(1, p.width() // 2), max(1, p.height() // 2),
                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return p.scaled(alvo_w, alvo_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class DocMini(QFrame):
    clicked = Signal()

    def __init__(self, parent=None, titulo: str = ""):
        super().__init__(parent)
        # objectName específico: QLabel HERDA de QFrame no Qt, então um seletor
        # 'QFrame' solto casaria com os labels filhos (caixas em volta do título)
        self.setObjectName("DocMini")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QFrame#DocMini { background: #FFFFFF; border: 1px solid #E6E9EF;"
                           " border-radius: 12px; } QFrame#DocMini:hover { border-color: #2E75B6; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        self.lbl_t = QLabel(titulo)
        self.lbl_t.setObjectName("MutedLabel")
        self.lbl_t.setAlignment(Qt.AlignCenter)
        self.lbl_img = QLabel("—")
        self.lbl_img.setAlignment(Qt.AlignCenter)
        self.lbl_img.setMinimumHeight(200)
        # Tamanho fixo no layout: pixmap nunca empurra o layout (causa do loop)
        self.lbl_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_img.setFixedHeight(380)
        self.lbl_img.setStyleSheet("background:#2b2b2b; color:#fff; border-radius:6px;")
        self.lbl_img.setScaledContents(False)
        self.lbl_n = QLabel("—")
        self.lbl_n.setObjectName("MutedLabel")
        self.lbl_n.setAlignment(Qt.AlignCenter)
        self.lbl_n.setWordWrap(True)
        for w in (self.lbl_t, self.lbl_img, self.lbl_n):
            lay.addWidget(w)
        self._path: Path | None = None
        self._pm_full: QPixmap | None = None
        self._last_w: int = 0
        self._dirty: bool = True      # pixmap novo ainda não aplicado ao label
        self._render_key = None       # (path, mtime) do arquivo já renderizado
        self._refit_timer = QTimer(self)
        self._refit_timer.setSingleShot(True)
        self._refit_timer.timeout.connect(self._do_refit)

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Refit com debounce: evita loop resize->setPixmap->resize->...
        if self._pm_full is None or self._pm_full.isNull():
            return
        if self._refit_timer.isActive():
            return
        self._refit_timer.start(120)

    def _do_refit(self):
        if self._pm_full is None or self._pm_full.isNull():
            return
        # Encaixa na ALTURA e na LARGURA do label (KeepAspectRatio) — antes
        # scaledToWidth estourava o card em página A4 retrato.
        dpr = self._pm_full.devicePixelRatio() or 1.0
        if dpr <= 0:
            dpr = 1.0
        avail_w = (self.lbl_img.width() or self.width() or 260) * dpr
        avail_h = (self.lbl_img.height() or 380) * dpr
        alvo = _reduz(self._pm_full, max(60, int(avail_w)), max(60, int(avail_h)))
        atual = self.lbl_img.pixmap()
        # _dirty: SEMPRE reaplica quando o arquivo mudou — sem ele, duas páginas
        # A4 geram alvo de mesmo tamanho e o pixmap antigo ficava "congelado".
        if (not self._dirty and atual is not None and not atual.isNull()
                and atual.size() == alvo.size()):
            return
        self._dirty = False
        self._last_w = alvo.width()
        self.lbl_img.setPixmap(alvo)

    def _refit(self):
        self._do_refit()

    def set_doc(self, caminho: Path | None, titulo: str = ""):
        if titulo:
            self.lbl_t.setText(titulo)
        novo = Path(caminho) if caminho else None
        chave = None
        if novo and novo.exists():
            try:
                chave = (str(novo.resolve()), novo.stat().st_mtime_ns)
            except OSError:
                chave = (str(novo), None)
        # Cache: mesmo arquivo já renderizado → mantém o pixmap (evita re-render)
        if (chave is not None and chave == self._render_key
                and self._pm_full is not None):
            self._path = novo
            return
        self._render_key = chave
        self._path = novo
        self._pm_full = None
        self._last_w = 0
        self._dirty = False
        if not self._path or not self._path.exists():
            self.lbl_img.setText("—")
            self.lbl_img.setPixmap(QPixmap())
            self.lbl_n.setText("Nenhum documento — clique p/ vincular")
            return
        self.lbl_n.setText(self._path.name)
        if self._path.suffix.lower() in (".docx", ".doc"):
            self.lbl_img.setText("DOCX\nAbrir no Word")
            self.lbl_img.setPixmap(QPixmap())
            return
        if fitz is None:
            self.lbl_img.setText("Clique p/ ampliar")
            return
        try:
            doc = fitz.open(str(self._path))
            pg = doc[0]
            # Render 3.6x (260 DPI): nítido após downscale p/ o card.
            # HiDPI 125%/150%: sobe proporcionalmente p/ não interpolar.
            from app_qt.pdf_view import BASE_DPI
            dpi = BASE_DPI
            try:
                from PySide6.QtWidgets import QApplication
                scr = QApplication.primaryScreen()
                if scr is not None:
                    dpi = BASE_DPI * max(1.0, float(scr.devicePixelRatio() or 1.0))
            except Exception:
                pass
            z = max(2.5, min(5.0, float(dpi) / 72.0))
            pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                         QImage.Format_RGB888)
            self._pm_full = QPixmap.fromImage(img.copy())
            try:
                self._pm_full.setDevicePixelRatio(max(1.0, z / 3.61))
            except Exception:
                pass
            doc.close()
            self.lbl_img.setText("")
            self._dirty = True
            self._refit()
        except Exception:
            self._pm_full = None
            self._render_key = None
            self._dirty = False
            self.lbl_img.setText("Clique p/ ampliar")

