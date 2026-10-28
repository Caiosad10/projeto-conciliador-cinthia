# Project Memory — Caixa INCA / caixa-inca-sis

**Última atualização:** 2026-10-28 (estado final de entrega)
**Tipo:** sistema desktop Python para fechamento de caixa financeiro (INCA LTDA)
**Pasta principal:** `caixa-inca-sis/`
**Objetivo de produto:** fechar o caixa do mês em **um dia**, com poucos cliques e poucas correções — não 100% automático.
**UI oficial:** PySide6/Qt (`main_qt.py` → `app_qt/`). **Tkinter removido (out/2026)** — `ui/` e `main.py` apagados; `core/` é UI-agnóstico.

> **Este arquivo é memória técnica histórica.** O documento de entrega/uso é o
> `README.md` (fluxo, decisões de design, como rodar). Seções antigas abaixo
> podem mencionar o Tk — ele não existe mais.

## Estado final out/2026 (entrega — saída do setor financeiro)

- **Sessão autosave v1**: `<extrato>.inca-sessao/sessao.json`, debounce ~1s +
  flush no fechar; restore com re-parse + religação por caminho/nome; arquivo
  ausente → `ATENCAO`/`SEM_COMPROVANTE` (nunca verde). Backups manuais em
  `.inca-sessao.backup-<data>/` ao lado.
- **Motor**: gate de data no auto-match (+2/−7 dias sem ID forte → score 0,
  anti-roubo de comprovante entre lançamentos iguais); divergências visíveis
  em qualquer status; duplicatas por ID forte descartadas.
- **Manual**: pré-seleciona vínculo atual; remover comp/base liberado (sem
  travar); remover comprovante **preserva a base**; mover vínculo com
  Mover/Manter os dois/Cancelar; conflito marcado "[ja em Lxxx]" na lista.
- **Round 1** uma vez só (botão trava); **Round 2** só preenche vazios,
  preserva manuais; adicionar pasta nova dispara Round 2 automático.
- **Recibos**: `.docx` via template `templates/Dividendo-Recibos.docx`;
  fallback de descrição `DIVIDENDO {FAVORECIDO}` (regra do financeiro);
  gerados são indexados na sessão (religam ao reabrir); sem conversão DOCX→PDF.
- **Empacotar**: lote do mês → `Pacote_Final_Ordenado/` (um PDF por lançamento
  em ordem; `.docx` em pasta de originais).
- **KPI**: 6 métricas (Total/Conciliados/Pendências/Atenção/Recibos?/Marcados),
  clique = filtro.
- **Testes**: 18 pytest + `teste_imports.py` (7 checks, janela offscreen).
- **Git**: versionado desde out/2026; dados reais (`DOCUMENTOS - CAIXA/`) fora
  do repo via `.gitignore`.

---
**Feedback de progresso:** overlay modal `app_qt/progress.py` (card flutuante central,
sem véu; bloqueia cliques; determinado p/ leitura de docs, indeterminado p/ conciliar).
**Sincronismo recibo↔manual (opção B):** manual→CONCILIADO desmarca, →PRECISA_RECIBO
marca, →SEM_COMPROVANTE desmarca; caixinha livre p/ marcar à mão.
**Identidade visual:** "Claro Moderno" — fonte da verdade em `app_qt/theme.py` + `app_qt/qss.py`
(o antigo TEMPLATE.md foi descontinuado). Template de composição p/ outros projetos: `TEMPLATE_FLUXO.md`.

---

## 1. Contexto de negócio

### Fluxo manual original (Cinthia / gestora)
1. Imprimir extrato Bradesco do mês  
2. Receber comprovantes/boletos/faturas em partes (dias 01–09, 10–20, 21–31)  
3. Separar comprovantes vs boletos/faturas  
4. Conciliar na ordem do extrato  
5. Se há boleto/fatura no comprovante → achar o documento base; se não → gerar **recibo**  
6. Recibo: valor, valor por extenso, **descrição do comprovante**, data  
7. Se comprovante sem descrição útil → `DIVIDENDO {NOME DE QUEM RECEBEU}`  
8. Lista de faltantes → gestora cobra Cinthia → reconcilia pendentes  
9. Confirmar ordem e documentos → caixa fechado  

### Papéis
- **Usuário do sistema:** faz conciliação, gera recibos, envia faltantes  
- **Gestora:** recebe lista de faltantes (sem poluir com “só precisa de recibo”)  
- **Cinthia:** envia documentos faltantes  

---

## 2. Stack e estrutura

```
caixa-inca-sis/
├── main.py
├── requirements.txt
├── core/
│   ├── models.py              # Lancamento, Documento, Resultado, Status, Tipo
│   ├── extrato_parser.py      # PDF extrato Bradesco
│   ├── documento_parser.py    # PDFs comprovante/boleto/fatura/PC
│   ├── conciliador.py         # Round 1 + Round 2 (pendentes)
│   └── recibo_generator.py    # DOCX a partir do template
├── ui/
│   ├── main_window.py         # UI principal, tabela, filtros, ações
│   ├── dialogs.py             # Manual (com busca), Faltantes, Progresso
│   ├── pdf_viewer.py          # Miniatura + DialogoQuickView
│   ├── components.py
│   └── progress_dialog.py
├── utils/
│   ├── text_utils.py
│   ├── pdf_utils.py
│   └── file_utils.py
└── templates/
    ├── Dividendo-Recibos.docx # template com placeholders
    ├── recibo_template.html
    └── logo_inca.jpg
```

**Dependências típicas:** Python 3, tkinter, PyMuPDF (`fitz`), python-docx, Pillow.

---

## 3. Regras de domínio consolidadas

### Matching (conciliação automática)
| Sinal | Uso |
|--------|-----|
| **Valor** | Obrigatório; diferença relevante → score 0 |
| **Data** | Reforço / penalidade por distância |
| **Favorecido** | Nome no extrato (`DES:` / `DEST.`) vs favorecido do PDF e nome do arquivo |
| **IDs fortes** | `PC_0220`, `AMX040`, etc. no extrato vs **nome do arquivo** |
| **Descrição do comprovante** | **Não** entra no match — só no **recibo** |

Limiar prático de aceite ~45–50. Valores repetidos (ex. muitos R$ 350 de aluguel) **não** devem casar só por valor.

### Round 1 vs Round 2
- **Conciliar (Round 1):** do zero  
- **Reconciliar (Round 2+):** só preenche **vazios**; não desfaz vínculos; linhas com `ajustado_manual=True` são intocáveis  

### Status
- `CONCILIADO` — comprovante (+ base se saída)  
- `PRECISA_RECIBO` — tem comprovante, falta base  
- `SEM_COMPROVANTE` / faltantes diversos  
- Cores e filtros na tabela (Todos / Conciliados / Pendências / Recibo? / Marcados)  

### Recibos
- Só das linhas **marcadas** (checkbox), não de tudo que é `PRECISA_RECIBO`  
- Template DOCX: `{VALOR}`, `{VALOR_EXTENSO}`, `{DESCRICAO}`, `{DATA}`  
- Centavos por **extenso** (ex. “Vinte e Seis Centavos”), não “26/100”  
- Descrição: campo **Descrição** do comprovante (não Identificação / txid / nome do arquivo)  
- Fallback: `DIVIDENDO {favorecido}`  
- **Não priorizar** conversão DOCX→PDF no pacote por enquanto (decisão do usuário)  

### Duplicatas
- Ignorar só com **chave forte** (txid `E…`, linha digitável, nosso número)  
- Similar ≠ duplicata  

### Faltantes (gestora)
- Exportar o que falta de documento real (comprovante/base)  
- Não poluir a lista com lançamentos que o usuário já resolve com recibo gerado por ele  

---

## 4. UX — o que já foi implementado (ZIP “ULTIMA VERSÃO”)

| Item | Onde | Comportamento |
|------|------|----------------|
| Busca na manual | `ui/dialogs.py` | Campos separados comprovante / base; tokens; ordena por valor/data do lançamento |
| Seleção após manual | `ui/main_window.py` | Reaplica `iid` = ordem, `see`, atualiza detalhes e viewer |
| Quick view | `ui/pdf_viewer.py` | Clique na miniatura / Ampliar / duplo clique na lista da manual; Esc fecha; zoom alto |
| Checkbox recibos | `main_window` | Marcar → gerar só a seleção |
| Cores / filtros | `main_window` | Status visual na Treeview |

---

## 5. Problemas conhecidos / backlog

### Alta prioridade (uso real)
1. **Pacote final** — linhas com recibo não saem unificadas com o comprovante para impressão contínua (recibo fica em pasta separada). Conversão DOCX→PDF **adiada** por escolha do usuário; ainda falta estratégia de pacote sem depender disso (ex. pasta por lançamento, ou mescla só PDF+PDF).  
2. **Match em valores iguais** — ainda exige atenção humana (favorecido ajuda, mas padronização da Cinthia varia).  
3. **Tipagem errada** — alguns bases classificados como comprovante (e vice-versa); manual permite qualquer PDF nas duas listas.  
4. **Parser de favorecido** — ruído (“RAZÃO SOCIAL CNPJ/CPF…”) atrapalha leitura na lista.  

### Média
- Visual da manual: linha já é `[TIPO] valor | data | fav | arquivo`; ainda pode melhorar se o mês trouxer mais lixo no favorecido  
- Visualizador embutido pequeno = resolvido em parte pelo Quick View  
- Estabilidade mês a mês depende da padronização dos PDFs  

### Fora de escopo atual
- App web gerado em modo Build (React) — **não** é o produto oficial; usuário gostou do visual para conversa futura, mas o sistema real é **Python/Tkinter**  

---

## 6. Como trabalhar com o Grok (plataforma)

- O painel de arquivos do **Project** no Grok **nem sempre** monta o código no sandbox do agente.  
- Forma confiável: **anexar ZIP na mensagem** (ex. `caixa-inca-sis - ULTIMA VERSÃO.zip`).  
- Após edições, devolver arquivos em `artifacts/caixa-inca-sis/` ou novo ZIP.  
- Não reescrever o domínio em web app a menos que o usuário peça explicitamente.  

---

## 7. Decisões fechadas (não reabrir sem pedido)

1. Match = valor + data + favorecido (+ IDs de arquivo); descrição só no recibo  
2. Recibos só com checkbox / seleção  
3. Round 2 não zera trabalho nem desfaz manual  
4. Duplicata só com ID forte  
5. Por ora **não** investir em DOCX→PDF no pacote  
6. Continuar no **Python**, não migrar o fluxo operacional para a web  

---

## 8. Próximos passos sugeridos (quando retomar)

1. Pacote final utilizável na impressão (sem forçar conversão de recibo se ainda não for desejada)  
2. Refino de parser (favorecido / tipo) com amostra real do mês seguinte  
3. Ajustes finos de UX da manual se a busca não bastar  
4. (Opcional) conversa sobre visual web **só** como referência de UI, sem substituir o desktop  

---

## 9. Amostra / arquivos de referência do projeto

Quando disponíveis no Project:
- Extrato: `EXTRATO BRADESCO INCA_MES 07.PDF`  
- Comprovantes em pastas por faixa de dias  
- Template: `Dividendo.docx` / `templates/Dividendo-Recibos.docx`  
- Exemplos de recibo gerado: `RECIBO_*.docx`  

Casos de teste úteis da conversa:
- R$ 25.723,64 + `PC_0220` / transformador (match por valor+ID)  
- Vários R$ 350 aluguel vs PIX/TED com nomes diferentes (não embaralhar)  
- `MAXIMA` no nome do comprovante e da fatura (busca na manual)  
- Recibo: descrição do PDF, não código `E607…`  

---

## 10. Contato do fluxo

Projeto Grok associado historicamente a **CAIXA INCA – CONCILIAÇÃO** / geração de recibos financeiros. Usuário final opera o fechamento; sistema reduz dias de trabalho manual para ~1 dia com correções pontuais.
