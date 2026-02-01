"""
HTTP Client robusto para APIs da Câmara e Senado.

REGRAS:
- SEM Streamlit
- SEM cache (cache fica no DataProvider)
- Exceções próprias com contexto
- Retry com backoff exponencial
"""

import time
import requests
from typing import Optional, Dict, Any, List


# ============================================================
# EXCEÇÕES
# ============================================================

class HttpClientError(Exception):
    """Erro base para operações HTTP."""
    
    def __init__(
        self,
        message: str,
        url: str = "",
        status_code: Optional[int] = None,
        response_snippet: str = ""
    ):
        self.url = url
        self.status_code = status_code
        self.response_snippet = response_snippet[:500] if response_snippet else ""
        super().__init__(message)
    
    def __str__(self):
        parts = [super().__str__()]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.response_snippet:
            parts.append(f"Response: {self.response_snippet[:200]}...")
        return " | ".join(parts)


class HttpTimeoutError(HttpClientError):
    """Timeout na requisição."""
    pass


class HttpConnectionError(HttpClientError):
    """Erro de conexão."""
    pass


class HttpNotFoundError(HttpClientError):
    """Recurso não encontrado (404)."""
    pass


class HttpRateLimitError(HttpClientError):
    """Rate limit exceeded (429)."""
    pass


class HttpServerError(HttpClientError):
    """Erro no servidor (5xx)."""
    pass


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFFS = [0.5, 1.0, 2.0, 4.0]

# Headers padrão para a Câmara
CAMARA_HEADERS = {
    "User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)",
    "Accept": "application/json",
}

# Headers padrão para o Senado
SENADO_HEADERS = {
    "User-Agent": "Monitor-Zanatta/1.0",
    "Accept": "application/json",
}

# SSL verification
try:
    import certifi
    SSL_VERIFY = certifi.where()
except ImportError:
    SSL_VERIFY = True


# ============================================================
# SESSÃO HTTP REUTILIZÁVEL
# ============================================================

def _create_session(headers: Optional[Dict[str, str]] = None) -> requests.Session:
    """Cria uma sessão HTTP configurada."""
    session = requests.Session()
    if headers:
        session.headers.update(headers)
    return session


# Sessões pré-configuradas
_camara_session: Optional[requests.Session] = None
_senado_session: Optional[requests.Session] = None


def get_camara_session() -> requests.Session:
    """Retorna sessão configurada para a Câmara."""
    global _camara_session
    if _camara_session is None:
        _camara_session = _create_session(CAMARA_HEADERS)
    return _camara_session


def get_senado_session() -> requests.Session:
    """Retorna sessão configurada para o Senado."""
    global _senado_session
    if _senado_session is None:
        _senado_session = _create_session(SENADO_HEADERS)
    return _senado_session


# ============================================================
# FUNÇÕES DE REQUISIÇÃO
# ============================================================

def safe_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoffs: Optional[List[float]] = None,
    session: Optional[requests.Session] = None,
    verify: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Executa GET com retry e backoff exponencial.
    
    Args:
        url: URL para requisição
        params: Query parameters
        headers: Headers adicionais (merge com sessão)
        timeout: Timeout em segundos
        max_retries: Número máximo de tentativas
        backoffs: Lista de delays entre tentativas
        session: Sessão HTTP (usa padrão se não fornecida)
        verify: Verificar SSL
        
    Returns:
        Dict com dados JSON ou None se 404
        
    Raises:
        HttpClientError: Em caso de erro após todas as tentativas
    """
    params = params or {}
    backoffs = backoffs or DEFAULT_BACKOFFS
    
    # Usar sessão fornecida ou criar uma nova
    if session is None:
        session = requests.Session()
        if headers:
            session.headers.update(headers)
    elif headers:
        # Merge headers temporariamente
        merged_headers = dict(session.headers)
        merged_headers.update(headers)
        headers = merged_headers
    
    last_error: Optional[Exception] = None
    last_status: Optional[int] = None
    last_response_text: str = ""
    
    for attempt in range(max_retries):
        try:
            resp = session.get(
                url,
                params=params,
                timeout=timeout,
                verify=verify if verify else SSL_VERIFY,
                headers=headers if headers and session is None else None
            )
            
            last_status = resp.status_code
            last_response_text = resp.text[:1000] if resp.text else ""
            
            # 404 - Não encontrado (válido, retorna None)
            if resp.status_code == 404:
                return None
            
            # 429 - Rate limit (retry)
            if resp.status_code == 429:
                delay = backoffs[min(attempt, len(backoffs) - 1)]
                time.sleep(delay)
                continue
            
            # 5xx - Erro do servidor (retry)
            if 500 <= resp.status_code <= 599:
                delay = backoffs[min(attempt, len(backoffs) - 1)]
                time.sleep(delay)
                continue
            
            # Outros erros HTTP
            resp.raise_for_status()
            
            # Sucesso - parse JSON
            return resp.json()
            
        except requests.exceptions.Timeout as e:
            last_error = e
            delay = backoffs[min(attempt, len(backoffs) - 1)]
            time.sleep(delay)
            
        except requests.exceptions.ConnectionError as e:
            last_error = e
            delay = backoffs[min(attempt, len(backoffs) - 1)]
            time.sleep(delay)
            
        except requests.exceptions.HTTPError as e:
            last_error = e
            # Não fazer retry para erros HTTP (exceto 429/5xx tratados acima)
            break
            
        except ValueError as e:
            # Erro ao parsear JSON
            last_error = e
            break
            
        except Exception as e:
            last_error = e
            break
    
    # Todas as tentativas falharam
    # Retorna dict com erro ao invés de lançar exceção (compatibilidade)
    error_msg = str(last_error) if last_error else "unknown_error"
    return {"__error__": error_msg, "__url__": url, "__status__": last_status}


def safe_get_strict(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoffs: Optional[List[float]] = None,
    session: Optional[requests.Session] = None,
    verify: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Versão estrita que lança exceções ao invés de retornar dict de erro.
    
    Mesmos parâmetros de safe_get().
    
    Raises:
        HttpNotFoundError: Se recurso não existe (404)
        HttpTimeoutError: Se timeout
        HttpConnectionError: Se erro de conexão
        HttpRateLimitError: Se rate limit (429)
        HttpServerError: Se erro do servidor (5xx)
        HttpClientError: Outros erros
    """
    result = safe_get(
        url=url,
        params=params,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        backoffs=backoffs,
        session=session,
        verify=verify
    )
    
    if result is None:
        return None
    
    if isinstance(result, dict) and "__error__" in result:
        error_msg = result.get("__error__", "unknown")
        status = result.get("__status__")
        
        if status == 404:
            raise HttpNotFoundError(
                f"Recurso não encontrado",
                url=url,
                status_code=404
            )
        elif status == 429:
            raise HttpRateLimitError(
                f"Rate limit exceeded",
                url=url,
                status_code=429
            )
        elif status and 500 <= status <= 599:
            raise HttpServerError(
                f"Erro do servidor: {error_msg}",
                url=url,
                status_code=status
            )
        elif "timeout" in error_msg.lower():
            raise HttpTimeoutError(
                f"Timeout na requisição",
                url=url
            )
        elif "connection" in error_msg.lower():
            raise HttpConnectionError(
                f"Erro de conexão",
                url=url
            )
        else:
            raise HttpClientError(
                f"Erro na requisição: {error_msg}",
                url=url,
                status_code=status
            )
    
    return result


def safe_get_raw(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    verify: bool = True
) -> Optional[requests.Response]:
    """
    Retorna o Response completo (para quando precisa de XML ou content).
    
    Args:
        url: URL para requisição
        params: Query parameters
        headers: Headers (merge com SENADO_HEADERS por padrão)
        timeout: Timeout em segundos
        max_retries: Número máximo de tentativas
        verify: Verificar SSL
        
    Returns:
        Response object ou None em caso de erro
    """
    backoffs = DEFAULT_BACKOFFS
    merged_headers = dict(SENADO_HEADERS)
    if headers:
        merged_headers.update(headers)
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=timeout,
                verify=SSL_VERIFY if verify else verify
            )
            
            # 404 - Não encontrado
            if resp.status_code == 404:
                return None
            
            # 429 ou 5xx - retry
            if resp.status_code == 429 or (500 <= resp.status_code <= 599):
                delay = backoffs[min(attempt, len(backoffs) - 1)]
                time.sleep(delay)
                continue
            
            return resp
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            delay = backoffs[min(attempt, len(backoffs) - 1)]
            time.sleep(delay)
            
        except Exception:
            break
    
    return None


def safe_post(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Executa POST simples (sem retry, usado para APIs de notificação).
    
    Args:
        url: URL para requisição
        json_data: Payload JSON
        headers: Headers adicionais
        timeout: Timeout em segundos
        
    Returns:
        Dict com resposta JSON ou None em caso de erro
    """
    try:
        resp = requests.post(
            url,
            json=json_data,
            headers=headers,
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


# ============================================================
# PAGINAÇÃO
# ============================================================

def safe_get_all_pages(
    base_url: str,
    params: Optional[Dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    max_pages: int = 100,
    items_per_page: int = 100,
    timeout: int = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    """
    Busca todos os dados paginados da API da Câmara.
    
    A API da Câmara usa links rel="next" para paginação.
    
    Args:
        base_url: URL base (ex: /proposicoes)
        params: Query parameters iniciais
        session: Sessão HTTP (usa Câmara se não fornecida)
        max_pages: Número máximo de páginas
        items_per_page: Itens por página
        timeout: Timeout por requisição
        
    Returns:
        Lista com todos os itens de todas as páginas
    """
    if session is None:
        session = get_camara_session()
    
    params = dict(params or {})
    if "itens" not in params:
        params["itens"] = items_per_page
    
    all_items: List[Dict[str, Any]] = []
    current_url = base_url
    current_params: Optional[Dict] = params
    page = 0
    
    while page < max_pages:
        data = safe_get(
            current_url,
            params=current_params,
            session=session,
            timeout=timeout
        )
        
        if data is None or "__error__" in data:
            break
        
        items = data.get("dados", [])
        if not items:
            break
        
        all_items.extend(items)
        
        # Verificar se tem próxima página
        links = data.get("links", [])
        next_link = None
        for link in links:
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        
        if not next_link:
            break
        
        # Próxima página usa URL completa
        current_url = next_link
        current_params = None  # URL já tem os params
        page += 1
    
    return all_items


# ============================================================
# VALIDAÇÃO DE RESPOSTA
# ============================================================

def validar_resposta_api(response: requests.Response) -> tuple:
    """
    Valida se a resposta da API é válida.
    
    Args:
        response: Objeto Response do requests
    
    Returns:
        (valida: bool, mensagem_erro: str)
    """
    # Verificar status code
    if response.status_code != 200:
        return False, f"API retornou status {response.status_code}"
    
    # Verificar content-type
    content_type = response.headers.get('content-type', '')
    if 'json' not in content_type.lower() and 'application/json' not in content_type.lower():
        # Se não for JSON, pode ser HTML de erro
        if 'html' in content_type.lower():
            return False, "API retornou HTML ao invés de JSON (possível erro do servidor)"
        # Pode ser XML (Senado às vezes retorna XML)
        if 'xml' not in content_type.lower():
            return False, f"Tipo de conteúdo inesperado: {content_type}"
    
    # Verificar se tem conteúdo
    if not response.text or len(response.text.strip()) == 0:
        return False, "API retornou resposta vazia"
    
    # Se for JSON, verificar se é válido
    if 'json' in content_type.lower():
        try:
            response.json()
            return True, ""
        except ValueError as e:
            return False, f"Resposta não é JSON válido: {str(e)}"
    
    return True, ""
