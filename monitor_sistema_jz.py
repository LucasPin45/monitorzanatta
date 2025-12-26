import datetime
import concurrent.futures
import unicodedata
import re
from functools import lru_cache
from io import BytesIO

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

HEADERS = {"User-Agent": "MonitorZanatta/4.9 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]


# ============================================================
# FUNÇÕES DE APOIO / TEXTO
# ============================================================

def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    return texto.lower().strip()


def build_link_tramitacao(id_prop: int | str) -> str:
    try:
        i = int(id_prop)
        return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={i}"
    except Exception:
        return ""


def canonical_situacao(s: str) -> str:
    """
    Unifica variações para evitar duplicidades no status.
    """
    if not s:
        return ""
    sn = normalizar_texto(s)

    # unifica "aguardando parecer ..." (com/sem "de relator")
    if "aguard" in sn and "parecer" in sn:
        return "Aguardando Parecer de Relator(a)"

    if "pronta" in sn and "pauta" in sn:
        return "Pronta para Pauta"

    return str(s).strip()


# ============================================================
# ESTRATÉGIAS (REGRAS FIXAS)
# ============================================================

def estrategia_por_situacao(situacao: str) -> list[str]:
    """
    Estratégias fixas conforme regras do usuário.
    Observação: sem relator no sistema (público). Quando o status pedir relator,
    mostramos as duas hipóteses (parceiro/neutro vs. adversário).
    """
    s = canonical_situacao(situacao)

    if s == "Aguardando Designação de Relator(a)":
        return ["Buscar entre os membros da Comissão, parlamentar parceiro."]

    if s == "Aguardando Parecer de Relator(a)":
        return [
            "Se o relator for parceiro/neutro: tentar acelerar a apresentação do parecer.",
            "Se o relator for adversário: articular um VTS com membros parceiros da Comissão."
        ]

    if s == "Pronta para Pauta":
        return [
            "Se o parecer for favorável: articular na Comissão para o parecer entrar na pauta.",
            "Se o parecer for contrário: articular pra não entrar na pauta.",
            "Caso entre na pauta: articular retirada de pauta; se não funcionar, articular obstrução e VTS."
        ]

    if s == "Aguardando Despacho do Presidente da Câmara dos Deputados":
        return ["Articular com a Mesa para acelerar a tramitação."]

    return ["Acompanhar e mapear o próximo passo (status não coberto nas regras fixas)."]


# ============================================================
# FUNÇÕES DE APOIO / API
# ============================================================

@lru_cache(maxsize=256)
def get_detalhes_proposicao(id_prop: int | str):
    """Retorna detalhes de uma proposição específica."""
    if not id_prop:
        return None
    url = f"{BASE_URL}/proposicoes/{id_prop}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("dados")
        return None
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_tramitacoes(id_prop: int | str) -> pd.DataFrame:
    """Retorna o histórico de tramitações."""
    url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            df = pd.DataFrame(r.json().get("dados", []))
            if not df.empty:
                df["dataHora"] = pd.to_datetime(df["dataHora"], errors="coerce")
                df = df.sort_values("dataHora", ascending=False)
                df["Data"] = df["dataHora"].dt.strftime("%d/%m/%Y")
                df["Hora"] = df["dataHora"].dt.strftime("%H:%M")
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def calcular_dias_parado(df_tram: pd.DataFrame) -> int:
    if df_tram is None or df_tram.empty:
        return 0
    ultima_data = df_tram["dataHora"].max()
    if pd.isna(ultima_data):
        return 0
    delta = datetime.datetime.now() - ultima_data.to_pydatetime()
    return max(0, int(delta.days))


def to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return (
        output.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    )


# ============================================================
# BUSCA BASE
# ============================================================

@st.cache_data(ttl=3600)
def buscar_proposicoes_base(ano: int, tipos_list: list[str]) -> list[dict]:
    resultados: list[dict] = []
    for t in tipos_list:
        # ordena por id para estabilidade
        url = f"{BASE_URL}/proposicoes?siglaTipo={t}&ano={ano}&ordem=ASC&ordenarPor=id"
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                resultados.extend(r.json().get("dados", []))
        except Exception:
            continue
    return resultados


def filtrar_keywords(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if not keywords:
        return df
    # escapa regex para não quebrar com caracteres especiais
    patt = "|".join([re.escape(normalizar_texto(k)) for k in keywords if k.strip()])
    if not patt:
        return df
    base = df["ementa"].fillna("").astype(str).apply(normalizar_texto)
    mask = base.str.contains(patt, na=False, regex=True)
    return df[mask]


def processar_detalhes(row: dict) -> dict:
    detalhes = get_detalhes_proposicao(row.get("id"))
    sigla = f"{row.get('siglaTipo', '')} {row.get('numero', '')}/{row.get('ano', '')}".strip()
    ementa = row.get("ementa", "")

    if detalhes:
        status = detalhes.get("statusProposicao", {}) or {}
        situacao_raw = status.get("descricaoSituacao", "Desconhecida") or "Desconhecida"
        situacao = canonical_situacao(situacao_raw)
        orgao = status.get("siglaOrgao", "N/A") or "N/A"
        andamento = status.get("descricaoTramitacao", "N/A") or "N/A"
        despacho = status.get("despacho", "N/A") or "N/A"
    else:
        situacao = "Indisponível"
        orgao = "Erro API"
        andamento = "Indisponível"
        despacho = "Erro ao obter dados"

    return {
        "id": row.get("id"),
        "Sigla": sigla,
        "Ementa": ementa,
        "Órgão": orgao,
        "Situação": situacao,
        "Andamento": andamento,
        "Despacho": despacho,
        "Link": build_link_tramitacao(row.get("id")),
    }


# ============================================================
# STREAMLIT UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor Legislativo - Júlia Zanatta", layout="wide")

    # CSS: fonte menor + wrap
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] * { font-size: 12px; }
        div[data-testid="stDataFrame"] td { white-space: normal !important; }
        div[data-testid="stDataFrame"] tbody tr td { line-height: 1.25em; }

        div[data-testid="stDataEditor"] * { font-size: 12px; }
        div[data-testid="stDataEditor"] td { white-space: normal !important; }
        div[data-testid="stDataEditor"] tbody tr td { line-height: 1.25em; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🏛️ Sistema de Monitoramento Legislativo")
    st.subheader(f"Foco: Dep. {DEPUTADA_NOME_PADRAO} ({DEPUTADA_PARTIDO_PADRAO}-{DEPUTADA_UF_PADRAO})")

    with st.sidebar:
        st.header("Filtros de Busca")
        ano = st.number_input("Ano das Proposições", min_value=2019, max_value=2030, value=2025)
        tipos = st.multiselect("Tipos de Proposição", TIPOS_CARTEIRA_PADRAO, default=["PL", "PEC", "PDL", "PLP", "RIC"])
        palavras = st.text_area("Palavras-chave (separadas por vírgula)", value=", ".join(PALAVRAS_CHAVE_PADRAO))
        lista_keywords = [p.strip() for p in palavras.split(",") if p.strip()]

        st.divider()
        st.caption("Exportação")
        export_limit = st.number_input("Limite de linhas para exportar (XLSX)", min_value=1, max_value=5000, value=2000)

    # 1) BUSCA
    with st.spinner("Buscando lista de proposições..."):
        dados_base = buscar_proposicoes_base(int(ano), list(tipos))

    if not dados_base:
        st.warning("Nenhuma proposição encontrada para os filtros selecionados.")
        return

    df_base = pd.DataFrame(dados_base)

    # 2) FILTRO KEYWORDS (ementa)
    df_filtrado = filtrar_keywords(df_base, lista_keywords)
    st.info(f"Encontradas {len(df_filtrado)} proposições com as palavras-chave selecionadas.")

    if df_filtrado.empty:
        st.warning("Após o filtro de palavras-chave, não restou nenhuma proposição.")
        return

    # 3) ENRIQUECIMENTO (detalhes/status)
    with st.spinner("Coletando detalhes técnicos (status/órgão/situação)..."):
        rows = df_filtrado.to_dict("records")
        # controle simples de performance
        max_rows = min(len(rows), 1500)
        rows = rows[:max_rows]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            resultados = list(executor.map(processar_detalhes, rows))

    df_exibicao = pd.DataFrame(resultados).copy()

    # 4) EXIBIÇÃO
    st.divider()

    if df_exibicao.empty:
        st.write("Sem dados para exibir.")
        return

    # Tabela principal (rastreador)
    st.markdown("### 🔎 Rastreador individual (clique em uma linha da tabela abaixo)")

    # Para “clicar” sem componente extra, usamos selectbox pela Sigla (leve e estável)
    # + mostramos tabela completa com Link clicável.
    df_view = df_exibicao[["Sigla", "Ementa", "id", "Órgão", "Situação", "Link"]].copy()

    st.data_editor(
        df_view,
        disabled=True,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sigla": st.column_config.TextColumn("Proposição", width="medium"),
            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            "id": st.column_config.NumberColumn("ID", width="small"),
            "Órgão": st.column_config.TextColumn("Órgão", width="small"),
            "Situação": st.column_config.TextColumn("Situação atual", width="medium"),
            "Link": st.column_config.LinkColumn("Tramitação", display_text="abrir", width="small"),
        },
    )

    st.markdown("### 📌 Details (selecione uma proposição)")
    escolha = st.selectbox("Selecione uma proposição:", df_exibicao["Sigla"].tolist())

    if not escolha:
        return

    row_sel = df_exibicao[df_exibicao["Sigla"] == escolha].iloc[0]
    selected_id = row_sel["id"]

    # Puxa tramitações para parado há e timeline
    df_tram = get_tramitacoes(selected_id)
    parado_dias = calcular_dias_parado(df_tram)

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        st.markdown("**Proposição**")
        st.write(row_sel["Sigla"])
    with c2:
        st.markdown("**Órgão**")
        st.write(row_sel["Órgão"])
    with c3:
        st.markdown("**Situação atual**")
        st.write(row_sel["Situação"])
    with c4:
        st.metric("Parado há", f"{parado_dias} dias")

    st.markdown("**Link da tramitação**")
    if row_sel["Link"]:
        st.link_button("Abrir ficha de tramitação", row_sel["Link"])
    else:
        st.write("—")

    st.markdown("**Ementa**")
    st.write(row_sel["Ementa"] if row_sel["Ementa"] else "—")

    st.markdown("**Último Despacho**")
    st.write(row_sel["Despacho"] if row_sel["Despacho"] else "—")

    st.markdown("### 🧠 Estratégia sugerida (por status)")
    for item in estrategia_por_situacao(row_sel["Situação"]):
        st.markdown(f"- {item}")

    st.markdown("### 🧭 Linha do Tempo (últimas 10 movimentações)")
    if df_tram is not None and not df_tram.empty:
        # Mostra colunas mais úteis
        cols = []
        for cand in ["Data", "Hora", "siglaOrgao", "descricaoTramitacao"]:
            if cand in df_tram.columns:
                cols.append(cand)
        if cols:
            st.data_editor(
                df_tram[cols].head(10),
                disabled=True,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "descricaoTramitacao": st.column_config.TextColumn("Tramitação", width="large"),
                    "siglaOrgao": st.column_config.TextColumn("Órgão", width="small"),
                },
            )
        else:
            st.write(df_tram.head(10))
    else:
        st.info("Nenhum histórico de tramitação encontrado (endpoint pode estar instável no momento).")

    # Export XLSX
    st.sidebar.divider()
    st.sidebar.subheader("📥 Exportar XLSX")
    df_export = df_exibicao.copy()
    if len(df_export) > int(export_limit):
        df_export = df_export.head(int(export_limit))
    xbytes, mime, ext = to_xlsx_bytes(df_export, sheet_name="Monitor")
    st.sidebar.download_button(
        "Baixar relatório (XLSX)",
        data=xbytes,
        file_name=f"relatorio_legislativo_{ano}.{ext}",
        mime=mime,
    )


if __name__ == "__main__":
    main()
