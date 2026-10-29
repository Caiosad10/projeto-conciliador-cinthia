# Conciliador INCA — Fechamento de Caixa (PySide6)

App desktop de conciliação bancária para o fechamento mensal de caixa da INCA:
cruza o **extrato Bradesco** com **comprovantes/PCs/boletos/faturas (PDF)**,
aponta pendências, gera **recibo em DOCX**, lista **documentos faltantes** e
**empacota tudo em ordem** para impressão.

> Interface gráfica: **PySide6** (`app_qt/`). A versão Tkinter antiga foi
> removida em out/2026 — todo o negócio vive em `core/` (sem dependência de UI).

## Requisitos e execução

```bash
pip install -r requirements.txt   # pypdf, python-docx, PyMuPDF, PySide6
python main_qt.py                 # abre maximizado
```

Testes e smoke:

```bash
python -m pytest tests/ -q        # 18 testes (motor, sessão, fluxo, pacote)
python teste_imports.py           # smoke de imports + janela offscreen
```

## Fluxo de trabalho (fechamento mensal)

1. **Arquivo > Abrir extrato…** (Ctrl+O) — PDF do extrato do mês
2. **Arquivo > Adicionar pasta docs…** (Ctrl+D) — pastas dos comprovantes/PCs (acumula, repetível)
3. **Conciliar (Round 1)** (F5) — match automático por valor+data+favorecido+ID; trava o botão depois (nunca refaz do zero por engano)
4. **Correções** — clique direito na linha ou botão **Conciliação manual** (M):
   - **Remover comp./base** deixa a linha como faltante (sem apagar a base junto)
   - Se o documento já estiver em outro lançamento: diálogo **Mover vínculo / Manter os dois / Cancelar**
   - Divergência de data aparece no painel de detalhe
5. **Gerar recibos** — marque a coluna **Recibo?** e gere os `.docx` (modelo `templates/Dividendo-Recibos.docx`)
6. **Ver faltantes** — lista para cobrar da administradora; salva em TXT
7. **Reconciliar (Round 2+)** — adicionando pastas novas (ex.: "DOCUMENTOS FALTANTES") ele só preenche **vazios**; nunca desfaz vínculo nem trabalho manual
8. **Empacotar** — gera `Pacote_Final_Ordenado/` com um PDF por lançamento em ordem (comprovante+base mesclados); lançamentos com `.docx` vão em pasta com os originais (sem conversão — imprima os recibos à parte)

## Sessão salva automática (sem botão Salvar)

- ~1s após cada mudança e ao fechar: `<extrato>.inca-sessao/sessao.json` ao lado do PDF do extrato
- Ao reabrir o extrato, pergunta **"Retomar sessão?"** e religa os vínculos
- Guarda só estado (caminhos/status/flags), nunca PDFs — arquivos movidos aparecem como **"Arquivo ausente"** e a linha fica em **ATENÇÃO** (nunca verde)
- Restaurar é rápido o suficiente, mas re-parseia os PDFs (sem cache)

## Decisões de design (não "quebrar sem saber")

- **Gate de data no auto-match**: comprovante com data > +2 dias (futuro) ou < −7 dias (passado) e sem ID forte (PC_xxx/AMXxxx) no nome do arquivo → score 0, não casa. Evita o lançamento de um dia "roubar" o comprovante de outro (caso real: dois R$200 do dia 16 vinculados aos comprovantes dos dias 29/30). Comprovante sem data continua neutro; bases (fatura/boleto) não sofrem o gate.
- **Round 1 uma vez só**; recomeçar = *Arquivo > Nova conciliação* (com confirmação)
- **Round 2 nunca desfaz**: só preenche slots vazios; linhas `ajustado_manual` são intocáveis
- **Mover vínculo** tem 3 saídas (inclui "manter os dois" para comprovante de lote)
- **Recibo sem descrição no comprovante** → texto `DIVIDENDO {FAVORECIDO}` (regra de negócio do financeiro)
- **Sem conversão DOCX→PDF** (perde fidelidade visual) — recibos são impressos direto do Word
- **Duplicatas por ID forte** (barras/txid/nosso número) são descartadas automaticamente

## Estrutura

```
main_qt.py            # bootstrap PySide6
app_qt/               # UI: janela, diálogo manual, tabela, sessão, tema
core/                 # negócio: parsers, conciliador (Round 1/2), recibo
utils/                # PDF (mescla/empacota), texto, arquivos
templates/            # modelo DOCX do recibo
tests/                # pytest (18 testes)
DOCUMENTOS - CAIXA/   # dados reais do caixa (fora do Git — ver .gitignore)
```

## Melhorias futuras (não implementadas)

- Cache de parse de PDFs p/ restore instantâneo
- Caminhos relativos na sessão (mudar de pasta não quebra vínculos)
- Aceitar `.docx` no "+ PDF" do diálogo manual

## Gerar o executavel (Windows)

Quem herda o sistema **nao precisa de Python** - basta o `.exe`. Para regenerar a build:

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name ConciliadorINCA --icon "assets\inca.ico" --add-data "assets;assets" --add-data "templates;templates" main_qt.py
```

- Saida: `dist/ConciliadorINCA.exe` (arquivo unico; renomeie como quiser - ex. `Conciliador INCA.exe`)
- Icone: `assets/inca.ico` (gerado do `templates/logo_inca.jpg`; quadrado vermelho INCA)
- `--windowed` = sem terminal; `templates/` vai embutido (modelo DOCX do recibo)
- A receita versionada e o `ConciliadorINCA.spec`; artefatos `build/` e `dist/` ficam fora do Git
- **SmartScreen/antivirus**: exe sem certificado de assinatura pode avisar "App nao reconhecido" na primeira execucao - e esperado; *Mais informacoes -> Executar assim mesmo*
