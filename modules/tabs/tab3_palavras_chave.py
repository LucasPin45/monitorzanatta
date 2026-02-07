# modules/tabs/tab3_palavras_chave.py
from __future__ import annotations

from typing import Any, Dict, List
import datetime

import streamlit as st
import pandas as pd

# Funções utilitárias
from core.utils import (
    to_xlsx_bytes,
    to_pdf_palavras_chave,
)

# Constantes do projeto
from core.config import PALAVRAS_CHAVE_PADRAO


def render_tab3(provider, id_deputada) -> None:
    """
    Aba 3 - Palavras-chave na pauta
    Monitora proposições com palavras-chave de interesse.
    
    Args:
        provider: DataProvider instance
        id_deputada: ID da deputada na API da Câmara
    """
    
    st.subheader("Palavras-chave na pauta")
    
    st.info(
        "💡 **Dica:** Configure palavras-chave de interesse (ex: vacina, aborto, armas) "
        "para monitorar proposições temáticas na pauta da semana."
    )
    
    # ============================================================
    # CONTROLES: PERÍODO, PALAVRAS-CHAVE E BOTÃO
    # ============================================================
    col_data_t3, col_kw_t3 = st.columns([1, 1])
    
    with col_data_t3:
        hoje = datetime.date.today()
        default_range = st.session_state.get(
            "date_range_tab3",
            (hoje, hoje + datetime.timedelta(days=7))
        )
        
        date_range_tab3 = st.date_input(
            "📅 Período de busca",
            value=default_range,
            format="DD/MM/YYYY",
            key="date_range_tab3"
        )
        
        # Validar range
        if isinstance(date_range_tab3, tuple) and len(date_range_tab3) == 2:
            dt_inicio_t3, dt_fim_t3 = date_range_tab3
        else:
            dt_inicio_t3 = hoje
            dt_fim_t3 = hoje + datetime.timedelta(days=7)
    
    with col_kw_t3:
        palavras_default = st.session_state.get(
            "palavras_t3",
            "\n".join(PALAVRAS_CHAVE_PADRAO)
        )
        
        palavras_str_t3 = st.text_area(
            "🔑 Palavras-chave (uma por linha)",
            value=palavras_default,
            height=100,
            key="palavras_input_t3"
        )
        
        # Processar palavras-chave
        palavras_chave_t3 = [
            p.strip() 
            for p in (palavras_str_t3 or "").splitlines() 
            if p.strip()
        ]
        
        # Salvar no session_state
        st.session_state["palavras_t3"] = palavras_str_t3
    
    # Botão de carregar
    run_scan_tab3 = st.button(
        "▶️ Carregar pauta com palavras-chave",
        type="primary",
        key="run_scan_tab3"
    )
    
    # ============================================================
    # CARREGAMENTO DE DADOS
    # ============================================================
    if run_scan_tab3:
        # Obter perfil da deputada
        perfil = provider.get_perfil_deputada() or {}
        
        if not id_deputada:
            st.error("❌ ID da deputada não encontrado.")
            return
        
        nome_deputada = perfil.get("nome", "Júlia Zanatta")
        partido_deputada = perfil.get("partido", "PL")
        uf_deputada = perfil.get("uf", "SC")
        
        with st.spinner("🔄 Carregando eventos..."):
            eventos = provider.get_eventos(dt_inicio_t3, dt_fim_t3)
        
        with st.spinner("🔄 Carregando proposições de autoria..."):
            ids_autoria = provider.get_ids_autoria_deputada(int(id_deputada))
        
        with st.spinner("🔍 Escaneando pautas com palavras-chave..."):
            df = provider.escanear_eventos_palavras_chave(
                eventos=eventos,
                nome_deputada=nome_deputada,
                partido_deputada=partido_deputada,
                uf_deputada=uf_deputada,
                palavras_chave=palavras_chave_t3,
                ids_autoria_deputada=ids_autoria,
            )
        
        # Salvar no session_state
        st.session_state["df_scan_tab3"] = df
        st.session_state["dt_range_tab3_saved"] = (dt_inicio_t3, dt_fim_t3)
        
        st.success(f"✅ {len(df)} eventos carregados com sucesso!")
        st.rerun()
    
    # ============================================================
    # EXIBIÇÃO DOS DADOS
    # ============================================================
    df = st.session_state.get("df_scan_tab3", pd.DataFrame())
    dt_range_saved = st.session_state.get("dt_range_tab3_saved")
    
    # Determinar período
    if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
        dt_inicio, dt_fim = dt_inicio_t3, dt_fim_t3
    else:
        dt_inicio, dt_fim = dt_range_saved
    
    if not df.empty:
        st.caption(f"📅 Período: {dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}")
    
    if df.empty:
        st.info("👆 Selecione o período, configure as palavras-chave e clique em **Carregar pauta**.")
        return
    
    # ============================================================
    # FILTRAR APENAS PALAVRAS-CHAVE
    # ============================================================
    df_kw = df[df["tem_palavras_chave"]].copy()
    
    if df_kw.empty:
        st.warning("⚠️ Nenhuma proposição com as palavras-chave foi encontrada no período.")
        return
    
    # ============================================================
    # PROCESSAR PROPOSIÇÕES COM PALAVRAS-CHAVE
    # ============================================================
    lista_proposicoes = []
    
    for _, row in df_kw.iterrows():
        props_str = row.get("proposicoes_palavras_chave", "")
        if not props_str or pd.isna(props_str):
            continue
        
        # Formato: matéria|||palavras|||ementa|||link|||relator|||comissao|||nome_comissao|||data
        for prop_detail in str(props_str).split("; "):
            if "|||" not in prop_detail:
                continue
            
            partes = prop_detail.split("|||")
            materia = partes[0].strip() if len(partes) > 0 else ""
            palavras = partes[1].strip() if len(partes) > 1 else ""
            ementa = partes[2].strip() if len(partes) > 2 else ""
            link = partes[3].strip() if len(partes) > 3 else ""
            relator = partes[4].strip() if len(partes) > 4 else ""
            comissao = partes[5].strip() if len(partes) > 5 else row.get("orgao_sigla", "")
            nome_comissao = partes[6].strip() if len(partes) > 6 else row.get("orgao_nome", "")
            data_evento = partes[7].strip() if len(partes) > 7 else row.get("data", "")
            
            # Formatar data
            data_formatada = ""
            if data_evento and len(data_evento) >= 10:
                try:
                    dt = datetime.datetime.strptime(data_evento[:10], "%Y-%m-%d")
                    data_formatada = dt.strftime("%d/%m/%Y")
                except:
                    data_formatada = data_evento
            
            if materia:
                lista_proposicoes.append({
                    "Data": data_formatada,
                    "Matéria": materia,
                    "Palavras-chave": palavras,
                    "Comissão": comissao,
                    "Nome Comissão": nome_comissao,
                    "Relator": relator if relator and "(-)" not in relator else "Sem relator",
                    "Ementa": ementa[:100] + "..." if len(ementa) > 100 else ementa,
                    "Link": link
                })
    
    # ============================================================
    # CRIAR DATAFRAME DE PROPOSIÇÕES
    # ============================================================
    df_props = pd.DataFrame(lista_proposicoes)
    
    if df_props.empty:
        st.info("ℹ️ Nenhuma matéria com palavras-chave encontrada.")
        return
    
    # Remover duplicatas
    df_props = df_props.drop_duplicates(subset=["Matéria", "Comissão"])
    df_props = df_props.sort_values(["Data", "Comissão", "Matéria"])
    
    # ============================================================
    # MÉTRICAS
    # ============================================================
    st.success(
        f"🔍 **{len(df_props)} matérias** com palavras-chave encontradas em "
        f"**{df_props['Comissão'].nunique()} comissões**!"
    )
    
    # Estatísticas por dia
    df_props["Data_dt"] = pd.to_datetime(df_props["Data"], dayfirst=True, errors="coerce")
    df_props_valid = df_props[df_props["Data_dt"].notna()].copy()
    df_props_valid["Dia"] = df_props_valid["Data_dt"].dt.date
    
    if not df_props_valid.empty:
        por_dia = (
            df_props_valid
            .groupby("Dia")
            .size()
            .reset_index(name="Qtd")
            .sort_values("Dia")
        )
        
        st.caption("📊 Matérias com palavras-chave por dia")
        st.dataframe(por_dia, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ============================================================
    # TABELA PRINCIPAL
    # ============================================================
    st.markdown("### 📋 Matérias Encontradas")
    
    st.dataframe(
        df_props,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="abrir"),
            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
        },
        height=400
    )
    
    # ============================================================
    # DOWNLOADS
    # ============================================================
    st.markdown("### ⬇️ Exportar Dados")
    
    col_x2, col_p2 = st.columns(2)
    
    with col_x2:
        try:
            data_bytes, mime, ext = to_xlsx_bytes(df_props, "PalavrasChave_Pauta")
            st.download_button(
                label="📥 Download XLSX",
                data=data_bytes,
                file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{ext}",
                mime=mime,
                use_container_width=True,
                key="download_kw_xlsx"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar XLSX: {e}")
    
    with col_p2:
        try:
            # Usar df_kw para PDF (tem todas as colunas necessárias)
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_palavras_chave(df_kw)
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                mime=pdf_mime,
                use_container_width=True,
                key="download_kw_pdf"
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
