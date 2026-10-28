# app_qt/faltantes_dialog.py
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QPushButton,
    QTextEdit, QVBoxLayout)
from utils.text_utils import format_data, format_decimal_br

class FaltantesDialog(QDialog):
    def __init__(self, parent, faltantes, titulo="Documentos Faltantes"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(800, 600)
        lay = QVBoxLayout(self)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        lay.addWidget(self.txt, 1)
        bb = QHBoxLayout()
        b_s = QPushButton("Salvar como TXT")
        b_s.clicked.connect(self._salvar)
        b_c = QPushButton("Fechar")
        b_c.setObjectName("PrimaryBtn")
        b_c.clicked.connect(self.close)
        bb.addWidget(b_s)
        bb.addStretch(1)
        bb.addWidget(b_c)
        lay.addLayout(bb)
        self._fill(faltantes or [])

    def _fill(self, falt):
        if not falt:
            self.txt.setPlainText("Nao ha documentos faltantes!")
            return
        ent = [r for r in falt if r.lancamento.eh_entrada]
        sai = [r for r in falt if r.lancamento.eh_saida]
        L = ["=" * 60, "DOCUMENTOS FALTANTES", "=" * 60, ""]
        for t, g in (("--- ENTRADAS ---", ent), ("--- SAIDAS ---", sai)):
            if g:
                L += ["", t, ""]
                for r in g:
                    l = r.lancamento
                    L.append(f"L{l.ordem:03d} | {format_data(l.data)} | "
                             f"R$ {format_decimal_br(l.valor_absoluto)}")
                    L.append(f"  Desc: {(l.descricao or '')[:100]}")
                    for f in r.faltantes:
                        L.append(f"  - {f}")
                    L.append("")
        self.txt.setPlainText("\n".join(L))

    def _salvar(self):
        arq, _ = QFileDialog.getSaveFileName(self, "Salvar", "faltantes.txt", "TXT (*.txt)")
        if arq:
            Path(arq).write_text(self.txt.toPlainText(), encoding="utf-8")
