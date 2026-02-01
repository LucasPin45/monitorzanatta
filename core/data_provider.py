# core/data_provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import streamlit as st


@st.cache_data(ttl=900, show_spinner=False)
def _cached_get_perfil_deputada() -> Dict[str, Any]:
    """
    Função cacheada GLOBAL (sem self) para evitar UnhashableParamError.
    """
    return {
        "nome": "Júlia Zanatta",
        "partido": "PL",
        "uf": "SC",
    }


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

    # ---------- Helpers ----------
    def _ttl(self) -> int:
        return int(self.cfg.ttl_seconds)

    # ---------- Métodos ----------
    def get_perfil_deputada(self) -> Dict[str, Any]:
        return _cached_get_perfil_deputada()

    def contar_tipos(self, props_autoria: Any) -> Dict[str, int]:
        """
        Conta proposições por siglaTipo (ex.: PL, PLP, RIC, PRL...).
        Espera props_autoria como lista de dicts.
        """
        tipos_count: Dict[str, int] = {}
        if not props_autoria:
            return tipos_count

        for p in props_autoria:
            if not isinstance(p, dict):
                continue
            tipo = p.get("siglaTipo", "Outro")
            if tipo:
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1

        return tipos_count

    def get_proposicoes_autoria(self, *_args, **_kwargs) -> Any:
        """
        Placeholder: aqui vai chamar self.camara.fetch_proposicoes_autoria(...)
        Retornar DataFrame ou lista (mas padronize depois).
        """
        # return self.camara.fetch_proposicoes_autoria(...)
        return []

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
