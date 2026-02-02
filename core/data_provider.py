# core/data_provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import streamlit as st

from core.services.camara_service import CamaraService
from core.services.senado_service import SenadoService


@dataclass(frozen=True)
class ProviderConfig:
    # TTL padrão de cache (em segundos)
    ttl_seconds: int = 900  # 15 min


class DataProvider:
    """
    Camada central de dados do app.
    - UI chama DataProvider
    - DataProvider chama Services (CamaraService / SenadoService)
    - Cache Streamlit fica aqui (centralizado) sempre que possível
    """

    def __init__(self, cfg: Optional[ProviderConfig] = None):
        self.cfg = cfg or ProviderConfig()

        # Services (Python puro, sem Streamlit)
        self.camara = CamaraService()
        self.senado = SenadoService()

    def _ttl(self) -> int:
        return int(self.cfg.ttl_seconds)

    # ---------------------------------------------------------------------
    # PERFIL
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_perfil_deputada(_self) -> Dict[str, Any]:
        """
        Perfil básico (pode virar fetch real via service depois).
        Mantive estável para não quebrar a UI.
        """
        return {
            "nome": "Júlia Zanatta",
            "partido": "PL",
            "uf": "SC",
        }

    def get_perfil_deputada(self) -> Dict[str, Any]:
        return self._cached_get_perfil_deputada()

    # ---------------------------------------------------------------------
    # AUTORIA / PROPOSIÇÕES
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_proposicoes_autoria(_self, id_deputada: int) -> Any:
        """
        Chama o service da Câmara e retorna lista/df (conforme seu service).
        IMPORTANTE: recebe id_deputada como parâmetro para o cache funcionar.
        """
        return _self.camara.get_proposicoes_autoria(id_deputada)

    def get_proposicoes_autoria(self, id_deputada: int) -> Any:
        """
        Interface usada pela UI (Aba 1, etc).
        """
        return self._cached_get_proposicoes_autoria(id_deputada)

    # ---------------------------------------------------------------------
    # UTIL: contar tipos
    # ---------------------------------------------------------------------

    def contar_tipos(self, props_autoria: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Conta proposições por siglaTipo (RIC, PL, PLP, PRL, etc).
        Aceita lista de dicts (records).
        """
        tipos_count: Dict[str, int] = {}
        if not props_autoria:
            return tipos_count

        for p in props_autoria:
            if not isinstance(p, dict):
                continue
            tipo = p.get("siglaTipo") or p.get("tipo") or p.get("sigla_tipo")
            if not tipo:
                continue
            tipos_count[str(tipo)] = tipos_count.get(str(tipo), 0) + 1

        return tipos_count

    # ---------------------------------------------------------------------
    # TRAMITAÇÕES (placeholder para evoluir)
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_tramitacoes(_self, *_args, **_kwargs) -> Any:
        # Quando você plugar o service real, troque aqui:
        # return _self.camara.get_tramitacoes(...)
        return []

    def get_tramitacoes(self, *_args, **_kwargs) -> Any:
        return self._cached_get_tramitacoes(*_args, **_kwargs)

    # ---------------------------------------------------------------------
    # SENADO sob demanda (não cacheado por padrão)
    # ---------------------------------------------------------------------

    def get_senado_sob_demanda(self, *_args, **_kwargs) -> Any:
        """
        Senado não deve rodar sozinho (só quando a aba pedir explicitamente).
        Se quiser cache futuramente, a gente coloca com chave controlada.
        """
        # return self.senado.get_andamento(...)
        return []
