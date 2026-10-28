# utils/pdf_utils.py

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import shutil
import subprocess
import tempfile


def extrair_texto_pdf(caminho: str | Path) -> str:
    """Extrai texto de um arquivo PDF."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(caminho))
        texto = []
        for pagina in reader.pages:
            texto.append(pagina.extract_text() or "")
        return "\n".join(texto)
    except Exception as e:
        print(f"Erro ao extrair texto de {caminho}: {e}")
        return ""


def abrir_arquivo_externo(caminho: Path | str) -> bool:
    """Abre arquivo no aplicativo padrão do sistema (Windows/macOS/Linux)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys_platform_is_darwin():
            subprocess.run(["open", str(caminho)], check=False)
        else:
            subprocess.run(["xdg-open", str(caminho)], check=False)
        return True
    except Exception as e:
        print(f"Erro ao abrir arquivo externamente: {e}")
        return False


def sys_platform_is_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


def abrir_pasta(caminho: Path | str) -> bool:
    """Abre uma pasta no explorador de arquivos."""
    caminho = Path(caminho)
    if not caminho.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys_platform_is_darwin():
            subprocess.run(["open", str(caminho)], check=False)
        else:
            subprocess.run(["xdg-open", str(caminho)], check=False)
        return True
    except Exception as e:
        print(f"Erro ao abrir pasta: {e}")
        return False


def _encontrar_soffice() -> Optional[str]:
    """Localiza o executável do LibreOffice/soffice."""
    candidatos = [
        "soffice",
        "libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for cmd in candidatos:
        if Path(cmd).exists() or shutil.which(cmd):
            return cmd
    return None


def converter_docx_para_pdf(caminho: Path, destino: Optional[Path] = None) -> Optional[Path]:
    """
    Converte DOCX em PDF via LibreOffice (melhor fidelidade visual).
    Retorna o caminho do PDF ou None se falhar.
    """
    caminho = Path(caminho)
    if not caminho.exists() or caminho.suffix.lower() not in {".docx", ".doc"}:
        return None

    soffice = _encontrar_soffice()
    if not soffice:
        print("LibreOffice/soffice não encontrado — não foi possível converter DOCX→PDF.")
        return None

    out_dir = Path(destino).parent if destino else caminho.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # LibreOffice grava o PDF no outdir com o mesmo stem
            cmd = [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_path),
                str(caminho.resolve()),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"Falha na conversão LibreOffice: {result.stderr or result.stdout}")
                return None

            gerado = tmp_path / f"{caminho.stem}.pdf"
            if not gerado.exists():
                # Às vezes o nome muda levemente
                pdfs = list(tmp_path.glob("*.pdf"))
                if not pdfs:
                    return None
                gerado = pdfs[0]

            alvo = Path(destino) if destino else (out_dir / f"{caminho.stem}.pdf")
            shutil.copy2(gerado, alvo)
            return alvo
    except Exception as e:
        print(f"Erro ao converter DOCX→PDF: {e}")
        return None


def garantir_pdf(caminho: Path, cache_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Garante um PDF utilizável a partir de PDF ou DOCX.
    Para DOCX, converte e grava em cache_dir (ou ao lado do original).
    """
    caminho = Path(caminho)
    if not caminho.exists():
        return None

    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        return caminho

    if sufixo in {".docx", ".doc"}:
        if cache_dir is None:
            cache_dir = caminho.parent / "_pdf_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        destino = cache_dir / f"{caminho.stem}.pdf"
        if destino.exists() and destino.stat().st_mtime >= caminho.stat().st_mtime:
            return destino
        return converter_docx_para_pdf(caminho, destino)

    return None


def mesclar_pdfs(documentos: List[Path], destino: Path) -> bool:
    """Mescla múltiplos PDFs em um único arquivo. Retorna True se gerou páginas."""
    if not documentos:
        return False

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for documento in documentos:
        documento = Path(documento)
        if not documento.exists():
            continue
        try:
            reader = PdfReader(str(documento))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"Erro ao mesclar {documento}: {e}")

    if not writer.pages:
        return False

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        writer.write(f)
    return True


def empacotar_lote(resultados, pasta_destino: Path, progress_cb=None) -> dict:
    """Empacota o mês inteiro em lote (porte do Tk `_gerar_pacotes`).

    - Percorre os resultados em ordem de lançamento.
    - Inclui todo lançamento com ao menos um arquivo existente
      (qualquer status — CONCILIADO, ATENCAO, PRECISA_RECIBO etc.).
    - Um item por lançamento em `Pacote_Final_Ordenado/`:
      `0001_20260901.pdf` (comprovante + base mesclados, base primeiro)
      ou pasta `0001_20260901/` com os originais quando há não-PDF
      (ex.: recibo .docx — SEM conversão, imprime à parte).
    - Retorna dict com `dir`, `pdfs`, `pastas`, `pulados`, `erros`.
    """
    pasta_destino = Path(pasta_destino)
    pasta_ordenada = pasta_destino / "Pacote_Final_Ordenado"
    pasta_ordenada.mkdir(parents=True, exist_ok=True)

    ordenados = sorted(list(resultados or []),
                       key=lambda r: getattr(getattr(r, "lancamento", None), "ordem", 0))
    total = max(1, len(ordenados))
    pdfs: List[Path] = []
    pastas: List[Path] = []
    pulados = 0
    erros: List[str] = []

    for i, r in enumerate(ordenados):
        try:
            lanc = getattr(r, "lancamento", None)
            if lanc is None:
                pulados += 1
                continue
            docs: List[Path] = []
            for lado in ("documento_base", "comprovante"):
                d = getattr(r, lado, None)
                arq = getattr(d, "arquivo", None) if d is not None else None
                if arq:
                    p = Path(arq)
                    if p.exists() and p.is_file():
                        docs.append(p)
            if not docs:
                pulados += 1
                continue
            nome_base = (f"{getattr(lanc, 'ordem', 0):04d}_"
                         f"{lanc.data.strftime('%Y%m%d')}")
            destino_pdf = pasta_ordenada / f"{nome_base}.pdf"
            pasta_item = pasta_ordenada / nome_base
            tem_nao_pdf = any(p.suffix.lower() != ".pdf" for p in docs)
            if tem_nao_pdf:
                pasta_item.mkdir(parents=True, exist_ok=True)
                for j, arq in enumerate(docs, start=1):
                    try:
                        shutil.copy2(arq, pasta_item / f"{j:02d}_{arq.name}")
                    except Exception as exc:  # noqa: BLE001
                        erros.append(f"L{lanc.ordem:03d}: {exc}")
                pastas.append(pasta_item)
            else:
                artefato = empacotar_documentos(
                    docs, destino_pdf, pasta_fallback=pasta_item)
                if artefato.is_dir():
                    pastas.append(artefato)
                else:
                    pdfs.append(artefato)
        except Exception as exc:  # noqa: BLE001
            try:
                ordem = getattr(getattr(r, "lancamento", None), "ordem", "?")
            except Exception:  # noqa: BLE001
                ordem = "?"
            erros.append(f"L{ordem}: {exc}")
        finally:
            if progress_cb:
                try:
                    progress_cb(int((i + 1) / total * 100),
                                f"Empacotando {i + 1}/{len(ordenados)}")
                except Exception:  # noqa: BLE001
                    pass

    return {"dir": pasta_ordenada, "pdfs": pdfs, "pastas": pastas,
            "pulados": pulados, "erros": erros}


def empacotar_documentos(
    arquivos: List[Path],
    destino_pdf: Path,
    pasta_fallback: Optional[Path] = None,
) -> Path:
    """
    Empacota documentos de um lançamento:
    - Converte DOCX→PDF quando necessário
    - Se conseguir 2+ PDFs, gera PDF único mesclado em destino_pdf
    - Caso contrário, copia originais para pasta_fallback

    Retorna o caminho do artefato principal (PDF mesclado ou pasta).
    """
    arquivos = [Path(a) for a in arquivos if a and Path(a).exists()]
    if not arquivos:
        raise ValueError("Nenhum arquivo para empacotar")

    cache = destino_pdf.parent / "_pdf_cache"
    pdfs: List[Path] = []
    for arq in arquivos:
        pdf = garantir_pdf(arq, cache_dir=cache)
        if pdf:
            pdfs.append(pdf)

    if len(pdfs) >= 1 and mesclar_pdfs(pdfs, destino_pdf):
        return destino_pdf

    # Fallback: pasta com originais
    if pasta_fallback is None:
        pasta_fallback = destino_pdf.with_suffix("")
    pasta_fallback.mkdir(parents=True, exist_ok=True)
    for i, arq in enumerate(arquivos, start=1):
        nome = f"{i:02d}_{arq.name}"
        shutil.copy2(arq, pasta_fallback / nome)
    return pasta_fallback
