# modules/tabs/tab5_buscar.py
# v11 08/02 14:25 (Brasília)
"""
Tab 5 - Buscar Proposição Específica

A TAB MAIS COMPLEXA DO SISTEMA!

Funcionalidades:
- Cache inteligente de proposições (auto-load)
- Filtros por ano e tipo
- Busca textual avançada
- Enriquecimento de status (situação, relator, órgão)
- INTEGRAÇÃO COMPLETA COM SENADO FEDERAL 🏛️
- Cache incremental do Senado (busca apenas IDs novos!)
- Detecção automática de proposições no Senado
- Integração de dados Câmara + Senado
- Seleção interativa de proposições
- Exibição de detalhes completos
- Downloads XLSX e PDF

IMPORTANTE: Apenas esta aba tem acesso ao Senado!
O gate de segurança garante que outras abas não façam chamadas desnecessárias.

Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import datetime
import unicodedata

import streamlit as st
import pandas as pd

# Funções utilitárias
from core.utils import (
    to_xlsx_bytes,
    to_pdf_bytes,
    normalize_text,
    camara_link_tramitacao,
)

# Serviço do Senado
from core.services.senado_integration import processar_lista_com_senado


def render_tab5(
    provider,
    exibir_detalhes_proposicao_func: Callable,
    id_deputada: int
) -> None:
    """
    Aba 5 - Buscar Proposição Específica
    
    Tab mais complexa com integração completa do Senado Federal.
    
    Args:
        provider: DataProvider instance
        exibir_detalhes_proposicao_func: Função para exibir detalhes da proposição
        id_deputada: ID da deputada na API da Câmara
    """
    
    st.markdown("### 🔍 Buscar Proposição Específica")
    
    st.info(
        "💡 **Dica:** Use os filtros de ano e tipo para encontrar proposições específicas. "
        "Clique em uma proposição na tabela para ver detalhes completos, tramitação e estratégia."
    )
    
    st.caption("Busque proposições de autoria da deputada e veja detalhes completos")
    
    # ============================================================
    # BOTÕES DE CONTROLE: LIMPAR CACHE E ATUALIZAR
    # ============================================================
    col_cache, col_refresh5 = st.columns([1, 1])
    
    with col_cache:
        if st.button("🧹 Limpar cache", key="limpar_cache_tab5"):
            # Limpar todos os caches
            provider.clear_proposicoes_cache()
            st.session_state.pop("df_status_last", None)
            st.session_state.pop("df_todas_enriquecido_tab5", None)
            st.session_state.pop("props_aba5_cache", None)
            st.session_state.pop("senado_cache_por_id", None)
            st.success("✅ Cache limpo! Recarregando...")
            st.rerun()
    
    with col_refresh5:
        btn_refresh_aba5 = st.button("🔄 Atualizar", key="btn_refresh_aba5")
    
    # ============================================================
    # CARREGAMENTO AUTOMÁTICO DE PROPOSIÇÕES
    # ============================================================
    # v39: Cache e carregamento automático (sem botão "Carregar")
    if "props_aba5_cache" not in st.session_state:
        st.session_state["props_aba5_cache"] = None
    
    # Carregar automaticamente se cache vazio OU se botão foi clicado
    precisa_carregar_aba5 = (
        st.session_state["props_aba5_cache"] is None or 
        btn_refresh_aba5
    )
    
    # Inicializar variável
    df_aut = pd.DataFrame()
    
    if precisa_carregar_aba5:
        # Carrega proposições automaticamente
        with st.spinner("Carregando proposições de autoria..."):
            df_aut = provider.fetch_proposicoes_autoria(id_deputada)
            st.session_state["props_aba5_cache"] = df_aut
            if btn_refresh_aba5:
                st.success("✅ Dados atualizados!")
    else:
        # Usar cache existente
        df_aut = st.session_state["props_aba5_cache"]
        if df_aut is None:
            df_aut = pd.DataFrame()
    
    # ============================================================
    # VALIDAÇÃO DE DADOS
    # ============================================================
    if df_aut.empty:
        st.info("Nenhuma proposição de autoria encontrada.")
        return
    
    # Filtrar apenas tipos da carteira padrão
    from core.config import TIPOS_CARTEIRA_PADRAO
    df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()
    
    # ============================================================
    # FILTROS BÁSICOS: ANO E TIPO
    # ============================================================
    st.markdown("#### 🗂️ Filtros de Proposições")
    col_ano, col_tipo = st.columns([1, 1])
    
    with col_ano:
        # Extrair anos disponíveis
        anos = sorted([
            a for a in df_aut["ano"].dropna().unique().tolist() 
            if str(a).strip().isdigit()
        ], reverse=True)
        
        # Usar helper do provider para anos padrão
        anos_default = provider.get_default_anos_filter(anos)
        
        anos_sel = st.multiselect(
            "Ano",
            options=anos,
            default=anos_default,
            key="anos_tab5"
        )
    
    with col_tipo:
        # Extrair tipos disponíveis
        tipos = sorted([
            t for t in df_aut["siglaTipo"].dropna().unique().tolist() 
            if str(t).strip()
        ])
        
        tipos_sel = st.multiselect(
            "Tipo",
            options=tipos,
            default=tipos,
            key="tipos_tab5"
        )
    
    # Aplicar filtros
    df_base = df_aut.copy()
    if anos_sel:
        df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
    if tipos_sel:
        df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()
    
    # ============================================================
    # INTEGRAÇÃO SENADO - INFO
    # ============================================================
    st.markdown("---")
    
    col_sen5, col_dbg5 = st.columns([4, 1])
    
    with col_sen5:
        st.info("🏛️ Integração Senado: **Automática** - detecta quando matéria está no Senado")
    
    with col_dbg5:
        # Debug mode apenas para admin
        if st.session_state.get("usuario_logado", "").lower() == "admin":
            debug_senado_5 = st.checkbox("🔧 Debug", value=False, key="debug_senado_5")
        else:
            debug_senado_5 = False
    
    # Sempre ativo (automático)
    incluir_senado_tab5 = True
    
    st.markdown("---")
    
    # ============================================================
    # BUSCA TEXTUAL
    # ============================================================
    q = st.text_input(
        "Filtrar proposições de autoria",
        value="",
        placeholder="Ex.: PL 321/2023 | 'pix' | 'conanda' | 'oab'",
        help="Busca entre as proposições de AUTORIA da deputada. Use sigla/número/ano ou palavras da ementa.",
        key="busca_tab5"
    )
    
    # v33: APENAS busca textual nas proposições de autoria
    if q.strip():
        qn = normalize_text(q)
        df_busca_completa = df_base.copy()
        df_busca_completa["_search"] = (
            df_busca_completa["Proposicao"].fillna("").astype(str) + " " + 
            df_busca_completa["ementa"].fillna("").astype(str)
        ).apply(normalize_text)
        
        df_rast = df_busca_completa[
            df_busca_completa["_search"].str.contains(qn, na=False)
        ].drop(columns=["_search"], errors="ignore")
        
        if df_rast.empty:
            # BUSCA DIRETA INTELIGENTE
            # Aceita tanto "PL 321/2023" quanto "PL 321" (sem ano)
            import re
            import datetime
            from monitor_sistema_jz import buscar_proposicao_direta
            
            # Padrão 1: Completo (PL 321/2023)
            match_completo = re.match(r"([A-Z]+)\s*(\d+)/(\d{4})", q.upper())
            
            # Padrão 2: Parcial (PL 321)
            match_parcial = re.match(r"([A-Z]+)\s*(\d+)$", q.upper())
            
            if match_completo:
                # Busca com ano específico
                sigla, numero, ano = match_completo.groups()
                
                st.info(f"🔍 Buscando diretamente: {sigla} {numero}/{ano}")
                
                try:
                    prop_direta = buscar_proposicao_direta(sigla, numero, ano)
                    if prop_direta:
                        df_rast = pd.DataFrame([prop_direta])
                        st.success(f"✅ Encontrado: {prop_direta['Proposicao']}")
                    else:
                        st.warning(f"⚠️ Proposição '{q}' não encontrada")
                except Exception as e:
                    st.error(f"❌ Erro na busca: {e}")
                    
            elif match_parcial:
                # Busca sem ano - tenta anos recentes
                sigla, numero = match_parcial.groups()
                
                st.info(f"🔍 Buscando {sigla} {numero} (testando anos recentes...)")
                
                # Tentar anos: atual e 3 anteriores
                ano_atual = datetime.datetime.now().year
                anos_tentar = [ano_atual, ano_atual - 1, ano_atual - 2, ano_atual - 3]
                
                prop_encontrada = None
                for ano in anos_tentar:
                    try:
                        prop = buscar_proposicao_direta(sigla, numero, str(ano))
                        if prop:
                            prop_encontrada = prop
                            break
                    except:
                        continue
                
                if prop_encontrada:
                    df_rast = pd.DataFrame([prop_encontrada])
                    st.success(f"✅ Encontrado: {prop_encontrada['Proposicao']}")
                else:
                    st.warning(f"⚠️ {sigla} {numero} não encontrado nos últimos {len(anos_tentar)} anos")
            else:
                st.warning(f"⚠️ Nenhuma proposição encontrada com '{q}'")
        else:
            st.caption(
                f"🔍 Encontrado(s) {len(df_rast)} resultado(s) entre "
                f"as {len(df_aut)} proposições de autoria"
            )
    else:
        df_rast = df_base.copy()
    
    # ============================================================
    # ENRIQUECIMENTO COM STATUS
    # ============================================================
    if df_rast.empty:
        st.info("Nenhuma proposição encontrada com os critérios informados.")
        return
    
    # Limitar a 400 resultados para performance
    df_rast_lim = df_rast.head(400).copy()
    
    with st.spinner("Carregando status das proposições..."):
        ids_r = df_rast_lim["id"].astype(str).tolist()
        status_map_r = provider.build_proposicoes_status_map(ids_r)
        
        # DEBUG: Verificar se status_map tem dados
        ids_com_situacao = sum(1 for k, v in status_map_r.items() if v.get("situacao"))
        ids_com_orgao = sum(1 for k, v in status_map_r.items() if v.get("siglaOrgao"))
        
        if ids_com_situacao < len(ids_r) // 2:
            st.warning(
                f"⚠️ API retornou poucos dados: Situação em {ids_com_situacao}/{len(ids_r)}, "
                f"Órgão em {ids_com_orgao}/{len(ids_r)}"
            )
        
        df_rast_enriched = provider.enrich_proposicoes_with_status(df_rast_lim, status_map_r)
    
    # Ordenar por data mais recente
    df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)
    
    st.caption(f"Resultados: {len(df_rast_enriched)} proposições")
    
    # ============================================================
    # PREPARAR TABELA PARA EXIBIÇÃO
    # ============================================================
    df_tbl = df_rast_enriched.rename(
        columns={
            "Proposicao": "Proposição",
            "ementa": "Ementa",
            "id": "ID",
            "ano": "Ano",
            "siglaTipo": "Tipo"
        }
    ).copy()
    
    df_tbl["Último andamento"] = df_rast_enriched["Andamento (status)"]
    df_tbl["Parado (dias)"] = df_rast_enriched.get(
        "Parado (dias)",
        pd.Series([None] * len(df_rast_enriched))
    )
    df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)
    
    # Criar coluna Alerta ANTES de processar Senado
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
    
    df_tbl["Alerta"] = df_tbl["Parado (dias)"].apply(get_alerta_emoji)
    
    # ============================================================
    # INTEGRAÇÃO SENADO - PROCESSAMENTO INCREMENTAL
    # ============================================================
    st.markdown("---")
    
    # Inicializar cache incremental no session_state
    if "senado_cache_por_id" not in st.session_state:
        st.session_state["senado_cache_por_id"] = {}
    
    # Filtrar apenas proposições em "Apreciação pelo Senado Federal" E que NÃO são RICs
    def esta_no_senado(row):
        situacao = str(row.get("Situação atual", "")).lower()
        tipo = str(row.get("Tipo", "")).upper()
        # Excluir RICs (não tramitam no Senado)
        if tipo == "RIC":
            return False
        return "apreciação pelo senado" in situacao or "senado federal" in situacao
    
    df_no_senado = df_tbl[df_tbl.apply(esta_no_senado, axis=1)].copy()
    
    if len(df_no_senado) > 0:
        st.markdown("#### 🏛️ Proposições em Apreciação pelo Senado Federal")
        st.caption(f"📊 {len(df_no_senado)} proposição(ões) em tramitação no Senado")
        
        # Identificar IDs que ainda não estão no cache
        ids_no_senado = df_no_senado["ID"].astype(str).tolist()
        ids_ja_cached = set(st.session_state["senado_cache_por_id"].keys())
        ids_para_buscar = [id_prop for id_prop in ids_no_senado if id_prop not in ids_ja_cached]
        
        # Buscar dados do Senado apenas para IDs novos (cache incremental)
        if ids_para_buscar:
            with st.spinner(f"🔍 Buscando dados do Senado para {len(ids_para_buscar)} nova(s) proposição(ões)..."):
                df_para_buscar = df_no_senado[df_no_senado["ID"].astype(str).isin(ids_para_buscar)].copy()
                df_enriquecido = processar_lista_com_senado(
                    df_para_buscar,
                    debug=debug_senado_5,
                    mostrar_progresso=True
                )
                # Atualizar cache
                for _, row in df_enriquecido.iterrows():
                    id_prop = str(row.get("ID", ""))
                    if id_prop:
                        st.session_state["senado_cache_por_id"][id_prop] = row.to_dict()
        
        # Aplicar dados do cache ao DataFrame
        def aplicar_cache_senado(row):
            id_prop = str(row.get("ID", ""))
            cache_data = st.session_state["senado_cache_por_id"].get(id_prop, {})
            if cache_data:
                for key, value in cache_data.items():
                    if key not in ["ID", "Proposição", "Ementa"]:
                        row[key] = value
            return row
        
        df_no_senado = df_no_senado.apply(aplicar_cache_senado, axis=1)
        
        # ============================================================
        # CRITICAL FIX: Aplicar cache do Senado de volta ao df_tbl!
        # Sem isso, df_tbl nunca recebe colunas como no_senado,
        # Relator_Senado, etc., e toda a integração é ignorada.
        # ============================================================
        df_tbl = df_tbl.apply(aplicar_cache_senado, axis=1)
        
        # Garantir que colunas do Senado existam com defaults para linhas sem dados
        _senado_defaults = {
            "no_senado": False,
            "Relator_Senado": "",
            "Orgao_Senado_Sigla": "",
            "Orgao_Senado_Nome": "",
            "situacao_senado": "",
            "url_senado": "",
            "codigo_materia_senado": "",
            "id_processo_senado": "",
            "UltimasMov_Senado": "",
            "tipo_numero_senado": "",
        }
        for col_name, col_default in _senado_defaults.items():
            if col_name not in df_tbl.columns:
                df_tbl[col_name] = col_default
            else:
                df_tbl[col_name] = df_tbl[col_name].fillna(col_default)
        
        # Exibir tabela com dados do Senado (APENAS dados do SF!)
        # Montar colunas derivadas do Senado para exibição limpa
        df_senado_view = df_no_senado.copy()
        
        # Relator SF: preferir Relator_Senado, fallback "Aguardando designação"
        def _rel_sf(row):
            r = str(row.get("Relator_Senado", "")).strip()
            return r if r else "Aguardando designação"
        
        # Órgão SF: preferir Orgao_Senado_Sigla, fallback de movimentações
        def _orgao_sf(row):
            o = str(row.get("Orgao_Senado_Sigla", "")).strip()
            if o:
                return o
            movs = str(row.get("UltimasMov_Senado", ""))
            if movs and " | " in movs:
                partes = movs.split("\n")[0].split(" | ")
                if len(partes) >= 2 and partes[1].strip():
                    return partes[1].strip()
            return "MESA"
        
        # Situação SF
        def _sit_sf(row):
            s = str(row.get("situacao_senado", "")).strip()
            return s if s else "AGUARDANDO DESPACHO"
        
        # Último andamento SF + Data SF + Parado SF
        def _andamento_sf(row):
            movs = str(row.get("UltimasMov_Senado", ""))
            if movs and movs != "Sem movimentações disponíveis" and " | " in movs:
                primeira = movs.split("\n")[0]
                partes = primeira.split(" | ")
                if len(partes) >= 3:
                    return partes[2][:80]
            return ""
        
        def _data_sf(row):
            movs = str(row.get("UltimasMov_Senado", ""))
            if movs and movs != "Sem movimentações disponíveis" and " | " in movs:
                primeira = movs.split("\n")[0]
                partes = primeira.split(" | ")
                if partes:
                    return partes[0].strip()
            return ""
        
        df_senado_view["Relator SF"] = df_senado_view.apply(_rel_sf, axis=1)
        df_senado_view["Órgão SF"] = df_senado_view.apply(_orgao_sf, axis=1)
        df_senado_view["Situação SF"] = df_senado_view.apply(_sit_sf, axis=1)
        df_senado_view["Último andamento SF"] = df_senado_view.apply(_andamento_sf, axis=1)
        df_senado_view["Data SF"] = df_senado_view.apply(_data_sf, axis=1)
        
        # Parado (dias): calcular via pd.to_datetime (mais robusto)
        def _calc_parado_dias(data_str):
            if not data_str or not str(data_str).strip():
                return None
            s = str(data_str).strip()
            try:
                dt = pd.to_datetime(s, dayfirst=True)
                return (pd.Timestamp.now() - dt).days
            except Exception:
                return None
        
        df_senado_view["Parado (dias)"] = df_senado_view["Data SF"].apply(_calc_parado_dias)
        
        colunas_exibir = [
            "Proposição", "Tipo", "Relator SF", "Último andamento SF",
            "Data SF", "Órgão SF", "Situação SF", "Parado (dias)",
        ]
        colunas_exibir = [c for c in colunas_exibir if c in df_senado_view.columns]
        
        st.dataframe(
            df_senado_view[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Proposição": st.column_config.TextColumn("Proposição", width="small"),
                "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                "Relator SF": st.column_config.TextColumn("Relator (Senado)", width="medium"),
                "Último andamento SF": st.column_config.TextColumn("Último andamento (SF)", width="large"),
                "Data SF": st.column_config.TextColumn("Data (SF)", width="small"),
                "Órgão SF": st.column_config.TextColumn("Órgão (SF)", width="small"),
                "Situação SF": st.column_config.TextColumn("Situação (SF)", width="medium"),
                "Parado (dias)": st.column_config.NumberColumn("Parado (dias)", width="small"),
            }
        )
        
        st.markdown("---")
    
    # ============================================================
    # GARANTIA: Aplicar cache do Senado ao df_tbl em TODOS os reruns
    # (o bloco acima pode não executar se df_no_senado estiver vazio neste ciclo,
    # mas o cache do session_state persiste entre reruns do Streamlit)
    # ============================================================
    if st.session_state.get("senado_cache_por_id") and "no_senado" not in df_tbl.columns:
        def _aplicar_cache_rerun(row):
            id_prop = str(row.get("ID", ""))
            cache_data = st.session_state["senado_cache_por_id"].get(id_prop, {})
            if cache_data:
                for key, value in cache_data.items():
                    if key not in ["ID", "Proposição", "Ementa"]:
                        row[key] = value
            return row
        
        df_tbl = df_tbl.apply(_aplicar_cache_rerun, axis=1)
        
        _senado_defaults_rerun = {
            "no_senado": False, "Relator_Senado": "", "Orgao_Senado_Sigla": "",
            "Orgao_Senado_Nome": "", "situacao_senado": "", "url_senado": "",
            "codigo_materia_senado": "", "id_processo_senado": "",
            "UltimasMov_Senado": "", "tipo_numero_senado": "",
        }
        for col_name, col_default in _senado_defaults_rerun.items():
            if col_name not in df_tbl.columns:
                df_tbl[col_name] = col_default
            else:
                df_tbl[col_name] = df_tbl[col_name].fillna(col_default)
    
    # ============================================================
    # INTEGRAÇÃO DE DADOS CÂMARA + SENADO
    # ============================================================
    if incluir_senado_tab5 and "no_senado" in df_tbl.columns:
        # Substituir Relator e Órgão pelos dados do Senado quando disponíveis
        if "Relator_Senado" in df_tbl.columns:
            def get_relator_integrado(row):
                if row.get("no_senado"):
                    relator_senado = row.get("Relator_Senado", "")
                    if relator_senado and relator_senado.strip():
                        return relator_senado
                    else:
                        return "—"  # Sem relator no Senado ainda
                return row.get("Relator(a)", "")
            
            def get_orgao_integrado(row):
                if row.get("no_senado"):
                    orgao_senado = row.get("Orgao_Senado_Sigla", "")
                    if orgao_senado and orgao_senado.strip():
                        return orgao_senado
                    else:
                        # Tentar pegar do último andamento
                        movs = str(row.get("UltimasMov_Senado", ""))
                        if movs and " | " in movs:
                            partes = movs.split("\n")[0].split(" | ")
                            if len(partes) >= 2 and partes[1].strip():
                                return partes[1].strip()
                        return "MESA"  # Padrão quando não foi distribuído
                return row.get("Órgão (sigla)", "")
            
            df_tbl["Relator_Exibido"] = df_tbl.apply(get_relator_integrado, axis=1)
            df_tbl["Orgao_Exibido"] = df_tbl.apply(get_orgao_integrado, axis=1)
        
        # Atualizar Último andamento, Data e Parado com dados do Senado
        def get_ultimo_andamento_integrado(row):
            if row.get("no_senado") and row.get("UltimasMov_Senado"):
                movs = str(row.get("UltimasMov_Senado", ""))
                if movs and movs != "Sem movimentações disponíveis":
                    # Pegar primeira linha (mais recente)
                    primeira = movs.split("\n")[0] if "\n" in movs else movs
                    # Formato: "26/11/2025 12:35 | CAE | Descrição"
                    partes = primeira.split(" | ")
                    if len(partes) >= 3:
                        return partes[2][:80]  # Descrição truncada
            return row.get("Último andamento", "") or row.get("Andamento (status)", "")
        
        def get_data_status_integrado(row):
            if row.get("no_senado") and row.get("UltimasMov_Senado"):
                movs = str(row.get("UltimasMov_Senado", ""))
                if movs and movs != "Sem movimentações disponíveis":
                    primeira = movs.split("\n")[0] if "\n" in movs else movs
                    partes = primeira.split(" | ")
                    if partes:
                        return partes[0].strip()  # Data/hora
            return row.get("Data do status", "")
        
        def get_parado_dias_integrado(row):
            if row.get("no_senado") and row.get("UltimasMov_Senado"):
                movs = str(row.get("UltimasMov_Senado", ""))
                if movs and movs != "Sem movimentações disponíveis":
                    primeira = movs.split("\n")[0] if "\n" in movs else movs
                    partes = primeira.split(" | ")
                    if partes:
                        data_str = partes[0].strip()
                        # Tentar parsear a data
                        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                            try:
                                dt = datetime.datetime.strptime(data_str[:16], fmt)
                                dias = (datetime.datetime.now() - dt).days
                                return dias
                            except:
                                continue
            # Fallback para valor original
            val = row.get("Parado (dias)")
            if pd.notna(val):
                return val
            return None
        
        df_tbl["Último andamento"] = df_tbl.apply(get_ultimo_andamento_integrado, axis=1)
        df_tbl["Data do status"] = df_tbl.apply(get_data_status_integrado, axis=1)
        df_tbl["Parado (dias)"] = df_tbl.apply(get_parado_dias_integrado, axis=1)
        
        # Atualizar "Situação atual" com status do SENADO
        def get_situacao_integrada(row):
            if row.get("no_senado"):
                # Priorizar situação do Senado
                sit_senado = row.get("situacao_senado", "")
                if sit_senado and sit_senado.strip():
                    return f"🏛️ {sit_senado}"  # Emoji indica Senado
            return row.get("Situação atual", "")
        
        df_tbl["Situação atual"] = df_tbl.apply(get_situacao_integrada, axis=1)
        
        # Recalcular alerta com novos valores
        df_tbl["Alerta"] = df_tbl["Parado (dias)"].apply(get_alerta_emoji)
    else:
        df_tbl["Relator_Exibido"] = df_tbl.get("Relator(a)", "")
        df_tbl["Orgao_Exibido"] = df_tbl.get("Órgão (sigla)", "")
    
    # ============================================================
    # PREPARAR COLUNAS PARA EXIBIÇÃO
    # ============================================================
    st.markdown("---")
    st.markdown("#### 📋 Proposições encontradas")
    st.caption(f"Mostrando {min(20, len(df_tbl))} de {len(df_tbl)} resultados")
    
    if incluir_senado_tab5 and "no_senado" in df_tbl.columns:
        show_cols_r = [
            "Alerta", "Proposição", "Tipo", "Ano",
            "Situação atual", "Orgao_Exibido", "Relator_Exibido",
            "Último andamento", "Data do status", "Parado (dias)",
            "no_senado", "url_senado", "LinkTramitacao",
            "Ementa", "ID", "id_processo_senado", "codigo_materia_senado",
        ]
    else:
        show_cols_r = [
            "Alerta", "Proposição", "Tipo", "Ano",
            "Situação atual", "Órgão (sigla)", "Relator(a)",
            "Último andamento", "Data do status", "Parado (dias)", "LinkTramitacao",
            "Ementa", "ID",
        ]
    
    for c in show_cols_r:
        if c not in df_tbl.columns:
            df_tbl[c] = ""
    
    # DEBUG: Verificar dados ANTES de salvar
    _debug_situacao = df_tbl["Situação atual"].dropna().astype(str)
    _debug_situacao_ok = (_debug_situacao != "").sum()
    _debug_orgao = df_tbl.get("Órgão (sigla)", pd.Series()).dropna().astype(str)
    _debug_orgao_ok = (_debug_orgao != "").sum() if len(_debug_orgao) > 0 else 0
    
    if _debug_situacao_ok == 0 or _debug_orgao_ok == 0:
        st.warning(
            f"⚠️ DEBUG: Dados incompletos! Situação: {_debug_situacao_ok}/{len(df_tbl)}, "
            f"Órgão: {_debug_orgao_ok}/{len(df_tbl)}"
        )
    
    # Salvar DataFrame enriquecido completo
    df_existente = st.session_state.get("df_todas_enriquecido_tab5", pd.DataFrame())
    precisa_recriar = (
        df_existente.empty or 
        len(df_existente) != len(df_aut) or
        "Situação atual" not in df_existente.columns
    )
    
    if precisa_recriar:
        with st.spinner("Preparando base completa (primeira vez)..."):
            df_aut_completo = df_aut.copy()
            ids_todas = df_aut_completo["id"].astype(str).tolist()
            
            status_map_todas = provider.build_proposicoes_status_map(ids_todas)
            df_aut_enriquecido = provider.enrich_proposicoes_with_status(
                df_aut_completo,
                status_map_todas
            )
            
            # Renomear colunas
            df_aut_enriquecido = df_aut_enriquecido.rename(
                columns={
                    "Proposicao": "Proposição",
                    "ementa": "Ementa",
                    "id": "ID",
                    "ano": "Ano",
                    "siglaTipo": "Tipo"
                }
            )
            
            st.session_state["df_todas_enriquecido_tab5"] = df_aut_enriquecido
    
    # ============================================================
    # CONFIGURAR COLUNAS DE EXIBIÇÃO
    # ============================================================
    column_config_base = {
        "Alerta": st.column_config.TextColumn("", width="small", help="Urgência"),
        "LinkTramitacao": st.column_config.LinkColumn("🏛️ Câmara", display_text="Abrir"),
        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
    }
    
    if incluir_senado_tab5 and "no_senado" in df_tbl.columns:
        column_config_base.update({
            "Orgao_Exibido": st.column_config.TextColumn(
                "Órgão",
                width="medium",
                help="Órgão atual (Câmara ou Senado)"
            ),
            "Relator_Exibido": st.column_config.TextColumn(
                "Relator",
                width="medium",
                help="Relator atual (Câmara ou Senado)"
            ),
            "no_senado": st.column_config.CheckboxColumn("No Senado?", width="small"),
            "codigo_materia_senado": st.column_config.TextColumn(
                "Código Matéria",
                width="small",
                help="Código interno da matéria no Senado"
            ),
            "url_senado": st.column_config.LinkColumn(
                "🏛️ Senado",
                display_text="Abrir",
                help="Clique para abrir a página da matéria no Senado"
            ),
        })
    
    # ============================================================
    # TABELA INTERATIVA COM SELEÇÃO
    # ============================================================
    sel = st.dataframe(
        df_tbl[show_cols_r],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=column_config_base,
        key="df_busca_tab5"
    )
    
    st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")
    
    # ============================================================
    # DOWNLOADS
    # ============================================================
    col_x4, col_p4 = st.columns(2)
    
    with col_x4:
        try:
            bytes_rast, mime_rast, ext_rast = to_xlsx_bytes(df_tbl[show_cols_r], "Busca_Especifica")
            st.download_button(
                "⬇️ XLSX",
                data=bytes_rast,
                file_name=f"busca_especifica_proposicoes.{ext_rast}",
                mime=mime_rast,
                key="export_busca_xlsx_tab5"
            )
        except Exception as e:
            st.error(f"Erro ao gerar XLSX: {e}")
    
    with col_p4:
        try:
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tbl[show_cols_r], "Busca Específica")
            st.download_button(
                "⬇️ PDF",
                data=pdf_bytes,
                file_name=f"busca_especifica_proposicoes.{pdf_ext}",
                mime=pdf_mime,
                key="export_busca_pdf_tab5"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
    
    # ============================================================
    # DETALHES DA PROPOSIÇÃO SELECIONADA
    # ============================================================
    selected_id = None
    senado_data_row = None
    
    try:
        if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
            row_idx = sel["selection"]["rows"][0]
            row_data = df_tbl.iloc[row_idx]
            selected_id = str(row_data["ID"])
            
            # Construir senado_data para Linha do Tempo Unificada funcionar
            # (Após correção do bug rel_sen no monólito, isso é seguro)
            def safe_get(series, key, default=""):
                try:
                    val = series.get(key, default)
                    if pd.isna(val):
                        return default
                    return val
                except:
                    return default
            
            def safe_get_bool(series, key):
                try:
                    val = series.get(key, False)
                    if pd.isna(val):
                        return False
                    return bool(val)
                except:
                    return False
            
            senado_data_row = {
                "no_senado": safe_get_bool(row_data, "no_senado"),
                "codigo_materia_senado": safe_get(row_data, "codigo_materia_senado", ""),
                "id_processo_senado": safe_get(row_data, "id_processo_senado", ""),
                "situacao_senado": safe_get(row_data, "situacao_senado", ""),
                "url_senado": safe_get(row_data, "url_senado", ""),
                "Relator_Senado": safe_get(row_data, "Relator_Senado", ""),
                "Orgao_Senado_Sigla": safe_get(row_data, "Orgao_Senado_Sigla", ""),
                "Orgao_Senado_Nome": safe_get(row_data, "Orgao_Senado_Nome", ""),
                "UltimasMov_Senado": safe_get(row_data, "UltimasMov_Senado", ""),
            }
    except Exception:
        selected_id = None
        senado_data_row = None
    
    st.markdown("---")
    st.markdown("#### 📋 Detalhes da Proposição Selecionada")
    
    if not selected_id:
        st.info("Clique em uma proposição acima para ver detalhes completos.")
    else:
        # Passar senado_data para Linha do Tempo Unificada funcionar
        # Bug do rel_sen foi corrigido no monólito (linha 8125)
        exibir_detalhes_proposicao_func(
            selected_id,
            key_prefix="tab5",
            senado_data=senado_data_row
        )
