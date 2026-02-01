"""
Services layer para acesso a dados externos (Câmara, Senado).

REGRAS:
- SEM Streamlit
- SEM cache (cache fica no DataProvider, fase 2C)
- Funções puras de busca e parsing

Uso:
    from core.services import CamaraService, SenadoService
    
    camara = CamaraService()
    prop = camara.get_proposicao("123456")
    
    senado = SenadoService()
    dados = senado.buscar_tramitacao_por_numero("PL", "321", "2023")
"""

from .http_client import (
    # Exceções
    HttpClientError,
    HttpTimeoutError,
    HttpConnectionError,
    HttpNotFoundError,
    HttpRateLimitError,
    HttpServerError,
    
    # Funções HTTP
    safe_get,
    safe_get_strict,
    safe_get_raw,
    safe_post,
    safe_get_all_pages,
    validar_resposta_api,
    
    # Sessões
    get_camara_session,
    get_senado_session,
    
    # Configuração
    CAMARA_HEADERS,
    SENADO_HEADERS,
    SSL_VERIFY,
)

from .camara_service import CamaraService
from .senado_service import SenadoService

__all__ = [
    # Classes de serviço
    "CamaraService",
    "SenadoService",
    
    # Exceções
    "HttpClientError",
    "HttpTimeoutError",
    "HttpConnectionError",
    "HttpNotFoundError",
    "HttpRateLimitError",
    "HttpServerError",
    
    # Funções HTTP (para uso avançado)
    "safe_get",
    "safe_get_strict",
    "safe_get_raw",
    "safe_post",
    "safe_get_all_pages",
    "validar_resposta_api",
]
