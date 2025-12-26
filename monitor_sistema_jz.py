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
DEPUTADA_ID_PADRAO = 220559  # ajuste se necessário

HEADERS = {"User-Agent": "MonitorZanatta/4.2 (gabinete-julia-zanatta)"}

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
    "Aguardando Parecer",
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


def needs_relator_info(situacao: str, andamento: str) -> bool:
    # Relator removido do sistema (performance e consistência)
    return False


def normalize_situacao(situacao: str) -> str:
    """Normaliza rótulos de Situação atual para evitar duplicidades e facilitar filtros."""
    s_raw = (situacao or "").strip()
    s = normalize_text(s_raw)

    # Unificar TODAS as variações de "aguardando parecer" (inclusive sem a palavra 'aguardando')
    # Ex.: "Aguardando Parecer", "Aguardando o Parecer", "Aguardando Parecer do Relator",
    #      "Aguardando Parecer de Relator(a)", "Parecer do Relator" etc.
    if "parecer" in s:
        if ("aguard" in s) or ("relator" in s) or s.startswith("parecer"):
            return "Aguardando Parecer de Relator(a)"

    # Outras normalizações leves (expanda conforme necessidade)
    return s_raw


# ============================================================
# HTTP ROBUSTO (retry/backoff)
# ============================================================

# Reuse HTTP connections (faster / fewer handshakes on Streamlit Cloud)
_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)


def normalize_situacao(s: str) -> str:
    # compat: alias para evitar NameError em versões anteriores
    return normalize_situacao(s)

def _request_json(url: str, params=None, timeout=30, max_retries=3):
    params = params or {}
    backoffs = [0.5, 1.0, 2.0, 4.0]
    last_err = None

    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)

            if resp.status_code == 404:
                return None

            # Rate limit / instabilidade (retry)
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
# RESOLVER DEPUTADO (RELATOR) VIA DADOS ABERTOS
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_deputado_info_by_id(dep_id: str) -> dict:
    """Retorna dados básicos do deputado para exibição (nome/partido/UF)."""
    if not dep_id:
        return {"nome": "", "siglaPartido": "", "siglaUf": ""}
    data = safe_get(f"{BASE_URL}/deputados/{dep_id}")
    if data is None or "__error__" in data:
        return {"nome": "", "siglaPartido": "", "siglaUf": ""}
    d = data.get("dados", {}) or {}
    return {
        "nome": (d.get("nome") or "").strip(),
        "siglaPartido": (d.get("siglaPartido") or "").strip(),
        "siglaUf": (d.get("siglaUf") or "").strip(),
    }


def resolve_relator_info(uri_ultimo_relator: str) -> tuple[str, str, str, str]:
    """Retorna (relator_id, relator_nome, relator_partido, relator_uf)."""
    rid = extract_id_from_uri(uri_ultimo_relator or "")
    if not rid:
        return "", "", "", ""
    info = fetch_deputado_info_by_id(rid)
    return rid, info.get("nome", ""), info.get("siglaPartido", ""), info.get("siglaUf", "")



@st.cache_data(show_spinner=False, ttl=3600)
def fetch_relator_atual_from_relatores(id_proposicao: str) -> tuple[str, str, str, str]:
    """Fallback: tenta descobrir relator(a) via endpoint /relatores quando statusProposicao não traz uriUltimoRelator.
    Retorna (relator_id, nome, partido, uf) ou ("","","","").
    """
    try:
        pid = str(id_proposicao).strip()
        if not pid:
            return "", "", "", ""
        data = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatores", params={"itens": 100, "ordem": "DESC"})
        if data is None or "__error__" in data:
            return "", "", "", ""
        items = data.get("dados", []) or []
        if not items:
            return "", "", "", ""

        # pega o mais recente que tenha algum vínculo de deputado
        for it in items:
            uri_dep = it.get("uriDeputado") or it.get("uriParlamentar") or it.get("uriDeputadoRelator") or ""
            rid = extract_id_from_uri(uri_dep)
            if rid:
                info = fetch_deputado_info_by_id(rid)
                nome = (info.get("nome") or "").strip()
                part = (info.get("siglaPartido") or "").strip()
                uf = (info.get("siglaUf") or "").strip()
                return rid, nome, part, uf

            # fallback: alguns retornos já trazem nome/partido/uf no item
            nome = (it.get("nome") or it.get("nomeDeputado") or "").strip()
            part = (it.get("siglaPartido") or it.get("partido") or "").strip()
            uf = (it.get("siglaUf") or it.get("uf") or "").strip()
            if nome:
                return "", nome, part, uf

        return "", "", "", ""
    except Exception:
        return "", "", "", ""



# ============================================================
# API: EVENTOS/PAUTA (MONITORAMENTO)
# ============================================================

@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
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

            texto_completo = f"{identificacao} — {ementa_prop}" if ementa_prop else identificacao

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


@st.cache_data(show_spinner=False, ttl=3600)
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
            "status_uriUltimoRelator": "",
            "status_ultimoRelator_id": "",
            "status_ultimoRelator_nome": "",
            "status_ultimoRelator_partido": "",
            "status_ultimoRelator_uf": "",
        }

    d = data.get("dados", {}) or {}
    status = d.get("statusProposicao", {}) or {}

    # Relator: só buscar quando fizer sentido (evita ficar lento)
    situacao_txt = (status.get("descricaoSituacao") or "").strip()
    andamento_txt = (status.get("descricaoTramitacao") or "").strip()

    relator_id = ""
    relator_nome = ""
    relator_partido = ""
    relator_uf = ""
    uri_ultimo_relator = status.get("uriUltimoRelator") or ""

    if needs_relator_info(situacao_txt, andamento_txt):
        relator_id, relator_nome, relator_partido, relator_uf = resolve_relator_info(uri_ultimo_relator)

        # Fallback: há casos em que o status não preenche uriUltimoRelator, mas já existe relatoria em /relatores
        if not relator_nome:
            rid2, nome2, part2, uf2 = fetch_relator_atual_from_relatores(str(id_proposicao))
            if nome2:
                relator_id, relator_nome, relator_partido, relator_uf = rid2, nome2, part2, uf2

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
        "status_descricaoSituacao": normalize_situacao(status.get("descricaoSituacao") or ""),
        "status_despacho": status.get("despacho") or "",
        "status_uriUltimoRelator": uri_ultimo_relator,
        "status_ultimoRelator_id": relator_id,
        "status_ultimoRelator_nome": relator_nome,
        "status_ultimoRelator_partido": relator_partido,
        "status_ultimoRelator_uf": relator_uf,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_tramitacoes_proposicao(id_proposicao):
    rows = []
    url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
    params = {"itens": 100, "ordem": "ASC", "ordenarPor": "dataHora"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for t in data.get("dados", []):
            rows.append(
                {
                    "dataHora": t.get("dataHora") or "",
                    "siglaOrgao": t.get("siglaOrgao") or "",
                    "uriOrgao": t.get("uriOrgao") or "",
                    "descricaoTramitacao": t.get("descricaoTramitacao") or "",
                    "despacho": t.get("despacho") or "",
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
        dt = pd.to_datetime(df["dataHora"], errors="coerce")
        df["DataHora_dt"] = dt
        df["Data"] = dt.dt.strftime("%d/%m/%Y")
        df["Hora"] = dt.dt.strftime("%H:%M")
        df = df[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho", "dataHora", "DataHora_dt"]]
    return df


def calc_ultima_mov(df_tram: pd.DataFrame, status_dataHora: str):
    last = None

    if df_tram is not None and not df_tram.empty:
        dt = df_tram.get("DataHora_dt")
        if dt is None:
            dt = pd.to_datetime(df_tram["dataHora"], errors="coerce")
        dt = dt.dropna()
        if not dt.empty:
            last = dt.max()

    if (last is None or pd.isna(last)) and status_dataHora:
        last = parse_dt(status_dataHora)

    parado = days_since(last) if last is not None and not pd.isna(last) else None
    return last, parado


def montar_estrategia_tabela(org_sigla: str, situacao: str, andamento: str, despacho: str, parado_dias, relator_nome: str, relator_partido: str = "", relator_uf: str = ""):
    combo = normalize_text(f"{situacao} {andamento} {despacho}")

    fase = "Indefinida"
    acao = "Conferir despacho e última tramitação."
    sinal = []
    alerta = ""

    if "aguard" in combo and "relator" in combo:
        sinal.append("Aguarda relator")
        if relator_nome:
            sinal.append(f"Relator: {relator_nome}")
            acao = "Acionar relator e mapear parecer (prazo/agenda)."

    if "parecer" in combo and "aguard" in combo:
        sinal.append("Aguarda parecer")
        if relator_nome:
            sinal.append(f"Relator: {relator_nome}")
            acao = "Cobrar parecer com o gabinete do relator (com minuta/argumentos)."

    if "arquiv" in combo:
        sinal.append("Arquivamento")
        acao = "Avaliar desarquivamento/novo PL/apensamento."

    org_sigla_u = (org_sigla or "").upper()
    if org_sigla_u in ("MESA", "PLEN"):
        fase = org_sigla_u
    elif org_sigla_u:
        fase = f"Comissão ({org_sigla_u})"

    if isinstance(parado_dias, int) and parado_dias >= 30:
        alerta = f"Parado há {parado_dias} dias (priorizar cobrança)."

    df = pd.DataFrame(
        [
            {"Campo": "Fase", "Valor": fase},
            {"Campo": "Relator(a) (último)", "Valor": (f"{relator_nome} ({relator_partido}-{relator_uf})" if relator_nome and (relator_partido or relator_uf) else (relator_nome or "—"))},
            {"Campo": "Ação sugerida", "Valor": acao},
            {"Campo": "Sinais do texto", "Valor": ", ".join(sinal) if sinal else "—"},
            {"Campo": "Alerta", "Valor": alerta or "—"},
        ]
    )
    return df


@st.cache_data(show_spinner=False, ttl=1800)
def build_status_map(ids: list[str]) -> dict:
    """Busca status (e relator quando aplicável) com paralelismo leve para ficar rápido."""
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    # worker
    def _one(pid: str):
        s = fetch_status_proposicao(pid)
        situacao = normalize_situacao((s.get("status_descricaoSituacao") or "").strip())
        andamento = (s.get("status_descricaoTramitacao") or "").strip()

        relator_nome = ""
        relator_partido = ""
        relator_uf = ""
        if needs_relator_info(situacao, andamento):
            relator_nome = (s.get("status_ultimoRelator_nome") or "").strip()
            relator_partido = (s.get("status_ultimoRelator_partido") or "").strip()
            relator_uf = (s.get("status_ultimoRelator_uf") or "").strip()

        return pid, {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": (s.get("status_dataHora") or "").strip(),
            "siglaOrgao": (s.get("status_siglaOrgao") or "").strip(),
            "relator_nome": relator_nome,
            "relator_partido": relator_partido,
            "relator_uf": relator_uf,
        }

    # Paralelismo moderado (evita estourar rate limit)
    max_workers = 10 if len(ids) >= 40 else 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for pid, payload in ex.map(_one, ids):
            out[str(pid)] = payload

    return out


def enrich_with_status(df_base: pd.DataFrame, status_map: dict) -> pd.DataFrame:
    """Enriquece a base com status (situação/órgão/data)  (quando aplicável) e sinais de inércia.

    Observação: 'Parado (dias)' é um proxy leve calculado pela data do status. Evita chamadas massivas
    ao endpoint de tramitações.
    """
    df = df_base.copy()

    df["Situação atual"] = df["id"].astype(str).map(
        lambda x: normalize_situacao(status_map.get(str(x), {}).get("situacao", ""))
    )
    df["Andamento (status)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("andamento", "")
    )
    df["Data do status (raw)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("status_dataHora", "")
    )
    df["Órgão (sigla)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("siglaOrgao", "")
    )

    # Relator (já vem vazio quando não faz sentido exibir)
    df["Relator(a)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_nome", "")
    )
    df["Relator(a) Partido"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_partido", "")
    )
    df["Relator(a) UF"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_uf", "")
    )

    # normaliza vazios
    df["Relator(a)"] = df["Relator(a)"].fillna("").astype(str)
    df["Relator(a) Partido"] = df["Relator(a) Partido"].fillna("").astype(str)
    df["Relator(a) UF"] = df["Relator(a) UF"].fillna("").astype(str)

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month

    # indicador leve: dias desde o último status (proxy para "parado há X dias")
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


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor – Dep. Júlia Zanatta", layout="wide")


    st.markdown("""<style>
div[data-testid="stDataFrame"] td { white-space: normal !important; }
div[data-testid="stDataFrame"] * { font-size: 12px; }
</style>""", unsafe_allow_html=True)

    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")

    # estado para clique na contagem (toggle)
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

    # ----------------------------------------------------------
    # TAB 1
    # ----------------------------------------------------------
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
                st.dataframe(view, use_container_width=True, hide_index=True)

                data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria_Pauta")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )

    # ----------------------------------------------------------
    # TAB 2
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # TAB 3
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # TAB 4
    # ----------------------------------------------------------
    with tab4:
        st.subheader("Tramitação (independente) — inclui PL/PEC/PDL/PLP e RIC (com link correto)")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh = st.button("🧹 Limpar cache (autoria/status/tramitação)")
        with colB:
            st.caption("Coluna **Link** abre a **Ficha de Tramitação** (site da Câmara).")

        if bt_refresh:
            fetch_lista_proposicoes_autoria_geral.clear()
            fetch_rics_por_autor.clear()
            fetch_lista_proposicoes_autoria.clear()
            fetch_status_proposicao.clear()
            fetch_tramitacoes_proposicao.clear()
            build_status_map.clear()
            fetch_deputado_info_by_id.clear()
            st.session_state.pop("df_status_last", None)
            st.session_state["status_click_sel"] = None

        with st.spinner("Carregando proposições de autoria (com RIC incluído)..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        # filtros base (lista de proposições)
        col1, col2, col3 = st.columns([2.2, 1.1, 1.1])
        with col1:
            q = st.text_input("🔎 Buscar por sigla/número/ano OU ementa", value="", placeholder="Ex.: RIC 123/2025 | 'pix' | 'conanda'")
        with col2:
            anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
            anos_sel = st.multiselect("Ano (da proposição)", options=anos, default=anos[:3] if len(anos) >= 3 else anos)
        with col3:
            tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
            tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos)

        df_f = df_aut.copy()
        if anos_sel:
            df_f = df_f[df_f["ano"].isin(anos_sel)].copy()
        if tipos_sel:
            df_f = df_f[df_f["siglaTipo"].isin(tipos_sel)].copy()

        if q.strip():
            qn = normalize_text(q)
            df_f["_search"] = (df_f["Proposicao"].fillna("").astype(str) + " " + df_f["ementa"].fillna("").astype(str)).apply(normalize_text)
            df_f = df_f[df_f["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")

        st.caption(f"Resultados: {len(df_f)} proposições")

        # ============================================================
        # CARTEIRA POR STATUS + Toggle na contagem + Relator(a)
        # ============================================================
        st.markdown("---")
        st.markdown("## 📌 Carteira por Situação atual (status) — filtros por órgão/mês/ano + clique (toggle) ")

        cS1, cS2, cS3, cS4 = st.columns([1.2, 1.2, 1.6, 1.0])
        with cS1:
            bt_status = st.button("📥 Carregar/Atualizar status da lista filtrada", type="primary")
        with cS2:
            max_status = st.number_input("Limite (performance)", min_value=20, max_value=600, value=min(200, len(df_f)), step=20)
        with cS3:
            st.caption("Aplique filtros acima (Ano/Tipo/Busca) e depois carregue o status.")
        with cS4:
            if st.button("✖ Limpar filtro por clique"):
                st.session_state["status_click_sel"] = None

        df_status_view = st.session_state.get("df_status_last", pd.DataFrame()).copy()

        dynamic_status = []
        if not df_status_view.empty and "Situação atual" in df_status_view.columns:
            dynamic_status = [s for s in df_status_view["Situação atual"].dropna().unique().tolist() if str(s).strip()]
        status_opts = merge_status_options(dynamic_status)

        # filtros UI
        f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])

        default_status_sel = []
        if st.session_state.get("status_click_sel"):
            default_status_sel = [st.session_state["status_click_sel"]]

        with f1:
            status_sel = st.multiselect("Situação atual", options=status_opts, default=default_status_sel)

        org_opts = []
        ano_status_opts = []
        mes_status_opts = []
        if not df_status_view.empty:
            org_opts = sorted([o for o in df_status_view["Órgão (sigla)"].dropna().unique().tolist() if str(o).strip()])
            ano_status_opts = sorted([int(a) for a in df_status_view["AnoStatus"].dropna().unique().tolist() if pd.notna(a)], reverse=True)
            mes_status_opts = sorted([int(m) for m in df_status_view["MesStatus"].dropna().unique().tolist() if pd.notna(m)])

        with f2:
            org_sel = st.multiselect("Órgão (sigla)", options=org_opts, default=[])

        with f3:
            ano_status_sel = st.multiselect("Ano (do status)", options=ano_status_opts, default=[])

        with f4:
            mes_labels = [f"{m:02d}-{MESES_PT.get(m,'')}" for m in mes_status_opts]
            mes_map = {f"{m:02d}-{MESES_PT.get(m,'')}": m for m in mes_status_opts}
            mes_sel_labels = st.multiselect("Mês (do status)", options=mes_labels, default=[])
            mes_status_sel = [mes_map[x] for x in mes_sel_labels if x in mes_map]

        if bt_status:
            with st.spinner("Buscando status (e relator quando aplicável)..."):
                ids_list = df_f["id"].astype(str).head(int(max_status)).tolist()
                status_map = build_status_map(ids_list)
                df_status_view = enrich_with_status(df_f.head(int(max_status)), status_map)
                st.session_state["df_status_last"] = df_status_view

        if df_status_view.empty:
            st.info("Clique em **Carregar/Atualizar status** para preencher Situação/Órgão/Data e habilitar filtros por mês/ano.")
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

            df_counts = (
                df_fil.assign(_s=df_fil["Situação atual"].fillna("—").replace("", "—"))
                .groupby("_s", as_index=False)
                .size()
                .rename(columns={"_s": "Situação atual", "size": "Qtde"})
                .sort_values("Qtde", ascending=False)
            )

            cC1, cC2 = st.columns([1.0, 2.0])

            with cC1:
                st.markdown("**Contagem por Situação atual (clique = filtra / clique de novo = desmarca)**")

                sel_counts = st.dataframe(
                    df_counts,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )

                # TOGGLE: se clicar na mesma situação já selecionada, desmarca
                try:
                    if sel_counts and isinstance(sel_counts, dict) and sel_counts.get("selection") and sel_counts["selection"].get("rows"):
                        row_idx = sel_counts["selection"]["rows"][0]
                        clicked_status = str(df_counts.iloc[row_idx]["Situação atual"])
                        if clicked_status and clicked_status != "—":
                            current = st.session_state.get("status_click_sel")
                            st.session_state["status_click_sel"] = None if current == clicked_status else clicked_status
                except Exception:
                    pass

                if st.session_state.get("status_click_sel"):
                    st.caption(f"Filtro por clique ativo: **{st.session_state['status_click_sel']}**")

                bytes_out, mime, ext = to_xlsx_bytes(df_counts, "Contagem_Status")
                st.download_button(
                    f"⬇️ Baixar contagem ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"contagem_situacao_atual.{ext}",
                    mime=mime,
                )

            with cC2:
                st.markdown("**Lista filtrada (Link = Ficha de Tramitação + Link = Ficha de Tramitação)**")

                df_tbl_status = df_fil[
                    ["Proposicao", "siglaTipo", "ano", "Situação atual", "Órgão (sigla)", "DataStatus_dt", "Parado (dias)", "Sinal", "Relator(a) Partido", "Relator(a) UF", "id", "ementa"]
                ].rename(columns={
                    "Proposicao": "Proposição",
                    "siglaTipo": "Tipo",
                    "ano": "Ano",
                    "ementa": "Ementa",
                }).copy()

                df_tbl_status["Data do status"] = df_tbl_status["DataStatus_dt"].apply(fmt_dt_br)
                df_tbl_status.drop(columns=["DataStatus_dt"], inplace=True, errors="ignore")

                def _fmt_relator_row(r):
                    nome = (r.get("Relator(a)") or "").strip()
                    if not nome:
                        return "—"
                    p = (r.get("Relator(a) Partido") or "").strip()
                    u = (r.get("Relator(a) UF") or "").strip()
                    return f"{nome} ({p}-{u})" if (p or u) else nome

                df_tbl_status["Relator(a)"] = df_tbl_status.apply(_fmt_relator_row, axis=1)
                df_tbl_status.drop(columns=["Relator(a) Partido", "Relator(a) UF"], inplace=True, errors="ignore")

                df_tbl_status["Parado (dias)"] = df_tbl_status["Parado (dias)"].apply(lambda x: int(x) if isinstance(x, (int, float)) and pd.notna(x) else None)
                df_tbl_status["Parado há"] = df_tbl_status["Parado (dias)"].apply(lambda x: f"{x} dias" if isinstance(x, int) else "—")
                df_tbl_status.drop(columns=["Parado (dias)"], inplace=True, errors="ignore")

                df_tbl_status["LinkTramitacao"] = df_tbl_status["id"].astype(str).apply(camara_link_tramitacao)

                df_tbl_status = df_tbl_status[
                    ["Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)", "Data do status", "Sinal", "Parado há", "id", "LinkTramitacao", "Ementa"]
                ]

                st.dataframe(
                    df_tbl_status,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                    },
                )

                bytes_out, mime, ext = to_xlsx_bytes(df_tbl_status, "Carteira_Status")
                st.download_button(
                    f"⬇️ Baixar lista ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"carteira_situacao_atual_filtrada.{ext}",
                    mime=mime,
                )

        # ============================================================
        # Rastreador individual (com relator na estratégia)
        # ============================================================
        st.markdown("---")
        st.markdown("## 🔎 Rastreador individual (clique em uma linha da tabela abaixo)")

        df_tbl = df_f[["Proposicao", "ementa", "id", "ano", "siglaTipo"]].rename(
            columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
        ).copy()
        df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)

        df_tbl_view = df_tbl.head(400).copy()

        sel = st.dataframe(
            df_tbl_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            },
        )

        selected_id = None
        try:
            if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                row_idx = sel["selection"]["rows"][0]
                selected_id = str(df_tbl_view.iloc[row_idx]["ID"])
        except Exception:
            selected_id = None

        st.markdown("---")
        st.markdown("### 📍 Detalhes (clique em uma linha acima)")

        if not selected_id:
            st.info("Clique em uma proposição para carregar status e tramitações.")
        else:
            with st.spinner("Carregando status + tramitações..."):
                status = fetch_status_proposicao(selected_id)
                df_tram = fetch_tramitacoes_proposicao(selected_id)
                status_dt = parse_dt(status.get("status_dataHora") or "")
                ultima_dt, parado_dias = calc_ultima_mov(df_tram, status.get("status_dataHora") or "")

            proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
            org_sigla = status.get("status_siglaOrgao") or "—"
            situacao = status.get("status_descricaoSituacao") or "—"
            andamento = status.get("status_descricaoTramitacao") or "—"
            despacho = status.get("status_despacho") or ""
            ementa = status.get("ementa") or ""
            relator_nome = (status.get("status_ultimoRelator_nome") or "").strip()
            relator_partido = (status.get("status_ultimoRelator_partido") or "").strip()
            relator_uf = (status.get("status_ultimoRelator_uf") or "").strip()

            # só exibe relator se fizer sentido
            if not needs_relator_info(situacao, andamento):
                relator_nome = ""
                relator_partido = ""
                relator_uf = ""

            c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.1, 1.2, 1.2, 1.0, 1.3])
            c1.metric("Proposição", proposicao_fmt or "—")
            c2.metric("Órgão", org_sigla)
            c3.metric("Data do Status", fmt_dt_br(status_dt))
            c4.metric("Última mov.", fmt_dt_br(ultima_dt))
            c5.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")
            relator_fmt = (f"{relator_nome} ({relator_partido}-{relator_uf})" if relator_nome and (relator_partido or relator_uf) else (relator_nome or "—"))
            # c6.metric(relator_fmt)

            st.markdown("**Link da tramitação**")
            st.write(camara_link_tramitacao(selected_id))

            st.markdown("**Ementa**")
            st.write(ementa)

            st.markdown("**Situação atual**")
            st.write(situacao)

            st.markdown("**Último andamento**")
            st.write(andamento)

            if despacho:
                st.markdown("**Despacho (chave para onde foi)**")
                st.write(despacho)

            if status.get("urlInteiroTeor"):
                st.markdown("**Inteiro teor**")
                st.write(status["urlInteiroTeor"])

            st.markdown("### 🧠 Estratégia (tabela)")
            df_estr = montar_estrategia_tabela(org_sigla, situacao, andamento, despacho, parado_dias, relator_nome, relator_partido, relator_uf)
            st.dataframe(df_estr, use_container_width=True, hide_index=True)

            st.markdown("### 🧭 Linha do tempo (tramitações)")
            if df_tram.empty:
                st.info("Sem tramitações retornadas (ou endpoint instável no momento).")
            else:
                view_tram = df_tram[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho"]].copy()
                view_tram = view_tram.rename(columns={"siglaOrgao": "Órgão", "descricaoTramitacao": "Andamento", "despacho": "Despacho"})
                st.datafrimport datetime
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
DEPUTADA_ID_PADRAO = 220559  # ajuste se necessário

HEADERS = {"User-Agent": "MonitorZanatta/4.2 (gabinete-julia-zanatta)"}

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
    "Aguardando Parecer",
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


def needs_relator_info(situacao: str, andamento: str) -> bool:
    # Relator removido do sistema (performance e consistência)
    return False


def normalize_situacao(situacao: str) -> str:
    """Normaliza rótulos de Situação atual para evitar duplicidades e facilitar filtros."""
    s_raw = (situacao or "").strip()
    s = normalize_text(s_raw)

    # Unificar TODAS as variações de "aguardando parecer" (inclusive sem a palavra 'aguardando')
    # Ex.: "Aguardando Parecer", "Aguardando o Parecer", "Aguardando Parecer do Relator",
    #      "Aguardando Parecer de Relator(a)", "Parecer do Relator" etc.
    if "parecer" in s:
        if ("aguard" in s) or ("relator" in s) or s.startswith("parecer"):
            return "Aguardando Parecer de Relator(a)"

    # Outras normalizações leves (expanda conforme necessidade)
    return s_raw


# ============================================================
# HTTP ROBUSTO (retry/backoff)
# ============================================================

# Reuse HTTP connections (faster / fewer handshakes on Streamlit Cloud)
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

            # Rate limit / instabilidade (retry)
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
# RESOLVER DEPUTADO (RELATOR) VIA DADOS ABERTOS
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_deputado_info_by_id(dep_id: str) -> dict:
    """Retorna dados básicos do deputado para exibição (nome/partido/UF)."""
    if not dep_id:
        return {"nome": "", "siglaPartido": "", "siglaUf": ""}
    data = safe_get(f"{BASE_URL}/deputados/{dep_id}")
    if data is None or "__error__" in data:
        return {"nome": "", "siglaPartido": "", "siglaUf": ""}
    d = data.get("dados", {}) or {}
    return {
        "nome": (d.get("nome") or "").strip(),
        "siglaPartido": (d.get("siglaPartido") or "").strip(),
        "siglaUf": (d.get("siglaUf") or "").strip(),
    }


def resolve_relator_info(uri_ultimo_relator: str) -> tuple[str, str, str, str]:
    """Retorna (relator_id, relator_nome, relator_partido, relator_uf)."""
    rid = extract_id_from_uri(uri_ultimo_relator or "")
    if not rid:
        return "", "", "", ""
    info = fetch_deputado_info_by_id(rid)
    return rid, info.get("nome", ""), info.get("siglaPartido", ""), info.get("siglaUf", "")



@st.cache_data(show_spinner=False, ttl=3600)
def fetch_relator_atual_from_relatores(id_proposicao: str) -> tuple[str, str, str, str]:
    """Fallback: tenta descobrir relator(a) via endpoint /relatores quando statusProposicao não traz uriUltimoRelator.
    Retorna (relator_id, nome, partido, uf) ou ("","","","").
    """
    try:
        pid = str(id_proposicao).strip()
        if not pid:
            return "", "", "", ""
        data = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatores", params={"itens": 100, "ordem": "DESC"})
        if data is None or "__error__" in data:
            return "", "", "", ""
        items = data.get("dados", []) or []
        if not items:
            return "", "", "", ""

        # pega o mais recente que tenha algum vínculo de deputado
        for it in items:
            uri_dep = it.get("uriDeputado") or it.get("uriParlamentar") or it.get("uriDeputadoRelator") or ""
            rid = extract_id_from_uri(uri_dep)
            if rid:
                info = fetch_deputado_info_by_id(rid)
                nome = (info.get("nome") or "").strip()
                part = (info.get("siglaPartido") or "").strip()
                uf = (info.get("siglaUf") or "").strip()
                return rid, nome, part, uf

            # fallback: alguns retornos já trazem nome/partido/uf no item
            nome = (it.get("nome") or it.get("nomeDeputado") or "").strip()
            part = (it.get("siglaPartido") or it.get("partido") or "").strip()
            uf = (it.get("siglaUf") or it.get("uf") or "").strip()
            if nome:
                return "", nome, part, uf

        return "", "", "", ""
    except Exception:
        return "", "", "", ""



# ============================================================
# API: EVENTOS/PAUTA (MONITORAMENTO)
# ============================================================

@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
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

            texto_completo = f"{identificacao} — {ementa_prop}" if ementa_prop else identificacao

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


@st.cache_data(show_spinner=False, ttl=3600)
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
            "status_uriUltimoRelator": "",
            "status_ultimoRelator_id": "",
            "status_ultimoRelator_nome": "",
            "status_ultimoRelator_partido": "",
            "status_ultimoRelator_uf": "",
        }

    d = data.get("dados", {}) or {}
    status = d.get("statusProposicao", {}) or {}

    # Relator: só buscar quando fizer sentido (evita ficar lento)
    situacao_txt = (status.get("descricaoSituacao") or "").strip()
    andamento_txt = (status.get("descricaoTramitacao") or "").strip()

    relator_id = ""
    relator_nome = ""
    relator_partido = ""
    relator_uf = ""
    uri_ultimo_relator = status.get("uriUltimoRelator") or ""

    if needs_relator_info(situacao_txt, andamento_txt):
        relator_id, relator_nome, relator_partido, relator_uf = resolve_relator_info(uri_ultimo_relator)

        # Fallback: há casos em que o status não preenche uriUltimoRelator, mas já existe relatoria em /relatores
        if not relator_nome:
            rid2, nome2, part2, uf2 = fetch_relator_atual_from_relatores(str(id_proposicao))
            if nome2:
                relator_id, relator_nome, relator_partido, relator_uf = rid2, nome2, part2, uf2

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
        "status_descricaoSituacao": normalize_situacao(status.get("descricaoSituacao") or ""),
        "status_despacho": status.get("despacho") or "",
        "status_uriUltimoRelator": uri_ultimo_relator,
        "status_ultimoRelator_id": relator_id,
        "status_ultimoRelator_nome": relator_nome,
        "status_ultimoRelator_partido": relator_partido,
        "status_ultimoRelator_uf": relator_uf,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_tramitacoes_proposicao(id_proposicao):
    rows = []
    url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
    params = {"itens": 100, "ordem": "ASC", "ordenarPor": "dataHora"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for t in data.get("dados", []):
            rows.append(
                {
                    "dataHora": t.get("dataHora") or "",
                    "siglaOrgao": t.get("siglaOrgao") or "",
                    "uriOrgao": t.get("uriOrgao") or "",
                    "descricaoTramitacao": t.get("descricaoTramitacao") or "",
                    "despacho": t.get("despacho") or "",
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
        dt = pd.to_datetime(df["dataHora"], errors="coerce")
        df["DataHora_dt"] = dt
        df["Data"] = dt.dt.strftime("%d/%m/%Y")
        df["Hora"] = dt.dt.strftime("%H:%M")
        df = df[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho", "dataHora", "DataHora_dt"]]
    return df


def calc_ultima_mov(df_tram: pd.DataFrame, status_dataHora: str):
    last = None

    if df_tram is not None and not df_tram.empty:
        dt = df_tram.get("DataHora_dt")
        if dt is None:
            dt = pd.to_datetime(df_tram["dataHora"], errors="coerce")
        dt = dt.dropna()
        if not dt.empty:
            last = dt.max()

    if (last is None or pd.isna(last)) and status_dataHora:
        last = parse_dt(status_dataHora)

    parado = days_since(last) if last is not None and not pd.isna(last) else None
    return last, parado


def montar_estrategia_tabela(org_sigla: str, situacao: str, andamento: str, despacho: str, parado_dias, relator_nome: str, relator_partido: str = "", relator_uf: str = ""):
    combo = normalize_text(f"{situacao} {andamento} {despacho}")

    fase = "Indefinida"
    acao = "Conferir despacho e última tramitação."
    sinal = []
    alerta = ""

    if "aguard" in combo and "relator" in combo:
        sinal.append("Aguarda relator")
        if relator_nome:
            sinal.append(f"Relator: {relator_nome}")
            acao = "Acionar relator e mapear parecer (prazo/agenda)."

    if "parecer" in combo and "aguard" in combo:
        sinal.append("Aguarda parecer")
        if relator_nome:
            sinal.append(f"Relator: {relator_nome}")
            acao = "Cobrar parecer com o gabinete do relator (com minuta/argumentos)."

    if "arquiv" in combo:
        sinal.append("Arquivamento")
        acao = "Avaliar desarquivamento/novo PL/apensamento."

    org_sigla_u = (org_sigla or "").upper()
    if org_sigla_u in ("MESA", "PLEN"):
        fase = org_sigla_u
    elif org_sigla_u:
        fase = f"Comissão ({org_sigla_u})"

    if isinstance(parado_dias, int) and parado_dias >= 30:
        alerta = f"Parado há {parado_dias} dias (priorizar cobrança)."

    df = pd.DataFrame(
        [
            {"Campo": "Fase", "Valor": fase},
            {"Campo": "Relator(a) (último)", "Valor": (f"{relator_nome} ({relator_partido}-{relator_uf})" if relator_nome and (relator_partido or relator_uf) else (relator_nome or "—"))},
            {"Campo": "Ação sugerida", "Valor": acao},
            {"Campo": "Sinais do texto", "Valor": ", ".join(sinal) if sinal else "—"},
            {"Campo": "Alerta", "Valor": alerta or "—"},
        ]
    )
    return df


@st.cache_data(show_spinner=False, ttl=1800)
def build_status_map(ids: list[str]) -> dict:
    """Busca status (e relator quando aplicável) com paralelismo leve para ficar rápido."""
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    # worker
    def _one(pid: str):
        s = fetch_status_proposicao(pid)
        situacao = normalize_situacao((s.get("status_descricaoSituacao") or "").strip())
        andamento = (s.get("status_descricaoTramitacao") or "").strip()

        relator_nome = ""
        relator_partido = ""
        relator_uf = ""
        if needs_relator_info(situacao, andamento):
            relator_nome = (s.get("status_ultimoRelator_nome") or "").strip()
            relator_partido = (s.get("status_ultimoRelator_partido") or "").strip()
            relator_uf = (s.get("status_ultimoRelator_uf") or "").strip()

        return pid, {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": (s.get("status_dataHora") or "").strip(),
            "siglaOrgao": (s.get("status_siglaOrgao") or "").strip(),
            "relator_nome": relator_nome,
            "relator_partido": relator_partido,
            "relator_uf": relator_uf,
        }

    # Paralelismo moderado (evita estourar rate limit)
    max_workers = 10 if len(ids) >= 40 else 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for pid, payload in ex.map(_one, ids):
            out[str(pid)] = payload

    return out


def enrich_with_status(df_base: pd.DataFrame, status_map: dict) -> pd.DataFrame:
    """Enriquece a base com status (situação/órgão/data)  (quando aplicável) e sinais de inércia.

    Observação: 'Parado (dias)' é um proxy leve calculado pela data do status. Evita chamadas massivas
    ao endpoint de tramitações.
    """
    df = df_base.copy()

    df["Situação atual"] = df["id"].astype(str).map(
        lambda x: normalize_situacao(status_map.get(str(x), {}).get("situacao", ""))
    )
    df["Andamento (status)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("andamento", "")
    )
    df["Data do status (raw)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("status_dataHora", "")
    )
    df["Órgão (sigla)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("siglaOrgao", "")
    )

    # Relator (já vem vazio quando não faz sentido exibir)
    df["Relator(a)"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_nome", "")
    )
    df["Relator(a) Partido"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_partido", "")
    )
    df["Relator(a) UF"] = df["id"].astype(str).map(
        lambda x: status_map.get(str(x), {}).get("relator_uf", "")
    )

    # normaliza vazios
    df["Relator(a)"] = df["Relator(a)"].fillna("").astype(str)
    df["Relator(a) Partido"] = df["Relator(a) Partido"].fillna("").astype(str)
    df["Relator(a) UF"] = df["Relator(a) UF"].fillna("").astype(str)

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month

    # indicador leve: dias desde o último status (proxy para "parado há X dias")
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


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor – Dep. Júlia Zanatta", layout="wide")


    st.markdown("""<style>
div[data-testid="stDataFrame"] td { white-space: normal !important; }
div[data-testid="stDataFrame"] * { font-size: 12px; }
</style>""", unsafe_allow_html=True)

    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")

    # estado para clique na contagem (toggle)
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

    # ----------------------------------------------------------
    # TAB 1
    # ----------------------------------------------------------
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
                st.dataframe(view, use_container_width=True, hide_index=True)

                data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria_Pauta")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )

    # ----------------------------------------------------------
    # TAB 2
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # TAB 3
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # TAB 4
    # ----------------------------------------------------------
    with tab4:
        st.subheader("Tramitação (independente) — inclui PL/PEC/PDL/PLP e RIC (com link correto)")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh = st.button("🧹 Limpar cache (autoria/status/tramitação)")
        with colB:
            st.caption("Coluna **Link** abre a **Ficha de Tramitação** (site da Câmara).")

        if bt_refresh:
            fetch_lista_proposicoes_autoria_geral.clear()
            fetch_rics_por_autor.clear()
            fetch_lista_proposicoes_autoria.clear()
            fetch_status_proposicao.clear()
            fetch_tramitacoes_proposicao.clear()
            build_status_map.clear()
            fetch_deputado_info_by_id.clear()
            st.session_state.pop("df_status_last", None)
            st.session_state["status_click_sel"] = None

        with st.spinner("Carregando proposições de autoria (com RIC incluído)..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        # filtros base (lista de proposições)
        col1, col2, col3 = st.columns([2.2, 1.1, 1.1])
        with col1:
            q = st.text_input("🔎 Buscar por sigla/número/ano OU ementa", value="", placeholder="Ex.: RIC 123/2025 | 'pix' | 'conanda'")
        with col2:
            anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
            anos_sel = st.multiselect("Ano (da proposição)", options=anos, default=anos[:3] if len(anos) >= 3 else anos)
        with col3:
            tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
            tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos)

        df_f = df_aut.copy()
        if anos_sel:
            df_f = df_f[df_f["ano"].isin(anos_sel)].copy()
        if tipos_sel:
            df_f = df_f[df_f["siglaTipo"].isin(tipos_sel)].copy()

        if q.strip():
            qn = normalize_text(q)
            df_f["_search"] = (df_f["Proposicao"].fillna("").astype(str) + " " + df_f["ementa"].fillna("").astype(str)).apply(normalize_text)
            df_f = df_f[df_f["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")

        st.caption(f"Resultados: {len(df_f)} proposições")

        # ============================================================
        # CARTEIRA POR STATUS + Toggle na contagem + Relator(a)
        # ============================================================
        st.markdown("---")
        st.markdown("## 📌 Carteira por Situação atual (status) — filtros por órgão/mês/ano + clique (toggle) ")

        cS1, cS2, cS3, cS4 = st.columns([1.2, 1.2, 1.6, 1.0])
        with cS1:
            bt_status = st.button("📥 Carregar/Atualizar status da lista filtrada", type="primary")
        with cS2:
            max_status = st.number_input("Limite (performance)", min_value=20, max_value=600, value=min(200, len(df_f)), step=20)
        with cS3:
            st.caption("Aplique filtros acima (Ano/Tipo/Busca) e depois carregue o status.")
        with cS4:
            if st.button("✖ Limpar filtro por clique"):
                st.session_state["status_click_sel"] = None

        df_status_view = st.session_state.get("df_status_last", pd.DataFrame()).copy()

        dynamic_status = []
        if not df_status_view.empty and "Situação atual" in df_status_view.columns:
            dynamic_status = [s for s in df_status_view["Situação atual"].dropna().unique().tolist() if str(s).strip()]
        status_opts = merge_status_options(dynamic_status)

        # filtros UI
        f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])

        default_status_sel = []
        if st.session_state.get("status_click_sel"):
            default_status_sel = [st.session_state["status_click_sel"]]

        with f1:
            status_sel = st.multiselect("Situação atual", options=status_opts, default=default_status_sel)

        org_opts = []
        ano_status_opts = []
        mes_status_opts = []
        if not df_status_view.empty:
            org_opts = sorted([o for o in df_status_view["Órgão (sigla)"].dropna().unique().tolist() if str(o).strip()])
            ano_status_opts = sorted([int(a) for a in df_status_view["AnoStatus"].dropna().unique().tolist() if pd.notna(a)], reverse=True)
            mes_status_opts = sorted([int(m) for m in df_status_view["MesStatus"].dropna().unique().tolist() if pd.notna(m)])

        with f2:
            org_sel = st.multiselect("Órgão (sigla)", options=org_opts, default=[])

        with f3:
            ano_status_sel = st.multiselect("Ano (do status)", options=ano_status_opts, default=[])

        with f4:
            mes_labels = [f"{m:02d}-{MESES_PT.get(m,'')}" for m in mes_status_opts]
            mes_map = {f"{m:02d}-{MESES_PT.get(m,'')}": m for m in mes_status_opts}
            mes_sel_labels = st.multiselect("Mês (do status)", options=mes_labels, default=[])
            mes_status_sel = [mes_map[x] for x in mes_sel_labels if x in mes_map]

        if bt_status:
            with st.spinner("Buscando status (e relator quando aplicável)..."):
                ids_list = df_f["id"].astype(str).head(int(max_status)).tolist()
                status_map = build_status_map(ids_list)
                df_status_view = enrich_with_status(df_f.head(int(max_status)), status_map)
                st.session_state["df_status_last"] = df_status_view

        if df_status_view.empty:
            st.info("Clique em **Carregar/Atualizar status** para preencher Situação/Órgão/Data e habilitar filtros por mês/ano.")
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

            df_counts = (
                df_fil.assign(_s=df_fil["Situação atual"].fillna("—").replace("", "—"))
                .groupby("_s", as_index=False)
                .size()
                .rename(columns={"_s": "Situação atual", "size": "Qtde"})
                .sort_values("Qtde", ascending=False)
            )

            cC1, cC2 = st.columns([1.0, 2.0])

            with cC1:
                st.markdown("**Contagem por Situação atual (clique = filtra / clique de novo = desmarca)**")

                sel_counts = st.dataframe(
                    df_counts,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )

                # TOGGLE: se clicar na mesma situação já selecionada, desmarca
                try:
                    if sel_counts and isinstance(sel_counts, dict) and sel_counts.get("selection") and sel_counts["selection"].get("rows"):
                        row_idx = sel_counts["selection"]["rows"][0]
                        clicked_status = str(df_counts.iloc[row_idx]["Situação atual"])
                        if clicked_status and clicked_status != "—":
                            current = st.session_state.get("status_click_sel")
                            st.session_state["status_click_sel"] = None if current == clicked_status else clicked_status
                except Exception:
                    pass

                if st.session_state.get("status_click_sel"):
                    st.caption(f"Filtro por clique ativo: **{st.session_state['status_click_sel']}**")

                bytes_out, mime, ext = to_xlsx_bytes(df_counts, "Contagem_Status")
                st.download_button(
                    f"⬇️ Baixar contagem ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"contagem_situacao_atual.{ext}",
                    mime=mime,
                )

            with cC2:
                st.markdown("**Lista filtrada (Link = Ficha de Tramitação + Link = Ficha de Tramitação)**")

                df_tbl_status = df_fil[
                    ["Proposicao", "siglaTipo", "ano", "Situação atual", "Órgão (sigla)", "DataStatus_dt", "Parado (dias)", "Sinal", "Relator(a) Partido", "Relator(a) UF", "id", "ementa"]
                ].rename(columns={
                    "Proposicao": "Proposição",
                    "siglaTipo": "Tipo",
                    "ano": "Ano",
                    "ementa": "Ementa",
                }).copy()

                df_tbl_status["Data do status"] = df_tbl_status["DataStatus_dt"].apply(fmt_dt_br)
                df_tbl_status.drop(columns=["DataStatus_dt"], inplace=True, errors="ignore")

                def _fmt_relator_row(r):
                    nome = (r.get("Relator(a)") or "").strip()
                    if not nome:
                        return "—"
                    p = (r.get("Relator(a) Partido") or "").strip()
                    u = (r.get("Relator(a) UF") or "").strip()
                    return f"{nome} ({p}-{u})" if (p or u) else nome

                df_tbl_status["Relator(a)"] = df_tbl_status.apply(_fmt_relator_row, axis=1)
                df_tbl_status.drop(columns=["Relator(a) Partido", "Relator(a) UF"], inplace=True, errors="ignore")

                df_tbl_status["Parado (dias)"] = df_tbl_status["Parado (dias)"].apply(lambda x: int(x) if isinstance(x, (int, float)) and pd.notna(x) else None)
                df_tbl_status["Parado há"] = df_tbl_status["Parado (dias)"].apply(lambda x: f"{x} dias" if isinstance(x, int) else "—")
                df_tbl_status.drop(columns=["Parado (dias)"], inplace=True, errors="ignore")

                df_tbl_status["LinkTramitacao"] = df_tbl_status["id"].astype(str).apply(camara_link_tramitacao)

                df_tbl_status = df_tbl_status[
                    ["Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)", "Data do status", "Sinal", "Parado há", "id", "LinkTramitacao", "Ementa"]
                ]

                st.dataframe(
                    df_tbl_status,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                    },
                )

                bytes_out, mime, ext = to_xlsx_bytes(df_tbl_status, "Carteira_Status")
                st.download_button(
                    f"⬇️ Baixar lista ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"carteira_situacao_atual_filtrada.{ext}",
                    mime=mime,
                )

        # ============================================================
        # Rastreador individual (com relator na estratégia)
        # ============================================================
        st.markdown("---")
        st.markdown("## 🔎 Rastreador individual (clique em uma linha da tabela abaixo)")

        df_tbl = df_f[["Proposicao", "ementa", "id", "ano", "siglaTipo"]].rename(
            columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
        ).copy()
        df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)

        df_tbl_view = df_tbl.head(400).copy()

        sel = st.dataframe(
            df_tbl_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            },
        )

        selected_id = None
        try:
            if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                row_idx = sel["selection"]["rows"][0]
                selected_id = str(df_tbl_view.iloc[row_idx]["ID"])
        except Exception:
            selected_id = None

        st.markdown("---")
        st.markdown("### 📍 Detalhes (clique em uma linha acima)")

        if not selected_id:
            st.info("Clique em uma proposição para carregar status e tramitações.")
        else:
            with st.spinner("Carregando status + tramitações..."):
                status = fetch_status_proposicao(selected_id)
                df_tram = fetch_tramitacoes_proposicao(selected_id)
                status_dt = parse_dt(status.get("status_dataHora") or "")
                ultima_dt, parado_dias = calc_ultima_mov(df_tram, status.get("status_dataHora") or "")

            proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
            org_sigla = status.get("status_siglaOrgao") or "—"
            situacao = status.get("status_descricaoSituacao") or "—"
            andamento = status.get("status_descricaoTramitacao") or "—"
            despacho = status.get("status_despacho") or ""
            ementa = status.get("ementa") or ""
            relator_nome = (status.get("status_ultimoRelator_nome") or "").strip()
            relator_partido = (status.get("status_ultimoRelator_partido") or "").strip()
            relator_uf = (status.get("status_ultimoRelator_uf") or "").strip()

            # só exibe relator se fizer sentido
            if not needs_relator_info(situacao, andamento):
                relator_nome = ""
                relator_partido = ""
                relator_uf = ""

            c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.1, 1.2, 1.2, 1.0, 1.3])
            c1.metric("Proposição", proposicao_fmt or "—")
            c2.metric("Órgão", org_sigla)
            c3.metric("Data do Status", fmt_dt_br(status_dt))
            c4.metric("Última mov.", fmt_dt_br(ultima_dt))
            c5.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")
            relator_fmt = (f"{relator_nome} ({relator_partido}-{relator_uf})" if relator_nome and (relator_partido or relator_uf) else (relator_nome or "—"))
            # c6.metric(relator_fmt)

            st.markdown("**Link da tramitação**")
            st.write(camara_link_tramitacao(selected_id))

            st.markdown("**Ementa**")
            st.write(ementa)

            st.markdown("**Situação atual**")
            st.write(situacao)

            st.markdown("**Último andamento**")
            st.write(andamento)

            if despacho:
                st.markdown("**Despacho (chave para onde foi)**")
                st.write(despacho)

            if status.get("urlInteiroTeor"):
                st.markdown("**Inteiro teor**")
                st.write(status["urlInteiroTeor"])

            st.markdown("### 🧠 Estratégia (tabela)")
            df_estr = montar_estrategia_tabela(org_sigla, situacao, andamento, despacho, parado_dias, relator_nome, relator_partido, relator_uf)
            st.dataframe(df_estr, use_container_width=True, hide_index=True)

            st.markdown("### 🧭 Linha do tempo (tramitações)")
            if df_tram.empty:
                st.info("Sem tramitações retornadas (ou endpoint instável no momento).")
            else:
                view_tram = df_tram[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho"]].copy()
                view_tram = view_tram.rename(columns={"siglaOrgao": "Órgão", "descricaoTramitacao": "Andamento", "despacho": "Despacho"})
                st.dataframe(view_tram, use_container_width=True, hide_index=True)

                bytes_out, mime, ext = to_xlsx_bytes(view_tram, "Tramitacoes")
                st.download_button(
                    f"⬇️ Baixar tramitações ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"tramitacoes_{selected_id}.{ext}",
                    mime=mime,
                )

        st.markdown("---")
        bytes_out, mime, ext = to_xlsx_bytes(df_tbl, "Base_Autoria_Filtrada")
        st.download_button(
            f"⬇️ Baixar base filtrada ({ext.upper()})",
            data=bytes_out,
            file_name=f"proposicoes_autoria_filtradas.{ext}",
            mime=mime,
        )


if __name__ == "__main__":
    main()
ame(view_tram, use_container_width=True, hide_index=True)

                bytes_out, mime, ext = to_xlsx_bytes(view_tram, "Tramitacoes")
                st.download_button(
                    f"⬇️ Baixar tramitações ({ext.upper()})",
                    data=bytes_out,
                    file_name=f"tramitacoes_{selected_id}.{ext}",
                    mime=mime,
                )

        st.markdown("---")
        bytes_out, mime, ext = to_xlsx_bytes(df_tbl, "Base_Autoria_Filtrada")
        st.download_button(
            f"⬇️ Baixar base filtrada ({ext.upper()})",
            data=bytes_out,
            file_name=f"proposicoes_autoria_filtradas.{ext}",
            mime=mime,
        )


if __name__ == "__main__":
    main()
