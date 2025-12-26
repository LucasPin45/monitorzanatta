import datetime
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

HEADERS = {"User-Agent": "MonitorZanatta/3.4 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]


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
    """Parse robusto para ISO, retorna Timestamp ou NaT."""
    return pd.to_datetime(iso_str, errors="coerce", utc=False)


def days_since(dt: pd.Timestamp):
    """Diferença em dias até hoje (timezone-agnóstico)."""
    if dt is None or pd.isna(dt):
        return None
    # normaliza para data local (sem tz) pra não dar bug com UTC
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    today = pd.Timestamp(datetime.date.today())
    return int((today - d.normalize()).days)


def fmt_dt_br(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return "—"
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    return d.strftime("%d/%m/%Y %H:%M")


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


# ============================================================
# HTTP ROBUSTO (retry/backoff)
# ============================================================

def _request_json(url: str, params=None, timeout=30, max_retries=3):
    params = params or {}
    backoffs = [0.6, 1.2, 2.4]
    last_err = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)

            if resp.status_code == 404:
                return None

            if resp.status_code == 429:
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                continue

            if 500 <= resp.status_code <= 599:
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
                    "uri": d.get("uri") or "",
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
                    "uri": d.get("uri") or "",
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
        return pd.DataFrame(columns=["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa", "uri"])

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

    cols = ["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa", "uri"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    return df


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_orgao_by_uri(uri_orgao: str):
    if not uri_orgao:
        return {"sigla": "", "nome": "", "id": ""}
    data = safe_get(uri_orgao)
    if data is None or "__error__" in data:
        return {"sigla": "", "nome": "", "id": ""}
    d = data.get("dados", {}) or {}
    return {"sigla": (d.get("sigla") or "").strip(), "nome": (d.get("nome") or "").strip(), "id": str(d.get("id") or "")}


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
        "status_descricaoSituacao": status.get("descricaoSituacao") or "",
        "status_despacho": status.get("despacho") or "",
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
    """
    Fonte da 'última movimentação':
    1) última tramitação (se houver)
    2) dataHora do statusProposicao (fallback)
    """
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


# ============================================================
# ESTRATÉGIA EM TABELA
# ============================================================

def montar_estrategia_tabela(org_sigla: str, org_nome: str, situacao: str, andamento: str, despacho: str, parado_dias):
    """
    Estrutura em tabela, pronta pra você substituir por regras melhores depois.
    """
    org_sigla_u = (org_sigla or "").upper()
    org_nome_u = (org_nome or "").upper()
    despacho_u = (despacho or "").upper()

    fase = "Indefinida"
    acao = "Conferir despacho e última tramitação."
    alerta = ""

    if "DESPACHO" in despacho_u or "MESA" in org_sigla_u or "MESA" in org_nome_u:
        fase = "Despacho/encaminhamento"
        acao = "Checar Mesa/SGM e confirmar comissões designadas."
    elif "PLEN" in org_sigla_u or "PLENÁRIO" in org_nome_u:
        fase = "Plenário"
        acao = "Mapear líderes, avaliar urgência e buscar janela de pauta."
    elif org_sigla_u:
        fase = f"Comissão ({org_sigla_u})"
        acao = "Checar relatoria/prazo e cobrar inclusão em pauta."

    combo = normalize_text(f"{situacao} {andamento} {despacho}")
    sinal = []
    if "aguard" in combo and "relator" in combo:
        sinal.append("Aguarda relator")
    if "parecer" in combo and "aguard" in combo:
        sinal.append("Aguarda parecer")
    if "arquiv" in combo:
        sinal.append("Arquivamento")

    if isinstance(parado_dias, int) and parado_dias >= 30:
        alerta = f"Parado há {parado_dias} dias (priorizar cobrança)."

    df = pd.DataFrame(
        [
            {"Campo": "Fase", "Valor": fase},
            {"Campo": "Ação sugerida", "Valor": acao},
            {"Campo": "Sinais do texto", "Valor": ", ".join(sinal) if sinal else "—"},
            {"Campo": "Alerta", "Valor": alerta or "—"},
        ]
    )
    return df


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor – Dep. Júlia Zanatta", layout="wide")
    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")

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
        ["1️⃣ Autoria/Relatoria na pauta", "2️⃣ Palavras-chave na pauta", "3️⃣ Comissões estratégicas", "4️⃣ Tramitação (independente) + RIC (com link)"]
    )

    # -------------------------
    # TABS 1-3 (pauta)
    # -------------------------
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
                st.dataframe(view, use_container_width=True, hide_index=True)

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

    # -------------------------
    # TAB 4 (independente + link + RIC)
    # -------------------------
    with tab4:
        st.subheader("Tramitação (independente) — inclui PL/PEC/PDL/PLP e RIC (com link)")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh = st.button("🧹 Limpar cache (autoria/status/tramitação)")
        with colB:
            st.caption("Clique na linha da tabela para abrir detalhes. A coluna 'Link' abre a proposição no navegador.")

        if bt_refresh:
            fetch_lista_proposicoes_autoria_geral.clear()
            fetch_rics_por_autor.clear()
            fetch_lista_proposicoes_autoria.clear()
            fetch_status_proposicao.clear()
            fetch_tramitacoes_proposicao.clear()
            fetch_orgao_by_uri.clear()

        with st.spinner("Carregando proposições de autoria (com fallback de RIC)..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        # filtros
        col1, col2, col3 = st.columns([2.2, 1.1, 1.1])
        with col1:
            q = st.text_input("🔎 Buscar por sigla/número/ano OU ementa", value="", placeholder="Ex.: RIC 123/2025 | 'pix' | 'conanda'")
        with col2:
            anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
            anos_sel = st.multiselect("Ano", options=anos, default=anos[:3] if len(anos) >= 3 else anos)
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

        # tabela com LINK clicável + seleção
        df_tbl = df_f[["Proposicao", "ementa", "id", "ano", "siglaTipo", "uri"]].rename(
            columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo", "uri": "Link"}
        ).copy()

        df_tbl_view = df_tbl.head(400).copy()

        sel = st.dataframe(
            df_tbl_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="abrir"),
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
            st.info("Clique em uma proposição na tabela para carregar status e tramitações.")
        else:
            with st.spinner("Carregando status + tramitações..."):
                status = fetch_status_proposicao(selected_id)
                orgao_atual = fetch_orgao_by_uri(status.get("status_uriOrgao") or "")
                df_tram = fetch_tramitacoes_proposicao(selected_id)

                status_dt = parse_dt(status.get("status_dataHora") or "")
                ultima_dt, parado_dias = calc_ultima_mov(df_tram, status.get("status_dataHora") or "")

            proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
            org_sigla = status.get("status_siglaOrgao") or orgao_atual.get("sigla") or "—"
            org_nome = orgao_atual.get("nome") or "—"
            situacao = status.get("status_descricaoSituacao") or "—"
            andamento = status.get("status_descricaoTramitacao") or "—"
            despacho = status.get("status_despacho") or ""
            ementa = status.get("ementa") or ""

            # MÉTRICAS (com datas)
            c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2])
            c1.metric("Proposição", proposicao_fmt or "—")
            c2.metric("Órgão atual (sigla)", org_sigla)
            c3.metric("Data do Status", fmt_dt_br(status_dt))
            c4.metric("Última movimentação", fmt_dt_br(ultima_dt))
            c5.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")

            st.markdown("**Ementa**")
            st.write(ementa)

            st.markdown("**Situação atual**")
            st.write(situacao)

            st.markdown("**Último andamento**")
            st.write(andamento)

            if despacho:
                st.markdown("**Despacho (chave para saber para onde foi)**")
                st.write(despacho)

            if status.get("urlInteiroTeor"):
                st.markdown("**Inteiro teor**")
                st.write(status["urlInteiroTeor"])

            st.markdown("### 🧠 Estratégia (tabela)")
            df_estr = montar_estrategia_tabela(org_sigla, org_nome, situacao, andamento, despacho, parado_dias)
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

        # export base filtrada
        st.markdown("---")
        bytes_out, mime, ext = to_xlsx_bytes(df_f, "Base_Autoria_Filtrada")
        st.download_button(
            f"⬇️ Baixar base filtrada ({ext.upper()})",
            data=bytes_out,
            file_name=f"proposicoes_autoria_filtradas.{ext}",
            mime=mime,
        )


if __name__ == "__main__":
    main()
