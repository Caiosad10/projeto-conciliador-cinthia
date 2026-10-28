# app_qt/theme.py — Identidade "Claro Moderno" (canvas cinza + cards brancos + navy accent)
# Nota: este arquivo + app_qt/qss.py são a fonte da verdade visual
# (o antigo TEMPLATE.md "Escritório Administrativo" foi descontinuado).
from __future__ import annotations

NAVY = "#1F3864"
NAVY_HOVER = "#2A4A85"
NAVY_PRESS = "#16294A"
NAVY_SOFT = "#C7D3EA"
CANVAS = "#F5F6F8"        # fundo da janela (era #FFFFFF)
SURFACE = "#FFFFFF"       # cards, listas, inputs
TEXT = "#1B2430"
MUTED = "#667085"
PLACEHOLDER = "#98A2B3"
BORDER = "#E6E9EF"        # borda sutil de superfície (era #DDE3EC)
BORDER_STRONG = "#D5DAE3"  # borda de controle (era #CCD4E0)
SUBTLE = "#EEF1F6"        # hover soft / fundo de chip
HOVER_ROW = "#F4F7FC"
SELECTED_ROW = "#E7EFFB"
ACCENT = "#2E75B6"
DANGER = "#C62828"
DANGER_BORDER = "#E5B8B8"
DANGER_HOVER = "#FDF3F3"
WARN_BG = "#FFF7E6"
WARN_BORDER = "#F0C36D"
WARN_TEXT = "#8A5A00"
PROGRESS_BG = "#EDF0F5"

# Raios (era tudo 6/8 do template)
RADIUS_CARD = 12
RADIUS_CTRL = 8

# Chips de status (contraste sobre fundo branco, WCAG AA em 9pt bold)
CHIP_CONCILIADO = "#1E7A46"
CHIP_PENDENCIA = "#B26B00"
CHIP_PERIGO = "#C62828"
CHIP_NEUTRO = "#667085"

STATUS_COLORS = {
    "CONCILIADO": "#1E7A46",
    "ATENCAO": "#B26B00",
    "DIVERGENTE": "#C62828",
    "SEM_COMPROVANTE": "#C62828",
    "FALTANDO": "#C62828",
    "PRECISA_RECIBO": "#B26B00",
}
CATEGORY_COLORS = {
    "comprovante": "#2E75B6",
    "pc": "#1F3864",
    "boleto": "#C0392B",
    "fatura": "#8E44AD",
    "guia": "#B7791F",
    "recibo": "#1E7A46",
    "extrato": "#1F3864",
    "outro": "#667085",
}

ROW_HEIGHT = 42
