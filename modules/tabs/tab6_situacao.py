# modules/tabs/tab6_situacao.py
# v2 08/02/2025 16:15 (Brasília)
"""
Tab 6 – Matérias por Situação Atual (Câmara)

Funcionalidades:
- Carregamento 100 % automático (proposições + status, sem botão)
- Tipos: PDL, PEC (só 1ª signatária), PL, PLP, PRC, RIC  —  desde 2023
- Limite: 300 proposições p/ performance
- Filtros: ano, tipo, situação, órgão, tema, relator, palavra-chave
- Visão executiva: resumo, atenção deputada, prioridades gabinete
- Gráficos: situação, tema, tipo, órgão, tendência mensal
- Tabela interativa + detalhamento por seleção
- Downloads XLSX e PDF
- SEM integração Senado (Senado fica na Aba 5)

Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import datetime
import requests

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # backend sem display
import matplotlib.pyplot as plt

from core.utils import (
    to_xlsx_bytes,
    to_pdf_bytes,
    normalize_text,
    camara_link_tramitacao,
)

# ============================================================
# CONSTANTES
# ============================================================

_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
_HEADERS  = {"User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)"}

# Tipos relevantes para a aba 6
TIPOS_TAB6 = {"PDL", "PEC", "PL", "PLP", "PRC", "RIC"}

# Limite de proposições para performance
LIMITE_PROPOSICOES = 300

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
    "Apreciação pelo Senado Federal",
    "Aguardando Remessa ao Arquivo",
    "Em providência Interna",
]

MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

PARTIDOS_OPOSICAO = {"PT", "PSOL", "PCDOB", "PC DO B", "REDE", "PV", "PSB", "PDT"}

TEMAS_CATEGORIAS = {
    "Saúde": [
        "vacina", "saude", "saúde", "hospital", "medicamento", "sus", "anvisa",
        "medico", "médico", "enfermeiro", "farmacia", "farmácia", "tratamento",
        "doenca", "doença", "epidemia", "pandemia", "leito", "uti", "plano de saude",
    ],
    "Segurança Pública": [
        "arma", "armas", "seguranca", "segurança", "policia", "polícia", "violencia",
        "violência", "crime", "criminal", "penal", "prisao", "prisão", "preso",
        "bandido", "trafic", "roubo", "furto", "homicidio", "homicídio", "legítima defesa",
        "porte", "posse de arma", "cac", "atirador", "caçador", "colecionador",
    ],
    "Economia e Tributos": [
        "pix", "drex", "imposto", "irpf", "tributo", "economia", "financeiro",
        "taxa", "contribuicao", "contribuição", "fiscal", "orcamento", "orçamento",
        "divida", "dívida", "inflacao", "inflação", "juros", "banco", "credito", "crédito",
        "renda", "salario", "salário", "aposentadoria", "previdencia", "previdência",
        "inss", "fgts", "trabalhista", "clt", "emprego", "desemprego",
    ],
    "Família e Costumes": [
        "aborto", "conanda", "crianca", "criança", "menor", "familia", "família",
        "genero", "gênero", "ideologia", "lgb", "trans", "casamento", "uniao", "união",
        "mae", "mãe", "pai", "filho", "maternidade", "paternidade", "nascituro",
        "vida", "pro-vida", "pró-vida", "adocao", "adoção", "tutela", "guarda",
    ],
    "Educação": [
        "educacao", "educação", "escola", "ensino", "universidade", "professor",
        "aluno", "estudante", "enem", "vestibular", "mec", "fundeb", "creche",
        "alfabetizacao", "alfabetização", "curriculo", "currículo", "didatico", "didático",
    ],
    "Agronegócio": [
        "agro", "rural", "fazenda", "produtor", "agricult", "pecuaria", "pecuária",
        "gado", "soja", "milho", "cafe", "café", "cana", "algodao", "algodão",
        "fertilizante", "agrotox", "defensivo", "irrigacao", "irrigação", "funrural",
        "terra", "propriedade rural", "mst", "invasao", "invasão", "demarcacao", "demarcação",
    ],
    "Meio Ambiente": [
        "ambiental", "ambiente", "ibama", "icmbio", "floresta", "desmatamento",
        "poluicao", "poluição", "saneamento", "residuo", "resíduo", "lixo",
        "sustentab", "carbono", "emissao", "emissão", "clima", "aquecimento",
    ],
    "Comunicação e Tecnologia": [
        "internet", "digital", "dado", "dados", "privacidade", "lgpd", "tecnologia",
        "telecomunicacao", "telecomunicação", "5g", "inteligencia artificial",
        "rede social", "plataforma", "fake news", "desinforma", "censura",
        "liberdade de expressao", "liberdade de expressão", "imprensa",
    ],
    "Direitos e Cidadania": [
        "pcd", "deficien", "acessibilidade", "idoso", "autismo", "autista",
        "inclusao", "inclusão", "igualdade", "discriminacao", "discriminação",
        "indigena", "indígena", "quilombo", "direitos humanos",
    ],
    "Transporte e Infraestrutura": [
        "transporte", "rodovia", "ferrovia", "porto", "aeroporto", "pedágio",
        "pedagio", "transito", "trânsito", "mobilidade", "infraestrutura",
        "obra", "saneamento", "habitacao", "habitação", "moradia",
    ],
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def _categorizar_tema(ementa: str) -> str:
    """Categoriza proposição por tema baseado na ementa (scoring)."""
    if not ementa:
        return "Não Classificado"
    ementa_norm = normalize_text(ementa)
    scores: Dict[str, int] = {}
    for tema, palavras in TEMAS_CATEGORIAS.items():
        score = sum(1 for p in palavras if p in ementa_norm)
        if score:
            scores[tema] = score
    return max(scores, key=scores.get) if scores else "Não Classificado"


def _sinal_alerta(dias) -> str:
    """Emoji de sinal baseado em dias parado."""
    try:
        if dias is None or pd.isna(dias):
            return "—"
        d = int(dias)
        if d >= 30:
            return "🔴"
        if d >= 15:
            return "🟠"
        if d >= 7:
            return "🟡"
        return "🟢"
    except (ValueError, TypeError):
        return "—"


def _merge_status_options(dynamic_opts: list) -> list:
    """Merge status pré-definidos + dinâmicos sem duplicatas."""
    seen: set = set()
    merged: list = []
    for s in STATUS_PREDEFINIDOS + sorted(
        [o for o in dynamic_opts if o and str(o).strip()]
    ):
        if s and s not in seen:
            merged.append(s)
            seen.add(s)
    return merged


# ============================================================
# FILTRO PEC — SÓ PRIMEIRA SIGNATÁRIA
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _verificar_primeira_signataria_pec(
    ids_pec: tuple,
    id_deputada: int,
) -> set:
    """
    Dada uma tupla de IDs de PECs, retorna o subconjunto onde a deputada
    é a **primeira signatária** (proponente / ordemAssinatura == 1).

    Chama ``/proposicoes/{id}/autores`` para cada PEC.
    Cache de 1 h para evitar chamadas repetidas.
    """
    ids_ok: set = set()
    for pid in ids_pec:
        try:
            url = f"{_BASE_URL}/proposicoes/{pid}/autores"
            resp = requests.get(url, headers=_HEADERS, timeout=12)
            if resp.status_code != 200:
                continue
            autores = resp.json().get("dados", [])
            if not autores:
                continue
            # O primeiro autor da lista é o proponente / 1ª assinatura
            primeiro = autores[0]
            uri_autor = primeiro.get("uri", "")
            # uri no formato .../deputados/{id}
            if str(id_deputada) in uri_autor:
                ids_ok.add(str(pid))
        except Exception:
            continue
    return ids_ok


# ============================================================
# PRIORIDADE / AÇÃO SUGERIDA
# ============================================================

def _calcular_prioridade(row: pd.Series) -> int:
    score = 0
    try:
        dias = int(row.get("Parado (dias)", 0) or 0) if pd.notna(row.get("Parado (dias)")) else 0
    except (ValueError, TypeError):
        dias = 0
    if dias >= 30:
        score += 100
    elif dias >= 15:
        score += 70
    elif dias >= 7:
        score += 40

    sit = str(row.get("Situação atual", "") or "").lower()
    if "pronta para pauta" in sit:
        score += 50
    elif "aguardando delibera" in sit:
        score += 45
    elif "aguardando designa" in sit:
        score += 30

    rel = str(row.get("Relator(a)", "") or "").upper()
    if any(p in rel for p in PARTIDOS_OPOSICAO):
        score += 20
    return score


def _gerar_acao_sugerida(row: pd.Series) -> str:
    sit = str(row.get("Situação atual", "") or "").lower()
    rel = str(row.get("Relator(a)", "") or "")
    acoes: list = []

    if rel.strip() and rel.strip() != "—":
        if any(p in rel.upper() for p in PARTIDOS_OPOSICAO):
            acoes.append("⚠️ Relator adversário: atenção")

    if "aguardando designa" in sit or "sem relator" in sit:
        acoes.append("Cobrar designação de relator")
    elif "pronta para pauta" in sit:
        acoes.append("Articular inclusão em pauta")
    elif "aguardando delibera" in sit:
        acoes.append("Preparar fala/destaque para votação")
    elif "aguardando parecer" in sit:
        acoes.append("Acompanhar elaboração do parecer")
    elif "tramitando em conjunto" in sit:
        acoes.append("Monitorar proposição principal")

    try:
        d = int(row.get("Parado (dias)", 0) or 0) if pd.notna(row.get("Parado (dias)")) else 0
    except (ValueError, TypeError):
        d = 0
    if d >= 30:
        acoes.append("DESTRAVAR: contato com comissão/liderança")
    elif d >= 15:
        acoes.append("Verificar andamento com secretaria")

    return " | ".join(acoes) if acoes else "Acompanhar tramitação"


# ============================================================
# VISÃO EXECUTIVA
# ============================================================

def _render_resumo_executivo(df: pd.DataFrame):
    if df.empty:
        return
    st.markdown("### 📊 Resumo Executivo")

    c1, c2, c3, c4 = st.columns(4)

    def _cnt_dias(mx_dias):
        """Conta proposições com Parado (dias) <= mx_dias (tramitou recentemente)."""
        try:
            col = pd.to_numeric(df["Parado (dias)"], errors="coerce")
            return int((col.notna() & (col <= mx_dias)).sum())
        except Exception:
            return 0

    def _cs(termo):
        if "Situação atual" not in df.columns:
            return 0
        return int(df["Situação atual"].fillna("").str.lower().str.contains(termo.lower()).sum())

    with c1:
        st.metric("📋 Total de Matérias", len(df))
    with c2:
        st.metric("🕐 Tramitou no último mês", _cnt_dias(30))
    with c3:
        st.metric("📨 Aguard. Despacho Presidente", _cs("aguardando despacho do presidente"))
    with c4:
        st.metric("🏛️ Apreciação pelo Senado", _cs("aprecia"))

    st.markdown("#### 📌 Por Situação-Chave")
    s1, s2, s3 = st.columns(3)

    with s1:
        st.metric("🔍 Aguard. Relator", _cs("aguardando designa"))
    with s2:
        st.metric("📝 Aguard. Parecer", _cs("aguardando parecer"))
    with s3:
        st.metric("📅 Pronta p/ Pauta", _cs("pronta para pauta"))

    st.markdown("#### 🏛️ Top 3 Órgãos e Situações")
    co, cs = st.columns(2)
    with co:
        if "Órgão (sigla)" in df.columns:
            for org, q in df["Órgão (sigla)"].value_counts().head(3).items():
                st.write(f"**{org}**: {q}")
    with cs:
        if "Situação atual" in df.columns:
            for si, q in df["Situação atual"].value_counts().head(3).items():
                st.write(f"**{str(si)[:40]}**: {q}")
    st.markdown("---")


def _render_atencao_deputada(df: pd.DataFrame):
    if df.empty:
        return
    st.markdown("### ⚠️ Atenção da Deputada (Top 5)")
    st.caption("Matérias que exigem decisão ou ação imediata")

    dfp = df.copy()
    # Garantir colunas
    if "Proposição" not in dfp.columns and "Proposicao" in dfp.columns:
        dfp["Proposição"] = dfp["Proposicao"]
    if "LinkTramitacao" not in dfp.columns and "id" in dfp.columns:
        dfp["LinkTramitacao"] = dfp["id"].astype(str).apply(camara_link_tramitacao)
    dfp["_pri"] = dfp.apply(_calcular_prioridade, axis=1)
    dfp["Ação Sugerida"] = dfp.apply(_gerar_acao_sugerida, axis=1)

    for idx, (_, r) in enumerate(dfp.nlargest(5, "_pri").iterrows(), 1):
        prop = r.get("Proposição", r.get("Proposicao", ""))
        dias = r.get("Parado (dias)", "—")
        link = r.get("LinkTramitacao", "")
        try:
            d = int(dias)
            sn = "🔴" if d >= 30 else "🟠" if d >= 15 else "🟡" if d >= 7 else "🟢"
        except (ValueError, TypeError):
            sn = "⚪"
        # Prop com link clicável
        prop_display = f"[{prop}]({link})" if link and str(link).startswith("http") else prop
        st.markdown(
            f"**{idx}. {sn} {prop_display}** | {r.get('Órgão (sigla)', '—')} | {dias} dias  \n"
            f"*Situação:* {str(r.get('Situação atual', '—'))[:50]}  \n"
            f"*→ Ação:* **{r.get('Ação Sugerida', '—')}**"
        )
    st.markdown("---")


def _render_prioridades_gabinete(df: pd.DataFrame):
    if df.empty:
        return
    st.markdown("### 📋 Top Prioridades do Gabinete (Top 20)")
    st.caption("Para distribuição de tarefas e acompanhamento")

    dfp = df.copy()
    # Garantir coluna Proposição existe
    if "Proposição" not in dfp.columns and "Proposicao" in dfp.columns:
        dfp["Proposição"] = dfp["Proposicao"]
    dfp["_pri"] = dfp.apply(_calcular_prioridade, axis=1)
    dfp["Ação Sugerida"] = dfp.apply(_gerar_acao_sugerida, axis=1)
    top = dfp.nlargest(20, "_pri")

    cols = [
        c for c in [
            "Proposição", "Situação atual", "Órgão (sigla)",
            "Parado (dias)", "Relator(a)", "Ação Sugerida",
        ]
        if c in top.columns
    ]
    if "Ação Sugerida" not in cols:
        cols.append("Ação Sugerida")

    st.dataframe(
        top[cols],
        use_container_width=True,
        hide_index=True,
        column_config={"Ação Sugerida": st.column_config.TextColumn("Ação Sugerida", width="large")},
    )
    st.markdown("---")


# ============================================================
# GRÁFICOS (matplotlib estático)
# ============================================================

def _graf_situacao(df):
    if df.empty or "Situação atual" not in df.columns:
        return
    dc = (
        df.assign(_s=df["Situação atual"].fillna("-").replace("", "-"))
        .groupby("_s", as_index=False).size()
        .rename(columns={"_s": "Situação", "size": "Qtde"})
        .sort_values("Qtde", ascending=True)
    )
    if dc.empty:
        return
    st.markdown("##### 📊 Distribuição por Situação Atual")
    fig, ax = plt.subplots(figsize=(10, max(4, len(dc) * 0.4)))
    bars = ax.barh(dc["Situação"], dc["Qtde"], color="#1f77b4")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Quantidade"); ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=9)
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)


def _graf_tema(df):
    if df.empty or "Tema" not in df.columns:
        return
    dc = df.groupby("Tema", as_index=False).size().rename(columns={"size": "Qtde"}).sort_values("Qtde", ascending=False)
    if dc.empty:
        return
    st.markdown("##### 📊 Distribuição por Tema")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(dc)), dc["Qtde"], color="#2ca02c")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(range(len(dc)))
    ax.set_xticklabels(dc["Tema"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)


def _graf_tipo(df):
    col_t = "Tipo" if "Tipo" in df.columns else "siglaTipo"
    if df.empty or col_t not in df.columns:
        return
    dc = df.groupby(col_t, as_index=False).size().rename(columns={col_t: "Tipo", "size": "Qtde"}).sort_values("Qtde", ascending=False)
    if dc.empty:
        return
    st.markdown("##### 📊 Distribuição por Tipo")
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(range(len(dc)), dc["Qtde"], color="#1f77b4")
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_xticks(range(len(dc))); ax.set_xticklabels(dc["Tipo"], fontsize=10)
    ax.set_ylabel("Quantidade")
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)


def _graf_orgao(df):
    if df.empty or "Órgão (sigla)" not in df.columns:
        return
    dv = df[df["Órgão (sigla)"].notna() & (df["Órgão (sigla)"] != "")].copy()
    if dv.empty:
        return
    dc = (
        dv.groupby("Órgão (sigla)", as_index=False).size()
        .rename(columns={"Órgão (sigla)": "Órgão", "size": "Qtde"})
        .sort_values("Qtde", ascending=False).head(15)
    )
    if dc.empty:
        return
    st.markdown("##### 📊 Distribuição por Órgão (Top 15)")
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(range(len(dc)), dc["Qtde"], color="#d62728")
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xticks(range(len(dc)))
    ax.set_xticklabels(dc["Órgão"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)


def _graf_mensal(df):
    if df.empty or "AnoStatus" not in df.columns or "MesStatus" not in df.columns:
        return
    dv = df.dropna(subset=["AnoStatus", "MesStatus"]).copy()
    if dv.empty:
        return
    dv["_ym"] = dv.apply(lambda r: int(r["AnoStatus"]) * 100 + int(r["MesStatus"]), axis=1)
    dm = dv.groupby("_ym", as_index=False).size().rename(columns={"size": "Mov"}).sort_values("_ym").reset_index(drop=True)
    if dm.empty or len(dm) < 2:
        return
    dm["Label"] = dm["_ym"].apply(lambda ym: f"{int(ym) % 100:02d}/{int(ym) // 100}")
    st.markdown("##### 📈 Tendência de Movimentações por Mês")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(range(len(dm)), dm["Mov"], marker="o", color="#ff7f0e", linewidth=2, markersize=6)
    for i, (x, y) in enumerate(zip(range(len(dm)), dm["Mov"])):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xticks(range(len(dm)))
    ax.set_xticklabels(dm["Label"], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Mês/Ano"); ax.set_ylabel("Movimentações"); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)


# ============================================================
# ██  RENDER PRINCIPAL
# ============================================================

def render_tab6(
    provider,
    exibir_detalhes_proposicao_func: Callable,
    id_deputada: int,
) -> None:
    """
    Aba 6 – Matérias por Situação Atual (Câmara).

    Args
    ----
    provider : DataProvider
    exibir_detalhes_proposicao_func : callback para detalhar proposição
    id_deputada : ID da deputada na API da Câmara
    """

    st.markdown("### 📊 Matérias por situação atual")
    st.info(
        "💡 **Dica:** Visualize a carteira completa de proposições por situação de tramitação. "
        "Use os filtros para segmentar por ano, tipo, órgão e tema."
    )
    st.caption("Análise da carteira de proposições por status de tramitação — somente Câmara")

    # ----------------------------------------------------------
    # CACHE (session_state)
    # ----------------------------------------------------------
    for key, default in [
        ("df_aut6_cache", pd.DataFrame()),
        ("df_status6_cache", pd.DataFrame()),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    cI, cR = st.columns([3, 1])
    with cI:
        st.caption("💡 **Matérias carregam automaticamente.** Clique em 'Atualizar' para forçar recarga.")
    with cR:
        btn_atualizar = st.button("🔄 Atualizar", key="btn_refresh_aba6")

    # ----------------------------------------------------------
    # 1. CARREGAR PROPOSIÇÕES DE AUTORIA (automático)
    # ----------------------------------------------------------
    precisa_carregar = st.session_state["df_aut6_cache"].empty or btn_atualizar

    if precisa_carregar:
        with st.spinner("Carregando proposições de autoria…"):
            df_aut = provider.fetch_proposicoes_autoria(id_deputada)
            st.session_state["df_aut6_cache"] = df_aut
            st.session_state["df_status6_cache"] = pd.DataFrame()   # força reload status
            if btn_atualizar:
                st.success(f"✅ {len(df_aut)} proposições recarregadas!")
    else:
        df_aut = st.session_state["df_aut6_cache"]

    if df_aut.empty:
        st.info("Nenhuma proposição de autoria encontrada.")
        return

    # ----------------------------------------------------------
    # 2. FILTRAR TIPOS RELEVANTES
    # ----------------------------------------------------------
    df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_TAB6)].copy()

    if df_aut.empty:
        st.info("Nenhuma proposição dos tipos selecionados.")
        return

    # ----------------------------------------------------------
    # 3. PEC — MANTER SOMENTE PRIMEIRA SIGNATÁRIA
    # ----------------------------------------------------------
    pecs = df_aut[df_aut["siglaTipo"] == "PEC"]
    if not pecs.empty:
        ids_pec = tuple(pecs["id"].astype(str).tolist())
        with st.spinner(f"Verificando 1ª signatária em {len(ids_pec)} PEC(s)…"):
            ids_ok = _verificar_primeira_signataria_pec(ids_pec, id_deputada)
        # Remover PECs onde NÃO é primeira signatária
        mask_pec_ruim = (df_aut["siglaTipo"] == "PEC") & (~df_aut["id"].astype(str).isin(ids_ok))
        n_removidas = int(mask_pec_ruim.sum())
        df_aut = df_aut[~mask_pec_ruim].copy()
        if n_removidas:
            st.caption(f"ℹ️ {n_removidas} PEC(s) removida(s) por não ser 1ª signatária.")

    if df_aut.empty:
        st.info("Nenhuma proposição após filtro de PEC 1ª signatária.")
        return

    # ----------------------------------------------------------
    # 4. FILTROS BÁSICOS — ANO e TIPO
    # ----------------------------------------------------------
    st.markdown("#### 🗂️ Filtros de Proposições")

    cA, cT = st.columns(2)
    with cA:
        anos = sorted(
            [a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()],
            reverse=True,
        )
        anos_default = [a for a in anos if int(a) >= 2023] or (anos[:3] if len(anos) >= 3 else anos)
        anos_sel = st.multiselect("Ano (da proposição)", options=anos, default=anos_default, key="anos_tab6")

    with cT:
        tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
        tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos, key="tipos_tab6")

    df_base = df_aut.copy()
    if anos_sel:
        df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
    if tipos_sel:
        df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()

    if df_base.empty:
        st.info("Nenhuma proposição encontrada com os filtros selecionados.")
        return

    st.markdown("---")

    # ----------------------------------------------------------
    # 5. CARREGAR STATUS — AUTOMÁTICO
    # ----------------------------------------------------------
    df_status = st.session_state["df_status6_cache"].copy()

    if df_status.empty:
        n_props = min(LIMITE_PROPOSICOES, len(df_base))
        with st.spinner(f"Carregando status de {n_props} proposições…"):
            ids_list = df_base["id"].astype(str).head(n_props).tolist()
            status_map = provider.build_proposicoes_status_map(ids_list)
            df_status = provider.enrich_proposicoes_with_status(
                df_base.head(n_props), status_map
            )

            # ----- UNIFICAÇÃO DE SITUAÇÕES -----
            if "Situação atual" in df_status.columns:
                df_status["Situação atual"] = df_status["Situação atual"].replace({
                    "Aguardando Devolução de Relator(a) que deixou de ser Membro": "Aguardando Designação de Relator(a)",
                    "Aguardando Apreciação pelo Senado Federal": "Apreciação pelo Senado Federal",
                })
                # Relator = "Aguardando" quando aguardando designação
                mask_aguard = df_status["Situação atual"].str.contains(
                    "Aguardando Designação de Relator", case=False, na=False
                )
                if "Relator(a)" in df_status.columns:
                    df_status.loc[mask_aguard, "Relator(a)"] = "Aguardando"

            # Colunas extras (provider pode não adicioná-las)
            if "Data do status (raw)" in df_status.columns:
                dt = pd.to_datetime(df_status["Data do status (raw)"], errors="coerce")
                if "AnoStatus" not in df_status.columns:
                    df_status["AnoStatus"] = dt.dt.year
                if "MesStatus" not in df_status.columns:
                    df_status["MesStatus"] = dt.dt.month
            if "Tema" not in df_status.columns and "ementa" in df_status.columns:
                df_status["Tema"] = df_status["ementa"].apply(_categorizar_tema)
            if "Sinal" not in df_status.columns and "Parado (dias)" in df_status.columns:
                df_status["Sinal"] = df_status["Parado (dias)"].apply(_sinal_alerta)

            st.session_state["df_status6_cache"] = df_status
            st.caption(f"✅ Status carregado para {len(df_status)} proposições")

    if df_status.empty:
        st.info("Nenhum dado de status disponível.")
        return

    # ----------------------------------------------------------
    # 6. FILTROS MULTI-NÍVEL
    # ----------------------------------------------------------
    st.markdown("##### 🔍 Filtros Multi-nível")

    dynamic_status = (
        [s for s in df_status["Situação atual"].dropna().unique().tolist() if str(s).strip()]
        if "Situação atual" in df_status.columns else []
    )
    status_opts = _merge_status_options(dynamic_status)

    org_opts = sorted(
        [o for o in df_status["Órgão (sigla)"].dropna().unique().tolist() if str(o).strip()]
    ) if "Órgão (sigla)" in df_status.columns else []

    ano_status_opts = sorted(
        [int(a) for a in df_status["AnoStatus"].dropna().unique().tolist() if pd.notna(a)], reverse=True,
    ) if "AnoStatus" in df_status.columns else []

    mes_status_opts = sorted(
        [int(m) for m in df_status["MesStatus"].dropna().unique().tolist() if pd.notna(m)]
    ) if "MesStatus" in df_status.columns else []

    tema_opts = sorted(
        [t for t in df_status["Tema"].dropna().unique().tolist() if str(t).strip()]
    ) if "Tema" in df_status.columns else []

    relator_opts = sorted(
        [r for r in df_status["Relator(a)"].dropna().unique().tolist()
         if str(r).strip() and str(r).strip() != "—"]
    ) if "Relator(a)" in df_status.columns else []

    default_status_sel = (
        [st.session_state["status_click_sel"]]
        if st.session_state.get("status_click_sel") else []
    )

    f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])
    with f1:
        status_sel = st.multiselect("Situação Atual", options=status_opts, default=default_status_sel, key="status_sel_tab6")
    with f2:
        org_sel = st.multiselect("Órgão (sigla)", options=org_opts, default=[], key="org_sel_tab6")
    with f3:
        ano_status_sel = st.multiselect("Ano (do status)", options=ano_status_opts, default=[], key="ano_status_sel_tab6")
    with f4:
        mes_labels = [f"{m:02d}-{MESES_PT.get(m, '')}" for m in mes_status_opts]
        mes_map = {f"{m:02d}-{MESES_PT.get(m, '')}": m for m in mes_status_opts}
        mes_sel_labels = st.multiselect("Mês (do status)", options=mes_labels, default=[], key="mes_sel_tab6")
        mes_status_sel = [mes_map[x] for x in mes_sel_labels if x in mes_map]

    f5, f6, f7 = st.columns([1.2, 1.2, 1.6])
    with f5:
        tema_sel = st.multiselect("Tema", options=tema_opts, default=[], key="tema_sel_tab6")
    with f6:
        relator_sel = st.multiselect("Relator(a)", options=relator_opts, default=[], key="relator_sel_tab6")
    with f7:
        palavra_filtro = st.text_input(
            "Palavra-chave na ementa",
            placeholder="Digite para filtrar…",
            help="Filtra proposições que contenham esta palavra na ementa",
            key="palavra_filtro_tab6",
        )

    if st.button("✖ Limpar filtro por clique", key="limpar_click_tab6"):
        st.session_state.pop("status_click_sel", None)

    # ----------------------------------------------------------
    # 7. APLICAR FILTROS
    # ----------------------------------------------------------
    df_fil = df_status.copy()
    if status_sel:
        df_fil = df_fil[df_fil["Situação atual"].isin(status_sel)]
    if org_sel:
        df_fil = df_fil[df_fil["Órgão (sigla)"].isin(org_sel)]
    if ano_status_sel:
        df_fil = df_fil[df_fil["AnoStatus"].isin(ano_status_sel)]
    if mes_status_sel:
        df_fil = df_fil[df_fil["MesStatus"].isin(mes_status_sel)]
    if tema_sel and "Tema" in df_fil.columns:
        df_fil = df_fil[df_fil["Tema"].isin(tema_sel)]
    if relator_sel and "Relator(a)" in df_fil.columns:
        df_fil = df_fil[df_fil["Relator(a)"].isin(relator_sel)]
    if palavra_filtro.strip():
        pn = normalize_text(palavra_filtro)
        df_fil = df_fil[df_fil["ementa"].apply(lambda x: pn in normalize_text(str(x)))]

    df_fil = df_fil.copy()

    if df_fil.empty:
        st.info("Nenhuma proposição encontrada com os filtros aplicados.")
        return

    if "Parado (dias)" in df_fil.columns and "Parado há (dias)" not in df_fil.columns:
        df_fil["Parado há (dias)"] = df_fil["Parado (dias)"]

    st.markdown("---")

    # ----------------------------------------------------------
    # 8. VISÃO EXECUTIVA
    # ----------------------------------------------------------
    with st.expander("🎯 Visão Executiva (Deputada / Chefia / Assessoria)", expanded=True):
        _render_resumo_executivo(df_fil)
        _render_atencao_deputada(df_fil)
        _render_prioridades_gabinete(df_fil)

    # ----------------------------------------------------------
    # 9. GRÁFICOS
    # ----------------------------------------------------------
    st.markdown("#### 📈 Análise Visual")
    with st.expander("📊 Gráficos e Análises", expanded=True):
        g1, g2 = st.columns(2)
        with g1:
            _graf_situacao(df_fil)
        with g2:
            _graf_tema(df_fil)
        g3, g4 = st.columns(2)
        with g3:
            _graf_tipo(df_fil)
        with g4:
            _graf_orgao(df_fil)
        _graf_mensal(df_fil)

    st.markdown("---")

    # ----------------------------------------------------------
    # 10. TABELA PRINCIPAL
    # ----------------------------------------------------------
    df_tbl = df_fil.copy()
    df_tbl["Parado há"] = df_tbl["Parado (dias)"].apply(
        lambda x: f"{int(x)} dias" if isinstance(x, (int, float)) and pd.notna(x) else "—"
    )
    if "LinkTramitacao" not in df_tbl.columns:
        df_tbl["LinkTramitacao"] = df_tbl["id"].astype(str).apply(camara_link_tramitacao)

    df_tbl = df_tbl.rename(columns={
        "Proposicao": "Proposição",
        "siglaTipo": "Tipo",
        "ano": "Ano",
        "ementa": "Ementa",
        "Data do status": "Última tramitação",
    })

    show_cols = [
        "Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)",
        "Relator(a)", "Última tramitação", "Sinal", "Parado há", "Tema",
        "id", "LinkTramitacao", "LinkRelator", "Ementa",
    ]
    for c in show_cols:
        if c not in df_tbl.columns:
            df_tbl[c] = ""

    # Contagem por situação
    df_counts = (
        df_fil.assign(_s=df_fil["Situação atual"].fillna("-").replace("", "-"))
        .groupby("_s", as_index=False).size()
        .rename(columns={"_s": "Situação atual", "size": "Qtde"})
        .sort_values("Qtde", ascending=False)
    )

    cC1, cC2 = st.columns([1.0, 2.0])
    with cC1:
        st.markdown("**Contagem por Situação atual**")
        st.dataframe(df_counts, hide_index=True, use_container_width=True)

    with cC2:
        st.markdown("**Lista filtrada (mais recente primeiro)**")
        if "DataStatus_dt" in df_tbl.columns:
            df_tbl = df_tbl.sort_values("DataStatus_dt", ascending=False)

        col_cfg = {
            "LinkTramitacao": st.column_config.LinkColumn("🏛️ Câmara", display_text="abrir"),
            "LinkRelator": st.column_config.LinkColumn("Link Relator", display_text="ver"),
            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            "Última tramitação": st.column_config.TextColumn("Última tramitação", width="small"),
            "Relator(a)": st.column_config.TextColumn("Relator(a)", width="medium"),
        }

        sel = st.dataframe(
            df_tbl[show_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=col_cfg,
            key="df_status_tab6",
        )

    # -- Seção RICs (se houver) --
    df_rics = df_tbl[df_tbl["Tipo"] == "RIC"].copy() if "Tipo" in df_tbl.columns else pd.DataFrame()
    if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
        with st.expander("📋 Detalhes de RICs (Requerimentos de Informação)", expanded=False):
            rics_cols = [c for c in [
                "Proposição", "Ementa", "RIC_Ministerio", "RIC_StatusResposta",
                "RIC_PrazoFim", "RIC_DiasRestantes", "Última tramitação", "LinkTramitacao",
            ] if c in df_rics.columns]
            st.dataframe(
                df_rics[rics_cols].rename(columns={
                    "RIC_Ministerio": "Ministério",
                    "RIC_StatusResposta": "Status Resposta",
                    "RIC_PrazoFim": "Prazo Final",
                    "RIC_DiasRestantes": "Dias Restantes",
                }),
                use_container_width=True, hide_index=True,
                column_config={"LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir")},
            )

    # ----------------------------------------------------------
    # 11. DOWNLOADS
    # ----------------------------------------------------------
    cx, cp = st.columns(2)
    with cx:
        try:
            bx, mx, ex = to_xlsx_bytes(df_tbl[show_cols], "Materias_Situacao")
            st.download_button("⬇️ XLSX", data=bx, file_name=f"materias_por_situacao_atual.{ex}", mime=mx, key="dl_xlsx_tab6")
        except Exception as e:
            st.error(f"Erro ao gerar XLSX: {e}")
    with cp:
        try:
            bp, mp, ep = to_pdf_bytes(df_tbl[show_cols], "Matérias por Situação")
            st.download_button("⬇️ PDF", data=bp, file_name=f"materias_por_situacao_atual.{ep}", mime=mp, key="dl_pdf_tab6")
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

    # ----------------------------------------------------------
    # 12. DETALHES DA PROPOSIÇÃO SELECIONADA
    # ----------------------------------------------------------
    selected_id = None
    try:
        if sel and isinstance(sel, dict) and sel.get("selection", {}).get("rows"):
            row_idx = sel["selection"]["rows"][0]
            selected_id = str(df_tbl.iloc[row_idx]["id"])
    except Exception:
        pass

    st.markdown("---")
    st.markdown("#### 📋 Detalhes da Proposição Selecionada")

    if not selected_id:
        st.info("Clique em uma proposição acima para ver detalhes completos.")
    else:
        exibir_detalhes_proposicao_func(selected_id, key_prefix="tab6")
