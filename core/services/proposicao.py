# core/services/proposicao.py
"""
Serviço de Proposições — API da Câmara dos Deputados

Contém toda a lógica de busca, consulta e enriquecimento de
proposições legislativas via API da Câmara.

Extraído do monólito v50.

Funcionalidades:
- Busca de proposições por autoria, tipo, ID
- Consulta completa de proposição (detalhes, tramitações, relatores)
- Busca de RICs por autor
- Mapa de status (build_status_map)
- Validação de respostas da API
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import re
import time
import datetime
from datetime import timezone

import streamlit as st
import requests
import pandas as pd

from core.utils.formatters import format_sigla_num_ano
from core.utils.text_utils import canonical_situacao, party_norm
from core.utils.links import extract_id_from_uri
from core.utils.date_utils import parse_prazo_resposta_ric
from core.services.apensados import PROPOSICOES_FALTANTES_API


# ============================================================
# CONFIGURAÇÃO
# ============================================================
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)"}

try:
    import certifi
    _REQUESTS_VERIFY = certifi.where()
except ImportError:
    _REQUESTS_VERIFY = True

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)


# ============================================================
# VALIDAÇÃO E HTTP
# ============================================================

def validar_resposta_api(response) -> tuple[bool, str]:
    """
    Valida se a resposta da API é válida.
    
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
        return False, f"Tipo de conteúdo inesperado: {content_type}"
    
    # Verificar se tem conteúdo
    if not response.text or len(response.text.strip()) == 0:
        return False, "API retornou resposta vazia"
    
    # Verificar se é JSON válido
    try:
        response.json()
        return True, ""
    except ValueError as e:
        return False, f"Resposta não é JSON válido: {str(e)}"



def _request_json(url: str, params=None, timeout=30, max_retries=3):
    params = params or {}
    backoffs = [0.5, 1.0, 2.0, 4.0]
    last_err = None

    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            if resp.status_code == 404:
                return None
            if resp.status_code in (429,) or (500 <= resp.status_code <= 599):
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
        except requests.exceptions.HTTPError as e:
            last_err = e
            break
        except Exception as e:
            last_err = e
            break

    return {"__error__": str(last_err) if last_err else "unknown_error"}



def safe_get(url, params=None):
    return _request_json(url, params=params, timeout=30, max_retries=3)


# ============================================================
# FUNÇÃO CENTRAL - BUSCA TUDO DE UMA VEZ
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)


# ============================================================
# APENSAÇÕES / TRAMITAÇÃO EM CONJUNTO — utilitários
# ============================================================


def fetch_proposicao_completa(id_proposicao: str) -> dict:
    """
    FUNÇÃO CENTRAL: Busca TODAS as informações da proposição de uma vez.
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
    
    # 1. DADOS BÁSICOS + STATUS
    try:
        data = safe_get(f"{BASE_URL}/proposicoes/{pid}")
        if data and isinstance(data, dict) and data.get("dados"):
            d = data.get("dados", {}) or {}
            resultado.update({
                "sigla": (d.get("siglaTipo") or "").strip(),
                "numero": str(d.get("numero") or "").strip(),
                "ano": str(d.get("ano") or "").strip(),
                "ementa": (d.get("ementa") or "").strip(),
                "urlInteiroTeor": d.get("urlInteiroTeor") or "",
            })
            
            status = d.get("statusProposicao", {}) or {}
            resultado.update({
                "status_dataHora": status.get("dataHora") or "",
                "status_siglaOrgao": status.get("siglaOrgao") or "",
                "status_descricaoTramitacao": status.get("descricaoTramitacao") or "",
                "status_descricaoSituacao": canonical_situacao(status.get("descricaoSituacao") or ""),
                "status_despacho": status.get("despacho") or "",
            })
    except Exception:
        pass
    
    # 2. TRAMITAÇÕES
    try:
        tramitacoes = []
        tram_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/tramitacoes")
        
        if tram_data and isinstance(tram_data, dict) and tram_data.get("dados"):
            tramitacoes = tram_data.get("dados", [])
        
        if not tramitacoes:
            pagina = 1
            while pagina <= 10:
                params = {"itens": 100, "ordem": "DESC", "ordenarPor": "dataHora", "pagina": pagina}
                tram_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/tramitacoes", params=params)
                
                if not tram_data or "__error__" in tram_data:
                    break
                
                dados = tram_data.get("dados", [])
                if not dados:
                    break
                
                tramitacoes.extend(dados)
                
                has_next = any(link.get("rel") == "next" for link in tram_data.get("links", []))
                if not has_next:
                    break
                
                pagina += 1
        
        resultado["tramitacoes"] = tramitacoes
        
    except Exception:
        pass
    
    # 3. EXTRAI RELATOR DAS TRAMITAÇÕES
    try:
        relator_info = {}
        patterns = [
            r'Designad[oa]\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
            r'Relator[a]?:?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
            r'Parecer\s+(?:do|da)\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
        ]
        
        orgao_atual = resultado.get("status_siglaOrgao", "")
        relator_orgao_atual = None
        relator_qualquer = None
        
        tramitacoes_ordenadas = sorted(
            resultado["tramitacoes"],
            key=lambda x: x.get("dataHora") or x.get("data") or "",
            reverse=True
        )
        
        for t in tramitacoes_ordenadas:
            despacho = t.get("despacho") or ""
            desc = t.get("descricaoTramitacao") or ""
            orgao_tram = t.get("siglaOrgao") or ""
            texto = f"{despacho} {desc}"
            
            for pattern in patterns:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    nome = match.group(1).strip()
                    partido = party_norm(match.group(2).strip())
                    uf = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ""
                    
                    if nome and len(nome) > 3:
                        candidato = {"nome": nome, "partido": partido, "uf": uf}
                        
                        if orgao_tram and orgao_atual and orgao_tram.upper() == orgao_atual.upper():
                            if not relator_orgao_atual:
                                relator_orgao_atual = candidato
                                break
                        
                        if not relator_qualquer:
                            relator_qualquer = candidato
                        
                        break
            
            if relator_orgao_atual:
                break
        
        relator_info = relator_orgao_atual or relator_qualquer
        
        if not relator_info:
            rel_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatores")
            if isinstance(rel_data, dict) and rel_data.get("dados"):
                candidatos = rel_data.get("dados", [])
                if candidatos:
                    r = candidatos[0]
                    nome = r.get("nome") or r.get("nomeRelator") or ""
                    partido = party_norm(r.get("siglaPartido") or r.get("partido") or "")
                    uf = r.get("siglaUf") or r.get("uf") or ""
                    id_dep = r.get("id") or r.get("idDeputado") or ""
                    
                    dep = r.get("deputado") or r.get("parlamentar") or {}
                    if isinstance(dep, dict):
                        nome = nome or dep.get("nome") or dep.get("nomeCivil") or ""
                        partido = partido or party_norm(dep.get("siglaPartido") or dep.get("partido") or "")
                        uf = uf or dep.get("siglaUf") or dep.get("uf") or ""
                        id_dep = id_dep or dep.get("id") or ""
                    
                    if nome:
                        relator_info = {"nome": nome, "partido": partido, "uf": uf, "id_deputado": str(id_dep)}
        
        if relator_info and not relator_info.get("id_deputado"):
            nome_relator = relator_info.get("nome", "")
            if nome_relator:
                dep_data = safe_get(f"{BASE_URL}/deputados", params={"nome": nome_relator, "itens": 5})
                if isinstance(dep_data, dict) and dep_data.get("dados"):
                    deps = dep_data.get("dados", [])
                    if deps:
                        relator_info["id_deputado"] = str(deps[0].get("id", ""))
        
        resultado["relator"] = relator_info
        
    except Exception:
        pass
    
    return resultado



@st.cache_data(show_spinner=False, ttl=1800)
def get_tramitacoes_ultimas10(id_prop):
    """Retorna as 10 últimas tramitações."""
    try:
        dados_completos = fetch_proposicao_completa(id_prop)
        tramitacoes = dados_completos.get("tramitacoes", [])
        
        if not tramitacoes:
            return pd.DataFrame()
        
        rows = []
        for t in tramitacoes:
            dh = t.get("dataHora") or ""
            if dh:
                rows.append({
                    "dataHora": dh,
                    "siglaOrgao": t.get("siglaOrgao") or "—",
                    "descricaoTramitacao": t.get("descricaoTramitacao") or "—",
                })
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df['dataHora_dt'] = pd.to_datetime(df['dataHora'], errors='coerce')
        df = df[df['dataHora_dt'].notna()].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        df['Data'] = df['dataHora_dt'].dt.strftime('%d/%m/%Y')
        df['Hora'] = df['dataHora_dt'].dt.strftime('%H:%M')
        df = df.sort_values('dataHora_dt', ascending=False)
        
        view = pd.DataFrame({
            "Data": df["Data"].values,
            "Hora": df["Hora"].values,
            "Órgão": df["siglaOrgao"].values,
            "Tramitação": df["descricaoTramitacao"].values,
        })
        
        resultado = view.head(10).reset_index(drop=True)
        
        return resultado
    except Exception:
        return pd.DataFrame()



@st.cache_data(show_spinner=False, ttl=1800)
def fetch_relator_atual(id_proposicao: str) -> dict:
    """Retorna relator usando a função centralizada."""
    try:
        dados_completos = fetch_proposicao_completa(id_proposicao)
        relator = dados_completos.get("relator", {})
        return relator
    except Exception:
        return {}



@lru_cache(maxsize=4096)
def fetch_proposicao_info(id_proposicao):
    data = safe_get(f"{BASE_URL}/proposicoes/{id_proposicao}")
    if data is None or "__error__" in data:
        return {"id": str(id_proposicao), "sigla": "", "numero": "", "ano": "", "ementa": ""}

    d = data.get("dados", {}) or {}
    return {
        "id": str(d.get("id") or id_proposicao),
        "sigla": (d.get("siglaTipo") or "").strip(),
        "numero": str(d.get("numero") or "").strip(),
        "ano": str(d.get("ano") or "").strip(),
        "ementa": (d.get("ementa") or "").strip(),
    }



@st.cache_data(show_spinner=False, ttl=3600)
def fetch_lista_proposicoes_autoria_geral(id_deputada):
    rows = []
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "DESC", "ordenarPor": "ano"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            rows.append(
                {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                }
            )

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break

        if not next_link:
            break
        url = next_link
        params = {}

    # WORKAROUND v33: Adicionar proposições que a API não retorna (bug da Câmara)
    id_str = str(id_deputada)
    if id_str in PROPOSICOES_FALTANTES_API:
        ids_existentes = {r["id"] for r in rows}
        for prop_faltante in PROPOSICOES_FALTANTES_API[id_str]:
            if prop_faltante["id"] not in ids_existentes:
                rows.append(prop_faltante)
                print(f"[API-WORKAROUND] ✅ Adicionada proposição faltante: {prop_faltante['siglaTipo']} {prop_faltante['numero']}/{prop_faltante['ano']} (ID {prop_faltante['id']})")

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Proposicao"] = df.apply(lambda r: format_sigla_num_ano(r["siglaTipo"], r["numero"], r["ano"]), axis=1)
    return df



@st.cache_data(show_spinner=False, ttl=1800)
def buscar_proposicao_direta(sigla_tipo: str, numero: str, ano: str) -> Optional[Dict]:
    """
    Busca proposição diretamente na API da Câmara por sigla/número/ano.
    Não depende de autoria - busca QUALQUER proposição.
    
    NOVO v32.2: Permite buscar proposições que a deputada acompanha
    mas não é autora.
    
    Args:
        sigla_tipo: PL, PLP, PEC, etc.
        numero: Número da proposição
        ano: Ano (4 dígitos)
        
    Returns:
        Dict com dados da proposição ou None
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
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        dados = data.get("dados", [])
        
        if not dados:
            return None
        
        # Pegar o primeiro resultado que bate exatamente
        for d in dados:
            if (str(d.get("numero", "")).strip() == num and 
                str(d.get("ano", "")).strip() == ano_str and
                (d.get("siglaTipo", "")).strip().upper() == sigla):
                return {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                    "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
                }
        
        # Se não achou exato, retorna o primeiro
        d = dados[0]
        return {
            "id": str(d.get("id") or ""),
            "siglaTipo": (d.get("siglaTipo") or "").strip(),
            "numero": str(d.get("numero") or "").strip(),
            "ano": str(d.get("ano") or "").strip(),
            "ementa": (d.get("ementa") or "").strip(),
            "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
        }
        
    except Exception as e:
        print(f"[BUSCA-DIRETA] Erro: {e}")
        return None



def parse_proposicao_input(texto: str) -> Optional[Tuple[str, str, str]]:
    """
    Extrai sigla, número e ano de uma string de proposição.
    
    Exemplos aceitos:
    - "PL 321/2023"
    - "PL321/2023" 
    - "pl 321 2023"
    - "PLP 223/2023"
    
    Returns:
        Tuple (sigla, numero, ano) ou None
    """
    
    texto = (texto or "").strip().upper()
    if not texto:
        return None
    
    # Padrão: SIGLA NUMERO/ANO ou SIGLA NUMERO ANO
    padrao = r"^(PL|PLP|PEC|PDL|PRC|PLV|MPV|RIC|REQ|PDS|PRS)\s*(\d+)\s*[/\s]\s*(\d{4})$"
    match = re.match(padrao, texto)
    
    if match:
        return (match.group(1), match.group(2), match.group(3))
    
    return None



@st.cache_data(show_spinner=False, ttl=3600)
def fetch_rics_por_autor(id_deputada):
    rows = []
    url = f"{BASE_URL}/proposicoes"
    params = {
        "siglaTipo": "RIC",
        "idDeputadoAutor": id_deputada,
        "itens": 100,
        "ordem": "DESC",
        "ordenarPor": "ano",
    }

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            rows.append(
                {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                    "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
                }
            )

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        if not next_link:
            break

        url = next_link
        params = {}

    return pd.DataFrame(rows)



@st.cache_data(show_spinner=False, ttl=3600)
def fetch_lista_proposicoes_autoria(id_deputada):
    df1 = fetch_lista_proposicoes_autoria_geral(id_deputada)
    df2 = fetch_rics_por_autor(id_deputada)

    if df1.empty and df2.empty:
        return pd.DataFrame(columns=["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"])

    df = pd.concat([df1, df2], ignore_index=True)

    if "Proposicao" not in df.columns:
        df["Proposicao"] = ""
    mask = df["Proposicao"].isna() | (df["Proposicao"].astype(str).str.strip() == "")
    if mask.any():
        df.loc[mask, "Proposicao"] = df.loc[mask].apply(
            lambda r: format_sigla_num_ano(r.get("siglaTipo"), r.get("numero"), r.get("ano")),
            axis=1
        )

    df = df.drop_duplicates(subset=["id"], keep="first")

    cols = ["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    return df


# ============================================================
# STATUS MAP
# ============================================================


@st.cache_data(show_spinner=False, ttl=900)
def build_status_map(ids: list[str]) -> dict:
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    # Lazy import — RIC helpers ainda no monólito
    from monitor_sistema_jz import extrair_ministerio_ric, extrair_assunto_ric

    def _one(pid: str):
        dados_completos = fetch_proposicao_completa(pid)
        
        situacao = canonical_situacao(dados_completos.get("status_descricaoSituacao", ""))
        andamento = dados_completos.get("status_descricaoTramitacao", "")
        relator_info = dados_completos.get("relator", {})
        tramitacoes = dados_completos.get("tramitacoes", [])
        sigla_tipo = dados_completos.get("sigla", "")
        ementa = dados_completos.get("ementa", "")
        
        # Formatar relator
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
        
        # Resultado base
        resultado = {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": dados_completos.get("status_dataHora", ""),
            "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
            "relator": relator_txt,
            "relator_id": relator_id,
            "sigla_tipo": sigla_tipo,
            "ementa": ementa,
        }
        
        # Se for RIC, extrair informações adicionais de prazo de resposta
        if sigla_tipo == "RIC":
            prazo_info = parse_prazo_resposta_ric(tramitacoes, situacao)
            resultado.update({
                "ric_data_remessa": prazo_info.get("data_remessa"),
                "ric_inicio_contagem": prazo_info.get("inicio_contagem"),
                "ric_prazo_inicio": prazo_info.get("prazo_inicio"),
                "ric_prazo_fim": prazo_info.get("prazo_fim"),
                "ric_prazo_str": prazo_info.get("prazo_str", ""),  # String formatada para exibição
                "ric_dias_restantes": prazo_info.get("dias_restantes"),
                "ric_fonte_prazo": prazo_info.get("fonte_prazo", ""),
                "ric_status_resposta": prazo_info.get("status_resposta"),
                "ric_data_resposta": prazo_info.get("data_resposta"),
                "ric_respondido": prazo_info.get("respondido", False),
                "ric_ministerio": extrair_ministerio_ric(ementa, tramitacoes),
                "ric_assunto": extrair_assunto_ric(ementa),
            })
        
        return pid, resultado

    max_workers = 10 if len(ids) >= 40 else 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for pid, payload in ex.map(_one, ids):
            out[str(pid)] = payload

    return out



