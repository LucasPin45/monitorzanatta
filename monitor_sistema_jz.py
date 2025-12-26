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

HEADERS = {"User-Agent": "MonitorZanatta/3.1 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV"]


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


def to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


def parse_dt(iso_str: str):
    return pd.to_datetime(iso_str, errors="coerce")


def days_since(dt: pd.Timestamp):
    if pd.isna(dt):
        return None
    return (pd.Timestamp(datetime.date.today()) - dt.normalize()).days


# ============================================================
# HTTP ROBUSTO (retry/backoff)
# ============================================================

def _request_json(url: str, params=None, timeout=30, max_retries=3):
    """
    Faz GET e devolve JSON.
    - 404: retorna None
    - 429/5xx/timeouts: tenta retry curto com backoff
    """
    params = params or {}
    backoffs = [0.6, 1.2, 2.4]  # curto para Streamlit Cloud
    last_err = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)

            # 404 -> não existe
            if resp.status_code == 404:
                return None

            # 429 -> rate limit: retry
            if resp.status_code == 429:
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                continue

            # 5xx -> retry
            if 500 <= resp.status_code <= 599:
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                continue

            resp.raise_for_status()
            return resp.json()

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
            continue
        except requests.exceptions.HTTPError as e:
            last_err = e
            # outros 4xx (exceto 404/429) não adianta insistir
            break
        except Exception as e:
            last_err = e
            break

    # se falhou, não derruba o app
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

    prop_rel = item.get("proposicaoRelacionada_") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop_rel.get(chave)
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
        proposicoes_keywords = set()
        palavras_evento = set()
        pares_kw_proposicao = set()

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
            else:
                prop = item.get("proposicao") or {}
                identificacao = format_sigla_num_ano(prop.get("siglaTipo"), prop.get("numero"), prop.get("ano")) or identificacao
                ementa_prop = prop.get("ementa") or ""

            texto_completo = f"{identificacao} — {ementa_prop}" if ementa_prop else identificacao

            if relatoria_flag:
                proposicoes_relatoria.add(texto_completo)
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
            if has_keywords:
                proposicoes_keywords.add(identificacao)
                for kw in kws_item:
                    palavras_evento.add(kw)
                    pares_kw_proposicao.add((kw, identificacao))

        if not (proposicoes_relatoria or proposicoes_autoria or palavras_evento):
            continue

        mapa_kw_prop = "; ".join([f"{kw}||{pl}" for kw, pl in sorted(pares_kw_proposicao)]) if pares_kw_proposicao else ""

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
                    "proposicoes_palavras_chave": "; ".join(sorted(proposicoes_keywords)),
                    "mapeamento_kw_proposicao": mapa_kw_prop,
                    "comissao_estrategica": is_comissao_estrategica(sigla_org, comissoes_estrategicas),
                }
            )

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values(["data", "hora", "orgao_sigla", "id_evento"])
    return df


# ============================================================
# API: RASTREADOR (INDEPENDENTE) + CARTEIRA
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_lista_proposicoes_autoria(id_deputada):
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
        df = df[["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa", "uri"]]
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
        # não derruba o app
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
            "status_sequencia": "",
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
        "status_sequencia": status.get("sequencia") or "",
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_tramitacoes_proposicao(id_proposicao):
    """
    Endpoint mais instável (404/429/5xx). Nunca deve derrubar o app.
    """
    rows = []
    url = f"{BASE_URL}/proposicoes/{id_proposicao}/tramitacoes"
    params = {"itens": 100, "ordem": "ASC", "ordenarPor": "dataHora"}

    while True:
        data = safe_get(url, params=params)
        if data is None:
            # 404: sem tramitações / não existe
            break
        if "__error__" in data:
            # falha momentânea: devolve vazio (não derruba)
            break

        for t in data.get("dados", []):
            rows.append(
                {
                    "dataHora": t.get("dataHora") or "",
                    "sequencia": t.get("sequencia") or "",
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

        # next_link já vem completo
        url = next_link
        params = {}

    df = pd.DataFrame(rows)
    if not df.empty:
        dt = pd.to_datetime(df["dataHora"], errors="coerce")
        df["Data"] = dt.dt.strftime("%d/%m/%Y")
        df["Hora"] = dt.dt.strftime("%H:%M")
        df["DataHora_dt"] = dt
        df = df[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho", "sequencia", "uriOrgao", "dataHora", "DataHora_dt"]]
    return df


def calc_ultima_mov(df_tram: pd.DataFrame):
    if df_tram is None or df_tram.empty:
        return (None, None)
    dt = df_tram.get("DataHora_dt")
    if dt is None:
        dt = pd.to_datetime(df_tram["dataHora"], errors="coerce")
    dt = dt.dropna()
    if dt.empty:
        return (None, None)
    last = dt.max()
    return (last, days_since(last))


def gerar_estrategia_curta(org_sigla: str, org_nome: str, situacao: str, andamento: str, despacho: str, parado_dias):
    org_sigla_u = (org_sigla or "").upper()
    org_nome_u = (org_nome or "").upper()
    despacho_u = (despacho or "").upper()

    if "DESPACHO" in despacho_u or "MESA" in org_sigla_u or "MESA" in org_nome_u:
        msg = (
            "• *Estratégia:* fase de *despacho/encaminhamento*. "
            "Ação: checar *Mesa/SGM* e confirmar *comissões designadas* no despacho."
        )
    elif "PLEN" in org_sigla_u or "PLENÁRIO" in org_nome_u:
        msg = (
            "• *Estratégia:* está no *Plenário*. "
            "Ação: mapear líderes, avaliar urgência, preparar orientação e falar com a Mesa sobre janela de pauta."
        )
    elif org_sigla_u:
        msg = (
            f"• *Estratégia:* tramita no órgão *{org_sigla_u}* ({org_nome}). "
            "Ação: identificar secretaria e status (relator? parecer? inclusão em pauta?) e acionar o fluxo correto."
        )
    else:
        msg = (
            "• *Estratégia:* órgão atual não está claro. "
            "Ação: conferir despacho e última tramitação para identificar onde travou."
        )

    if isinstance(parado_dias, int) and parado_dias >= 30:
        msg += f" *Alerta:* parado há {parado_dias} dias → priorizar cobrança e mapa de entraves."

    combo = normalize_text(f"{situacao} {andamento} {despacho}")
    if "aguard" in combo and "relator" in combo:
        msg += " Sinal: *aguarda relator* → pressionar designação (presidência/secretaria)."
    if "parecer" in combo and "aguard" in combo:
        msg += " Sinal: *aguarda parecer* → alinhar com relator e calendarizar entrega."
    if "arquiv" in combo:
        msg += " Sinal: *arquivamento* → checar desarquivamento/reapresentação."

    return msg


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
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            alvo_partido = st.text_input("Partido", value=DEPUTADA_PARTIDO_PADRAO)
        with col2:
            alvo_uf = st.text_input("UF", value=DEPUTADA_UF_PADRAO)
        with col3:
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
        ["1️⃣ Autoria/Relatoria na pauta", "2️⃣ Palavras-chave na pauta", "3️⃣ Comissões estratégicas", "4️⃣ Rastreador + Carteira (Autoria)"]
    )

    df = pd.DataFrame()
    if bt_rodar_monitor:
        if dt_inicio > dt_fim:
            st.error("Data inicial não pode ser maior que a data final.")
            return

        with st.spinner("Consultando eventos/pauta e analisando..."):
            eventos = fetch_eventos(dt_inicio, dt_fim)

            ids_autoria = set()
            if buscar_autoria:
                ids_autoria = fetch_ids_autoria_deputada(id_deputada)

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
        st.subheader("Autoria/Relatoria na pauta (depende do monitoramento)")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_jz = df[(df["tem_autoria_deputada"]) | (df["tem_relatoria_deputada"])].copy()
            if df_jz.empty:
                st.info("Sem itens de autoria/relatoria no período.")
            else:
                view = df_jz[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "tem_autoria_deputada", "proposicoes_autoria",
                     "tem_relatoria_deputada", "proposicoes_relatoria", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(view, use_container_width=True, hide_index=True)

                xlsx = to_xlsx_bytes(view, "Autoria_Relatoria_Pauta")
                st.download_button(
                    "⬇️ XLSX – Autoria/Relatoria (pauta)",
                    data=xlsx,
                    file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    with tab2:
        st.subheader("Palavras-chave na pauta (depende do monitoramento)")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_kw = df[df["tem_palavras_chave"]].copy()
            if df_kw.empty:
                st.info("Sem palavras-chave no período.")
            else:
                view = df_kw[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "palavras_chave_encontradas", "mapeamento_kw_proposicao", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(view, use_container_width=True, hide_index=True)

                xlsx = to_xlsx_bytes(view, "PalavrasChave_Pauta")
                st.download_button(
                    "⬇️ XLSX – Palavras-chave (pauta)",
                    data=xlsx,
                    file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    with tab3:
        st.subheader("Comissões estratégicas (depende do monitoramento)")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_com = df[df["comissao_estrategica"]].copy()
            if df_com.empty:
                st.info("Sem eventos em comissões estratégicas no período.")
            else:
                view = df_com[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "tem_autoria_deputada", "proposicoes_autoria",
                     "tem_relatoria_deputada", "proposicoes_relatoria",
                     "tem_palavras_chave", "palavras_chave_encontradas", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(view, use_container_width=True, hide_index=True)

                xlsx = to_xlsx_bytes(view, "ComissoesEstrategicas_Pauta")
                st.download_button(
                    "⬇️ XLSX – Comissões estratégicas (pauta)",
                    data=xlsx,
                    file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    with tab4:
        st.subheader("Rastreador + Carteira de Projetos (Autoria) — independente da pauta")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh_base = st.button("🔄 Limpar cache (autoria/status)")
        with colB:
            st.caption("Agora endpoints instáveis (tramitações/status) NÃO derrubam o app.")

        if bt_refresh_base:
            fetch_lista_proposicoes_autoria.clear()
            fetch_status_proposicao.clear()
            fetch_tramitacoes_proposicao.clear()
            fetch_orgao_by_uri.clear()

        with st.spinner("Carregando base de proposições de autoria..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        col1, col2, col3 = st.columns([2.2, 1.1, 1.1])
        with col1:
            q = st.text_input("🔎 Buscar por sigla/número/ano OU ementa", value="", placeholder="Ex.: PL 123/2025 | 'pix' | 'vacina'")
        with col2:
            anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
            anos_sel = st.multiselect("Ano", options=anos, default=anos[:4] if len(anos) >= 4 else anos)
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

        st.caption(f"Resultados (autoria): {len(df_f)} proposições")

        st.markdown("## 📌 Carteira de Projetos (mapa de onde está)")
        colK1, colK2 = st.columns([1.2, 1.8])
        with colK1:
            bt_load_carteira = st.button("📥 Carregar/Atualizar carteira (status)", type="primary")
        with colK2:
            filtro_parado_30 = st.checkbox("Filtrar: parado > 30 dias", value=False)

        carteira_key = f"carteira_{id_deputada}_{hash(tuple(df_f['id'].tolist()))}"

        if bt_load_carteira:
            ids_list = df_f["id"].tolist()
            total = len(ids_list)
            if total == 0:
                st.info("Nada para carregar.")
            else:
                prog = st.progress(0)
                msg = st.empty()
                rows = []

                for i, pid in enumerate(ids_list, start=1):
                    msg.write(f"Carregando {i}/{total}… (ID {pid})")

                    r = df_f[df_f["id"] == pid].iloc[0]
                    status = fetch_status_proposicao(str(pid))
                    org = fetch_orgao_by_uri(status.get("status_uriOrgao") or "")
                    df_tram = fetch_tramitacoes_proposicao(str(pid))
                    last_dt, parado_dias = calc_ultima_mov(df_tram)

                    prop_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or r.get("Proposicao") or ""
                    rows.append({
                        "ID": str(pid),
                        "Proposição": prop_fmt,
                        "Tipo": r.get("siglaTipo") or status.get("sigla") or "",
                        "Ano": r.get("ano") or status.get("ano") or "",
                        "Ementa": status.get("ementa") or r.get("ementa") or "",
                        "Órgão atual (sigla)": status.get("status_siglaOrgao") or org.get("sigla") or "",
                        "Órgão atual (nome)": org.get("nome") or "",
                        "Situação atual": status.get("status_descricaoSituacao") or "",
                        "Último andamento": status.get("status_descricaoTramitacao") or "",
                        "Última mov. (dataHora)": last_dt.strftime("%Y-%m-%d %H:%M") if isinstance(last_dt, pd.Timestamp) and not pd.isna(last_dt) else "",
                        "Parado há (dias)": parado_dias if parado_dias is not None else "",
                        "Inteiro teor": status.get("urlInteiroTeor") or "",
                        "Despacho (status)": status.get("status_despacho") or "",
                    })
                    prog.progress(int(i * 100 / total))

                msg.empty()
                prog.empty()

                df_carteira = pd.DataFrame(rows)
                if not df_carteira.empty:
                    df_carteira["_parado_sort"] = pd.to_numeric(df_carteira["Parado há (dias)"], errors="coerce").fillna(-1)
                    df_carteira = df_carteira.sort_values(["_parado_sort", "Ano", "Tipo", "Proposição"], ascending=[False, False, True, True]).drop(columns=["_parado_sort"])
                st.session_state[carteira_key] = df_carteira

        df_carteira = st.session_state.get(carteira_key)
        if df_carteira is None:
            st.info("Clique em **Carregar/Atualizar carteira (status)** para montar o mapa completo.")
        else:
            view_c = df_carteira.copy()
            if filtro_parado_30:
                view_c["_p"] = pd.to_numeric(view_c["Parado há (dias)"], errors="coerce")
                view_c = view_c[view_c["_p"].fillna(-1) > 30].drop(columns=["_p"], errors="ignore")

            st.dataframe(
                view_c[
                    ["Proposição", "Tipo", "Ano", "Órgão atual (sigla)", "Órgão atual (nome)",
                     "Situação atual", "Último andamento", "Última mov. (dataHora)", "Parado há (dias)", "Ementa"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "⬇️ XLSX – Carteira de projetos",
                data=to_xlsx_bytes(view_c, "Carteira_Projetos"),
                file_name="carteira_projetos_autoria.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("---")
        st.markdown("## 🔎 Rastreador individual (status + tramitação + estratégia)")

        df_show = df_f.head(400).copy()
        st.dataframe(
            df_show[["Proposicao", "ementa", "id", "ano", "siglaTipo"]].rename(
                columns={"ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
            ),
            use_container_width=True,
            hide_index=True,
        )

        ids = df_show["id"].tolist()
        if not ids:
            st.info("Nenhuma proposição com esses filtros.")
            return

        options = df_show.apply(
            lambda r: f"{r['Proposicao']} — {r['ementa'][:120]}{'...' if len(r['ementa']) > 120 else ''}",
            axis=1
        ).tolist()

        idx = st.selectbox("Selecionar proposição para rastrear:", range(len(ids)), format_func=lambda i: options[i])
        id_sel = str(ids[idx])

        with st.spinner("Buscando ONDE ESTÁ agora + tramitação..."):
            status = fetch_status_proposicao(id_sel)
            orgao_atual = fetch_orgao_by_uri(status.get("status_uriOrgao") or "")
            df_tram = fetch_tramitacoes_proposicao(id_sel)
            last_dt, parado_dias = calc_ultima_mov(df_tram)

        proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or df_show.iloc[idx]["Proposicao"]

        org_sigla = status.get("status_siglaOrgao") or orgao_atual.get("sigla") or "—"
        org_nome = orgao_atual.get("nome") or "—"
        situacao = status.get("status_descricaoSituacao") or "—"
        andamento = status.get("status_descricaoTramitacao") or "—"
        despacho = status.get("status_despacho") or ""

        st.markdown("### 📍 Onde está AGORA")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Proposição", proposicao_fmt)
        c2.metric("Órgão atual (sigla)", org_sigla)
        c3.metric("Órgão atual (nome)", org_nome if len(org_nome) <= 28 else org_nome[:28] + "…")
        c4.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")

        st.markdown("**Situação atual**")
        st.write(situacao)
        st.markdown("**Último andamento**")
        st.write(andamento)
        if despacho:
            st.markdown("**Despacho**")
            st.write(despacho)

        if status.get("urlInteiroTeor"):
            st.markdown("**Inteiro teor**")
            st.write(status["urlInteiroTeor"])

        st.markdown("### 🧠 Estratégia (curta)")
        if st.button("🧩 Gerar estratégia para este projeto"):
            estrategia = gerar_estrategia_curta(org_sigla, org_nome, situacao, andamento, despacho, parado_dias)
            st.text_area("Copiar/colar:", value=estrategia, height=110)

        st.markdown("### 🧭 Linha do tempo (tramitações)")
        if df_tram.empty:
            st.info("Sem tramitações retornadas (ou endpoint instável no momento).")
        else:
            view_tram = df_tram[["Data", "Hora", "siglaOrgao", "descricaoTramitacao", "despacho", "dataHora"]].copy()
            view_tram = view_tram.rename(columns={"siglaOrgao": "Órgão", "descricaoTramitacao": "Andamento", "despacho": "Despacho"})
            st.dataframe(view_tram[["Data", "Hora", "Órgão", "Andamento", "Despacho"]], use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ XLSX – Tramitações",
                data=to_xlsx_bytes(view_tram, "Tramitacoes"),
                file_name=f"tramitacoes_{proposicao_fmt.replace(' ', '_').replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.download_button(
            "⬇️ XLSX – Base filtrada (autoria)",
            data=to_xlsx_bytes(df_f, "Base_Autoria_Filtrada"),
            file_name="proposicoes_autoria_filtradas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
