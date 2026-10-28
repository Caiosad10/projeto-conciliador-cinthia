from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Set
import shutil
import hashlib

def nome_arquivo_seguro(nome: str) -> str:
    """
    Converte um nome para ser seguro como nome de arquivo.
    Remove caracteres inválidos e limita tamanho.
    """
    # Normaliza Unicode
    nome = unicodedata.normalize("NFKD", nome)
    nome = nome.encode("ascii", "ignore").decode("ascii")
    
    # Remove caracteres inválidos para nomes de arquivo
    nome = re.sub(r'[<>:"/\\|?*]', " ", nome)
    
    # Remove espaços extras
    nome = re.sub(r"\s+", " ", nome).strip()
    
    # Limita tamanho
    return nome[:150] or "documento"

def criar_pasta_segura(pasta: Path) -> Path:
    """Cria uma pasta de forma segura, adicionando sufixo se já existir"""
    if not pasta.exists():
        pasta.mkdir(parents=True)
        return pasta
    
    # Se já existe, adiciona sufixo numérico
    base = pasta.parent / pasta.stem
    extensao = pasta.suffix
    contador = 1
    
    while True:
        nova_pasta = Path(f"{base}_{contador}{extensao}")
        if not nova_pasta.exists():
            nova_pasta.mkdir(parents=True)
            return nova_pasta
        contador += 1

def copiar_arquivo_seguro(origem: Path, destino: Path) -> Path:
    """Copia um arquivo de forma segura, evitando sobrescrita"""
    if not destino.exists():
        shutil.copy2(origem, destino)
        return destino
    
    # Se já existe, adiciona sufixo numérico
    base = destino.parent / destino.stem
    extensao = destino.suffix
    contador = 1
    
    while True:
        novo_destino = Path(f"{base}_{contador}{extensao}")
        if not novo_destino.exists():
            shutil.copy2(origem, novo_destino)
            return novo_destino
        contador += 1

def listar_pdfs(pasta: Path) -> List[Path]:
    """Lista recursivamente todos os PDFs em uma pasta"""
    return sorted(pasta.rglob("*.pdf"))

def hash_arquivo(caminho: Path) -> str:
    """Calcula hash MD5 de um arquivo para verificação de duplicatas"""
    if not caminho.exists():
        return ""
    
    hasher = hashlib.md5()
    with open(caminho, "rb") as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    
    return hasher.hexdigest()

def normalizar_caminho(caminho: Path) -> Path:
    """Normaliza um caminho para formato consistente"""
    return caminho.resolve()

def caminho_relativo(caminho: Path, base: Path) -> str:
    """Retorna o caminho relativo de um arquivo em relação a uma base"""
    try:
        return str(caminho.relative_to(base))
    except ValueError:
        return str(caminho)