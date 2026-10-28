# app_qt/main_window.py parte 1 — imports + init + header
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSplitter, QTableView, QTextEdit, QVBoxLayout, QWidget)
from app_qt.doc_mini import DocMini
from app_qt.faltantes_dialog import FaltantesDialog
from app_qt.manual_dialog import ManualDialog
from app_qt.models_qt import ResultadosModel
from app_qt.pdf_view import QuickViewDialog
from app_qt.progress import ProgressOverlay
from app_qt.session_store import (SESSAO_NOME, carregar_sessao, montar_payload,
                                  pasta_sessao, salvar_sessao)
from app_qt.state import AppState
from app_qt.widgets import KpiPanel, Toast
from app_qt.workers import run_in_thread
from core.extrato_parser import parse_extrato
from core.models import StatusConciliacao
from core.recibo_generator import gerar_recibos_para_faltantes
from utils.pdf_utils import abrir_pasta, empacotar_documentos, empacotar_lote
from utils.text_utils import format_data, format_decimal_br

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conciliador INCA - Qt")
        self.resize(1400, 820)
        self.state = AppState()
        self.model = ResultadosModel(self)
        self._build()
        self._refresh_buttons()

    def ordens_recibo_changed(self, ordens: set):
        self.state.ordens_recibo = set(ordens)
        self._refresh_buttons()
        self._update_summary()
        self._agenda_autosave()

    def _build(self):
        root = QWidget()
        self._root = root
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(12, 10, 12, 8)
        lay.setSpacing(10)
        # ---------- Topbar: identidade + menu bar real ----------
        mb = self.menuBar()
        mb.setObjectName("TopMenuBar")
        # Título como item de menu desabilitado (QWidgetAction/insertWidget no
        # QMenuBar do Qt6 não renderizam; texto é garantido)
        a_tit = mb.addAction("  Conciliador INCA  ")
        a_tit.setEnabled(False)
        mb.addSeparator()
        m_arq = mb.addMenu("Arquivo")
        a_ext = m_arq.addAction("Abrir extrato…")
        a_ext.setShortcut(QKeySequence("Ctrl+O"))
        a_ext.triggered.connect(self._load_extrato)
        a_docs = m_arq.addAction("Adicionar pasta docs…")
        a_docs.setShortcut(QKeySequence("Ctrl+D"))
        a_docs.triggered.connect(self._load_docs)
        a_sess = m_arq.addAction("Abrir sessão salva…")
        a_sess.triggered.connect(self._abrir_sessao)
        m_arq.addSeparator()
        a_novo = m_arq.addAction("Nova conciliação (limpar tudo)")
        a_novo.triggered.connect(self._nova_conciliacao)
        m_arq.addSeparator()
        a_sair = m_arq.addAction("Sair")
        a_sair.setShortcut(QKeySequence("Ctrl+Q"))
        a_sair.triggered.connect(self.close)
        m_con = mb.addMenu("Conciliação")
        a_conc = m_con.addAction("Conciliar (Round 1)")
        a_conc.setShortcut(QKeySequence("F5"))
        a_conc.triggered.connect(self._conciliar)
        a_reconc = m_con.addAction("Reconciliar (Round 2+)")
        a_reconc.triggered.connect(self._reconciliar)
        m_con.addSeparator()
        a_manual = m_con.addAction("Conciliação manual")
        a_manual.setShortcut(QKeySequence("M"))
        a_manual.triggered.connect(self._manual)
        m_fer = mb.addMenu("Ferramentas")
        a_quick = m_fer.addAction("Quick View")
        a_quick.triggered.connect(self._quick)
        a_rec = m_fer.addAction("Gerar recibos (marcados)")
        a_rec.triggered.connect(self._recibos)
        a_falt = m_fer.addAction("Ver faltantes")
        a_falt.triggered.connect(self._faltantes)
        a_pac = m_fer.addAction("Empacotar")
        a_pac.triggered.connect(self._pacote)
        m_aj = mb.addMenu("Ajuda")
        a_sobre = m_aj.addAction("Sobre")
        a_sobre.triggered.connect(self._sobre)
        # Ações ↔ botões: habilitar/desabilitar em conjunto
        self._menu_bindings = [
            (a_ext, "btn_open_ext"), (a_docs, "btn_add_docs"),
            (a_conc, "btn_conc"), (a_reconc, "btn_reconc"),
            (a_manual, "btn_manual"), (a_quick, "btn_view"),
            (a_rec, "btn_recibo"), (a_falt, "btn_falt"), (a_pac, "btn_pac"),
        ]
        self._act_sessao = a_sess
        self._act_novo = a_novo
        self.banner = QFrame()
        self.banner.setObjectName("Banner")
        bl = QHBoxLayout(self.banner)
        self.banner_lbl = QLabel("")
        self.banner_lbl.setObjectName("BannerLabel")
        bl.addWidget(self.banner_lbl)
        self.banner.setVisible(False)
        lay.addWidget(self.banner)
        # ---------- Painel de métricas (métrica = filtro; repetir limpa) ----------
        self.kpi = KpiPanel([("Total", "TODOS"), ("Conciliados", "CONCILIADOS"),
                             ("Pendências", "PENDÊNCIAS"), ("Atenção", "ATENCAO"),
                             ("Recibos?", "RECIBO?"), ("Marcados", "MARCADOS")])
        self.kpi.filtro_solicitado.connect(self._filtro)
        lay.addWidget(self.kpi)
        # ---------- Toolbar em 3 grupos ----------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        # Passos de entrada vivem no menu Arquivo (botões ocultos: só existem
        # para o sincronismo de habilitado/desabilitado com as ações do menu).
        self.btn_open_ext = QPushButton("Extrato…")
        self.btn_open_ext.setToolTip("Carregar o PDF do extrato Bradesco (passo 1)")
        self.btn_open_ext.clicked.connect(self._load_extrato)
        self.btn_add_docs = QPushButton("Pasta docs…")
        self.btn_add_docs.setToolTip(
            "Acumula pastas 01-09, 10-20, 21-31 como na versão Tk (pode repetir)")
        self.btn_add_docs.clicked.connect(self._load_docs)
        self.btn_conc = QPushButton("Conciliar (Round 1)")
        self.btn_conc.setObjectName("PrimaryBtn")
        self.btn_conc.clicked.connect(self._conciliar)
        self.btn_reconc = QPushButton("Reconciliar (Round 2+)")
        self.btn_reconc.clicked.connect(self._reconciliar)
        self.btn_manual = QPushButton("Conciliação manual")
        self.btn_manual.clicked.connect(self._manual)
        self.btn_view = QPushButton("Quick View")
        self.btn_view.clicked.connect(self._quick)
        self.btn_recibo = QPushButton("Gerar recibos")
        self.btn_recibo.clicked.connect(self._recibos)
        self.btn_falt = QPushButton("Ver faltantes")
        self.btn_falt.clicked.connect(self._faltantes)
        self.btn_pac = QPushButton("Empacotar")
        self.btn_pac.clicked.connect(self._pacote)

        def _grupo(rotulo, *botoes):
            lb = QLabel(rotulo.upper())
            lb.setObjectName("ToolGroupLabel")
            toolbar.addWidget(lb)
            for b in botoes:
                toolbar.addWidget(b)
            sep = QFrame()
            sep.setObjectName("ToolbarSep")
            sep.setFixedWidth(1)
            toolbar.addWidget(sep)

        # Toolbar só de processo (TEMPLATE_FLUXO §4): Dados ficam no menu
        # Arquivo; o filtro vive no painel de métricas (métrica = filtro).
        _grupo("Conciliação", self.btn_conc, self.btn_reconc, self.btn_manual,
               self.btn_view)
        _grupo("Saída", self.btn_recibo, self.btn_falt, self.btn_pac)
        toolbar.addStretch(1)
        lay.addLayout(toolbar)
        split = QSplitter(Qt.Horizontal)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 55)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(3, 380)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 140)
        self.table.selectionModel().selectionChanged.connect(lambda a, b: self._detail())
        self.table.doubleClicked.connect(lambda *a: self._quick())
        split.addWidget(self.table)
        # Menu de contexto: botão direito = Conciliação manual (fluxo rápido)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_tabela)
        # ---------- Painel direito: detalhes em cima, docs embaixo ----------
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        sec = QLabel("Detalhes do lançamento")
        sec.setObjectName("SectionTitle")
        rl.addWidget(sec)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        # Força fundo branco + texto escuro (print mostrava fundo #2b2b2b)
        self.txt.setStyleSheet("QTextEdit { background: #FFFFFF; color: #1B2430; }")
        self.txt.setMinimumHeight(150)
        self.txt.setMaximumHeight(200)
        rl.addWidget(self.txt)
        # Ação colada no detalhe (paridade Tk: botão ficava sob a descrição)
        det_btns = QHBoxLayout()
        self.btn_manual_near = QPushButton("Conciliação manual do lançamento")
        self.btn_manual_near.setObjectName("PrimaryBtn")
        self.btn_manual_near.setToolTip("Abre a vinculação manual deste lançamento (atalho: M)")
        self.btn_manual_near.clicked.connect(self._manual)
        det_btns.addWidget(self.btn_manual_near)
        det_btns.addStretch(1)
        rl.addLayout(det_btns)
        docs_row = QHBoxLayout()
        self.mini_comp = DocMini(titulo="Comprovante — clique p/ ampliar")
        self.mini_comp.clicked.connect(lambda: self._quick_kind("comp"))
        self.mini_base = DocMini(titulo="Documento Base — clique p/ vincular/ampliar")
        self.mini_base.clicked.connect(self._click_base_vazia)
        docs_row.addWidget(self.mini_comp)
        docs_row.addWidget(self.mini_base)
        rl.addLayout(docs_row, 1)
        self.lbl_comp = QLabel("Comp: -")
        self.lbl_comp.setObjectName("MutedLabel")
        self.lbl_base = QLabel("Base: -")
        self.lbl_base.setObjectName("MutedLabel")
        rl.addWidget(self.lbl_comp)
        rl.addWidget(self.lbl_base)
        hint = QLabel("Clique na miniatura vazia ou botão acima p/ vincular. "
                      "Botão direito na tabela = menu rápido.")
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)
        rl.addWidget(hint)
        split.addWidget(right)
        split.setSizes([880, 520])
        lay.addWidget(split, 1)
        # ---------- Rodapé: resumo + progresso embutido + status ----------
        bottom = QFrame()
        bottom.setObjectName("StatusBar")
        bot = QHBoxLayout(bottom)
        bot.setContentsMargins(10, 4, 10, 4)
        bot.setSpacing(10)
        self.lbl_summary = QLabel("Nenhum dado carregado")
        self.lbl_summary.setObjectName("SummaryLabel")
        bot.addWidget(self.lbl_summary)
        bot.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setFixedWidth(240)
        bot.addWidget(self.progress)
        self.lbl_status = QLabel("Pronto")
        self.lbl_status.setObjectName("StatusLabel")
        bot.addWidget(self.lbl_status)
        lay.addWidget(bottom)
        # Overlay modal de progresso (porta o ProgressDialog do Tk): cobre a
        # janela, bloqueia cliques e mostra etapa + arquivo + %.
        self.overlay = ProgressOverlay(self._root)
        # Toast de sucesso (não-modal) sobre a janela; reposicionado no resize.
        self.toast = Toast(self._root)
        # Autosave com debounce: fotografa o estado ~1s após cada mudança,
        # em thread (nunca trava a UI).
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._autosave_agora)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        t = getattr(self, "toast", None)
        if t is not None and t.isVisible():
            t.reposicionar()

    def closeEvent(self, e):
        """Fecha salvando: se houver autosave pendente, grava na hora (síncrono).

        Sem isso, fechar dentro da janela de ~1s do debounce perdia o último
        ajuste manual — o trabalho sumia e a sessão reabria sem ele.
        """
        try:
            timer = getattr(self, "_save_timer", None)
            if timer is not None and timer.isActive():
                timer.stop()
            if self.state.extrato_path and self.state.resultados:
                salvar_sessao(pasta_sessao(self.state.extrato_path) / SESSAO_NOME,
                              montar_payload(self.state))
        except Exception:
            pass
        super().closeEvent(e)

    def _say(self, t: str):
        self.lbl_status.setText(t)

    def _busy(self, on: bool, t: str = ""):
        if on:
            self.progress.setVisible(True)
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self._say(t or "Processando...")
            # Overlay modal: cobre a janela, bloqueia cliques, mostra etapa + %.
            # (Sem ele, só a barrinha do rodapé girava — invisível em janela cheia.)
            try:
                if "Conciliando" in t or "econciliando" in t:
                    self.overlay.modo_indeterminado(t or "Processando…")
                else:
                    self.overlay.mostrar(t or "Processando…")
            except Exception:
                pass
            self._set_working(True)
        else:
            self.progress.setVisible(False)
            self.progress.setValue(0)
            try:
                self.overlay.fechar()
            except Exception:
                pass
            self._set_working(False)

    def _on_progress(self, pct: int, texto: str = ""):
        if not self.progress.isVisible():
            self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        try:
            self.progress.setValue(int(pct))
        except Exception:
            pass
        try:
            self.overlay.atualizar(pct, texto)
        except Exception:
            pass
        if texto:
            self._say(f"{texto} ({int(pct)}%)")
        else:
            self._say(f"Processando... {int(pct)}%")

    def _set_working(self, working: bool):
        """Trava botoes que disparam jobs; nunca deixa a barra girando solta."""
        self._working = working
        for b in (self.btn_open_ext, self.btn_add_docs, self.btn_conc,
                  self.btn_reconc, self.btn_manual, self.btn_manual_near,
                  self.btn_recibo, self.btn_falt, self.btn_pac, self.btn_view):
            try:
                b.setEnabled(False if working else True)
            except Exception:
                pass
        for act, _attr in getattr(self, "_menu_bindings", []):
            try:
                act.setEnabled(not working)
            except Exception:
                pass
        for act in (getattr(self, "_act_sessao", None),
                    getattr(self, "_act_novo", None)):
            try:
                if act is not None:
                    act.setEnabled(not working)
            except Exception:
                pass
        if not working:
            self._refresh_buttons()

    def _refresh_buttons(self):
        has = bool(self.state.resultados)
        if getattr(self, "_working", False):
            return
        # Blindagem Round 1: depois de conciliado, o botão trava (evita o
        # "apagou tudo" — Round 1 reconstrói do zero e descarta manuais).
        # Recomeçar do zero = menu Arquivo > Nova conciliação (com confirmação).
        pode_r1 = (self.state.extrato_carregado
                   and self.state.documentos_carregados
                   and not self.state.resultados)
        self.btn_conc.setEnabled(pode_r1)
        self.btn_conc.setToolTip(
            "Conciliar do zero (só antes da primeira conciliação)"
            if not has else
            "Bloqueado: use Reconciliar p/ faltantes. "
            "Recomeçar do zero = Arquivo > Nova conciliação.")
        self.btn_reconc.setEnabled(has)
        self.btn_manual.setEnabled(has)
        self.btn_manual_near.setEnabled(has)
        self.btn_falt.setEnabled(has)
        self.btn_pac.setEnabled(has)
        self.btn_view.setEnabled(has)
        marc = len(self.state.ordens_recibo)
        self.btn_recibo.setEnabled(has and marc > 0)
        txt = f"Gerar recibos ({marc})" if marc else "Gerar recibos"
        self.btn_recibo.setText(txt)
        # Sincroniza ações de menu com o estado dos botões
        for act, attr in getattr(self, "_menu_bindings", []):
            try:
                act.setEnabled(getattr(self, attr).isEnabled())
            except Exception:
                pass

    def _reload_model(self):
        self.model.set_dados(self.state.resultados, self.state.filtro, self.state.ordens_recibo)
        self._update_summary()
        self._refresh_buttons()
        if self.state.resultados:
            self.table.selectRow(0)

    def _update_summary(self):
        rs = self.state.resultados
        if not rs:
            self.lbl_summary.setText("Nenhum dado carregado")
            return
        tot = len(rs)
        conc = sum(1 for r in rs if r.status == StatusConciliacao.CONCILIADO)
        rec = sum(1 for r in rs if r.status == StatusConciliacao.PRECISA_RECIBO)
        sem = sum(1 for r in rs if r.status == StatusConciliacao.SEM_COMPROVANTE)
        atn = sum(1 for r in rs if r.status == StatusConciliacao.ATENCAO)
        marc = len(self.state.ordens_recibo)
        self.lbl_summary.setText(
            f"{tot} lanc. | {conc} conc. | {rec} recibo | {sem} sem | "
            f"{atn} atenção | {marc} marcados")
        # Painel de métricas: valores + célula ativa = filtro atual
        self.kpi.atualizar({"TODOS": tot, "CONCILIADOS": conc,
                            "PENDÊNCIAS": tot - conc, "ATENCAO": atn,
                            "RECIBO?": rec, "MARCADOS": marc})
        self.kpi.set_ativo(self.state.filtro)

    def _current(self):
        try:
            rows = self.table.selectionModel().selectedRows()
        except Exception:
            return None
        if not rows:
            return None
        return self.model.resultado_na_linha(rows[0].row())

    def _detail_empty(self):
        self.txt.setPlainText("Selecione um lançamento.")

    def _load_extrato(self):
        if getattr(self, "_working", False):
            return
        arq, _ = QFileDialog.getOpenFileName(self, "Extrato Bradesco (PDF)", "",
                                             "PDF (*.pdf)")
        if not arq:
            return
        # Guarda o caminho escolhido (canônico): o parser pode registrar
        # arquivo_origem de outra forma, e a pasta .inca-sessao é procurada
        # a partir daqui. Sem isso, a pergunta de retomar nunca aparecia.
        self._extrato_pendente = Path(arq).resolve()
        self._busy(True, f"Lendo extrato: {Path(arq).name} ...")
        run_in_thread(self, parse_extrato, self._ok_ext, self._err,
                      self._on_progress, Path(arq))

    def _ok_ext(self, lancs):
        self._busy(False)
        if not lancs:
            self._say("Extrato sem lançamentos — verifique o PDF.")
            QMessageBox.warning(self, "Extrato", "Nenhum lançamento encontrado.")
            return
        self.state.conciliador.lancamentos = lancs
        self.state.extrato_carregado = True
        # Caminho canônico: o arquivo escolhido (resolve), com fallback p/ o que
        # o parser registrou em arquivo_origem.
        pend = getattr(self, "_extrato_pendente", None)
        origem = (self.state.conciliador.lancamentos[0].arquivo_origem
                  if self.state.conciliador.lancamentos else None)
        try:
            self.state.extrato_path = Path(pend).resolve() if pend else (
                Path(origem).resolve() if origem else None)
        except Exception:
            self.state.extrato_path = Path(pend or origem) if (pend or origem) else None
        self.banner.setVisible(False)
        # Sessão salva? Pergunta se retoma (Sim) ou segue fluxo normal (Não).
        dados = carregar_sessao(
            pasta_sessao(self.state.extrato_path) / SESSAO_NOME) \
            if self.state.extrato_path else {}
        if self.state.extrato_path and not dados:
            # Nunca mais silêncio: diz onde procurou.
            self._say("Sem sessão salva em "
                      f"{pasta_sessao(self.state.extrato_path).name}/ — fluxo normal.")
        if dados and dados.get("versao") == 1 and dados.get("resultados"):
            n_man = sum(1 for r in dados["resultados"] if r.get("ajustado_manual"))
            n_tot = len(dados["resultados"])
            resp = QMessageBox.question(
                self, "Retomar sessão",
                f"Encontrei trabalho salvo: {n_tot} lançamentos "
                f"({n_man} ajustes manuais).\n\n"
                "Retomar de onde parou?\n"
                "(Não = continuar sem restaurar.)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if resp == QMessageBox.Yes:
                self._busy(True, "Retomando sessão…")
                run_in_thread(self, self._restaurar_sessao, self._ok_sessao,
                              self._err, self._on_progress,
                              self.state.extrato_path, dados)
                return
        if self.state.documentos_carregados:
            self._conciliar()
        else:
            self._say(f"Extrato OK: {len(lancs)} lançamentos. Adicione as pastas de docs.")
            self._refresh_buttons()
            self._update_summary_extrato(len(lancs), 0)
            self.banner_lbl.setText(
                "Extrato OK. Clique em 'Pasta docs…' (pode repetir: 01-09, 10-20, 21-31).")
            self.banner.setVisible(True)

    def _update_summary_extrato(self, n_lanc: int, n_docs: int):
        base = f"Extrato: {n_lanc} lançamentos"
        if n_docs:
            base += f" · Documentos: {n_docs} PDFs em {len(self.state.pastas_docs)} pasta(s)"
        self.lbl_summary.setText(base)
        if not self.state.resultados:
            self.kpi.atualizar({"TODOS": n_lanc})

    def _err(self, msg: str):
        self._busy(False)
        self._say(f"Erro: {msg[:120]}")
        QMessageBox.critical(self, "Erro", msg)

    def _load_docs(self):
        if getattr(self, "_working", False):
            QMessageBox.information(self, "Aguarde",
                                    "Ainda processando. Aguarde a barra concluir.")
            return
        pasta = QFileDialog.getExistingDirectory(
            self, "Pasta de documentos (pode repetir p/ 01-09, 10-20, 21-31)")
        if not pasta:
            return
        if Path(pasta) in self.state.pastas_docs:
            QMessageBox.information(self, "Pasta repetida",
                                    "Essa pasta já foi adicionada.")
            return
        self._busy(True, f"Lendo documentos: {Path(pasta).name} ...")
        run_in_thread(self, self._parse_docs, self._ok_docs, self._err,
                      self._on_progress, Path(pasta))

    def _parse_docs(self, pasta: Path, progress_cb=None):
        from core.documento_parser import identificar_tipo_pdf, parse_documento as pd
        docs = []
        pdfs = sorted(pasta.rglob("*.pdf"))
        n = max(1, len(pdfs))
        for i, arq in enumerate(pdfs):
            try:
                identificar_tipo_pdf(arq)
                docs.append(pd(arq))
            except Exception:
                continue
            if progress_cb:
                progress_cb(int((i + 1) / n * 100), arq.name)
        return docs, pasta

    def _ok_docs(self, payload):
        self._busy(False)
        docs, pasta = payload
        # ACUMULA como o Tk (nao zera a cada pasta)
        ja = {d.arquivo.resolve() for d in self.state.conciliador.documentos}
        novos = [d for d in docs if d.arquivo.resolve() not in ja]
        self.state.conciliador.documentos.extend(novos)
        if pasta not in self.state.pastas_docs:
            self.state.pastas_docs.append(Path(pasta))
        total = len(self.state.conciliador.documentos)
        if total == 0:
            QMessageBox.warning(self, "Documentos", "Nenhum PDF válido nas pastas.")
            return
        self.state.documentos_carregados = True
        self.banner.setVisible(False)
        n_lanc = len(self.state.conciliador.lancamentos)
        self._update_summary_extrato(n_lanc, total)
        if self.state.extrato_carregado:
            if self.state.resultados:
                # Já há trabalho: faltantes vão para o Round 2 (nunca Round 1,
                # que reconstruiria do zero e descartaria os manuais).
                self.banner_lbl.setText(
                    f"{len(novos)} novos de '{Path(pasta).name}' (total {total}). "
                    "Reconciliando pendentes…")
                self.banner.setVisible(True)
                self._reconciliar()
            else:
                self._conciliar()
        else:
            self._say(f"{total} documentos em {len(self.state.pastas_docs)} pasta(s). "
                      f"Carregue o extrato (1).")
            self._refresh_buttons()
            self.banner_lbl.setText(
                f"{len(novos)} novos de '{Path(pasta).name}' (total {total}). "
                "Adicione outra pasta ou carregue o extrato.")
            self.banner.setVisible(True)

    def _conciliar(self):
        if getattr(self, "_working", False):
            return
        if not (self.state.extrato_carregado and self.state.documentos_carregados):
            QMessageBox.information(self, "Passos",
                                    "Passo 1: extrato + Passo 2: ao menos 1 pasta de docs.")
            return
        self._busy(True, "Conciliando (Round 1)...")
        self.progress.setRange(0, 0)  # indeterminado aqui: conciliador nao reporta %
        run_in_thread(self, lambda: self.state.conciliador.conciliar(),
                      self._ok_conc, self._err)

    def _ok_conc(self, res):
        self._busy(False)
        self.state.reset_resultados(res)
        self.state.ordens_recibo = {r.lancamento.ordem for r in res
                                    if r.status == StatusConciliacao.PRECISA_RECIBO}
        self._reload_model()
        self._say("Conciliacao Round 1 OK.")
        self._agenda_autosave()

    def _reconciliar(self):
        if getattr(self, "_working", False):
            return
        if not self.state.resultados:
            return
        self._busy(True, "Reconciliando pendentes (Round 2)...")
        self.progress.setRange(0, 0)
        atual = list(self.state.resultados)
        run_in_thread(self,
                      lambda: self.state.conciliador.reconciliar_pendentes(atual),
                      self._ok_reconc, self._err)

    def _ok_reconc(self, res):
        self._busy(False)
        self.state.reset_resultados(res)
        self._reload_model()
        self._say("Reconciliacao OK.")
        self._agenda_autosave()

    def _filtro(self, t: str):
        self.state.filtro = t
        self.model.set_filtro(t)
        self.kpi.set_ativo(t)
        if self.model.rowCount():
            self.table.selectRow(0)
        self._detail()

    def _agenda_autosave(self):
        """Agenda salvamento da sessão (~1s após a última mudança)."""
        try:
            self._save_timer.start(1000)
        except Exception:
            pass

    def _autosave_agora(self):
        """Fotografa o estado em `<extrato>.inca-sessao/sessao.json` (thread)."""
        if not self.state.extrato_path or not self.state.resultados:
            return
        payload = montar_payload(self.state)
        dest = pasta_sessao(self.state.extrato_path) / SESSAO_NOME
        run_in_thread(self, salvar_sessao, self._ok_autosave,
                      self._err_autosave, None, dest, payload)

    def _ok_autosave(self, dest):
        from datetime import datetime
        self._say(f"Sessão salva · {datetime.now():%H:%M} · {Path(dest).parent.name}/")

    def _err_autosave(self, msg: str):
        self._say(f"Aviso: sessão não salva ({msg[:80]})")

    def _abrir_sessao(self):
        """Arquivo > Abrir sessão salva — escolhe o extrato e retoma o trabalho."""
        if getattr(self, "_working", False):
            return
        arq, _ = QFileDialog.getOpenFileName(self, "Retomar sessão: escolha o EXTRATO (PDF) — o trabalho salvo ao lado dele é localizado sozinho", "",
                                             "PDF (*.pdf)")
        if not arq:
            return
        pasta = pasta_sessao(Path(arq))
        dados = carregar_sessao(pasta / SESSAO_NOME)
        if not dados or dados.get("versao") != 1:
            QMessageBox.information(
                self, "Sessão",
                "Nenhuma sessão salva para este extrato.\n"
                f"(Procurado em: {pasta.name}/)\n"
                "Carregue extrato + docs normalmente.\n\n"
                "Como funciona: o app salva sozinho ~1s após cada mudança, "
                "na pasta '<nome-do-extrato>.inca-sessao/' ao lado do extrato. "
                "Não há botão Salvar — é só fechar e retomar depois.")
            return
        n_man = sum(1 for r in dados.get("resultados", [])
                    if r.get("ajustado_manual"))
        n_tot = len(dados.get("resultados", []))
        resp = QMessageBox.question(
            self, "Retomar sessão",
            f"Encontrado trabalho salvo: {n_tot} lançamentos "
            f"({n_man} ajustes manuais).\n\n"
            "Retomar de onde parou?\n"
            "(Não = limpar e começar nova conciliação.)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if resp != QMessageBox.Yes:
            return
        self._busy(True, "Retomando sessão…")
        run_in_thread(self, self._restaurar_sessao, self._ok_sessao, self._err,
                      self._on_progress, Path(arq), dados)

    def _restaurar_sessao(self, extrato: Path, dados: dict, progress_cb=None):
        """Re-parseia extrato+docs e reaplica vínculos/scores/flags (sem re-match)."""
        from core.documento_parser import parse_documento as pd
        from core.models import ResultadoConcilacao, StatusConciliacao
        lancs = parse_extrato(extrato)
        if progress_cb:
            progress_cb(10, extrato.name)
        docs = []
        pastas = [Path(p) for p in dados.get("pastas_docs", []) if Path(p).exists()]
        todos_pdf = [a for p in pastas for a in sorted(p.rglob("*.pdf"))]
        n = max(1, len(todos_pdf))
        for i, a in enumerate(todos_pdf):
            try:
                docs.append(pd(a))
            except Exception:
                continue
            if progress_cb and i % 5 == 0:
                progress_cb(10 + int(70 * (i + 1) / n), a.name)
        por_arq = {str(d.arquivo.resolve()): d for d in docs}
        por_nome: dict = {}
        for d in docs:
            por_nome.setdefault(d.arquivo.name, d)
        if progress_cb:
            progress_cb(85, "reaplicando vínculos…")
        salva = {r["ordem"]: r for r in dados.get("resultados", [])}
        resultados = []
        for L in lancs:
            s = salva.get(L.ordem)
            if s is None:
                resultados.append(ResultadoConcilacao(
                    lancamento=L, status=StatusConciliacao.FALTANDO))
                continue

            def _acha(ref):
                if not ref:
                    return None
                d = por_arq.get(str(Path(ref).resolve()))
                if d is None:
                    d = por_nome.get(Path(ref).name)
                if d is None:
                    # Recibo .docx gerado pelo próprio app: não está no índice
                    # de PDFs, mas existe em disco → religa sem re-parse.
                    try:
                        p = Path(ref)
                        if p.exists() and p.suffix.lower() in (".docx", ".doc"):
                            from core.models import DocumentoFinanceiro as _DF
                            from core.models import TipoDocumento as _TD
                            d = _DF(arquivo=p, tipo=_TD.RECIBO,
                                    valor=L.valor_absoluto, data=L.data,
                                    identificadores=[f"L{L.ordem:03d}"])
                            docs.append(d)
                            por_arq[str(p.resolve())] = d
                            por_nome.setdefault(p.name, d)
                    except Exception:  # noqa: BLE001
                        d = None
                return d

            comp = _acha(s.get("comp"))
            base = _acha(s.get("base"))
            aus_comp = bool(s.get("comp")) and comp is None
            aus_base = bool(s.get("base")) and base is None
            try:
                st = StatusConciliacao(s.get("status", "FALTANDO"))
            except ValueError:
                st = StatusConciliacao.FALTANDO
            falt = list(s.get("faltantes", []))
            if aus_comp or aus_base:
                for ref in (s.get("comp"), s.get("base")):
                    if ref:
                        try:
                            p = Path(ref)
                        except Exception:  # noqa: BLE001
                            continue
                        if not p.exists():
                            aviso = f"Arquivo ausente: {p.name}"
                            if aviso not in falt:
                                falt.append(aviso)
            # Status honesto: arquivo ausente nunca fica verde (era o "reset"
            # aparente: grade CONCILIADO + faltante "Arquivo ausente").
            # Migração one-shot: sessões antigas persistiram base/comp null
            # com o aviso "Arquivo ausente" mas status CONCILIADO herdado.
            tem_ausente = any(str(f).startswith("Arquivo ausente") for f in falt)
            if aus_comp:
                st = StatusConciliacao.SEM_COMPROVANTE
                if "Comprovante" not in falt:
                    falt.append("Comprovante")
            elif aus_base:
                if st == StatusConciliacao.CONCILIADO:
                    st = StatusConciliacao.ATENCAO
            elif tem_ausente and st == StatusConciliacao.CONCILIADO:
                if comp is None:
                    st = StatusConciliacao.SEM_COMPROVANTE
                    if "Comprovante" not in falt:
                        falt.append("Comprovante")
                elif base is None:
                    st = StatusConciliacao.ATENCAO
            resultados.append(ResultadoConcilacao(
                lancamento=L, comprovante=comp, documento_base=base, status=st,
                score_comprovante=int(s.get("score_comp", 0)),
                score_base=int(s.get("score_base", 0)),
                divergencias=list(s.get("divergencias", [])),
                faltantes=falt,
                ajustado_manual=bool(s.get("ajustado_manual"))))
        if progress_cb:
            progress_cb(100, "pronto")
        return {"lancs": lancs, "docs": docs, "pastas": pastas,
                "resultados": resultados,
                "ordens": set(dados.get("ordens_recibo", [])),
                "filtro": dados.get("filtro", "TODOS"), "extrato": extrato}

    def _ok_sessao(self, payload):
        self._busy(False)
        c = self.state.conciliador
        c.lancamentos = payload["lancs"]
        c.documentos = payload["docs"]
        self.state.extrato_carregado = True
        self.state.documentos_carregados = bool(payload["docs"])
        self.state.pastas_docs = list(payload["pastas"])
        self.state.extrato_path = payload["extrato"]
        self.state.reset_resultados(payload["resultados"])
        # Sync: Faltantes le conciliador.resultados (obter_faltantes) — sem
        # isso o dialogo vinha vazio apos restaurar sessao.
        c.resultados = list(payload["resultados"])
        self.state.ordens_recibo = set(payload["ordens"])
        self.state.filtro = payload.get("filtro", "TODOS")
        self._reload_model()
        self._filtro(self.state.filtro)
        aus = sum(1 for r in payload["resultados"]
                  for f in (r.faltantes or []) if "Arquivo ausente" in f)
        msg = f"Sessão retomada: {len(payload['resultados'])} lançamentos."
        if aus:
            msg += f" {aus} vínculo(s) com arquivo ausente."
        self._say(msg)
        self.toast.mostrar(msg)
        self.banner.setVisible(False)

    def _nova_conciliacao(self):
        """Arquivo > Nova conciliação — limpa tudo (com confirmação)."""
        if getattr(self, "_working", False):
            return
        if self.state.resultados or self.state.extrato_carregado:
            resp = QMessageBox.question(
                self, "Nova conciliação",
                "Limpar todo o trabalho atual e começar do zero?\n"
                "(A sessão salva em disco é mantida.)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        from app_qt.state import AppState
        filtro = self.state.filtro
        self.state = AppState()
        self.state.filtro = filtro
        self._reload_model()
        self._detail_empty()
        self.banner.setVisible(False)
        self._say("Pronto para nova conciliação.")

    def _sobre(self):
        QMessageBox.about(
            self, "Sobre",
            "<b>Conciliador INCA</b> — Fechamento de caixa<br>"
            "Interface PySide6 · versão Qt 2.0.0<br><br>"
            "Atalhos: Ctrl+O extrato · Ctrl+D pasta docs · F5 conciliar · "
            "M manual · Enter quick view.<br><br>"
            "Sessão salva automaticamente ao lado do extrato "
            "(pasta '&lt;nome-do-extrato&gt;.inca-sessao/'). "
            "Não há botão Salvar: feche e retome depois.")

    def _arq_key(self, d) -> str:
        from app_qt.manual_dialog import arq_key as _ak
        return _ak(d)

    def _resolver_conflito(self, dlg, lado: str, sel, outro_ordem: int, minha_ordem: int) -> str:
        """Fase 3: documento ja vinculado em outro lancamento.
        Retorna 'mover' | 'manter' | 'cancelar'."""
        nome = getattr(sel, "nome", "?")
        tipo_txt = "Comprovante" if lado == "comprovante" else "Documento base"
        box = QMessageBox(dlg)
        box.setWindowTitle("Documento em uso")
        box.setText(
            f"{tipo_txt} '{nome}' já está vinculado ao lançamento "
            f"L{outro_ordem:03d}.\nDeseja desvincular de lá e vincular em "
            f"L{minha_ordem:03d}?")
        b_mover = box.addButton("Mover vínculo", QMessageBox.AcceptRole)
        box.addButton("Manter os dois", QMessageBox.ActionRole)
        box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(b_mover)
        box.exec()
        clicado = box.clickedButton()
        if clicado is not None and box.buttonRole(clicado) == QMessageBox.RejectRole:
            return "cancelar"
        if clicado is not None and box.buttonRole(clicado) == QMessageBox.ActionRole:
            return "manter"
        # MOVER: limpa o doador e congela como manual (Round 2 não re-preenche
        # sozinho — o doador cai para SEM_COMPROVANTE e vai aos Faltantes).
        doador = next((rr for rr in self.state.resultados
                       if rr.lancamento.ordem == outro_ordem), None)
        if doador is not None:
            if lado == "comprovante":
                doador.comprovante = None
                doador.score_comprovante = 0
            else:
                doador.documento_base = None
                doador.score_base = 0
            self._recalcular_status(doador)
            doador.ajustado_manual = True
            try:
                self.state.ordens_recibo.discard(outro_ordem)
            except Exception:  # noqa: BLE001
                pass
            self._reload_model()
        return "mover"

    def _recalcular_status(self, r) -> None:
        """Replica as regras de status/faltantes de _apply_manual p/ o doador."""
        comp, base = r.comprovante, r.documento_base
        if not comp:
            # Congela SEM_COMPROVANTE mas preserva base (regra 2026-10).
            r.status = StatusConciliacao.SEM_COMPROVANTE
            r.faltantes = ["Comprovante"]
            if r.lancamento.eh_saida and base is None:
                r.faltantes = ["Comprovante e Documento Base"]
        elif r.lancamento.eh_saida and not base:
            r.status = StatusConciliacao.PRECISA_RECIBO
            r.faltantes = ["Documento Base (PC/Boleto/Fatura)"]
        else:
            r.status = StatusConciliacao.CONCILIADO
            r.faltantes = []
        r.divergencias = []

    def _manual(self):
        r = self._current()
        if not r:
            QMessageBox.information(self, "Selecao", "Selecione um lancamento.")
            return
        # Mapa de uso atual {arquivo -> ordem}: o dialogo marca "ja em Lxxx"
        # e oferece mover o vinculo (Fase 3).
        usos: dict = {}
        try:
            for rr in self.state.resultados:
                o = rr.lancamento.ordem
                for lado in ("comprovante", "documento_base"):
                    d = getattr(rr, lado, None)
                    k = self._arq_key(d)
                    if k:
                        usos.setdefault(k, o)
        except Exception:  # noqa: BLE001
            usos = {}
        # Passa TODOS os docs (paridade Tk linha 1055): tipagem errada nao bloqueia
        ManualDialog(self, r, list(self.state.conciliador.documentos),
                     lambda s: self._apply_manual(r, s),
                     usos=usos, resolver=self._resolver_conflito).exec()

    def _apply_manual(self, r, sel: dict):
        # Replica ui/main_window.py::_confirmar_manual (linhas 1083-1100):
        # comprovante vazio = remove; base vazia p/ saída = PRECISA_RECIBO.
        comp = sel.get("comprovante")
        base = sel.get("base")
        r.comprovante = comp
        r.score_comprovante = 100 if comp else 0
        if r.lancamento.eh_saida:
            r.documento_base = base
            r.score_base = 100 if base else 0
        else:
            r.documento_base = None
            r.score_base = 0
        r.divergencias = []
        # Aviso IGNORÁVEL de divergência de data (decisão 2026-10: só aviso —
        # boleto pode vencer depois/do pagamento antes; usuário confere).
        # Não muda status nem bloqueia; aparece no painel de detalhe.
        if comp is not None and comp.data and r.lancamento.data:
            dias = abs((comp.data - r.lancamento.data).days)
            if dias > 2:
                r.divergencias.append(
                    f"Data: {r.lancamento.data} vs {comp.data} "
                    f"({dias} dias — conferir; pode ser normal p/ boleto/agendamento)")
        if not comp:
            # Remover só o comprovante NÃO apaga a base (decisão 2026-10: a
            # base pode ser legítima e reaproveitada; antes sumia junto).
            r.status = StatusConciliacao.SEM_COMPROVANTE
            r.faltantes = ["Comprovante"]
            if r.lancamento.eh_saida and not base:
                r.faltantes = ["Comprovante e Documento Base"]
        elif r.lancamento.eh_saida and not base:
            r.status = StatusConciliacao.PRECISA_RECIBO
            r.faltantes = ["Documento Base (PC/Boleto/Fatura)"]
        else:
            r.status = StatusConciliacao.CONCILIADO
            r.faltantes = []
        r.ajustado_manual = True
        # Sincronismo recibo<->manual (opção B simétrica): a caixinha continua
        # livre para marcar/desmarcar, mas acompanha o resultado — CONCILIADO
        # desmarca, PRECISA_RECIBO marca, SEM_COMPROVANTE desmarca (sem base).
        ord_ = r.lancamento.ordem
        if r.status == StatusConciliacao.PRECISA_RECIBO:
            self.state.ordens_recibo.add(ord_)
        else:
            self.state.ordens_recibo.discard(ord_)
        self._reload_model()
        self._reselect_ordem(r.lancamento.ordem)
        self._detail()
        self._say(f"L{r.lancamento.ordem:03d} manual OK (Round 2 não desfaz).")
        # Autosave IMEDIATO do manual (antes faltava: o manual se perdia ao
        # fechar e a sessão reabria com 0 ajustes manuais).
        self._agenda_autosave()
        try:
            self.toast.mostrar("Ajuste manual salvo na sessão")
        except Exception:
            pass

    def _reselect_ordem(self, ordem: int):
        for row in range(self.model.rowCount()):
            r = self.model.resultado_na_linha(row)
            if r and r.lancamento.ordem == ordem:
                self.table.selectRow(row)
                break

    def _recibos(self):
        if not self.state.ordens_recibo:
            QMessageBox.information(self, "Recibos", "Marque a coluna Recibo? primeiro.")
            return
        pasta = QFileDialog.getExistingDirectory(self, "Destino dos recibos")
        if not pasta:
            return
        marcados = [r for r in self.state.resultados
                    if r.lancamento.ordem in self.state.ordens_recibo
                    and r.status == StatusConciliacao.PRECISA_RECIBO and r.comprovante]
        if not marcados:
            QMessageBox.information(self, "Recibos", "Nenhum PRECISA_RECIBO marcado.")
            return
        try:
            arqs = gerar_recibos_para_faltantes(marcados, Path(pasta))
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Recibos", str(e))
            return
        for r in marcados:
            self.state.ordens_recibo.discard(r.lancamento.ordem)
            # Marca informativa: recibo gerado (antes só zerava o contador e
            # parecia que "voltou a pedir recibo").
            try:
                info = f"Recibo gerado: {r.documento_base.nome}"
                if info not in (r.divergencias or []):
                    r.divergencias = list(r.divergencias or []) + [info]
            except Exception:  # noqa: BLE001
                pass
        # Recibos .docx entram no índice p/ o restore religar (fora de pastas_docs).
        try:
            idx = {str(d.arquivo.resolve()) for d in self.state.conciliador.documentos}
            for a in arqs:
                if str(Path(a).resolve()) not in idx:
                    from core.models import DocumentoFinanceiro as _DF
                    from core.models import TipoDocumento as _TD
                    self.state.conciliador.documentos.append(_DF(
                        arquivo=Path(a), tipo=_TD.RECIBO))
        except Exception:  # noqa: BLE001
            pass
        self._reload_model()
        self._agenda_autosave()
        self.toast.mostrar(f"{len(arqs)} recibo(s) gerado(s) em {Path(pasta).name}")
        self._say(f"Recibos OK: {len(arqs)} arquivo(s).")
        abrir_pasta(pasta)

    def _faltantes(self):
        falt = self.state.conciliador.obter_faltantes()
        FaltantesDialog(self, falt).exec()

    def _pacote(self):
        """Empacota o mês inteiro em lote (paridade Tk `_gerar_pacotes`):
        um item por lançamento com documento, em ordem, dentro de
        `Pacote_Final_Ordenado/`. Não-PDF (recibo .docx) vai em pasta com
        os originais — sem conversão."""
        if getattr(self, "_working", False):
            return
        if not self.state.resultados:
            QMessageBox.information(self, "Pacote", "Sem resultados para empacotar.")
            return
        base = QFileDialog.getExistingDirectory(self, "Destino do pacote final")
        if not base:
            return
        self._busy(True, "Empacotando mês inteiro...")
        self.progress.setRange(0, 100)
        run_in_thread(self, empacotar_lote, self._ok_pacote, self._err,
                      self._on_progress,
                      list(self.state.resultados), Path(base))

    def _ok_pacote(self, res: dict):
        self._busy(False)
        try:
            n_pdf = len(res.get("pdfs", []))
            n_pas = len(res.get("pastas", []))
            n_pul = int(res.get("pulados", 0))
            erros = list(res.get("erros", []))
            local = res.get("dir", "")
            msg = (f"Pacote final: {n_pdf + n_pas} item(ns) em {local}\n\n"
                   f"PDFs mesclados: {n_pdf}\n"
                   f"Pastas (c/ não-PDF, originais): {n_pas}\n"
                   f"Pulados (sem arquivo): {n_pul}")
            if erros:
                msg += f"\n\nAvisos: {len(erros)} item(ns) com erro."
                msg += "\n" + "\n".join(str(e)[:100] for e in erros[:5])
            QMessageBox.information(self, "Pacote final", msg)
            self._say(f"Pacote final: {n_pdf + n_pas} item(ns).")
            try:
                abrir_pasta(local)
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Pacote", str(e))

    def _quick(self):
        r = self._current()
        if not r:
            QMessageBox.information(self, "Seleção",
                                    "Selecione um lançamento na tabela primeiro.")
            return
        alvo = (r.comprovante.arquivo if r.comprovante else None) or \
               (r.documento_base.arquivo if r.documento_base else None)
        if not alvo:
            QMessageBox.information(self, "Docs", "Sem documentos neste registro.")
            return
        QuickViewDialog(self, alvo, "Documento").exec()

    def _quick_kind(self, kind: str):
        r = self._current()
        if not r:
            return
        alvo = None
        titulo = "Documento"
        if kind == "comp" and r.comprovante:
            alvo = r.comprovante.arquivo
            titulo = "Comprovante"
        elif kind == "base" and r.documento_base:
            alvo = r.documento_base.arquivo
            titulo = "Documento Base"
        if not alvo:
            QMessageBox.information(self, "Docs", "Nada vinculado aqui. "
                                    "Use 'Conciliação manual' para vincular.")
            return
        QuickViewDialog(self, alvo, titulo).exec()

    def _click_base_vazia(self):
        # Campo vazio clicável: abre manual direto (fluxo que você pediu)
        r = self._current()
        if not r:
            return
        if r.documento_base and r.documento_base.arquivo:
            self._quick_kind("base")
        else:
            self._manual()

    def _menu_tabela(self, pos):
        idx = self.table.indexAt(pos)
        if idx.isValid():
            self.table.selectRow(idx.row())
        menu = QMenu(self)
        a_man = menu.addAction("Conciliação manual (M)")
        a_man.triggered.connect(self._manual)
        a_view = menu.addAction("Quick View (Enter)")
        a_view.triggered.connect(self._quick)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_M,):
            if self.state.resultados:
                self._manual()
                return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.state.resultados:
                self._quick()
                return
        super().keyPressEvent(e)

    def _detail(self):
        r = self._current()
        if not r:
            self.txt.setPlainText("Selecione um lancamento.")
            return
        L = [f"L{r.lancamento.ordem:03d} | {format_data(r.lancamento.data)} | "
             f"R$ {format_decimal_br(r.lancamento.valor_absoluto)}",
             f"Status: {r.status.value}",
             f"Extrato: {(r.lancamento.descricao or '')[:240]}", "",
             f"Comprovante: {r.comprovante.nome if r.comprovante else 'NAO ENCONTRADO'}",
             f"Base: {r.documento_base.nome if r.documento_base else 'NAO ENCONTRADO'}", "",
             f"Score comp: {r.score_comprovante} | Score base: {r.score_base}"]
        if r.divergencias:
            L += ["", "Divergencias:"] + [f"  - {d}" for d in r.divergencias]
        if r.faltantes:
            L += ["", "Faltantes:"] + [f"  - {f}" for f in r.faltantes]
        self.txt.setPlainText("\n".join(L))
        comp_path = r.comprovante.arquivo if r.comprovante else None
        base_path = r.documento_base.arquivo if r.documento_base else None
        try:
            self.mini_comp.set_doc(comp_path, "Comprovante — clique p/ ampliar")
            self.mini_base.set_doc(base_path, "Documento Base — clique p/ ampliar")
        except Exception:
            pass
        self.lbl_comp.setText(f"Comp: {r.comprovante.arquivo.name if r.comprovante else '-'}")
        self.lbl_base.setText(f"Base: {r.documento_base.arquivo.name if r.documento_base else '-'}")
