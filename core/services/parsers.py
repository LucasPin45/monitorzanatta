"""
Funções puras de parsing e extração de dados.

REGRAS:
- SEM Streamlit
- SEM requests/HTTP
- SEM pandas (dados retornados como dicts/lists)
- Funções puras (entrada -> saída)
"""

import re
import json
import datetime
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Any, Tuple


# ============================================================
# PARSING DE JSON - CÂMARA
# ============================================================

def parse_proposicao_dados(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai dados básicos de uma proposição da resposta da API.
    
    Args:
        data: Resposta da API /proposicoes/{id}
        
    Returns:
        Dict com campos normalizados
    """
    if not data or not isinstance(data, dict):
        return {}
    
    d = data.get("dados", {}) or {}
    
    resultado = {
        "id": str(d.get("id") or ""),
        "sigla": (d.get("siglaTipo") or "").strip(),
        "numero": str(d.get("numero") or "").strip(),
        "ano": str(d.get("ano") or "").strip(),
        "ementa": (d.get("ementa") or "").strip(),
        "urlInteiroTeor": d.get("urlInteiroTeor") or "",
    }
    
    # Status
    status = d.get("statusProposicao", {}) or {}
    resultado.update({
        "status_dataHora": status.get("dataHora") or "",
        "status_siglaOrgao": status.get("siglaOrgao") or "",
        "status_descricaoTramitacao": status.get("descricaoTramitacao") or "",
        "status_descricaoSituacao": status.get("descricaoSituacao") or "",
        "status_despacho": status.get("despacho") or "",
    })
    
    return resultado


def parse_proposicao_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai dados de um item de lista de proposições.
    
    Args:
        item: Item da lista /proposicoes
        
    Returns:
        Dict com campos normalizados
    """
    return {
        "id": str(item.get("id") or ""),
        "siglaTipo": (item.get("siglaTipo") or "").strip(),
        "numero": str(item.get("numero") or "").strip(),
        "ano": str(item.get("ano") or "").strip(),
        "ementa": (item.get("ementa") or "").strip(),
    }


def parse_tramitacoes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de tramitações da resposta da API.
    
    Args:
        data: Resposta da API /proposicoes/{id}/tramitacoes
        
    Returns:
        Lista de tramitações
    """
    if not data or not isinstance(data, dict):
        return []
    
    return data.get("dados", []) or []


def parse_relatores(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de relatores da resposta da API.
    
    Args:
        data: Resposta da API /proposicoes/{id}/relatores
        
    Returns:
        Lista de relatores
    """
    if not data or not isinstance(data, dict):
        return []
    
    return data.get("dados", []) or []


def parse_eventos(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de eventos da resposta da API.
    
    Args:
        data: Resposta da API /eventos
        
    Returns:
        Lista de eventos
    """
    if not data or not isinstance(data, dict):
        return []
    
    return data.get("dados", []) or []


def parse_pauta(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de itens da pauta de um evento.
    
    Args:
        data: Resposta da API /eventos/{id}/pauta
        
    Returns:
        Lista de itens da pauta
    """
    if not data or not isinstance(data, dict):
        return []
    
    return data.get("dados", []) or []


def parse_deputados(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de deputados da resposta da API.
    
    Args:
        data: Resposta da API /deputados
        
    Returns:
        Lista de deputados
    """
    if not data or not isinstance(data, dict):
        return []
    
    return data.get("dados", []) or []


def has_next_page(data: Dict[str, Any]) -> bool:
    """
    Verifica se há próxima página nos links.
    
    Args:
        data: Resposta da API com links
        
    Returns:
        True se há próxima página
    """
    if not data or not isinstance(data, dict):
        return False
    
    links = data.get("links", [])
    return any(link.get("rel") == "next" for link in links)


def get_next_page_url(data: Dict[str, Any]) -> Optional[str]:
    """
    Extrai URL da próxima página.
    
    Args:
        data: Resposta da API com links
        
    Returns:
        URL da próxima página ou None
    """
    if not data or not isinstance(data, dict):
        return None
    
    links = data.get("links", [])
    for link in links:
        if link.get("rel") == "next":
            return link.get("href")
    
    return None


# ============================================================
# EXTRAÇÃO DE RELATOR DAS TRAMITAÇÕES
# ============================================================

# Padrões para extrair relator do texto de tramitação
RELATOR_PATTERNS = [
    r'Designad[oa]\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
    r'Relator[a]?:?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
    r'Parecer\s+(?:do|da)\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
]


def extrair_relator_de_tramitacoes(
    tramitacoes: List[Dict[str, Any]],
    orgao_atual: str = ""
) -> Dict[str, Any]:
    """
    Extrai informações do relator das tramitações.
    
    Args:
        tramitacoes: Lista de tramitações
        orgao_atual: Órgão atual para priorizar relator
        
    Returns:
        Dict com nome, partido, uf do relator ou {}
    """
    if not tramitacoes:
        return {}
    
    relator_orgao_atual = None
    relator_qualquer = None
    
    # Ordenar por data (mais recente primeiro)
    tramitacoes_ordenadas = sorted(
        tramitacoes,
        key=lambda x: x.get("dataHora") or x.get("data") or "",
        reverse=True
    )
    
    for t in tramitacoes_ordenadas:
        despacho = t.get("despacho") or ""
        desc = t.get("descricaoTramitacao") or ""
        orgao_tram = t.get("siglaOrgao") or ""
        texto = f"{despacho} {desc}"
        
        for pattern in RELATOR_PATTERNS:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                partido = match.group(2).strip()
                uf = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ""
                
                if nome and len(nome) > 3:
                    candidato = {"nome": nome, "partido": partido, "uf": uf}
                    
                    # Priorizar relator do órgão atual
                    if orgao_tram and orgao_atual and orgao_tram.upper() == orgao_atual.upper():
                        if not relator_orgao_atual:
                            relator_orgao_atual = candidato
                            break
                    
                    if not relator_qualquer:
                        relator_qualquer = candidato
                    
                    break
        
        if relator_orgao_atual:
            break
    
    return relator_orgao_atual or relator_qualquer or {}


def extrair_relator_de_relatores(relatores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extrai informações do relator da lista de relatores.
    
    Args:
        relatores: Lista de relatores da API
        
    Returns:
        Dict com nome, partido, uf, id_deputado ou {}
    """
    if not relatores:
        return {}
    
    r = relatores[0]
    nome = r.get("nome") or r.get("nomeRelator") or ""
    partido = r.get("siglaPartido") or r.get("partido") or ""
    uf = r.get("siglaUf") or r.get("uf") or ""
    id_dep = r.get("id") or r.get("idDeputado") or ""
    
    # Tentar extrair de estrutura aninhada
    dep = r.get("deputado") or r.get("parlamentar") or {}
    if isinstance(dep, dict):
        nome = nome or dep.get("nome") or dep.get("nomeCivil") or ""
        partido = partido or dep.get("siglaPartido") or dep.get("partido") or ""
        uf = uf or dep.get("siglaUf") or dep.get("uf") or ""
        id_dep = id_dep or dep.get("id") or ""
    
    if nome:
        return {
            "nome": nome,
            "partido": partido,
            "uf": uf,
            "id_deputado": str(id_dep) if id_dep else ""
        }
    
    return {}


# ============================================================
# PARSING DE JSON/XML - SENADO
# ============================================================

def parse_processo_senado(data: Any) -> Optional[Dict[str, Any]]:
    """
    Extrai dados do processo do Senado.
    
    Args:
        data: Resposta da API /processo (pode ser lista ou dict)
        
    Returns:
        Dict com dados ou None
    """
    if not data:
        return None
    
    # Normalizar para lista
    itens = data if isinstance(data, list) else [data]
    
    if not itens:
        return None
    
    # Pegar primeiro item
    escolhido = itens[0]
    
    codigo_materia = str(escolhido.get("codigoMateria") or "").strip()
    id_processo = str(escolhido.get("id") or "").strip()
    identificacao = str(escolhido.get("identificacao") or "").strip()
    situacao = str(escolhido.get("situacao") or escolhido.get("situacaoAtual") or "").strip()
    
    if not codigo_materia:
        return None
    
    return {
        "codigo_materia": codigo_materia,
        "id_processo": id_processo,
        "identificacao": identificacao,
        "situacao": situacao,
    }


def parse_processo_senado_com_identificacao(
    data: Any,
    identificacao_alvo: str
) -> Optional[Dict[str, Any]]:
    """
    Extrai dados do processo do Senado buscando identificação específica.
    
    Args:
        data: Resposta da API /processo
        identificacao_alvo: Ex: "PL 123/2023"
        
    Returns:
        Dict com dados ou None
    """
    if not data:
        return None
    
    itens = data if isinstance(data, list) else [data]
    
    if not itens:
        return None
    
    # Buscar por identificação
    escolhido = None
    for it in itens:
        ident = (it.get("identificacao") or "").strip()
        if ident.upper() == identificacao_alvo.upper():
            escolhido = it
            break
    
    if escolhido is None:
        escolhido = itens[0]
    
    return parse_processo_senado([escolhido])


def parse_relatoria_senado_json(data: Any) -> List[Dict[str, Any]]:
    """
    Extrai relatorias de resposta JSON do Senado.
    
    Args:
        data: Resposta JSON (lista ou dict)
        
    Returns:
        Lista de relatorias
    """
    if not data:
        return []
    
    if isinstance(data, list):
        return data
    
    if isinstance(data, dict):
        # Tentar chaves comuns
        for k in ("relatorias", "Relatorias", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    
    return []


def parse_relatoria_senado_xml(content: bytes) -> List[Dict[str, Any]]:
    """
    Extrai relatorias de resposta XML do Senado.
    
    Args:
        content: Bytes do XML
        
    Returns:
        Lista de relatorias
    """
    try:
        root = ET.fromstring(content)
    except Exception:
        return []
    
    def strip_ns(tag: str) -> str:
        """Remove namespace do tag."""
        return tag.split("}", 1)[-1] if "}" in tag else tag
    
    relatorias = []
    
    # Buscar nós de relatoria
    rel_nodes = []
    for el in root.iter():
        if strip_ns(el.tag).lower() in ("relatoria", "relator"):
            rel_nodes.append(el)
    
    for el in rel_nodes:
        values = {}
        for child in el.iter():
            t = strip_ns(child.tag)
            if child.text and child.text.strip():
                values[t] = child.text.strip()
        
        if values:
            relatorias.append({
                "dataDestituicao": values.get("dataDestituicao") or values.get("DataDestituicao"),
                "descricaoTipoRelator": values.get("descricaoTipoRelator") or values.get("DescricaoTipoRelator"),
                "dataDesignacao": values.get("dataDesignacao") or values.get("DataDesignacao"),
                "nomeParlamentar": values.get("nomeParlamentar") or values.get("NomeParlamentar"),
                "siglaPartidoParlamentar": values.get("siglaPartidoParlamentar") or values.get("SiglaPartidoParlamentar"),
                "ufParlamentar": values.get("ufParlamentar") or values.get("UfParlamentar"),
                "siglaColegiado": values.get("siglaColegiado") or values.get("SiglaColegiado"),
                "nomeColegiado": values.get("nomeColegiado") or values.get("NomeColegiado"),
            })
    
    return relatorias


def selecionar_relatoria_ativa(relatorias: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Seleciona a relatoria ativa de uma lista.
    
    Args:
        relatorias: Lista de relatorias
        
    Returns:
        Relatoria ativa ou None
    """
    if not relatorias:
        return None
    
    def is_active(r: Dict) -> bool:
        dd = r.get("dataDestituicao")
        return dd in (None, "", "null")
    
    candidatas = [r for r in relatorias if is_active(r)]
    if not candidatas:
        candidatas = relatorias
    
    # Preferir tipo "Relator"
    relator_cands = [r for r in candidatas if (r.get("descricaoTipoRelator") or "").lower() == "relator"]
    if relator_cands:
        candidatas = relator_cands
    
    # Ordenar por data (mais recente primeiro)
    candidatas.sort(key=lambda r: (r.get("dataDesignacao") or "").strip(), reverse=True)
    
    return candidatas[0] if candidatas else None


def parse_informes_senado_json(proc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai informes legislativos de resposta JSON do processo.
    
    Args:
        proc: Resposta JSON do processo
        
    Returns:
        Lista de informes
    """
    if not isinstance(proc, dict):
        return []
    
    try:
        autuacoes = proc.get("autuacoes") or []
        if autuacoes and isinstance(autuacoes, list):
            return autuacoes[0].get("informesLegislativos") or []
    except Exception:
        pass
    
    return []


def parse_informes_senado_xml(content: bytes) -> List[Dict[str, Any]]:
    """
    Extrai informes legislativos de resposta XML do processo.
    
    Args:
        content: Bytes do XML
        
    Returns:
        Lista de informes
    """
    try:
        root = ET.fromstring(content)
    except Exception:
        return []
    
    informes = []
    
    for it in root.findall(".//informesLegislativos//informeLegislativo"):
        data_txt = (it.findtext("data") or "").strip()
        desc = (it.findtext("descricao") or "").strip()
        coleg_sigla = (it.findtext(".//colegiado/sigla") or "").strip()
        
        informes.append({
            "data": data_txt,
            "descricao": desc,
            "colegiado": {"sigla": coleg_sigla}
        })
    
    return informes


def parse_status_senado_json(proc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai situação e órgão atual de resposta JSON do processo.
    
    Args:
        proc: Resposta JSON do processo
        
    Returns:
        Dict com situacao e órgão
    """
    out = {"situacao": "", "orgao_sigla": "", "orgao_nome": ""}
    
    if not isinstance(proc, dict):
        return out
    
    autuacoes = proc.get("autuacoes") or []
    if not autuacoes or not isinstance(autuacoes, list):
        return out
    
    a0 = autuacoes[0] or {}
    out["orgao_sigla"] = (a0.get("siglaColegiadoControleAtual") or "").strip()
    out["orgao_nome"] = (a0.get("nomeColegiadoControleAtual") or "").strip()
    
    situacoes = a0.get("situacoes") or []
    if isinstance(situacoes, list) and situacoes:
        # Buscar situação ativa (sem fim)
        ativa = None
        for s in reversed(situacoes):
            if not s.get("fim"):
                ativa = s
                break
        if not ativa:
            ativa = situacoes[-1]
        out["situacao"] = (ativa.get("descricao") or "").strip()
    
    return out


def parse_status_senado_xml(content: bytes) -> Dict[str, Any]:
    """
    Extrai situação e órgão atual de resposta XML do processo.
    
    Args:
        content: Bytes do XML
        
    Returns:
        Dict com situacao e órgão
    """
    out = {"situacao": "", "orgao_sigla": "", "orgao_nome": ""}
    
    try:
        root = ET.fromstring(content)
    except Exception:
        return out
    
    out["orgao_sigla"] = (root.findtext(".//autuacao/siglaColegiadoControleAtual") or "").strip()
    out["orgao_nome"] = (root.findtext(".//autuacao/nomeColegiadoControleAtual") or "").strip()
    
    situacoes = root.findall(".//autuacao/situacoes/situacao")
    if situacoes:
        ativa = None
        for s in reversed(situacoes):
            fim = (s.findtext("fim") or "").strip()
            if not fim:
                ativa = s
                break
        if not ativa:
            ativa = situacoes[-1]
        out["situacao"] = (ativa.findtext("descricao") or "").strip()
    
    return out


def parse_senadores_lista(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai lista de senadores da API.
    
    Args:
        data: Resposta da API /senador/lista/atual
        
    Returns:
        Lista de senadores com código e nome
    """
    if not isinstance(data, dict):
        return []
    
    lista = data.get("ListaParlamentarEmExercicio", {})
    parls = lista.get("Parlamentares", {})
    parlamentares = parls.get("Parlamentar", [])
    
    if not isinstance(parlamentares, list):
        parlamentares = [parlamentares] if parlamentares else []
    
    result = []
    for p in parlamentares:
        ident = p.get("IdentificacaoParlamentar", {})
        result.append({
            "codigo": ident.get("CodigoParlamentar"),
            "nome_parlamentar": (ident.get("NomeParlamentar") or "").lower(),
            "nome_completo": (ident.get("NomeCompletoParlamentar") or "").lower(),
        })
    
    return result


def parse_materias_senado(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai matérias da pesquisa do Senado.
    
    Args:
        data: Resposta da API /materia/pesquisa/lista
        
    Returns:
        Lista de matérias
    """
    if not isinstance(data, dict):
        return []
    
    if "PesquisaBasicaMateria" not in data:
        return []
    
    pesquisa = data["PesquisaBasicaMateria"]
    
    if "Materias" not in pesquisa:
        return []
    
    if "Materia" not in pesquisa["Materias"]:
        return []
    
    materias_raw = pesquisa["Materias"]["Materia"]
    
    if not isinstance(materias_raw, list):
        materias_raw = [materias_raw]
    
    return materias_raw


# ============================================================
# EXTRAÇÃO DE ID DE URI
# ============================================================

def extract_id_from_uri(uri: str) -> Optional[str]:
    """
    Extrai ID de uma URI da API da Câmara.
    
    Args:
        uri: URI como "https://dadosabertos.camara.leg.br/api/v2/proposicoes/123456"
        
    Returns:
        ID extraído ou None
    """
    if not uri:
        return None
    
    uri = str(uri).strip()
    
    # Padrão: último segmento numérico da URL
    match = re.search(r'/(\d+)/?$', uri)
    if match:
        return match.group(1)
    
    # Fallback: qualquer número no final
    match = re.search(r'(\d+)\s*$', uri)
    if match:
        return match.group(1)
    
    return None


def get_proposicao_id_from_item(item: Dict[str, Any]) -> Optional[str]:
    """
    Extrai ID da proposição de um item de pauta ou relacionada.
    
    Args:
        item: Item com estrutura aninhada
        
    Returns:
        ID ou None
    """
    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_", "proposicao_relacionada"],
        ["proposicaoPrincipal", "proposicao_principal"],
        ["proposicao", "proposicao_"],
    ]
    
    # Primeiro tentar ID direto
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                if prop.get("id"):
                    return str(prop["id"])
                if prop.get("idProposicao"):
                    return str(prop["idProposicao"])
    
    # Depois tentar extrair de URI
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                uri = prop.get("uri") or prop.get("uriProposicao") or prop.get("uriProposicaoPrincipal")
                if uri:
                    return extract_id_from_uri(uri)
    
    # Fallback: URI no próprio item
    for chave_uri in ["uriProposicaoPrincipal", "uriProposicao", "uri"]:
        if item.get(chave_uri):
            return extract_id_from_uri(item[chave_uri])
    
    return None


# ============================================================
# PARSING DE DATAS
# ============================================================

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
]


def parse_datetime(data_str: str) -> Optional[datetime.datetime]:
    """
    Tenta parsear string de data/hora em vários formatos.
    
    Args:
        data_str: String de data
        
    Returns:
        datetime ou None
    """
    if not data_str:
        return None
    
    data_str = data_str.strip()[:26]  # Limitar para microsegundos
    
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(data_str, fmt)
        except ValueError:
            continue
    
    return None


def format_datetime_br(dt: Optional[datetime.datetime]) -> Tuple[str, str]:
    """
    Formata datetime para padrão brasileiro.
    
    Args:
        dt: datetime
        
    Returns:
        (data, hora) no formato brasileiro
    """
    if not dt:
        return ("", "")
    
    return (dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"))


# ============================================================
# EXTRAÇÃO DE PL PRINCIPAL DO TEXTO
# ============================================================

PL_PRINCIPAL_PATTERNS = [
    r'apensad[ao]\s+(?:ao?|à)\s+(?:PL|PLP|PEC|PDL|MPV)\s*(\d+)[/\.](\d{4})',
    r'tramita(?:r|ndo)?\s+(?:em\s+)?conjunto\s+(?:com|ao?|à)\s+(?:PL|PLP|PEC|PDL|MPV)\s*(\d+)[/\.](\d{4})',
    r'anexad[ao]\s+(?:ao?|à)\s+(?:PL|PLP|PEC|PDL|MPV)\s*(\d+)[/\.](\d{4})',
]


def extrair_pl_principal_do_texto(texto: str) -> Optional[Dict[str, str]]:
    """
    Extrai referência ao PL principal de um texto de tramitação.
    
    Args:
        texto: Texto de tramitação/despacho
        
    Returns:
        Dict com tipo, numero, ano ou None
    """
    if not texto:
        return None
    
    texto_lower = texto.lower()
    
    # Verificar se menciona apensamento
    if not any(kw in texto_lower for kw in ["apensad", "anexad", "tramita", "conjunto"]):
        return None
    
    # Extrair tipo/número/ano
    match = re.search(
        r'(PL|PLP|PEC|PDL|MPV)\s*(\d+)[/\.](\d{4})',
        texto,
        re.IGNORECASE
    )
    
    if match:
        tipo = match.group(1).upper()
        numero = match.group(2)
        ano = match.group(3)
        
        return {
            "tipo": tipo,
            "numero": numero,
            "ano": ano,
            "pl_principal": f"{tipo} {numero}/{ano}"
        }
    
    return None
