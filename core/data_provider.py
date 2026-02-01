# core/data_provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# Se ainda não tiver service pronto, deixa esses imports comentados por enquanto.
# from core.services.camara_service import CamaraService
# from core.services.senado_service import SenadoService


@dataclass(frozen=True)
class ProviderConfig:
    ttl_seconds: int = 900  # 15 min (ajusta depois)


class DataProvider:
    """
    Camada central de dados do app.
    - UI chama DataProvider
    - DataProvider chama Services
    - Cache Streamlit fica aqui (centralizado)
    """

    def __init__(self, cfg: Optional[ProviderConfig] = None):
        self.cfg = cfg or ProviderConfig()
        # self.camara = CamaraService()
        # self.senado = SenadoService()

    # ---------- Helpers de cache ----------
    def _ttl(self) -> int:
        return int(self.cfg.ttl_seconds)

    # ---------- EXEMPLOS (você vai plugar nos Services) ----------
    @st.cache_data(ttl=900, show_spinner=False)
    def get_perfil_deputada(self) -> Dict[str, Any]:
        """
        Exemplo: dados fixos/estáveis (nome, partido, uf, ids etc).
        Pode virar fetch real via Câmara depois.
        """
        return {
            "nome": "Júlia Zanatta",
            "partido": "PL",
            "uf": "SC",
        }

    @st.cache_data(ttl=900, show_spinner=False)
    def get_proposicoes_autoria(_self, *_args, **_kwargs) -> Any:
        """
        Placeholder: aqui vai chamar self.camara.fetch_proposicoes_autoria(...)
        Retornar DataFrame ou lista (mas padronize depois).
        """
        # return self.camara.fetch_proposicoes_autoria(...)
        return []

    @st.cache_data(ttl=900, show_spinner=False)
    def get_tramitacoes(self, *_args, **_kwargs) -> Any:
        # return self.camara.fetch_tramitacoes(...)
        return []

    def get_senado_sob_demanda(self, *_args, **_kwargs) -> Any:
        """
        IMPORTANTE: Senado não deve ser cacheado/rodado automaticamente se
        você quiser controle por interação.
        Você pode colocar cache também, mas só se a aba chamar explicitamente.
        """
        # return self.senado.fetch_andamento(...)
        return []
