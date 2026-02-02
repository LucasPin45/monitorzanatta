# modules/tabs/tab1_dashboard.py
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st
import pandas as pd
import datetime

import matplotlib.pyplot as plt

# Usa funções utilitárias já existentes no projeto
from core.utils.date_utils import get_brasilia_now
from core.config import DEPUTADA_ID_PADRAO



def render_tab1(provider) -> None:
    """
    Aba 1 - Dashboard Executivo
    Agora roda 100% fora do monólito (UI isolada).
    Depende apenas do provider para dados.
    """

    # ============================================================
    # PERFIL / HEADER
    # ============================================================
    perfil: Dict[str, Any] = provider.get_perfil_deputada() or {}
    nome_deputada = perfil.get("nome", "Júlia Zanatta")
    partido_deputada = perfil.get("partido", "PL")
    uf_deputada = perfil.get("uf", "SC")

    st.title("📊 Dashboard Executivo")

    st.markdown(f"### {nome_deputada}")
    st.markdown(f"**Partido:** {partido_deputada} | **UF:** {uf_deputada}")
    st.markdown(f"🕐 **Última atualização:** {get_brasilia_now().strftime('%d/%m/%Y às %H:%M:%S')}")
    st.markdown("---")

    # ============================================================
    # CARREGAMENTO (via DataProvider)
    # ============================================================
    # OBS: aqui precisamos do ID da deputada para buscar proposições reais.
    # Como o monólito ainda controla isso, vamos obter do session_state (já existe no app).
    # Se o seu projeto usa outro nome de chave, ajuste aqui.
    id_deputada = (
        st.session_state.get("ID_DEPUTADA")
        or st.session_state.get("id_deputada")
        or DEPUTADA_ID_PADRAO
    )


    col_info1, col_refresh1 = st.columns([3, 1])
    with col_info1:
        st.caption("💡 **Dashboard carrega automaticamente.** Clique em 'Atualizar' para forçar recarga.")
    with col_refresh1:
        btn_atualizar_aba1 = st.button("🔄 Atualizar", key="btn_refresh_aba1")

    props_autoria: List[Dict[str, Any]] = []

    if not id_deputada:
        st.warning("⚠️ ID da deputada não encontrado no session_state (ID_DEPUTADA / id_deputada).")
        st.info("Ajuste a chave no tab1_dashboard.py ou garanta que o monólito define o ID antes de renderizar.")
        return

    # Se clicou atualizar, limpa cache do Streamlit dessa execução
    # (sem mexer em implementação interna do provider)
    if btn_atualizar_aba1:
        try:
            st.cache_data.clear()
        except Exception:
            pass

    with st.spinner("📊 Carregando métricas do dashboard..."):
        try:
            # ✅ Agora NÃO usamos mais fetch_lista_proposicoes_autoria do monólito.
            props_autoria = provider.get_proposicoes_autoria(int(id_deputada)) or []
        except Exception as e:
            st.error(f"⚠️ Erro ao carregar proposições: {e}")
            props_autoria = []

    # ============================================================
    # CARDS DE MÉTRICAS (KPIs)
    # ============================================================
    st.markdown("### 📈 Visão Geral")

    col1, col2, col3, col4, col5 = st.columns(5)

    tipos_count = provider.contar_tipos(props_autoria)

    with col1:
        st.metric(
            label="📝 Proposições de Autoria",
            value=len(props_autoria),
            help="Total de proposições de autoria (todas)"
        )

    with col2:
        rics = tipos_count.get("RIC", 0)
        st.metric(
            label="📄 RICs",
            value=rics,
            help="Requerimentos de Informação"
        )

    with col3:
        pls = tipos_count.get("PL", 0) + tipos_count.get("PLP", 0)
        st.metric(
            label="📋 Projetos de Lei",
            value=pls,
            help="PL + PLP"
        )

    with col4:
        pareceres = tipos_count.get("PRL", 0)
        st.metric(
            label="📑 Pareceres",
            value=pareceres,
            help="Pareceres de Relatoria (PRL)"
        )

    with col5:
        tipos_outros = {k: v for k, v in tipos_count.items() if k not in ["RIC", "PL", "PLP", "PRL"]}
        outros = sum(tipos_outros.values())

        if tipos_outros:
            tipos_sorted = sorted(tipos_outros.items(), key=lambda x: x[1], reverse=True)[:5]
            tipos_desc = ", ".join([f"{k}({v})" for k, v in tipos_sorted])
            if len(tipos_outros) > 5:
                tipos_desc += f" e mais {len(tipos_outros) - 5} tipos"
            help_text = f"Inclui: {tipos_desc}"
        else:
            help_text = "Outros tipos de proposição"

        st.metric(
            label="📁 Outros",
            value=outros,
            help=help_text
        )

    with st.expander("📋 Ver todos os tipos de proposição", expanded=False):
        if tipos_count:
            df_tipos_detalhe = pd.DataFrame(
                sorted(tipos_count.items(), key=lambda x: x[1], reverse=True),
                columns=["Tipo", "Quantidade"]
            )
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                st.dataframe(df_tipos_detalhe, use_container_width=True, hide_index=True)
            with col_t2:
                st.markdown("**Legenda:**")
                st.caption("• **RIC** - Req. de Informação")
                st.caption("• **PL** - Projeto de Lei")
                st.caption("• **PLP** - Projeto de Lei Complementar")
                st.caption("• **PRL** - Parecer de Relatoria")
                st.caption("• **PEC** - Proposta de Emenda")
                st.caption("• **REQ** - Requerimento")
                st.caption("• **PDL** - Projeto de Decreto Legislativo")
                st.caption("• **RPD** - Req. regimentais internos")
        else:
            st.info("Nenhum tipo encontrado.")

    st.markdown("---")

    # ============================================================
    # GRÁFICOS RESUMIDOS
    # ============================================================
    st.markdown("### 📊 Análise Rápida")

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        if props_autoria and tipos_count:
            df_tipos = pd.DataFrame(list(tipos_count.items()), columns=["Tipo", "Quantidade"])
            df_tipos = df_tipos.sort_values("Quantidade", ascending=False)

            fig, ax = plt.subplots(figsize=(8, 5))
            ax.barh(df_tipos["Tipo"], df_tipos["Quantidade"])
            ax.set_xlabel("Quantidade")
            ax.set_title("Proposições por Tipo")
            ax.grid(axis="x", alpha=0.3)

            for i, v in enumerate(df_tipos["Quantidade"]):
                ax.text(v + 0.5, i, str(v), va="center")

            st.pyplot(fig)
            plt.close(fig)

    with col_graf2:
        if props_autoria:
            anos_count: Dict[str, int] = {}
            for p in props_autoria:
                ano = p.get("ano", "")
                if ano and str(ano).isdigit() and len(str(ano)) == 4:
                    anos_count[str(ano)] = anos_count.get(str(ano), 0) + 1

            if anos_count:
                df_anos = pd.DataFrame(list(anos_count.items()), columns=["Ano", "Quantidade"])
                df_anos = df_anos.sort_values("Ano", ascending=False)

                fig, ax = plt.subplots(figsize=(8, 5))
                ax.barh(df_anos["Ano"], df_anos["Quantidade"])
                ax.set_xlabel("Quantidade")
                ax.set_title("Proposições por Ano")
                ax.grid(axis="x", alpha=0.3)

                for i, v in enumerate(df_anos["Quantidade"]):
                    ax.text(v + 0.5, i, str(v), va="center")

                st.pyplot(fig)
                plt.close(fig)
            else:
                st.info("Nenhum ano válido encontrado.")

    st.markdown("---")

    # ============================================================
    # AÇÕES RÁPIDAS
    # ============================================================
    st.markdown("### ⚡ Ações Rápidas")

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("📅 Ver Pauta", use_container_width=True, key="btn_pauta_home"):
            st.session_state["aba_destino"] = "pauta"
            st.info("👉 Vá para a aba **2️⃣ Autoria & Relatoria na pauta**")

    with col_btn2:
        if st.button("🔍 Buscar Proposição", use_container_width=True, key="btn_buscar_home"):
            st.session_state["aba_destino"] = "buscar"
            st.info("👉 Vá para a aba **5️⃣ Buscar Proposição Específica**")

    with col_btn3:
        if st.button("📊 Ver Matérias", use_container_width=True, key="btn_materias_home"):
            st.session_state["aba_destino"] = "materias"
            st.info("👉 Vá para a aba **6️⃣ Matérias por situação atual**")

    with col_btn4:
        if st.button("📝 Ver RICs", use_container_width=True, key="btn_rics_home"):
            st.session_state["aba_destino"] = "rics"
            st.info("👉 Vá para a aba **7️⃣ RICs (Requerimentos)**")

    if st.session_state.get("aba_destino"):
        destinos = {
            "pauta": "2️⃣ Autoria & Relatoria na pauta",
            "buscar": "5️⃣ Buscar Proposição Específica",
            "materias": "6️⃣ Matérias por situação atual",
            "rics": "7️⃣ RICs (Requerimentos)",
        }
        destino = destinos.get(st.session_state["aba_destino"], "")
        if destino:
            st.success(f"👆 Clique na aba **{destino}** acima para acessar")
            st.session_state["aba_destino"] = None

    st.markdown("---")

    # ============================================================
    # TELEGRAM
    # ============================================================
    st.markdown("### 📱 Receba Atualizações no Telegram")

    col_tg1, col_tg2 = st.columns([3, 1])

    with col_tg1:
        st.info(
            "🔔 **Entre no grupo do Monitor Parlamentar no Telegram!**\n\n"
            "Receba notificações automáticas sobre:\n"
            "- Novas tramitações de proposições da Dep. Júlia Zanatta\n"
            "- Movimentações em projetos de lei\n"
            "- Atualizações em requerimentos de informação (RICs)\n"
        )

    with col_tg2:
        st.markdown("")
        st.link_button(
            "📲 Entrar no Grupo",
            url="https://t.me/+LJUCm1ZwxoJkNDkx",
            type="primary",
            use_container_width=True
        )

    st.markdown("---")

    # Rodapé simples
    st.caption("📊 Dados: API Câmara dos Deputados | Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta")
