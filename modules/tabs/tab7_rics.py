# modules/tabs/tab7_rics.py
"""
Aba 7 - RICs (Requerimentos de Informação)

Módulo migrado do monólito. Renderiza a aba completa de RICs.
Depende do DataProvider para acesso a dados.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# Imports de utils já existentes
from core.utils.links import camara_link_tramitacao
from core.utils.formatters import format_sigla_num_ano
from core.utils.text_utils import normalize_ministerio, canonical_situacao
from core.utils.xlsx_generator import to_xlsx_bytes
from core.utils.pdf_generator import to_pdf_rics_por_status
from core.utils.date_utils import (
    parse_dt,
    days_since,
    fmt_dt_br,
    parse_prazo_resposta_ric,
)
from core.config import DEPUTADA_ID_PADRAO


# ============================================================
# FUNÇÕES AUXILIARES ESPECÍFICAS DE RIC
# ============================================================

def extrair_ministerio_ric(ementa: str, tramitacoes: list = None) -> str:
    """
    Extrai o ministério destinatário de um RIC.
    Primeiro tenta extrair da ementa, depois das tramitações.
    Sempre retorna o nome CANÔNICO normalizado.
    """
    if not ementa:
        ementa = ""
    
    ementa_lower = ementa.lower()
    
    # Padrões para extrair ministério da ementa
    patterns_ministerio = [
        r"ministr[oa]\s+(?:de\s+estado\s+)?(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre|acerca|a\s+respeito)",
        r"ministério\s+(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre|acerca|a\s+respeito)",
        r"sr[ªa]?\.\s+ministr[oa]\s+([^,\.;]+?)(?:,|\.|;|sobre)",
        r"senhor[a]?\s+ministr[oa]\s+(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre)",
    ]
    
    for pattern in patterns_ministerio:
        match = re.search(pattern, ementa_lower)
        if match:
            ministerio_extraido = match.group(1).strip()
            ministerio_normalizado = normalize_ministerio(ministerio_extraido)
            if ministerio_normalizado and ministerio_normalizado != "Não identificado":
                return ministerio_normalizado
    
    # Tentar identificar diretamente na ementa
    ministerio_direto = normalize_ministerio(ementa)
    if ministerio_direto and ministerio_direto != "Não identificado":
        return ministerio_direto
    
    # Se não encontrou na ementa, tentar nas tramitações
    if tramitacoes:
        for t in tramitacoes:
            sigla_orgao = (t.get("siglaOrgao") or "").upper()
            if "1SEC" in sigla_orgao:
                despacho = t.get("despacho") or ""
                desc = t.get("descricaoTramitacao") or ""
                texto = f"{despacho} {desc}"
                
                ministerio_tram = normalize_ministerio(texto)
                if ministerio_tram and ministerio_tram != "Não identificado":
                    return ministerio_tram
    
    return "Não identificado"


def extrair_assunto_ric(ementa: str) -> str:
    """
    Extrai o assunto/tema de um RIC baseado em palavras-chave.
    """
    if not ementa:
        return ""
    
    ementa_lower = ementa.lower()
    
    assuntos_keywords = {
        "Correios/ECT": ["correios", "ect", "empresa de correios"],
        "Agricultura/Agronegócio": ["arroz", "leite", "agro", "agricultura", "pecuária", "soja", "milho", "rural"],
        "Saúde/Vacinas": ["vacina", "vacinação", "imunizante", "sus", "saúde", "medicamento", "anvisa"],
        "Segurança Pública": ["polícia", "policia", "arma", "segurança", "crime", "prisão", "presídio"],
        "Educação": ["escola", "ensino", "educação", "universidade", "mec", "enem"],
        "Economia/Finanças": ["imposto", "pix", "drex", "banco", "receita", "tributo", "economia"],
        "Direitos Humanos": ["direitos humanos", "conanda", "criança", "adolescente", "indígena"],
        "Meio Ambiente": ["ambiente", "clima", "floresta", "ibama", "desmatamento"],
        "Comunicações/Tecnologia": ["internet", "tecnologia", "telecom", "comunicação", "digital"],
        "Relações Exteriores": ["exterior", "internacional", "embaixada", "diplomacia"],
        "Defesa/Militar": ["defesa", "militar", "exército", "forças armadas"],
        "Transportes": ["transporte", "rodovia", "ferrovia", "estrada", "aeroporto"],
        "Assistência Social": ["bolsa família", "assistência", "fome", "pobreza"],
    }
    
    for assunto, keywords in assuntos_keywords.items():
        for kw in keywords:
            if kw in ementa_lower:
                return assunto
    
    return ""


def _fmt_prazo(row) -> str:
    """
    Formata o prazo para exibição com indicadores de urgência:
    🚨 ≤2 dias (URGENTÍSSIMO)
    ⚠️ ≤5 dias (URGENTE)
    🔔 ≤15 dias (Atenção)
    """
    prazo_str = row.get("RIC_PrazoStr", "")
    prazo_fim = row.get("RIC_PrazoFim")
    dias = row.get("RIC_DiasRestantes")
    status = row.get("RIC_StatusResposta", "")
    
    if prazo_str and str(prazo_str).strip():
        base = str(prazo_str)
    elif prazo_fim and pd.notna(prazo_fim):
        try:
            if isinstance(prazo_fim, datetime.date):
                base = f"até {prazo_fim.strftime('%d/%m/%Y')}"
            else:
                base = f"até {str(prazo_fim)[:10]}"
        except:
            return "—"
    else:
        return "—"
    
    if dias is not None and pd.notna(dias):
        try:
            dias_int = int(dias)
            if "Respondido" in str(status):
                return f"{base} ✅"
            elif dias_int < 0:
                return f"{base} (🚨 VENCIDO há {abs(dias_int)}d)"
            elif dias_int <= 2:
                return f"{base} (🚨 {dias_int}d - URGENTÍSSIMO)"
            elif dias_int <= 5:
                return f"{base} (⚠️ {dias_int}d - URGENTE)"
            elif dias_int <= 15:
                return f"{base} (🔔 {dias_int}d restantes)"
            else:
                return f"{base} ({dias_int}d restantes)"
        except:
            return base
    
    return base


def _check_dias(x, cond) -> bool:
    """Verifica condição nos dias restantes."""
    if x is None or pd.isna(x):
        return False
    try:
        return cond(int(x))
    except:
        return False


# ============================================================
# FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO
# ============================================================

def render_tab7(provider, id_deputada: int = None) -> None:
    """
    Renderiza a Aba 7 - RICs (Requerimentos de Informação).
    
    Args:
        provider: Instância do DataProvider
        id_deputada: ID da deputada (opcional, usa padrão se não fornecido)
    """
    if id_deputada is None:
        id_deputada = (
            st.session_state.get("ID_DEPUTADA")
            or st.session_state.get("id_deputada")
            or DEPUTADA_ID_PADRAO
        )
    
    st.markdown("### 📋 RICs - Requerimentos de Informação")
    
    st.info("💡 **Dica:** Acompanhe os prazos de resposta dos RICs (30 dias). Use os filtros de status para identificar RICs vencidos ou próximos do vencimento. Clique em um RIC para ver detalhes e tramitação.")
    
    st.markdown("""
    **Acompanhamento dos Requerimentos de Informação** da Deputada Júlia Zanatta.
    
    O RIC é um instrumento de fiscalização que permite ao parlamentar solicitar informações 
    a Ministros de Estado sobre atos de suas pastas. O Poder Executivo tem **30 dias** 
    para responder, contados a partir do dia útil seguinte à remessa do ofício.
    """)
    
    st.markdown("---")
    
    # Inicializar estado
    if "df_rics_completo" not in st.session_state:
        st.session_state["df_rics_completo"] = pd.DataFrame()
    
    # ============================================================
    # CARREGAMENTO AUTOMÁTICO DE RICs
    # ============================================================
    col_info_ric, col_refresh_ric = st.columns([3, 1])
    
    with col_info_ric:
        st.caption("💡 **RICs carregam automaticamente.** Clique em 'Atualizar' para forçar recarga.")
    
    with col_refresh_ric:
        btn_atualizar_rics = st.button("🔄 Atualizar", key="btn_refresh_rics")
    
    # Carregar automaticamente se ainda não carregou OU se botão foi clicado
    precisa_carregar = st.session_state["df_rics_completo"].empty or btn_atualizar_rics
    
    if precisa_carregar:
        with st.spinner("🔍 Carregando RICs da Deputada..."):
            # Usar o provider para buscar RICs
            df_rics_base = provider.fetch_rics_por_autor(int(id_deputada))
            
            if df_rics_base.empty:
                st.warning("Nenhum RIC encontrado.")
                st.session_state["df_rics_completo"] = pd.DataFrame()
            else:
                # Buscar status completo de cada RIC
                ids_rics = df_rics_base["id"].astype(str).tolist()
                status_map_rics = provider.build_status_map_rics(ids_rics)
                
                # Enriquecer com status
                df_rics_enriquecido = provider.enrich_rics_with_status(df_rics_base, status_map_rics)
                
                st.session_state["df_rics_completo"] = df_rics_enriquecido
                
                # Registrar atualização
                if "ultima_atualizacao" not in st.session_state:
                    st.session_state["ultima_atualizacao"] = {}
                st.session_state["ultima_atualizacao"]["rics"] = datetime.datetime.now()
                
                if btn_atualizar_rics:
                    st.success(f"✅ {len(df_rics_enriquecido)} RICs atualizados!")
    
    # Mostrar última atualização
    if "ultima_atualizacao" in st.session_state:
        timestamp = st.session_state["ultima_atualizacao"].get("rics")
        if timestamp:
            st.caption(f"🕐 Última atualização: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
    
    df_rics = st.session_state.get("df_rics_completo", pd.DataFrame())
    
    if not df_rics.empty:
        # Mostrar distribuição por ano
        anos_dist = df_rics["ano"].value_counts().sort_index(ascending=False)
        anos_info = ", ".join([f"{ano}: {qtd}" for ano, qtd in anos_dist.items() if str(ano).strip()])
        st.caption(f"📅 Distribuição por ano: {anos_info}")
        
        st.markdown("---")
        
        # ============================================================
        # FILTROS PARA RICs
        # ============================================================
        with st.expander("🔍 Filtros", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                # Filtro por ano
                todos_anos = df_rics["ano"].dropna().unique().tolist()
                anos_validos = [str(a) for a in todos_anos if str(a).strip().isdigit() and len(str(a).strip()) == 4]
                anos_ric = sorted(anos_validos, reverse=True)
                
                # Contar RICs sem ano válido
                rics_sem_ano = len(df_rics[~df_rics["ano"].isin(anos_validos)])
                
                anos_sel_ric = st.multiselect("Ano", options=anos_ric, default=anos_ric, key="anos_ric")
                
                if rics_sem_ano > 0:
                    st.caption(f"⚠️ {rics_sem_ano} RICs sem ano válido")
            
            with col_f2:
                # Filtro por status de resposta
                status_resp_options = [
                    "Todos", 
                    "Aguardando resposta",
                    "Em tramitação na Câmara",
                    "Fora do prazo",
                    "Respondido", 
                    "Respondido fora do prazo"
                ]
                status_resp_sel = st.selectbox("Status de Resposta", options=status_resp_options, key="status_resp_ric")
            
            with col_f3:
                # Filtro por ministério
                ministerios = df_rics["RIC_Ministerio"].dropna().replace("", pd.NA).dropna().unique().tolist()
                ministerios = [m for m in ministerios if m and str(m).strip()]
                ministerios_sel = st.multiselect("Ministério", options=sorted(ministerios), key="ministerios_ric")
            
            with col_f4:
                # Filtro por prazo
                prazo_options = ["Todos", "Vencidos", "Vencendo em 5 dias", "Vencendo em 15 dias", "No prazo"]
                prazo_sel = st.selectbox("Prazo", options=prazo_options, key="prazo_ric")
        
        # Aplicar filtros
        df_rics_fil = df_rics.copy()
        
        if anos_sel_ric:
            df_rics_fil = df_rics_fil[df_rics_fil["ano"].isin([str(a) for a in anos_sel_ric])].copy()
        
        if status_resp_sel != "Todos":
            df_rics_fil = df_rics_fil[df_rics_fil["RIC_StatusResposta"] == status_resp_sel].copy()
        
        if ministerios_sel:
            df_rics_fil = df_rics_fil[df_rics_fil["RIC_Ministerio"].isin(ministerios_sel)].copy()
        
        if prazo_sel != "Todos":
            if prazo_sel == "Vencidos":
                df_rics_fil = df_rics_fil[df_rics_fil["RIC_DiasRestantes"].apply(lambda x: _check_dias(x, lambda d: d < 0))].copy()
            elif prazo_sel == "Vencendo em 5 dias":
                df_rics_fil = df_rics_fil[df_rics_fil["RIC_DiasRestantes"].apply(lambda x: _check_dias(x, lambda d: 0 <= d <= 5))].copy()
            elif prazo_sel == "Vencendo em 15 dias":
                df_rics_fil = df_rics_fil[df_rics_fil["RIC_DiasRestantes"].apply(lambda x: _check_dias(x, lambda d: 0 <= d <= 15))].copy()
            elif prazo_sel == "No prazo":
                df_rics_fil = df_rics_fil[df_rics_fil["RIC_DiasRestantes"].apply(lambda x: _check_dias(x, lambda d: d > 0))].copy()
        
        # ============================================================
        # RESUMO EXECUTIVO DOS RICs
        # ============================================================
        st.markdown("### 📊 Resumo dos RICs")
        
        total_geral = len(df_rics)
        total_filtrado = len(df_rics_fil)
        
        if total_filtrado < total_geral:
            st.caption(f"📌 Exibindo **{total_filtrado}** de **{total_geral}** RICs (filtros ativos)")
        
        col_m1, col_m2, col_m3, col_m4, col_m5, col_m6, col_m7 = st.columns(7)
        
        total_rics = total_filtrado
        em_tramitacao = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Em tramitação na Câmara"])
        aguardando = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Aguardando resposta"])
        fora_prazo = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Fora do prazo"])
        respondidos_ok = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Respondido"])
        respondidos_fora = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Respondido fora do prazo"])
        respondidos_total = respondidos_ok + respondidos_fora
        
        # Calcular urgentes
        urgentes = 0
        for _, row in df_rics_fil.iterrows():
            dias = row.get("RIC_DiasRestantes")
            status = row.get("RIC_StatusResposta", "")
            if dias is not None and pd.notna(dias) and "Respondido" not in str(status) and status != "Em tramitação na Câmara":
                try:
                    dias_int = int(dias)
                    if 0 <= dias_int <= 5:
                        urgentes += 1
                except:
                    pass
        
        with col_m1:
            if total_filtrado < total_geral:
                st.metric("Total", total_rics, help=f"Filtrado: {total_filtrado} de {total_geral} RICs")
            else:
                st.metric("Total", total_rics)
        with col_m2:
            st.metric("🏛️ Na Câmara", em_tramitacao, help="RICs ainda em tramitação interna na Câmara")
        with col_m3:
            st.metric("⏳ Aguardando", aguardando, help="Enviados ao Ministério, aguardando resposta dentro do prazo")
        with col_m4:
            st.metric("🚨 S/ resposta", fora_prazo, delta=f"-{fora_prazo}" if fora_prazo > 0 else None, delta_color="inverse", help="Sem resposta e prazo vencido")
        with col_m5:
            st.metric("✅ Resp. OK", respondidos_ok, help="Respondidos dentro do prazo de 30 dias")
        with col_m6:
            st.metric("⚠️ Resp. atraso", respondidos_fora, help="Respondidos após o prazo de 30 dias")
        with col_m7:
            st.metric("🔔 Urgentes", urgentes, delta=f"{urgentes}" if urgentes > 0 else None, delta_color="off", help="Vencendo em até 5 dias")
        
        # Validação da soma
        soma = em_tramitacao + aguardando + fora_prazo + respondidos_ok + respondidos_fora
        if soma != total_rics:
            st.warning(f"⚠️ Soma das categorias ({soma}) difere do total ({total_rics}). Pode haver status não mapeado.")
        
        st.markdown("---")
        
        # ============================================================
        # ALERTAS DE PRAZO
        # ============================================================
        df_fora_prazo = df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Fora do prazo"].copy()
        df_urgentes_alert = df_rics_fil[
            (df_rics_fil["RIC_StatusResposta"] == "Aguardando resposta") &
            (df_rics_fil["RIC_DiasRestantes"].apply(lambda x: x is not None and pd.notna(x) and 0 <= int(x) <= 5 if x is not None and pd.notna(x) else False))
        ].copy()
        
        if not df_fora_prazo.empty:
            st.error(f"🚨 **{len(df_fora_prazo)} RIC(s) FORA DO PRAZO (sem resposta)!**")
            for _, row in df_fora_prazo.head(5).iterrows():
                prop = row.get("Proposicao", "")
                dias = row.get("RIC_DiasRestantes")
                dias_str = f"há {abs(int(dias))} dias" if dias is not None and pd.notna(dias) else ""
                ministerio = row.get("RIC_Ministerio", "Não identificado")
                link = camara_link_tramitacao(row.get("id", ""))
                st.markdown(f"- **[{prop}]({link})** - Vencido {dias_str} - {ministerio}")
        
        if not df_urgentes_alert.empty:
            st.warning(f"⚠️ **{len(df_urgentes_alert)} RIC(s) VENCENDO EM ATÉ 5 DIAS!**")
            for _, row in df_urgentes_alert.head(5).iterrows():
                prop = row.get("Proposicao", "")
                try:
                    dias = int(row.get("RIC_DiasRestantes", 0) or 0)
                except (ValueError, TypeError):
                    dias = 0
                ministerio = row.get("RIC_Ministerio", "Não identificado")
                link = camara_link_tramitacao(row.get("id", ""))
                st.markdown(f"- **[{prop}]({link})** - Vence em **{dias} dias** - {ministerio}")
        
        st.markdown("---")
        
        # ============================================================
        # TABELA DE RICs COM SELEÇÃO
        # ============================================================
        st.markdown("### 📋 Lista de RICs")
        
        # Ordenar por data mais recente primeiro
        if "DataStatus_dt" in df_rics_fil.columns:
            df_rics_fil = df_rics_fil.sort_values("DataStatus_dt", ascending=False)
        
        # Preparar colunas para exibição
        df_rics_view = df_rics_fil.copy()
        df_rics_view["LinkTramitacao"] = df_rics_view["id"].astype(str).apply(camara_link_tramitacao)
        
        # Normalizar ministério
        df_rics_view["Ministério"] = df_rics_view["RIC_Ministerio"].apply(normalize_ministerio)
        
        # Formatar prazo
        df_rics_view["Prazo"] = df_rics_view.apply(_fmt_prazo, axis=1)
        
        # Formatar data
        if "Data do status" in df_rics_view.columns:
            df_rics_view = df_rics_view.rename(columns={"Data do status": "Última tramitação"})
        
        # Renomear colunas
        df_rics_view = df_rics_view.rename(columns={
            "Proposicao": "RIC",
            "RIC_StatusResposta": "Status",
            "RIC_Assunto": "Assunto",
            "Parado (dias)": "Parado há",
        })
        
        # Colunas para exibir
        show_cols_ric = ["RIC", "ano", "Ministério", "Status", "Prazo", "Última tramitação", 
                        "Parado há", "Situação atual", "LinkTramitacao", "ementa", "id"]
        show_cols_ric = [c for c in show_cols_ric if c in df_rics_view.columns]
        
        # TABELA COM SELEÇÃO
        sel_ric = st.dataframe(
            df_rics_view[show_cols_ric],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                "ementa": st.column_config.TextColumn("Ementa", width="large"),
                "Ministério": st.column_config.TextColumn("Ministério", width="medium"),
                "Prazo": st.column_config.TextColumn("Prazo", width="medium"),
                "id": None,
            },
            key="df_rics_selecao"
        )
        
        st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Atenção) | ✅ Respondido")
        
        # ============================================================
        # DOWNLOADS
        # ============================================================
        st.markdown("---")
        col_dx, col_dp = st.columns(2)
        
        with col_dx:
            bytes_out, mime, ext = to_xlsx_bytes(df_rics_view[show_cols_ric], "RICs")
            st.download_button(
                "⬇️ Baixar XLSX",
                data=bytes_out,
                file_name=f"rics_deputada.{ext}",
                mime=mime,
                key="download_rics_xlsx"
            )
        
        with col_dp:
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_rics_por_status(df_rics_view, "RICs - Requerimentos de Informação")
            st.download_button(
                "⬇️ Baixar PDF",
                data=pdf_bytes,
                file_name=f"rics_deputada.{pdf_ext}",
                mime=pdf_mime,
                key="download_rics_pdf"
            )
        
        # ============================================================
        # DETALHES DO RIC SELECIONADO
        # ============================================================
        st.markdown("---")
        st.markdown("### 🔍 Detalhes do RIC Selecionado")
        
        selected_ric_id = None
        try:
            if sel_ric and isinstance(sel_ric, dict) and sel_ric.get("selection") and sel_ric["selection"].get("rows"):
                row_idx = sel_ric["selection"]["rows"][0]
                selected_ric_id = str(df_rics_view.iloc[row_idx]["id"])
        except Exception:
            selected_ric_id = None
        
        if not selected_ric_id:
            st.info("👆 Clique em um RIC na tabela acima para ver detalhes completos.")
        else:
            # Exibir detalhes usando o provider
            _exibir_detalhes_ric(provider, selected_ric_id)
    
    else:
        st.info("👆 Clique em **Carregar/Atualizar RICs** para começar.")

    st.markdown("---")
    st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")


def _exibir_detalhes_ric(provider, selected_id: str) -> None:
    """
    Exibe detalhes de um RIC selecionado.
    Versão simplificada para a aba de RICs.
    """
    with st.spinner("Carregando informações completas..."):
        dados = provider.get_proposicao_completa(selected_id)
    
    if not dados:
        st.warning("Não foi possível carregar os detalhes da proposição.")
        return
    
    # Informações básicas
    proposicao_fmt = format_sigla_num_ano(dados.get("sigla"), dados.get("numero"), dados.get("ano")) or ""
    situacao = dados.get("status_descricaoSituacao") or "—"
    orgao = dados.get("status_siglaOrgao") or "—"
    andamento = dados.get("status_descricaoTramitacao") or "—"
    ementa = dados.get("ementa") or "—"
    url_teor = dados.get("urlInteiroTeor") or ""
    
    st.markdown(f"**Proposição:** {proposicao_fmt}")
    st.markdown(f"**Situação:** {situacao}")
    st.markdown(f"**Órgão:** {orgao}")
    st.markdown(f"**Andamento:** {andamento}")
    st.markdown(f"**Ementa:** {ementa}")
    
    if url_teor:
        st.markdown(f"[📄 Ver Inteiro Teor]({url_teor})")
    
    # Link para tramitação completa
    link_tram = camara_link_tramitacao(selected_id)
    st.markdown(f"[🔗 Ver tramitação completa na Câmara]({link_tram})")
