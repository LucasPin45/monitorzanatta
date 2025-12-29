# monitor_sistema_jz.py - v13
# ============================================================
# Monitor Legislativo – Dep. Júlia Zanatta (Streamlit)
# VERSÃO 13: Gráficos, Exportação XLSX, Filtros Multi-nível
# ============================================================

import datetime
import concurrent.futures
import time
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
import re

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

HEADERS = {"User-Agent": "MonitorZanatta/13.0 (gabinete-julia-zanatta)"}

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

# Temas para categorização (palavras-chave por tema)
TEMAS_CATEGORIAS = {
    "Saúde": ["vacina", "saude", "saúde", "hospital", "medicamento", "sus", "anvisa"],
    "Segurança": ["arma", "armas", "seguranca", "segurança", "policia", "polícia", "violencia", "violência"],
    "Economia": ["pix", "drex", "imposto", "irpf", "tributo", "economia", "financeiro"],
    "Direitos Humanos": ["aborto", "conanda", "crianca", "criança", "menor", "familia", "família"],
    "Educação": ["educacao", "educação", "escola", "ensino", "universidade"],
    "Meio Ambiente": ["ambiente", "ambiental", "clima", "floresta", "agro"],
    "Outros": []
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
    """Sempre tenta exportar como XLSX, fallback para CSV apenas se necessário."""
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


def categorizar_tema(ementa: str) -> str:
    """Categoriza uma proposição por tema baseado na ementa."""
    if not ementa:
        return "Outros"
    ementa_norm = normalize_text(ementa)
    for tema, palavras in TEMAS_CATEGORIAS.items():
        if tema == "Outros":
            continue
        for palavra in palavras:
            if palavra in ementa_norm:
                return tema
    return "Outros"


# ============================================================
# HTTP ROBUSTO
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
# FUNÇÃO CENTRAL - BUSCA TUDO DE UMA VEZ
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)
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


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_status_proposicao(id_proposicao):
    """Busca status usando a função centralizada."""
    dados_completos = fetch_proposicao_completa(id_proposicao)
    return {
        "id": dados_completos.get("id"),
        "sigla": dados_completos.get("sigla"),
        "numero": dados_completos.get("numero"),
        "ano": dados_completos.get("ano"),
        "ementa": dados_completos.get("ementa"),
        "urlInteiroTeor": dados_completos.get("urlInteiroTeor"),
        "status_dataHora": dados_completos.get("status_dataHora"),
        "status_siglaOrgao": dados_completos.get("status_siglaOrgao"),
        "status_descricaoTramitacao": dados_completos.get("status_descricaoTramitacao"),
        "status_descricaoSituacao": dados_completos.get("status_descricaoSituacao"),
        "status_despacho": dados_completos.get("status_despacho"),
    }


def relator_adversario_alert(relator_info: dict) -> str:
    if not relator_info:
        return ""
    p = party_norm(relator_info.get("partido") or "")
    if p and p in PARTIDOS_RELATOR_ADVERSARIO:
        return "⚠️ Relator adversário"
    return ""


def calc_ultima_mov(df_tram_ult10: pd.DataFrame, status_dataHora: str):
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
        ids_proposicoes_autoria = set()
        ids_proposicoes_relatoria = set()

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
                if id_prop:
                    ids_proposicoes_relatoria.add(str(id_prop))
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
                if id_prop:
                    ids_proposicoes_autoria.add(str(id_prop))
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
                    "ids_proposicoes_relatoria": ";".join(sorted(ids_proposicoes_relatoria)),
                    "tem_autoria_deputada": bool(proposicoes_autoria),
                    "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)),
                    "ids_proposicoes_autoria": ";".join(sorted(ids_proposicoes_autoria)),
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
# STATUS MAP
# ============================================================

@st.cache_data(show_spinner=False, ttl=900)
def build_status_map(ids: list[str]) -> dict:
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    def _one(pid: str):
        dados_completos = fetch_proposicao_completa(pid)
        
        situacao = canonical_situacao(dados_completos.get("status_descricaoSituacao", ""))
        andamento = dados_completos.get("status_descricaoTramitacao", "")
        relator_info = dados_completos.get("relator", {})
        
        relator_txt = ""
        if relator_info and relator_info.get("nome"):
            nome = relator_info.get("nome", "")
            partido = relator_info.get("partido", "")
            uf = relator_info.get("uf", "")
            if partido or uf:
                relator_txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
            else:
                relator_txt = nome
        
        return pid, {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": dados_completos.get("status_dataHora", ""),
            "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
            "relator": relator_txt,
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
    df["Relator(a)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("relator", "—"))

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["Data do status"] = dt.apply(fmt_dt_br)
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month
    df["Parado (dias)"] = df["DataStatus_dt"].apply(days_since)
    
    # Adiciona tema
    df["Tema"] = df["ementa"].apply(categorizar_tema)

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
    df = df.sort_values("DataStatus_dt", ascending=True)
    
    return df


# ============================================================
# ESTRATÉGIAS
# ============================================================

def estrategia_por_situacao(situacao: str) -> list[str]:
    s = normalize_text(canonical_situacao(situacao or ""))

    if "aguardando designacao de relator" in s or "aguardando designação de relator" in s:
        return ["Pressionar Presidência da Comissão para evitar relator governista; buscar nome técnico ou neutro."]

    if "aguardando parecer" in s:
        return ["Cobrar celeridade e confrontar viés ideológico; preparar voto em separado ou emenda supressiva."]

    if "tramitando em conjunto" in s:
        return ["Identificar projeto principal e expor 'jabutis'; atuar para desmembrar ou travar avanço."]

    if "pronta para pauta" in s:
        return ["Atuar pela retirada de pauta; se não houver recuo, preparar obstrução e discurso crítico."]

    if "aguardando deliberacao" in s or "aguardando deliberação" in s:
        return ["Mapear ambiente político da comissão; usar requerimentos para ganhar tempo ou inviabilizar votação."]

    if "aguardando apreciacao" in s or "aguardando apreciação" in s:
        return ["Pressionar Presidência para não pautar; evitar avanço silencioso do governo."]

    if "aguardando distribuicao" in s or "aguardando distribuição" in s:
        return ["Atuar para impedir envio a comissão dominada pela esquerda; antecipar contenção política."]

    if "aguardando designacao" in s or "aguardando designação" in s:
        return ["Cobrar despacho e denunciar engavetamento seletivo; manter controle do rito."]

    if "aguardando votacao" in s or "aguardando votação" in s:
        return ["Fazer contagem voto a voto; acionar obstrução, destaques e narrativa contra aumento de poder do Estado."]

    if "arquivada" in s:
        return ["Mapear possibilidade de desarquivamento ou reapresentação; avaliar custo político e timing."]

    if "aguardando despacho" in s and "presidente" in s and "camara" in s:
        return ["Atuar junto à Mesa para evitar despacho desfavorável; antecipar reação conforme comissão designada."]

    return ["—"]


def exibir_detalhes_proposicao(selected_id: str, key_prefix: str = ""):
    """
    Função reutilizável para exibir detalhes completos de uma proposição.
    """
    with st.spinner("Carregando informações completas..."):
        dados_completos = fetch_proposicao_completa(selected_id)
        
        status = {
            "status_dataHora": dados_completos.get("status_dataHora"),
            "status_siglaOrgao": dados_completos.get("status_siglaOrgao"),
            "status_descricaoTramitacao": dados_completos.get("status_descricaoTramitacao"),
            "status_descricaoSituacao": dados_completos.get("status_descricaoSituacao"),
            "status_despacho": dados_completos.get("status_despacho"),
            "ementa": dados_completos.get("ementa"),
            "urlInteiroTeor": dados_completos.get("urlInteiroTeor"),
            "sigla": dados_completos.get("sigla"),
            "numero": dados_completos.get("numero"),
            "ano": dados_completos.get("ano"),
        }
        
        relator = dados_completos.get("relator", {})
        situacao = status.get("status_descricaoSituacao") or "—"
        
        situacao_norm = normalize_text(situacao)
        precisa_relator = (
            "pronta para pauta" in situacao_norm or 
            "pronto para pauta" in situacao_norm or
            "aguardando parecer" in situacao_norm
        )
        
        alerta_relator = relator_adversario_alert(relator) if relator else ""
        df_tram10 = get_tramitacoes_ultimas10(selected_id)
        
        status_dt = parse_dt(status.get("status_dataHora") or "")
        ultima_dt, parado_dias = calc_ultima_mov(df_tram10, status.get("status_dataHora") or "")

    proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
    org_sigla = status.get("status_siglaOrgao") or "—"
    andamento = status.get("status_descricaoTramitacao") or "—"
    despacho = status.get("status_despacho") or ""
    ementa = status.get("ementa") or ""

    st.markdown("#### 🧾 Contexto")
    
    if parado_dias is not None:
        if parado_dias <= 2:
            st.error("🚨 **URGENTÍSSIMO** - Tramitação há 2 dias ou menos!")
        elif parado_dias <= 5:
            st.warning("⚠️ **URGENTE** - Tramitação há 5 dias ou menos!")
        elif parado_dias <= 15:
            st.info("🔔 **TRAMITAÇÃO RECENTE** - Movimentação nos últimos 15 dias")
    
    st.markdown(f"**Proposição:** {proposicao_fmt or '—'}")
    st.markdown(f"**Órgão:** {org_sigla}")
    st.markdown(f"**Situação atual:** {situacao}")
    
    if relator and (relator.get("nome") or relator.get("partido") or relator.get("uf")):
        rel_nome = relator.get('nome','—')
        rel_partido = relator.get('partido','')
        rel_uf = relator.get('uf','')
        rel_id = relator.get('id_deputado','')
        
        rel_txt = f"{rel_nome}"
        if rel_partido or rel_uf:
            rel_txt += f" ({rel_partido}/{rel_uf})".replace("//", "/")
        
        col_foto, col_info = st.columns([1, 3])
        
        with col_foto:
            if rel_id:
                foto_url = f"https://www.camara.leg.br/internet/deputado/bandep/{rel_id}.jpg"
                try:
                    st.image(foto_url, width=120, caption=rel_nome)
                except:
                    st.markdown(f"**Relator(a):** {rel_txt}")
            else:
                st.markdown("📷")
        
        with col_info:
            st.markdown(f"**Relator(a):**")
            st.markdown(f"**{rel_txt}**")
            
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
    
    df_estr = montar_estrategia_tabela(situacao, relator_alerta=alerta_relator)
    st.dataframe(df_estr, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🕒 Linha do Tempo (últimas 10 movimentações)")

    if df_tram10.empty:
        st.info("Sem tramitações retornadas.")
    else:
        st.dataframe(df_tram10, use_container_width=True, hide_index=True)

        bytes_out, mime, ext = to_xlsx_bytes(df_tram10, "LinhaDoTempo_10")
        st.download_button(
            f"⬇️ Baixar linha do tempo ({ext.upper()})",
            data=bytes_out,
            file_name=f"linha_do_tempo_10_{selected_id}.{ext}",
            mime=mime,
            key=f"{key_prefix}_download_timeline_{selected_id}"
        )


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
# GRÁFICOS
# ============================================================

def render_grafico_barras_situacao(df: pd.DataFrame):
    """Renderiza gráfico de barras horizontal por situação usando Streamlit nativo."""
    if df.empty or "Situação atual" not in df.columns:
        st.info("Sem dados para gráfico de situação.")
        return
    
    df_counts = (
        df.assign(_s=df["Situação atual"].fillna("-").replace("", "-"))
        .groupby("_s", as_index=False)
        .size()
        .rename(columns={"_s": "Situação", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=True)
    )
    
    if df_counts.empty:
        st.info("Sem dados para gráfico.")
        return
    
    st.markdown("##### 📊 Distribuição por Situação Atual")
    st.bar_chart(df_counts.set_index("Situação")["Quantidade"], horizontal=True, use_container_width=True)


def render_grafico_barras_tema(df: pd.DataFrame):
    """Renderiza gráfico de barras por tema."""
    if df.empty or "Tema" not in df.columns:
        st.info("Sem dados para gráfico de tema.")
        return
    
    df_counts = (
        df.groupby("Tema", as_index=False)
        .size()
        .rename(columns={"size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Tema")
    st.bar_chart(df_counts.set_index("Tema")["Quantidade"], use_container_width=True)


def render_grafico_mensal(df: pd.DataFrame):
    """Renderiza gráfico de tendência mensal."""
    if df.empty or "AnoStatus" not in df.columns or "MesStatus" not in df.columns:
        st.info("Sem dados para gráfico mensal.")
        return
    
    df_valid = df.dropna(subset=["AnoStatus", "MesStatus"]).copy()
    if df_valid.empty:
        return
    
    df_valid["AnoMes"] = df_valid.apply(
        lambda r: f"{int(r['AnoStatus'])}-{int(r['MesStatus']):02d}", axis=1
    )
    
    df_mensal = (
        df_valid.groupby("AnoMes", as_index=False)
        .size()
        .rename(columns={"size": "Movimentações"})
        .sort_values("AnoMes")
    )
    
    if df_mensal.empty or len(df_mensal) < 2:
        return
    
    st.markdown("##### 📈 Tendência de Movimentações por Mês")
    st.line_chart(df_mensal.set_index("AnoMes")["Movimentações"], use_container_width=True)


def render_grafico_tipo(df: pd.DataFrame):
    """Renderiza gráfico por tipo de proposição."""
    if df.empty or "siglaTipo" not in df.columns:
        return
    
    df_counts = (
        df.groupby("siglaTipo", as_index=False)
        .size()
        .rename(columns={"siglaTipo": "Tipo", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Tipo de Proposição")
    st.bar_chart(df_counts.set_index("Tipo")["Quantidade"], use_container_width=True)


def render_grafico_orgao(df: pd.DataFrame):
    """Renderiza gráfico por órgão atual."""
    if df.empty or "Órgão (sigla)" not in df.columns:
        return
    
    df_valid = df[df["Órgão (sigla)"].notna() & (df["Órgão (sigla)"] != "")].copy()
    if df_valid.empty:
        return
    
    df_counts = (
        df_valid.groupby("Órgão (sigla)", as_index=False)
        .size()
        .rename(columns={"Órgão (sigla)": "Órgão", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
        .head(15)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Órgão (Top 15)")
    st.bar_chart(df_counts.set_index("Órgão")["Quantidade"], use_container_width=True)


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(
        page_title="Monitor Legislativo – Dep. Júlia Zanatta",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.markdown("""
    <style>
    .map-small iframe { height: 320px !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🏛️ Monitor Legislativo – Dep. Júlia Zanatta")
    st.caption("v13 – Gráficos, Filtros Multi-nível, Exportação XLSX")

    with st.sidebar:
        st.header("⚙️ Configurações")

        nome_deputada = st.text_input("Nome completo", value=DEPUTADA_NOME_PADRAO)
        partido_deputada = st.text_input("Partido", value=DEPUTADA_PARTIDO_PADRAO)
        uf_deputada = st.text_input("UF", value=DEPUTADA_UF_PADRAO)
        id_deputada = st.number_input("ID na API", value=DEPUTADA_ID_PADRAO, step=1)

        st.markdown("---")
        st.subheader("Período de busca (pauta)")
        dt_inicio = st.date_input("Início", value=datetime.date.today())
        dt_fim = st.date_input("Fim", value=datetime.date.today() + datetime.timedelta(days=7))

        st.markdown("---")
        st.subheader("Palavras-chave")
        palavras_str = st.text_area("Uma por linha", value="\n".join(PALAVRAS_CHAVE_PADRAO), height=120)
        palavras_chave = [p.strip() for p in palavras_str.splitlines() if p.strip()]

        st.subheader("Comissões estratégicas")
        comissoes_str = st.text_input("Siglas (sep. vírgula)", value=", ".join(COMISSOES_ESTRATEGICAS_PADRAO))
        comissoes_estrategicas = [c.strip().upper() for c in comissoes_str.split(",") if c.strip()]

        st.markdown("---")
        run_scan = st.button("▶️ Rodar monitoramento (pauta)", type="primary")

    df = st.session_state.get("df_scan", pd.DataFrame())

    if run_scan:
        with st.spinner("Carregando eventos..."):
            eventos = fetch_eventos(dt_inicio, dt_fim)

        with st.spinner("Carregando autorias..."):
            ids_autoria = fetch_ids_autoria_deputada(int(id_deputada))

        with st.spinner("Escaneando pautas..."):
            df = escanear_eventos(
                eventos,
                nome_deputada,
                partido_deputada,
                uf_deputada,
                palavras_chave,
                comissoes_estrategicas,
                apenas_reuniao_deliberativa=False,
                buscar_autoria=True,
                ids_autoria_deputada=ids_autoria,
            )

        st.session_state["df_scan"] = df
        st.success(f"Monitoramento concluído – {len(df)} registros")

    tab1, tab2, tab3, tab4 = st.tabs([
        "👩‍⚖️ Autoria & Relatoria",
        "🔑 Palavras-chave",
        "🏛️ Comissões estratégicas",
        "🔎 Rastreador Individual"
    ])

    with tab1:
        st.subheader("Proposições de autoria ou relatoria da deputada")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_a = df[df["tem_autoria_deputada"] | df["tem_relatoria_deputada"]].copy()
            if df_a.empty:
                st.info("Sem autoria nem relatoria no período.")
            else:
                view = df_a[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "proposicoes_autoria", "ids_proposicoes_autoria", 
                     "proposicoes_relatoria", "ids_proposicoes_relatoria", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria")
                st.download_button(
                    f"⬇️ Baixar ({ext.upper()})",
                    data=data_bytes,
                    file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                    mime=mime,
                )
                
                st.markdown("---")
                st.markdown("### 📋 Ver detalhes de proposição de autoria na pauta")
                
                ids_autoria_pauta = set()
                for _, row in df_a.iterrows():
                    val = row.get("ids_proposicoes_autoria", "")
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != "nan":
                            for prop_texto in val_str.split("; "):
                                prop_texto = prop_texto.strip()
                                if not prop_texto:
                                    continue
                                prop_id_texto = prop_texto.split(" – ")[0].strip() if " – " in prop_texto else prop_texto
                                match = re.match(r"([A-Z]+)\s*(\d+)/(\d+)", prop_id_texto)
                                if match:
                                    sigla, numero, ano = match.groups()
                                    url = f"{BASE_URL}/proposicoes"
                                    params = {"siglaTipo": sigla, "numero": numero, "ano": ano, "itens": 1}
                                    data = safe_get(url, params=params)
                                    if data and isinstance(data, dict) and data.get("dados"):
                                        prop_data = data["dados"][0]
                                        pid = str(prop_data.get("id", ""))
                                        if pid:
                                            ids_autoria_pauta.add(pid)
                
                if not ids_autoria_pauta:
                    st.info("Nenhuma proposição de autoria identificada na pauta.")
                else:
                    st.markdown(f"**{len(ids_autoria_pauta)} proposição(ões) de autoria encontrada(s)**")
                    
                    opcoes_props = {}
                    for pid in sorted(ids_autoria_pauta):
                        info = fetch_proposicao_info(pid)
                        label = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or f"ID {pid}"
                        opcoes_props[label] = pid
                    
                    if opcoes_props:
                        prop_selecionada = st.selectbox(
                            "Selecione uma proposição para ver detalhes:",
                            options=list(opcoes_props.keys()),
                            key="select_prop_autoria_tab1"
                        )
                        
                        if prop_selecionada:
                            selected_id_tab1 = opcoes_props[prop_selecionada]
                            exibir_detalhes_proposicao(selected_id_tab1, key_prefix="tab1")

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
        st.markdown("### 🔎 Rastreador Individual")
        st.caption("Busque e acompanhe proposições de autoria da deputada")

        colA, colB = st.columns([1.2, 1.8])
        with colA:
            bt_refresh = st.button("🧹 Limpar cache (TUDO)")
        with colB:
            st.caption("Busca centralizada otimizada")

        if bt_refresh:
            fetch_proposicao_completa.clear()
            fetch_lista_proposicoes_autoria_geral.clear()
            fetch_rics_por_autor.clear()
            fetch_lista_proposicoes_autoria.clear()
            build_status_map.clear()
            st.session_state.pop("df_status_last", None)
            st.session_state["status_click_sel"] = None
            st.success("✅ Cache limpo!")

        with st.spinner("Carregando proposições de autoria..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
            return

        df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

        st.markdown("#### 🗂️ Filtros de Proposições")
        
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
        st.markdown("#### 📊 Carteira por Situação Atual")

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

        # ============================================================
        # FILTROS MULTI-NÍVEL
        # ============================================================
        st.markdown("##### 🔍 Filtros Multi-nível")
        
        f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])

        default_status_sel = []
        if st.session_state.get("status_click_sel"):
            default_status_sel = [st.session_state["status_click_sel"]]

        org_opts = []
        ano_status_opts = []
        mes_status_opts = []
        tema_opts = []
        relator_opts = []
        palavra_chave_opts = PALAVRAS_CHAVE_PADRAO.copy()

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
            
            if "Tema" in df_status_view.columns:
                tema_opts = sorted(
                    [t for t in df_status_view["Tema"].dropna().unique().tolist() if str(t).strip()]
                )
            
            if "Relator(a)" in df_status_view.columns:
                relator_opts = sorted(
                    [r for r in df_status_view["Relator(a)"].dropna().unique().tolist() 
                     if str(r).strip() and str(r).strip() != "—"]
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
        
        # Segunda linha de filtros multi-nível
        f5, f6, f7 = st.columns([1.2, 1.2, 1.6])
        
        with f5:
            tema_sel = st.multiselect("Tema", options=tema_opts, default=[])
        
        with f6:
            relator_sel = st.multiselect("Relator(a)", options=relator_opts, default=[])
        
        with f7:
            palavra_filtro = st.text_input(
                "Palavra-chave na ementa",
                placeholder="Digite para filtrar...",
                help="Filtra proposições que contenham esta palavra na ementa"
            )

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

            # Aplicar filtros multi-nível
            if status_sel:
                df_fil = df_fil[df_fil["Situação atual"].isin(status_sel)].copy()

            if org_sel:
                df_fil = df_fil[df_fil["Órgão (sigla)"].isin(org_sel)].copy()

            if ano_status_sel:
                df_fil = df_fil[df_fil["AnoStatus"].isin(ano_status_sel)].copy()

            if mes_status_sel:
                df_fil = df_fil[df_fil["MesStatus"].isin(mes_status_sel)].copy()
            
            if tema_sel and "Tema" in df_fil.columns:
                df_fil = df_fil[df_fil["Tema"].isin(tema_sel)].copy()
            
            if relator_sel and "Relator(a)" in df_fil.columns:
                df_fil = df_fil[df_fil["Relator(a)"].isin(relator_sel)].copy()
            
            if palavra_filtro.strip():
                palavra_norm = normalize_text(palavra_filtro)
                df_fil = df_fil[df_fil["ementa"].apply(lambda x: palavra_norm in normalize_text(str(x)))].copy()

            st.markdown("---")
            
            # ============================================================
            # GRÁFICOS
            # ============================================================
            st.markdown("#### 📈 Análise Visual")
            
            with st.expander("📊 Gráficos e Análises", expanded=True):
                g1, g2 = st.columns(2)
                
                with g1:
                    render_grafico_barras_situacao(df_fil)
                
                with g2:
                    render_grafico_barras_tema(df_fil)
                
                g3, g4 = st.columns(2)
                
                with g3:
                    render_grafico_tipo(df_fil)
                
                with g4:
                    render_grafico_orgao(df_fil)
                
                render_grafico_mensal(df_fil)

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
                "Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)", "Relator(a)",
                "Data do status", "Sinal", "Parado há", "Tema", "id", "LinkTramitacao", "Ementa"
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
                st.markdown("**Contagem por Situação atual**")
                st.dataframe(df_counts, hide_index=True, use_container_width=True)

            with cC2:
                st.markdown("**Lista filtrada (mais antigo no topo)**")
                
                st.markdown('<div class="map-small">', unsafe_allow_html=True)
                st.dataframe(
                    df_tbl_status[show_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                        "Relator(a)": st.column_config.TextColumn("Relator(a)", width="medium"),
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
        st.markdown("#### 🔍 Buscar Proposição Específica")

        q = st.text_input(
            "Filtrar proposições",
            value="",
            placeholder="Ex.: PL 2030/2025 | 'pix' | 'conanda'",
            help="Busque por sigla/número/ano ou palavras na ementa"
        )

        df_rast = df_base.copy()
        if q.strip():
            qn = normalize_text(q)
            df_rast["_search"] = (df_rast["Proposicao"].fillna("").astype(str) + " " + df_rast["ementa"].fillna("").astype(str)).apply(normalize_text)
            df_rast = df_rast[df_rast["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")

        df_rast_lim = df_rast.head(400).copy()
        with st.spinner("Carregando datas de status do rastreador..."):
            ids_r = df_rast_lim["id"].astype(str).tolist()
            status_map_r = build_status_map(ids_r)
            df_rast_enriched = enrich_with_status(df_rast_lim, status_map_r)

        df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)

        st.caption(f"Resultados no rastreador (limitado a 400): {len(df_rast_enriched)} proposições")

        df_tbl = df_rast_enriched.rename(
            columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
        ).copy()
        
        df_tbl["Último andamento"] = df_rast_enriched["Andamento (status)"]
        df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)
        
        def get_alerta_emoji(dias):
            if pd.isna(dias):
                return ""
            if dias <= 2:
                return "🚨"
            if dias <= 5:
                return "⚠️"
            if dias <= 15:
                return "🔔"
            return ""
        
        df_tbl["Alerta"] = df_rast_enriched["Parado (dias)"].apply(get_alerta_emoji)

        show_cols_r = [
            "Alerta", "Proposição", "Ementa", "ID", "Ano", "Tipo", "Órgão (sigla)",
            "Situação atual", "Último andamento", "Data do status", "LinkTramitacao",
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
                "Alerta": st.column_config.TextColumn("", width="small", help="Urgência da tramitação"),
                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            }
        )
        
        # Legenda
        st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")
        
        # Botão de exportação XLSX para busca específica
        col_exp1, col_exp2 = st.columns([1, 3])
        with col_exp1:
            bytes_rast, mime_rast, ext_rast = to_xlsx_bytes(df_tbl[show_cols_r], "Busca_Especifica")
            st.download_button(
                f"⬇️ Exportar resultados ({ext_rast.upper()})",
                data=bytes_rast,
                file_name=f"busca_especifica_proposicoes.{ext_rast}",
                mime=mime_rast,
                key="export_busca_especifica"
            )

        selected_id = None
        try:
            if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                row_idx = sel["selection"]["rows"][0]
                selected_id = str(df_tbl.iloc[row_idx]["ID"])
        except Exception:
            selected_id = None

        st.markdown("---")
        st.markdown("#### 📋 Detalhes da Proposição Selecionada")

        if not selected_id:
            st.info("Clique em uma proposição para carregar status, estratégia e linha do tempo.")
        else:
            exibir_detalhes_proposicao(selected_id, key_prefix="tab4")

    st.markdown("---")


if __name__ == "__main__":
    main()