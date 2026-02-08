# modules/tabs/tab8_apensados.py
# v2 08/02/2025 17:30 (Brasília)
"""
Tab 8 – Projetos Apensados (ex-Aba 9)

Funcionalidades:
- Carregamento automático dos projetos apensados
- Métricas: total, aguardando parecer, aguardando relator, pronta p/ pauta
- Tabela interativa (single-row select) com dados do PL RAIZ
- Expander com detalhes completos: autor, foto, cadeia, tramitações
- Downloads XLSX e PDF
- Integração com exibir_detalhes_proposicao para ver tramitações do PL Raiz

Dados pesados (detecção de apensados) importados do monólito.
UI renderizada neste módulo.

Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta
"""
from __future__ import annotations

from typing import Callable
import datetime

import streamlit as st
import pandas as pd

from core.utils import (
    to_xlsx_bytes,
    to_pdf_bytes,
)

# Funções pesadas — permanecem no monólito até eventual migração p/ data_provider
from monitor_sistema_jz import (
    buscar_projetos_apensados_automatico,
    fetch_relator_atual,
    MAPEAMENTO_APENSADOS,
    PROPOSICOES_FALTANTES_API,
)


# ============================================================
# HELPERS LOCAIS
# ============================================================

def _parse_data_br(data_str: str) -> datetime.datetime:
    """Converte DD/MM/YYYY → datetime (para ordenação)."""
    try:
        if data_str and data_str != "—":
            return datetime.datetime.strptime(data_str, "%d/%m/%Y")
    except Exception:
        pass
    return datetime.datetime.min


def _format_parado(dias: int) -> str:
    """Formata dias parado — sempre em dias exatos."""
    if dias < 0:
        return "—"
    if dias == 0:
        return "Hoje"
    if dias == 1:
        return "1 dia"
    return f"{dias} dias"


def _sinal_alerta(dias: int) -> str:
    """
    Sinal de alerta padronizado:
    🚨 ≤2d  |  ⚠️ ≤5d  |  🔔 ≤15d  |  (vazio) >15d
    """
    if dias < 0:
        return "—"
    if dias <= 2:
        return "🚨"
    if dias <= 5:
        return "⚠️"
    if dias <= 15:
        return "🔔"
    return ""


# ============================================================
# ██  RENDER PRINCIPAL
# ============================================================

def render_tab8(
    provider,
    exibir_detalhes_proposicao_func: Callable,
    id_deputada: int,
) -> None:
    """
    Aba 8 – Projetos Apensados.

    Args
    ----
    provider : DataProvider (não usado diretamente, mas mantém assinatura padrão)
    exibir_detalhes_proposicao_func : callback para detalhar proposição
    id_deputada : ID da deputada na API da Câmara
    """

    st.title("📎 Projetos Apensados")

    st.markdown("""
    ### 🔗 Monitoramento de Projetos Tramitando em Conjunto

    Esta aba exibe os **projetos da Dep. Júlia Zanatta que estão apensados** a outros projetos.

    **O que significa "apensado"?**
    > Quando um PL é apensado a outro, ele **para de tramitar sozinho**.
    > As movimentações passam a ocorrer no **PL principal** (ou no PL raiz da cadeia).
    > Por isso, monitoramos o PL raiz para acompanhar o andamento real.

    ---
    """)

    # ----------------------------------------------------------
    # CACHE
    # ----------------------------------------------------------
    if "projetos_apensados_cache" not in st.session_state:
        st.session_state["projetos_apensados_cache"] = None

    cI, cR = st.columns([3, 1])
    with cI:
        st.caption("💡 **Projetos apensados carregam automaticamente.** Clique em 'Atualizar' para forçar recarga.")
    with cR:
        btn_atualizar = st.button("🔄 Atualizar", key="btn_refresh_apensados")

    # ----------------------------------------------------------
    # 1. CARREGAR (automático)
    # ----------------------------------------------------------
    precisa_carregar = st.session_state["projetos_apensados_cache"] is None or btn_atualizar

    if precisa_carregar:
        with st.spinner("🔍 Detectando projetos apensados e buscando cadeia completa..."):
            raw = buscar_projetos_apensados_automatico(id_deputada)

            if not raw:
                st.session_state["projetos_apensados_cache"] = []
            else:
                # Ordenar do mais recente para o mais antigo
                ordenados = sorted(
                    raw,
                    key=lambda x: _parse_data_br(x.get("data_ultima_mov", "—")),
                    reverse=True,
                )
                st.session_state["projetos_apensados_cache"] = ordenados

                if btn_atualizar:
                    st.success(f"✅ {len(ordenados)} projetos apensados atualizados!")

    projetos = st.session_state.get("projetos_apensados_cache") or []

    if not projetos:
        st.warning("Nenhum projeto apensado encontrado ou erro na detecção.")
        st.info("💡 Isso pode significar que nenhum projeto da deputada está apensado no momento.")
        return

    # ----------------------------------------------------------
    # 2. MÉTRICAS
    # ----------------------------------------------------------
    st.markdown("### 📊 Resumo")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Total de PLs Apensados", len(projetos))
    with c2:
        ap_parecer = sum(1 for p in projetos if "Aguardando Parecer" in p.get("situacao_raiz", ""))
        st.metric("Aguardando Parecer", ap_parecer)
    with c3:
        ap_relator = sum(1 for p in projetos if "Designação de Relator" in p.get("situacao_raiz", ""))
        st.metric("Aguardando Relator", ap_relator)
    with c4:
        pronta = sum(1 for p in projetos if "Pronta para Pauta" in p.get("situacao_raiz", ""))
        st.metric("Pronta para Pauta", pronta, delta="⚠️ Atenção!" if pronta > 0 else None)

    st.markdown("---")

    # ----------------------------------------------------------
    # 3. TABELA PRINCIPAL (single-row select)
    # ----------------------------------------------------------
    st.markdown("### 📋 Projetos Apensados Detectados")
    st.caption("👆 Clique em um projeto para ver detalhes completos")

    rows = []
    for p in projetos:
        dias = p.get("dias_parado", -1)
        cadeia = p.get("cadeia_apensamento", [])
        cadeia_str = (
            " → ".join(c.get("pl", "") for c in cadeia)
            if cadeia and len(cadeia) > 1
            else p.get("pl_principal", "")
        )

        rows.append({
            "Sinal": _sinal_alerta(dias),
            "PL Zanatta": p.get("pl_zanatta", ""),
            "PL Raiz": p.get("pl_raiz", ""),
            "Situação": (p.get("situacao_raiz", ""))[:50],
            "Órgão": p.get("orgao_raiz", ""),
            "Relator": (p.get("relator_raiz", "—"))[:30],
            "Parado há": _format_parado(dias),
            "Última Mov.": p.get("data_ultima_mov", "—"),
            "id_raiz": p.get("id_raiz", ""),
            "id_zanatta": p.get("id_zanatta", ""),
            "Cadeia": cadeia_str,
        })

    df_tbl = pd.DataFrame(rows)

    show_cols = [
        "Sinal", "PL Zanatta", "PL Raiz", "Situação",
        "Órgão", "Relator", "Parado há", "Última Mov.",
    ]

    sel = st.dataframe(
        df_tbl[show_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=400,
        column_config={
            "Sinal": st.column_config.TextColumn("Sinal", width="small"),
            "Relator": st.column_config.TextColumn("Relator", width="medium"),
            "Parado há": st.column_config.TextColumn("Parado há", width="small"),
        },
        key="df_apensados_tab8",
    )

    # Legenda
    st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")

    # ----------------------------------------------------------
    # 4. DETALHES DO PROJETO SELECIONADO
    # ----------------------------------------------------------
    selected_idx = None
    try:
        if sel and isinstance(sel, dict) and sel.get("selection", {}).get("rows"):
            selected_idx = sel["selection"]["rows"][0]
    except Exception:
        pass

    st.markdown("---")
    st.markdown("### 🔍 Detalhes do Projeto Selecionado")

    if selected_idx is None:
        st.info("👆 **Selecione um projeto acima** para ver detalhes completos e tramitações")
    else:
        ap = projetos[selected_idx]
        situacao_raiz = ap.get("situacao_raiz", "")
        dias = ap.get("dias_parado", 0)
        parado_str = _format_parado(dias)
        sinal = _sinal_alerta(dias)

        # Cadeia
        cadeia = ap.get("cadeia_apensamento", [])
        if cadeia and len(cadeia) > 1:
            cadeia_resumo = f" → ... → {ap.get('pl_raiz', '')}"
        else:
            cadeia_resumo = f" → {ap.get('pl_principal', '')}"

        st.markdown(f"#### {sinal} {ap['pl_zanatta']}{cadeia_resumo} | ⏱️ {parado_str}")

        # Cadeia completa
        if cadeia and len(cadeia) > 1:
            cadeia_str = " → ".join(c.get("pl", "") for c in cadeia)
            st.info(f"📎 **Cadeia de apensamento:** {ap['pl_zanatta']} → {cadeia_str}")

        st.markdown("---")

        # Layout: 4 colunas (foto autor | PL Zanatta | PL Raiz | foto relator)
        col_foto, col_zanatta, col_raiz, col_foto_rel = st.columns([1, 2, 2, 1])

        with col_foto:
            foto_url = ap.get("foto_autor", "")
            if foto_url:
                st.image(foto_url, width=100)
            st.caption(f"**{ap.get('autor_principal', '—')}**")
            st.caption("Autor do PL Principal")

        with col_zanatta:
            st.markdown("**📌 Projeto da Deputada**")
            st.markdown(f"### {ap['pl_zanatta']}")
            em_z = ap.get("ementa_zanatta", "")
            st.caption(em_z[:150] + "..." if len(em_z) > 150 else em_z)
            id_z = ap.get("id_zanatta", "")
            if id_z:
                st.markdown(
                    f"[🔗 Ver PL](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_z})"
                )

        with col_raiz:
            st.markdown("**🎯 PL RAIZ (onde tramita)**")
            st.markdown(f"### {ap.get('pl_raiz', ap.get('pl_principal', ''))}")
            st.markdown(f"🏛️ **Órgão:** {ap.get('orgao_raiz', '—')}")
            st.markdown(f"👨‍⚖️ **Relator:** {ap.get('relator_raiz', '—')}")
            st.markdown(f"📅 **Última mov.:** {ap.get('data_ultima_mov', '—')}")
            st.markdown(f"⏱️ **Parado há:** {parado_str}")
            id_r = ap.get("id_raiz", "")
            if id_r:
                st.markdown(
                    f"[🔗 Ver PL Raiz](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_r})"
                )

        with col_foto_rel:
            relator_nome = ap.get("relator_raiz", "—")
            if relator_nome and relator_nome != "—":
                try:
                    rel_dict = fetch_relator_atual(ap.get("id_raiz", ""))
                    # O dict retorna "id_deputado" (não "id")
                    rel_id = None
                    if rel_dict:
                        rel_id = (
                            rel_dict.get("id_deputado")
                            or rel_dict.get("id")
                            or rel_dict.get("idDeputado")
                            or ""
                        )
                    if rel_id:
                        foto_rel_url = f"https://www.camara.leg.br/internet/deputado/bandep/{rel_id}.jpg"
                        st.image(foto_rel_url, width=100)
                        st.caption("**Relator(a)**")
                    else:
                        st.caption("Relator(a)")
                except Exception:
                    st.caption("Relator(a)")
            else:
                st.markdown("*Sem relator*")
                st.caption("designado")

        st.markdown("---")

        # Situação + ementa do PL Raiz
        st.markdown(f"**📊 Situação atual (PL Raiz):** {situacao_raiz}")
        ementa_raiz = ap.get("ementa_raiz", ap.get("ementa_principal", "—"))
        st.markdown(f"**📝 Ementa:** {ementa_raiz[:300]}...")

        # Botão para carregar tramitações do PL RAIZ
        key_unica = ap.get("id_zanatta", "") or ap.get("pl_zanatta", "").replace(" ", "_").replace("/", "_")
        if st.button("🔄 Ver tramitações do PL Raiz", key=f"btn_tram_{key_unica}"):
            exibir_detalhes_proposicao_func(ap.get("id_raiz", ""), key_prefix=f"apensado_{key_unica}")

    st.markdown("---")

    # ----------------------------------------------------------
    # 5. DOWNLOADS
    # ----------------------------------------------------------
    st.markdown("### ⬇️ Downloads")

    df_dl = pd.DataFrame(projetos)
    df_dl = df_dl.rename(columns={
        "pl_zanatta": "PL Zanatta",
        "pl_principal": "PL Principal",
        "pl_raiz": "PL Raiz",
        "autor_principal": "Autor Principal",
        "situacao_raiz": "Situação (Raiz)",
        "orgao_raiz": "Órgão (Raiz)",
        "relator_raiz": "Relator (Raiz)",
        "ementa_zanatta": "Ementa (Zanatta)",
        "ementa_principal": "Ementa (Principal)",
        "data_ultima_mov": "Última Movimentação",
        "dias_parado": "Dias Parado",
    })

    cd1, cd2 = st.columns(2)
    with cd1:
        try:
            bx, mx, ex = to_xlsx_bytes(df_dl, "Projetos_Apensados")
            st.download_button(
                "⬇️ XLSX", data=bx,
                file_name=f"projetos_apensados_zanatta.{ex}",
                mime=mx, key="dl_xlsx_tab8",
            )
        except Exception as e:
            st.error(f"Erro XLSX: {e}")

    with cd2:
        try:
            bp, mp, ep = to_pdf_bytes(df_dl, "Projetos Apensados - Dep. Julia Zanatta")
            st.download_button(
                "⬇️ PDF", data=bp,
                file_name=f"projetos_apensados_zanatta.{ep}",
                mime=mp, key="dl_pdf_tab8",
            )
        except Exception as e:
            st.caption(f"PDF indisponível: {e}")

    st.markdown("---")

    # Info/Estatísticas
    st.info(f"""
    **📊 Estatísticas da detecção:**
    - Total de projetos apensados encontrados: **{len(projetos)}**
    - Mapeamentos no dicionário: **{len(MAPEAMENTO_APENSADOS)}**
    - Projetos no cadastro manual: **{len(PROPOSICOES_FALTANTES_API.get('220559', []))}**
    - Ordenação: **Do mais recente para o mais antigo**
    """)

    st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")
