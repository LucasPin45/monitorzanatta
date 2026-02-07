# modules/tabs/tab4_comissoes.py
from __future__ import annotations

from typing import Any, Dict, List
import datetime

import streamlit as st
import pandas as pd

# Funções utilitárias
from core.utils import (
    to_xlsx_bytes,
    to_pdf_comissoes_estrategicas,
)

# Constantes do projeto
from core.config import COMISSOES_ESTRATEGICAS_PADRAO


def render_tab4(provider, id_deputada) -> None:
    """
    Aba 4 - Comissões Estratégicas
    Monitora eventos nas comissões estratégicas de interesse.
    
    Args:
        provider: DataProvider instance
        id_deputada: ID da deputada na API da Câmara
    """
    
    st.subheader("Comissões estratégicas")
    
    st.info(
        "💡 **Dica:** Acompanhe eventos nas comissões em que a deputada é membro. "
        "Configure as siglas das comissões de interesse (ex: CDC, CCJC, CREDN)."
    )
    
    # ============================================================
    # CONTROLES: PERÍODO, COMISSÕES E BOTÃO
    # ============================================================
    col_data_t4, col_com_t4 = st.columns([1, 1])
    
    with col_data_t4:
        hoje = datetime.date.today()
        default_range = st.session_state.get(
            "date_range_tab4",
            (hoje, hoje + datetime.timedelta(days=7))
        )
        
        date_range_tab4 = st.date_input(
            "📅 Período de busca",
            value=default_range,
            format="DD/MM/YYYY",
            key="date_range_tab4"
        )
        
        # Validar range
        if isinstance(date_range_tab4, tuple) and len(date_range_tab4) == 2:
            dt_inicio_t4, dt_fim_t4 = date_range_tab4
        else:
            dt_inicio_t4 = hoje
            dt_fim_t4 = hoje + datetime.timedelta(days=7)
    
    with col_com_t4:
        # Obter comissões do session_state ou usar padrão
        comissoes_salvas = st.session_state.get("comissoes_t4", "")
        
        # Se estiver vazio, usar padrão
        if not comissoes_salvas or not comissoes_salvas.strip():
            comissoes_default = ", ".join(COMISSOES_ESTRATEGICAS_PADRAO)
        else:
            comissoes_default = comissoes_salvas
        
        comissoes_str_t4 = st.text_input(
            "🏛️ Comissões estratégicas (siglas separadas por vírgula)",
            value=comissoes_default,
            key="comissoes_input_t4"
        )
        
        # Processar comissões
        comissoes_t4 = [
            c.strip().upper() 
            for c in (comissoes_str_t4 or "").split(",") 
            if c.strip()
        ]
        
        # Salvar no session_state
        st.session_state["comissoes_t4"] = comissoes_str_t4
    
    # Botão de carregar
    run_scan_tab4 = st.button(
        "▶️ Carregar pauta das comissões",
        type="primary",
        key="run_scan_tab4"
    )
    
    # ============================================================
    # CARREGAMENTO DE DADOS
    # ============================================================
    if run_scan_tab4:
        # Obter perfil da deputada
        perfil = provider.get_perfil_deputada() or {}
        
        if not id_deputada:
            st.error("❌ ID da deputada não encontrado.")
            return
        
        nome_deputada = perfil.get("nome", "Júlia Zanatta")
        partido_deputada = perfil.get("partido", "PL")
        uf_deputada = perfil.get("uf", "SC")
        
        with st.spinner("🔄 Carregando eventos..."):
            eventos = provider.get_eventos(dt_inicio_t4, dt_fim_t4)
        
        with st.spinner("🔄 Carregando proposições de autoria..."):
            ids_autoria = provider.get_ids_autoria_deputada(int(id_deputada))
        
        with st.spinner("🔍 Escaneando pautas das comissões..."):
            df = provider.escanear_eventos_comissoes(
                eventos=eventos,
                nome_deputada=nome_deputada,
                partido_deputada=partido_deputada,
                uf_deputada=uf_deputada,
                comissoes_estrategicas=comissoes_t4,
                ids_autoria_deputada=ids_autoria,
            )
        
        # Salvar no session_state
        st.session_state["df_scan_tab4"] = df
        st.session_state["dt_range_tab4_saved"] = (dt_inicio_t4, dt_fim_t4)
        
        st.success(f"✅ {len(df)} eventos carregados com sucesso!")
        st.rerun()
    
    # ============================================================
    # EXIBIÇÃO DOS DADOS
    # ============================================================
    df = st.session_state.get("df_scan_tab4", pd.DataFrame())
    dt_range_saved = st.session_state.get("dt_range_tab4_saved")
    
    # Determinar período
    if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
        dt_inicio, dt_fim = dt_inicio_t4, dt_fim_t4
    else:
        dt_inicio, dt_fim = dt_range_saved
    
    if not df.empty:
        st.caption(f"📅 Período: {dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}")
    
    if df.empty:
        st.info("👆 Selecione o período, configure as comissões e clique em **Carregar pauta**.")
        return
    
    # ============================================================
    # FILTRAR APENAS COMISSÕES ESTRATÉGICAS
    # ============================================================
    df_com = df[df["comissao_estrategica"]].copy()
    
    if df_com.empty:
        st.warning("⚠️ Nenhum evento encontrado nas comissões estratégicas configuradas no período.")
        return
    
    # ============================================================
    # PREPARAR VISUALIZAÇÃO
    # ============================================================
    view = df_com[
        ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
         "proposicoes_autoria", "proposicoes_relatoria", "palavras_chave_encontradas", 
         "descricao_evento"]
    ].copy()
    
    # Formatar data
    view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")
    
    # ============================================================
    # MÉTRICAS
    # ============================================================
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric("📊 Total de Eventos", len(view))
    
    with col_m2:
        comissoes_unicas = df_com["orgao_sigla"].nunique()
        st.metric("🏛️ Comissões", comissoes_unicas)
    
    with col_m3:
        eventos_autoria = df_com["tem_autoria_deputada"].sum()
        st.metric("✍️ Com Autoria", eventos_autoria)
    
    st.markdown("---")
    
    # ============================================================
    # TABELA PRINCIPAL
    # ============================================================
    st.markdown("### 📋 Eventos nas Comissões Estratégicas")
    
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "data": st.column_config.TextColumn("Data", width="small"),
            "hora": st.column_config.TextColumn("Hora", width="small"),
            "orgao_sigla": st.column_config.TextColumn("Comissão", width="small"),
            "orgao_nome": st.column_config.TextColumn("Nome da Comissão", width="medium"),
            "tipo_evento": st.column_config.TextColumn("Tipo", width="medium"),
            "proposicoes_autoria": st.column_config.TextColumn("Autoria", width="large"),
            "proposicoes_relatoria": st.column_config.TextColumn("Relatoria", width="large"),
            "palavras_chave_encontradas": st.column_config.TextColumn("Palavras-chave", width="medium"),
            "descricao_evento": st.column_config.TextColumn("Descrição", width="large"),
        },
        height=400
    )
    
    # ============================================================
    # DOWNLOADS
    # ============================================================
    st.markdown("### ⬇️ Exportar Dados")
    
    col_x3, col_p3 = st.columns(2)
    
    with col_x3:
        try:
            data_bytes, mime, ext = to_xlsx_bytes(view, "ComissoesEstrategicas_Pauta")
            st.download_button(
                label="📥 Download XLSX",
                data=data_bytes,
                file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{ext}",
                mime=mime,
                use_container_width=True,
                key="download_com_xlsx"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar XLSX: {e}")
    
    with col_p3:
        try:
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_comissoes_estrategicas(view)
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                mime=pdf_mime,
                use_container_width=True,
                key="download_com_pdf"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar PDF: {e}")
    
    # ============================================================
    # RODAPÉ
    # ============================================================
    st.markdown("---")
    st.caption(
        "📊 Dados: API Câmara dos Deputados | "
        "Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta"
    )
