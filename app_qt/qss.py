# app_qt/qss.py — Folha de estilo "Claro Moderno"
# canvas cinza #F5F6F8 + superfícies brancas com raios 12/8 + navy só como accent.
# Contrato de objectName preservado (PrimaryBtn, Banner, MutedLabel...) para não
# quebrar as chamadas existentes; novos: TopMenuBar, KpiPanel, ToolGroupLabel,
# ToolbarSep, StatusBar, Toast.
from __future__ import annotations

QSS = """
/* ================= Base: canvas cinza ================= */
QMainWindow, QDialog { background: #F5F6F8; }
QWidget { color: #1B2430; font-size: 9pt; }
QToolTip { background: #1B2430; color: #FFFFFF; border: none; padding: 4px 7px; font-size: 8pt; }

/* ================= Topbar / menu ================= */
QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E6E9EF; padding: 2px 6px; }
QMenuBar::item { background: transparent; padding: 6px 10px; border-radius: 6px; color: #4C566A; }
QMenuBar::item:selected { background: #EEF1F6; color: #1F3864; }
QMenuBar::item:pressed { background: #E1E7F0; color: #1F3864; }
QMenu { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 7px 26px 7px 14px; border-radius: 6px; color: #1B2430; }
QMenu::item:selected { background: #E7EFFB; color: #1F3864; }
QMenu::item:disabled { color: #98A2B3; }
QMenu::separator { height: 1px; background: #E6E9EF; margin: 5px 8px; }
QLabel#TopbarTitle { color: #1F3864; font-size: 13pt; font-weight: 700; }
QLabel#TopbarSub { color: #98A2B3; font-size: 8pt; padding-bottom: 1px; }
QMenuBar::item:disabled { color: #1F3864; font-weight: 700; font-size: 12pt; }
QMenuBar::separator { width: 1px; background: #E6E9EF; margin: 6px 4px; }

/* ================= Banner ================= */
#Banner { background: #FFF7E6; border: 1px solid #F0C36D; border-radius: 8px; }
#BannerLabel { color: #8A5A00; }

/* ================= Painel de métricas (métrica = filtro) ================= */
QFrame#KpiPanel { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 12px; }
QFrame#KpiCel { background: transparent; border: none; border-radius: 10px; }
QFrame#KpiCel:hover { background: #F4F7FC; }
QFrame#KpiCel[ativo="true"] { background: #E7EFFB; }
QFrame#KpiDiv { background: #E6E9EF; border: none; min-width: 1px; max-width: 1px; }
QLabel#KpiValue { color: #1F3864; font-size: 18pt; font-weight: 700; }
QLabel#KpiLabel { color: #667085; font-size: 8pt; font-weight: 600; }

/* ================= Toast (sucesso efêmero, não-modal) ================= */
QFrame#Toast { background: #1B2430; border-radius: 8px; }
QLabel#ToastLabel { color: #FFFFFF; font-size: 9pt; }

/* ================= Overlay de progresso (modal, bloqueia cliques) ================= */
/* Sem véu escuro: só o card flutuante aparece; o fundo transparente engole cliques */
QWidget#ProgressOverlay { background: transparent; }
QWidget#ProgressOverlay QProgressBar { min-height: 18px; max-height: 18px; }
QWidget#ProgressOverlay QFrame#StatusBar { border: 1px solid #9FB1CC; }

/* ================= Toolbar agrupada ================= */
QLabel#ToolGroupLabel { color: #98A2B3; font-size: 8pt; font-weight: 700; padding: 0 4px; }
QFrame#ToolbarSep { background: #E6E9EF; border: none; min-width: 1px; max-width: 1px; }

/* ================= Botões ================= */
QPushButton { background: #FFFFFF; border: 1px solid #D5DAE3; border-radius: 8px; padding: 6px 14px; color: #1B2430; }
QPushButton:hover { background: #F2F5FA; border-color: #9FB1CC; }
QPushButton:pressed { background: #E7ECF5; }
QPushButton:disabled { background: #F5F6F8; color: #A7AFBC; border-color: #E5E8EE; }
QPushButton#PrimaryBtn { background: #1F3864; border-color: #1F3864; color: #FFFFFF; font-weight: 600; }
QPushButton#PrimaryBtn:hover { background: #2A4A85; border-color: #2A4A85; }
QPushButton#PrimaryBtn:pressed { background: #16294A; border-color: #16294A; }
QPushButton#PrimaryBtn:disabled { background: #AEB9CE; border-color: #AEB9CE; color: #F0F2F6; }
QPushButton#DangerBtn { color: #C62828; border: 1px solid #E5B8B8; background: #FFFFFF; }
QPushButton#DangerBtn:hover { background: #FDF3F3; border-color: #C62828; }
QPushButton#LinkBtn { background: transparent; border: none; color: #2E75B6; font-weight: 600; padding: 4px 6px; }
QPushButton#LinkBtn:hover { color: #1F3864; }
QPushButton#MiniBtn { padding: 6px 9px; font-weight: 600; }
QPushButton#HeaderBtn { background: rgba(31,56,100,0.08); color: #1F3864; border: 1px solid rgba(31,56,100,0.25); border-radius: 8px; padding: 6px 14px; font-weight: 600; }
QPushButton#HeaderBtn:hover { background: rgba(31,56,100,0.16); }

/* ================= Rótulos ================= */
QLabel#SummaryLabel { color: #4C566A; }
QLabel#MutedLabel { color: #667085; }
QLabel#EmptyHint { color: #98A2B3; font-size: 11pt; }
QLabel#SectionTitle { color: #1F3864; font-size: 11pt; font-weight: 700; }
QLabel#StatusLabel { color: #667085; font-size: 8pt; }

/* ================= Tabela (card flutuante) ================= */
QTableView { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 12px; outline: none; gridline-color: #F0F2F6; selection-background-color: #E7EFFB; selection-color: #1B2430; }
QTableView::item { padding: 4px 6px; border: none; }
QTableView::item:hover { background: #F4F7FC; }
QHeaderView::section { background: #FAFBFC; color: #667085; border: none; border-bottom: 1px solid #E6E9EF; padding: 8px 6px; font-weight: 700; font-size: 8pt; }
QListWidget { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 12px; outline: none; color: #1B2430; }
QTextEdit { background: #FFFFFF; color: #1B2430; border: 1px solid #E6E9EF; border-radius: 12px; selection-background-color: #1F3864; selection-color: #FFFFFF; }
QGraphicsView { background: #2B2F36; border: 1px solid #E6E9EF; border-radius: 12px; }

/* ================= Abas painel direito ================= */
QTabWidget::pane { border: 1px solid #E6E9EF; border-radius: 12px; background: #FFFFFF; top: -1px; }
QTabBar::tab { background: transparent; color: #667085; border: none; border-bottom: 2px solid transparent; padding: 7px 16px; margin-right: 2px; font-weight: 600; }
QTabBar::tab:selected { color: #1F3864; border-bottom-color: #1F3864; }
QTabBar::tab:hover:!selected { color: #1F3864; }

/* ================= Inputs ================= */
QLineEdit, QSpinBox, QComboBox { background: #FFFFFF; border: 1px solid #D5DAE3; border-radius: 8px; padding: 6px 9px; color: #1B2430; selection-background-color: #1F3864; selection-color: #FFFFFF; min-height: 16px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #2E75B6; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 8px; selection-background-color: #E7EFFB; selection-color: #1B2430; }

/* ================= Progresso ================= */
QProgressBar { background: #EDF0F5; border: 1px solid #E0E5EE; border-radius: 7px; min-height: 14px; max-height: 14px; text-align: center; font-size: 8pt; color: #4C566A; }
QProgressBar::chunk { background: #2E75B6; border-radius: 6px; }

/* ================= Rodapé (status card) ================= */
#StatusBar { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 8px; }

/* ================= Splitter ================= */
QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 8px; }

/* ================= Scrollbars finas ================= */
QScrollBar:vertical { background: transparent; width: 9px; margin: 0; border: none; }
QScrollBar::handle:vertical { background: #CBD3E0; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #A9B4C8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 9px; background: transparent; border: none; }
QScrollBar::handle:horizontal { background: #CBD3E0; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { height: 0; width: 0; }
"""
