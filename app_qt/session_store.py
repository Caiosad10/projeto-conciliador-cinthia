# app_qt/session_store.py — persistência da sessão (retomar de onde parou)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SESSAO_VERSAO = 1
SESSAO_NOME = "sessao.json"


def pasta_sessao(extrato_path: Path) -> Path:
    """Pasta da sessão: ao lado do extrato, `<stem>.inca-sessao/`."""
    extrato_path = Path(extrato_path)
    return extrato_path.parent / f"{extrato_path.stem}.inca-sessao"


def salvar_sessao(path: Path, payload: Dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def carregar_sessao(path: Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def montar_payload(state) -> Dict[str, Any]:
    """Fotografa o AppState em dict JSON-serializável (só paths + estado)."""
    resultados: List[Dict[str, Any]] = []
    for r in state.resultados:
        L = r.lancamento
        resultados.append({
            "ordem": L.ordem,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "score_comp": r.score_comprovante,
            "score_base": r.score_base,
            "divergencias": list(r.divergencias or []),
            "faltantes": list(r.faltantes or []),
            "ajustado_manual": bool(r.ajustado_manual),
            "comp": str(r.comprovante.arquivo) if r.comprovante else None,
            "base": str(r.documento_base.arquivo) if r.documento_base else None,
        })
    return {
        "versao": SESSAO_VERSAO,
        "extrato_path": str(state.extrato_path) if state.extrato_path else None,
        "pastas_docs": [str(p) for p in state.pastas_docs],
        "resultados": resultados,
        "ordens_recibo": sorted(state.ordens_recibo),
        "filtro": state.filtro,
    }

