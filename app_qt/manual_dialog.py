# app_qt/manual_dialog.py — manual Qt (busca + quick view)
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QSplitter, QVBoxLayout)
from core.documento_parser import parse_documento
from core.models import TipoDocumento
from utils.text_utils import format_data, format_decimal_br

def fmt_doc(d) -> str:
    t = d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo)
    v = format_decimal_br(getattr(d, "valor", None)) or "s/valor"
    dt = format_data(getattr(d, "data", None)) or "s/data"
    f = (getattr(d, "favorecido", "") or "")[:35]
    return f"[{t}] R$ {v} | {dt} | {f} | {getattr(d, 'nome', '?')}"


def arq_key(d) -> str:
    """Chave estavel p/ comparar documentos (resolve() ou nome)."""
    try:
        a = getattr(d, "arquivo", None)
        if a is None:
            return ""
        return str(Path(a).resolve())
    except Exception:  # noqa: BLE001
        try:
            return getattr(d, "nome", "") or ""
        except Exception:  # noqa: BLE001
            return ""

def match_busca(d, termo: str) -> bool:
    if not termo:
        return True
    t = termo.lower()
    cps = [(d.arquivo.name if getattr(d, "arquivo", None) else ""),
           getattr(d, "favorecido", "") or "", getattr(d, "descricao", "") or "",
           " ".join(getattr(d, "identificadores", []) or [])]
    return any(t in (c or "").lower() for c in cps)

# Mesma ordenação do Tk (ui/dialogs.py): prováveis primeiro, resto depois.
_TIPOS_COMP = {TipoDocumento.COMPROVANTE, TipoDocumento.EXTRATO}
_TIPOS_BASE = {TipoDocumento.PC, TipoDocumento.BOLETO, TipoDocumento.FATURA, TipoDocumento.GUIA}

class ManualDialog(QDialog):
    def __init__(self, parent, resultado, documentos, callback,
                 usos: dict | None = None, resolver=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manual L{resultado.lancamento.ordem:03d}")
        self.resize(1000, 620)
        self.setModal(True)
        self.resultado = resultado
        self.documentos = list(documentos or [])
        self.callback = callback
        # Fase 3: {chave-arquivo -> ordem} de quem ja usa cada documento,
        # e hook `resolver` (MainWindow) que pergunta Mover/Manter/Cancelar.
        self.usos = dict(usos or {})
        self.resolver = resolver
        self.sel_comp = None
        self.sel_base = None
        # Pre-seleciona o vinculo atual (antes abria como "Nenhum" mesmo
        # com comprovante vinculado). Remover vira acao explicita via flags.
        self._rm_comp = False
        self._rm_base = False
        try:
            cur_c = getattr(resultado, "comprovante", None)
            cur_b = getattr(resultado, "documento_base", None)
            if cur_c is not None:
                self.sel_comp = cur_c
            if cur_b is not None:
                self.sel_base = cur_b
        except Exception:  # noqa: BLE001
            pass
        lay = QVBoxLayout(self)
        lc = resultado.lancamento
        info = QLabel(f"L{lc.ordem:03d} | {format_data(lc.data)} | "
                      f"R$ {format_decimal_br(lc.valor_absoluto)} | {(lc.descricao or '')[:90]}")
        info.setObjectName("SectionTitle")
        lay.addWidget(info)
        bl = QHBoxLayout()
        self.ed_comp = QLineEdit()
        self.ed_comp.setPlaceholderText("Buscar comprovante...")
        self.ed_comp.textChanged.connect(self._filtrar)
        self.ed_base = QLineEdit()
        self.ed_base.setPlaceholderText("Buscar base...")
        self.ed_base.textChanged.connect(self._filtrar)
        bl.addWidget(self.ed_comp)
        bl.addWidget(self.ed_base)
        lay.addLayout(bl)
        sp = QSplitter()
        self.list_comp = QListWidget()
        self.list_comp.itemClicked.connect(self._sel_c)
        self.list_comp.itemDoubleClicked.connect(self._quick_c)
        self.list_base = QListWidget()
        self.list_base.itemClicked.connect(self._sel_b)
        self.list_base.itemDoubleClicked.connect(self._quick_b)
        sp.addWidget(self.list_comp)
        sp.addWidget(self.list_base)
        lay.addWidget(sp, 1)
        self.lbl = QLabel("Comprovante: Nenhum | Base: Nenhum")
        self.lbl.setObjectName("MutedLabel")
        lay.addWidget(self.lbl)
        bb = QHBoxLayout()
        b_ac = QPushButton("+ PDF comp.")
        b_ac.clicked.connect(lambda: self._add("c"))
        b_ab = QPushButton("+ PDF base")
        b_ab.clicked.connect(lambda: self._add("b"))
        b_rc = QPushButton("Remover comp.")
        b_rc.setObjectName("DangerBtn")
        b_rc.clicked.connect(self._rm_c)
        b_rb = QPushButton("Remover base")
        b_rb.setObjectName("DangerBtn")
        b_rb.clicked.connect(self._rm_b)
        b_ok = QPushButton("Confirmar")
        b_ok.setObjectName("PrimaryBtn")
        b_ok.clicked.connect(self._ok)
        b_no = QPushButton("Cancelar")
        b_no.clicked.connect(self.reject)
        for w in (b_ac, b_ab, b_rc, b_rb):
            bb.addWidget(w)
        bb.addStretch(1)
        bb.addWidget(b_ok)
        bb.addWidget(b_no)
        lay.addLayout(bb)
        self._filtrar()
        self._upd()

    def _comp_ok(self, d) -> bool:
        # Paridade Tk: manual permite QUALQUER pdf nos dois lados.
        # Tipagem errada (base como comprovante e vice-versa) nao bloqueia.
        return True

    def _base_ok(self, d) -> bool:
        return True

    def _filtrar(self):
        # Ordena como o Tk: candidatos prováveis primeiro, resto depois.
        # Nunca esconde nada — tipagem errada não bloqueia vínculo.
        tc = self.ed_comp.text().strip()
        tb = self.ed_base.text().strip()
        comps, outros_c = self._split(self.documentos, _TIPOS_COMP)
        bases, outros_b = self._split(self.documentos, _TIPOS_BASE)
        orden_c = self._ordenar(comps + outros_c)
        orden_b = self._ordenar(bases + outros_b)
        self.vc = [d for d in orden_c if match_busca(d, tc)]
        self.vb = [d for d in orden_b if match_busca(d, tb)]
        self.list_comp.clear()
        for d in self.vc:
            # Fase 3: sinaliza documento ja vinculado em outro lancamento.
            o = self.usos.get(arq_key(d)) if self.usos else None
            suf = f"  [ja em L{o:03d}]" if o and o != self.resultado.lancamento.ordem else ""
            self.list_comp.addItem(fmt_doc(d) + suf)
        if not self.vc:
            self.list_comp.addItem("(Nenhum resultado — limpe a busca)")
        self.list_base.clear()
        for d in self.vb:
            o = self.usos.get(arq_key(d)) if self.usos else None
            suf = f"  [ja em L{o:03d}]" if o and o != self.resultado.lancamento.ordem else ""
            self.list_base.addItem(fmt_doc(d) + suf)
        if not self.vb:
            self.list_base.addItem("(Nenhum resultado — limpe a busca)")
        self._restore_selection()

    def _split(self, docs, tipos):
        a = [d for d in docs if getattr(d, "tipo", None) in tipos]
        b = [d for d in docs if getattr(d, "tipo", None) not in tipos]
        return a, b

    def _ordenar(self, docs):
        lanc = self.resultado.lancamento
        lv = lanc.valor_absoluto
        ld = lanc.data

        def chave(d):
            dv = getattr(d, "valor", None)
            dd = getattr(d, "data", None)
            try:
                diff = abs(float(dv) - float(lv)) if dv is not None else 1e12
            except Exception:
                diff = 1e12
            try:
                dias = abs((dd - ld).days) if dd and ld else 9999
            except Exception:
                dias = 9999
            return (diff, dias, getattr(d, "nome", ""))
        return sorted(docs, key=chave)

    def _restore_selection(self):
        # Mantém destaque do já selecionado após refiltrar (paridade Tk)
        for lista, vis, sel in ((self.list_comp, self.vc, self.sel_comp),
                                (self.list_base, self.vb, self.sel_base)):
            if sel is None:
                continue
            for i, d in enumerate(vis):
                try:
                    if d.arquivo == sel.arquivo:
                        lista.setCurrentRow(i)
                        break
                except Exception:
                    continue

    def _sel_c(self):
        r = self.list_comp.selectedIndexes()
        if r and r[0].row() < len(self.vc):
            self.sel_comp = self.vc[r[0].row()]
            self._upd()

    def _sel_b(self):
        r = self.list_base.selectedIndexes()
        if r and r[0].row() < len(self.vb):
            self.sel_base = self.vb[r[0].row()]
            self._upd()

    def _quick_c(self):
        from app_qt.pdf_view import QuickViewDialog
        if self.sel_comp and getattr(self.sel_comp, "arquivo", None):
            QuickViewDialog(self, self.sel_comp.arquivo, "Comprovante").exec()

    def _quick_b(self):
        from app_qt.pdf_view import QuickViewDialog
        if self.sel_base and getattr(self.sel_base, "arquivo", None):
            QuickViewDialog(self, self.sel_base.arquivo, "Base").exec()

    def _add(self, qual: str):
        arq, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if not arq:
            return
        try:
            doc = parse_documento(Path(arq))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Erro", str(e))
            return
        self.documentos.append(doc)
        if qual == "c":
            self.sel_comp = doc
        else:
            self.sel_base = doc
        self._filtrar()
        self._upd()

    def _rm_c(self):
        self.sel_comp = None
        self._rm_comp = True
        self._upd()

    def _rm_b(self):
        self.sel_base = None
        self._rm_base = True
        self._upd()

    def _upd(self):
        # Selecionar algo novo cancela o pedido de remocao daquele lado.
        if self.sel_comp is not None:
            self._rm_comp = False
        if self.sel_base is not None:
            self._rm_base = False
        c = self.sel_comp.nome if self.sel_comp else ("[remover]" if self._rm_comp else "Nenhum")
        b = self.sel_base.nome if self.sel_base else ("[remover]" if self._rm_base else "Nenhum")
        self.lbl.setText(f"Comprovante: {c} | Base: {b}")

    def _ok(self):
        # Permite confirmar vazio quando ha remocao explicita ou quando a
        # linha ja possuia vinculo (remover = deixar faltante). So barra
        # quando nao ha nada a aplicar e nada a remover.
        nada_sel = self.sel_comp is None and self.sel_base is None
        if nada_sel and not (self._rm_comp or self._rm_base):
            QMessageBox.information(self, "Manual",
                                    "Selecione ao menos um comprovante ou uma base.")
            return
        # Fase 3: conflito de uso — o documento escolhido ja esta vinculado
        # em outro lancamento. Pergunta Mover / Manter os dois / Cancelar.
        if self.resolver is not None:
            for lado, sel in (("comprovante", self.sel_comp),
                              ("base", self.sel_base)):
                if sel is None:
                    continue
                outro = self.usos.get(arq_key(sel))
                minha = self.resultado.lancamento.ordem
                if outro and outro != minha:
                    decisao = self.resolver(self, lado, sel, outro, minha)
                    if decisao == "cancelar":
                        return
        try:
            self.callback({"comprovante": self.sel_comp, "base": self.sel_base})
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Manual", f"Falha ao aplicar:\n{e}")
            return
        self.accept()

    def showEvent(self, e):
        super().showEvent(e)
        # pré-seleciona o que já está vinculado (paridade Tk)
        try:
            cur_c = getattr(self.resultado, "comprovante", None)
            cur_b = getattr(self.resultado, "documento_base", None)
            if cur_c is not None:
                self.sel_comp = cur_c
            if cur_b is not None:
                self.sel_base = cur_b
            self._upd()
        except Exception:
            pass
