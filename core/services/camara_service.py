"""
Serviço de acesso à API da Câmara dos Deputados.

REGRAS:
- SEM Streamlit
- SEM cache (cache fica no DataProvider)
- Usa http_client para requisições
- Usa parsers para extração de dados
"""

import time
import concurrent.futures
from typing import Optional, Dict, List, Any

from .http_client import (
    safe_get,
    safe_get_all_pages,
    get_camara_session,
    CAMARA_HEADERS,
    SSL_VERIFY,
)
from .parsers import (
    parse_proposicao_dados,
    parse_proposicao_item,
    parse_tramitacoes,
    parse_relatores,
    parse_eventos,
    parse_pauta,
    parse_deputados,
    has_next_page,
    get_next_page_url,
    extrair_relator_de_tramitacoes,
    extrair_relator_de_relatores,
    extract_id_from_uri,
    get_proposicao_id_from_item,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

# Workaround: Proposições faltantes na API da Câmara
# A API não retorna algumas proposições quando consultamos por idDeputadoAutor
PROPOSICOES_FALTANTES_API = {
    "220559": [  # Julia Zanatta
        {"id": "2570510", "siglaTipo": "PL", "numero": "5072", "ano": "2025"},
        {"id": "2571359", "siglaTipo": "PL", "numero": "5128", "ano": "2025"},
        {"id": "2483453", "siglaTipo": "PLP", "numero": "19", "ano": "2025"},
        {"id": "2455568", "siglaTipo": "PL", "numero": "3341", "ano": "2024"},
        {"id": "2436763", "siglaTipo": "PL", "numero": "2098", "ano": "2024"},
        {"id": "2455562", "siglaTipo": "PL", "numero": "3338", "ano": "2024"},
        {"id": "2482260", "siglaTipo": "PDL", "numero": "24", "ano": "2025"},
        {"id": "2482169", "siglaTipo": "PDL", "numero": "16", "ano": "2025"},
        {"id": "2567301", "siglaTipo": "PL", "numero": "4954", "ano": "2025"},
        {"id": "2531615", "siglaTipo": "PL", "numero": "3222", "ano": "2025"},
        {"id": "2372482", "siglaTipo": "PLP", "numero": "141", "ano": "2023"},
        {"id": "2399426", "siglaTipo": "PL", "numero": "5198", "ano": "2023"},
        {"id": "2423254", "siglaTipo": "PL", "numero": "955", "ano": "2024"},
        {"id": "2374405", "siglaTipo": "PDL", "numero": "194", "ano": "2023"},
        {"id": "2374340", "siglaTipo": "PDL", "numero": "189", "ano": "2023"},
        {"id": "2485135", "siglaTipo": "PL", "numero": "623", "ano": "2025"},
        {"id": "2419264", "siglaTipo": "PDL", "numero": "30", "ano": "2024"},
        {"id": "2375447", "siglaTipo": "PDL", "numero": "209", "ano": "2023"},
        {"id": "2456691", "siglaTipo": "PDL", "numero": "348", "ano": "2024"},
        {"id": "2462038", "siglaTipo": "PL", "numero": "3887", "ano": "2024"},
        {"id": "2448732", "siglaTipo": "PEC", "numero": "28", "ano": "2024"},
        {"id": "2390075", "siglaTipo": "PDL", "numero": "337", "ano": "2023"},
        {"id": "2361454", "siglaTipo": "PL", "numero": "2472", "ano": "2023"},
        {"id": "2365600", "siglaTipo": "PL", "numero": "2815", "ano": "2023"},
        {"id": "2347150", "siglaTipo": "PL", "numero": "321", "ano": "2023"},
        {"id": "2381193", "siglaTipo": "PL", "numero": "4045", "ano": "2023"},
    ]
}


class CamaraService:
    """
    Serviço para acesso à API da Câmara dos Deputados.
    
    Todos os métodos retornam dados brutos (dicts/lists).
    Não há cache nesta camada - cache fica no DataProvider.
    """
    
    def __init__(self):
        self._session = get_camara_session()
    
    # ============================================================
    # PROPOSIÇÕES - BUSCA BÁSICA
    # ============================================================
    
    def get_proposicao(self, id_proposicao: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados básicos de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict com dados ou None
        """
        if not id_proposicao:
            return None
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}"
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return None
        
        return parse_proposicao_dados(data)
    
    def get_proposicao_info(self, id_proposicao: str) -> Dict[str, Any]:
        """
        Busca informações resumidas de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict com id, sigla, numero, ano, ementa
        """
        data = self.get_proposicao(id_proposicao)
        
        if not data:
            return {
                "id": str(id_proposicao),
                "sigla": "",
                "numero": "",
                "ano": "",
                "ementa": ""
            }
        
        return {
            "id": data.get("id", str(id_proposicao)),
            "sigla": data.get("sigla", ""),
            "numero": data.get("numero", ""),
            "ano": data.get("ano", ""),
            "ementa": data.get("ementa", ""),
        }
    
    def buscar_proposicao(
        self,
        sigla_tipo: str,
        numero: str,
        ano: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca proposição por sigla/número/ano.
        
        Args:
            sigla_tipo: PL, PLP, PEC, etc.
            numero: Número
            ano: Ano
            
        Returns:
            Dict com dados ou None
        """
        sigla = (sigla_tipo or "").strip().upper()
        num = (numero or "").strip()
        ano_str = (ano or "").strip()
        
        if not (sigla and num and ano_str):
            return None
        
        url = f"{BASE_URL}/proposicoes"
        params = {
            "siglaTipo": sigla,
            "numero": num,
            "ano": ano_str,
            "itens": 5,
        }
        
        data = safe_get(url, params=params, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return None
        
        dados = data.get("dados", [])
        if not dados:
            return None
        
        # Encontrar match exato
        for d in dados:
            if (str(d.get("numero", "")).strip() == num and
                str(d.get("ano", "")).strip() == ano_str and
                (d.get("siglaTipo", "")).strip().upper() == sigla):
                return parse_proposicao_item(d)
        
        # Fallback: primeiro resultado
        return parse_proposicao_item(dados[0])
    
    def buscar_id_proposicao(
        self,
        sigla_tipo: str,
        numero: str,
        ano: str
    ) -> str:
        """
        Busca apenas o ID de uma proposição.
        
        Args:
            sigla_tipo: PL, PLP, PEC, etc.
            numero: Número
            ano: Ano
            
        Returns:
            ID como string ou ""
        """
        prop = self.buscar_proposicao(sigla_tipo, numero, ano)
        return prop.get("id", "") if prop else ""
    
    # ============================================================
    # TRAMITAÇÕES
    # ============================================================
    
    def get_tramitacoes(
        self,
        id_proposicao: str,
        itens: int = 100,
        ordem: str = "DESC",
        ordenar_por: str = "dataHora"
    ) -> List[Dict[str, Any]]:
        """
        Busca tramitações de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            itens: Itens por página
            ordem: ASC ou DESC
            ordenar_por: Campo para ordenação
            
        Returns:
            Lista de tramitações
        """
        if not id_proposicao:
            return []
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
        
        # Primeira tentativa sem paginação
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return []
        
        tramitacoes = data.get("dados", [])
        
        # Se vazio, tentar com paginação
        if not tramitacoes:
            params = {
                "itens": itens,
                "ordem": ordem,
                "ordenarPor": ordenar_por,
            }
            
            all_items = safe_get_all_pages(url, params=params, session=self._session)
            return all_items
        
        return tramitacoes
    
    def get_ultima_tramitacao(self, id_proposicao: str) -> Optional[Dict[str, Any]]:
        """
        Busca a última tramitação de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict da tramitação ou None
        """
        if not id_proposicao:
            return None
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
        params = {
            "itens": 1,
            "ordem": "DESC",
            "ordenarPor": "dataHora"
        }
        
        data = safe_get(url, params=params, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return None
        
        dados = data.get("dados", [])
        return dados[0] if dados else None
    
    # ============================================================
    # RELATORES
    # ============================================================
    
    def get_relatores(self, id_proposicao: str) -> List[Dict[str, Any]]:
        """
        Busca relatores de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Lista de relatores
        """
        if not id_proposicao:
            return []
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}/relatores"
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return []
        
        return parse_relatores(data)
    
    def get_relator_atual(self, id_proposicao: str) -> Dict[str, Any]:
        """
        Busca relator atual de uma proposição.
        
        Tenta extrair das tramitações primeiro, depois da API de relatores.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict com nome, partido, uf, id_deputado ou {}
        """
        if not id_proposicao:
            return {}
        
        # Buscar dados completos
        prop = self.get_proposicao(id_proposicao)
        orgao_atual = prop.get("status_siglaOrgao", "") if prop else ""
        
        # Buscar tramitações
        tramitacoes = self.get_tramitacoes(id_proposicao)
        
        # Tentar extrair das tramitações
        relator = extrair_relator_de_tramitacoes(tramitacoes, orgao_atual)
        
        if relator:
            # Se não tem ID, tentar buscar
            if not relator.get("id_deputado"):
                dep = self.buscar_deputado_por_nome(relator.get("nome", ""))
                if dep:
                    relator["id_deputado"] = str(dep.get("id", ""))
            return relator
        
        # Fallback: buscar na API de relatores
        relatores = self.get_relatores(id_proposicao)
        relator = extrair_relator_de_relatores(relatores)
        
        if relator and not relator.get("id_deputado"):
            dep = self.buscar_deputado_por_nome(relator.get("nome", ""))
            if dep:
                relator["id_deputado"] = str(dep.get("id", ""))
        
        return relator
    
    # ============================================================
    # RELACIONADAS / APENSADOS
    # ============================================================
    
    def get_relacionadas(self, id_proposicao: str) -> List[Dict[str, Any]]:
        """
        Busca proposições relacionadas (apensadas).
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Lista de relacionadas
        """
        if not id_proposicao:
            return []
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}/relacionadas"
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return []
        
        return data.get("dados", []) or []
    
    def get_proposicao_principal_id(self, id_proposicao: str) -> Optional[str]:
        """
        Descobre a proposição principal à qual esta está apensada.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            ID da principal ou None
        """
        dados = self.get_relacionadas(str(id_proposicao))
        if not dados:
            return None
        
        # Preferir campos explícitos de principal
        for item in dados:
            prop_princ = item.get("proposicaoPrincipal") or item.get("proposicao_principal")
            if isinstance(prop_princ, dict):
                uri = (prop_princ.get("uri") or 
                       prop_princ.get("uriProposicao") or 
                       prop_princ.get("uriProposicaoPrincipal"))
                if uri:
                    pid = extract_id_from_uri(uri)
                    if pid:
                        return pid
            
            for chave_uri in ("uriProposicaoPrincipal", "uriProposicao_principal", "uriPrincipal"):
                if item.get(chave_uri):
                    pid = extract_id_from_uri(item.get(chave_uri))
                    if pid:
                        return pid
        
        # Fallback
        for item in dados:
            pid = get_proposicao_id_from_item(item)
            if pid:
                return pid
        
        return None
    
    # ============================================================
    # AUTORES
    # ============================================================
    
    def get_autores(self, id_proposicao: str) -> List[Dict[str, Any]]:
        """
        Busca autores de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Lista de autores
        """
        if not id_proposicao:
            return []
        
        url = f"{BASE_URL}/proposicoes/{id_proposicao}/autores"
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return []
        
        return data.get("dados", []) or []
    
    # ============================================================
    # DEPUTADOS
    # ============================================================
    
    def buscar_deputado_por_nome(self, nome: str, itens: int = 5) -> Optional[Dict[str, Any]]:
        """
        Busca deputado por nome.
        
        Args:
            nome: Nome do deputado
            itens: Limite de resultados
            
        Returns:
            Dict do deputado ou None
        """
        if not nome:
            return None
        
        url = f"{BASE_URL}/deputados"
        params = {"nome": nome, "itens": itens}
        
        data = safe_get(url, params=params, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return None
        
        deps = parse_deputados(data)
        return deps[0] if deps else None
    
    # ============================================================
    # LISTAS DE PROPOSIÇÕES
    # ============================================================
    
    def listar_proposicoes_autoria(
        self,
        id_deputado: int,
        incluir_faltantes: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Lista proposições de autoria de um deputado.
        
        Args:
            id_deputado: ID do deputado
            incluir_faltantes: Se True, adiciona proposições do workaround
            
        Returns:
            Lista de proposições
        """
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": id_deputado,
            "itens": 100,
            "ordem": "DESC",
            "ordenarPor": "ano"
        }
        
        items = safe_get_all_pages(url, params=params, session=self._session)
        
        # Workaround: adicionar proposições faltantes
        if incluir_faltantes:
            id_str = str(id_deputado)
            if id_str in PROPOSICOES_FALTANTES_API:
                ids_existentes = {str(d.get("id")) for d in items}
                for prop_faltante in PROPOSICOES_FALTANTES_API[id_str]:
                    if str(prop_faltante.get("id")) not in ids_existentes:
                        items.append(prop_faltante)
        
        return [parse_proposicao_item(d) for d in items]
    
    def listar_rics_autoria(self, id_deputado: int) -> List[Dict[str, Any]]:
        """
        Lista RICs de autoria de um deputado.
        
        Args:
            id_deputado: ID do deputado
            
        Returns:
            Lista de RICs
        """
        url = f"{BASE_URL}/proposicoes"
        params = {
            "siglaTipo": "RIC",
            "idDeputadoAutor": id_deputado,
            "itens": 100,
            "ordem": "DESC",
            "ordenarPor": "ano"
        }
        
        items = safe_get_all_pages(url, params=params, session=self._session)
        return [parse_proposicao_item(d) for d in items]
    
    def listar_ids_autoria(self, id_deputado: int) -> set:
        """
        Lista IDs de proposições de autoria de um deputado.
        
        Args:
            id_deputado: ID do deputado
            
        Returns:
            Set de IDs
        """
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": id_deputado,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "id"
        }
        
        items = safe_get_all_pages(url, params=params, session=self._session)
        return {str(d.get("id")) for d in items if d.get("id")}
    
    def listar_proposicoes_por_tipo(
        self,
        id_deputado: int,
        sigla_tipo: str,
        data_inicio: str = "2023-01-01"
    ) -> List[Dict[str, Any]]:
        """
        Lista proposições de um tipo específico.
        
        Args:
            id_deputado: ID do deputado
            sigla_tipo: PL, PLP, etc.
            data_inicio: Data inicial
            
        Returns:
            Lista de proposições
        """
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": id_deputado,
            "siglaTipo": sigla_tipo,
            "dataApresentacaoInicio": data_inicio,
            "itens": 100,
            "ordem": "DESC",
            "ordenarPor": "dataApresentacao"
        }
        
        items = safe_get_all_pages(url, params=params, session=self._session)
        return [parse_proposicao_item(d) for d in items]
    
    # ============================================================
    # EVENTOS
    # ============================================================
    
    def listar_eventos(
        self,
        data_inicio: str,
        data_fim: str,
        itens: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista eventos em um período.
        
        Args:
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            itens: Itens por página
            
        Returns:
            Lista de eventos
        """
        url = f"{BASE_URL}/eventos"
        params = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "itens": itens,
            "ordem": "ASC",
            "ordenarPor": "dataHoraInicio"
        }
        
        return safe_get_all_pages(url, params=params, session=self._session)
    
    def get_pauta_evento(self, event_id: int) -> List[Dict[str, Any]]:
        """
        Busca pauta de um evento.
        
        Args:
            event_id: ID do evento
            
        Returns:
            Lista de itens da pauta
        """
        url = f"{BASE_URL}/eventos/{event_id}/pauta"
        data = safe_get(url, session=self._session)
        
        if data is None or (isinstance(data, dict) and "__error__" in data):
            return []
        
        return parse_pauta(data)
    
    # ============================================================
    # PROPOSIÇÃO COMPLETA (AGREGAÇÃO)
    # ============================================================
    
    def get_proposicao_completa(self, id_proposicao: str) -> Dict[str, Any]:
        """
        Busca TODAS as informações de uma proposição.
        
        Agrega: dados básicos, status, tramitações, relator.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict completo com todos os dados
        """
        pid = str(id_proposicao).strip()
        if not pid:
            return {}
        
        resultado = {
            "id": pid,
            "sigla": "",
            "numero": "",
            "ano": "",
            "ementa": "",
            "urlInteiroTeor": "",
            "status_dataHora": "",
            "status_siglaOrgao": "",
            "status_descricaoTramitacao": "",
            "status_descricaoSituacao": "",
            "status_despacho": "",
            "tramitacoes": [],
            "relator": {},
        }
        
        # 1. Dados básicos + Status
        prop = self.get_proposicao(pid)
        if prop:
            resultado.update(prop)
        
        # 2. Tramitações
        tramitacoes = self.get_tramitacoes(pid)
        resultado["tramitacoes"] = tramitacoes
        
        # 3. Relator (extraído das tramitações + API)
        relator = self.get_relator_atual(pid)
        resultado["relator"] = relator
        
        return resultado
    
    def build_status_map(
        self,
        ids: List[str],
        max_workers: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """
        Constrói mapa de status para múltiplas proposições.
        
        Args:
            ids: Lista de IDs
            max_workers: Threads para processamento paralelo
            
        Returns:
            Dict mapeando ID -> status
        """
        out = {}
        ids = [str(x) for x in (ids or []) if str(x).strip()]
        
        if not ids:
            return out
        
        def _one(pid: str):
            dados = self.get_proposicao_completa(pid)
            
            relator_info = dados.get("relator", {}) or {}
            relator_txt = ""
            relator_id = ""
            
            if relator_info and relator_info.get("nome"):
                nome = relator_info.get("nome", "")
                partido = relator_info.get("partido", "")
                uf = relator_info.get("uf", "")
                relator_id = str(relator_info.get("id_deputado", ""))
                
                if partido or uf:
                    relator_txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
                else:
                    relator_txt = nome
            
            return pid, {
                "situacao": dados.get("status_descricaoSituacao", ""),
                "andamento": dados.get("status_descricaoTramitacao", ""),
                "status_dataHora": dados.get("status_dataHora", ""),
                "siglaOrgao": dados.get("status_siglaOrgao", ""),
                "relator": relator_txt,
                "relator_id": relator_id,
                "sigla_tipo": dados.get("sigla", ""),
                "ementa": dados.get("ementa", ""),
            }
        
        workers = 10 if len(ids) >= 40 else 6
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for pid, payload in ex.map(_one, ids):
                out[str(pid)] = payload
        
        return out
