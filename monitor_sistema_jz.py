# monitor_sistema_jz.py
# ============================================================
# Monitor Legislativo – Dep. Júlia Zanatta (Streamlit)
# Versão estável (SEM relator) + abas + toggle + filtros por órgão/mês/ano
#
# Fixes (26/12):
# - Quebra de texto em TODAS as tabelas (sem precisar passar mouse)
# - Rastreador individual: incluir "Data do status" e ordenar desc (mais novo no topo)
# - Linha do Tempo (últimas 10 movimentações) funcionando com paginação/fallback
# - Detalhes do rastreador: remover link e mostrar Órgão + Situação
# - Alerta de "Relator adversário" (PT, PV, PSB, PCdoB, PSOL, REDE) na estratégia
# ============================================================

import datetime
import concurrent.futures
import time
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559

HEADERS = {"User-Agent": "MonitorZanatta/5.3 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]

STATUS_PREDEFINIDOS = [
    "Arquivada",
    "Aguardando Despacho do Presidente da Câmara dos Deputados",
    "Aguardando Designação de Relator(a)",
    "Aguardando Parecer de Relator(a)",
    "Tramitando em Conjunto",
    "Pronta para Pauta",
    "Aguardando Deliberação",
    "Aguardando Apreciação",
    "Aguardando Distribuição",
    "Aguardando Designação",
    "Aguardando Votação",
]

MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

PARTIDOS_RELATOR_ADVERSARIO = {"PT", "PV", "PSB", "PCDOB", "PSOL", "REDE"}

# ============================================================
# UTILITÁRIOS
# ============================================================

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


def format_sigla_num_ano(sigla, numero, ano) -> str:
    sigla = (sigla or "").strip()
    numero = (str(numero) or "").strip()
    ano = (str(ano) or "").strip()
    if sigla and numero and ano:
        return f"{sigla} {numero}/{ano}"
    return ""


def extract_id_from_uri(uri: str):
    if not uri:
        return None
    try:
        path = urlparse(uri).path.rstrip("/")
        return path.split("/")[-1]
    except Exception:
        return None


def is_comissao_estrategica(sigla_orgao, lista_siglas):
    if not sigla_orgao:
        return False
    return sigla_orgao.upper() in [s.upper() for s in lista_siglas]


def parse_dt(iso_str: str):
    return pd.to_datetime(iso_str, errors="coerce", utc=False)


def days_since(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return None
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    today = pd.Timestamp(datetime.date.today())
    return int((today - d.normalize()).days)


def fmt_dt_br(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return "—"
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    return d.strftime("%d/%m/%Y %H:%M")


def camara_link_tramitacao(id_proposicao: str) -> str:
    pid = str(id_proposicao).strip()
    return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"


def to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> tuple[bytes, str, str]:
    for engine in ["xlsxwriter", "openpyxl"]:
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine=engine) as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            return (
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            )
        except ModuleNotFoundError:
            continue
        except Exception:
            continue

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return (csv_bytes, "text/csv", "csv")


def canonical_situacao(situacao: str) -> str:
    """
    Normaliza rótulos de Situação atual para evitar duplicidades.
    Unifica TODAS as variações de "aguardando parecer" em:
      "Aguardando Parecer de Relator(a)"
    """
    s_raw = (situacao or "").strip()
    s = normalize_text(s_raw)

    if "parecer" in s:
        return "Aguardando Parecer de Relator(a)"

    return s_raw


def merge_status_options(dynamic_opts: list[str]) -> list[str]:
    base = [s for s in STATUS_PREDEFINIDOS if s and str(s).strip()]
    dyn = [s for s in dynamic_opts if s and str(s).strip()]
    merged = []
    seen = set()
    for s in base + sorted(dyn):
        if s not in seen:
            merged.append(s)
            seen.add(s)
    return merged


def party_norm(sigla: str) -> str:
    s = (sigla or "").strip().upper()
    if s in {"PC DO B", "PCDOB", "PCDOB ", "PCD0B"}:
        return "PCDOB"
    return s


# ============================================================
# HTTP ROBUSTO (retry/backoff)
# ============================================================

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)

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
# API: EVENTOS/PAUTA (MONITORAMENTO)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_eventos(start_date, end_date):
    eventos = []
    pagina = 1
    while True:
        params = {
            "dataInicio": start_date.strftime("%Y-%m-%d"),
            "dataFim": end_date.strftime("%Y-%m-%d"),
            "pagina": pagina,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "dataHoraInicio",
        }
        data = safe_get(f"{BASE_URL}/eventos", params=params)
        if data is None or "__error__" in data:
            break

        dados = data.get("dados", [])
        if not dados:
            break
        eventos.extend(dados)

        links = data.get("links", [])
        if not any(link.get("rel") == "next" for link in links):
            break
        pagina += 1
    return eventos


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pauta_evento(event_id):
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    if data is None or "__error__" in data:
        return []
    return data.get("dados", [])


def get_proposicao_id_from_item(item):
    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_", "proposicao_relacionada"],
        ["proposicaoPrincipal", "proposicao_principal"],
        ["proposicao", "proposicao_"],
    ]

    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                if prop.get("id"):
                    return str(prop["id"])
                if prop.get("idProposicao"):
                    return str(prop["idProposicao"])

    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                uri = prop.get("uri") or prop.get("uriProposicao") or prop.get("uriProposicaoPrincipal")
                if uri:
                    return extract_id_from_uri(uri)

    for chave_uri in ["uriProposicaoPrincipal", "uriProposicao", "uri"]:
        if item.get(chave_uri):
            return extract_id_from_uri(item[chave_uri])

    return None


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


def pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf):
    relator = item.get("relator") or {}
    nome = relator.get("nome") or ""
    partido = relator.get("siglaPartido") or ""
    uf = relator.get("siglaUf") or ""

    if normalize_text(alvo_nome) not in normalize_text(nome):
        return False
    if alvo_partido and partido and normalize_text(alvo_partido) != normalize_text(partido):
        return False
    if alvo_uf and uf and normalize_text(alvo_uf) != normalize_text(uf):
        return False
    return True


def pauta_item_palavras_chave(item, palavras_chave_normalizadas):
    textos = []
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        v = item.get(chave)
        if v:
            textos.append(str(v))

    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop.get(chave)
        if v:
            textos.append(str(v))

    texto_norm = normalize_text(" ".join(textos))
    encontradas = set()
    for kw_norm, kw_original in palavras_chave_normalizadas:
        if kw_norm and kw_norm in texto_norm:
            encontradas.add(kw_original)
    return encontradas


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ids_autoria_deputada(id_deputada):
    ids = set()
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "ASC", "ordenarPor": "id"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            if d.get("id"):
                ids.add(str(d["id"]))

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        if not next_link:
            break

        url = next_link
        params = {}

    return ids


def escanear_eventos(
    eventos,
    alvo_nome,
    alvo_partido,
    alvo_uf,
    palavras_chave,
    comissoes_estrategicas,
    apenas_reuniao_deliberativa=False,
    buscar_autoria=True,
    ids_autoria_deputada=None,
):
    registros = []
    palavras_chave_norm = [(normalize_text(p), p) for p in palavras_chave if p.strip()]
    ids_autoria_deputada = ids_autoria_deputada or set()

    for ev in eventos:
        desc_tipo = (ev.get("descricaoTipo") or "").lower()
        if apenas_reuniao_deliberativa and "reunião deliberativa" not in desc_tipo:
            continue

        event_id = ev.get("id") or ev.get("codEvento")
        if event_id is None:
            continue

        data_hora_ini = ev.get("dataHoraInicio") or ""
        data_str = data_hora_ini[:10] if len(data_hora_ini) >= 10 else ""
        hora_str = data_hora_ini[11:16] if len(data_hora_ini) >= 16 else ""

        descricao_evento = ev.get("descricao") or ""
        tipo_evento = ev.get("descricaoTipo") or ""

        orgaos = ev.get("orgaos") or []
        if not orgaos:
            orgaos = [{"sigla": "", "nome": "", "id": None}]

        pauta = fetch_pauta_evento(event_id)

        proposicoes_relatoria = set()
        proposicoes_autoria = set()
        palavras_evento = set()

        for item in pauta:
            kws_item = pauta_item_palavras_chave(item, palavras_chave_norm)
            has_keywords = bool(kws_item)
            relatoria_flag = pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf)

            autoria_flag = False
            id_prop_tmp = None
            if buscar_autoria and ids_autoria_deputada:
                id_prop_tmp = get_proposicao_id_from_item(item)
                if id_prop_tmp and id_prop_tmp in ids_autoria_deputada:
                    autoria_flag = True

            if not (relatoria_flag or autoria_flag or has_keywords):
                continue

            id_prop = id_prop_tmp or get_proposicao_id_from_item(item)
            identificacao = "(proposição não identificada)"
            ementa_prop = ""

            if id_prop:
                info = fetch_proposicao_info(id_prop)
                identificacao = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or identificacao
                ementa_prop = info["ementa"]

            texto_completo = f"{identificacao} – {ementa_prop}" if ementa_prop else identificacao

            if relatoria_flag:
                proposicoes_relatoria.add(texto_completo)
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
            if has_keywords:
                for kw in kws_item:
                    palavras_evento.add(kw)

        if not (proposicoes_relatoria or proposicoes_autoria or palavras_evento):
            continue

        for org in orgaos:
            sigla_org = org.get("siglaOrgao") or org.get("sigla") or ""
            nome_org = org.get("nomeOrgao") or org.get("nome") or ""
            orgao_id = org.get("id")

            registros.append(
                {
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
                    "tem_autoria_deputada": bool(proposicoes_autoria),
                    "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)),
                    "tem_palavras_chave": bool(palavras_evento),
                    "palavras_chave_encontradas": "; ".join(sorted(palavras_evento)),
                    "comissao_estrategica": is_comissao_estrategica(sigla_org, comissoes_estrategicas),
                }
            )

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values(["data", "hora", "orgao_sigla", "id_evento"])
    return df


# ============================================================
# API: RASTREADOR (INDEPENDENTE) + RIC Fallback
# ============================================================

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

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Proposicao"] = df.apply(lambda r: format_sigla_num_ano(r["siglaTipo"], r["numero"], r["ano"]), axis=1)
    return df


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
# STATUS / TRAMITAÇÕES
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)
def fetch_status_proposicao(id_proposicao):
    data = safe_get(f"{BASE_URL}/proposicoes/{id_proposicao}")
    if data is None or "__error__" in data:
        return {
            "id": str(id_proposicao),
            "sigla": "",
            "numero": "",
            "ano": "",
            "ementa": "",
            "urlInteiroTeor": "",
            "status_dataHora": "",
            "status_siglaOrgao": "",
            "status_uriOrgao": "",
            "status_descricaoTramitacao": "",
            "status_descricaoSituacao": "",
            "status_despacho": "",
        }

    d = data.get("dados", {}) or {}
    status = d.get("statusProposicao", {}) or {}

    return {
        "id": str(d.get("id") or id_proposicao),
        "sigla": (d.get("siglaTipo") or "").strip(),
        "numero": str(d.get("numero") or "").strip(),
        "ano": str(d.get("ano") or "").strip(),
        "ementa": (d.get("ementa") or "").strip(),
        "urlInteiroTeor": d.get("urlInteiroTeor") or "",
        "status_dataHora": status.get("dataHora") or "",
        "status_siglaOrgao": status.get("siglaOrgao") or "",
        "status_uriOrgao": status.get("uriOrgao") or "",
        "status_descricaoTramitacao": status.get("descricaoTramitacao") or "",
        "status_descricaoSituacao": canonical_situacao(status.get("descricaoSituacao") or ""),
        "status_despacho": status.get("despacho") or "",
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_tramitacoes_proposicao_paginado(id_proposicao):
    """
    Paginação robusta do endpoint /tramitacoes.
    Retorna dataframe com:
      - dataHora (str)
      - dataHora_dt (datetime)
      - Data (dd/mm/aaaa)
      - Hora (hh:mm)
      - siglaOrgao
      - uriOrgao
      - descricaoTramitacao
      - despacho
    """
    rows = []
    url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
    params = {"itens": 100, "ordem": "ASC", "ordenarPor": "dataHora"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        dados = data.get("dados", []) or []
        for t in dados:
            rows.append({
                "dataHora": t.get("dataHora") or "",
                "siglaOrgao": t.get("siglaOrgao") or "",
                "uriOrgao": t.get("uriOrgao") or "",
                "descricaoTramitacao": t.get("descricaoTramitacao") or "",
                "despacho": t.get("despacho") or "",
            })

        next_link = None
        for link in (data.get("links", []) or []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break

        if not next_link:
            break

        url = next_link
        params = {}

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["dataHora_dt"] = pd.to_datetime(df["dataHora"], errors="coerce")
    df["Data"] = df["dataHora_dt"].dt.strftime("%d/%m/%Y")
    df["Hora"] = df["dataHora_dt"].dt.strftime("%H:%M")

    df = df.sort_values("dataHora_dt", ascending=True)

    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=1800)
def get_tramitacoes_ultimas10(id_prop):
    """
    Linha do Tempo (últimas 10 movimentações).
    Busca TODAS as tramitações e retorna as 10 mais recentes.
    """
    rows = []
    url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
    params = {"itens": 100, "ordem": "DESC", "ordenarPor": "dataHora"}
    
    max_paginas = 5
    pagina_atual = 0
    
    while pagina_atual < max_paginas:
        data = safe_get(url, params=params)
        
        if not data or "__error__" in data:
            break
        
        dados = data.get("dados", [])
        if not dados:
            break
        
        # Adiciona todos os registros desta página
        for t in dados:
            rows.append({
                "dataHora": t.get("dataHora") or "",
                "siglaOrgao": t.get("siglaOrgao") or "—",
                "descricaoTramitacao": t.get("descricaoTramitacao") or "—",
            })
        
        # Verifica próxima página
        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        
        if not next_link:
            break
        
        url = next_link
        params = {}
        pagina_atual += 1
    
    # Processa os dados coletados
    if rows:
        df = pd.DataFrame(rows)
        df['dataHora_dt'] = pd.to_datetime(df['dataHora'], errors='coerce')
        df = df.dropna(subset=['dataHora_dt'])  # Remove linhas sem data válida
        
        if not df.empty:
            df['Data'] = df['dataHora_dt'].dt.strftime('%d/%m/%Y')
            df['Hora'] = df['dataHora_dt'].dt.strftime('%H:%M')
            df = df.sort_values('dataHora_dt', ascending=False)
            
            view = pd.DataFrame({
                "Data": df["Data"],
                "Hora": df["Hora"],
                "Órgão": df["siglaOrgao"],
                "Tramitação": df["descricaoTramitacao"],
            })
            
            return view.head(10).reset_index(drop=True)
    
    # FALLBACK: usa statusProposicao
    status = fetch_status_proposicao(id_prop)
    if not status or not status.get("status_dataHora"):
        return pd.DataFrame()

    dt = parse_dt(status.get("status_dataHora"))
    return pd.DataFrame([{
        "Data": dt.strftime("%d/%m/%Y") if pd.notna(dt) else "—",
        "Hora": dt.strftime("%H:%M") if pd.notna(dt) else "—",
        "Órgão": status.get("status_siglaOrgao") or "—",
        "Tramitação": status.get("status_descricaoTramitacao") or "Situação atual",
    }])


def calc_ultima_mov(df_tram_ult10: pd.DataFrame, status_dataHora: str):
    """
    Usa as tramitações (se existirem) para achar última movimentação.
    Se não existirem, usa data do status.
    """
    last = None

    if df_tram_ult10 is not None and not df_tram_ult10.empty:
        try:
            first = df_tram_ult10.iloc[0]
            if str(first.get("Data", "")).strip() and str(first.get("Hora", "")).strip():
                dt_guess = pd.to_datetime(f"{first['Data']} {first['Hora']}", errors="coerce", dayfirst=True)
                if pd.notna(dt_guess):
                    last = dt_guess
        except Exception:
            last = None

    if (last is None or pd.isna(last)) and status_dataHora:
        last = parse_dt(status_dataHora)

    parado = days_since(last) if last is not None and not pd.isna(last) else None
    return last, parado


@st.cache_data(show_spinner=False, ttl=900)
def build_status_map(ids: list[str]) -> dict:
    """
    Busca status com paralelismo moderado (rápido e sem estourar rate limit).
    """
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    def _one(pid: str):
        s = fetch_status_proposicao(pid)
        situacao = canonical_situacao((s.get("status_descricaoSituacao") or "").strip())
        andamento = (s.get("status_descricaoTramitacao") or "").strip()
        return pid, {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": (s.get("status_dataHora") or "").strip(),
            "siglaOrgao": (s.get("status_siglaOrgao") or "").strip(),
        }

    max_workers = 10 if len(ids) >= 40 else 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for pid, payload in ex.map(_one, ids):
            out[str(pid)] = payload

    return out


def enrich_with_status(df_base: pd.DataFrame, status_map: dict) -> pd.DataFrame:
    df = df_base.copy()
    df["Situação atual"] = df["id"].astype(str).map(lambda x: canonical_situacao(status_map.get(str(x), {}).get("situacao", "")))
    df["Andamento (status)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("andamento", ""))
    df["Data do status (raw)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("status_dataHora", ""))
    df["Órgão (sigla)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("siglaOrgao", ""))

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["Data do status"] = dt.apply(fmt_dt_br)
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month
    df["Parado (dias)"] = df["DataStatus_dt"].apply(days_since)

    def _sinal(d):
        try:
            if d is None or pd.isna(d):
                return "—"
            d = int(d)
            if d >= 30:
                return "🔴"
            if d >= 15:
                return "🟠"
            if d >= 7:
                return "🟡"
            return "🟢"
        except Exception:
            return "—"

    df["Sinal"] = df["Parado (dias)"].apply(_sinal)
    return df


# ============================================================
# RELATOR (somente para ALERTA no detalhe)
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)
def fetch_relator_atual(id_proposicao: str) -> dict:
    """
    Busca relator com múltiplas estratégias robustas.
    Prioriza dados estruturados da API antes de regex.
    """
    import re
    
    pid = str(id_proposicao).strip()
    if not pid:
        return {}

    # ========================================
    # ESTRATÉGIA 1: Endpoint /autores (relator como autor especial)
    # ========================================
    autores_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/autores")
    if isinstance(autores_data, dict) and autores_data.get("dados"):
        for autor in autores_data.get("dados", []):
            tipo_autor = (autor.get("tipoAutor") or "").lower()
            if "relator" in tipo_autor:
                nome = autor.get("nome") or ""
                partido = party_norm(autor.get("siglaPartido") or "")
                uf = autor.get("siglaUF") or autor.get("uf") or ""
                if nome:
                    return {"nome": nome, "partido": partido, "uf": uf}

    # ========================================
    # ESTRATÉGIA 2: Endpoint /relatores
    # ========================================
    candidatos = []
    data = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatores")
    if isinstance(data, dict) and data.get("dados"):
        candidatos = data.get("dados") or []

    if not candidatos:
        data2 = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatoria")
        if isinstance(data2, dict) and data2.get("dados"):
            candidatos = data2.get("dados") or []

    if candidatos:
        def _pick_dt(x):
            for k in ("dataDesignacao", "dataHora", "data", "dataRelatoria"):
                if x.get(k):
                    dt = pd.to_datetime(x.get(k), errors="coerce")
                    if pd.notna(dt):
                        return dt
            return pd.NaT

        dfc = pd.DataFrame(candidatos)
        if not dfc.empty:
            if any(k in dfc.columns for k in ("dataDesignacao", "dataHora", "data", "dataRelatoria")):
                dfc["_dt"] = dfc.apply(lambda r: _pick_dt(r.to_dict()), axis=1)
                dfc = dfc.sort_values("_dt", ascending=False)

            r = (dfc.iloc[0].to_dict() if not dfc.empty else {}) or {}
            nome = r.get("nome") or r.get("nomeRelator") or ""
            partido = r.get("siglaPartido") or r.get("partido") or r.get("sigla") or ""
            uf = r.get("siglaUf") or r.get("uf") or ""

            dep = r.get("deputado") or r.get("parlamentar") or {}
            if isinstance(dep, dict):
                nome = nome or dep.get("nome") or dep.get("nomeCivil") or ""
                partido = partido or dep.get("siglaPartido") or dep.get("partido") or ""
                uf = uf or dep.get("siglaUf") or dep.get("uf") or ""

            partido = party_norm(partido)
            if nome:
                return {"nome": str(nome).strip(), "partido": str(partido).strip(), "uf": str(uf).strip()}

    # ========================================
    # ESTRATÉGIA 3: Despacho no statusProposicao
    # ========================================
    status_data = safe_get(f"{BASE_URL}/proposicoes/{pid}")
    if isinstance(status_data, dict) and status_data.get("dados"):
        status_prop = status_data.get("dados", {}).get("statusProposicao", {})
        despacho_status = status_prop.get("despacho") or ""
        
        if despacho_status:
            patterns = [
                r'Designad[oa]\s+Relator[a]?,\s*Dep\.\s*([^(]+?)\s*\(([A-Z]+)(?:-([A-Z]{2}))?\)',
                r'Relator[a]?\s*Designad[oa]:\s*Dep\.\s*([^(]+?)\s*\(([A-Z]+)(?:-([A-Z]{2}))?\)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, despacho_status, re.IGNORECASE)
                if match:
                    nome = match.group(1).strip()
                    partido = party_norm(match.group(2).strip())
                    uf = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ""
                    if nome:
                        return {"nome": nome, "partido": partido, "uf": uf}

    # ========================================
    # ESTRATÉGIA 4: Tramitações (despacho + descricaoTramitacao)
    # ========================================
    tram_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/tramitacoes", 
                         params={"itens": 150, "ordem": "DESC", "ordenarPor": "dataHora"})
    
    if isinstance(tram_data, dict) and tram_data.get("dados"):
        for t in tram_data.get("dados", []):
            despacho = t.get("despacho") or ""
            desc_tram = t.get("descricaoTramitacao") or ""
            
            # Procura em ambos
            texto_busca = f"{despacho} {desc_tram}"
            
            # Padrões mais específicos primeiro
            patterns = [
                # Padrão principal: Designado Relator, Dep. Nome (PARTIDO-UF)
                r'Designad[oa]\s+Relator[a]?,\s*Dep\.\s*([^(]+?)\s*\(([A-Z]+)(?:-([A-Z]{2}))?\)',
                # Relator: Dep. Nome (PARTIDO-UF)
                r'Relator[a]?:\s*Dep\.\s*([^(]+?)\s*\(([A-Z]+)(?:-([A-Z]{2}))?\)',
                # Dep. Nome (PARTIDO-UF) quando menciona relator
                r'Dep\.\s*([^(]+?)\s*\(([A-Z]+)(?:-([A-Z]{2}))?\)',
            ]
            
            for idx, pattern in enumerate(patterns):
                match = re.search(pattern, texto_busca, re.IGNORECASE)
                # Para o último padrão genérico, exige que tenha "relator" no texto
                if match:
                    if idx == 2 and "relator" not in texto_busca.lower():
                        continue
                    
                    nome = match.group(1).strip()
                    partido = party_norm(match.group(2).strip())
                    uf = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ""
                    
                    # Validação: nome não pode ser muito curto ou suspeito
                    if nome and len(nome) > 3:
                        return {"nome": nome, "partido": partido, "uf": uf}

    # ========================================
    # ESTRATÉGIA 5: Busca no órgão atual (comissão)
    # ========================================
    if isinstance(status_data, dict) and status_data.get("dados"):
        status_prop = status_data.get("dados", {}).get("statusProposicao", {})
        uri_orgao = status_prop.get("uriOrgao") or ""
        
        if uri_orgao:
            id_orgao = extract_id_from_uri(uri_orgao)
            if id_orgao:
                # Tenta buscar membros do órgão
                membros_data = safe_get(f"{BASE_URL}/orgaos/{id_orgao}/membros")
                if isinstance(membros_data, dict) and membros_data.get("dados"):
                    for membro in membros_data.get("dados", []):
                        titulo = (membro.get("titulo") or "").lower()
                        if "relator" in titulo:
                            nome = membro.get("nome") or ""
                            partido = party_norm(membro.get("siglaPartido") or "")
                            uf = membro.get("siglaUf") or ""
                            if nome:
                                return {"nome": nome, "partido": partido, "uf": uf}

    return {}


def relator_adversario_alert(relator_info: dict) -> str:
    if not relator_info:
        return ""
    p = party_norm(relator_info.get("partido") or "")
    if p and p in PARTIDOS_RELATOR_ADVERSARIO:
        return "⚠️ Relator adversário"
    return ""


# ============================================================
# ESTRATÉGIAS (REGRAS FIXAS)
# ============================================================

def estrategia_por_situacao(situacao: str) -> list[str]:
    s = normalize_text(canonical_situacao(situacao or ""))

    if "aguardando designacao de relator" in s or "aguardando designação de relator" in s:
        return ["Buscar entre os membros da Comissão, parlamentar parceiro."]

    if "aguardando parecer" in s:
        return [
            "Se o relator for parceiro/neutro: tentar acelerar a apresentação do parecer.",
            "Se o relator for adversário: articular um VTS com membros parceiros da Comissão.",
        ]

    if "pronta para pauta" in s:
        return [
            "Se o parecer for favorável: articular na Comissão para o parecer entrar na pauta.",
            "Se o parecer for contrário: articular pra não entrar na pauta.",
            "Caso entre na pauta: articular retirada de pauta; se não funcionar, articular obstrução e VTS.",
        ]

    if "aguardando despacho" in s and "presidente" in s and "camara" in s:
        return ["Articular com a Mesa para acelerar a tramitação."]

    return ["—"]


def montar_estrategia_tabela(situacao: str, relator_alerta: str = "") -> pd.DataFrame:
    rows = []
    if relator_alerta:
        rows.append({"Estratégia sugerida": relator_alerta})
    for it in estrategia_por_situacao(situacao):
        rows.append({"Estratégia sugerida": it})
    if not rows:
        rows = [{"Estratégia sugerida": "—"}]
    return pd.DataFrame(rows)


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor – Dep. Júlia Zanatta", layout="wide")

    st.markdown(
        """
        <style>
        /* Geral: quebra em qualquer grid */
        div[data-testid="stDataFrame"] * {
            white-space: normal !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
        }
        div[data-testid="stDataFrame"] [role="gridcell"],
        div[data-testid="stDataFrame"] [role="columnheader"] {
            white-space: normal !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
            line-height: 1.25em !important;
        }

        .map-small div[data-testid="stDataFrame"] * { font-size: 11px !important; }

        a { word-break: break-word; overflow-wrap: anywhere; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")

    if "status_click_sel" not in st.session_state:
        st.session_state["status_click_sel"] = None

    with st.sidebar:
        st.header("⚙️ Configurações")

        hoje = datetime.date.today()
        default_inicio = hoje
        default_fim = hoje + datetime.timedelta(days=7)

        st.subheader("Monitoramento de pauta (eventos)")
        date_range = st.date_input("Intervalo de datas", value=(default_inicio, default_fim), format="DD/MM/YYYY")
        if isinstance(date_range, tuple):
            dt_inicio, dt_fim = date_range
        else:
            dt_inicio = date_range
            dt_fim = date_range

        st.subheader("Deputada monitorada")
        alvo_nome = st.text_input("Nome", value=DEPUTADA_NOME_PADRAO)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            alvo_partido = st.text_input("Partido", value=DEPUTADA_PARTIDO_PADRAO)
        with c2:
            alvo_uf = st.text_input("UF", value=DEPUTADA_UF_PADRAO)
        with c3:
            id_dep_str = st.text_input("ID (Dados Abertos)", value=str(DEPUTADA_ID_PADRAO))

        try:
            id_deputada = int(id_dep_str)
        except ValueError:
            st.error("ID da deputada inválido. Use apenas números.")
            return

        st.subheader("Palavras-chave (pauta)")
        palavras_str = st.text_area("Uma por linha", value="\n".join(PALAVRAS_CHAVE_PADRAO), height=140)
        palavras_lista = [p.strip() for p in palavras_str.splitlines() if p.strip()]

        st.subheader("Comissões estratégicas")
        comissoes_str = st.text_area("Siglas (uma por linha)", value="\n".join(COMISSOES_ESTRATEGICAS_PADRAO), height=110)
        comissoes_lista = [c.strip().upper() for c in comissoes_str.splitlines() if c.strip()]

        apenas_delib = st.checkbox("Considerar apenas Reuniões Deliberativas", value=False)
        buscar_autoria = st.checkbox("Verificar AUTORIA da deputada", value=True)

        st.markdown("---")
        bt_rodar_monitor = st.button("🔍 Rodar monitoramento (pauta)", type="primary")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["1️⃣ Autoria/Relatoria na pauta", "2️⃣ Palavras-chave na pauta", "3️⃣ Comissões estratégicas", "4️⃣ Tramitação (independente) + RIC + Carteira por Status"]
    )

    df = pd.DataFrame()
    if bt_rodar_monitor:
        if dt_inicio > dt_fim:
            st.error("Data inicial não pode ser maior que a data final.")
            return

        with st.spinner("Consultando eventos/pauta e analisando..."):
            eventos = fetch_eventos(dt_inicio, dt_fim)
            ids_autoria = fetch_ids_autoria_deputada(id_deputada) if buscar_autoria else set()

            df = escanear_eventos(
                eventos=eventos,
                alvo_nome=alvo_nome,
                alvo_partido=alvo_partido,
                alvo_uf=alvo_uf,
                palavras_chave=palavras_lista,
                comissoes_estrategicas=comissoes_lista,
                apenas_reuniao_deliberativa=apenas_delib,
                buscar_autoria=buscar_autoria,
                ids_autoria_deputada=ids_autoria,
            )

    with tab1:
        st.subheader("Autoria/Relatoria na pauta")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_jz = df[(df["tem_autoria_deputada"]) | (df["tem_relatoria_deputada"])].copy()
            if df_jz.empty:
                st.info("Sem itens de autoria/relatoria no período.")
            else:
                view = df_jz[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "proposicoes_autoria", "proposicoes_relatoria", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(
                    view,
                    use_container_width=True,
                    hide_index=True,
                )

                data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria_Pauta")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )

    with tab2:
        st.subheader("Palavras-chave na pauta")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_kw = df[df["tem_palavras_chave"]].copy()
            if df_kw.empty:
                st.info("Sem palavras-chave no período.")
            else:
                view = df_kw[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "palavras_chave_encontradas", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                data_bytes, mime, ext = to_xlsx_bytes(view, "PalavrasChave_Pauta")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )

    with tab3:
        st.subheader("Comissões estratégicas")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_com = df[df["comissao_estrategica"]].copy()
            if df_com.empty:
                st.info("Sem eventos em comissões estratégicas no período.")
            else:
                view = df_com[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "proposicoes_autoria", "proposicoes_relatoria", "palavras_chave_encontradas", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                data_bytes, mime, ext = to_xlsx_bytes(view, "ComissoesEstrategicas_Pauta")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )

    with tab4:
        st.subheader("Tramitação (independente) – inclui PL/PEC/PDL/PLP e RIC")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh = st.button("🧹 Limpar cache (autoria/status/tramitação/relator)")
        with colB:
            st.caption("Coluna **Link** abre a **Ficha de Tramitação** (site da Câmara).")

        if bt_refresh:
            fetch_lista_proposicoes_autoria_geral.clear()
            fetch_rics_por_autor.clear()
            fetch_lista_proposicoes_autoria.clear()
            fetch_status_proposicao.clear()
            fetch_tramitacoes_proposicao_paginado.clear()
            get_tramitacoes_ultimas10.clear()
            build_status_map.clear()
            fetch_relator_atual.clear()
            st.session_state.pop("df_status_last", None)
            st.session_state["status_click_sel"] = None
            st.session_state.pop("df_rast_status", None)

        with st.spinner("Carregando proposições de autoria (com RIC incluído)..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        col2, col3 = st.columns([1.1, 1.1])
        with col2:
            anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
            anos_sel = st.multiselect("Ano (da proposição)", options=anos, default=anos[:3] if len(anos) >= 3 else anos)
        with col3:
            tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
            tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos)

        df_base = df_aut.copy()
        if anos_sel:
            df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
        if tipos_sel:
            df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()

        st.markdown("---")
        st.markdown("📌 Matérias de autoria filtradas por situação atual")

        cS1, cS2, cS3, cS4 = st.columns([1.2, 1.2, 1.6, 1.0])
       
        with cS2:
            max_status = st.number_input(
                "Limite (performance)",
                min_value=20,
                max_value=600,
                value=min(200, len(df_base)) if len(df_base) else 20,
                step=20
            )
        with cS3:
            st.caption("Aplique filtros acima (Ano/Tipo) e depois carregue o status.")
        with cS4:
            if st.button("✖ Limpar filtro por clique"):
                st.session_state["status_click_sel"] = None

        df_status_view = st.session_state.get("df_status_last", pd.DataFrame()).copy()

        dynamic_status = []
        if not df_status_view.empty and "Situação atual" in df_status_view.columns:
            dynamic_status = [s for s in df_status_view["Situação atual"].dropna().unique().tolist() if str(s).strip()]
        status_opts = merge_status_options(dynamic_status)

        f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])

        default_status_sel = []
        if st.session_state.get("status_click_sel"):
            default_status_sel = [st.session_state["status_click_sel"]]

        org_opts = []
        ano_status_opts = []
        mes_status_opts = []

        if not df_status_view.empty:
            org_opts = sorted(
                [o for o in df_status_view["Órgão (sigla)"].dropna().unique().tolist() if str(o).strip()]
            )

            ano_status_opts = sorted(
                [int(a) for a in df_status_view["AnoStatus"].dropna().unique().tolist() if pd.notna(a)],
                reverse=True
            )

            mes_status_opts = sorted(
                [int(m) for m in df_status_view["MesStatus"].dropna().unique().tolist() if pd.notna(m)]
            )

        with f1:
            status_sel = st.multiselect("Situação Atual", options=status_opts, default=default_status_sel)

        with f2:
            org_sel = st.multiselect("Órgão (sigla)", options=org_opts, default=[])

        with f3:
            ano_status_sel = st.multiselect("Ano (do status)", options=ano_status_opts, default=[])

        with f4:
            mes_labels = [f"{m:02d}-{MESES_PT.get(m, '')}" for m in mes_status_opts]
            mes_map = {f"{m:02d}-{MESES_PT.get(m, '')}": m for m in mes_status_opts}
            mes_sel_labels = st.multiselect("Mês (do status)", options=mes_labels, default=[])
            mes_status_sel = [mes_map[x] for x in mes_sel_labels if x in mes_map]

        bt_status = st.button("Carregar/Atualizar status", type="primary")

        if bt_status:
            with st.spinner("Buscando status..."):
                ids_list = df_base["id"].astype(str).head(int(max_status)).tolist()
                status_map = build_status_map(ids_list)
                df_status_view = enrich_with_status(df_base.head(int(max_status)), status_map)
                st.session_state["df_status_last"] = df_status_view

        if df_status_view.empty:
            st.info(
                "Clique em **Carregar/Atualizar status** para preencher "
                "Situação/Órgão/Data e habilitar filtros por mês/ano."
            )
        else:
            df_fil = df_status_view.copy()

            if status_sel:
                df_fil = df_fil[df_fil["Situação atual"].isin(status_sel)].copy()

            if org_sel:
                df_fil = df_fil[df_fil["Órgão (sigla)"].isin(org_sel)].copy()

            if ano_status_sel:
                df_fil = df_fil[df_fil["AnoStatus"].isin(ano_status_sel)].copy()

            if mes_status_sel:
                df_fil = df_fil[df_fil["MesStatus"].isin(mes_status_sel)].copy()

            st.markdown("---")

            df_tbl_status = df_fil.copy()
            df_tbl_status["Parado há"] = df_tbl_status["Parado (dias)"].apply(
                lambda x: f"{int(x)} dias" if isinstance(x, (int, float)) and pd.notna(x) else "—"
            )
            df_tbl_status["LinkTramitacao"] = df_tbl_status["id"].astype(str).apply(camara_link_tramitacao)

            df_tbl_status = df_tbl_status.rename(columns={
                "Proposicao": "Proposição",
                "siglaTipo": "Tipo",
                "ano": "Ano",
                "ementa": "Ementa",
            })

            show_cols = [
                "Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)",
                "Data do status", "Sinal", "Parado há", "id", "LinkTramitacao", "Ementa"
            ]
            for c in show_cols:
                if c not in df_tbl_status.columns:
                    df_tbl_status[c] = ""

            df_counts = (
                df_fil.assign(
                    _s=df_fil["Situação atual"].fillna("-").replace("", "-")
                )
                .groupby("_s", as_index=False)
                .size()
                .rename(columns={"_s": "Situação atual", "size": "Qtde"})
                .sort_values("Qtde", ascending=False)
            )

            cC1, cC2 = st.columns([1.0, 2.0])

            with cC1:
                st.markdown(
                    "**Contagem por Situação atual "
                    "(clique = filtra / clique de novo = desmarca)**"
                )
                st.dataframe(df_counts, hide_index=True, use_container_width=True)

            with cC2:
                st.markdown("**Lista filtrada (Link = Ficha de Tramitação)**")
                
                st.markdown('<div class="map-small">', unsafe_allow_html=True)
                st.dataframe(
                    df_tbl_status[show_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                    },
                )
                st.markdown("</div>", unsafe_allow_html=True)

            bytes_out, mime, ext = to_xlsx_bytes(df_tbl_status[show_cols], "Carteira_Status")
            st.download_button(
                f"⬇️ Baixar lista ({ext.upper()})",
                data=bytes_out,
                file_name=f"carteira_situacao_atual_filtrada.{ext}",
                mime=mime,
            )

        st.markdown("---")
        st.markdown("## 🔎 Rastreador individual (clique em uma linha da tabela abaixo)")

        q = st.text_input(
            "Buscar no rastreador (sigla/número/ano OU ementa)",
            value="",
            placeholder="Ex.: PL 2030/2025 | 'pix' | 'conanda'"
        )

        df_rast = df_base.copy()
        if q.strip():
            qn = normalize_text(q)
            df_rast["_search"] = (df_rast["Proposicao"].fillna("").astype(str) + " " + df_rast["ementa"].fillna("").astype(str)).apply(normalize_text)
            df_rast = df_rast[df_rast["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")

        df_rast_lim = df_rast.head(400).copy()
        with st.spinner("Carregando datas de status do rastreador (para ordenar)..."):
            ids_r = df_rast_lim["id"].astype(str).tolist()
            status_map_r = build_status_map(ids_r)
            df_rast_enriched = enrich_with_status(df_rast_lim, status_map_r)

        df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)

        st.caption(f"Resultados no rastreador (limitado a 400 para performance): {len(df_rast_enriched)} proposições")

        df_tbl = df_rast_enriched.rename(
            columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
        ).copy()
        
        df_tbl["Último andamento"] = df_rast_enriched["Andamento (status)"]
        df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)

        show_cols_r = [
            "Proposição",
            "Ementa",
            "ID",
            "Ano",
            "Tipo",
            "Órgão (sigla)",
            "Situação atual",
            "Último andamento",
            "Data do status",
            "LinkTramitacao",
        ]

        for c in show_cols_r:
            if c not in df_tbl.columns:
                df_tbl[c] = ""

        sel = st.dataframe(
            df_tbl[show_cols_r],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            }
        )

        selected_id = None
        try:
            if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                row_idx = sel["selection"]["rows"][0]
                selected_id = str(df_tbl.iloc[row_idx]["ID"])
        except Exception:
            selected_id = None

        st.markdown("---")
        st.markdown("### 📋 Detalhes (clique em uma linha acima)")

        if not selected_id:
            st.info("Clique em uma proposição para carregar status, estratégia e linha do tempo.")
        else:
            with st.spinner("Carregando status + relator + linha do tempo..."):
                status = fetch_status_proposicao(selected_id)
                situacao = status.get("status_descricaoSituacao") or "—"
                
                # Busca relator SEMPRE que estiver em situações específicas
                situacao_norm = normalize_text(situacao)
                precisa_relator = (
                    "pronta para pauta" in situacao_norm or 
                    "pronto para pauta" in situacao_norm or
                    "aguardando parecer" in situacao_norm
                )
                
                relator = {}
                alerta_relator = ""
                
                if precisa_relator:
                    relator = fetch_relator_atual(selected_id)
                    alerta_relator = relator_adversario_alert(relator)
                
                df_tram10 = get_tramitacoes_ultimas10(selected_id)

                status_dt = parse_dt(status.get("status_dataHora") or "")
                ultima_dt, parado_dias = calc_ultima_mov(df_tram10, status.get("status_dataHora") or "")

            proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
            org_sigla = status.get("status_siglaOrgao") or "—"
            andamento = status.get("status_descricaoTramitacao") or "—"
            despacho = status.get("status_despacho") or ""
            ementa = status.get("ementa") or ""

            st.markdown("#### 🧾 Contexto")
            st.markdown(f"**Proposição:** {proposicao_fmt or '—'}")
            st.markdown(f"**Órgão:** {org_sigla}")
            st.markdown(f"**Situação atual:** {situacao}")
            
            # Mostra relator se encontrado (especialmente para as situações críticas)
            if relator and (relator.get("nome") or relator.get("partido") or relator.get("uf")):
                rel_txt = f"{relator.get('nome','—')}"
                if relator.get("partido") or relator.get("uf"):
                    rel_txt += f" ({relator.get('partido','')}/{relator.get('uf','')})".replace("//", "/")
                st.markdown(f"**Relator(a):** {rel_txt}")
                
                if alerta_relator:
                    st.warning(alerta_relator)
            elif precisa_relator:
                st.markdown("**Relator(a):** Não identificado")
            
            c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
            c1.metric("Data do Status", fmt_dt_br(status_dt))
            c2.metric("Última mov.", fmt_dt_br(ultima_dt))
            c3.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")

            st.markdown("**Ementa**")
            st.write(ementa)

            st.markdown("**Último andamento**")
            st.write(andamento)

            if despacho:
                st.markdown("**Despacho (chave para onde foi)**")
                st.write(despacho)

            if status.get("urlInteiroTeor"):
                st.markdown("**Inteiro teor**")
                st.write(status["urlInteiroTeor"])

            st.markdown(f"[Tramitação]({camara_link_tramitacao(selected_id)})")

            st.markdown("---")
            st.markdown("### 🧠 Estratégia")
            
            df_estr = montar_estrategia_tabela(
                situacao,
                relator_alerta=alerta_relator
            )

            st.dataframe(df_estr, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🕒 Linha do Tempo (últimas 10 movimentações)")

            if df_tram10.empty:
                st.info("Sem tramitações retornadas (ou endpoint instável no momento).")
            else:
                st.dataframe(df_tram10, use_container_width=True, hide_index=True)

                bytes_out, mime, ext = to_xlsx_bytes(df_tram10, "LinhaDoTempo_10")
                st.download_button(
                    f"⬇️ Baixar linha do tempo ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"linha_do_tempo_10_{selected_id}.{ext}",
                    mime=mime,
                )

    st.markdown("---")


if __name__ == "__main__":
    main()