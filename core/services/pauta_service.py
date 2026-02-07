# core/services/pauta_service.py
"""
Serviço para processamento de eventos e pautas da Câmara dos Deputados.
Funções auxiliares extraídas do monólito.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Set
import re
import pandas as pd
import streamlit as st
from functools import lru_cache

from core.utils import (
    normalize_text,
    extract_id_from_uri,
    format_sigla_num_ano,
    is_comissao_estrategica,
)

from core.config import BASE_URL


def safe_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Faz requisição HTTP GET com tratamento de erros.
    
    Args:
        url: URL do endpoint
        params: Parâmetros da requisição
        
    Returns:
        Dados da resposta ou None em caso de erro
        
    Nota:
        - Esta função deve estar em core.utils ou core.services.camara_service
        - Incluída aqui para referência
    """
    import requests
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERRO] safe_get({url}): {e}")
        return {"__error__": str(e)}


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pauta_evento(event_id: str) -> List[Dict[str, Any]]:
    """
    Busca a pauta de um evento específico da Câmara.
    
    Args:
        event_id: ID do evento
        
    Returns:
        Lista de itens da pauta (cada item é um dict)
        
    Endpoint: GET /api/v2/eventos/{event_id}/pauta
    Cache: 1 hora
    """
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    
    if data is None or "__error__" in data:
        return []
    
    return data.get("dados", [])


def get_proposicao_id_from_item(item: Dict[str, Any]) -> Optional[str]:
    """
    Extrai ID de proposição de um item da pauta.
    
    A API da Câmara pode retornar o ID em vários campos diferentes
    dependendo do tipo de item. Esta função tenta todos os possíveis.
    
    Args:
        item: Item da pauta do evento
        
    Returns:
        ID da proposição como string, ou None se não encontrado
        
    Ordem de busca:
        1. proposicaoRelacionada.id
        2. proposicaoRelacionada.idProposicao  
        3. proposicaoPrincipal.id
        4. proposicaoPrincipal.idProposicao
        5. proposicao.id
        6. proposicao.idProposicao
        7. URIs (extração do ID da URI)
    """
    # Grupos de campos para testar, em ordem de prioridade
    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_", "proposicao_relacionada"],
        ["proposicaoPrincipal", "proposicao_principal"],
        ["proposicao", "proposicao_"],
    ]
    
    # Tentar pegar ID direto dos campos
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                # Tentar campo "id"
                if prop.get("id"):
                    return str(prop["id"])
                # Tentar campo "idProposicao"
                if prop.get("idProposicao"):
                    return str(prop["idProposicao"])
    
    # Se não achou, tentar extrair de URIs
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                uri = (
                    prop.get("uri") 
                    or prop.get("uriProposicao") 
                    or prop.get("uriProposicaoPrincipal")
                )
                if uri:
                    id_extracted = extract_id_from_uri(uri)
                    if id_extracted:
                        return id_extracted
    
    # Última tentativa: buscar URIs diretas no item
    for chave_uri in ["uriProposicaoPrincipal", "uriProposicao", "uri"]:
        uri = item.get(chave_uri)
        if uri:
            id_extracted = extract_id_from_uri(uri)
            if id_extracted:
                return id_extracted
    
    return None


def pauta_item_tem_relatoria_deputada(
    item: Dict[str, Any],
    alvo_nome: str,
    alvo_partido: str,
    alvo_uf: str
) -> bool:
    """
    Verifica se a deputada alvo é relatora no item da pauta.
    
    Args:
        item: Item da pauta
        alvo_nome: Nome da deputada (ex: "Júlia Zanatta")
        alvo_partido: Sigla do partido (ex: "PL")
        alvo_uf: UF (ex: "SC")
        
    Returns:
        True se a deputada é relatora deste item
        
    Critérios:
        - Nome deve conter o nome alvo (normalizado)
        - Partido deve bater exatamente (se ambos presentes)
        - UF deve bater exatamente (se ambos presentes)
    """
    relator = item.get("relator") or {}
    
    nome = relator.get("nome") or ""
    partido = relator.get("siglaPartido") or ""
    uf = relator.get("siglaUf") or ""
    
    # Verificar nome (normalizado)
    if normalize_text(alvo_nome) not in normalize_text(nome):
        return False
    
    # Verificar partido (se ambos presentes)
    if alvo_partido and partido:
        if normalize_text(alvo_partido) != normalize_text(partido):
            return False
    
    # Verificar UF (se ambos presentes)
    if alvo_uf and uf:
        if normalize_text(alvo_uf) != normalize_text(uf):
            return False
    
    return True


def pauta_item_palavras_chave(
    item: Dict[str, Any],
    palavras_chave_normalizadas: List[tuple],
    id_prop: Optional[str] = None
) -> Set[str]:
    """
    Busca palavras-chave na ementa e descrição do item da pauta.
    
    Args:
        item: Item da pauta
        palavras_chave_normalizadas: Lista de tuplas (palavra_normalizada, palavra_original)
        id_prop: ID da proposição (opcional) para buscar ementa completa
        
    Returns:
        Set de palavras-chave encontradas (originais)
        
    IMPORTANTE: Busca por PALAVRA INTEIRA para evitar falsos positivos
    (ex: "arma" não deve casar com "Farmanguinhos")
    """
    textos = []
    
    # Buscar nos campos do item da pauta
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        v = item.get(chave)
        if v:
            textos.append(str(v))
    
    # Buscar nos campos da proposição interna do item
    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop.get(chave)
        if v:
            textos.append(str(v))
    
    # Buscar na proposição relacionada
    prop_rel = item.get("proposicaoRelacionada") or item.get("proposicao_") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop_rel.get(chave)
        if v:
            textos.append(str(v))
    
    # Se tiver ID da proposição, buscar ementa completa na API
    if id_prop:
        info_prop = fetch_proposicao_info_cached(id_prop)
        if info_prop and info_prop.get("ementa"):
            textos.append(info_prop["ementa"])
    
    # Normalizar texto combinado
    texto_norm = normalize_text(" ".join(textos))
    encontradas = set()
    
    # Buscar cada palavra-chave usando regex para palavra inteira
    for kw_norm, kw_original in palavras_chave_normalizadas:
        if not kw_norm:
            continue
        
        # Usar regex com word boundary para buscar palavra inteira
        # Isso evita que "arma" case com "farmanguinhos"
        pattern = r'\b' + re.escape(kw_norm) + r'\b'
        if re.search(pattern, texto_norm):
            encontradas.add(kw_original)
    
    return encontradas


@lru_cache(maxsize=4096)
def fetch_proposicao_info_cached(id_proposicao: str) -> Dict[str, Any]:
    """
    Busca informações básicas de uma proposição pelo ID.
    
    Args:
        id_proposicao: ID da proposição
        
    Returns:
        Dict com campos:
            - id: ID (string)
            - sigla: Tipo da proposição (PL, PLP, etc.)
            - numero: Número
            - ano: Ano
            - ementa: Ementa completa
            
    Em caso de erro, retorna dict com valores vazios.
    
    Cache: LRU cache de 4096 itens
    """
    data = safe_get(f"{BASE_URL}/proposicoes/{id_proposicao}")
    
    if data is None or "__error__" in data:
        return {
            "id": str(id_proposicao),
            "sigla": "",
            "numero": "",
            "ano": "",
            "ementa": ""
        }
    
    dados = data.get("dados", {})
    
    return {
        "id": str(dados.get("id") or id_proposicao),
        "sigla": (dados.get("siglaTipo") or "").strip(),
        "numero": str(dados.get("numero") or "").strip(),
        "ano": str(dados.get("ano") or "").strip(),
        "ementa": (dados.get("ementa") or "").strip(),
    }


def escanear_eventos(
    eventos: List[Dict[str, Any]],
    alvo_nome: str,
    alvo_partido: str,
    alvo_uf: str,
    comissoes_estrategicas: List[str],
    palavras_chave: Optional[List[str]] = None,
    ids_autoria_deputada: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Escaneia eventos da Câmara buscando autoria, relatoria e/ou palavras-chave.
    
    Args:
        eventos: Lista de eventos (retorno de GET /eventos)
        alvo_nome: Nome da deputada
        alvo_partido: Partido da deputada
        alvo_uf: UF da deputada
        comissoes_estrategicas: Lista de siglas de comissões estratégicas
        palavras_chave: Lista de palavras-chave a buscar (opcional)
        ids_autoria_deputada: Set de IDs de proposições de autoria (opcional)
        
    Returns:
        DataFrame com eventos filtrados contendo autoria, relatoria ou palavras-chave
        
    Colunas do DataFrame:
        - data, hora, orgao_id, orgao_sigla, orgao_nome
        - id_evento, tipo_evento, descricao_evento
        - tem_relatoria_deputada, proposicoes_relatoria, ids_proposicoes_relatoria
        - tem_autoria_deputada, proposicoes_autoria, ids_proposicoes_autoria
        - tem_palavras_chave, palavras_chave_encontradas, proposicoes_palavras_chave
        - comissao_estrategica
    """
    if ids_autoria_deputada is None:
        ids_autoria_deputada = set()
    
    if palavras_chave is None:
        palavras_chave = []
    
    # Normalizar palavras-chave
    palavras_chave_norm = [(normalize_text(p), p) for p in palavras_chave if p.strip()]
    
    registros = []
    
    for ev in eventos:
        event_id = ev.get("id") or ev.get("codEvento")
        if event_id is None:
            continue
        
        # Extrair data e hora
        data_hora_ini = ev.get("dataHoraInicio") or ""
        data_str = data_hora_ini[:10] if len(data_hora_ini) >= 10 else ""
        hora_str = data_hora_ini[11:16] if len(data_hora_ini) >= 16 else ""
        
        descricao_evento = ev.get("descricao") or ""
        tipo_evento = ev.get("descricaoTipo") or ""
        
        # Órgãos do evento
        orgaos = ev.get("orgaos") or []
        if not orgaos:
            orgaos = [{"sigla": "", "nome": "", "id": None}]
        
        # Buscar pauta do evento
        pauta = fetch_pauta_evento(str(event_id))
        
        # Sets para acumular proposições
        proposicoes_relatoria = set()
        proposicoes_autoria = set()
        ids_proposicoes_autoria = set()
        ids_proposicoes_relatoria = set()
        palavras_evento = set()
        proposicoes_palavras_chave = set()
        
        # Processar cada item da pauta
        for item in pauta:
            # Extrair ID da proposição
            id_prop = get_proposicao_id_from_item(item)
            
            # Verificar palavras-chave
            kws_item = pauta_item_palavras_chave(item, palavras_chave_norm, id_prop)
            has_keywords = bool(kws_item)
            
            # Verificar relatoria
            relatoria_flag = pauta_item_tem_relatoria_deputada(
                item, alvo_nome, alvo_partido, alvo_uf
            )
            
            # Verificar autoria
            autoria_flag = False
            if ids_autoria_deputada and id_prop:
                autoria_flag = id_prop in ids_autoria_deputada
            
            # Se não tem nem autoria, nem relatoria, nem palavras-chave, pular
            if not (relatoria_flag or autoria_flag or has_keywords):
                continue
            
            # Buscar informações da proposição
            identificacao = "(proposição não identificada)"
            ementa_prop = ""
            
            if id_prop:
                info = fetch_proposicao_info_cached(id_prop)
                identificacao = format_sigla_num_ano(
                    info["sigla"], 
                    info["numero"], 
                    info["ano"]
                ) or identificacao
                ementa_prop = info["ementa"]
            
            # Montar texto completo
            texto_completo = (
                f"{identificacao} – {ementa_prop}" 
                if ementa_prop 
                else identificacao
            )
            
            # Adicionar aos sets apropriados
            if relatoria_flag:
                proposicoes_relatoria.add(texto_completo)
                if id_prop:
                    ids_proposicoes_relatoria.add(str(id_prop))
            
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
                if id_prop:
                    ids_proposicoes_autoria.add(str(id_prop))
            
            if has_keywords:
                for kw in kws_item:
                    palavras_evento.add(kw)
                
                # Pegar relator do item
                relator_info = item.get("relator") or {}
                relator_nome = relator_info.get("nome") or ""
                relator_partido = relator_info.get("siglaPartido") or ""
                relator_uf = relator_info.get("siglaUf") or ""
                
                if relator_nome:
                    relator_str = f"{relator_nome} ({relator_partido}-{relator_uf})"
                else:
                    relator_str = "Sem relator designado"
                
                # Link para tramitação
                link_tram = (
                    f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_prop}" 
                    if id_prop 
                    else ""
                )
                
                # Armazenar com formato detalhado incluindo comissão e data
                # formato: matéria|||palavras|||ementa|||link|||relator|||comissao|||nome_comissao|||data
                for org in orgaos:
                    sigla_org_temp = org.get("siglaOrgao") or org.get("sigla") or ""
                    nome_org_temp = org.get("nomeOrgao") or org.get("nome") or ""
                    proposicoes_palavras_chave.add(
                        f"{identificacao}|||{', '.join(kws_item)}|||{ementa_prop}|||"
                        f"{link_tram}|||{relator_str}|||{sigla_org_temp}|||{nome_org_temp}|||{data_str}"
                    )
        
        # Se não achou nenhuma proposição relevante, pular evento
        if not (proposicoes_relatoria or proposicoes_autoria or palavras_evento):
            continue
        
        # Criar registro para cada órgão do evento
        for org in orgaos:
            sigla_org = org.get("siglaOrgao") or org.get("sigla") or ""
            nome_org = org.get("nomeOrgao") or org.get("nome") or ""
            orgao_id = org.get("id")
            
            registros.append({
                "data": data_str,
                "hora": hora_str,
                "orgao_id": orgao_id,
                "orgao_sigla": sigla_org,
                "orgao_nome": nome_org,
                "id_evento": event_id,
                "tipo_evento": tipo_evento,
                "descricao_evento": descricao_evento,
                "tem_relatoria_deputada": bool(proposicoes_relatoria),
                "proposicoes_relatoria": "; ".join(sorted(proposicoes_relatoria)),
                "ids_proposicoes_relatoria": ";".join(sorted(ids_proposicoes_relatoria)),
                "tem_autoria_deputada": bool(proposicoes_autoria),
                "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)),
                "ids_proposicoes_autoria": ";".join(sorted(ids_proposicoes_autoria)),
                "tem_palavras_chave": bool(palavras_evento),
                "palavras_chave_encontradas": "; ".join(sorted(palavras_evento)),
                "proposicoes_palavras_chave": "; ".join(sorted(proposicoes_palavras_chave)),
                "comissao_estrategica": is_comissao_estrategica(
                    sigla_org, 
                    comissoes_estrategicas
                ),
            })
    
    # Criar DataFrame
    df = pd.DataFrame(registros)
    
    # Ordenar
    if not df.empty:
        df = df.sort_values(["data", "hora", "orgao_sigla", "id_evento"])
    
    return df
