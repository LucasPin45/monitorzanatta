"""
Utilitários de links para o Monitor Parlamentar.
Funções de geração de URLs para Câmara e Senado.

REGRA: Este módulo NÃO pode importar streamlit.
"""
from urllib.parse import urlparse
from typing import Optional


def camara_link_tramitacao(id_proposicao: str) -> str:
    """Gera link para a ficha de tramitação de uma proposição na Câmara."""
    pid = str(id_proposicao).strip()
    return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"


def camara_link_deputado(id_deputado: str) -> str:
    """Gera link para a página do deputado na Câmara."""
    if not id_deputado or str(id_deputado).strip() in ('', 'nan', 'None'):
        return ""
    return f"https://www.camara.leg.br/deputados/{str(id_deputado).strip()}"


def extract_id_from_uri(uri: str) -> Optional[str]:
    """Extrai o ID final de uma URI da API da Câmara."""
    if not uri:
        return None
    try:
        path = urlparse(uri).path.rstrip("/")
        return path.split("/")[-1]
    except Exception:
        return None
