"""
Gerenciamento centralizado do Session State do Monitor Parlamentar.

Este módulo define TODAS as chaves de st.session_state usadas no sistema,
seus valores default e funções de inicialização.

REGRA: Este módulo recebe `st` como parâmetro para evitar import direto.
REGRA: NÃO contém lógica de negócio, apenas definição de estado.
"""

import datetime
import pandas as pd
from typing import Any, Dict, Optional


# ============================================================
# DEFINIÇÃO DE TODAS AS CHAVES DO SESSION_STATE
# ============================================================
# Cada entrada define: chave, valor_default, descrição
# ============================================================

STATE_KEYS: Dict[str, Dict[str, Any]] = {
    # ========================================
    # AUTENTICAÇÃO
    # ========================================
    "autenticado": {
        "default": False,
        "type": "bool",
        "desc": "Indica se o usuário está autenticado",
    },
    "usuario_logado": {
        "default": None,
        "type": "Optional[str]",
        "desc": "Nome do usuário logado (None se não autenticado)",
    },
    
    # ========================================
    # NAVEGAÇÃO ENTRE ABAS
    # ========================================
    "aba_destino": {
        "default": None,
        "type": "Optional[str]",
        "desc": "Aba de destino para navegação (pauta, buscar, materias, rics)",
    },
    "aba_atual_senado": {
        "default": None,
        "type": "Optional[int]",
        "desc": "Número da aba atual (usado para controle de consultas ao Senado)",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 1 (Autoria)
    # ========================================
    "props_autoria_aba1_cache": {
        "default": None,
        "type": "Optional[list]",
        "desc": "Cache de proposições de autoria na Aba 1",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 2 (Pauta Câmara)
    # ========================================
    "df_scan_tab2": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "DataFrame com resultado do scan da Aba 2",
    },
    "dt_range_tab2_saved": {
        "default": None,
        "type": "Optional[tuple]",
        "desc": "Range de datas salvo da última busca na Aba 2",
    },
    "date_range_tab2": {
        "default": None,  # Será calculado dinamicamente
        "type": "Optional[tuple]",
        "desc": "Range de datas selecionado na Aba 2",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 3 (Palavras-chave)
    # ========================================
    "df_scan_tab3": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "DataFrame com resultado do scan da Aba 3",
    },
    "dt_range_tab3_saved": {
        "default": None,
        "type": "Optional[tuple]",
        "desc": "Range de datas salvo da última busca na Aba 3",
    },
    "date_range_tab3": {
        "default": None,
        "type": "Optional[tuple]",
        "desc": "Range de datas selecionado na Aba 3",
    },
    "palavras_t3": {
        "default": None,  # Será preenchido com PALAVRAS_CHAVE_PADRAO
        "type": "Optional[str]",
        "desc": "Palavras-chave configuradas na Aba 3",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 4 (Comissões Estratégicas)
    # ========================================
    "df_scan_tab4": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "DataFrame com resultado do scan da Aba 4",
    },
    "dt_range_tab4_saved": {
        "default": None,
        "type": "Optional[tuple]",
        "desc": "Range de datas salvo da última busca na Aba 4",
    },
    "date_range_tab4": {
        "default": None,
        "type": "Optional[tuple]",
        "desc": "Range de datas selecionado na Aba 4",
    },
    "comissoes_t4": {
        "default": None,  # Será preenchido com COMISSOES_ESTRATEGICAS_PADRAO
        "type": "Optional[str]",
        "desc": "Comissões configuradas na Aba 4",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 5 (Carteira Completa)
    # ========================================
    "props_aba5_cache": {
        "default": None,
        "type": "Optional[pd.DataFrame]",
        "desc": "Cache de proposições da Aba 5",
    },
    "df_todas_enriquecido_tab5": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "DataFrame enriquecido com dados do Senado na Aba 5",
    },
    "df_status_last": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "Último DataFrame de status gerado",
    },
    "senado_cache_por_id": {
        "default_factory": "empty_dict",
        "type": "dict",
        "desc": "Cache incremental de dados do Senado por ID de proposição",
    },
    "filtro_busca_tab5": {
        "default": "",
        "type": "str",
        "desc": "Texto de filtro de busca na Aba 5",
    },
    "busca_tab5": {
        "default": "",
        "type": "str",
        "desc": "Campo de busca na Aba 5",
    },
    "status_click_sel": {
        "default": None,
        "type": "Optional[str]",
        "desc": "Status selecionado por clique no gráfico",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 6 (Relatoria)
    # ========================================
    "df_aut6_cache": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "Cache de proposições para análise de relatoria na Aba 6",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 7 (RICs)
    # ========================================
    "df_rics_completo": {
        "default_factory": "empty_dataframe",
        "type": "pd.DataFrame",
        "desc": "DataFrame completo de RICs enriquecido",
    },
    
    # ========================================
    # CACHE DE DADOS - ABA 8 (Apensados)
    # ========================================
    "projetos_apensados_cache": {
        "default": None,
        "type": "Optional[list]",
        "desc": "Cache de projetos apensados",
    },
    "apensados_selecionado_id": {
        "default": None,
        "type": "Optional[str]",
        "desc": "ID do projeto apensado selecionado na tabela",
    },
    
    # ========================================
    # CONTROLE DE ATUALIZAÇÃO
    # ========================================
    "ultima_atualizacao": {
        "default_factory": "empty_dict",
        "type": "dict",
        "desc": "Timestamps da última atualização por chave/aba",
    },
}


# ============================================================
# FUNÇÕES DE INICIALIZAÇÃO
# ============================================================

def _get_default_value(key_config: Dict[str, Any]) -> Any:
    """
    Retorna o valor default para uma chave do session_state.
    Trata casos especiais como DataFrames vazios e dicts.
    """
    if "default_factory" in key_config:
        factory = key_config["default_factory"]
        if factory == "empty_dataframe":
            return pd.DataFrame()
        elif factory == "empty_dict":
            return {}
        elif factory == "empty_list":
            return []
    return key_config.get("default")


def init_state(st) -> None:
    """
    Inicializa TODAS as chaves do session_state com valores default.
    
    Deve ser chamada no início do app, ANTES de qualquer uso do session_state.
    
    Args:
        st: Módulo streamlit (passado como parâmetro para evitar import)
    
    Uso:
        from core.state import init_state
        init_state(st)
    """
    for key, config in STATE_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = _get_default_value(config)


def reset_state(st, keys: Optional[list] = None) -> None:
    """
    Reseta chaves específicas do session_state para seus valores default.
    
    Args:
        st: Módulo streamlit
        keys: Lista de chaves para resetar. Se None, reseta TODAS.
    """
    keys_to_reset = keys if keys else list(STATE_KEYS.keys())
    for key in keys_to_reset:
        if key in STATE_KEYS:
            st.session_state[key] = _get_default_value(STATE_KEYS[key])


def reset_cache_abas(st) -> None:
    """
    Reseta todos os caches de dados das abas.
    Útil para o botão "Atualizar" global.
    """
    cache_keys = [
        "props_autoria_aba1_cache",
        "df_scan_tab2",
        "df_scan_tab3",
        "df_scan_tab4",
        "props_aba5_cache",
        "df_todas_enriquecido_tab5",
        "df_status_last",
        "senado_cache_por_id",
        "df_aut6_cache",
        "df_rics_completo",
        "projetos_apensados_cache",
        "ultima_atualizacao",
    ]
    reset_state(st, cache_keys)


def get_state_key(st, key: str, default: Any = None) -> Any:
    """
    Obtém valor do session_state com fallback para default.
    
    Args:
        st: Módulo streamlit
        key: Nome da chave
        default: Valor default se a chave não existir (opcional)
    
    Returns:
        Valor da chave ou default
    """
    if default is None and key in STATE_KEYS:
        default = _get_default_value(STATE_KEYS[key])
    return st.session_state.get(key, default)


def set_state_key(st, key: str, value: Any) -> None:
    """
    Define valor no session_state.
    
    Args:
        st: Módulo streamlit
        key: Nome da chave
        value: Valor a definir
    """
    st.session_state[key] = value


# ============================================================
# HELPERS ESPECÍFICOS
# ============================================================

def is_authenticated(st) -> bool:
    """Verifica se o usuário está autenticado."""
    return st.session_state.get("autenticado", False)


def get_current_user(st) -> Optional[str]:
    """Retorna o nome do usuário logado ou None."""
    return st.session_state.get("usuario_logado")


def is_admin(st) -> bool:
    """Verifica se o usuário logado é admin."""
    user = get_current_user(st)
    return user is not None and user.lower() == "admin"


def set_authenticated(st, usuario: str) -> None:
    """Define o usuário como autenticado."""
    st.session_state["autenticado"] = True
    st.session_state["usuario_logado"] = usuario


def clear_authentication(st) -> None:
    """Remove autenticação do usuário."""
    st.session_state["autenticado"] = False
    st.session_state["usuario_logado"] = None


# ============================================================
# __all__ - EXPORTS PÚBLICOS
# ============================================================

__all__ = [
    # Definição de estado
    'STATE_KEYS',
    # Funções principais
    'init_state',
    'reset_state',
    'reset_cache_abas',
    'get_state_key',
    'set_state_key',
    # Helpers de autenticação
    'is_authenticated',
    'get_current_user',
    'is_admin',
    'set_authenticated',
    'clear_authentication',
]
