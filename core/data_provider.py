# core/data_provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import streamlit as st

from core.services.camara_service import CamaraService
from core.services.senado_service import SenadoService


# =====================================================
# Cache functions (NUNCA recebem self)
# =====================================================

@st.cache_data(ttl=900, show_spinner=False)
def _cached_get_perfil_deputada() -> Dict[str, Any]:
    return {
        "nome": "Júlia Zanatta",
        "partido": "PL",
        "uf": "SC",
    }


@st.cache_data(ttl=900, show_spinner=False)
def _cached_get_proposicoes_autoria(
    nome: str,
    partido: str,
    uf: str,
) -> Any:
    """
    Cache GLOBAL de proposições de autoria.
    NÃO recebe self.
    """
    svc = CamaraService()

    # ⚠️ AJUSTE AQUI SE O NOME DO MÉTODO FOR DIFERENTE
    return svc.listar_proposicoes_autoria(
        nome=nome,
        partido=partido,
        uf=uf,
    )


# =====================================================
# Provider config
# =====================================================

@dataclass(frozen=True)
class ProviderConfig:
    ttl_seconds: int = 900  # 15 minutos


# =====================================================
# DataProvider (fachada central do app)
# =====================================================

class DataProvider:
    """
    Camada central de dados do app.

    UI  --->  DataProvider  --->  Services
                     |
                  Cache
    """

    def __init__(self, cfg: Optional[ProviderConfig] = None):
        self.cfg = cfg or ProviderConfig()
        self.camara = CamaraService()
        self.senado = SenadoService()

    # -------------------------------------------------
    # Perfil
    # -------------------------------------------------

    def get_perfil_deputada(self) -> Dict[str, Any]:
        return _cached_get_perfil_deputada()

    # -------------------------------------------------
    # Proposições de autoria
    # -------------------------------------------------

    def get_proposicoes_autoria(self) -> Any:
        perfil = self.get_perfil_deputada()
        return _cached_get_proposicoes_autoria(
            nome=perfil.get("nome", ""),
            partido=perfil.get("partido", ""),
            uf=perfil.get("uf", ""),
        )

    # -------------------------------------------------
    # Tramitacoes (placeholder)
    # -------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def get_tramitacoes(_self, *_args, **_kwargs) -> Any:
        return []

    # -------------------------------------------------
    # Senado sob demanda (SEM cache automático)
    # -------------------------------------------------

    def get_senado_sob_demanda(self, *_args, **_kwargs) -> Any:
        return []

    # -------------------------------------------------
    # Utilitário: contar tipos
    # -------------------------------------------------

    def contar_tipos(self, proposicoes: list[dict]) -> dict[str, int]:
        tipos_count: dict[str, int] = {}
        for p in proposicoes:
            tipo = p.get("siglaTipo") or p.get("tipo") or "Outro"
            tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        return tipos_count
