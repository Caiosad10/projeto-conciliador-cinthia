# Template — Aplicativo de Fluxo

Kit de composição de **telas de trabalho** (conciliação, filas, cadastros,
painéis de controle) para **PySide6**, sem dependências externas. Foca na
**filosofia de interação e na anatomia de tela** — o que fazer, onde colocar
e — sobretudo — o que **não** colocar.

- **Origem:** cada regra nasceu de feedback real sobre a interface do
  Conciliador INCA (Qt). As seções marcam a origem em *"Por que funciona"*.
- **Princípio dos princípios:** o usuário precisa **descobrir** a ação pelo
  menu, **acelerar** pelo atalho e **repetir** pela toolbar. Se uma peça não
  cumpre nesses três papéis, ela é ruído.
- **Nada aqui exige biblioteca:** só PySide6 + QSS embutido em string.

## Índice

1. [Filosofia — 6 princípios](#1-filosofia--6-princípios)
2. [Anatomia da tela](#2-anatomia-da-tela)
3. [Topbar e menus](#3-topbar-e-menus)
4. [Toolbar de processo](#4-toolbar-de-processo)
5. [Painel de métricas (KPIs)](#5-painel-de-métricas-kpis)
6. [Notificações — banner × toast × statusbar](#6-notificações--banner--toast--statusbar)
7. [Esqueleto list-detail](#7-esqueleto-list-detail)
8. [Tabela](#8-tabela)
9. [StatusBar](#9-statusbar)
10. [Tokens resumidos](#10-tokens-resumidos)
11. [Checklist de aceite e anti-padrões](#11-checklist-de-aceite-e-anti-padrões)
12. [Anexo: snippets copiáveis](#12-anexo-snippets-copiáveis)

---

## 1. Filosofia — 6 princípios

1. **Descoberta → velocidade.** Toda ação existe em três velocidades:
   `menu` (descobre, com atalho visível ao lado) → `atalho` (acelera, já
   aprendido) → `toolbar` (só as de alta frequência do processo).
   *Origem: "gostei das funções ao lado do título … mostra o atalho …
   nostalgia com visual moderno".*

2. **Hierarquia: uma ação primária por área.** Navy (`#1F3864`) só no
   comando que move o processo (ex.: *Conciliar*). Todo o resto é secundário
   (borda leve, fundo branco). Se tudo é destaque, nada é.
   *Origem: "o Toolbar só é válido para a questão do processo".*

3. **Um controle por semântica.** Se dois controles fazem o mesmo filtro,
   um deles é ruído — remova. Mas então o controle restante **precisa
   mostrar o estado ativo** (senão o usuário não sabe onde está).
   *Origem: "o filtro, possa ser desnecessário … vejo que só polui".*

4. **Três níveis de feedback, três durabilidades.** Contextual que exige
   ação (*banner*), sucesso efêmero (*toast*), estado persistente
   (*statusbar*). Nunca modal para informar.
   *Origem: "o banner poderia ser outra forma de notificações".*

5. **Esqueleto list-detail com splitter.** Lista sempre visível + contexto
   ao lado, nunca modal; o usuário controla a proporção. O painel de contexto
   segue 5 níveis: resumo → ação primária do contexto → evidências visuais →
   metadados → dica.
   *Origem: "gostei do layout do painel direito … dá para aplicar em outros
   contextos".*

6. **Cor é semântica, não decoração.** Cor categoriza status/tipo (chip na
   célula), nunca pinta botão comum nem texto corrido. Fundo cinza-claro,
   superfícies brancas, profundidade por borda de 1px — sem sombras.
   *Origem: chips da tabela e tokens "Claro Moderno" aprovados.*

## 2. Anatomia da tela

```
┌─ TOPBAR (QMenuBar branca, borda inferior 1px) ────────────────────────────┐
│ TituloDoApp │ Arquivo ▾  Processo ▾  Ferramentas ▾  Ajuda ▾   (atalhos↗) │
├─ BANNER (só quando exige ação — oculto no estado normal) ─────────────────┤
│ ⚠ Extrato OK. Adicione as pastas de documentos (Ctrl+D).                  │
├─ PAINEL DE MÉTRICAS (card único, divisórias internas) ────────────────────┤
│   8        │  4           │  4          │ 2       │ 2                    │
│   TOTAL    │  CONCILIADOS │  PENDÊNCIAS │ RECIBOS │ MARCADOS             │
│            ▲ clique filtra · ativo ganha fundo selecionado · repete=limpa │
├─ TOOLBAR DE PROCESSO (só pipeline, ordem cronológica) ────────────────────┤
│  PROCESSO: [Conciliar*] Reconciliar  ·  SAÍDA: Recibos Faltantes Empacotar│
│                                 (nenhum Filtro aqui — os cards filtram)   │
├─ QSPLITTER HORIZONTAL ─────────────────────┬─ PAINEL DE CONTEXTO ─────────┤
│ QTableView (seleção → painel)              │ 1. Resumo curto (texto)      │
│ · chips coloridos na coluna de status      │ 2. Ação primária do contexto │
│ · checkbox in-place                        │ 3. Evidências (miniaturas ↗) │
│ · menu de contexto = atalhos do painel     │ 4. Metadados (labels cinzas) │
│ · duplo clique = ampliar                   │ 5. Dica de uso              │
├─ STATUSBAR (card branco contínuo) ──────────┴─────────────────────────────┤
│ 160 lanc. | 8 conc. │ [──── progresso embutido ────] │ última ação       │
└───────────────────────────────────────────────────────────────────────────┘
```

Critério de inclusão — se a peça não tem resposta clara, **não adicione**:

| Peça | Usar quando | Não usar quando |
|---|---|---|
| Banner | estado intermediário exige ação do usuário | mensagem de sucesso/erro pontual (→ toast) |
| Painel de métricas | existem ≥ 3 subconjuntos navegáveis dos dados | tela tem 1 estado só |
| Toolbar | ação repetida várias vezes por sessão | ação executada 1–2×/dia (→ menu) |
| Splitter | lista + contexto correlacionados | contexto é o foco total (→ tela cheia) |
| StatusBar | sempre (fecha a tela, dá certeza de estado) | — |

*Origem: "o Toolbar achei desnecessário para a questão de Dados … só acho
válido para o processo".*

---

## 3. Topbar e menus

A topbar é o `QMenuBar` do `QMainWindow` — branca, borda inferior 1px,
altura nativa (~26px). Ela faz **três** trabalhos: identidade, navegação e
ensino de atalhos.

**Regras:**

1. **Título embutido** como primeira posição, visualmente distinto (navy,
   bold, 12pt) e **não clicável** (ação desabilitada funciona bem e evita
   problemas de `QWidgetAction` no `QMenuBar` do Qt 6).
2. **3–4 menus no máximo**, na ordem de frequência:
   - `Arquivo` — entrada de dados (abrir, importar) com atalhos `Ctrl+O`,
     `Ctrl+D`; separador; `Sair` `Ctrl+Q`.
   - `<Processo>` — ações do domínio, na ordem do pipeline, com o atalho
     (`F5`, `M`…). É o menu que espelha a toolbar.
   - `Ferramentas>` — utilitários (visualizar, empacotar, exportar).
   - `Ajuda` — **obrigatório**: `Atalhos` (lista todos) e `Sobre`. O app se
     documenta sozinho.
3. **Atalho visível ao lado de cada item** — é o motor da "descoberta
   passiva": o usuário vê `Ctrl+O` dez vezes antes de usar.
4. **Ações de menu espelham os botões** (mesmo *handler*), habilitando e
   desabilitando em conjunto — uma lista de pares `(ação, botão)` resolvida
   nos mesmos métodos de estado.
5. Menu é **descoberta**, não lugar de truque: tudo que o menu tem, o
   usuário deve achar também no fluxo visual (toolbar/painel) ou no `Ajuda`.

```python
# Esqueleto (QMainWindow.__init__)
mb = self.menuBar()
a_tit = mb.addAction("  Meu Aplicativo  ")   # título embutido
a_tit.setEnabled(False)                      # não clicável
mb.addSeparator()
m_arq = mb.addMenu("Arquivo")
a_abrir = m_arq.addAction("Abrir…")
a_abrir.setShortcut(QKeySequence("Ctrl+O"))
a_abrir.triggered.connect(self._abrir)
# … Ajuda → Atalhos (QMessageBox com a tabela) e Sobre
```

---

## 4. Toolbar de processo

A toolbar **não** é atalho visual do menu — é a **linha do tempo do
processo**. Passe no teste antes de adicionar um botão:

- [ ] É repetida ≥ 5× por sessão de trabalho?
- [ ] Faz parte do pipeline (entrada → processamento → saída)?
- [ ] Já existe no `Arquivo`/`Processo` do menu (para descoberta)?

Requisitos satisfeitos + **falta um** → toolbar. Senão, só menu.

**Composição:**

```
[RÓTULO GRUPO] botão botão │ [RÓTULO] botão │  …stretch…   Filtro do usuário
   8pt bold, cinza     divisor vertical 1px    (rótulo aqui só se houver
   maiúsculas                              controle real de usuário, ex.: busca)
```

1. **Grupos na ordem cronológica** do pipeline com rótulo + divisor — o
   próprio layout ensina o fluxo.
2. **Uma única ação primária** (navy) — a próxima etapa do processo.
3. **Proibidos:** abrir arquivo/pasta (menu `Arquivo`), filtros que os
   cards já cobrem, configurações, ajuda.
4. Rótulo do grupo em maiúsculas cinza-claro; sem rótulo, o grupo não
   comunica ordem — prefira manter.

```python
def _grupo(lay, rotulo, *botoes):
    lb = QLabel(rotulo.upper()); lb.setObjectName("ToolGroupLabel")
    lay.addWidget(lb)
    for b in botoes:
        lay.addWidget(b)
    sep = QFrame(); sep.setObjectName("ToolbarSep"); sep.setFixedWidth(1)
    lay.addWidget(sep)
```

## 5. Painel de métricas (KPIs)

**Métrica é porta de entrada:** o número não decora — ele *filtra*. Clique
no valor → tabela mostra só aquele subconjunto. Isso substitui combos de
filtro: um controle, uma semântica.

**Regras (todas obrigatórias):**

1. **Card único com divisórias internas** — 5 números soltos parecem 5
   widgets brigando; um painel lê como "instrumento". Uma borda, um raio 12,
   divisórias `1px #E6E9EF`.
2. **Estado ativo visível:** a célula filtrada ganha fundo `#E7EFFB` e o
   valor navy. Sem isso, remover o combo deixa o usuário cego
   (*"o filtro só polui"* só é verdade se os cards assumirem o papel).
3. **Clicar de novo limpa** (volta a `TODOS`) — o próprio painel é o botão
   "limpar filtro".
4. **Hierarquia tipográfica fixa:** valor 18pt bold navy / rótulo 8pt bold
   cinza maiúsculo, sempre alinhados à esquerda, mesma linha de base.
5. Valores atualizam junto do resumo (um único método `atualizar()` no
   model/window) — números dessincronizados destroem a confiança.

```
┌ Métricas ────────────────────────────────────────────────────────┐
│  8        │  4           │  4          │ 2       │ 2             │
│  TOTAL    │  CONCILIADOS │  PENDÊNCIAS │ RECIBOS │ MARCADOS      │
└───────────┴──────────────┴─────────────┴─────────┴───────────────┘
   célula ativa:  ┌──────────────┐          clique no ativo = limpar
                  │ 4  (fundo    │
                  │ CONCILIADOS  │
                  └──────────────┘
```

Variante compacta (pouca altura): painel de uma linha só, valores 13pt,
rótulos 8pt — mesma estrutura de código.

*Anti-padrão aprovado pelo feedback: "combo Filtro ao lado dos cards = só
polui". Nunca entregue os dois.*

---

## 6. Notificações — banner × toast × statusbar

| | Banner | Toast | StatusBar |
|---|---|---|---|
| **Pergunta** | "O que preciso **fazer**?" | "O que **acabou** de acontecer?" | "Onde **estou**?" |
| **Durabilidade** | enquanto o estado avança | 2–4 s, auto-dismiss | permanente |
| **Posição** | topo, abaixo da topbar | canto inferior direito, flutuando | rodapé fixo |
| **Ação?** | sim (botão/atalho no texto) | não | não |
| **Exemplo** | "Extrato OK — adicione as pastas (Ctrl+D)" | "3 recibos gerados em X" | "160 lanc. | 8 conc." |

1. **Banner** nunca é decorativo: se o estado avançou, some (chame
   `setVisible(False)` na transição). Um banner eterno vira ruído.
2. **Toast** para sucesso/erro pontual de ação concluída — substitua os
   `QMessageBox.information` de confirmação ("N recibos gerados") que só
   atrapalham o fluxo. Erros destrutivos/erro de sistema continuam em
   `QMessageBox.critical`.
3. **Statusbar** recebe o texto curto da última ação (log de uma linha) —
   o toast é o statusbar que *some*.
4. Nunca dois canais simultâneos para a mesma mensagem.

```python
# banner: crie escondido e só mostre quando houver ação pendente
banner.setVisible(False)
...
self.banner_lbl.setText("Extrato OK. Adicione as pastas (Ctrl+D).")
self.banner.setVisible(True)      # some em _ok_docs/_ok_conc
```

---

## 7. Esqueleto list-detail

Aparência aprovada para qualquer "tabela + explicação/contexto". Esqueleto
reaplicável: `QSplitter(Horizontal)` com `QTableView` à esquerda e um
`QWidget` de 5 níveis à direita.

```python
split = QSplitter(Qt.Horizontal)
split.addWidget(self.table)                 # lista virtualizada
split.addWidget(self.painel_contexto)       # 5 níveis abaixo
split.setSizes([880, 520])                  # persistir com QSettingsDepois
lay.addWidget(split, 1)                     # stretch 1 = começa o resto
```

**Anatomia do painel de contexto (ordem obrigatória):**

1. **Resumo curto** — `QTextEdit`/`QLabel` com o essencial (o quê, quanto,
   status). Teto de altura (150–200px): é leitura, não arquivo.
2. **Ação primária do contexto** — o comando específico do item selecionado
   (ex.: *Conciliação manual* `M`), colada embaixo do resumo, navy se for o
   caminho feliz; atalho no tooltip.
3. **Evidências visuais** — miniaturas clicáveis (documento/imagem) lado a
   lado; clicar abre visor em tela cheia (modal **só** para visualização).
   Miniatura vazio = convite explícito ("clique p/ vincular").
4. **Metadados** — labels cinzas (`MutedLabel`), chave-valor curtos.
5. **Dica de uso** — uma frase, última posição, sempre presente ("botão
   direito na tabela = menu rápido").

**Regras de comportamento:**

- Seleção da linha alimenta o painel (`selectionChanged → atualizar()`),
  nunca modal, nunca aba escondida — tudo visível de uma vez quando couber.
- Duplo clique / `Enter` = ampliar (mesmo comando da miniatura).
- Menu de contexto da tabela = **atalhos do painel** (mesmas ações), para
  quem prefere mouse.
- O painel deve sobreviver a seleção vazia ("Selecione um lançamento").
- Splitter: o usuário pode restringir, mas a janela mínima de cada lado
  garante legibilidade (ex.: direito ≥ 420px).

*Origem: "gostei do layout do painel direito, a função dele é muito boa e
dá para aplicar em outros contextos".*

## 8. Tabela

A lista é o coração — **não há para onde fugir** (feedback aprovado); o
segredo é o acervo de comportamentos, não o visual:

- **Virtualizada** — `QAbstractTableModel` + `QTableView` aguenta milhares
  de linhas sem paginação (nunca `QTableWidget` com widgets-célula).
- **Seleção de linha alimenta o painel** (SingleSelection); a linha
  selecionada é a fonte da verdade do painel de contexto.
- **Chip de status na célula**: fundo `cor com alpha 38` + texto na cor
  sólida — a coluna de status vira faixa colorida legível. Cores por
  semântica (verde ok / âmbar atenção / vermelho problema / cinza neutro),
  vindas de um único dicionário de tokens.
- **Checkbox in-place** na coluna de ação (ex.: "Recibo?") — decidir sem
  sair da linha; o estado mora num `set` do model, sincronizado com o
  estado global via callback.
- **Menu de contexto** = atalhos do painel (ações principais + atalho no
  texto do item).
- **Duplo clique / Enter** = ampliar o item (visor do documento).
- Cabeçalho: 8pt bold cinza, fundo `#FAFBFC`, borda só inferior; larguras
  fixas nas colunas curtas, `Stretch`/resíduo na última.
- Linha de 30–42px; hover `#F4F7FC`; seleção `#E7EFFB` com texto navy.

## 9. StatusBar

O "acabamento perfeito" (feedback) — uma faixa `QFrame` branca com borda e
raio 8, altura fixa, fechando a janela:

```
[ resumo agregado ] ── stretch ── [ progresso embutido ] [ última ação ]
   9pt, atualiza com          240px, oculto sem          8pt cinza,
   os dados (KPIs/log)        trabalho (não é linha      texto curto
                              própria do layout!)
```

1. **Uma linha só para tudo** — o `QProgressBar` mora *dentro* do rodapé
   (largura fixa 240px); nunca uma faixa separada só para progresso (rouba
   altura vertical da tabela).
2. Resumo à esquerda sempre visível = segurança de estado sem clicar em
   lugar nenhum.
3. Última ação à direita (ex.: "L008 manual OK") — log vivencial de uma
   linha.
4. Progresso **determinate** quando há % (parse de arquivos) e
   **indeterminate** (`setRange(0,0)`) só em processos sem % (conciliação);
   ao terminar, some da barra mas deixa a confirmação no texto.

```python
bottom = QFrame(); bottom.setObjectName("StatusBar")
bot = QHBoxLayout(bottom); bot.setContentsMargins(10, 4, 10, 4)
self.lbl_resumo = QLabel("Nenhum dado carregado"); self.lbl_resumo.setObjectName("SummaryLabel")
bot.addWidget(self.lbl_resumo); bot.addStretch(1)
self.progress = QProgressBar(); self.progress.setVisible(False); self.progress.setFixedWidth(240)
bot.addWidget(self.progress)
self.lbl_status = QLabel("Pronto"); self.lbl_status.setObjectName("StatusLabel")
bot.addWidget(self.lbl_status)
```

---

## 10. Tokens resumidos

O pacote visual "Claro Moderno" aprovado neste projeto — a fonte canônica
é `app_qt/theme.py` + `app_qt/qss.py`:

| Token | Valor | Papel |
|---|---|---|
| `CANVAS` | `#F5F6F8` | fundo da janela (nunca branco puro) |
| `SURFACE` | `#FFFFFF` | cards, tabela, inputs |
| `BORDER` | `#E6E9EF` | toda borda de superfície (1px, sem sombra) |
| `RADIUS_CARD` | `12` | cards, tabela, painéis |
| `RADIUS_CTRL` | `8` | botões, inputs, menus |
| `NAVY` | `#1F3864` | **só**: título, ação primária, valor de KPI, seleção/aba ativa |
| `ACCENT` | `#2E75B6` | progresso, foco, hover de link |
| `SELECTED_ROW` | `#E7EFFB` | seleção de linha **e** célula de métrica ativa |
| `TEXT` / `MUTED` | `#1B2430` / `#667085` | texto principal / secundário |

Regra de ouro mantida: **nenhuma sombra** (`QGraphicsDropShadowEffect` é
anti-padrão aqui); profundidade = borda + contraste de fundo.

---

## 11. Checklist de aceite e anti-padrões

Checklist (passe antes de entregar a tela):

- [ ] Título do app na topbar + 3–4 menus + `Ajuda > Atalhos`
- [ ] Todo item de menu visível mostra o atalho; ações de menu e botões
      habilitam/desabilitam juntos
- [ ] Toolbar só com pipeline, grupos cronológicos, 1 primário navy
- [ ] Nenhum controle duplicado (combo de filtro vs. cards)
- [ ] Painel de métricas: card único, estado ativo visível, clique limpa
- [ ] Banner some quando o estado avança; sucesso pontual vai para toast
- [ ] Splitter list-detail com os 5 níveis do painel, na ordem
- [ ] Chips de status coloridos; seleção alimenta o painel
- [ ] Statusbar com resumo + progresso embutido + última ação
- [ ] Todos os `objectName` usados existem no QSS (contrato)

Anti-padrões (do feedback real):

| Anti-padrão | Por que falha | Em vez disso |
|---|---|---|
| Combo de filtro ao lado de cards clicáveis | duplica semântica, polui ("só polui") | remover combo; estado ativo no card |
| Toolbar com abrir-arquivo/pasta | pipeline ≠ entrada; menu já cobre | `Arquivo` com `Ctrl+O`/`Ctrl+D` |
| 5 cards KPI soltos, sem estado ativo | visual fragmentado ("achei feio") + usuário cego | painel único com divisórias + destaque |
| Filtro escondido só em combo | estado invisível | métrica = filtro, sempre à vista |
| `QMessageBox.information` para sucesso | quebra o fluxo | toast / statusbar |
| Banner eterno (nunca some) | vira decoração | somente enquanto exige ação |
| Modal para ver documento da linha | pesado demais para olhar | miniatura no painel + modal só p/ tela cheia |
| Linha extra só de progresso | rouba altura | progresso embutido no statusbar |
| Sombra/QSS cinza-escuro de dashboard | quebra leitura de documento | fundo `#F5F6F8`, borda 1px, sem sombra |
| Tudo navy (ação, barras, progresso) | perde hierarquia | navy: título, primário, KPI ativo |

## 12. Anexo: snippets copiáveis

Todos os trechos abaixo são PySide6 puro (testados com
`py_compile` + instanciação offscreen). QSS em string, aplicado uma vez em
`main()`.

### 12.1 QSS da topbar + menus

```css
QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E6E9EF; padding: 2px 6px; }
QMenuBar::item { background: transparent; padding: 6px 10px; border-radius: 6px; color: #4C566A; }
QMenuBar::item:selected { background: #EEF1F6; color: #1F3864; }
QMenuBar::item:disabled { color: #1F3864; font-weight: 700; font-size: 12pt; }  /* título embutido */
QMenuBar::separator { width: 1px; background: #E6E9EF; margin: 6px 4px; }
QMenu { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 7px 26px 7px 14px; border-radius: 6px; color: #1B2430; }
QMenu::item:selected { background: #E7EFFB; color: #1F3864; }
QMenu::item:disabled { color: #98A2B3; }
QMenu::separator { height: 1px; background: #E6E9EF; margin: 5px 8px; }
QLabel#ToolGroupLabel { color: #98A2B3; font-size: 8pt; font-weight: 700; padding: 0 4px; }
QFrame#ToolbarSep { background: #E6E9EF; border: none; min-width: 1px; max-width: 1px; }
```

### 12.2 QSS do statusbar

```css
#StatusBar { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 8px; }
QLabel#SummaryLabel { color: #4C566A; }
QLabel#StatusLabel { color: #667085; font-size: 8pt; }
QProgressBar { background: #EDF0F5; border: 1px solid #E0E5EE; border-radius: 7px;
               min-height: 14px; max-height: 14px; text-align: center;
               font-size: 8pt; color: #4C566A; }
QProgressBar::chunk { background: #2E75B6; border-radius: 6px; }
```

### 12.3 QSS do painel de métricas

```css
QFrame#KpiPanel { background: #FFFFFF; border: 1px solid #E6E9EF; border-radius: 12px; }
QFrame#KpiCel  { background: transparent; border: none; border-radius: 10px; }
QFrame#KpiCel:hover { background: #F4F7FC; }
QFrame#KpiCel[ativo="true"] { background: #E7EFFB; }
QFrame#KpiDiv  { background: #E6E9EF; border: none; min-width: 1px; max-width: 1px; }
QLabel#KpiValue { color: #1F3864; font-size: 18pt; font-weight: 700; }
QLabel#KpiLabel { color: #667085; font-size: 8pt; font-weight: 600; }
```

### 12.4 QSS do toast

```css
QFrame#Toast { background: #1B2430; border-radius: 8px; }
QLabel#ToastLabel { color: #FFFFFF; font-size: 9pt; }
```

### 12.5 `KpiPanel` — card único, divisórias, clique-filtro, estado ativo

```python
# painel_kpi.py — PySide6, sem dependências
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout


class _Celula(QFrame):
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
    """Métrica = filtro. Clique filtra; célula ativa ganha destaque;
    clicar na ativa limpa o filtro (emite 'TODOS')."""
    filtro_solicitado = Signal(str)

    def __init__(self, celulas: list[tuple[str, str]], parent=None):
        # celulas: [("Total", "TODOS"), ("Conciliados", "CONCILIADOS"), ...]
        super().__init__(parent)
        self.setObjectName("KpiPanel")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)
        self._celulas: dict[str, _Celula] = {}
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

    def atualizar(self, valores: dict[str, object]) -> None:
        for f, c in self._celulas.items():
            if f in valores:
                c.set_valor(valores[f])
```

Uso no `MainWindow`:

```python
self.kpis = KpiPanel([("Total", "TODOS"), ("Conciliados", "CONCILIADOS"),
                      ("Pendências", "PENDÊNCIAS"), ("Recibos?", "RECIBO?"),
                      ("Marcados", "MARCADOS")])
self.kpis.filtro_solicitado.connect(self._aplicar_filtro)
lay.addWidget(self.kpis)

def _aplicar_filtro(self, filtro: str):
    self.state.filtro = filtro
    self.kpis.set_ativo(filtro)
    self.model.set_filtro(filtro)
    # valores: self.kpis.atualizar({"TODOS": tot, "CONCILIADOS": conc, ...})
```

### 12.6 `Toast` — notificação efêmera (auto-dismiss)

```python
# toast.py — PySide6, sem dependências
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class Toast(QFrame):
    """Sucesso efêmero no canto inferior direito do parent.
    Uso: self.toast = Toast(self.janela); self.toast.mostrar("3 recibos gerados").
    NÃO use para erro de sistema (QMessageBox.critical) nem para estado
    que exige ação (banner)."""

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
        self._posicionar()
        self.show()
        self.raise_()
        self._timer.start(ms)

    def _posicionar(self) -> None:
        p = self.parentWidget()
        if p is None:
            return
        margem = 44  # sobe a statusbar se a tiver no canto direito
        self.move(max(8, p.width() - self.width() - 16),
                  max(8, p.height() - self.height() - margem))

    def resizeEvent(self, e):
        if self.isVisible():
            self._posicionar()
        super().resizeEvent(e)
```

Uso:

```python
self.toast = Toast(self)                      # filho da janela/janela central
...
self.toast.mostrar(f"{len(arqs)} recibo(s) gerados em {pasta}")
self._say("Recibos OK")                       # statusbar guarda a mesma linha
```

---

*Fim do template. Fontes: `app_qt/theme.py`, `app_qt/qss.py`,
`app_qt/main_window.py` (estrutura aprovada) e `app_qt/widgets.py`
(KpiPanel, Toast). Feedback consolidado em 30/09/2026.*
