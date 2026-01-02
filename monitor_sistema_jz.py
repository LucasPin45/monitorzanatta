# monitor_sistema_jz.py - v25
# ============================================================
# Monitor Legislativo – Dep. Júlia Zanatta (Streamlit)
# VERSÃO 25: Chat IA integrado em todas as abas
# - Chat com IA nas abas 2-7 com contexto da aba
# - Saídas prontas (briefings, análises, checklists)
# - Modo especial para RICs com análise de prazos
# - Controles anti-alucinação
# - Convite para grupo Telegram na aba inicial
# - Layout wide fixo (sem redimensionamento ao clicar)
# - CSS estabilizado para evitar "pulos" na interface
# - Links clicáveis no PDF
# - Data da última tramitação (não data de cadastro)
# - Ordenação por data mais recente primeiro
# - Campo "Parado há (dias)" calculado
# - Relator com alerta de adversário (PT, PSOL, PCdoB, PSB, PV, Rede)
# - RIC: extração de prazo de resposta, ministério, status respondido
# ============================================================

import datetime
import concurrent.futures
import time
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
import re
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend não-interativo

# ============================================================
# MÓDULO CHAT IA (INLINE)
# ============================================================
# Código do chat_ia.py integrado diretamente para facilitar deploy

# --- Configuração da API ---
def get_api_key_chat() -> str:
    """Obtém a chave da API do Anthropic via st.secrets."""
    try:
        return st.secrets.get("anthropic", {}).get("api_key", "")
    except Exception:
        return ""

def is_chat_enabled() -> bool:
    """Verifica se o chat está habilitado (API key configurada)."""
    return bool(get_api_key_chat())

# --- System Prompts ---
CHAT_SYSTEM_PROMPT_BASE = """Você é um assistente legislativo especializado do Gabinete da Deputada Júlia Zanatta (PL-SC).

REGRAS FUNDAMENTAIS (NUNCA VIOLAR):
1. NUNCA invente números de proposições (PL, RIC, etc.), datas, prazos, órgãos ou status.
2. Se uma informação não constar nos dados fornecidos, diga: "Não consta na base do Monitor."
3. SEMPRE cite as fontes: IDs das proposições, colunas consultadas, datas dos dados.
4. Responda APENAS com base nos dados do contexto fornecido.
5. Use linguagem formal, técnica e institucional adequada ao ambiente parlamentar.

FORMATO DE RESPOSTA PADRÃO:
Suas respostas devem conter (quando aplicável):
- **Resumo**: Síntese em 2-3 frases
- **Situação atual**: O que está acontecendo agora
- **Próximo passo**: Ação prática recomendada
- **Riscos/Alertas**: Pontos de atenção
- **Fontes**: IDs e dados consultados

PERSONA ATUAL: {persona}

CONTEXTO DA ABA: {contexto_aba}
"""

CHAT_PERSONAS = {
    "Deputada": "Responda como se estivesse assessorando diretamente a Deputada Júlia Zanatta. Seja direto, estratégico e focado em decisões políticas.",
    "Chefe de Gabinete": "Responda como se estivesse orientando a equipe do gabinete. Foque em gestão, prazos, distribuição de tarefas e coordenação.",
    "Assessoria Legislativa": "Responda com foco técnico-legislativo. Detalhe procedimentos regimentais, prazos legais e aspectos jurídicos."
}

CHAT_CONTEXTOS_ABA = {
    "tab2": "Autoria & Relatoria na Pauta - Proposições de autoria da deputada ou onde ela é relatora que estão na pauta de votações.",
    "tab3": "Palavras-chave na Pauta - Proposições de interesse temático identificadas por palavras-chave configuradas.",
    "tab4": "Comissões Estratégicas - Eventos e pautas das comissões prioritárias (CDC, CCOM, CE, CREDN, CCJC).",
    "tab5": "Buscar Proposição - Busca livre por qualquer proposição da Câmara dos Deputados.",
    "tab6": "Matérias por Situação - Visão geral das proposições de autoria organizadas por situação atual.",
    "tab7": "RICs (Requerimentos de Informação) - Fiscalização do Executivo com controle de prazos de resposta."
}

# --- Templates de Saídas Prontas ---
CHAT_TEMPLATE_BRIEFING = """Gere um BRIEFING DE 30 SEGUNDOS.
REGRAS: Máximo 5 frases. Foco em: O que é, por que importa, o que fazer AGORA. Tom direto.
DADOS: {dados}
Gere o briefing:"""

CHAT_TEMPLATE_ANALISE = """Gere uma ANÁLISE TÉCNICA detalhada.
ESTRUTURA: 1. OBJETO 2. CONTEXTO 3. MÉRITO 4. TRAMITAÇÃO 5. POSICIONAMENTO SUGERIDO 6. FONTES
DADOS: {dados}
Gere a análise:"""

CHAT_TEMPLATE_ESTRATEGIA = """Gere orientações de ESTRATÉGIA REGIMENTAL.
FOCO: Ações práticas, instrumentos disponíveis, timing, articulação. NÃO cite artigos do RICD textualmente.
DADOS: {dados}
Gere a estratégia:"""

CHAT_TEMPLATE_PERGUNTAS = """Gere 2 a 4 PERGUNTAS PARA DEBATE.
CRITÉRIOS: Objetivas, provocativas, úteis para discurso, exponham contradições.
DADOS: {dados}
Gere as perguntas:"""

CHAT_TEMPLATE_CHECKLIST = """Gere um CHECKLIST DE PROVIDÊNCIAS.
FORMATO: Lista numerada com O QUE fazer, QUEM deve fazer, PRAZO sugerido. Ordenar por prioridade.
DADOS: {dados}
Gere o checklist:"""

CHAT_TEMPLATE_RESUMO = """Gere um RESUMO DA SEMANA.
ESTRUTURA: 1. DESTAQUES 2. MOVIMENTAÇÕES 3. PENDÊNCIAS 4. PRÓXIMA SEMANA 5. ALERTAS
DADOS: {dados}
Gere o resumo:"""

CHAT_TEMPLATE_COBRANCA = """Gere texto de COBRANÇA/FOLLOW-UP sobre RICs pendentes.
FORMATO: Tom formal mas firme. Identificar atrasados, órgão, prazo, sugerir ação.
DADOS: {dados}
Gere o texto:"""

CHAT_TEMPLATE_ACAO_RIC = """Analise RICs e sugira AÇÕES RECOMENDADAS.
OPÇÕES: Reiterar RIC, Novo RIC específico, Convocar ministro, Audiência pública, Acionar TCU, Elaborar PL, Arquivar.
DADOS: {dados}
Analise e recomende:"""

# --- Funções de Contexto ---
def chat_get_context(tab_id: str, df_filtrado: pd.DataFrame, filtros: dict = None, selecionado: dict = None, max_rows: int = 200) -> dict:
    """Extrai contexto estruturado de uma aba para enviar à IA."""
    filtros = filtros or {}
    selecionado = selecionado or {}
    
    # Se há item selecionado mas df vazio, tentar buscar dados do item
    dados_item_selecionado = ""
    if selecionado.get("id") and (df_filtrado is None or df_filtrado.empty):
        try:
            id_sel = str(selecionado["id"])
            # Buscar dados da proposição selecionada
            dados_prop = fetch_proposicao_completa(id_sel)
            if dados_prop:
                dados_item_selecionado = f"""
DADOS DA PROPOSIÇÃO SELECIONADA (ID {id_sel}):
- Tipo: {dados_prop.get('sigla', 'N/A')}
- Número/Ano: {dados_prop.get('numero', 'N/A')}/{dados_prop.get('ano', 'N/A')}
- Ementa: {dados_prop.get('ementa', 'N/A')[:300]}
- Situação: {dados_prop.get('status_descricaoSituacao', 'N/A')}
- Órgão atual: {dados_prop.get('status_siglaOrgao', 'N/A')}
- Último andamento: {dados_prop.get('status_descricaoTramitacao', 'N/A')[:200]}
- Data status: {dados_prop.get('status_dataHora', 'N/A')[:10] if dados_prop.get('status_dataHora') else 'N/A'}
"""
                # Relator
                relator = dados_prop.get('relator', {})
                if relator and relator.get('nome'):
                    dados_item_selecionado += f"- Relator(a): {relator.get('nome', '')} ({relator.get('partido', '')}-{relator.get('uf', '')})\n"
        except Exception:
            pass
    
    meta = {
        "tab_id": tab_id,
        "tab_descricao": CHAT_CONTEXTOS_ABA.get(tab_id, "Aba não identificada"),
        "total_registros": len(df_filtrado) if df_filtrado is not None and not df_filtrado.empty else (1 if dados_item_selecionado else 0),
        "colunas": list(df_filtrado.columns) if df_filtrado is not None and not df_filtrado.empty else [],
        "filtros_ativos": filtros,
        "item_selecionado": selecionado,
        "data_consulta": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    
    contexto_partes = [
        f"Aba: {meta['tab_descricao']}",
        f"Total de registros visíveis: {meta['total_registros']}",
        f"Data da consulta: {meta['data_consulta']}"
    ]
    
    if filtros:
        filtros_str = ", ".join([f"{k}={v}" for k, v in filtros.items() if v])
        if filtros_str:
            contexto_partes.append(f"Filtros aplicados: {filtros_str}")
    
    if selecionado:
        sel_str = ", ".join([f"{k}={v}" for k, v in selecionado.items() if v])
        if sel_str:
            contexto_partes.append(f"Item selecionado: {sel_str}")
    
    contexto_textual = "\n".join(contexto_partes)
    
    # Se temos dados do item selecionado, usar isso
    if dados_item_selecionado:
        tabela_compacta = dados_item_selecionado
    elif df_filtrado is not None and not df_filtrado.empty:
        # Pegar TODAS as linhas (até max_rows) para dar contexto completo
        df_amostra = df_filtrado.head(max_rows)
        
        # Selecionar colunas mais relevantes
        colunas_prioridade = [
            "ID", "id", "Proposição", "Proposicao", "siglaTipo", "numero", "ano", 
            "Ementa", "ementa", "Situação atual", "Órgão (sigla)", "Data do status", 
            "Parado (dias)", "Relator(a)", "Tema", "Último andamento",
            "RIC_Ministerio", "RIC_StatusResposta", "RIC_DiasRestantes", "RIC_PrazoStr"
        ]
        colunas_disponiveis = [c for c in colunas_prioridade if c in df_amostra.columns]
        if not colunas_disponiveis:
            colunas_disponiveis = list(df_amostra.columns)[:10]
        
        df_resumo = df_amostra[colunas_disponiveis].copy()
        
        # Truncar textos longos mas manter informação suficiente
        for col in df_resumo.columns:
            if df_resumo[col].dtype == 'object':
                df_resumo[col] = df_resumo[col].astype(str).str[:150]  # Aumentado de 120 para 150
        
        tabela_compacta = df_resumo.to_string(index=False, max_colwidth=80)  # Aumentado de 60 para 80
        
        # Se a base for grande, adicionar estatísticas
        if len(df_filtrado) > max_rows:
            tabela_compacta += f"\n\n[... e mais {len(df_filtrado) - max_rows} registros não exibidos ...]"
            tabela_compacta += f"\n\nNOTA: Para buscar em toda a base, use termos específicos na pergunta."
    else:
        tabela_compacta = "Nenhum dado disponível. Carregue os dados da aba primeiro clicando no botão de carregar."
    
    return {"contexto_textual": contexto_textual, "tabela_compacta": tabela_compacta, "metadados": meta}

def chat_format_context(contexto: dict) -> str:
    """Formata o contexto para incluir no prompt."""
    return f"""
=== CONTEXTO DOS DADOS ===
{contexto.get("contexto_textual", "")}

AMOSTRA DOS DADOS:
{contexto.get("tabela_compacta", "Nenhum dado disponível")}

Colunas disponíveis: {', '.join(contexto.get('metadados', {}).get('colunas', [])[:15])}
========================
"""

# --- Análise específica de RICs ---
def chat_analisar_rics(df_rics: pd.DataFrame) -> str:
    """Gera contexto textual específico para RICs."""
    if df_rics is None or df_rics.empty:
        return "Nenhum RIC carregado."
    
    total = len(df_rics)
    aguardando = 0
    respondidos = 0
    atrasados = 0
    vencendo_7_dias = 0
    
    if "RIC_StatusResposta" in df_rics.columns:
        aguardando = len(df_rics[df_rics["RIC_StatusResposta"].str.contains("Aguardando", case=False, na=False)])
        respondidos = len(df_rics[df_rics["RIC_StatusResposta"].str.contains("Respondido", case=False, na=False)])
        atrasados = len(df_rics[df_rics["RIC_StatusResposta"].str.contains("Fora do prazo|Vencido", case=False, na=False)])
    
    if "RIC_DiasRestantes" in df_rics.columns:
        for _, row in df_rics.iterrows():
            dias = row.get("RIC_DiasRestantes")
            if pd.notna(dias):
                try:
                    dias = int(dias)
                    if dias < 0:
                        atrasados = max(atrasados, 1)
                    elif 0 <= dias <= 7:
                        vencendo_7_dias += 1
                except (ValueError, TypeError):
                    pass
    
    alertas = []
    if atrasados > 0:
        alertas.append(f"🔴 {atrasados} RIC(s) com prazo VENCIDO")
    if vencendo_7_dias > 0:
        alertas.append(f"🟠 {vencendo_7_dias} RIC(s) vencem nos próximos 7 dias")
    
    partes = [
        f"ANÁLISE DOS RICs:",
        f"- Total: {total}",
        f"- Aguardando resposta: {aguardando}",
        f"- Respondidos: {respondidos}",
        f"- Atrasados: {atrasados}",
        f"- Vencendo em 7 dias: {vencendo_7_dias}",
    ]
    
    if alertas:
        partes.append("\nALERTAS:")
        partes.extend([f"  {a}" for a in alertas])
    
    # Por ministério
    if "RIC_Ministerio" in df_rics.columns:
        partes.append("\nPOR MINISTÉRIO (top 5):")
        for ministerio in df_rics["RIC_Ministerio"].value_counts().head(5).index:
            if ministerio and str(ministerio).strip():
                qtd = len(df_rics[df_rics["RIC_Ministerio"] == ministerio])
                partes.append(f"  - {ministerio}: {qtd}")
    
    return "\n".join(partes)

# --- Chamada à API ---
def chat_chamar_api(mensagens: list, system_prompt: str, max_tokens: int = 1500) -> tuple:
    """Chama a API do Anthropic (Claude)."""
    api_key = get_api_key_chat()
    if not api_key:
        return "❌ API não configurada. Adicione a chave em Settings > Secrets.", False
    
    try:
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": mensagens
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            texto = ""
            for bloco in data.get("content", []):
                if bloco.get("type") == "text":
                    texto += bloco.get("text", "")
            return texto, True
        else:
            return f"❌ Erro na API: {response.status_code} - {response.text[:200]}", False
            
    except Exception as e:
        return f"❌ Erro ao chamar API: {str(e)}", False

# --- Componente de Chat ---
def render_chat_ia(tab_id: str, df_contexto: pd.DataFrame, filtros: dict = None, selecionado: dict = None):
    """Renderiza o componente de chat em uma aba."""
    
    # Verificar se API está configurada
    if not is_chat_enabled():
        with st.expander("💬 Chat IA (configurar)", expanded=False):
            st.warning("Chat IA indisponível - Configure a chave da API Anthropic em Settings > Secrets")
            st.code('[anthropic]\napi_key = "sua-chave-aqui"', language="toml")
        return
    
    # Chaves de session_state
    history_key = f"chat_history_{tab_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    
    # Container do chat
    with st.expander("💬 Chat IA", expanded=False):
        # Seletor de modo e persona
        col_modo, col_persona = st.columns(2)
        
        with col_modo:
            modo = st.selectbox(
                "Modo",
                options=["Base", "RICs"] if tab_id == "tab7" else ["Base"],
                index=0,
                key=f"chat_modo_{tab_id}",
                help="Base: responde só com dados. RICs: especializado em requerimentos."
            )
        
        with col_persona:
            persona = st.selectbox(
                "Persona",
                options=list(CHAT_PERSONAS.keys()),
                index=2,
                key=f"chat_persona_{tab_id}"
            )
        
        # Botões de saídas prontas
        st.markdown("**Saídas prontas:**")
        
        if tab_id == "tab7":
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                btn_briefing = st.button("📋 Briefing", key=f"chat_brief_{tab_id}", use_container_width=True)
            with c2:
                btn_cobranca = st.button("📨 Cobrança", key=f"chat_cobr_{tab_id}", use_container_width=True)
            with c3:
                btn_acao = st.button("🎯 Ação", key=f"chat_acao_{tab_id}", use_container_width=True)
            with c4:
                btn_checklist = st.button("✅ Checklist", key=f"chat_check_{tab_id}", use_container_width=True)
            
            btn_analise = btn_estrategia = btn_perguntas = False
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                btn_briefing = st.button("📋 Briefing", key=f"chat_brief_{tab_id}", use_container_width=True)
            with c2:
                btn_analise = st.button("📊 Análise", key=f"chat_anal_{tab_id}", use_container_width=True)
            with c3:
                btn_estrategia = st.button("⚔️ Estratégia", key=f"chat_estr_{tab_id}", use_container_width=True)
            with c4:
                btn_checklist = st.button("✅ Checklist", key=f"chat_check_{tab_id}", use_container_width=True)
            
            btn_cobranca = btn_acao = False
        
        # Botão limpar
        if st.button("🗑️ Limpar conversa", key=f"chat_limpar_{tab_id}"):
            st.session_state[history_key] = []
            st.rerun()
        
        # Preparar contexto
        contexto = chat_get_context(tab_id, df_contexto, filtros, selecionado)
        contexto_formatado = chat_format_context(contexto)
        
        # Adicionar contexto de RICs se aplicável
        if tab_id == "tab7" and df_contexto is not None:
            contexto_formatado += "\n\n" + chat_analisar_rics(df_contexto)
        
        # Processar botões
        prompt_auto = None
        nome_saida = None
        
        if btn_briefing:
            prompt_auto = CHAT_TEMPLATE_BRIEFING.format(dados=contexto_formatado)
            nome_saida = "📋 Briefing 30s"
        elif btn_checklist:
            prompt_auto = CHAT_TEMPLATE_CHECKLIST.format(dados=contexto_formatado)
            nome_saida = "✅ Checklist"
        elif btn_cobranca:
            prompt_auto = CHAT_TEMPLATE_COBRANCA.format(dados=contexto_formatado)
            nome_saida = "📨 Cobrança"
        elif btn_acao:
            prompt_auto = CHAT_TEMPLATE_ACAO_RIC.format(dados=contexto_formatado)
            nome_saida = "🎯 Ação recomendada"
        elif btn_analise:
            prompt_auto = CHAT_TEMPLATE_ANALISE.format(dados=contexto_formatado)
            nome_saida = "📊 Análise técnica"
        elif btn_estrategia:
            prompt_auto = CHAT_TEMPLATE_ESTRATEGIA.format(dados=contexto_formatado)
            nome_saida = "⚔️ Estratégia"
        
        # Exibir histórico
        for msg in st.session_state[history_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Input do usuário
        user_input = st.chat_input("Pergunte sobre os dados...", key=f"chat_input_{tab_id}")
        
        # Processar input
        input_final = prompt_auto or user_input
        
        if input_final:
            # Adicionar mensagem ao histórico
            if user_input:
                st.session_state[history_key].append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
            elif nome_saida:
                st.session_state[history_key].append({"role": "user", "content": f"[{nome_saida}]"})
                with st.chat_message("user"):
                    st.markdown(f"[{nome_saida}]")
            
            # Preparar system prompt COM O CONTEXTO DOS DADOS
            system = CHAT_SYSTEM_PROMPT_BASE.format(
                persona=CHAT_PERSONAS.get(persona, CHAT_PERSONAS["Assessoria Legislativa"]),
                contexto_aba=CHAT_CONTEXTOS_ABA.get(tab_id, "")
            )
            
            # IMPORTANTE: Adicionar o contexto dos dados ao system prompt
            system += f"\n\n{contexto_formatado}"
            
            # Preparar mensagens
            mensagens_api = []
            for msg in st.session_state[history_key][-8:]:
                mensagens_api.append({"role": msg["role"], "content": msg["content"]})
            
            if prompt_auto:
                mensagens_api.append({"role": "user", "content": prompt_auto})
            elif user_input:
                # Para perguntas livres, incluir o contexto junto com a pergunta
                pergunta_com_contexto = f"Com base nos dados abaixo, responda: {user_input}\n\nDADOS ATUAIS:\n{contexto_formatado}"
                mensagens_api.append({"role": "user", "content": pergunta_com_contexto})
            
            # Chamar API
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    resposta, sucesso = chat_chamar_api(mensagens_api, system)
                    st.markdown(resposta)
            
            st.session_state[history_key].append({"role": "assistant", "content": resposta})
        
        # Info do contexto (para debug)
        with st.expander("📊 Contexto atual (debug)", expanded=False):
            st.caption(f"**Registros no contexto:** {contexto.get('metadados', {}).get('total_registros', 0)}")
            st.caption(f"**Colunas:** {len(contexto.get('metadados', {}).get('colunas', []))}")
            if contexto.get('metadados', {}).get('filtros_ativos'):
                st.caption(f"**Filtros:** {contexto.get('metadados', {}).get('filtros_ativos')}")
            st.text_area("Dados enviados para IA:", value=contexto.get('tabela_compacta', '')[:2000], height=150, disabled=True, key=f"debug_contexto_{tab_id}")


# ============================================================
# CONFIGURAÇÃO DA PÁGINA (OBRIGATORIAMENTE PRIMEIRA CHAMADA ST)
# ============================================================

st.set_page_config(
    page_title="Monitor Legislativo – Dep. Júlia Zanatta",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CONTROLE DE ACESSO — ACESSO RESTRITO AO GABINETE
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("## 🔒 Acesso restrito – Gabinete da Deputada Júlia Zanatta")
    st.markdown("Este sistema é de uso interno do gabinete.")

    senha = st.text_input("Digite a senha de acesso", type="password")

    senha_correta = st.secrets.get("auth", {}).get("senha")
    if not senha_correta:
        st.error("Erro de configuração: defina [auth].senha em Settings → Secrets.")
        st.stop()

    if senha:
        if senha == senha_correta:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta")

    st.stop()


# ============================================================
# TIMEZONE DE BRASÍLIA
# ============================================================

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


def get_brasilia_now():
    """Retorna datetime atual no fuso de Brasília."""
    return datetime.datetime.now(TZ_BRASILIA)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559

HEADERS = {"User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Vacinas", "Armas", "Arma", "Armamento", "Aborto", "Conanda", 
    "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF", "Logística"
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

# ============================================================
# NORMALIZAÇÃO DE MINISTÉRIOS (nomes canônicos)
# ============================================================
# Mapeamento de variações textuais para nomes canônicos únicos

MINISTERIOS_CANONICOS = {
    # Ministério da Agricultura e Pecuária
    "Ministério da Agricultura e Pecuária": [
        "agricultura", "pecuária", "pecuaria", "agro", "agropecuária", "agropecuaria",
        "agricultura e pecuária", "agricultura e pecuaria", "mapa", "favaro",
        "ministro de estado da agricultura", "ministério da agricultura"
    ],
    
    # Ministério das Cidades
    "Ministério das Cidades": [
        "cidades", "ministério das cidades", "ministerio das cidades", "jader filho"
    ],
    
    # Ministério da Ciência, Tecnologia e Inovação
    "Ministério da Ciência, Tecnologia e Inovação": [
        "ciência", "ciencia", "tecnologia", "inovação", "inovacao", "mcti",
        "ciência e tecnologia", "ciencia e tecnologia", "luciana santos"
    ],
    
    # Ministério das Comunicações
    "Ministério das Comunicações": [
        "comunicações", "comunicacoes", "correios", "ect", "anatel", "juscelino",
        "ministério das comunicações", "ministerio das comunicacoes", "telecomunicações"
    ],
    
    # Ministério da Cultura
    "Ministério da Cultura": [
        "cultura", "ministério da cultura", "ministerio da cultura", "minc", "margareth menezes"
    ],
    
    # Ministério da Defesa
    "Ministério da Defesa": [
        "defesa", "forças armadas", "forcas armadas", "exército", "exercito",
        "marinha", "aeronáutica", "aeronautica", "múcio", "mucio", "militar",
        "ministério da defesa", "ministerio da defesa"
    ],
    
    # Ministério do Desenvolvimento Agrário
    "Ministério do Desenvolvimento Agrário": [
        "desenvolvimento agrário", "desenvolvimento agrario", "reforma agrária",
        "reforma agraria", "mda", "agricultura familiar", "assentamento"
    ],
    
    # Ministério do Desenvolvimento e Assistência Social
    "Ministério do Desenvolvimento e Assistência Social": [
        "desenvolvimento social", "assistência social", "assistencia social",
        "bolsa família", "bolsa familia", "wellington dias", "combate à fome",
        "combate a fome", "mds", "desenvolvimento e assistência"
    ],
    
    # Ministério do Desenvolvimento, Indústria, Comércio e Serviços
    "Ministério do Desenvolvimento, Indústria, Comércio e Serviços": [
        "desenvolvimento", "indústria", "industria", "comércio", "comercio",
        "mdic", "desenvolvimento industrial", "geraldo alckmin"
    ],
    
    # Ministério da Educação
    "Ministério da Educação": [
        "educação", "educacao", "mec", "escola", "universidade", "ensino",
        "camilo santana", "ministério da educação", "ministerio da educacao",
        "enem", "fies", "prouni"
    ],
    
    # Ministério do Esporte
    "Ministério do Esporte": [
        "esporte", "esportes", "ministério do esporte", "ministerio do esporte", "andré fufuca"
    ],
    
    # Ministério da Fazenda
    "Ministério da Fazenda": [
        "fazenda", "haddad", "receita federal", "imposto", "tributo",
        "economia", "ministério da fazenda", "ministerio da fazenda",
        "tesouro", "fiscal"
    ],
    
    # Ministério da Gestão e da Inovação em Serviços Públicos
    "Ministério da Gestão e da Inovação em Serviços Públicos": [
        "gestão", "gestao", "inovação em serviços", "inovacao em servicos",
        "gestão e inovação", "gestao e inovacao", "serviços públicos",
        "servicos publicos", "esther dweck", "mgi"
    ],
    
    # Ministério da Igualdade Racial
    "Ministério da Igualdade Racial": [
        "igualdade racial", "racial", "ministério da igualdade racial",
        "ministerio da igualdade racial", "anielle franco"
    ],
    
    # Ministério da Integração e do Desenvolvimento Regional
    "Ministério da Integração e do Desenvolvimento Regional": [
        "integração", "integracao", "desenvolvimento regional", "midr",
        "ministério da integração", "ministerio da integracao", "waldez góes"
    ],
    
    # Ministério da Justiça e Segurança Pública
    "Ministério da Justiça e Segurança Pública": [
        "justiça", "justica", "segurança pública", "seguranca publica",
        "polícia federal", "policia federal", "pf", "lewandowski",
        "ministério da justiça", "ministerio da justica", "mjsp",
        "de justiça e segurança pública", "justiça e segurança",
        "diretor-geral da pf", "diretor geral da pf", "diretor da pf",
        "javali", "javalis", "caça de javalis", "controle de fauna"
    ],
    
    # Ministério do Meio Ambiente e Mudança do Clima
    "Ministério do Meio Ambiente e Mudança do Clima": [
        "meio ambiente", "ambiente", "ambiental", "ibama", "clima",
        "mudança do clima", "mudanca do clima", "floresta", "marina silva",
        "mma", "ministério do meio ambiente", "ministerio do meio ambiente"
    ],
    
    # Ministério de Minas e Energia
    "Ministério de Minas e Energia": [
        "minas e energia", "energia", "petróleo", "petroleo", "petrobras",
        "alexandre silveira", "mme", "elétrica", "eletrica", "aneel"
    ],
    
    # Ministério das Mulheres
    "Ministério das Mulheres": [
        "mulheres", "ministério das mulheres", "ministerio das mulheres",
        "aparecida gonçalves", "aparecida goncalves", "cida gonçalves"
    ],
    
    # Ministério da Pesca e Aquicultura
    "Ministério da Pesca e Aquicultura": [
        "pesca", "aquicultura", "pescador", "ministério da pesca",
        "ministerio da pesca", "andré de paula"
    ],
    
    # Ministério do Planejamento e Orçamento
    "Ministério do Planejamento e Orçamento": [
        "planejamento", "orçamento", "orcamento", "ministério do planejamento",
        "ministerio do planejamento", "simone tebet", "mpo"
    ],
    
    # Ministério dos Povos Indígenas
    "Ministério dos Povos Indígenas": [
        "povos indígenas", "povos indigenas", "indígena", "indigena",
        "funai", "demarcação", "demarcacao", "sonia guajajara", "sônia guajajara"
    ],
    
    # Ministério da Previdência Social
    "Ministério da Previdência Social": [
        "previdência", "previdencia", "inss", "aposentadoria",
        "ministério da previdência", "ministerio da previdencia", "carlos lupi"
    ],
    
    # Ministério das Relações Exteriores
    "Ministério das Relações Exteriores": [
        "relações exteriores", "relacoes exteriores", "itamaraty", "embaixada",
        "exterior", "mauro vieira", "mre", "chanceler", "diplomacia"
    ],
    
    # Ministério da Saúde
    "Ministério da Saúde": [
        "saúde", "saude", "anvisa", "sus", "vacina", "medicamento",
        "hospital", "nísia trindade", "nisia trindade", "ministério da saúde",
        "ministerio da saude", "ms"
    ],
    
    # Ministério do Trabalho e Emprego
    "Ministério do Trabalho e Emprego": [
        "trabalho", "emprego", "trabalhista", "clt", "luiz marinho",
        "ministério do trabalho", "ministerio do trabalho", "mte"
    ],
    
    # Ministério dos Transportes
    "Ministério dos Transportes": [
        "transportes", "transporte", "rodovia", "ferrovia", "antt",
        "renan filho", "ministério dos transportes", "ministerio dos transportes",
        "estado dos transportes"
    ],
    
    # Ministério do Turismo
    "Ministério do Turismo": [
        "turismo", "ministério do turismo", "ministerio do turismo", "celso sabino"
    ],
    
    # Ministério dos Direitos Humanos e da Cidadania
    "Ministério dos Direitos Humanos e da Cidadania": [
        "direitos humanos", "cidadania", "conanda", "lgbtq", "macaé evaristo",
        "macae evaristo", "ministério dos direitos humanos",
        "ministerio dos direitos humanos", "mdhc"
    ],
    
    # Ministério dos Portos e Aeroportos
    "Ministério dos Portos e Aeroportos": [
        "portos", "aeroportos", "porto", "aeroporto", "ministério dos portos",
        "ministerio dos portos", "silvio costa filho"
    ],
    
    # Ministério do Empreendedorismo, da Microempresa e da Empresa de Pequeno Porte
    "Ministério do Empreendedorismo": [
        "empreendedorismo", "microempresa", "pequeno porte", "márcio frança",
        "marcio franca", "microempreendedor individual", "simples nacional",
        "ministério do empreendedorismo", "empresa de pequeno porte"
    ],
    
    # Casa Civil da Presidência da República
    "Casa Civil": [
        "casa civil", "rui costa", "planalto", "ministro-chefe da casa civil",
        "ministro chefe da casa civil", "agenda presidencial", "agendas da presidência",
        "agendas presidenciais", "secretaria extraordinária", "secretaria extraordinaria",
        "reconstrução do rs", "reconstrucao do rs", "rio grande do sul",
        "primeira-dama", "primeira dama", "rosângela da silva", "rosangela da silva", 
        "janja", "cop-30", "cop30", "cop 30", "contrato internacional", 
        "coordenação interministerial", "oei", "olimpíadas", "olimpiadas"
    ],
    
    # Secretaria de Comunicação Social (SECOM)
    "Secretaria de Comunicação Social (SECOM)": [
        "secom", "secretaria de comunicação social", "secretaria de comunicacao social",
        "comunicação social", "comunicacao social", "publicidade", "verbas publicitárias",
        "verbas publicitarias", "influenciadores digitais", "influenciador digital",
        "veículos de comunicação", "veiculos de comunicacao", "repasses a veículos",
        "publicidade do governo", "publicidade institucional", "publicidade federal",
        "despesas com publicidade", "banco do brasil publicidade", "caixa publicidade"
    ],
    
    # Secretaria de Relações Institucionais (SRI)
    "Secretaria de Relações Institucionais (SRI)": [
        "sri", "secretaria de relações institucionais", "secretaria de relacoes institucionais",
        "relações institucionais", "relacoes institucionais", "gleisi hoffmann",
        "gleisi", "emendas parlamentares", "articulação política", "articulacao politica"
    ],
    
    # Secretaria-Geral da Presidência
    "Secretaria-Geral da Presidência": [
        "secretaria-geral", "secretaria geral", "presidência da república",
        "presidencia da republica"
    ],
    
    # Gabinete de Segurança Institucional
    "Gabinete de Segurança Institucional": [
        "gsi", "segurança institucional", "seguranca institucional",
        "gabinete de segurança", "marcos antonio amaro"
    ],
    
    # Advocacia-Geral da União
    "Advocacia-Geral da União": [
        "agu", "advocacia-geral", "advocacia geral", "jorge messias"
    ],
    
    # Controladoria-Geral da União
    "Controladoria-Geral da União": [
        "cgu", "controladoria", "vinícius de carvalho", "vinicius de carvalho"
    ],
    
    # Banco Central
    "Banco Central do Brasil": [
        "banco central", "bacen", "bcb", "galípolo", "galipolo", "campos neto"
    ],
}


def normalize_ministerio(texto: str) -> str:
    """
    Normaliza o nome do ministério para uma nomenclatura canônica única.
    
    Regras:
    - Remove acentos e converte para minúsculas
    - Ignora nomes de ministros, cargos, artigos
    - Para keywords curtas (<6 chars), usa word boundary para evitar falsos positivos
    - Retorna o nome canônico ou "Não identificado"
    """
    if not texto:
        return "Não identificado"
    
    # Normalizar texto: remover acentos, lowercase
    texto_norm = texto.lower().strip()
    
    # Remover acentos
    texto_norm = unicodedata.normalize('NFD', texto_norm)
    texto_norm = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    
    # Remover termos genéricos
    termos_remover = [
        "ministro de estado", "ministra de estado", "ministro", "ministra",
        "sr.", "sra.", "senhor", "senhora", "exmo.", "exma.",
        "chefe da", "chefe do", "chefe", "ao ", "a ", "do ", "da ", "de ", "dos ", "das "
    ]
    
    for termo in termos_remover:
        texto_norm = texto_norm.replace(termo, " ")
    
    # Limpar espaços extras
    texto_norm = " ".join(texto_norm.split())
    
    # Procurar correspondência nos ministérios canônicos
    melhor_match = None
    melhor_score = 0
    
    for nome_canonico, keywords in MINISTERIOS_CANONICOS.items():
        for kw in keywords:
            # Normalizar keyword também
            kw_norm = unicodedata.normalize('NFD', kw.lower())
            kw_norm = ''.join(c for c in kw_norm if unicodedata.category(c) != 'Mn')
            
            # Para keywords curtas, usar word boundary para evitar falsos positivos
            if len(kw_norm) < 6:
                # Usar regex com word boundary
                pattern = r'\b' + re.escape(kw_norm) + r'\b'
                if re.search(pattern, texto_norm):
                    score = len(kw_norm) + 10  # Bonus por match exato
                    if score > melhor_score:
                        melhor_score = score
                        melhor_match = nome_canonico
            else:
                # Para keywords longas, substring match é ok
                if kw_norm in texto_norm:
                    # Priorizar matches mais longos (mais específicos)
                    score = len(kw_norm)
                    if score > melhor_score:
                        melhor_score = score
                        melhor_match = nome_canonico
    
    return melhor_match if melhor_match else "Não identificado"


def canonical_situacao(situacao: str) -> str:
    """
    Normaliza o texto da situação de uma proposição.
    Retorna o texto limpo e padronizado.
    """
    if not situacao:
        return ""
    
    # Limpar e normalizar
    texto = str(situacao).strip()
    
    # Remover múltiplos espaços
    texto = " ".join(texto.split())
    
    return texto


# Mapeamento legado (mantido para compatibilidade)
MINISTERIOS_KEYWORDS = MINISTERIOS_CANONICOS

# Palavras-chave para detectar resposta em RICs
RIC_RESPOSTA_KEYWORDS = [
    "resposta", "encaminha resposta", "recebimento de resposta", 
    "resposta do poder executivo", "resposta ao requerimento",
    "resposta do ministério", "resposta do ministerio", "atendimento ao requerimento"
]

# Temas para categorização (palavras-chave por tema)
TEMAS_CATEGORIAS = {
    "Saúde": [
        "vacina", "saude", "saúde", "hospital", "medicamento", "sus", "anvisa", 
        "medico", "médico", "enfermeiro", "farmacia", "farmácia", "tratamento",
        "doenca", "doença", "epidemia", "pandemia", "leito", "uti", "plano de saude"
    ],
    "Segurança Pública": [
        "arma", "armas", "seguranca", "segurança", "policia", "polícia", "violencia", 
        "violência", "crime", "criminal", "penal", "prisao", "prisão", "preso",
        "bandido", "trafic", "roubo", "furto", "homicidio", "homicídio", "legítima defesa",
        "porte", "posse de arma", "cac", "atirador", "caçador", "colecionador"
    ],
    "Economia e Tributos": [
        "pix", "drex", "imposto", "irpf", "tributo", "economia", "financeiro",
        "taxa", "contribuicao", "contribuição", "fiscal", "orcamento", "orçamento",
        "divida", "dívida", "inflacao", "inflação", "juros", "banco", "credito", "crédito",
        "renda", "salario", "salário", "aposentadoria", "previdencia", "previdência",
        "inss", "fgts", "trabalhista", "clt", "emprego", "desemprego"
    ],
    "Família e Costumes": [
        "aborto", "conanda", "crianca", "criança", "menor", "familia", "família",
        "genero", "gênero", "ideologia", "lgb", "trans", "casamento", "uniao", "união",
        "mae", "mãe", "pai", "filho", "maternidade", "paternidade", "nascituro",
        "vida", "pro-vida", "pró-vida", "adocao", "adoção", "tutela", "guarda"
    ],
    "Educação": [
        "educacao", "educação", "escola", "ensino", "universidade", "professor",
        "aluno", "estudante", "enem", "vestibular", "mec", "fundeb", "creche",
        "alfabetizacao", "alfabetização", "curriculo", "currículo", "didatico", "didático"
    ],
    "Agronegócio": [
        "agro", "rural", "fazenda", "produtor", "agricult", "pecuaria", "pecuária",
        "gado", "soja", "milho", "cafe", "café", "cana", "algodao", "algodão",
        "fertilizante", "agrotox", "defensivo", "irrigacao", "irrigação", "funrural",
        "terra", "propriedade rural", "mst", "invasao", "invasão", "demarcacao", "demarcação"
    ],
    "Meio Ambiente": [
        "ambiente", "ambiental", "clima", "floresta", "desmatamento", "ibama",
        "icmbio", "reserva", "unidade de conserv", "carbono", "emissao", "emissão",
        "poluicao", "poluição", "saneamento", "residuo", "resíduo", "lixo", "reciclagem"
    ],
    "Comunicação e Tecnologia": [
        "internet", "digital", "tecnologia", "telecom", "comunicacao", "comunicação",
        "imprensa", "midia", "mídia", "censura", "liberdade de expressao", "expressão",
        "rede social", "plataforma", "fake news", "desinformacao", "desinformação",
        "inteligencia artificial", "ia", "dados pessoais", "lgpd", "privacidade"
    ],
    "Administração Pública": [
        "servidor", "funcionalismo", "concurso", "licitacao", "licitação", "contrato",
        "administracao", "administração", "gestao", "gestão", "ministerio", "ministério",
        "autarquia", "estatal", "privatizacao", "privatização", "reforma administrativa"
    ],
    "Transporte e Infraestrutura": [
        "transporte", "rodovia", "ferrovia", "aeroporto", "porto", "infraestrutura",
        "mobilidade", "transito", "trânsito", "veiculo", "veículo", "combustivel", "combustível",
        "pedagio", "pedágio", "concessao", "concessão", "obra", "construcao", "construção"
    ],
    "Defesa e Soberania": [
        "defesa", "militar", "forcas armadas", "forças armadas", "exercito", "exército",
        "marinha", "aeronautica", "aeronáutica", "fronteira", "soberania", "nacional",
        "estrategico", "estratégico", "inteligencia", "inteligência", "espionagem"
    ],
    "Direito e Justiça": [
        "justica", "justiça", "judiciario", "judiciário", "tribunal", "stf", "stj",
        "magistrado", "juiz", "promotor", "advogado", "oab", "processo", "recurso",
        "habeas corpus", "prisao", "prisão", "inquerito", "inquérito", "investigacao", "investigação"
    ],
    "Relações Exteriores": [
        "internacional", "exterior", "diplomacia", "embaixada", "consulado",
        "mercosul", "brics", "onu", "tratado", "acordo internacional", "exportacao", "exportação",
        "importacao", "importação", "alfandega", "alfândega", "comercio exterior", "comércio exterior"
    ],
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


def camara_link_deputado(id_deputado: str) -> str:
    """Gera link para a página do deputado na Câmara."""
    if not id_deputado or str(id_deputado).strip() in ('', 'nan', 'None'):
        return ""
    return f"https://www.camara.leg.br/deputados/{str(id_deputado).strip()}"


# ============================================================
# FUNÇÕES AUXILIARES PARA RIC (Prazo de Resposta)
# ============================================================


# ============================================================
# NOTIFICAÇÕES - TELEGRAM
# ============================================================

def telegram_enviar_mensagem(bot_token: str, chat_id: str, mensagem: str, parse_mode: str = "HTML") -> dict:
    """
    Envia mensagem via Telegram Bot API.
    
    Para configurar:
    1. Crie um bot com @BotFather no Telegram
    2. Copie o token do bot
    3. Inicie conversa com o bot e envie /start
    4. Obtenha seu chat_id em: https://api.telegram.org/bot<TOKEN>/getUpdates
    
    Returns:
        dict com 'ok' (bool) e 'message' ou 'error'
    """
    if not bot_token or not chat_id:
        return {"ok": False, "error": "Bot token ou chat_id não configurado"}
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get("ok"):
            return {"ok": True, "message": "Mensagem enviada com sucesso!"}
        else:
            return {"ok": False, "error": data.get("description", "Erro desconhecido")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def telegram_testar_conexao(bot_token: str, chat_id: str) -> dict:
    """Testa a conexão enviando uma mensagem de teste."""
    msg = "🔔 <b>Monitor Legislativo</b>\n\n✅ Conexão configurada com sucesso!\n\nVocê receberá notificações de novidades na tramitação."
    return telegram_enviar_mensagem(bot_token, chat_id, msg)


def formatar_notificacao_tramitacao(proposicao: dict, tramitacoes_novas: list) -> str:
    """
    Formata mensagem de notificação para nova tramitação.
    
    Args:
        proposicao: dict com dados da proposição (sigla, numero, ano, ementa)
        tramitacoes_novas: lista de tramitações novas
    """
    sigla = proposicao.get("sigla", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = proposicao.get("ementa", "")[:200]
    id_prop = proposicao.get("id", "")
    
    titulo = f"{sigla} {numero}/{ano}" if sigla and numero and ano else "Proposição"
    
    linhas = [
        f"🔔 <b>Nova movimentação!</b>",
        f"",
        f"📋 <b>{titulo}</b>",
    ]
    
    if ementa:
        linhas.append(f"<i>{ementa}...</i>")
    
    linhas.append("")
    
    for tram in tramitacoes_novas[:3]:  # Limita a 3 tramitações
        data = tram.get("dataHora", "")[:10] if tram.get("dataHora") else ""
        despacho = tram.get("despacho", "")[:150] or tram.get("descricaoSituacao", "")[:150]
        if data:
            linhas.append(f"📅 <b>{data}</b>")
        if despacho:
            linhas.append(f"→ {despacho}")
        linhas.append("")
    
    if id_prop:
        link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_prop}"
        linhas.append(f"🔗 <a href='{link}'>Ver tramitação completa</a>")
    
    return "\n".join(linhas)


def verificar_e_notificar_tramitacoes(
    bot_token: str,
    chat_id: str,
    proposicoes_monitoradas: list,
    ultima_verificacao: datetime.datetime = None
) -> dict:
    """
    Verifica tramitações novas e envia notificações.
    
    Args:
        bot_token: Token do bot Telegram
        chat_id: ID do chat para enviar
        proposicoes_monitoradas: Lista de IDs de proposições para monitorar
        ultima_verificacao: Data/hora da última verificação (para filtrar novidades)
    
    Returns:
        dict com 'notificacoes_enviadas' e 'erros'
    """
    if not bot_token or not chat_id:
        return {"notificacoes_enviadas": 0, "erros": ["Telegram não configurado"]}
    
    if ultima_verificacao is None:
        # Se não tem última verificação, usa últimas 24 horas
        ultima_verificacao = get_brasilia_now() - datetime.timedelta(days=1)
    
    notificacoes = 0
    erros = []
    
    for id_prop in proposicoes_monitoradas:
        try:
            # Busca tramitações da proposição
            url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            tramitacoes = data.get("dados", [])
            
            # Filtra tramitações novas
            tramitacoes_novas = []
            for tram in tramitacoes:
                data_hora = tram.get("dataHora", "")
                if data_hora:
                    try:
                        dt_tram = datetime.datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                        if dt_tram.tzinfo is None:
                            dt_tram = dt_tram.replace(tzinfo=TZ_BRASILIA)
                        
                        if dt_tram > ultima_verificacao.replace(tzinfo=TZ_BRASILIA):
                            tramitacoes_novas.append(tram)
                    except:
                        pass
            
            if tramitacoes_novas:
                # Busca dados da proposição
                info = fetch_proposicao_info(id_prop)
                if info:
                    proposicao = {
                        "id": id_prop,
                        "sigla": info.get("sigla", ""),
                        "numero": info.get("numero", ""),
                        "ano": info.get("ano", ""),
                        "ementa": info.get("ementa", "")
                    }
                    
                    # Formata e envia mensagem
                    msg = formatar_notificacao_tramitacao(proposicao, tramitacoes_novas)
                    resultado = telegram_enviar_mensagem(bot_token, chat_id, msg)
                    
                    if resultado.get("ok"):
                        notificacoes += 1
                    else:
                        erros.append(f"Erro ao notificar {id_prop}: {resultado.get('error')}")
                    
                    # Pausa para não sobrecarregar API do Telegram
                    time.sleep(0.5)
        
        except Exception as e:
            erros.append(f"Erro ao verificar {id_prop}: {str(e)}")
    
    return {"notificacoes_enviadas": notificacoes, "erros": erros}

def proximo_dia_util(dt: datetime.date) -> datetime.date:
    """
    Retorna o próximo dia útil após a data informada.
    Pula sábados (5) e domingos (6).
    """
    if dt is None:
        return None
    proximo = dt + datetime.timedelta(days=1)
    while proximo.weekday() in (5, 6):  # Sábado=5, Domingo=6
        proximo += datetime.timedelta(days=1)
    return proximo


def ajustar_para_dia_util(dt: datetime.date) -> datetime.date:
    """
    Se a data cair em fim de semana, retorna o próximo dia útil.
    Caso contrário, retorna a própria data.
    """
    if dt is None:
        return None
    while dt.weekday() in (5, 6):
        dt += datetime.timedelta(days=1)
    return dt


def calcular_prazo_ric(data_remessa: datetime.date) -> tuple:
    """
    Calcula o prazo de 30 dias para resposta de RIC conforme regra constitucional.
    
    REGRA:
    - Dia 1 = 1º dia ÚTIL após a remessa
    - Dia 30 = 30º dia se for útil, ou próximo dia útil se não for
    
    Exemplo:
    - Remessa: 27/11/2025 (quinta)
    - Dia 1: 28/11/2025 (sexta) - primeiro dia útil após remessa
    - Dia 30 seria: 28/11 + 29 dias = 27/12/2025 (sábado)
    - Como 27/12 é sábado, prazo final = 29/12/2025 (segunda)
    
    Retorna: (inicio_contagem, prazo_fim)
    """
    if data_remessa is None:
        return None, None
    
    # Dia 1 = primeiro dia ÚTIL após a remessa
    inicio_contagem = proximo_dia_util(data_remessa)
    
    # Dia 30 = 29 dias após o Dia 1 (porque Dia 1 já conta)
    dia_30_bruto = inicio_contagem + datetime.timedelta(days=29)
    
    # Se o Dia 30 cair em fim de semana, estende para o próximo dia útil
    prazo_fim = ajustar_para_dia_util(dia_30_bruto)
    
    return inicio_contagem, prazo_fim


def contar_dias_uteis(data_inicio: datetime.date, data_fim: datetime.date) -> int:
    """Conta dias úteis entre duas datas (excluindo fins de semana)."""
    if data_inicio is None or data_fim is None:
        return 0
    if data_fim < data_inicio:
        return 0
    dias = 0
    atual = data_inicio
    while atual <= data_fim:
        if atual.weekday() < 5:  # Segunda a sexta
            dias += 1
        atual += datetime.timedelta(days=1)
    return dias


def parse_prazo_resposta_ric(tramitacoes: list, situacao_atual: str = "") -> dict:
    """
    Extrai informações de prazo de resposta de RIC a partir das tramitações.
    
    REGRA CONSTITUCIONAL DE PRAZO:
    ==============================
    O Poder Executivo tem 30 DIAS para responder, contados a partir da REMESSA.
    
    DETECÇÃO DE REMESSA:
    - Órgão: 1SECM (1ª Secretaria da Câmara dos Deputados)
    - Texto contém: "Remessa por meio do Ofício" (qualquer variação)
    
    DETECÇÃO DE RESPOSTA:
    - Órgão: 1SECM (1ª Secretaria da Câmara dos Deputados)
    - Texto contém: "Recebimento de resposta conforme Ofício"
    
    CÁLCULO DO PRAZO:
    - Se houver texto "Prazo para Resposta Externas (de DD/MM/AAAA a DD/MM/AAAA)": usar datas explícitas
    - Senão: prazo_fim = data_remessa + 30 dias
    """
    resultado = {
        "data_remessa": None,
        "inicio_contagem": None,
        "prazo_inicio": None,
        "prazo_fim": None,
        "prazo_str": "",
        "dias_restantes": None,
        "fonte_prazo": "",
        "status_resposta": "Aguardando resposta",
        "data_resposta": None,
        "respondido": False,
        "ministerio_destinatario": "",
        "tramitacao_remessa_texto": "",
    }
    
    if not tramitacoes:
        resultado["status_resposta"] = _determinar_status_por_situacao(situacao_atual, False, None, None)
        return resultado
    
    # Ordenar tramitações por data (cronológica)
    tramitacoes_ordenadas = sorted(
        tramitacoes,
        key=lambda x: x.get("dataHora") or x.get("data") or "",
        reverse=False
    )
    
    # Regex para prazo explícito (se existir no texto)
    regex_prazo = r"Prazo\s+para\s+Resposta\s+Externas?\s*\(de\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})\)"
    
    def normalizar_texto_busca(texto):
        """Normaliza texto removendo acentos e convertendo para minúsculas"""
        texto = texto.lower()
        # Substituir caracteres especiais
        texto = texto.replace('ª', 'a').replace('º', 'o')
        # Remover acentos usando unicodedata
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto
    
    # ============================================================
    # PASSO 1: Procurar tramitação de REMESSA
    # Critério: 1SECM + "Remessa por meio do Ofício 1ªSec/RI/E"
    # ============================================================
    tramitacao_remessa = None
    data_remessa = None
    
    for t in tramitacoes_ordenadas:
        sigla_orgao = (t.get("siglaOrgao") or "").upper().strip()
        despacho = t.get("despacho") or ""
        desc = t.get("descricaoTramitacao") or ""
        texto_completo = f"{despacho} {desc}"
        
        # Normalizar texto para busca
        texto_busca = normalizar_texto_busca(texto_completo)
        
        is_1secm = "1SEC" in sigla_orgao or sigla_orgao == "1SECM"
        
        # Critério de REMESSA: "Remessa por meio do Ofício 1ªSec/RI/E" ou variações
        # Aceita: "remessa por meio do oficio", "1asec/ri/e", "1sec/ri/e"
        has_remessa = "remessa por meio do oficio" in texto_busca
        has_1sec_ri = "1asec/ri/e" in texto_busca or "1sec/ri/e" in texto_busca
        
        # NÃO é remessa se for recebimento de resposta
        is_recebimento = "recebimento de resposta" in texto_busca
        
        if is_1secm and (has_remessa or has_1sec_ri) and not is_recebimento:
            tramitacao_remessa = t
            resultado["tramitacao_remessa_texto"] = texto_completo.strip()
            
            # Extrair data da tramitação de remessa
            data_str = t.get("dataHora") or t.get("data")
            if data_str:
                try:
                    dt = pd.to_datetime(data_str, errors="coerce")
                    if pd.notna(dt):
                        data_remessa = dt.date()
                        resultado["data_remessa"] = data_remessa
                except:
                    pass
            
            # Verificar se tem prazo EXPLÍCITO no texto
            match_prazo = re.search(regex_prazo, texto_completo, re.IGNORECASE)
            if match_prazo:
                try:
                    prazo_inicio_str = match_prazo.group(1)
                    prazo_fim_str = match_prazo.group(2)
                    resultado["prazo_inicio"] = datetime.datetime.strptime(prazo_inicio_str, "%d/%m/%Y").date()
                    resultado["prazo_fim"] = datetime.datetime.strptime(prazo_fim_str, "%d/%m/%Y").date()
                    resultado["prazo_str"] = f"{prazo_inicio_str} a {prazo_fim_str}"
                    resultado["fonte_prazo"] = "explicitado_na_tramitacao"
                    resultado["inicio_contagem"] = resultado["prazo_inicio"]
                except:
                    pass
            
            # Continua procurando para pegar a ÚLTIMA remessa (mais recente)
    
    # ============================================================
    # PASSO 2: Se não encontrou prazo explícito, CALCULAR
    # Regra: Dia 1 = 1º dia útil após remessa, Dia 30 = 30º dia (ou próximo útil)
    # ============================================================
    if tramitacao_remessa and not resultado["prazo_fim"] and data_remessa:
        # Usar função que calcula corretamente os dias úteis
        inicio_contagem, prazo_fim = calcular_prazo_ric(data_remessa)
        if inicio_contagem and prazo_fim:
            resultado["prazo_inicio"] = inicio_contagem
            resultado["inicio_contagem"] = inicio_contagem
            resultado["prazo_fim"] = prazo_fim
            resultado["prazo_str"] = f"até {prazo_fim.strftime('%d/%m/%Y')}"
            resultado["fonte_prazo"] = "calculado_30_dias"
    
    # ============================================================
    # PASSO 3: Calcular dias restantes
    # ============================================================
    if resultado["prazo_fim"]:
        hoje = datetime.date.today()
        delta = (resultado["prazo_fim"] - hoje).days
        resultado["dias_restantes"] = delta
    
    # ============================================================
    # PASSO 4: Verificar se foi RESPONDIDO
    # Critério: 1SECM + "Recebimento de resposta conforme Ofício"
    # A data da resposta é a data mencionada NO TEXTO do ofício, não a data da tramitação
    # ============================================================
    data_resposta = None
    respondido = False
    
    # Regex para extrair data do texto do ofício
    # Padrões: "de 24 de novembro de 2025" ou "de 27/12/2025"
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    regex_data_extenso = r"de\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"
    regex_data_num = r"de\s+(\d{1,2})/(\d{1,2})/(\d{4})"
    
    for t in tramitacoes_ordenadas:
        sigla_orgao = (t.get("siglaOrgao") or "").upper().strip()
        despacho = (t.get("despacho") or "")
        desc = (t.get("descricaoTramitacao") or "")
        texto = f"{despacho} {desc}"
        texto_busca = normalizar_texto_busca(texto)
        
        is_1secm = "1SEC" in sigla_orgao or sigla_orgao == "1SECM"
        
        # Critério PRINCIPAL: "Recebimento de resposta conforme Ofício"
        is_recebimento_resposta = "recebimento de resposta conforme of" in texto_busca
        
        if is_1secm and is_recebimento_resposta:
            respondido = True
            
            # Tentar extrair data do texto do ofício (ex: "de 24 de novembro de 2025")
            match_extenso = re.search(regex_data_extenso, texto, re.IGNORECASE)
            match_num = re.search(regex_data_num, texto)
            
            if match_extenso:
                try:
                    dia = int(match_extenso.group(1))
                    mes_nome = match_extenso.group(2).lower()
                    ano = int(match_extenso.group(3))
                    mes = meses_pt.get(mes_nome)
                    if mes:
                        data_resposta = datetime.date(ano, mes, dia)
                except:
                    pass
            elif match_num:
                try:
                    dia = int(match_num.group(1))
                    mes = int(match_num.group(2))
                    ano = int(match_num.group(3))
                    data_resposta = datetime.date(ano, mes, dia)
                except:
                    pass
            
            # Se não conseguiu extrair do texto, usar data da tramitação como fallback
            if not data_resposta:
                data_str = t.get("dataHora") or t.get("data")
                if data_str:
                    try:
                        dt_resp = pd.to_datetime(data_str, errors="coerce")
                        if pd.notna(dt_resp):
                            data_resposta = dt_resp.date()
                    except:
                        pass
    
    resultado["respondido"] = respondido
    resultado["data_resposta"] = data_resposta
    
    # ============================================================
    # PASSO 5: Determinar STATUS FINAL
    # ============================================================
    resultado["status_resposta"] = _determinar_status_por_situacao(
        situacao_atual, 
        respondido, 
        data_resposta, 
        resultado["prazo_fim"]
    )
    
    return resultado


def _determinar_status_por_situacao(situacao_atual: str, respondido: bool, data_resposta, prazo_fim) -> str:
    """
    Determina o status do RIC baseado na situação atual e dados de prazo/resposta.
    
    REGRAS:
    1. "Aguardando Remessa ao Arquivo" → "Respondido"
    2. "Aguardando Providências Internas" → "Em tramitação na Câmara"
    3. "Aguardando Despacho do Presidente da Câmara..." → "Em tramitação na Câmara"
    4. "Aguardando Designação de Relator" → "Em tramitação na Câmara"
    5. "Aguardando Resposta" (situação da Câmara) → "Em tramitação na Câmara" SE não houver prazo
    6. Se respondido e data_resposta > prazo_fim → "Respondido fora do prazo"
    7. Se respondido e data_resposta <= prazo_fim → "Respondido"
    8. Se não respondido e hoje > prazo_fim → "Fora do prazo"
    9. Se não há prazo_fim (não encontrou remessa) → "Em tramitação na Câmara"
    10. Caso contrário → "Aguardando resposta"
    """
    situacao_norm = (situacao_atual or "").lower().strip()
    hoje = datetime.date.today()
    
    # REGRA 1: Aguardando Remessa ao Arquivo = JÁ FOI RESPONDIDO
    if "aguardando remessa ao arquivo" in situacao_norm or "remessa ao arquivo" in situacao_norm:
        if prazo_fim and data_resposta and data_resposta > prazo_fim:
            return "Respondido fora do prazo"
        return "Respondido"
    
    # REGRA 2, 3, 4 e 5: Situações que indicam tramitação interna na Câmara
    situacoes_tramitacao_camara = [
        "aguardando providências internas",
        "aguardando providencias internas",
        "aguardando despacho do presidente da câmara",
        "aguardando despacho do presidente da camara",
        "aguardando designação de relator",
        "aguardando designacao de relator",
        "aguardando recebimento",
        "retirado pelo(a) autor(a)",
        "retirado pelo autor",
    ]
    for sit in situacoes_tramitacao_camara:
        if sit in situacao_norm:
            return "Em tramitação na Câmara"
    
    # REGRA 6 e 7: Se foi respondido (detectado nas tramitações)
    if respondido:
        if prazo_fim and data_resposta:
            if data_resposta > prazo_fim:
                return "Respondido fora do prazo"
            else:
                return "Respondido"
        else:
            return "Respondido"
    
    # REGRA 8: Se não foi respondido e prazo venceu
    if prazo_fim and hoje > prazo_fim:
        return "Fora do prazo"
    
    # REGRA 9: Se não há prazo (não encontrou remessa) → Em tramitação na Câmara
    # Isso significa que o RIC ainda não foi remetido ao Executivo
    if not prazo_fim:
        return "Em tramitação na Câmara"
    
    # REGRA 10: Caso padrão - já foi remetido, aguardando resposta
    return "Aguardando resposta"


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
    # "Solicita informações ao Ministro/Ministra/Ministério de/da/do X"
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
            # Normalizar para nome canônico
            ministerio_normalizado = normalize_ministerio(ministerio_extraido)
            if ministerio_normalizado and ministerio_normalizado != "Não identificado":
                return ministerio_normalizado
    
    # Tentar identificar diretamente na ementa usando normalize_ministerio
    ministerio_direto = normalize_ministerio(ementa)
    if ministerio_direto and ministerio_direto != "Não identificado":
        return ministerio_direto
    
    # Se não encontrou na ementa, tentar nas tramitações (texto da remessa)
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
    
    # Mapeamento de palavras-chave para assuntos
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


def sanitize_text_pdf(text: str) -> str:
    """Remove caracteres problemáticos para PDF."""
    if not text:
        return ""
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        '–': '-', '—': '-', '"': '"', '"': '"', ''': "'", ''': "'",
        '…': '...', '•': '*', '°': 'o', '²': '2', '³': '3',
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = result.encode('ascii', 'ignore').decode('ascii')
    return result



# ============================================================
# FUNÇÕES AUXILIARES PARA PDF - VERSÃO 21
# ============================================================

def _padronizar_colunas_pdf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza colunas do DataFrame para geração de PDF.
    Garante colunas canônicas e evita heurísticas frágeis.
    """
    df_out = df.copy()
    
    # Mapeamento de nomes possíveis para nomes canônicos
    mapeamentos = {
        'Situação atual': ['Situação atual', 'Situacao atual', 'situacao_atual', 'status_descricaoSituacao', 'situacao'],
        'Data da última tramitação': ['Data do status', 'Data', 'DataStatus', 'data_status', 'status_dataHora', 'Data do status (raw)'],
        'Parado há (dias)': ['Parado (dias)', 'Parado há (dias)', 'dias_parado', 'parado_dias'],
        'Relator(a)': ['Relator(a)', 'Relator', 'relator'],
        'LinkTramitacao': ['LinkTramitacao', 'Link', 'link', 'url_tramitacao'],
        'LinkRelator': ['LinkRelator', 'link_relator'],
        'Órgão (sigla)': ['Órgão (sigla)', 'Orgao (sigla)', 'orgao_sigla', 'siglaOrgao'],
        'Proposição': ['Proposição', 'Proposicao', 'proposicao'],
        'Ementa': ['Ementa', 'ementa'],
        'Tema': ['Tema', 'tema'],
        'Andamento': ['Andamento (status)', 'Último andamento', 'Andamento', 'andamento', 'status_descricaoTramitacao'],
        # Colunas RIC
        'RIC_Ministerio': ['RIC_Ministerio', 'ric_ministerio', 'Ministerio'],
        'RIC_StatusResposta': ['RIC_StatusResposta', 'ric_status_resposta', 'StatusResposta'],
        'RIC_PrazoFim': ['RIC_PrazoFim', 'ric_prazo_fim', 'PrazoFim'],
        'RIC_DiasRestantes': ['RIC_DiasRestantes', 'ric_dias_restantes', 'DiasRestantes'],
    }
    
    for col_canonica, possiveis in mapeamentos.items():
        if col_canonica not in df_out.columns:
            for possivel in possiveis:
                if possivel in df_out.columns and possivel != col_canonica:
                    df_out[col_canonica] = df_out[possivel]
                    break
    
    # Garantir que LinkTramitacao existe
    if 'LinkTramitacao' not in df_out.columns:
        if 'id' in df_out.columns:
            df_out['LinkTramitacao'] = df_out['id'].astype(str).apply(camara_link_tramitacao)
        elif 'ID' in df_out.columns:
            df_out['LinkTramitacao'] = df_out['ID'].astype(str).apply(camara_link_tramitacao)
    
    # Garantir que Parado há (dias) existe
    if 'Parado há (dias)' not in df_out.columns:
        if 'DataStatus_dt' in df_out.columns:
            df_out['Parado há (dias)'] = df_out['DataStatus_dt'].apply(days_since)
        elif 'Data da última tramitação' in df_out.columns:
            dt = pd.to_datetime(df_out['Data da última tramitação'], errors='coerce', dayfirst=True)
            df_out['Parado há (dias)'] = dt.apply(days_since)
    
    return df_out


def _verificar_relator_adversario(relator_str: str) -> tuple:
    """
    Verifica se o relator é de partido adversário.
    Retorna: (texto_relator_formatado, is_adversario)
    """
    if not relator_str or not str(relator_str).strip() or str(relator_str).strip() in ('-', '—', 'nan'):
        return "Sem relator designado", False
    
    relator = str(relator_str).strip()
    relator_upper = relator.upper()
    
    for partido in PARTIDOS_RELATOR_ADVERSARIO:
        if f"({partido}/" in relator_upper or f"({partido}-" in relator_upper or f"/{partido})" in relator_upper:
            return relator, True
        if partido == "PCDOB" and ("(PC DO B" in relator_upper or "/PC DO B" in relator_upper):
            return relator, True
    
    return relator, False


def _obter_situacao_com_fallback(row: pd.Series) -> str:
    """
    Obtém a situação da proposição com fallback para andamento/tramitação.
    """
    situacao = ""
    for col in ['Situação atual', 'Situacao atual', 'situacao']:
        if col in row.index and pd.notna(row.get(col)) and str(row.get(col)).strip():
            situacao = str(row.get(col)).strip()
            break
    
    if not situacao or situacao in ('-', '—'):
        for col in ['Andamento (status)', 'Último andamento', 'Andamento', 'status_descricaoTramitacao']:
            if col in row.index and pd.notna(row.get(col)) and str(row.get(col)).strip():
                situacao = str(row.get(col)).strip()
                if len(situacao) > 60:
                    situacao = situacao[:57] + "..."
                break
    
    return situacao if situacao else "Situacao nao informada"


def _categorizar_situacao_para_ordenacao(situacao: str) -> tuple:
    """
    Categoriza a situação para ordenação personalizada dos blocos no PDF.
    Retorna: (ordem_prioridade, categoria_agrupada, situacao_original)
    
    Ordem de prioridade:
    1. Pronta para Pauta
    2. Aguardando Parecer de Relator(a)
    3. Aguardando Designação de Relator(a)
    4. Aguardando Apreciação pelo Senado Federal
    5. Aguardando Despacho do Presidente da Câmara
    6. Tramitando em Conjunto
    7. Aguardando Encaminhamentos/Procedimentos Administrativos
    8. Arquivadas/Aguardando Remessa ao Arquivo
    9. Outras situações
    """
    s = situacao.lower().strip()
    
    # 1. Pronta para Pauta
    if 'pronta' in s and 'pauta' in s:
        return (1, "Pronta para Pauta", situacao)
    
    # 2. Aguardando Parecer de Relator(a)
    if 'aguardando parecer' in s and 'relator' in s:
        return (2, "Aguardando Parecer de Relator(a)", situacao)
    
    # 3. Aguardando Designação de Relator(a) (incluindo devolução)
    if ('aguardando design' in s and 'relator' in s) or ('devolucao de relator' in s) or ('devolução de relator' in s):
        return (3, "Aguardando Designacao de Relator(a)", situacao)
    
    # 4. Aguardando Apreciação pelo Senado Federal
    if 'senado' in s or 'aguardando aprecia' in s:
        return (4, "Aguardando Apreciacao pelo Senado Federal", situacao)
    
    # 5. Aguardando Despacho do Presidente (todos os tipos)
    if ('despacho' in s and 'presidente' in s) or ('autorizacao do despacho' in s) or ('autorização do despacho' in s) or ('deliberacao de recurso' in s) or ('deliberação de recurso' in s):
        return (5, "Aguardando Despacho do Presidente da Camara", situacao)
    
    # 6. Tramitando em Conjunto (incluindo Aguardando Apensação)
    if 'tramitando em conjunto' in s or 'apensacao' in s or 'apensação' in s:
        return (6, "Tramitando em Conjunto", situacao)
    
    # 7. Aguardando Encaminhamentos/Procedimentos Administrativos
    if 'aguardando encaminhamento' in s or 'aguardando recebimento' in s or 'comissao temporaria' in s or 'comissão temporária' in s or 'criacao de comissao' in s or 'criação de comissão' in s:
        return (7, "Aguardando Procedimentos Administrativos da Casa", situacao)
    
    # 8. Arquivadas/Aguardando Remessa ao Arquivo
    if 'arquiv' in s or 'remessa ao arquivo' in s:
        return (8, "Arquivadas / Aguardando Remessa ao Arquivo", situacao)
    
    # 9. Outras situações (situacao nao informada, retirado pelo autor, etc.)
    return (9, "Outras Situacoes", situacao)


def _renderizar_card_proposicao(pdf, row, idx, col_proposicao, col_ementa, col_situacao, col_orgao,
                                 col_data, col_relator, col_tema, col_parado, col_link, mostrar_situacao=True):
    """Renderiza um card de proposição no PDF."""
    pdf.set_fill_color(245, 247, 250)
    
    # Número do registro
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(0, 51, 102)
    pdf.cell(8, 6, str(idx), fill=True, align='C')
    
    # Proposição (destaque)
    if col_proposicao and pd.notna(row.get(col_proposicao)):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 6, f"  {sanitize_text_pdf(str(row[col_proposicao]))}", ln=True)
    else:
        pdf.ln(6)
    
    pdf.set_x(20)
    
    # SITUAÇÃO COM FALLBACK
    if mostrar_situacao:
        situacao = _obter_situacao_com_fallback(row)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Situacao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        if 'Arquiv' in situacao:
            pdf.set_text_color(150, 50, 50)
        elif 'Pronta' in situacao or 'Sancion' in situacao:
            pdf.set_text_color(50, 150, 50)
        else:
            pdf.set_text_color(50, 50, 150)
        pdf.cell(0, 5, sanitize_text_pdf(situacao)[:60], ln=True)
        pdf.set_x(20)
    
    # Órgão
    if col_orgao and pd.notna(row.get(col_orgao)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Orgao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_orgao]))[:50], ln=True)
        pdf.set_x(20)
    
    # DATA DA ÚLTIMA TRAMITAÇÃO
    if col_data and pd.notna(row.get(col_data)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(35, 5, "Ultima tramitacao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_data]))[:20], ln=True)
        pdf.set_x(20)
    
    # PARADO HÁ (DIAS)
    dias_parado = None
    if col_parado and pd.notna(row.get(col_parado)):
        try:
            dias_parado = int(row[col_parado])
        except (ValueError, TypeError):
            dias_parado = None
    
    if dias_parado is not None:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(28, 5, "Parado ha (dias): ", ln=False)
        pdf.set_font('Helvetica', 'B', 9)
        if dias_parado >= 30:
            pdf.set_text_color(180, 50, 50)
        elif dias_parado >= 15:
            pdf.set_text_color(200, 120, 0)
        elif dias_parado >= 7:
            pdf.set_text_color(180, 180, 0)
        else:
            pdf.set_text_color(50, 150, 50)
        pdf.cell(0, 5, str(dias_parado), ln=True)
        pdf.set_x(20)
    
    # RELATOR COM ALERTA DE ADVERSÁRIO
    relator_txt = row.get(col_relator, "") if col_relator else ""
    relator_formatado, is_adversario = _verificar_relator_adversario(relator_txt)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(20, 5, "Relator(a): ", ln=False)
    pdf.set_font('Helvetica', '', 9)
    
    # Obter link do relator se existir
    link_relator = None
    if 'LinkRelator' in row.index and pd.notna(row.get('LinkRelator')):
        link_relator = str(row.get('LinkRelator')).strip()
        if not link_relator.startswith('http'):
            link_relator = None
    
    if is_adversario:
        pdf.set_text_color(180, 50, 50)
        if link_relator:
            pdf.set_font('Helvetica', 'U', 9)
            pdf.write(5, sanitize_text_pdf(relator_formatado)[:50], link=link_relator)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 5, " [!] ADVERSARIO", ln=True)
        else:
            pdf.cell(0, 5, sanitize_text_pdf(f"{relator_formatado} [!] RELATOR ADVERSARIO")[:70], ln=True)
    elif relator_formatado == "Sem relator designado":
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, "Sem relator designado", ln=True)
    else:
        pdf.set_text_color(0, 0, 0)
        if link_relator:
            pdf.set_font('Helvetica', 'U', 9)
            pdf.write(5, sanitize_text_pdf(relator_formatado)[:50], link=link_relator)
            pdf.ln(5)
        else:
            pdf.cell(0, 5, sanitize_text_pdf(relator_formatado)[:50], ln=True)
    
    pdf.set_x(20)
    
    # INFORMAÇÕES DE RIC (se for RIC)
    sigla_tipo = row.get('siglaTipo', '') or row.get('sigla_tipo', '')
    if sigla_tipo == 'RIC':
        # Ministério
        ministerio = row.get('RIC_Ministerio', '') or ''
        if ministerio and str(ministerio).strip() and str(ministerio).strip() != 'nan':
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Ministerio: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 4, sanitize_text_pdf(str(ministerio))[:50], ln=True)
            pdf.set_x(20)
        
        # Status de resposta
        status_resp = row.get('RIC_StatusResposta', '') or ''
        if status_resp and str(status_resp).strip() and str(status_resp).strip() != 'nan':
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Status: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            if 'Respondido' in str(status_resp):
                pdf.set_text_color(50, 150, 50)
            else:
                pdf.set_text_color(200, 120, 0)
            pdf.cell(0, 4, sanitize_text_pdf(str(status_resp))[:30], ln=True)
            pdf.set_x(20)
        
        # Prazo e dias restantes
        dias_rest = row.get('RIC_DiasRestantes', None)
        prazo_fim = row.get('RIC_PrazoFim', None)
        if prazo_fim and pd.notna(prazo_fim):
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Prazo: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            try:
                if isinstance(prazo_fim, datetime.date):
                    prazo_str = prazo_fim.strftime("%d/%m/%Y")
                else:
                    prazo_str = str(prazo_fim)[:10]
            except:
                prazo_str = str(prazo_fim)[:10]
            
            if dias_rest is not None and pd.notna(dias_rest):
                try:
                    dias_int = int(dias_rest)
                    if dias_int < 0:
                        pdf.set_text_color(180, 50, 50)
                        pdf.cell(0, 4, f"{prazo_str} (VENCIDO ha {abs(dias_int)} dias)", ln=True)
                    elif dias_int <= 5:
                        pdf.set_text_color(200, 120, 0)
                        pdf.cell(0, 4, f"{prazo_str} ({dias_int} dias restantes - URGENTE)", ln=True)
                    else:
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 4, f"{prazo_str} ({dias_int} dias restantes)", ln=True)
                except:
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 4, prazo_str, ln=True)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 4, prazo_str, ln=True)
            pdf.set_x(20)
    
    # Tema
    if col_tema and pd.notna(row.get(col_tema)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Tema: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_tema]))[:40], ln=True)
        pdf.set_x(20)
    
    # Ementa
    if col_ementa and pd.notna(row.get(col_ementa)):
        ementa = sanitize_text_pdf(str(row[col_ementa]))
        if ementa and ementa.strip():
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "Ementa:", ln=True)
            pdf.set_x(20)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(170, 4, ementa[:300] + ('...' if len(ementa) > 300 else ''))
    
    # LINK CLICÁVEL
    link_url = None
    if col_link and pd.notna(row.get(col_link)):
        link_url = str(row[col_link]).strip()
    elif 'id' in row.index and pd.notna(row.get('id')):
        link_url = camara_link_tramitacao(str(row['id']))
    elif 'ID' in row.index and pd.notna(row.get('ID')):
        link_url = camara_link_tramitacao(str(row['ID']))
    
    if link_url and link_url.startswith('http'):
        pdf.set_x(20)
        pdf.set_font('Helvetica', 'I', 7)
        pdf.set_text_color(0, 0, 200)
        pdf.cell(10, 4, "Link: ", ln=False)
        pdf.set_font('Helvetica', 'U', 7)
        pdf.write(4, "Abrir tramitacao na Camara", link=link_url)
        pdf.ln(4)
    
    # Linha divisória
    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.2)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)


def to_pdf_bytes(df: pd.DataFrame, subtitulo: str = "Relatório") -> tuple:
    """
    Exporta DataFrame para PDF em formato de relatório profissional.
    VERSÃO 21 - PDFs otimizados para decisão política em gabinete.
    """
    colunas_excluir = ['Tipo', 'Ano', 'Alerta', 'ID', 'id', 'sinal', 'AnoStatus', 'MesStatus', 
                       'ids_proposicoes_autoria', 'ids_proposicoes_relatoria', 'id_evento',
                       'DataStatus_dt', 'Data do status (raw)', '_search', '_dt_sort',
                       '_situacao_group', '_categoria_info', '_ordem_prioridade', '_categoria_agrupada']
    
    try:
        from fpdf import FPDF
        
        df_proc = _padronizar_colunas_pdf(df)
        is_materias_por_situacao = "Situação" in subtitulo or "Situacao" in subtitulo
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df_proc.copy()
        col_data_sort = None
        for col in ['DataStatus_dt', 'Data da última tramitação', 'Data do status']:
            if col in df_sorted.columns:
                col_data_sort = col
                break
        
        if col_data_sort:
            if col_data_sort == 'DataStatus_dt':
                df_sorted = df_sorted.sort_values(col_data_sort, ascending=False, na_position='last')
            else:
                df_sorted['_dt_sort'] = pd.to_datetime(df_sorted[col_data_sort], errors='coerce', dayfirst=True)
                df_sorted = df_sorted.sort_values('_dt_sort', ascending=False, na_position='last')
        
        # Garantir remoção de colunas temporárias
        for col_temp in ['_dt_sort', '_search']:
            if col_temp in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=[col_temp])
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 297, 25, 'F')
                self.set_font('Helvetica', 'B', 20)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Subtítulo e data
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, sanitize_text_pdf(subtitulo), ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # CABEÇALHO INFORMATIVO - FONTE E CRITÉRIO
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Ultima tramitacao (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de registros: {len(df_sorted)}", ln=True)
        pdf.ln(3)
        
        # Definir colunas para renderização (excluindo colunas temporárias)
        cols_mostrar = [c for c in df_sorted.columns if c not in colunas_excluir]
        
        col_proposicao = next((c for c in cols_mostrar if 'Proposi' in c or c == 'Proposição'), None)
        col_ementa = next((c for c in cols_mostrar if 'Ementa' in c or 'ementa' in c), None)
        col_situacao = next((c for c in cols_mostrar if 'Situa' in c), None)
        col_orgao = next((c for c in cols_mostrar if 'Org' in c and 'sigla' in c.lower()), None)
        col_data = next((c for c in cols_mostrar if 'Data' in c and 'última' in c.lower()), None)
        if not col_data:
            col_data = next((c for c in cols_mostrar if 'Data do status' in c or 'Data' in c), None)
        col_relator = next((c for c in cols_mostrar if 'Relator' in c), None)
        col_tema = next((c for c in cols_mostrar if 'Tema' in c), None)
        col_parado = next((c for c in cols_mostrar if 'Parado' in c and 'dias' in c.lower()), None)
        col_link = next((c for c in ['LinkTramitacao', 'Link'] if c in df_sorted.columns), None)
        
        # AGRUPAMENTO POR SITUAÇÃO COM ORDENAÇÃO PERSONALIZADA
        if is_materias_por_situacao and col_situacao:
            df_sorted['_situacao_group'] = df_sorted.apply(_obter_situacao_com_fallback, axis=1)
            
            # Aplicar categorização para ordenação
            df_sorted['_categoria_info'] = df_sorted['_situacao_group'].apply(_categorizar_situacao_para_ordenacao)
            df_sorted['_ordem_prioridade'] = df_sorted['_categoria_info'].apply(lambda x: x[0])
            df_sorted['_categoria_agrupada'] = df_sorted['_categoria_info'].apply(lambda x: x[1])
            
            # Ordenar por prioridade da categoria e depois por data dentro de cada categoria
            if '_dt_sort' not in df_sorted.columns and col_data_sort:
                df_sorted['_dt_sort'] = pd.to_datetime(df_sorted[col_data_sort], errors='coerce', dayfirst=True)
            
            # Ordenar - usar _dt_sort só se existir
            if '_dt_sort' in df_sorted.columns:
                df_sorted = df_sorted.sort_values(['_ordem_prioridade', '_dt_sort'], ascending=[True, False], na_position='last')
                # Remover _dt_sort após ordenação
                df_sorted = df_sorted.drop(columns=['_dt_sort'])
            else:
                df_sorted = df_sorted.sort_values('_ordem_prioridade', ascending=True, na_position='last')
            
            # Agrupar por categoria agrupada (não pela situação original)
            categorias_ordenadas = df_sorted.groupby('_categoria_agrupada', sort=False).agg({
                '_ordem_prioridade': 'first',
                '_situacao_group': 'count'
            }).reset_index()
            categorias_ordenadas = categorias_ordenadas.sort_values('_ordem_prioridade')
            
            registro_num = 0
            for _, cat_row in categorias_ordenadas.iterrows():
                categoria = cat_row['_categoria_agrupada']
                qtd_categoria = cat_row['_situacao_group']
                
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                # Cabeçalho da categoria principal
                pdf.ln(3)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(255, 255, 255)
                categoria_txt = sanitize_text_pdf(str(categoria))
                pdf.cell(0, 8, f"  {categoria_txt} ({qtd_categoria})", ln=True, fill=True)
                pdf.ln(2)
                
                df_categoria = df_sorted[df_sorted['_categoria_agrupada'] == categoria]
                
                # Subcategorias (situações originais dentro da categoria)
                situacoes_na_categoria = df_categoria.groupby('_situacao_group', sort=False).size()
                
                for situacao_original, qtd_sit in situacoes_na_categoria.items():
                    # Se a categoria tem múltiplas situações originais, mostrar subcabeçalho
                    if len(situacoes_na_categoria) > 1:
                        if pdf.get_y() > 245:
                            pdf.add_page()
                            pdf.set_y(30)
                        
                        pdf.set_fill_color(220, 230, 240)
                        pdf.set_font('Helvetica', 'B', 9)
                        pdf.set_text_color(0, 51, 102)
                        sit_txt = sanitize_text_pdf(str(situacao_original))[:65]
                        pdf.cell(0, 6, f"    {sit_txt} ({qtd_sit})", ln=True, fill=True)
                        pdf.ln(1)
                    
                    df_grupo = df_categoria[df_categoria['_situacao_group'] == situacao_original]
                    
                    for _, row in df_grupo.head(100).iterrows():
                        registro_num += 1
                        if registro_num > 300:
                            break
                        
                        if pdf.get_y() > 250:
                            pdf.add_page()
                            pdf.set_y(30)
                        
                        _renderizar_card_proposicao(
                            pdf, row, registro_num,
                            col_proposicao, col_ementa, col_situacao, col_orgao,
                            col_data, col_relator, col_tema, col_parado, col_link,
                            mostrar_situacao=False
                        )
                    
                    if registro_num > 300:
                        break
                
                if registro_num > 300:
                    break
        else:
            # Remover colunas temporárias antes de iterar
            for col_temp in ['_dt_sort', '_search']:
                if col_temp in df_sorted.columns:
                    df_sorted = df_sorted.drop(columns=[col_temp])
            
            for idx, (_, row) in enumerate(df_sorted.head(300).iterrows()):
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_y(30)
                
                _renderizar_card_proposicao(
                    pdf, row, idx + 1,
                    col_proposicao, col_ementa, col_situacao, col_orgao,
                    col_data, col_relator, col_tema, col_parado, col_link,
                    mostrar_situacao=True
                )
        
        if len(df) > 300:
            pdf.ln(5)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"* Exibindo 300 de {len(df)} registros. Exporte em XLSX para lista completa.", ln=True, align='C')
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except ImportError:
        # fpdf não instalado - gerar PDF simples de erro
        raise Exception("Biblioteca fpdf2 não disponível. Instale com: pip install fpdf2")
    except Exception as e:
        # Propagar o erro para debug - NÃO fazer fallback para CSV
        import traceback
        raise Exception(f"Erro ao gerar PDF: {str(e)} | Traceback: {traceback.format_exc()}")



def to_pdf_autoria_relatoria(df: pd.DataFrame) -> tuple[bytes, str, str]:
    """PDF específico para Autoria e Relatoria na Pauta - formato de gabinete com dados completos."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Autoria e Relatoria na Pauta", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # Cabeçalho informativo - fonte e critério
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Data do evento (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df.copy()
        if 'data' in df_sorted.columns:
            df_sorted['_data_sort'] = pd.to_datetime(df_sorted['data'], errors='coerce', dayfirst=True)
            df_sorted = df_sorted.sort_values('_data_sort', ascending=False)
        
        # Função auxiliar para extrair IDs e buscar info
        def extrair_ids(texto_ids):
            """Extrai lista de IDs de uma string separada por ;"""
            ids = []
            if pd.isna(texto_ids) or str(texto_ids).strip() in ('', 'nan'):
                return ids
            for pid in str(texto_ids).split(';'):
                pid = pid.strip()
                if pid and pid.isdigit():
                    ids.append(pid)
            return ids
        
        def buscar_info_proposicao(pid):
            """Busca info completa de uma proposição"""
            try:
                info = fetch_proposicao_completa(str(pid))
                return info
            except:
                return {}
        
        # Separar AUTORIA e RELATORIA com dados enriquecidos
        registros_autoria = []
        registros_relatoria = []
        
        for _, row in df_sorted.iterrows():
            data = str(row.get('data', '-'))
            hora = str(row.get('hora', '-')) if pd.notna(row.get('hora')) else '-'
            orgao_sigla = str(row.get('orgao_sigla', '-'))
            orgao_nome = str(row.get('orgao_nome', ''))
            local = f"{orgao_sigla}" + (f" - {orgao_nome}" if orgao_nome and orgao_nome != orgao_sigla else "")
            id_evento = str(row.get('id_evento', ''))
            link_evento = f"https://www.camara.leg.br/evento-legislativo/{id_evento}" if id_evento and id_evento != 'nan' else ""
            
            # IDs das proposições
            ids_autoria = extrair_ids(row.get('ids_proposicoes_autoria', ''))
            ids_relatoria = extrair_ids(row.get('ids_proposicoes_relatoria', ''))
            
            # Processar AUTORIA
            if ids_autoria:
                materias_autoria = []
                for pid in ids_autoria:
                    info = buscar_info_proposicao(pid)
                    sigla = f"{info.get('sigla', '')} {info.get('numero', '')}/{info.get('ano', '')}"
                    ementa = info.get('ementa', '')
                    situacao = info.get('status_descricaoSituacao', '')
                    relator_info = info.get('relator', {}) or {}
                    relator_nome = relator_info.get('nome', '')
                    relator_partido = relator_info.get('partido', '')
                    relator_uf = relator_info.get('uf', '')
                    relator_str = f"{relator_nome} ({relator_partido}/{relator_uf})" if relator_nome else "Sem relator designado"
                    link_materia = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"
                    
                    # Verificar se relator é adversário
                    _, is_adversario = _verificar_relator_adversario(relator_str)
                    
                    materias_autoria.append({
                        'sigla': sigla.strip(),
                        'ementa': ementa,
                        'situacao': situacao if situacao else "Situacao nao informada",
                        'relator': relator_str,
                        'link': link_materia,
                        'is_adversario': is_adversario
                    })
                
                registros_autoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'link_evento': link_evento, 'materias': materias_autoria
                })
            
            # Processar RELATORIA
            if ids_relatoria:
                materias_relatoria = []
                for pid in ids_relatoria:
                    info = buscar_info_proposicao(pid)
                    sigla = f"{info.get('sigla', '')} {info.get('numero', '')}/{info.get('ano', '')}"
                    ementa = info.get('ementa', '')
                    situacao = info.get('status_descricaoSituacao', '')
                    despacho = info.get('status_despacho', '')
                    url_teor = info.get('urlInteiroTeor', '')
                    link_materia = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"
                    
                    # Buscar info do parecer nas tramitações
                    parecer_info = ""
                    tramitacoes = info.get('tramitacoes', [])
                    for tram in tramitacoes[:10]:  # Últimas 10 tramitações
                        desc = tram.get('descricaoTramitacao', '') or ''
                        desp = tram.get('despacho', '') or ''
                        if 'parecer' in desc.lower() or 'parecer' in desp.lower():
                            parecer_info = f"{desc} - {desp}".strip(' -')
                            break
                    
                    materias_relatoria.append({
                        'sigla': sigla.strip(),
                        'ementa': ementa,
                        'situacao': situacao,
                        'parecer': parecer_info,
                        'link': link_materia,
                        'link_teor': url_teor
                    })
                
                registros_relatoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'link_evento': link_evento, 'materias': materias_relatoria
                })
        
        # === SEÇÃO AUTORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 100, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  AUTORIA DA DEPUTADA ({len(registros_autoria)} reuniao(oes))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_autoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de autoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_autoria, 1):
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                # Cabeçalho da reunião
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(0, 100, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(8, 6, str(idx), fill=True, align='C')
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 6, f"  {reg['data']} as {reg['hora']}", ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:70], ln=True)
                
                # Cada matéria
                for mat in reg['materias']:
                    if pdf.get_y() > 250:
                        pdf.add_page()
                        pdf.set_y(30)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 5, sanitize_text_pdf(mat['sigla']), ln=True)
                    
                    # Situação
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Situacao: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    sit = mat['situacao'] or '-'
                    if 'Arquiv' in sit:
                        pdf.set_text_color(150, 50, 50)
                    elif 'Pronta' in sit:
                        pdf.set_text_color(50, 150, 50)
                    else:
                        pdf.set_text_color(50, 50, 150)
                    pdf.cell(0, 4, sanitize_text_pdf(sit)[:55], ln=True)
                    
                    # Relator com alerta de adversário
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Relator: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    if mat.get('is_adversario'):
                        pdf.set_text_color(180, 50, 50)
                        pdf.cell(0, 4, sanitize_text_pdf(mat['relator'] + " [!] ADVERSARIO")[:60], ln=True)
                    elif mat['relator'] == "Sem relator designado":
                        pdf.set_text_color(150, 150, 150)
                        pdf.cell(0, 4, "Sem relator designado", ln=True)
                    else:
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 4, sanitize_text_pdf(mat['relator'])[:50], ln=True)
                    
                    # Ementa
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', '', 7)
                    pdf.set_text_color(60, 60, 60)
                    ementa = mat['ementa'][:250] + ('...' if len(mat['ementa']) > 250 else '')
                    pdf.multi_cell(160, 3.5, sanitize_text_pdf(ementa))
                    
                    # Link da matéria (clicável)
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'I', 6)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(3, "Abrir tramitacao", link=mat['link'])
                    pdf.ln(4)
                
                # Link do evento (clicável)
                if reg['link_evento']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(4, "Ver pauta do evento", link=reg['link_evento'])
                    pdf.ln(4)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        pdf.ln(5)
        
        # === SEÇÃO RELATORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  RELATORIA DA DEPUTADA ({len(registros_relatoria)} reuniao(oes))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_relatoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de relatoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_relatoria, 1):
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(8, 6, str(idx), fill=True, align='C')
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, f"  {reg['data']} as {reg['hora']}", ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:70], ln=True)
                
                # Cada matéria de relatoria
                for mat in reg['materias']:
                    if pdf.get_y() > 250:
                        pdf.add_page()
                        pdf.set_y(30)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 5, sanitize_text_pdf(mat['sigla']), ln=True)
                    
                    # Situação
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Situacao: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    sit = mat['situacao'] or '-'
                    if 'Arquiv' in sit:
                        pdf.set_text_color(150, 50, 50)
                    elif 'Pronta' in sit:
                        pdf.set_text_color(50, 150, 50)
                    else:
                        pdf.set_text_color(50, 50, 150)
                    pdf.cell(0, 4, sanitize_text_pdf(sit)[:55], ln=True)
                    
                    # Parecer (se houver)
                    if mat['parecer']:
                        pdf.set_x(25)
                        pdf.set_font('Helvetica', 'B', 8)
                        pdf.set_text_color(150, 100, 0)
                        pdf.cell(18, 4, "Parecer: ", ln=False)
                        pdf.set_font('Helvetica', '', 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.multi_cell(145, 4, sanitize_text_pdf(mat['parecer'])[:150])
                    
                    # Ementa
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', '', 7)
                    pdf.set_text_color(60, 60, 60)
                    ementa = mat['ementa'][:250] + ('...' if len(mat['ementa']) > 250 else '')
                    pdf.multi_cell(160, 3.5, sanitize_text_pdf(ementa))
                    
                    # Link da matéria (clicável)
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'I', 6)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(3, "Abrir tramitacao", link=mat['link'])
                    
                    # Link inteiro teor (se houver, clicável)
                    if mat.get('link_teor'):
                        pdf.write(3, " | ")
                        pdf.write(3, "Inteiro teor", link=mat['link_teor'])
                    
                    pdf.ln(4)
                
                # Link do evento (clicável)
                if reg['link_evento']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(4, "Ver pauta do evento", link=reg['link_evento'])
                    pdf.ln(4)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de autoria/relatoria: {str(e)}")


def to_pdf_comissoes_estrategicas(df: pd.DataFrame) -> tuple[bytes, str, str]:
    """PDF específico para Comissões Estratégicas - formato de gabinete."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Comissoes Estrategicas - Pautas", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # Cabeçalho informativo - fonte e critério
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Data do evento (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de reunioes: {len(df)}", ln=True)
        pdf.ln(3)
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df.copy()
        if 'data' in df_sorted.columns:
            df_sorted['_data_sort'] = pd.to_datetime(df_sorted['data'], errors='coerce', dayfirst=True)
            df_sorted = df_sorted.sort_values('_data_sort', ascending=False)
        
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(30)
            
            data = str(row.get('data', '-'))
            hora = str(row.get('hora', '-')) if pd.notna(row.get('hora')) else '-'
            orgao_sigla = str(row.get('orgao_sigla', '-'))
            orgao_nome = str(row.get('orgao_nome', ''))
            tipo_evento = str(row.get('tipo_evento', ''))
            id_evento = str(row.get('id_evento', ''))
            link = f"https://www.camara.leg.br/evento-legislativo/{id_evento}" if id_evento and id_evento != 'nan' else ""
            
            props_autoria = str(row.get('proposicoes_autoria', ''))
            props_relatoria = str(row.get('proposicoes_relatoria', ''))
            palavras_chave = str(row.get('palavras_chave_encontradas', ''))
            descricao = str(row.get('descricao_evento', ''))
            
            # Determinar cor baseado se tem relatoria/autoria
            tem_relatoria = props_relatoria and props_relatoria.strip() and props_relatoria != 'nan'
            tem_autoria = props_autoria and props_autoria.strip() and props_autoria != 'nan'
            
            # Card header
            pdf.set_font('Helvetica', 'B', 9)
            if tem_relatoria:
                pdf.set_fill_color(0, 51, 102)
            elif tem_autoria:
                pdf.set_fill_color(0, 100, 0)
            else:
                pdf.set_fill_color(100, 100, 100)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(8, 6, str(idx), fill=True, align='C')
            
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 6, f"  {orgao_sigla} - {data} as {hora}", ln=True)
            
            # Tipo e local
            pdf.set_x(20)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(100, 100, 100)
            if tipo_evento and tipo_evento != 'nan':
                pdf.cell(0, 4, sanitize_text_pdf(tipo_evento)[:80], ln=True)
            if orgao_nome and orgao_nome != orgao_sigla:
                pdf.set_x(20)
                pdf.cell(0, 4, sanitize_text_pdf(orgao_nome)[:80], ln=True)
            
            # Relatoria da deputada (destaque)
            if tem_relatoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 5, ">>> RELATORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_relatoria)[:400])
            
            # Autoria da deputada
            if tem_autoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 5, ">>> AUTORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_autoria)[:400])
            
            # Palavras-chave encontradas
            if palavras_chave and palavras_chave.strip() and palavras_chave != 'nan':
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_text_color(150, 100, 0)
                pdf.cell(30, 4, "Palavras-chave: ", ln=False)
                pdf.set_font('Helvetica', '', 8)
                pdf.cell(0, 4, sanitize_text_pdf(palavras_chave)[:60], ln=True)
            
            # Link (clicável)
            if link:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'I', 7)
                pdf.set_text_color(0, 0, 200)
                pdf.write(4, "Ver pauta do evento", link=link)
                pdf.ln(4)
            
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de comissões estratégicas: {str(e)}")


def to_pdf_palavras_chave(df: pd.DataFrame) -> tuple[bytes, str, str]:
    """
    Gera PDF de palavras-chave na pauta, organizado por Comissão.
    Foco nas PROPOSIÇÕES (matérias), não nos eventos.
    
    Estrutura por proposição:
    - Matéria (PL, REQ, etc)
    - Palavras-chave encontradas
    - Ementa
    - Relator
    - Link
    """
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Subtítulo e data
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Palavras-chave na Pauta", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # Extrair todas as proposições e agrupar por comissão
        proposicoes_por_comissao = {}
        todas_proposicoes = set()  # Para evitar duplicatas
        
        for _, row in df.iterrows():
            props_str = row.get("proposicoes_palavras_chave", "") or ""
            
            if not props_str or pd.isna(props_str):
                continue
            
            # Cada proposição está separada por "; "
            for prop_detail in str(props_str).split("; "):
                if "|||" not in prop_detail:
                    continue
                    
                partes = prop_detail.split("|||")
                
                # Formato: matéria|||palavras|||ementa|||link|||relator|||comissao|||nome_comissao|||data
                materia = partes[0].strip() if len(partes) > 0 else ""
                palavras = partes[1].strip() if len(partes) > 1 else ""
                ementa = partes[2].strip() if len(partes) > 2 else ""
                link = partes[3].strip() if len(partes) > 3 else ""
                
                # Relator - garantir que não está corrompido
                relator_raw = partes[4].strip() if len(partes) > 4 else ""
                if not relator_raw or len(relator_raw) < 5:
                    relator = "Sem relator designado"
                else:
                    relator = relator_raw
                
                comissao = partes[5].strip() if len(partes) > 5 else row.get("orgao_sigla", "Outras")
                nome_comissao = partes[6].strip() if len(partes) > 6 else ""
                data_evento = partes[7].strip() if len(partes) > 7 else ""
                
                # Formatar data para DD/MM/YYYY
                data_formatada = ""
                if data_evento and len(data_evento) >= 10:
                    try:
                        dt = datetime.datetime.strptime(data_evento[:10], "%Y-%m-%d")
                        data_formatada = dt.strftime("%d/%m/%Y")
                    except:
                        data_formatada = data_evento
                
                if not materia:
                    continue
                
                # Chave única para evitar duplicatas
                chave_unica = f"{materia}_{comissao}"
                if chave_unica in todas_proposicoes:
                    continue
                todas_proposicoes.add(chave_unica)
                
                if comissao not in proposicoes_por_comissao:
                    proposicoes_por_comissao[comissao] = {
                        "nome": nome_comissao,
                        "proposicoes": []
                    }
                
                proposicoes_por_comissao[comissao]["proposicoes"].append({
                    "materia": materia,
                    "palavras": palavras,
                    "ementa": ementa,
                    "link": link,
                    "relator": relator,
                    "data": data_formatada
                })
        
        # Ordenar comissões alfabeticamente
        comissoes_ordenadas = sorted(proposicoes_por_comissao.keys())
        
        # Contar total de proposições
        total_props = sum(len(c["proposicoes"]) for c in proposicoes_por_comissao.values())
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de materias encontradas: {total_props}", ln=True)
        pdf.cell(0, 6, f"Comissoes: {len(comissoes_ordenadas)}", ln=True)
        pdf.ln(4)
        
        # Iterar por comissão
        for comissao in comissoes_ordenadas:
            dados = proposicoes_por_comissao[comissao]
            props = dados["proposicoes"]
            nome_comissao = dados["nome"]
            
            if not props:
                continue
            
            # Cabeçalho da Comissão
            pdf.set_fill_color(0, 102, 153)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 11)
            titulo_comissao = f"  {sanitize_text_pdf(comissao)}"
            if nome_comissao:
                titulo_comissao += f" - {sanitize_text_pdf(nome_comissao)}"
            titulo_comissao += f" ({len(props)} materia{'s' if len(props) > 1 else ''})"
            pdf.cell(0, 8, titulo_comissao, ln=True, fill=True)
            pdf.ln(3)
            
            # Listar proposições
            for idx, prop in enumerate(props, 1):
                # 1. Matéria (em destaque) com data
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(0, 51, 102)
                materia_text = sanitize_text_pdf(prop.get('materia', '') or '')
                data_text = (prop.get("data", "") or "").strip()
                if data_text:
                    pdf.cell(0, 6, f"{idx}. [{data_text}] {materia_text}", ln=True)
                else:
                    pdf.cell(0, 6, f"{idx}. {materia_text}", ln=True)
                
                # 2. Palavras-chave
                palavras = (prop.get("palavras", "") or "").strip()
                if palavras:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(180, 0, 0)
                    pdf.cell(0, 5, f"   Palavras-chave: {sanitize_text_pdf(palavras)}", ln=True)
                
                # 3. Ementa (pode ser longa, usar multi_cell)
                ementa = (prop.get("ementa", "") or "").strip()
                if ementa:
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(60, 60, 60)
                    ementa_text = sanitize_text_pdf(ementa)
                    if len(ementa_text) > 250:
                        ementa_text = ementa_text[:250] + "..."
                    pdf.multi_cell(0, 4, f"   {ementa_text}")
                    # Garantir nova linha após multi_cell
                    pdf.ln(1)
                
                # 4. Relator - linha curta, usar cell
                relator_raw = (prop.get("relator", "") or "").strip()
                
                # Validação do relator
                relator_valido = (
                    relator_raw 
                    and len(relator_raw) > 5 
                    and "Sem relator" not in relator_raw 
                    and "(-)" not in relator_raw
                )
                
                pdf.set_font('Helvetica', 'B', 9)
                if relator_valido:
                    pdf.set_text_color(0, 100, 0)
                    texto_relator = "   Relator(a): " + sanitize_text_pdf(relator_raw)
                else:
                    pdf.set_text_color(128, 128, 128)
                    texto_relator = "   Relator(a): Sem relator designado"
                
                pdf.cell(0, 5, texto_relator, ln=True)
                
                # 5. Link
                link = (prop.get("link", "") or "").strip()
                if link:
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(0, 0, 180)
                    pdf.cell(0, 4, f"   {link}", ln=True)
                
                pdf.ln(3)
            
            pdf.ln(2)
        
        pdf_bytes = pdf.output()
        return (bytes(pdf_bytes), "application/pdf", "pdf")
        
    except Exception as e:
        # Fallback simples
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 10, f"Erro ao gerar PDF: {str(e)}", ln=True)
        pdf_bytes = pdf.output()
        return (bytes(pdf_bytes), "application/pdf", "pdf")


def to_pdf_rics_por_status(df: pd.DataFrame, titulo: str = "RICs - Requerimentos de Informação") -> tuple[bytes, str, str]:
    """
    Gera PDF de RICs organizado por blocos de status.
    
    Blocos na ordem:
    1. Aguardando resposta (No prazo)
    2. Aguardando resposta (Fora do prazo) / Fora do prazo
    3. Em tramitação na Câmara
    4. Respondido / Respondido fora do prazo
    """
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 22, 'F')
                self.set_font('Helvetica', 'B', 16)
                self.set_text_color(255, 255, 255)
                self.set_y(6)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(18)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Título
        pdf.set_y(28)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, sanitize_text_pdf(titulo), ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Prazo constitucional: 30 dias apos remessa", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # Total geral
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de RICs: {len(df)}", ln=True)
        pdf.ln(3)
        
        # Determinar coluna de status
        col_status = None
        for c in ['Status', 'RIC_StatusResposta']:
            if c in df.columns:
                col_status = c
                break
        
        if not col_status:
            col_status = 'Status'
            df[col_status] = 'Aguardando resposta'
        
        # Definir os blocos
        blocos = [
            {
                'titulo': '⏳ AGUARDANDO RESPOSTA (No Prazo)',
                'filtro': lambda x: x == 'Aguardando resposta',
                'cor': (255, 193, 7),  # Amarelo
            },
            {
                'titulo': '⚠️ FORA DO PRAZO (Sem Resposta)',
                'filtro': lambda x: x == 'Fora do prazo',
                'cor': (220, 53, 69),  # Vermelho
            },
            {
                'titulo': '🏛️ EM TRAMITAÇÃO NA CÂMARA',
                'filtro': lambda x: x == 'Em tramitação na Câmara',
                'cor': (108, 117, 125),  # Cinza
            },
            {
                'titulo': '✅ RESPONDIDOS',
                'filtro': lambda x: x in ['Respondido', 'Respondido fora do prazo'],
                'cor': (40, 167, 69),  # Verde
            },
        ]
        
        # Colunas para exibir nos cards
        col_ric = next((c for c in ['RIC', 'Proposicao'] if c in df.columns), None)
        col_ministerio = next((c for c in ['Ministério', 'RIC_Ministerio'] if c in df.columns), None)
        col_prazo = next((c for c in ['Prazo', 'RIC_PrazoStr'] if c in df.columns), None)
        col_ementa = next((c for c in ['ementa', 'Ementa'] if c in df.columns), None)
        col_situacao = next((c for c in ['Situação atual', 'Situacao atual'] if c in df.columns), None)
        col_data = next((c for c in ['Última tramitação', 'Data do status'] if c in df.columns), None)
        
        for bloco in blocos:
            df_bloco = df[df[col_status].apply(bloco['filtro'])].copy()
            
            if df_bloco.empty:
                continue
            
            # Cabeçalho do bloco
            pdf.ln(4)
            pdf.set_fill_color(*bloco['cor'])
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, f"  {sanitize_text_pdf(bloco['titulo'])} ({len(df_bloco)})", ln=True, fill=True)
            pdf.ln(3)
            
            # Ordenar por data mais recente
            if col_data and col_data in df_bloco.columns:
                df_bloco['_sort_dt'] = pd.to_datetime(df_bloco[col_data], errors='coerce', dayfirst=True)
                df_bloco = df_bloco.sort_values('_sort_dt', ascending=False)
            
            # Renderizar cada RIC
            for idx, (_, row) in enumerate(df_bloco.iterrows()):
                # Verificar se precisa nova página
                if pdf.get_y() > 250:
                    pdf.add_page()
                
                # Nome do RIC
                ric_nome = sanitize_text_pdf(str(row.get(col_ric, ''))) if col_ric else "RIC"
                
                # Card do RIC
                pdf.set_fill_color(245, 245, 245)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, f"{idx+1}. {ric_nome}", ln=True)
                
                # Ministério
                if col_ministerio:
                    ministerio = sanitize_text_pdf(str(row.get(col_ministerio, '') or 'Não identificado'))
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(60, 60, 60)
                    pdf.cell(0, 5, f"Ministerio: {ministerio}", ln=True)
                
                # Prazo - tentar múltiplas fontes
                prazo_display = "-"
                if col_prazo:
                    prazo_val = row.get(col_prazo, '')
                    if prazo_val and str(prazo_val).strip() and str(prazo_val) != '-':
                        prazo_display = sanitize_text_pdf(str(prazo_val))
                    else:
                        # Fallback para RIC_PrazoFim ou RIC_PrazoStr
                        prazo_fim = row.get('RIC_PrazoFim') or row.get('RIC_PrazoStr', '')
                        if prazo_fim and str(prazo_fim).strip():
                            try:
                                if hasattr(prazo_fim, 'strftime'):
                                    prazo_display = f"ate {prazo_fim.strftime('%d/%m/%Y')}"
                                else:
                                    prazo_display = sanitize_text_pdf(str(prazo_fim))
                            except:
                                pass
                        # Verificar dias restantes
                        dias = row.get('RIC_DiasRestantes')
                        if dias is not None and pd.notna(dias) and prazo_display != "-":
                            try:
                                dias_int = int(dias)
                                if dias_int < 0:
                                    prazo_display += f" ({abs(dias_int)}d restantes)"
                                else:
                                    prazo_display += f" ({dias_int}d restantes)"
                            except:
                                pass
                pdf.cell(0, 5, f"Prazo: {prazo_display}", ln=True)
                
                # Situação atual
                if col_situacao:
                    sit = sanitize_text_pdf(str(row.get(col_situacao, '') or '-'))
                    pdf.cell(0, 5, f"Situacao: {sit}", ln=True)
                
                # Data última tramitação
                if col_data:
                    data = sanitize_text_pdf(str(row.get(col_data, '') or '-'))
                    pdf.cell(0, 5, f"Ultima tramitacao: {data}", ln=True)
                
                # Ementa
                if col_ementa:
                    ementa = str(row.get(col_ementa, '') or '')
                    if ementa:
                        ementa_trunc = sanitize_text_pdf(ementa[:200] + "..." if len(ementa) > 200 else ementa)
                        pdf.set_font('Helvetica', 'I', 8)
                        pdf.set_text_color(80, 80, 80)
                        pdf.multi_cell(0, 4, f"Ementa: {ementa_trunc}")
                
                # Linha separadora
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(3)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de RICs: {str(e)}")


def buscar_pauta_semana_atual(id_deputada: int, nome_deputada: str, partido: str, uf: str) -> pd.DataFrame:
    """
    Busca a pauta da semana atual (segunda a sexta) diretamente da API.
    Retorna DataFrame com eventos que têm matérias de autoria ou relatoria da deputada.
    """
    hoje = get_brasilia_now().date()
    
    # Calcular segunda-feira da semana atual
    dias_desde_segunda = hoje.weekday()  # 0 = segunda, 6 = domingo
    segunda = hoje - datetime.timedelta(days=dias_desde_segunda)
    sexta = segunda + datetime.timedelta(days=4)
    
    try:
        # Buscar eventos da semana
        eventos = []
        pagina = 1
        while True:
            params = {
                "dataInicio": segunda.strftime("%Y-%m-%d"),
                "dataFim": sexta.strftime("%Y-%m-%d"),
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
        
        if not eventos:
            return pd.DataFrame()
        
        # Buscar IDs de autoria da deputada
        ids_autoria = set()
        url = f"{BASE_URL}/proposicoes"
        params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "ASC", "ordenarPor": "id"}
        while True:
            data = safe_get(url, params=params)
            if data is None or "__error__" in data:
                break
            for d in data.get("dados", []):
                if d.get("id"):
                    ids_autoria.add(str(d["id"]))
            next_link = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_link = link.get("href")
                    break
            if not next_link:
                break
            url = next_link
            params = {}
        
        # Escanear eventos para encontrar matérias de autoria/relatoria
        registros = []
        for ev in eventos:
            event_id = ev.get("id") or ev.get("codEvento")
            if event_id is None:
                continue
            
            data_hora_ini = ev.get("dataHoraInicio") or ""
            data_str = data_hora_ini[:10] if len(data_hora_ini) >= 10 else ""
            hora_str = data_hora_ini[11:16] if len(data_hora_ini) >= 16 else ""
            
            orgaos = ev.get("orgaos") or [{"sigla": "", "nome": "", "id": None}]
            
            # Buscar pauta do evento
            pauta_data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
            pauta = pauta_data.get("dados", []) if pauta_data and "__error__" not in pauta_data else []
            
            proposicoes_relatoria = set()
            proposicoes_autoria = set()
            
            for item in pauta:
                # Verificar relatoria
                relator = item.get("relator") or {}
                nome_relator = relator.get("nome") or ""
                if normalize_text(nome_deputada) in normalize_text(nome_relator):
                    id_prop = get_proposicao_id_from_item(item)
                    if id_prop:
                        info = fetch_proposicao_info(id_prop)
                        identificacao = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or "(proposicao)"
                        ementa_prop = info["ementa"]
                        texto = f"{identificacao} - {ementa_prop[:150]}..." if ementa_prop else identificacao
                        proposicoes_relatoria.add(texto)
                
                # Verificar autoria
                id_prop = get_proposicao_id_from_item(item)
                if id_prop and id_prop in ids_autoria:
                    info = fetch_proposicao_info(id_prop)
                    identificacao = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or "(proposicao)"
                    ementa_prop = info["ementa"]
                    texto = f"{identificacao} - {ementa_prop[:150]}..." if ementa_prop else identificacao
                    proposicoes_autoria.add(texto)
            
            if proposicoes_relatoria or proposicoes_autoria:
                for org in orgaos:
                    sigla_org = org.get("siglaOrgao") or org.get("sigla") or ""
                    nome_org = org.get("nomeOrgao") or org.get("nome") or ""
                    registros.append({
                        "data": data_str,
                        "hora": hora_str,
                        "orgao_sigla": sigla_org,
                        "orgao_nome": nome_org,
                        "tem_relatoria_deputada": bool(proposicoes_relatoria),
                        "proposicoes_relatoria": "; ".join(sorted(proposicoes_relatoria)),
                        "tem_autoria_deputada": bool(proposicoes_autoria),
                        "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)),
                    })
        
        df = pd.DataFrame(registros)
        if not df.empty:
            df = df.sort_values(["data", "hora", "orgao_sigla"])
        return df
    
    except Exception as e:
        return pd.DataFrame()


def gerar_texto_analise_estrategica(
    nome_deputada: str,
    partido: str,
    uf: str,
    props_autoria: list,
    tipos_count: dict,
    df_pauta: pd.DataFrame,
    df_rics: pd.DataFrame
) -> str:
    """
    Gera texto corrido de análise estratégica como um analista legislativo sênior.
    Linguagem formal, técnica e institucional, sem listas ou bullets.
    """
    hoje = get_brasilia_now().date()
    dias_desde_segunda = hoje.weekday()
    segunda = hoje - datetime.timedelta(days=dias_desde_segunda)
    sexta = segunda + datetime.timedelta(days=4)
    periodo = f"{segunda.strftime('%d/%m')} a {sexta.strftime('%d/%m/%Y')}"
    
    total_props = len(props_autoria) if props_autoria else 0
    rics_total = tipos_count.get('RIC', 0) if tipos_count else 0
    pls_total = (tipos_count.get('PL', 0) + tipos_count.get('PLP', 0)) if tipos_count else 0
    
    # Análise da pauta
    tem_pauta = not df_pauta.empty
    autoria_count = 0
    relatoria_count = 0
    materias_autoria = []
    materias_relatoria = []
    
    if tem_pauta:
        if "tem_autoria_deputada" in df_pauta.columns:
            df_aut = df_pauta[df_pauta["tem_autoria_deputada"] == True]
            autoria_count = len(df_aut)
            for _, row in df_aut.iterrows():
                orgao = row.get("orgao_sigla", "")
                props = row.get("proposicoes_autoria", "")
                if props:
                    # Extrair sigla da proposição (ex: PL 1234/2025)
                    prop_sigla = props.split(" - ")[0] if " - " in props else props.split(";")[0].strip()
                    materias_autoria.append(f"{prop_sigla} na {orgao}")
        
        if "tem_relatoria_deputada" in df_pauta.columns:
            df_rel = df_pauta[df_pauta["tem_relatoria_deputada"] == True]
            relatoria_count = len(df_rel)
            for _, row in df_rel.iterrows():
                orgao = row.get("orgao_sigla", "")
                props = row.get("proposicoes_relatoria", "")
                if props:
                    prop_sigla = props.split(" - ")[0] if " - " in props else props.split(";")[0].strip()
                    materias_relatoria.append(f"{prop_sigla} na {orgao}")
    
    # Análise dos RICs
    rics_fora_prazo = 0
    rics_aguardando = 0
    if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
        rics_fora_prazo = len(df_rics[df_rics["RIC_StatusResposta"] == "Fora do prazo"])
        rics_aguardando = len(df_rics[df_rics["RIC_StatusResposta"] == "Aguardando resposta"])
    
    # Construir texto corrido
    paragrafos = []
    
    # Parágrafo 1: Contexto e pauta
    if not tem_pauta or (autoria_count == 0 and relatoria_count == 0):
        p1 = f"Na semana de {periodo}, nao foram identificadas materias de autoria ou relatoria da Deputada {nome_deputada} ({partido}-{uf}) nas pautas das comissoes e do Plenario da Camara dos Deputados. "
        p1 += f"Este cenario permite concentrar esforcos na articulacao politica, no acompanhamento de proposicoes em tramitacao e na preparacao de novas iniciativas legislativas. "
    else:
        p1 = f"A semana legislativa de {periodo} apresenta movimentacao relevante para o mandato da Deputada {nome_deputada} ({partido}-{uf}). "
        
        if autoria_count > 0:
            p1 += f"Foram identificadas {autoria_count} materia(s) de autoria em pauta, demandando acompanhamento prioritario para eventual votacao. "
            if materias_autoria:
                p1 += f"Destaca-se {materias_autoria[0]}, que avanca na tramitacao e requer decisao estrategica quanto a articulacao com a base aliada. "
        
        if relatoria_count > 0:
            p1 += f"Alem disso, a parlamentar figura como relatora em {relatoria_count} proposicao(oes), "
            if materias_relatoria:
                p1 += f"incluindo {materias_relatoria[0]}, exigindo finalizacao de parecer e posicionamento institucional. "
            else:
                p1 += "o que exige atencao para elaboracao ou atualizacao de pareceres. "
    
    paragrafos.append(p1)
    
    # Parágrafo 2: Produção e fiscalização
    p2 = f"No ambito da producao legislativa, o acervo da Deputada totaliza {total_props} proposicoes de autoria, sendo {pls_total} projetos de lei e {rics_total} requerimentos de informacao. "
    
    if rics_fora_prazo > 0 or rics_aguardando > 0:
        p2 += f"Quanto a atividade fiscalizatoria, "
        if rics_fora_prazo > 0:
            p2 += f"ha {rics_fora_prazo} RIC(s) com prazo de resposta vencido pelo Poder Executivo, situacao que demanda avaliacao de medidas de cobranca formal. "
        if rics_aguardando > 0:
            p2 += f"Outros {rics_aguardando} requerimento(s) aguardam resposta dentro do prazo legal. "
    else:
        p2 += "Os requerimentos de informacao encontram-se em situacao regular quanto aos prazos de resposta. "
    
    paragrafos.append(p2)
    
    return " ".join(paragrafos)


def gerar_relatorio_semanal(
    nome_deputada: str,
    partido: str,
    uf: str,
    id_deputada: int,
    props_autoria: list,
    tipos_count: dict,
    df_rics: pd.DataFrame
) -> bytes:
    """
    Gera um relatório PDF semanal com análise estratégica.
    BUSCA AUTOMATICAMENTE a pauta da semana (segunda a sexta).
    Segue o padrão visual dos outros PDFs do sistema.
    """
    from fpdf import FPDF
    
    # Buscar pauta da semana automaticamente
    df_pauta = buscar_pauta_semana_atual(id_deputada, nome_deputada, partido, uf)
    
    # Calcular datas da semana
    hoje = get_brasilia_now().date()
    dias_desde_segunda = hoje.weekday()
    segunda = hoje - datetime.timedelta(days=dias_desde_segunda)
    sexta = segunda + datetime.timedelta(days=4)
    periodo_semana = f"{segunda.strftime('%d/%m')} a {sexta.strftime('%d/%m/%Y')}"
    
    class RelatorioSemanalPDF(FPDF):
        def header(self):
            self.set_fill_color(0, 51, 102)
            self.rect(0, 0, 210, 25, 'F')
            self.set_font('Helvetica', 'B', 20)
            self.set_text_color(255, 255, 255)
            self.set_y(8)
            self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
            self.ln(20)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.set_x(10)
            self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
            self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
    
    pdf = RelatorioSemanalPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # ============================================================
    # CABEÇALHO
    # ============================================================
    pdf.set_y(30)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "Relatorio Semanal", ln=True, align='C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
    pdf.cell(0, 6, sanitize_text_pdf(f"Dep. {nome_deputada} ({partido}-{uf})"), ln=True, align='C')
    pdf.cell(0, 6, f"Semana: {periodo_semana}", ln=True, align='C')
    
    pdf.ln(2)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br", ln=True, align='C')
    
    pdf.ln(3)
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ============================================================
    # ANÁLISE ESTRATÉGICA (TEXTO CORRIDO - DESTAQUE PRINCIPAL)
    # ============================================================
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "Analise Estrategica", ln=True)
    pdf.ln(2)
    
    # Gerar texto de análise
    texto_analise = gerar_texto_analise_estrategica(
        nome_deputada, partido, uf, props_autoria, tipos_count, df_pauta, df_rics
    )
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5, sanitize_text_pdf(texto_analise))
    
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ============================================================
    # PAUTA DA SEMANA (DETALHAMENTO)
    # ============================================================
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "Pauta da Semana - Detalhamento", ln=True)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    if df_pauta.empty:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Nao ha materias de autoria ou relatoria na pauta da semana.", ln=True)
    else:
        tem_autoria = "tem_autoria_deputada" in df_pauta.columns
        tem_relatoria = "tem_relatoria_deputada" in df_pauta.columns
        
        autoria_count = len(df_pauta[df_pauta["tem_autoria_deputada"] == True]) if tem_autoria else 0
        relatoria_count = len(df_pauta[df_pauta["tem_relatoria_deputada"] == True]) if tem_relatoria else 0
        
        # Listar matérias de autoria
        if tem_autoria and autoria_count > 0:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(40, 167, 69)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 7, f"  AUTORIA ({autoria_count})", ln=True, fill=True)
            pdf.ln(2)
            
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(0, 0, 0)
            
            df_aut_pauta = df_pauta[df_pauta["tem_autoria_deputada"] == True]
            for idx, (_, row) in enumerate(df_aut_pauta.head(15).iterrows(), 1):
                data = row.get("data", "")
                hora = row.get("hora", "")
                orgao = row.get("orgao_sigla", "")
                props = row.get("proposicoes_autoria", "")
                
                if props:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.cell(0, 5, f"{idx}. {data} {hora} - {orgao}", ln=True)
                    pdf.set_font('Helvetica', '', 8)
                    props_trunc = str(props)[:250] + "..." if len(str(props)) > 250 else str(props)
                    pdf.multi_cell(0, 4, f"   {sanitize_text_pdf(props_trunc)}")
                    pdf.ln(1)
            pdf.ln(3)
        
        # Listar matérias de relatoria
        if tem_relatoria and relatoria_count > 0:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(0, 123, 255)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 7, f"  RELATORIA ({relatoria_count})", ln=True, fill=True)
            pdf.ln(2)
            
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(0, 0, 0)
            
            df_rel_pauta = df_pauta[df_pauta["tem_relatoria_deputada"] == True]
            for idx, (_, row) in enumerate(df_rel_pauta.head(15).iterrows(), 1):
                data = row.get("data", "")
                hora = row.get("hora", "")
                orgao = row.get("orgao_sigla", "")
                props = row.get("proposicoes_relatoria", "")
                
                if props:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.cell(0, 5, f"{idx}. {data} {hora} - {orgao}", ln=True)
                    pdf.set_font('Helvetica', '', 8)
                    props_trunc = str(props)[:250] + "..." if len(str(props)) > 250 else str(props)
                    pdf.multi_cell(0, 4, f"   {sanitize_text_pdf(props_trunc)}")
                    pdf.ln(1)
    
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ============================================================
    # RESUMO EM NÚMEROS
    # ============================================================
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "Resumo em Numeros", ln=True)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    total_props = len(props_autoria) if props_autoria else 0
    rics_total = tipos_count.get('RIC', 0) if tipos_count else 0
    pls_total = (tipos_count.get('PL', 0) + tipos_count.get('PLP', 0)) if tipos_count else 0
    pareceres_total = tipos_count.get('PRL', 0) if tipos_count else 0
    
    pdf.cell(0, 6, f"Total de proposicoes de autoria: {total_props}", ln=True)
    pdf.cell(0, 6, f"Requerimentos de Informacao (RIC): {rics_total}", ln=True)
    pdf.cell(0, 6, f"Projetos de Lei (PL + PLP): {pls_total}", ln=True)
    pdf.cell(0, 6, f"Pareceres (PRL): {pareceres_total}", ln=True)
    
    # RICs pendentes
    if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
        rics_pendentes = len(df_rics[df_rics["RIC_StatusResposta"].isin(["Aguardando resposta", "Fora do prazo", "Em tramitação na Câmara"])])
        rics_respondidos = len(df_rics[df_rics["RIC_StatusResposta"].str.contains("Respondido", na=False)])
        pdf.cell(0, 6, f"RICs pendentes de resposta: {rics_pendentes}", ln=True)
        pdf.cell(0, 6, f"RICs respondidos: {rics_respondidos}", ln=True)
    
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ============================================================
    # RICS PENDENTES (SE HOUVER)
    # ============================================================
    if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
        df_fora = df_rics[df_rics["RIC_StatusResposta"] == "Fora do prazo"]
        df_aguard = df_rics[df_rics["RIC_StatusResposta"] == "Aguardando resposta"]
        
        if not df_fora.empty or not df_aguard.empty:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 8, "RICs Pendentes - Atencao", ln=True)
            pdf.ln(2)
            
            if not df_fora.empty:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(220, 53, 69)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 7, f"  FORA DO PRAZO ({len(df_fora)})", ln=True, fill=True)
                pdf.ln(2)
                
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                
                for idx, (_, row) in enumerate(df_fora.head(10).iterrows(), 1):
                    ric = row.get("Proposicao", f"{row.get('siglaTipo', '')} {row.get('numero', '')}/{row.get('ano', '')}")
                    ministerio = row.get("RIC_Ministerio", "Nao identificado")
                    pdf.cell(0, 5, f"{idx}. {sanitize_text_pdf(str(ric))} - {sanitize_text_pdf(str(ministerio))}", ln=True)
                pdf.ln(2)
            
            if not df_aguard.empty:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(255, 193, 7)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 7, f"  AGUARDANDO RESPOSTA ({len(df_aguard)})", ln=True, fill=True)
                pdf.ln(2)
                
                pdf.set_font('Helvetica', '', 9)
                
                for idx, (_, row) in enumerate(df_aguard.head(10).iterrows(), 1):
                    ric = row.get("Proposicao", f"{row.get('siglaTipo', '')} {row.get('numero', '')}/{row.get('ano', '')}")
                    ministerio = row.get("RIC_Ministerio", "Nao identificado")
                    dias = row.get("RIC_DiasRestantes", "?")
                    pdf.cell(0, 5, f"{idx}. {sanitize_text_pdf(str(ric))} - {sanitize_text_pdf(str(ministerio))} ({dias} dias)", ln=True)
    
    output = BytesIO()
    pdf.output(output)
    return output.getvalue()


def gerar_analise_estrategica(props_autoria: list, tipos_count: dict, df_pauta: pd.DataFrame, df_rics: pd.DataFrame) -> str:
    """
    Gera um texto de análise estratégica baseado nos dados disponíveis.
    (Mantida para compatibilidade, mas não é mais usada no PDF principal)
    """
    paragrafos = []
    hoje = get_brasilia_now().date()
    
    paragrafos.append(f"Analise referente a semana de {hoje.strftime('%d/%m/%Y')}.")
    
    if not df_pauta.empty:
        total_eventos = len(df_pauta)
        tem_autoria = "tem_autoria_deputada" in df_pauta.columns
        tem_relatoria = "tem_relatoria_deputada" in df_pauta.columns
        autoria_count = len(df_pauta[df_pauta["tem_autoria_deputada"] == True]) if tem_autoria else 0
        relatoria_count = len(df_pauta[df_pauta["tem_relatoria_deputada"] == True]) if tem_relatoria else 0
        
        if autoria_count > 0 or relatoria_count > 0:
            paragrafos.append(f"\nPAUTA: {total_eventos} eventos identificados. ")
            if autoria_count > 0:
                paragrafos.append(f"{autoria_count} materia(s) de autoria em votacao. ")
            if relatoria_count > 0:
                paragrafos.append(f"{relatoria_count} materia(s) de relatoria. ")
        else:
            paragrafos.append(f"\nPAUTA: {total_eventos} eventos, sem materias de autoria/relatoria.")
    else:
        paragrafos.append("\nPAUTA: Nao ha materias na pauta da semana.")
    
    if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
        fora_prazo = len(df_rics[df_rics["RIC_StatusResposta"] == "Fora do prazo"])
        aguardando = len(df_rics[df_rics["RIC_StatusResposta"] == "Aguardando resposta"])
        
        if fora_prazo > 0:
            paragrafos.append(f"\nALERTA: {fora_prazo} RIC(s) fora do prazo. ")
        if aguardando > 0:
            paragrafos.append(f"{aguardando} RIC(s) aguardando resposta. ")
    
    if props_autoria and tipos_count:
        total = len(props_autoria)
        pls = tipos_count.get('PL', 0) + tipos_count.get('PLP', 0)
        pareceres = tipos_count.get('PRL', 0)
        paragrafos.append(f"\nPRODUCAO: {total} proposicoes, {pls} PL(s), {pareceres} parecer(es).")
    
    return "".join(paragrafos)


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


# Partidos da base/oposição para identificar relator adversário
PARTIDOS_OPOSICAO = {"PT", "PSOL", "PCDOB", "PC DO B", "REDE", "PV", "PSB", "PDT", "PSDB"}


def gerar_acao_sugerida(row: pd.Series) -> str:
    """Gera ação sugerida baseada na situação e contexto da proposição."""
    situacao = str(row.get("Situação atual", "") or "").lower()
    dias_parado = row.get("Parado há (dias)", 0)
    relator = str(row.get("Relator(a)", "") or "")
    
    acoes = []
    
    # Verificar relator adversário
    if relator and relator.strip() and relator != "-":
        for partido in PARTIDOS_OPOSICAO:
            if partido in relator.upper():
                acoes.append("⚠️ Relator adversario: atencao")
                break
    
    # Ações por situação
    if "aguardando designa" in situacao or "sem relator" in situacao:
        acoes.append("Cobrar designacao de relator")
    elif "pronta para pauta" in situacao:
        acoes.append("Articular inclusao em pauta")
    elif "aguardando delibera" in situacao:
        acoes.append("Preparar fala/destaque para votacao")
    elif "aguardando parecer" in situacao:
        acoes.append("Acompanhar elaboracao do parecer")
    elif "tramitando em conjunto" in situacao:
        acoes.append("Monitorar proposicao principal")
    
    # Ação por tempo parado
    try:
        dias = int(dias_parado) if pd.notna(dias_parado) else 0
    except:
        dias = 0
    
    if dias >= 30:
        acoes.append("DESTRAVAR: contato com comissao/lideranca")
    elif dias >= 15:
        acoes.append("Verificar andamento com secretaria")
    
    return " | ".join(acoes) if acoes else "Acompanhar tramitacao"


def calcular_prioridade(row: pd.Series) -> int:
    """Calcula score de prioridade (quanto maior, mais urgente)."""
    score = 0
    
    # Por sinal/dias parado
    dias = row.get("Parado há (dias)", 0)
    try:
        dias = int(dias) if pd.notna(dias) else 0
    except:
        dias = 0
    
    if dias >= 30:
        score += 100  # Crítico
    elif dias >= 15:
        score += 70   # Atenção
    elif dias >= 7:
        score += 40   # Monitoramento
    
    # Por situação crítica
    situacao = str(row.get("Situação atual", "") or "").lower()
    if "pronta para pauta" in situacao:
        score += 50
    elif "aguardando delibera" in situacao:
        score += 45
    elif "aguardando designa" in situacao:
        score += 30
    
    # Relator adversário
    relator = str(row.get("Relator(a)", "") or "")
    for partido in PARTIDOS_OPOSICAO:
        if partido in relator.upper():
            score += 20
            break
    
    return score


def render_resumo_executivo(df: pd.DataFrame):
    """Renderiza bloco de resumo executivo no topo."""
    if df.empty:
        return
    
    st.markdown("### 📊 Resumo Executivo")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(df)
    
    # Contagem por sinal (baseado em dias parado)
    def get_sinal_count(df, min_dias, max_dias=None):
        try:
            if "Parado há (dias)" in df.columns:
                if max_dias:
                    return len(df[(df["Parado há (dias)"] >= min_dias) & (df["Parado há (dias)"] < max_dias)])
                return len(df[df["Parado há (dias)"] >= min_dias])
        except:
            pass
        return 0
    
    criticos = get_sinal_count(df, 30)
    atencao = get_sinal_count(df, 15, 30)
    monitoramento = get_sinal_count(df, 7, 15)
    
    with col1:
        st.metric("📋 Total de Matérias", total)
    with col2:
        st.metric("🔴 Críticas (≥30 dias)", criticos)
    with col3:
        st.metric("🟠 Atenção (15-29 dias)", atencao)
    with col4:
        st.metric("🟡 Monitorar (7-14 dias)", monitoramento)
    
    # Contagem por situações-chave
    st.markdown("#### 📌 Por Situação-Chave")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    def count_situacao(df, termo):
        if "Situação atual" not in df.columns:
            return 0
        return len(df[df["Situação atual"].fillna("").str.lower().str.contains(termo.lower())])
    
    with col_s1:
        st.metric("🔍 Aguard. Relator", count_situacao(df, "aguardando designa"))
    with col_s2:
        st.metric("📝 Aguard. Parecer", count_situacao(df, "aguardando parecer"))
    with col_s3:
        st.metric("📅 Pronta p/ Pauta", count_situacao(df, "pronta para pauta"))
    with col_s4:
        st.metric("🗳️ Aguard. Deliberação", count_situacao(df, "aguardando delibera"))
    
    # Top 3 órgãos e situações
    st.markdown("#### 🏛️ Top 3 Órgãos e Situações")
    col_o, col_sit = st.columns(2)
    
    with col_o:
        if "Órgão (sigla)" in df.columns:
            top_orgaos = df["Órgão (sigla)"].value_counts().head(3)
            for orgao, qtd in top_orgaos.items():
                st.write(f"**{orgao}**: {qtd}")
    
    with col_sit:
        if "Situação atual" in df.columns:
            top_sit = df["Situação atual"].value_counts().head(3)
            for sit, qtd in top_sit.items():
                sit_short = sit[:40] + "..." if len(str(sit)) > 40 else sit
                st.write(f"**{sit_short}**: {qtd}")
    
    st.markdown("---")


def render_atencao_deputada(df: pd.DataFrame):
    """Renderiza bloco 'Atenção da Deputada' com Top 5 prioridades."""
    if df.empty:
        return
    
    st.markdown("### ⚠️ Atenção da Deputada (Top 5)")
    st.caption("Matérias que exigem decisão ou ação imediata")
    
    # Adicionar coluna de prioridade e ação
    df_pri = df.copy()
    df_pri["_prioridade"] = df_pri.apply(calcular_prioridade, axis=1)
    df_pri["Ação Sugerida"] = df_pri.apply(gerar_acao_sugerida, axis=1)
    
    # Ordenar por prioridade e pegar top 5
    df_top5 = df_pri.nlargest(5, "_prioridade")
    
    # Mostrar cards
    for idx, (_, row) in enumerate(df_top5.iterrows(), 1):
        prop = row.get("Proposição", row.get("siglaTipo", "")) 
        if "numero" in df.columns:
            prop = f"{row.get('siglaTipo', '')} {row.get('numero', '')}/{row.get('ano', '')}"
        
        orgao = row.get("Órgão (sigla)", "-")
        situacao = str(row.get("Situação atual", "-"))[:50]
        acao = row.get("Ação Sugerida", "-")
        dias = row.get("Parado há (dias)", "-")
        
        # Cor do sinal
        try:
            d = int(dias)
            if d >= 30:
                sinal = "🔴"
            elif d >= 15:
                sinal = "🟠"
            elif d >= 7:
                sinal = "🟡"
            else:
                sinal = "🟢"
        except:
            sinal = "⚪"
        
        st.markdown(f"""
        **{idx}. {sinal} {prop}** | {orgao} | {dias} dias  
        *Situação:* {situacao}  
        *→ Ação:* **{acao}**
        """)
    
    st.markdown("---")


def render_prioridades_gabinete(df: pd.DataFrame):
    """Renderiza tabela 'Top Prioridades do Gabinete' com Top 20."""
    if df.empty:
        return
    
    st.markdown("### 📋 Top Prioridades do Gabinete (Top 20)")
    st.caption("Para distribuição de tarefas e acompanhamento")
    
    # Adicionar colunas calculadas
    df_pri = df.copy()
    df_pri["_prioridade"] = df_pri.apply(calcular_prioridade, axis=1)
    df_pri["Ação Sugerida"] = df_pri.apply(gerar_acao_sugerida, axis=1)
    
    # Ordenar e pegar top 20
    df_top20 = df_pri.nlargest(20, "_prioridade")
    
    # Selecionar colunas para exibição
    colunas_exibir = []
    for col in ["Proposição", "Situação atual", "Órgão (sigla)", "Parado há (dias)", "Relator(a)", "Ação Sugerida"]:
        if col in df_top20.columns:
            colunas_exibir.append(col)
    
    if "Ação Sugerida" not in colunas_exibir:
        colunas_exibir.append("Ação Sugerida")
    
    if colunas_exibir:
        st.dataframe(
            df_top20[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ação Sugerida": st.column_config.TextColumn("Ação Sugerida", width="large"),
            }
        )
    
    st.markdown("---")


def categorizar_tema(ementa: str) -> str:
    """Categoriza uma proposição por tema baseado na ementa - REFINADO com scoring."""
    if not ementa:
        return "Não Classificado"
    ementa_norm = normalize_text(ementa)
    
    # Conta matches por tema para pegar o mais relevante
    scores = {}
    for tema, palavras in TEMAS_CATEGORIAS.items():
        score = 0
        for palavra in palavras:
            if palavra in ementa_norm:
                score += 1
        if score > 0:
            scores[tema] = score
    
    if scores:
        # Retorna o tema com mais matches
        return max(scores, key=scores.get)
    
    return "Não Classificado"


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


def pauta_item_palavras_chave(item, palavras_chave_normalizadas, id_prop=None):
    """
    Busca palavras-chave na ementa e descrição do item da pauta.
    Se id_prop for fornecido, também busca a ementa completa da proposição na API.
    
    IMPORTANTE: Busca por PALAVRA INTEIRA para evitar falsos positivos
    (ex: "arma" não deve casar com "Farmanguinhos")
    """
    textos = []
    
    # Busca nos campos do item da pauta
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        v = item.get(chave)
        if v:
            textos.append(str(v))

    # Busca nos campos da proposição interna do item
    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop.get(chave)
        if v:
            textos.append(str(v))
    
    # Busca na proposição relacionada
    prop_rel = item.get("proposicaoRelacionada") or item.get("proposicao_") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop_rel.get(chave)
        if v:
            textos.append(str(v))
    
    # Se tiver ID da proposição, busca ementa completa na API
    if id_prop:
        info_prop = fetch_proposicao_info(id_prop)
        if info_prop and info_prop.get("ementa"):
            textos.append(info_prop["ementa"])

    texto_norm = normalize_text(" ".join(textos))
    encontradas = set()
    
    for kw_norm, kw_original in palavras_chave_normalizadas:
        if not kw_norm:
            continue
        # Usar regex com word boundary para buscar palavra inteira
        # Isso evita que "arma" case com "farmanguinhos"
        pattern = r'\b' + re.escape(kw_norm) + r'\b'
        if re.search(pattern, texto_norm):
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
        proposicoes_palavras_chave = set()  # Proposições que contêm palavras-chave
        ids_proposicoes_autoria = set()
        ids_proposicoes_relatoria = set()

        for item in pauta:
            # Primeiro, pega o ID da proposição para buscar ementa completa
            id_prop_tmp = get_proposicao_id_from_item(item)
            
            # Busca palavras-chave passando o ID para buscar ementa completa
            kws_item = pauta_item_palavras_chave(item, palavras_chave_norm, id_prop_tmp)
            has_keywords = bool(kws_item)
            relatoria_flag = pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf)

            autoria_flag = False
            if buscar_autoria and ids_autoria_deputada:
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
                # Pegar relator do item
                relator_info = item.get("relator") or {}
                relator_nome = relator_info.get("nome") or ""
                relator_partido = relator_info.get("siglaPartido") or ""
                relator_uf = relator_info.get("siglaUf") or ""
                if relator_nome:
                    relator_str = f"{relator_nome} ({relator_partido}-{relator_uf})"
                else:
                    relator_str = "Sem relator designado"
                
                # Link para tramitação
                link_tram = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_prop}" if id_prop else ""
                
                # Armazenar com formato detalhado incluindo comissão e data
                # formato: matéria|||palavras|||ementa|||link|||relator|||comissao|||nome_comissao|||data
                for org in orgaos:
                    sigla_org_temp = org.get("siglaOrgao") or org.get("sigla") or ""
                    nome_org_temp = org.get("nomeOrgao") or org.get("nome") or ""
                    proposicoes_palavras_chave.add(
                        f"{identificacao}|||{', '.join(kws_item)}|||{ementa_prop}|||{link_tram}|||{relator_str}|||{sigla_org_temp}|||{nome_org_temp}|||{data_str}"
                    )

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
                    "proposicoes_palavras_chave": "; ".join(sorted(proposicoes_palavras_chave)),
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
        tramitacoes = dados_completos.get("tramitacoes", [])
        sigla_tipo = dados_completos.get("sigla", "")
        ementa = dados_completos.get("ementa", "")
        
        # Formatar relator
        relator_txt = ""
        relator_id = ""
        if relator_info and relator_info.get("nome"):
            nome = relator_info.get("nome", "")
            partido = relator_info.get("partido", "")
            uf = relator_info.get("uf", "")
            relator_id = str(relator_info.get("id_deputado", ""))
            if partido or uf:
                relator_txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
            else:
                relator_txt = nome
        
        # Resultado base
        resultado = {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": dados_completos.get("status_dataHora", ""),
            "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
            "relator": relator_txt,
            "relator_id": relator_id,
            "sigla_tipo": sigla_tipo,
            "ementa": ementa,
        }
        
        # Se for RIC, extrair informações adicionais de prazo de resposta
        if sigla_tipo == "RIC":
            prazo_info = parse_prazo_resposta_ric(tramitacoes, situacao)
            resultado.update({
                "ric_data_remessa": prazo_info.get("data_remessa"),
                "ric_inicio_contagem": prazo_info.get("inicio_contagem"),
                "ric_prazo_inicio": prazo_info.get("prazo_inicio"),
                "ric_prazo_fim": prazo_info.get("prazo_fim"),
                "ric_prazo_str": prazo_info.get("prazo_str", ""),  # String formatada para exibição
                "ric_dias_restantes": prazo_info.get("dias_restantes"),
                "ric_fonte_prazo": prazo_info.get("fonte_prazo", ""),
                "ric_status_resposta": prazo_info.get("status_resposta"),
                "ric_data_resposta": prazo_info.get("data_resposta"),
                "ric_respondido": prazo_info.get("respondido", False),
                "ric_ministerio": extrair_ministerio_ric(ementa, tramitacoes),
                "ric_assunto": extrair_assunto_ric(ementa),
            })
        
        return pid, resultado

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
    df["Relator_ID"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("relator_id", ""))
    
    # Link do relator (se tiver id)
    def _link_relator(row):
        relator_id = row.get("Relator_ID", "")
        if relator_id and str(relator_id).strip() not in ('', 'nan', 'None'):
            return camara_link_deputado(relator_id)
        return ""
    df["LinkRelator"] = df.apply(_link_relator, axis=1)

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["Data do status"] = dt.apply(fmt_dt_br)
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month
    df["Parado (dias)"] = df["DataStatus_dt"].apply(days_since)
    
    # Link da tramitação
    df["LinkTramitacao"] = df["id"].astype(str).apply(camara_link_tramitacao)
    
    # Adiciona tema
    df["Tema"] = df["ementa"].apply(categorizar_tema)
    
    # Dados específicos de RIC
    df["RIC_DataRemessa"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_data_remessa"))
    df["RIC_InicioContagem"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_inicio_contagem"))
    df["RIC_PrazoInicio"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_inicio"))
    df["RIC_PrazoFim"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_fim"))
    df["RIC_PrazoStr"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_str", ""))
    df["RIC_DiasRestantes"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_dias_restantes"))
    df["RIC_FontePrazo"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_fonte_prazo", ""))
    df["RIC_StatusResposta"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_status_resposta", ""))
    df["RIC_DataResposta"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_data_resposta"))
    df["RIC_Respondido"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_respondido", False))
    df["RIC_Ministerio"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_ministerio", ""))
    df["RIC_Assunto"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_assunto", ""))

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
    
    # Ordenar por data mais recente primeiro
    df = df.sort_values("DataStatus_dt", ascending=False)
    
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
            if rel_id:
                link_relator = camara_link_deputado(rel_id)
                st.markdown(f"**[{rel_txt}]({link_relator})**")
            else:
                st.markdown(f"**{rel_txt}**")
            
            if alerta_relator:
                st.warning(alerta_relator)
                
    elif precisa_relator:
        st.markdown("**Relator(a):** Não identificado")
    
    c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
    c1.metric("Data do Status", fmt_dt_br(status_dt))
    c2.metric("Última mov.", fmt_dt_br(ultima_dt))
    c3.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")
    
    # SEÇÃO ESPECIAL PARA RICs - PRAZO DE RESPOSTA
    sigla_tipo = status.get("sigla", "")
    if sigla_tipo == "RIC":
        tramitacoes = dados_completos.get("tramitacoes", [])
        prazo_info = parse_prazo_resposta_ric(tramitacoes)
        ministerio = extrair_ministerio_ric(ementa, tramitacoes)
        assunto = extrair_assunto_ric(ementa)
        
        st.markdown("---")
        st.markdown("### 📋 Informações do RIC (Requerimento de Informação)")
        
        col_ric1, col_ric2 = st.columns(2)
        
        with col_ric1:
            if ministerio:
                st.markdown(f"**Ministério/Órgão:** {ministerio}")
            if assunto:
                st.markdown(f"**Assunto/Tema:** {assunto}")
        
        with col_ric2:
            status_resp = prazo_info.get("status_resposta", "Aguardando resposta")
            if status_resp == "Respondido":
                st.success(f"✅ **Status:** {status_resp}")
            else:
                st.warning(f"⏳ **Status:** {status_resp}")
        
        # Dados de prazo de resposta
        if prazo_info.get("data_remessa"):
            st.markdown("#### 📅 Prazo de Resposta")
            
            col_p1, col_p2, col_p3 = st.columns(3)
            
            with col_p1:
                data_remessa = prazo_info.get("data_remessa")
                st.metric("Remessa (1SECM)", data_remessa.strftime("%d/%m/%Y") if data_remessa else "—")
            
            with col_p2:
                inicio = prazo_info.get("inicio_contagem")
                st.metric("Início da contagem", inicio.strftime("%d/%m/%Y") if inicio else "—")
            
            with col_p3:
                prazo_fim = prazo_info.get("prazo_fim")
                st.metric("Prazo final", prazo_fim.strftime("%d/%m/%Y") if prazo_fim else "—")
        
        st.markdown("---")

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

        col_xlsx, col_pdf = st.columns(2)
        with col_xlsx:
            try:
                bytes_out, mime, ext = to_xlsx_bytes(df_tram10, "LinhaDoTempo_10")
                st.download_button(
                    f"⬇️ Baixar XLSX",
                    data=bytes_out,
                    file_name=f"linha_do_tempo_10_{selected_id}.{ext}",
                    mime=mime,
                    key=f"{key_prefix}_download_timeline_xlsx_{selected_id}"
                )
            except Exception as e:
                st.error(f"Erro ao gerar XLSX: {e}")
        with col_pdf:
            try:
                pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tram10, f"Linha do Tempo - ID {selected_id}")
                st.download_button(
                    f"⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"linha_do_tempo_10_{selected_id}.{pdf_ext}",
                    mime=pdf_mime,
                    key=f"{key_prefix}_download_timeline_pdf_{selected_id}"
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")


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
# GRÁFICOS - COM PLOTLY PARA MELHOR VISUALIZAÇÃO
# ============================================================

def render_grafico_barras_situacao(df: pd.DataFrame):
    """Renderiza gráfico de barras horizontal por situação - MATPLOTLIB ESTÁTICO."""
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
    
    fig, ax = plt.subplots(figsize=(10, max(4, len(df_counts) * 0.4)))
    bars = ax.barh(df_counts["Situação"], df_counts["Quantidade"], color='#1f77b4')
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Quantidade")
    ax.set_ylabel("")
    ax.tick_params(axis='y', labelsize=9)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_barras_tema(df: pd.DataFrame):
    """Renderiza gráfico de barras por tema - MATPLOTLIB ESTÁTICO."""
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
    
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#2ca02c')
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Tema"], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_mensal(df: pd.DataFrame):
    """Renderiza gráfico de tendência mensal - MATPLOTLIB ESTÁTICO."""
    if df.empty or "AnoStatus" not in df.columns or "MesStatus" not in df.columns:
        st.info("Sem dados para gráfico mensal.")
        return

    df_valid = df.dropna(subset=["AnoStatus", "MesStatus"]).copy()
    if df_valid.empty:
        return

    df_valid["AnoMes_sort"] = df_valid.apply(
        lambda r: int(r["AnoStatus"]) * 100 + int(r["MesStatus"]), axis=1
    )

    df_mensal = (
        df_valid.groupby("AnoMes_sort", as_index=False)
        .size()
        .rename(columns={"size": "Movimentações"})
        .sort_values("AnoMes_sort")
        .reset_index(drop=True)
    )

    if df_mensal.empty or len(df_mensal) < 2:
        return

    df_mensal["Label"] = df_mensal["AnoMes_sort"].apply(
        lambda ym: f"{int(ym)%100:02d}/{int(ym)//100}"
    )

    st.markdown("##### 📈 Tendência de Movimentações por Mês")
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(range(len(df_mensal)), df_mensal["Movimentações"], marker='o', color='#ff7f0e', linewidth=2, markersize=6)
    
    for i, (x, y) in enumerate(zip(range(len(df_mensal)), df_mensal["Movimentações"])):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=8)
    
    ax.set_xticks(range(len(df_mensal)))
    ax.set_xticklabels(df_mensal["Label"], rotation=45, ha='right', fontsize=8)
    ax.set_xlabel("Mês/Ano")
    ax.set_ylabel("Movimentações")
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_tipo(df: pd.DataFrame):
    """Renderiza gráfico por tipo de proposição - MATPLOTLIB ESTÁTICO."""
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
    
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#1f77b4')
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Tipo"], fontsize=10)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_orgao(df: pd.DataFrame):
    """Renderiza gráfico por órgão atual - MATPLOTLIB ESTÁTICO."""
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
    
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#d62728')
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Órgão"], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ============================================================
# UI
# ============================================================

def mostrar_ultima_atualizacao(chave: str):
    """Mostra a última atualização de uma seção específica."""
    if "ultima_atualizacao" in st.session_state:
        timestamp = st.session_state["ultima_atualizacao"].get(chave)
        if timestamp:
            st.caption(f"🕐 Última atualização: {timestamp.strftime('%d/%m/%Y %H:%M')}")

def registrar_atualizacao(chave: str):
    """Registra o timestamp de atualização de uma seção."""
    if "ultima_atualizacao" not in st.session_state:
        st.session_state["ultima_atualizacao"] = {}
    st.session_state["ultima_atualizacao"][chave] = datetime.datetime.now()

def main():
    st.markdown("""
    <style>
    /* Estabilizar layout - evitar "pulos" ao clicar */
    .main .block-container {
        min-width: 800px;
        max-width: 1200px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Manter tabelas com largura consistente */
    .map-small iframe { height: 320px !important; }
    div[data-testid="stDataFrame"] * {
        white-space: normal !important;
        word-break: break-word !important;
    }
    
    /* Evitar redimensionamento de colunas */
    div[data-testid="column"] {
        min-height: 50px;
    }
    
    /* Botões com tamanho mínimo */
    .stButton > button {
        min-width: 120px;
    }
    
    /* Rolagem lateral nas abas para telas menores */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto;
        overflow-y: hidden;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
        padding-bottom: 5px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        height: 6px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
        background-color: #ccc;
        border-radius: 3px;
    }
    
    .stTabs [data-baseweb="tab"] {
        white-space: nowrap;
        flex-shrink: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ============================================================
    # SISTEMA DE ÚLTIMA ATUALIZAÇÃO
    # ============================================================
    if "ultima_atualizacao" not in st.session_state:
        st.session_state["ultima_atualizacao"] = {
            "pauta": None,
            "proposicoes": None,
            "materias": None,
            "rics": None,
            "comissoes": None
        }

    # ============================================================
    # TÍTULO DO SISTEMA (sem foto - foto fica no card abaixo)
    # ============================================================
    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")
    st.caption("v25 – com Chat IA")

    if "status_click_sel" not in st.session_state:
        st.session_state["status_click_sel"] = None

    # Constantes fixas da deputada (não editáveis)
    nome_deputada = DEPUTADA_NOME_PADRAO
    partido_deputada = DEPUTADA_PARTIDO_PADRAO
    uf_deputada = DEPUTADA_UF_PADRAO
    id_deputada = DEPUTADA_ID_PADRAO

    # ============================================================
    # CARD FIXO DA DEPUTADA (aparece em todas as abas)
    # ============================================================
    with st.container():
        col_dep_foto, col_dep_info, col_dep_acoes = st.columns([1, 4, 1])
        with col_dep_foto:
            try:
                st.image(f"https://www.camara.leg.br/internet/deputado/bandep/{id_deputada}.jpg", width=100)
            except:
                st.markdown("👤")
        with col_dep_info:
            st.markdown(f"**{nome_deputada}**")
            st.markdown(f"**Partido:** {partido_deputada} | **UF:** {uf_deputada}")
            st.markdown(f"[🔗 Perfil na Câmara](https://www.camara.leg.br/deputados/{id_deputada})")
        with col_dep_acoes:
            if st.button("🔄 Atualizar tudo", use_container_width=True, help="Limpa cache e recarrega todos os dados"):
                # Limpar todos os caches
                st.cache_data.clear()
                # Limpar session state de dados
                keys_to_clear = [
                    "df_pauta", "df_comissoes", "df_rics_completo", 
                    "df_autoria_status", "props_autoria_api"
                ]
                for k in keys_to_clear:
                    if k in st.session_state:
                        del st.session_state[k]
                # Resetar timestamps
                st.session_state["ultima_atualizacao"] = {}
                st.success("✅ Cache limpo! Recarregue as abas para atualizar os dados.")
                st.rerun()
    
    with st.expander("📋 Minibiografia", expanded=False):
        st.markdown("""
**Júlia Pedroso Zanatta** é deputada federal por Santa Catarina, filiada ao Partido Liberal (PL). 
Natural de Criciúma (SC), nasceu em 20 de março de 1985 e é formada em **Jornalismo** e **Direito**. 
Antes de ingressar no Congresso Nacional, atuou como jornalista, advogada e assessora política, 
com forte presença na comunicação e no debate público.

Iniciou sua trajetória eleitoral em 2020, quando concorreu à Prefeitura de Criciúma. Em 2022, 
foi eleita deputada federal, assumindo o mandato na Câmara dos Deputados em fevereiro de 2023, 
para a legislatura 2023–2027. No Parlamento, integra a bancada conservadora e liberal, sendo **vice-líder do PL**.

Sua atuação legislativa é marcada pela defesa da **liberdade econômica**, da **redução da carga tributária**, 
da **segurança jurídica**, da **liberdade de expressão** e de pautas conservadoras nos campos social e institucional. 
Júlia Zanatta também se destaca pela postura crítica ao aumento de impostos, ao expansionismo do Estado 
e a políticas que, em sua visão, ampliam a intervenção governamental na economia e na vida dos cidadãos.
        """)
    
    st.markdown("---")

    # ============================================================
    # ABAS REORGANIZADAS (7 abas)
    # ============================================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1️⃣ Apresentação",
        "2️⃣ Autoria & Relatoria na pauta",
        "3️⃣ Palavras-chave na pauta",
        "4️⃣ Comissões estratégicas",
        "5️⃣ Buscar Proposição Específica",
        "6️⃣ Matérias por situação atual",
        "7️⃣ RICs (Requerimentos de Informação)"
    ])

    # ============================================================
    # ABA 1 - APRESENTAÇÃO E GLOSSÁRIO
    # ============================================================
   # ============================================================
# ============================================================
# CÓDIGO CORRIGIDO - DASHBOARD EXECUTIVO (Aba 1)
# ============================================================
# Substitua o conteúdo do "with tab1:" por este código
# ============================================================

    with tab1:
        st.title("📊 Dashboard Executivo")
        
        # ============================================================
        # HEADER SIMPLES (sem foto)
        # ============================================================
        st.markdown(f"### {nome_deputada}")
        st.markdown(f"**Partido:** {partido_deputada} | **UF:** {uf_deputada}")
        st.markdown(f"🕐 **Última atualização:** {get_brasilia_now().strftime('%d/%m/%Y às %H:%M:%S')}")
        
        st.markdown("---")
        
        # ============================================================
        # BUSCAR MÉTRICAS USANDO FUNÇÃO EXISTENTE
        # ============================================================
        with st.spinner("📊 Carregando métricas do dashboard..."):
            try:
                # Usar função que já existe no código
                df_props = fetch_lista_proposicoes_autoria(id_deputada)
                
                if df_props.empty:
                    props_autoria = []
                else:
                    props_autoria = df_props.to_dict('records')
                
            except Exception as e:
                st.error(f"⚠️ Erro ao carregar métricas: {e}")
                props_autoria = []
        
        # ============================================================
        # CARDS DE MÉTRICAS (KPIs)
        # ============================================================
        st.markdown("### 📈 Visão Geral")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Contar por tipo primeiro para usar em todos os cards
        tipos_count = {}
        for p in props_autoria:
            tipo = p.get('siglaTipo', 'Outro')
            if tipo:  # Ignora tipos vazios
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        
        with col1:
            st.metric(
                label="📝 Proposições de Autoria",
                value=len(props_autoria),
                help="Total de proposições de autoria (todas)"
            )
        
        with col2:
            rics = tipos_count.get('RIC', 0)
            st.metric(
                label="📄 RICs",
                value=rics,
                help="Requerimentos de Informação"
            )
        
        with col3:
            pls = tipos_count.get('PL', 0) + tipos_count.get('PLP', 0)
            st.metric(
                label="📋 Projetos de Lei",
                value=pls,
                help="PL + PLP"
            )
        
        with col4:
            pareceres = tipos_count.get('PRL', 0)
            st.metric(
                label="📑 Pareceres",
                value=pareceres,
                help="Pareceres de Relatoria (PRL)"
            )
        
        with col5:
            # Calcular outros e listar tipos incluídos (excluindo RIC, PL, PLP e PRL)
            tipos_outros = {k: v for k, v in tipos_count.items() if k not in ['RIC', 'PL', 'PLP', 'PRL']}
            outros = sum(tipos_outros.values())
            
            # Criar descrição dos tipos incluídos
            if tipos_outros:
                # Ordenar por quantidade (top 5)
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
        
        # Expander com detalhamento de todos os tipos
        with st.expander("📋 Ver todos os tipos de proposição", expanded=False):
            if tipos_count:
                # Criar dataframe para exibir
                df_tipos_detalhe = pd.DataFrame(
                    sorted(tipos_count.items(), key=lambda x: x[1], reverse=True),
                    columns=['Tipo', 'Quantidade']
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
                    st.caption("• **RPD** - Req. regimentais de procedimentos internos (Retirada de Pauta, Adiamento, etc.)")
            else:
                st.info("Nenhum tipo encontrado.")
        
        st.markdown("---")
        
        # ============================================================
        # GRÁFICOS RESUMIDOS
        # ============================================================
        st.markdown("### 📊 Análise Rápida")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Gráfico por tipo de proposição
            if props_autoria and tipos_count:
                df_tipos = pd.DataFrame(list(tipos_count.items()), columns=['Tipo', 'Quantidade'])
                df_tipos = df_tipos.sort_values('Quantidade', ascending=False)
                
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.barh(df_tipos['Tipo'], df_tipos['Quantidade'], color='steelblue')
                ax.set_xlabel('Quantidade')
                ax.set_title('Proposições por Tipo')
                ax.grid(axis='x', alpha=0.3)
                
                # Adicionar valores nas barras
                for i, v in enumerate(df_tipos['Quantidade']):
                    ax.text(v + 0.5, i, str(v), va='center')
                
                st.pyplot(fig)
                plt.close()
        
        with col_graf2:
            # Gráfico por ano (filtra anos válidos)
            if props_autoria:
                anos_count = {}
                for p in props_autoria:
                    ano = p.get('ano', '')
                    # Filtra apenas anos válidos (4 dígitos numéricos)
                    if ano and str(ano).isdigit() and len(str(ano)) == 4:
                        anos_count[str(ano)] = anos_count.get(str(ano), 0) + 1
                
                if anos_count:
                    df_anos = pd.DataFrame(list(anos_count.items()), columns=['Ano', 'Quantidade'])
                    df_anos = df_anos.sort_values('Ano', ascending=False)
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.barh(df_anos['Ano'], df_anos['Quantidade'], color='coral')
                    ax.set_xlabel('Quantidade')
                    ax.set_title('Proposições por Ano')
                    ax.grid(axis='x', alpha=0.3)
                    
                    # Adicionar valores nas barras
                    for i, v in enumerate(df_anos['Quantidade']):
                        ax.text(v + 0.5, i, str(v), va='center')
                    
                    st.pyplot(fig)
                    plt.close()
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
        
        # Mostrar indicação se algum destino foi selecionado
        if st.session_state.get("aba_destino"):
            destinos = {
                "pauta": "2️⃣ Autoria & Relatoria na pauta",
                "buscar": "5️⃣ Buscar Proposição Específica",
                "materias": "6️⃣ Matérias por situação atual",
                "rics": "7️⃣ RICs (Requerimentos)"
            }
            destino = destinos.get(st.session_state["aba_destino"], "")
            if destino:
                st.success(f"👆 Clique na aba **{destino}** acima para acessar")
                # Limpa após mostrar
                st.session_state["aba_destino"] = None
        
        st.markdown("---")
        
        # ============================================================
        # CARD DO TELEGRAM (convite para grupo)
        # ============================================================
        st.markdown("### 📱 Receba Atualizações no Telegram")
        
        col_tg1, col_tg2 = st.columns([3, 1])
        
        with col_tg1:
            st.info("""
            🔔 **Entre no grupo do Monitor Parlamentar no Telegram!**
            
            Receba notificações automáticas sobre:
            - Novas tramitações de proposições da Dep. Júlia Zanatta
            - Movimentações em projetos de lei
            - Atualizações em requerimentos de informação (RICs)
            """)
        
        with col_tg2:
            st.markdown("")  # Espaçador
            st.link_button(
                "📲 Entrar no Grupo",
                url="https://t.me/+LJUCm1ZwxoJkNDkx",
                type="primary",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # ============================================================
        # RELATÓRIO DA SEMANA (PDF consolidado)
        # ============================================================
        st.markdown("### 📄 Relatório da Semana")
        st.caption("Gere um relatório consolidado em PDF com análise estratégica. **A pauta da semana é buscada automaticamente.**")
        
        col_rel1, col_rel2 = st.columns([2, 1])
        
        with col_rel1:
            # Verificar dados disponíveis
            df_rics = st.session_state.get("df_rics_completo", pd.DataFrame())
            
            dados_disponiveis = []
            dados_disponiveis.append("✅ Pauta da semana (busca automática)")
            
            if props_autoria:
                dados_disponiveis.append(f"✅ {len(props_autoria)} proposições de autoria")
            else:
                dados_disponiveis.append("⚠️ Proposições de autoria não carregadas")
            
            if not df_rics.empty:
                dados_disponiveis.append(f"✅ {len(df_rics)} RICs")
            else:
                dados_disponiveis.append("⚠️ RICs (carregue na aba 7)")
            
            st.caption("**Dados disponíveis:**")
            for item in dados_disponiveis:
                st.caption(item)
        
        with col_rel2:
            if st.button("📥 Gerar Relatório PDF", use_container_width=True, type="primary", key="btn_gerar_relatorio"):
                with st.spinner("Gerando relatório... (buscando pauta da semana)"):
                    try:
                        # Gerar o relatório (busca pauta automaticamente)
                        pdf_bytes = gerar_relatorio_semanal(
                            nome_deputada=nome_deputada,
                            partido=partido_deputada,
                            uf=uf_deputada,
                            id_deputada=id_deputada,
                            props_autoria=props_autoria,
                            tipos_count=tipos_count if 'tipos_count' in dir() else {},
                            df_rics=df_rics
                        )
                        
                        # Disponibilizar download
                        st.download_button(
                            "⬇️ Baixar Relatório PDF",
                            data=pdf_bytes,
                            file_name=f"relatorio_semanal_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            key="download_relatorio_semanal"
                        )
                        st.success("✅ Relatório gerado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao gerar relatório: {e}")
        
        st.markdown("---")
        
        # ============================================================
        # GLOSSÁRIO (em expander, opcional)
        # ============================================================
        with st.expander("📚 Glossário e Ajuda do Sistema", expanded=False):
            st.markdown("### 🎯 Funcionalidades por Aba")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
**2️⃣ Autoria & Relatoria na pauta**
- Proposições de **autoria** da deputada que estão na pauta da semana
- Proposições onde a deputada é **relatora**
- Filtrado pelo período selecionado

**3️⃣ Palavras-chave na pauta**
- Busca por **palavras-chave** configuráveis
- Identifica proposições de interesse temático em pauta na semana

**4️⃣ Comissões estratégicas**
- Eventos nas comissões estratégicas
- CDC, CCOM, CE, CREDN, CCJC
                """)
            
            with col2:
                st.markdown("""
**5️⃣ Buscar Proposição Específica**
- Busca livre por qualquer proposição
- Filtros por ano e tipo
- Detalhes completos com linha do tempo

**6️⃣ Matérias por situação atual**
- Visão geral com filtros avançados
- Gráficos analíticos

**7️⃣ RICs**
- Requerimentos de Informação
- Prazo de 30 dias para resposta
- Indicadores de urgência
                """)
            
            st.markdown("---")
            st.markdown("### 📋 Tipos de Proposições")
            
            st.markdown("""
| Sigla | Nome | Descrição |
|-------|------|-----------|
| **PL** | Projeto de Lei | Lei ordinária |
| **PLP** | Projeto de Lei Complementar | Complementa a Constituição |
| **PEC** | Proposta de Emenda | Altera a Constituição |
| **RIC** | Requerimento de Informação | Prazo: 30 dias |
| **PDL** | Projeto de Decreto Legislativo | Competência do Congresso |
            """)
        
        st.markdown("---")
        st.caption("📊 Dados: API Câmara dos Deputados | Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta")

    # ============================================================
    # ABA 2 - AUTORIA & RELATORIA NA PAUTA - OTIMIZADA
    # ============================================================
    with tab2:
        st.subheader("Autoria & Relatoria na pauta")
        
        st.info("💡 **Dica:** Selecione o período da semana e clique em **Carregar pauta** para ver as proposições de sua autoria ou relatoria que estão na pauta de votações.")
        
        # Período de busca e botão de rodar
        col_periodo, col_btn = st.columns([3, 1])
        with col_periodo:
            hoje = datetime.date.today()
            date_range_tab2 = st.date_input(
                "📅 Período de busca", 
                value=st.session_state.get("date_range_tab2", (hoje, hoje + datetime.timedelta(days=7))),
                format="DD/MM/YYYY",
                key="date_range_tab2"
            )
            if isinstance(date_range_tab2, tuple) and len(date_range_tab2) == 2:
                dt_inicio_t2, dt_fim_t2 = date_range_tab2
            else:
                dt_inicio_t2 = hoje
                dt_fim_t2 = hoje + datetime.timedelta(days=7)
        
        with col_btn:
            st.write("")  # Espaçador
            run_scan_tab2 = st.button("▶️ Carregar pauta", type="primary", key="run_scan_tab2")
        
        if run_scan_tab2:
            with st.spinner("Carregando eventos..."):
                eventos = fetch_eventos(dt_inicio_t2, dt_fim_t2)
            with st.spinner("Carregando autorias..."):
                ids_autoria = fetch_ids_autoria_deputada(int(id_deputada))
            with st.spinner("Escaneando pautas..."):
                df = escanear_eventos(
                    eventos, nome_deputada, partido_deputada, uf_deputada,
                    PALAVRAS_CHAVE_PADRAO, COMISSOES_ESTRATEGICAS_PADRAO,
                    apenas_reuniao_deliberativa=False, buscar_autoria=True,
                    ids_autoria_deputada=ids_autoria,
                )
            st.session_state["df_scan_tab2"] = df
            st.session_state["dt_range_tab2_saved"] = (dt_inicio_t2, dt_fim_t2)
            registrar_atualizacao("pauta")
            st.success(f"✅ {len(df)} registros carregados")
            st.rerun()
        
        # Mostrar última atualização
        mostrar_ultima_atualizacao("pauta")
        
        df = st.session_state.get("df_scan_tab2", pd.DataFrame())
        dt_range_saved = st.session_state.get("dt_range_tab2_saved", (dt_inicio_t2, dt_fim_t2))
        dt_inicio, dt_fim = dt_range_saved
        
        if df.empty:
            st.info("👆 Selecione o período e clique em **Carregar pauta** para começar.")
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

                col_x1, col_p1 = st.columns(2)
                with col_x1:
                    data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=data_bytes,
                        file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                        mime=mime,
                    )
                with col_p1:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_autoria_relatoria(view)
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                        mime=pdf_mime,
                    )
                
                st.markdown("---")
                st.markdown("### 📋 Ver detalhes de proposição de autoria na pauta")
                
                # OTIMIZADO: Extrai IDs diretamente da coluna ids_proposicoes_autoria (já tem os IDs)
                ids_autoria_pauta = set()
                for _, row in df_a.iterrows():
                    val = row.get("ids_proposicoes_autoria", "")
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != "nan":
                            # IDs já estão separados por ;
                            for pid in val_str.split(";"):
                                pid = pid.strip()
                                if pid and pid.isdigit():
                                    ids_autoria_pauta.add(pid)
                
                if not ids_autoria_pauta:
                    st.info("Nenhuma proposição de autoria identificada na pauta.")
                else:
                    st.markdown(f"**{len(ids_autoria_pauta)} proposição(ões) de autoria encontrada(s)**")
                    
                    # Carrega info apenas quando usuário selecionar (lazy loading)
                    opcoes_props = {}
                    for pid in sorted(ids_autoria_pauta):
                        info = fetch_proposicao_info(pid)
                        label = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or f"ID {pid}"
                        opcoes_props[label] = pid
                    
                    if opcoes_props:
                        prop_selecionada = st.selectbox(
                            "Selecione uma proposição para ver detalhes:",
                            options=list(opcoes_props.keys()),
                            key="select_prop_autoria_tab2"
                        )
                        
                        if prop_selecionada:
                            selected_id_tab2 = opcoes_props[prop_selecionada]
                            exibir_detalhes_proposicao(selected_id_tab2, key_prefix="tab2")
        
        # Chat IA da aba 2
        st.markdown("---")
        df_chat_tab2 = st.session_state.get("df_scan_tab2", pd.DataFrame())
        render_chat_ia("tab2", df_chat_tab2, filtros={"periodo": st.session_state.get("dt_range_tab2_saved", None)})

    # ============================================================
    # ABA 3 - PALAVRAS-CHAVE
    # ============================================================
    with tab3:
        st.subheader("Palavras-chave na pauta")
        
        st.info("💡 **Dica:** Configure palavras-chave de interesse (ex: vacina, aborto, armas) para monitorar proposições temáticas na pauta da semana.")
        
        # Controles: Data + Palavras-chave + Botão
        col_data_t3, col_kw_t3 = st.columns([1, 1])
        
        with col_data_t3:
            hoje = datetime.date.today()
            date_range_tab3 = st.date_input(
                "📅 Período de busca", 
                value=st.session_state.get("date_range_tab3", (hoje, hoje + datetime.timedelta(days=7))),
                format="DD/MM/YYYY",
                key="date_range_tab3"
            )
            if isinstance(date_range_tab3, tuple) and len(date_range_tab3) == 2:
                dt_inicio_t3, dt_fim_t3 = date_range_tab3
            else:
                dt_inicio_t3 = hoje
                dt_fim_t3 = hoje + datetime.timedelta(days=7)
        
        with col_kw_t3:
            palavras_str_t3 = st.text_area(
                "🔑 Palavras-chave (uma por linha)", 
                value=st.session_state.get("palavras_t3", "\n".join(PALAVRAS_CHAVE_PADRAO)),
                height=100,
                key="palavras_input_t3"
            )
            palavras_chave_t3 = [p.strip() for p in palavras_str_t3.splitlines() if p.strip()]
            st.session_state["palavras_t3"] = palavras_str_t3
        
        run_scan_tab3 = st.button("▶️ Carregar pauta com palavras-chave", type="primary", key="run_scan_tab3")
        
        if run_scan_tab3:
            with st.spinner("Carregando eventos..."):
                eventos = fetch_eventos(dt_inicio_t3, dt_fim_t3)
            with st.spinner("Carregando autorias..."):
                ids_autoria = fetch_ids_autoria_deputada(int(id_deputada))
            with st.spinner("Escaneando pautas..."):
                df = escanear_eventos(
                    eventos, nome_deputada, partido_deputada, uf_deputada,
                    palavras_chave_t3, COMISSOES_ESTRATEGICAS_PADRAO,
                    apenas_reuniao_deliberativa=False, buscar_autoria=True,
                    ids_autoria_deputada=ids_autoria,
                )
            st.session_state["df_scan_tab3"] = df
            st.session_state["dt_range_tab3_saved"] = (dt_inicio_t3, dt_fim_t3)
            registrar_atualizacao("palavras_chave")
            st.success(f"✅ {len(df)} registros carregados")
            st.rerun()
        
        # Mostrar última atualização
        mostrar_ultima_atualizacao("palavras_chave")
        
        df = st.session_state.get("df_scan_tab3", pd.DataFrame())
        dt_range_saved = st.session_state.get("dt_range_tab3_saved", (dt_inicio_t3, dt_fim_t3))
        dt_inicio, dt_fim = dt_range_saved
        
        if df.empty:
            st.info("👆 Selecione o período, configure as palavras-chave e clique em **Carregar pauta**.")
        else:
            df_kw = df[df["tem_palavras_chave"]].copy()
            if df_kw.empty:
                st.info("Sem palavras-chave no período.")
            else:
                # Extrair proposições individuais para exibição focada na matéria
                lista_proposicoes = []
                
                for _, row in df_kw.iterrows():
                    props_str = row.get("proposicoes_palavras_chave", "")
                    if not props_str or pd.isna(props_str):
                        continue
                    
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
                        
                        # Formatar data para DD/MM/YYYY
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
                
                # Criar DataFrame e remover duplicatas
                df_props = pd.DataFrame(lista_proposicoes)
                
                if df_props.empty:
                    st.info("Sem matérias com palavras-chave encontradas.")
                else:
                    df_props = df_props.drop_duplicates(subset=["Matéria", "Comissão"])
                    df_props = df_props.sort_values(["Data", "Comissão", "Matéria"])
                    
                    # Mostrar quantidade
                    st.success(f"🔍 **{len(df_props)} matérias** com palavras-chave encontradas em **{df_props['Comissão'].nunique()} comissões**!")
                    
                    # Exibir tabela focada nas proposições
                    st.dataframe(
                        df_props,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Link", display_text="abrir"),
                            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                        }
                    )

                    col_x2, col_p2 = st.columns(2)
                    with col_x2:
                        data_bytes, mime, ext = to_xlsx_bytes(df_props, "PalavrasChave_Pauta")
                        st.download_button(
                            f"⬇️ XLSX",
                            data=data_bytes,
                            file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{ext}",
                            mime=mime,
                            key="download_kw_xlsx"
                        )
                    with col_p2:
                        # Usar df_kw para PDF (tem todas as colunas necessárias)
                        pdf_bytes, pdf_mime, pdf_ext = to_pdf_palavras_chave(df_kw)
                        st.download_button(
                            f"⬇️ PDF",
                            data=pdf_bytes,
                            file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                            mime=pdf_mime,
                            key="download_kw_pdf"
                        )
        
        # Chat IA da aba 3
        st.markdown("---")
        df_chat_tab3 = st.session_state.get("df_scan_tab3", pd.DataFrame())
        render_chat_ia("tab3", df_chat_tab3, filtros={"palavras_chave": st.session_state.get("palavras_t3", "")})

    # ============================================================
    # ABA 4 - COMISSÕES ESTRATÉGICAS
    # ============================================================
    with tab4:
        st.subheader("Comissões estratégicas")
        
        st.info("💡 **Dica:** Acompanhe eventos nas comissões em que a deputada é membro. Configure as siglas das comissões de interesse (ex: CDC, CCJC, CREDN).")
        
        # Controles: Data + Comissões + Botão
        col_data_t4, col_com_t4 = st.columns([1, 1])
        
        with col_data_t4:
            hoje = datetime.date.today()
            date_range_tab4 = st.date_input(
                "📅 Período de busca", 
                value=st.session_state.get("date_range_tab4", (hoje, hoje + datetime.timedelta(days=7))),
                format="DD/MM/YYYY",
                key="date_range_tab4"
            )
            if isinstance(date_range_tab4, tuple) and len(date_range_tab4) == 2:
                dt_inicio_t4, dt_fim_t4 = date_range_tab4
            else:
                dt_inicio_t4 = hoje
                dt_fim_t4 = hoje + datetime.timedelta(days=7)
        
        with col_com_t4:
            comissoes_str_t4 = st.text_input(
                "🏛️ Comissões estratégicas (siglas separadas por vírgula)", 
                value=st.session_state.get("comissoes_t4", ", ".join(COMISSOES_ESTRATEGICAS_PADRAO)),
                key="comissoes_input_t4"
            )
            comissoes_t4 = [c.strip().upper() for c in comissoes_str_t4.split(",") if c.strip()]
            st.session_state["comissoes_t4"] = comissoes_str_t4
        
        run_scan_tab4 = st.button("▶️ Carregar pauta das comissões", type="primary", key="run_scan_tab4")
        
        if run_scan_tab4:
            with st.spinner("Carregando eventos..."):
                eventos = fetch_eventos(dt_inicio_t4, dt_fim_t4)
            with st.spinner("Carregando autorias..."):
                ids_autoria = fetch_ids_autoria_deputada(int(id_deputada))
            with st.spinner("Escaneando pautas..."):
                df = escanear_eventos(
                    eventos, nome_deputada, partido_deputada, uf_deputada,
                    PALAVRAS_CHAVE_PADRAO, comissoes_t4,
                    apenas_reuniao_deliberativa=False, buscar_autoria=True,
                    ids_autoria_deputada=ids_autoria,
                )
            st.session_state["df_scan_tab4"] = df
            st.session_state["dt_range_tab4_saved"] = (dt_inicio_t4, dt_fim_t4)
            registrar_atualizacao("comissoes")
            st.success(f"✅ {len(df)} registros carregados")
            st.rerun()
        
        # Mostrar última atualização
        mostrar_ultima_atualizacao("comissoes")
        
        df = st.session_state.get("df_scan_tab4", pd.DataFrame())
        dt_range_saved = st.session_state.get("dt_range_tab4_saved", (dt_inicio_t4, dt_fim_t4))
        dt_inicio, dt_fim = dt_range_saved
        
        if df.empty:
            st.info("👆 Selecione o período, configure as comissões e clique em **Carregar pauta**.")
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

                col_x3, col_p3 = st.columns(2)
                with col_x3:
                    data_bytes, mime, ext = to_xlsx_bytes(view, "ComissoesEstrategicas_Pauta")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=data_bytes,
                        file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{ext}",
                        mime=mime,
                        key="download_com_xlsx"
                    )
                with col_p3:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_comissoes_estrategicas(view)
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                        mime=pdf_mime,
                        key="download_com_pdf"
                    )
        
        # Chat IA da aba 4
        st.markdown("---")
        df_chat_tab4 = st.session_state.get("df_scan_tab4", pd.DataFrame())
        render_chat_ia("tab4", df_chat_tab4, filtros={"comissoes": st.session_state.get("comissoes_t4", "")})

    # ============================================================
    # ABA 5 - BUSCAR PROPOSIÇÃO ESPECÍFICA (LIMPA)
    # ============================================================
    with tab5:
        st.markdown("### 🔍 Buscar Proposição Específica")
        
        st.info("💡 **Dica:** Use os filtros de ano e tipo para encontrar proposições específicas. Clique em uma proposição na tabela para ver detalhes completos, tramitação e estratégia.")
        
        st.caption("Busque proposições de autoria da deputada e veja detalhes completos")

        # Botão de limpar cache
        col_cache, col_info = st.columns([1, 3])
        with col_cache:
            if st.button("🧹 Limpar cache", key="limpar_cache_tab5"):
                fetch_proposicao_completa.clear()
                fetch_lista_proposicoes_autoria_geral.clear()
                fetch_rics_por_autor.clear()
                fetch_lista_proposicoes_autoria.clear()
                build_status_map.clear()
                st.session_state.pop("df_status_last", None)
                st.success("✅ Cache limpo!")

        # Carrega proposições
        with st.spinner("Carregando proposições de autoria..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
        else:
            df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

            # Filtros básicos
            st.markdown("#### 🗂️ Filtros de Proposições")
            col_ano, col_tipo = st.columns([1, 1])
            with col_ano:
                anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
                anos_sel = st.multiselect("Ano", options=anos, default=anos[:3] if len(anos) >= 3 else anos, key="anos_tab5")
            with col_tipo:
                tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
                tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos, key="tipos_tab5")

            df_base = df_aut.copy()
            if anos_sel:
                df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
            if tipos_sel:
                df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()

            st.markdown("---")

            # Campo de busca
            q = st.text_input(
                "Filtrar proposições",
                value="",
                placeholder="Ex.: PL 2030/2025 | 'pix' | 'conanda' | 'oab'",
                help="Busque por sigla/número/ano ou palavras na ementa. A busca textual procura em TODAS as proposições, ignorando filtros de ano.",
                key="busca_tab5"
            )

            # Se há busca textual, buscar em TODAS as proposições (ignora filtro de ano)
            # Isso garante que o Chat IA também tenha acesso a todas
            if q.strip():
                qn = normalize_text(q)
                df_busca_completa = df_aut.copy()  # Usar df_aut completo, não df_base filtrado
                df_busca_completa["_search"] = (df_busca_completa["Proposicao"].fillna("").astype(str) + " " + df_busca_completa["ementa"].fillna("").astype(str)).apply(normalize_text)
                df_rast = df_busca_completa[df_busca_completa["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")
                st.caption(f"🔍 Busca textual em **todas** as {len(df_aut)} proposições")
            else:
                df_rast = df_base.copy()

            df_rast_lim = df_rast.head(400).copy()
            
            with st.spinner("Carregando status das proposições..."):
                ids_r = df_rast_lim["id"].astype(str).tolist()
                status_map_r = build_status_map(ids_r)
                df_rast_enriched = enrich_with_status(df_rast_lim, status_map_r)

            df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)

            st.caption(f"Resultados: {len(df_rast_enriched)} proposições")

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
            
            # IMPORTANTE: Salvar o DataFrame que VAI SER EXIBIDO para o Chat IA
            # Isso garante que o chat recebe exatamente os mesmos dados da tabela
            st.session_state["df_chat_tab5"] = df_tbl.copy()
            st.session_state["filtro_busca_tab5"] = q  # Salvar também o filtro usado
            
            # Também salvar TODAS as proposições (sem filtro) para o chat poder buscar
            st.session_state["df_todas_proposicoes_tab5"] = df_aut.copy()
            
            sel = st.dataframe(
                df_tbl[show_cols_r],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Alerta": st.column_config.TextColumn("", width="small", help="Urgência"),
                    "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                    "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                },
                key="df_busca_tab5"
            )
            
            st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")
            
            # Exportação
            col_x4, col_p4 = st.columns(2)
            with col_x4:
                try:
                    bytes_rast, mime_rast, ext_rast = to_xlsx_bytes(df_tbl[show_cols_r], "Busca_Especifica")
                    st.download_button(
                        f"⬇️ XLSX",
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
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"busca_especifica_proposicoes.{pdf_ext}",
                        mime=pdf_mime,
                        key="export_busca_pdf_tab5"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

            # Detalhes da proposição selecionada
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
                st.info("Clique em uma proposição acima para ver detalhes completos.")
            else:
                exibir_detalhes_proposicao(selected_id, key_prefix="tab5")
        
        # Chat IA da aba 5
        st.markdown("---")
        # Se há filtro de busca, usar o resultado filtrado
        # Se não há filtro, usar TODAS as proposições para o chat poder responder sobre qualquer uma
        filtro_busca = st.session_state.get("filtro_busca_tab5", "")
        if filtro_busca:
            df_para_chat = st.session_state.get("df_chat_tab5", pd.DataFrame())
        else:
            # Usar todas as proposições para o chat poder responder perguntas genéricas
            df_para_chat = st.session_state.get("df_todas_proposicoes_tab5", st.session_state.get("df_chat_tab5", pd.DataFrame()))
        
        # Garantir que selected_id existe
        sel_id_tab5 = selected_id if 'selected_id' in dir() and selected_id else None
        render_chat_ia("tab5", df_para_chat, filtros={"busca": filtro_busca} if filtro_busca else None, selecionado={"id": sel_id_tab5} if sel_id_tab5 else None)

    # ============================================================
    # ABA 6 - MATÉRIAS POR SITUAÇÃO ATUAL (separada)
    # ============================================================
    with tab6:
        st.markdown("### 📊 Matérias por situação atual")
        
        st.info("💡 **Dica:** Visualize a carteira completa de proposições por situação de tramitação. Use os filtros para segmentar por ano, tipo, órgão e tema. Clique em uma proposição para ver detalhes.")
        
        st.caption("Análise da carteira de proposições por status de tramitação")

        with st.spinner("Carregando proposições de autoria..."):
            df_aut6 = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut6.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
        else:
            df_aut6 = df_aut6[df_aut6["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

            st.markdown("#### 🗂️ Filtros de Proposições")
            
            col2, col3 = st.columns([1.1, 1.1])
            with col2:
                anos6 = sorted([a for a in df_aut6["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
                anos_sel6 = st.multiselect("Ano (da proposição)", options=anos6, default=anos6[:3] if len(anos6) >= 3 else anos6, key="anos_tab6")
            with col3:
                tipos6 = sorted([t for t in df_aut6["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
                tipos_sel6 = st.multiselect("Tipo", options=tipos6, default=tipos6, key="tipos_tab6")

            df_base6 = df_aut6.copy()
            if anos_sel6:
                df_base6 = df_base6[df_base6["ano"].isin(anos_sel6)].copy()
            if tipos_sel6:
                df_base6 = df_base6[df_base6["siglaTipo"].isin(tipos_sel6)].copy()

            st.markdown("---")

            cS1, cS2, cS3, cS4 = st.columns([1.2, 1.2, 1.6, 1.0])
           
            with cS2:
                max_status = st.number_input(
                    "Limite (performance)",
                    min_value=20,
                    max_value=600,
                    value=min(200, len(df_base6)) if len(df_base6) else 20,
                    step=20,
                    key="max_status_tab6"
                )
            with cS3:
                st.caption("Aplique filtros acima (Ano/Tipo) e depois carregue o status.")
            with cS4:
                if st.button("✖ Limpar filtro por clique", key="limpar_click_tab6"):
                    st.session_state["status_click_sel"] = None

            df_status_view = st.session_state.get("df_status_last", pd.DataFrame()).copy()

            dynamic_status = []
            if not df_status_view.empty and "Situação atual" in df_status_view.columns:
                dynamic_status = [s for s in df_status_view["Situação atual"].dropna().unique().tolist() if str(s).strip()]
            status_opts = merge_status_options(dynamic_status)

            # Filtros Multi-nível
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
            
            # Segunda linha de filtros multi-nível
            f5, f6, f7 = st.columns([1.2, 1.2, 1.6])
            
            with f5:
                tema_sel = st.multiselect("Tema", options=tema_opts, default=[], key="tema_sel_tab6")
            
            with f6:
                relator_sel = st.multiselect("Relator(a)", options=relator_opts, default=[], key="relator_sel_tab5")
            
            with f7:
                palavra_filtro = st.text_input(
                    "Palavra-chave na ementa",
                    placeholder="Digite para filtrar...",
                    help="Filtra proposições que contenham esta palavra na ementa",
                    key="palavra_filtro_tab5"
                )

            bt_status = st.button("Carregar/Atualizar status", type="primary", key="carregar_status_tab5")

            if bt_status:
                with st.spinner("Buscando status..."):
                    ids_list = df_base6["id"].astype(str).head(int(max_status)).tolist()
                    status_map = build_status_map(ids_list)
                    df_status_view = enrich_with_status(df_base6.head(int(max_status)), status_map)
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

                # Garantir coluna de dias parado para cálculos
                if "Parado (dias)" in df_fil.columns and "Parado há (dias)" not in df_fil.columns:
                    df_fil["Parado há (dias)"] = df_fil["Parado (dias)"]
                
                # Salvar para o Chat IA
                st.session_state["df_chat_tab6"] = df_fil.copy()

                st.markdown("---")
                
                # ============================================================
                # VISÃO EXECUTIVA - RESUMO, ATENÇÃO, PRIORIDADES
                # ============================================================
                with st.expander("🎯 Visão Executiva (Deputada / Chefia / Assessoria)", expanded=True):
                    render_resumo_executivo(df_fil)
                    render_atencao_deputada(df_fil)
                    render_prioridades_gabinete(df_fil)
                
                # ============================================================
                # GRÁFICOS - ORDENADOS DECRESCENTE
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
                    "Data do status": "Última tramitação",
                })
                
                # Criar coluna com link do relator se disponível
                if "LinkRelator" in df_tbl_status.columns:
                    def _relator_com_link(row):
                        relator = row.get("Relator(a)", "—")
                        link = row.get("LinkRelator", "")
                        if link and str(link).startswith("http"):
                            return f"[{relator}]({link})"
                        return relator
                    # Mantemos Relator(a) como texto, o link estará em LinkRelator

                show_cols = [
                    "Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)", "Relator(a)",
                    "Última tramitação", "Sinal", "Parado há", "Tema", "id", "LinkTramitacao", "LinkRelator", "Ementa"
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
                    st.markdown("**Lista filtrada (mais recente primeiro)**")
                    
                    # Ordenar por data mais recente primeiro
                    if "DataStatus_dt" in df_tbl_status.columns:
                        df_tbl_status = df_tbl_status.sort_values("DataStatus_dt", ascending=False)
                    
                    st.dataframe(
                        df_tbl_status[show_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "LinkTramitacao": st.column_config.LinkColumn("Link Tramitação", display_text="abrir"),
                            "LinkRelator": st.column_config.LinkColumn("Link Relator", display_text="ver"),
                            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                            "Relator(a)": st.column_config.TextColumn("Relator(a)", width="medium"),
                            "Última tramitação": st.column_config.TextColumn("Última tramitação", width="small"),
                        },
                    )
                
                # Seção especial para RICs se houver
                df_rics = df_tbl_status[df_tbl_status["Tipo"] == "RIC"].copy() if "Tipo" in df_tbl_status.columns else pd.DataFrame()
                if not df_rics.empty and "RIC_StatusResposta" in df_rics.columns:
                    with st.expander("📋 Detalhes de RICs (Requerimentos de Informação)", expanded=False):
                        st.markdown("**Status dos RICs**")
                        
                        rics_cols = ["Proposição", "Ementa", "RIC_Ministerio", "RIC_StatusResposta", 
                                    "RIC_PrazoFim", "RIC_DiasRestantes", "Última tramitação", "LinkTramitacao"]
                        rics_cols = [c for c in rics_cols if c in df_rics.columns]
                        
                        df_rics_view = df_rics[rics_cols].copy()
                        df_rics_view = df_rics_view.rename(columns={
                            "RIC_Ministerio": "Ministério",
                            "RIC_StatusResposta": "Status Resposta",
                            "RIC_PrazoFim": "Prazo Final",
                            "RIC_DiasRestantes": "Dias Restantes"
                        })
                        
                        st.dataframe(
                            df_rics_view,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                            }
                        )

                col_x5, col_p5 = st.columns(2)
                with col_x5:
                    try:
                        bytes_out, mime, ext = to_xlsx_bytes(df_tbl_status[show_cols], "Materias_Situacao")
                        st.download_button(
                            f"⬇️ XLSX",
                            data=bytes_out,
                            file_name=f"materias_por_situacao_atual.{ext}",
                            mime=mime,
                            key="download_materias_xlsx_tab6"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar XLSX: {e}")
                with col_p5:
                    try:
                        pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tbl_status[show_cols], "Matérias por Situação")
                        st.download_button(
                            f"⬇️ PDF",
                            data=pdf_bytes,
                            file_name=f"materias_por_situacao_atual.{pdf_ext}",
                            mime=pdf_mime,
                            key="download_materias_pdf_tab6"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
        
        # Chat IA da aba 6
        st.markdown("---")
        df_chat_tab6 = st.session_state.get("df_chat_tab6", pd.DataFrame())
        render_chat_ia("tab6", df_chat_tab6)

    # ============================================================
    # ABA 7 - RICs (REQUERIMENTOS DE INFORMAÇÃO)
    # ============================================================
    with tab7:
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
        
        col_load_ric, col_info_ric = st.columns([1, 2])
        
        with col_load_ric:
            if st.button("🔄 Carregar/Atualizar RICs", key="btn_load_rics", type="primary"):
                with st.spinner("Buscando RICs da Deputada..."):
                    # Buscar RICs
                    df_rics_base = fetch_rics_por_autor(id_deputada)
                    
                    if df_rics_base.empty:
                        st.warning("Nenhum RIC encontrado.")
                        st.session_state["df_rics_completo"] = pd.DataFrame()
                    else:
                        st.info(f"Encontrados {len(df_rics_base)} RICs. Carregando detalhes...")
                        
                        # Buscar status completo de cada RIC
                        ids_rics = df_rics_base["id"].astype(str).tolist()
                        status_map_rics = build_status_map(ids_rics)
                        
                        # Enriquecer com status
                        df_rics_enriquecido = enrich_with_status(df_rics_base, status_map_rics)
                        
                        st.session_state["df_rics_completo"] = df_rics_enriquecido
                        registrar_atualizacao("rics")
                        st.success(f"✅ {len(df_rics_enriquecido)} RICs carregados com sucesso!")
        
        with col_info_ric:
            st.caption("""
            💡 **Dica:** Clique em "Carregar/Atualizar RICs" para buscar todos os Requerimentos de Informação 
            da Deputada e extrair automaticamente os prazos de resposta das tramitações.
            """)
        
        # Mostrar última atualização
        mostrar_ultima_atualizacao("rics")
        
        df_rics = st.session_state.get("df_rics_completo", pd.DataFrame())
        
        if not df_rics.empty:
            # Mostrar distribuição por ano para debug
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
                    # Filtro por ano - apenas anos válidos (4 dígitos)
                    todos_anos = df_rics["ano"].dropna().unique().tolist()
                    anos_validos = [str(a) for a in todos_anos if str(a).strip().isdigit() and len(str(a).strip()) == 4]
                    anos_invalidos = [a for a in todos_anos if str(a).strip() not in anos_validos]
                    
                    anos_ric = sorted(anos_validos, reverse=True)
                    
                    # Contar RICs sem ano válido
                    rics_sem_ano = len(df_rics[~df_rics["ano"].isin(anos_validos)])
                    
                    # Default: todos os anos disponíveis
                    anos_sel_ric = st.multiselect("Ano", options=anos_ric, default=anos_ric, key="anos_ric")
                    
                    if rics_sem_ano > 0:
                        st.caption(f"⚠️ {rics_sem_ano} RICs sem ano válido")
                
                with col_f2:
                    # Filtro por status de resposta - incluindo novos status
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
                def _check_dias(x, cond):
                    if x is None or pd.isna(x):
                        return False
                    try:
                        return cond(int(x))
                    except:
                        return False
                
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
            
            # Total geral vs filtrado
            total_geral = len(df_rics)
            total_filtrado = len(df_rics_fil)
            
            # Mostrar indicação se há filtro ativo
            if total_filtrado < total_geral:
                st.caption(f"📌 Exibindo **{total_filtrado}** de **{total_geral}** RICs (filtros ativos)")
            
            col_m1, col_m2, col_m3, col_m4, col_m5, col_m6, col_m7 = st.columns(7)
            
            total_rics = total_filtrado
            em_tramitacao = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Em tramitação na Câmara"])
            aguardando = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Aguardando resposta"])
            fora_prazo = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Fora do prazo"])
            # Separar respondidos no prazo e fora do prazo para a soma bater
            respondidos_ok = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Respondido"])
            respondidos_fora = len(df_rics_fil[df_rics_fil["RIC_StatusResposta"] == "Respondido fora do prazo"])
            respondidos_total = respondidos_ok + respondidos_fora
            
            # Calcular urgentes (vencendo em até 5 dias, excluindo respondidos)
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
                # Mostrar total com indicação se filtrado
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
            
            # Mostrar validação da soma
            soma = em_tramitacao + aguardando + fora_prazo + respondidos_ok + respondidos_fora
            if soma != total_rics:
                st.warning(f"⚠️ Soma das categorias ({soma}) difere do total ({total_rics}). Pode haver status não mapeado.")
            
            st.markdown("---")
            
            # ============================================================
            # ALERTAS DE PRAZO
            # ============================================================
            # Filtrar apenas os que estão fora do prazo (não respondidos)
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
            
            # Normalizar ministério para nome canônico
            df_rics_view["Ministério"] = df_rics_view["RIC_Ministerio"].apply(normalize_ministerio)
            
            # Formatar datas de prazo usando RIC_PrazoStr ou fallback
            def fmt_prazo(row):
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
            
            df_rics_view["Prazo"] = df_rics_view.apply(fmt_prazo, axis=1)
            
            # Formatar data da última tramitação
            if "Data do status" in df_rics_view.columns:
                df_rics_view = df_rics_view.rename(columns={"Data do status": "Última tramitação"})
            
            # Renomear colunas para exibição
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
                    "id": None,  # Ocultar coluna id
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
                # PDF com blocos por status
                pdf_bytes, pdf_mime, pdf_ext = to_pdf_rics_por_status(df_rics_view, "RICs - Requerimentos de Informação")
                st.download_button(
                    "⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"rics_deputada.{pdf_ext}",
                    mime=pdf_mime,
                    key="download_rics_pdf"
                )
            
            # ============================================================
            # DETALHES DO RIC SELECIONADO NA TABELA
            # ============================================================
            st.markdown("---")
            st.markdown("### 🔍 Detalhes do RIC Selecionado")
            
            # Obter seleção da tabela
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
                exibir_detalhes_proposicao(selected_ric_id, key_prefix="ric_detalhe")
        
        else:
            st.info("👆 Clique em **Carregar/Atualizar RICs** para começar.")
        
        # Chat IA da aba 7 (RICs) - com modo especializado
        st.markdown("---")
        st.markdown("### 💬 Chat IA - Análise de RICs")
        df_chat_tab7 = st.session_state.get("df_rics_completo", pd.DataFrame())
        render_chat_ia("tab7", df_chat_tab7, filtros=st.session_state.get("filtros_rics", {}), selecionado={"id": selected_ric_id} if 'selected_ric_id' in dir() and selected_ric_id else None)
        
        st.markdown("---")
        st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")

    st.markdown("---")


if __name__ == "__main__":
    main()