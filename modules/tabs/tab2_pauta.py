# modules/tabs/tab2_pauta.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import datetime

import streamlit as st
import pandas as pd

# Funções utilitárias já existentes no projeto
from core.utils import (
    format_sigla_num_ano,
    to_xlsx_bytes,
    to_pdf_autoria_relatoria,
)


def render_tab2(provider, exibir_detalhes_proposicao_func) -> None:
    """
    Aba 2 - Autoria & Relatoria na pauta
    Agora roda 100% fora do monólito (UI isolada).
    Depende apenas do provider para dados.
    
    Args:
        provider: DataProvider instance
        exibir_detalhes_proposicao_func: Função para exibir detalhes de uma proposição
    """
    
    st.subheader("Autoria & Relatoria na pauta")
    
    st.info(
        "💡 **Dica:** Selecione o período da semana e clique em **Carregar pauta** "
        "para ver as proposições de sua autoria ou relatoria que estão na pauta de votações."
    )
    
    # ============================================================
    # CONTROLES: PERÍODO E BOTÃO DE CARREGAR
    # ============================================================
    col_periodo, col_btn = st.columns([3, 1])
    
    with col_periodo:
        hoje = datetime.date.today()
        default_range = st.session_state.get(
            "date_range_tab2", 
            (hoje, hoje + datetime.timedelta(days=7))
        )
        
        date_range_tab2 = st.date_input(
            "📅 Período de busca", 
            value=default_range,
            format="DD/MM/YYYY",
            key="date_range_tab2"
        )
        
        # Validar range
        if isinstance(date_range_tab2, tuple) and len(date_range_tab2) == 2:
            dt_inicio_t2, dt_fim_t2 = date_range_tab2
        else:
            dt_inicio_t2 = hoje
            dt_fim_t2 = hoje + datetime.timedelta(days=7)
    
    with col_btn:
        st.write("")  # Espaçador para alinhamento
        run_scan_tab2 = st.button(
            "▶️ Carregar pauta", 
            type="primary", 
            key="run_scan_tab2"
        )
    
    # ============================================================
    # CARREGAMENTO DE DADOS (quando botão clicado)
    # ============================================================
    if run_scan_tab2:
        # Obter perfil e ID da deputada
        perfil = provider.get_perfil_deputada() or {}
        id_deputada = st.session_state.get("ID_DEPUTADA") or st.session_state.get("id_deputada")
        
        if not id_deputada:
            st.error("❌ ID da deputada não encontrado. Configure o ID antes de continuar.")
            return
        
        nome_deputada = perfil.get("nome", "Júlia Zanatta")
        partido_deputada = perfil.get("partido", "PL")
        uf_deputada = perfil.get("uf", "SC")
        
        with st.spinner("🔄 Carregando eventos da Câmara..."):
            eventos = provider.get_eventos(dt_inicio_t2, dt_fim_t2)
        
        with st.spinner("🔄 Carregando proposições de autoria..."):
            ids_autoria = provider.get_ids_autoria_deputada(int(id_deputada))
        
        with st.spinner("🔍 Escaneando pautas..."):
            df = provider.escanear_eventos_pauta(
                eventos=eventos,
                nome_deputada=nome_deputada,
                partido_deputada=partido_deputada,
                uf_deputada=uf_deputada,
                ids_autoria_deputada=ids_autoria,
            )
        
        # Salvar no session_state
        st.session_state["df_scan_tab2"] = df
        st.session_state["dt_range_tab2_saved"] = (dt_inicio_t2, dt_fim_t2)
        
        st.success(f"✅ {len(df)} eventos carregados com sucesso!")
        st.rerun()
    
    # ============================================================
    # EXIBIÇÃO DOS DADOS JÁ CARREGADOS
    # ============================================================
    df = st.session_state.get("df_scan_tab2", pd.DataFrame())
    dt_range_saved = st.session_state.get("dt_range_tab2_saved")
    
    # Determinar período salvo
    if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
        dt_inicio, dt_fim = dt_inicio_t2, dt_fim_t2
    else:
        dt_inicio, dt_fim = dt_range_saved
    
    # Mostrar quando foi a última atualização
    if not df.empty:
        st.caption(f"📅 Período: {dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}")
    
    if df.empty:
        st.info("👆 Selecione o período e clique em **Carregar pauta** para começar.")
        return
    
    # ============================================================
    # FILTRAR APENAS AUTORIA E RELATORIA
    # ============================================================
    df_autoria_relatoria = df[
        df["tem_autoria_deputada"] | df["tem_relatoria_deputada"]
    ].copy()
    
    if df_autoria_relatoria.empty:
        st.warning("⚠️ Nenhuma proposição de autoria ou relatoria encontrada no período selecionado.")
        return
    
    # ============================================================
    # PREPARAR VISUALIZAÇÃO
    # ============================================================
    view_columns = [
        "data", "hora", "orgao_sigla", "orgao_nome", 
        "id_evento", "tipo_evento",
        "proposicoes_autoria", "ids_proposicoes_autoria", 
        "proposicoes_relatoria", "ids_proposicoes_relatoria", 
        "descricao_evento"
    ]
    
    view = df_autoria_relatoria[view_columns].copy()
    
    # Formatar data
    view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")
    
    # ============================================================
    # MÉTRICAS RÁPIDAS
    # ============================================================
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        total_eventos = len(view)
        st.metric(
            label="📋 Total de Eventos",
            value=total_eventos,
            help="Total de eventos com autoria ou relatoria"
        )
    
    with col_m2:
        com_autoria = view["proposicoes_autoria"].notna().sum()
        st.metric(
            label="✍️ Com Autoria",
            value=com_autoria,
            help="Eventos com proposições de autoria da deputada"
        )
    
    with col_m3:
        com_relatoria = view["proposicoes_relatoria"].notna().sum()
        st.metric(
            label="📝 Com Relatoria",
            value=com_relatoria,
            help="Eventos onde a deputada é relatora"
        )
    
    st.markdown("---")
    
    # ============================================================
    # TABELA DE RESULTADOS
    # ============================================================
    st.markdown("### 📊 Eventos Encontrados")
    
    st.dataframe(
        view, 
        use_container_width=True, 
        hide_index=True,
        height=400
    )
    
    # ============================================================
    # DOWNLOADS
    # ============================================================
    st.markdown("### ⬇️ Exportar Dados")
    
    col_x1, col_p1 = st.columns(2)
    
    with col_x1:
        try:
            data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria")
            st.download_button(
                label="📥 Download XLSX",
                data=data_bytes,
                file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                mime=mime,
                use_container_width=True,
                key="download_xlsx_tab2"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar XLSX: {e}")
    
    with col_p1:
        try:
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_autoria_relatoria(view)
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                mime=pdf_mime,
                use_container_width=True,
                key="download_pdf_tab2"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar PDF: {e}")
    
    st.markdown("---")
    
    # ============================================================
    # DETALHES DE PROPOSIÇÕES DE AUTORIA
    # ============================================================
    st.markdown("### 🔍 Ver Detalhes de Proposição")
    
    # Extrair IDs de proposições de autoria
    ids_autoria_pauta = set()
    
    for _, row in df_autoria_relatoria.iterrows():
        ids_str = row.get("ids_proposicoes_autoria", "")
        if pd.notna(ids_str) and str(ids_str).strip():
            # IDs separados por ;
            for pid in str(ids_str).split(";"):
                pid = pid.strip()
                if pid and pid.isdigit():
                    ids_autoria_pauta.add(pid)
    
    if not ids_autoria_pauta:
        st.info("ℹ️ Nenhuma proposição de autoria identificada na pauta do período.")
    else:
        st.markdown(f"**{len(ids_autoria_pauta)} proposição(ões) de autoria encontrada(s)**")
        
        # Criar opções para selectbox (lazy loading)
        opcoes_props = {}
        
        with st.spinner("🔄 Carregando informações das proposições..."):
            for pid in sorted(ids_autoria_pauta):
                try:
                    info = provider.get_proposicao_info(pid)
                    label = format_sigla_num_ano(
                        info.get("sigla", ""),
                        info.get("numero", ""),
                        info.get("ano", "")
                    ) or f"ID {pid}"
                    opcoes_props[label] = pid
                except Exception:
                    opcoes_props[f"ID {pid}"] = pid
        
        if opcoes_props:
            prop_selecionada = st.selectbox(
                "📄 Selecione uma proposição para ver detalhes:",
                options=list(opcoes_props.keys()),
                key="select_prop_autoria_tab2"
            )
            
            if prop_selecionada:
                selected_id_tab2 = opcoes_props[prop_selecionada]
                
                # Chamar função de exibição de detalhes
                # (essa função vem do monólito por enquanto)
                exibir_detalhes_proposicao_func(
                    selected_id_tab2, 
                    key_prefix="tab2"
                )
    
    # ============================================================
    # RODAPÉ
    # ============================================================
    st.markdown("---")
    st.caption(
        "📊 Dados: API Câmara dos Deputados | "
        "Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta"
    )
