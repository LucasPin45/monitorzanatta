# monitor_sistema_jz.py - v50 FASE DE INTEGRAÇÃO
#
# ALTERAÇÕES v50 - Cleanup & Extração de Services (08/02/2026):
#   - Todas as 9 abas extraídas para modules/tabs/tab{1-9}_*.py
#   - Removidas 68 funções mortas (_legacy_*, PDFs, gráficos, análises)
#   - Removidas constantes duplicadas (MINISTERIOS_CANONICOS, STATUS_PREDEFINIDOS, MESES_PT)
#   - 11 funções Senado extraídas → core/services/senado_integration.py
#   - 6 funções + 3 constantes Apensados extraídas → core/services/apensados.py
#   - 8 funções Notificação extraídas → core/services/notificacao.py
#   - 13 funções Proposição/API extraídas → core/services/proposicao.py
#   - Abas 8/9 reordenadas em sequência no main()
#   - Re-exports de core/utils para compatibilidade com data_provider
#   - Monólito reduzido de 8.874 → 1.681 linhas (-81%)
#
# ALTERAÇÕES v41 - Dividir para Conquistar:
#
# 🔧 ABA 9 - EMOJI PADRONIZADO:
#   - CORRIGIDO: Usa padrão do sistema
#   - 🚨 = ≤2 dias (URGENTÍSSIMO)
#   - ⚠️ = ≤5 dias (URGENTE)
#   - 🔔 = ≤15 dias (Recente)
#   - Tabela, legenda e cards agora usam mesmo padrão
#
# 🔧 ABA 9 - SELEÇÃO ÚNICA:
#   - Mantida lógica single-select existente
#   - Checkbox permite apenas 1 item por vez
#
# 🔧 ABA 9 - PDF DOWNLOAD:
#   - ADICIONADO: Botão PDF igual às outras abas
#   - Usa função to_pdf_bytes padrão do sistema
#
# 🔧 ABA 9 - FOTO RELATOR:
#   - Mantida exibição da foto do relator no card
#
# 🔧 SENADO - TEXTO TÉCNICO:
#   - Debug checkbox só aparece para admin
#
# ALTERAÇÕES v39 - AJUSTES FINAIS DE UX:
#
# 🔧 LOGIN:
#   - CORRIGIDO: Exige USUÁRIO E SENHA (ambos obrigatórios)
#   - CORRIGIDO: Cor do texto "Deputada Júlia Zanatta" → AMARELO (#FFD700)
#   - Contraste melhorado para legibilidade
#
# 🔧 ABA 5 (BUSCAR PROPOSIÇÃO):
#   - REMOVIDO: Botão "📊 Carregar Proposições"
#   - ADICIONADO: Carregamento automático ao entrar na aba
#   - CACHE: st.session_state["props_aba5_cache"]
#
# 🔧 ABA 9 (APENSADOS):
#   - CHECKBOX: Seleção ÚNICA (single-select) - apenas um item por vez
#   - FOTO RELATOR: Exibida no card do PL Raiz (4 colunas)
#   - EMOJI: Padronizado igual às abas 5 e 7
#
# ALTERAÇÕES v38 - CORREÇÕES FINAIS:
#
# 🔧 CORREÇÃO 1 - ABA 1 (DASHBOARD):
#   - REMOVIDO: Botão "📊 Carregar Dashboard" e st.stop()
#   - ADICIONADO: Carregamento automático ao entrar na aba
#   - CACHE: st.session_state["props_autoria_aba1_cache"]
#   - BOTÃO ATUALIZAR: Disponível apenas para forçar recarga manual
#
# 🔧 CORREÇÃO 2 - ABA 9 (ÚLTIMA MOV. E PARADO HÁ):
#   - CORRIGIDO: Não usa mais trams[0] cegamente
#   - ORDENAÇÃO: Tramitações ordenadas por dataHora DESC (mais recente primeiro)
#   - FILTRO: Remove eventos de "Apresentação" (não são tramitações reais)
#   - FALLBACK: Se só tiver "Apresentação", usa como último recurso
#   - PL 10556/2018: Agora mostra 26/11/2025, não 10/07/2018
#
# 🔧 CORREÇÃO 3 - ABA 9 (TRAVAMENTO CHECKBOX):
#   - GARANTIDO: Detecção pesada roda 1 vez e fica em cache
#   - GARANTIDO: Rerun de UI (checkbox, filtro) NÃO dispara nova detecção
#   - CACHE: st.session_state["projetos_apensados_cache"]
#
# 🔧 CORREÇÃO 4 - ABA 9 (PADRONIZAÇÃO EMOJI):
#   - PADRONIZADO: Usa mesma lógica da função _sinal() das abas 5 e 7
#   - 🔴 = ≥30 dias (crítico)
#   - 🟠 = 15-29 dias (atenção)
#   - 🟡 = 7-14 dias (monitorar)
#   - 🟢 = <7 dias (ok)
#   - COLUNA: Renomeada de "🚦" para "Sinal"
#
# ALTERAÇÕES v37 - OTIMIZAÇÃO E AUTOMAÇÃO (ABAS 5, 6, 7 e 9):
#
# 🔧 ABA 5 - SENADO (OTIMIZADA):
#   - AUTOMÁTICO: Dados do Senado carregam sem clique em botão
#   - CACHE INCREMENTAL: st.session_state["senado_cache_por_id"] armazena por ID
#   - FILTRO INTELIGENTE: Só busca Senado para proposições em "Apreciação pelo Senado Federal"
#   - EXCLUI RICs: RICs não tramitam no Senado
#   - VISUAL LIMPO: Tabela focada apenas nas proposições no Senado
#
# 🔧 ABA 6 - MATÉRIAS (OTIMIZADA):
#   - AUTOMÁTICO: Carrega ao entrar na aba (sem botão)
#   - CACHE: st.session_state["df_aut6_cache"] evita recarga
#   - BOTÃO ATUALIZAR: Disponível para forçar recarga quando necessário
#
# 🔧 ABA 7 - RICs (OTIMIZADA):
#   - AUTOMÁTICO: Carrega ao entrar na aba (sem botão)
#   - CACHE: st.session_state["df_rics_completo"] evita recarga
#   - BOTÃO ATUALIZAR: Disponível para forçar recarga quando necessário
#
# 🔧 ABA 9 - APENSADOS (CORREÇÃO CRÍTICA):
#   - CACHE DA DETECÇÃO: st.session_state["projetos_apensados_cache"]
#   - @st.cache_data: Função buscar_projetos_apensados_completo com TTL de 30min
#   - SEPARAÇÃO UI/DETECÇÃO: Checkboxes NÃO disparam recálculo
#   - AUTOMÁTICO: Carrega ao entrar na aba
#   - SEM TRAVAMENTO: Interações de UI não executam detecção pesada
#
# 🔧 INDEPENDÊNCIA ENTRE ABAS:
#   - Cada aba tem seu próprio cache em st.session_state
#   - Não há dependência entre abas para carregar dados
#   - Senado continua restrito à Aba 5 (gate _pode_chamar_senado mantido)
#
# ALTERAÇÕES v36 - PROJETOS APENSADOS (CORREÇÕES FINAIS):
# - 🔧 CORRIGIDO: PL 5198/2023 → raiz é PL 4953/2016 (não PL 736/2022)
# - ✅ ORDENAÇÃO: Projetos ordenados do mais recente para o mais antigo
# - ✅ CHECKBOXES: Sistema de seleção igual às outras abas
# - ✅ EMOJIS: Lógica igual à aba 5 (🔴 <30 dias, 🟡 30-90, 🟢 >90)
# - ✅ RELATOR: Aparece na tabela principal
# - ✅ AÇÕES: Copiar, abrir links, baixar selecionados
#
# ALTERAÇÕES v35 - PROJETOS APENSADOS (DETECÇÃO HÍBRIDA):
# - NOVA ABA: "📎 Projetos Apensados" para monitorar PLs tramitando em conjunto
# - ✅ DETECÇÃO HÍBRIDA: 
#   1. Usa dicionário MAPEAMENTO_APENSADOS (fonte: CSV da Câmara - confiável)
#   2. Para novos projetos, tenta buscar nas tramitações (automático)
# - DICIONÁRIO: 20 mapeamentos conhecidos de PL → PL principal
# - EXIBE: Situação atual, órgão, última movimentação dos PLs principais
# - ALERTA: Quando PL principal está "Pronta para Pauta"
# - DOWNLOAD: Planilha XLSX com todos os projetos apensados
# - INTEGRAÇÃO: Com robô monitorar_apensados.py (também híbrido)
#
# ALTERAÇÕES v34 - PROPOSIÇÕES FALTANTES:
# - ADICIONADO: PL 2472/2023 (TEA/acompanhante escolas) - Apensado ao PL 1620/2023
# - ADICIONADO: PL 2815/2023 (Bagagem de mão aeronaves) - Apensado ao PL 9417/2017
# - ADICIONADO: PL 4045/2023 (Impedimento OAB) - Apensado ao PL 3593/2020
# - NOTA: Proposições apensadas não tramitam mais individualmente
#
# ALTERAÇÕES v33 - CORREÇÕES CRÍTICAS:
# - REMOVIDO: Busca direta de projetos que NÃO são da deputada na Aba 5
# - CORRIGIDO: Workaround para PL 321/2023 e outras proposições faltantes na API
# - CORRIGIDO: "Situação atual" agora mostra status do SENADO (não da Câmara)
# - CORRIGIDO: Órgão e Relator mostram dados do Senado automaticamente
# - CONCEITO: Sistema Monitor Zanatta = SOMENTE proposições de autoria da deputada
#
# ALTERAÇÕES v32.4 - CORREÇÕES E MELHORIAS:
# - Verificação expandida para detecção de Senado
# - Filtro de anos: garantir que 2023 está incluído por padrão
#
# (v32.3 removida - funcionalidade de busca direta incompatível com conceito do sistema)
#
# ALTERAÇÕES v32.2 - DADOS INTEGRADOS NA TABELA E DETALHES:
# - "Último andamento" mostra do Senado quando matéria está lá
# - "Data do status" / "Última mov." / "Parado há" do Senado
# - Métricas no detalhe usam dados do Senado
# - Removido "(Senado)" dos nomes das colunas
# - UltimasMov_Senado passado para exibir_detalhes_proposicao
#
# ALTERAÇÕES v32.1 - CORREÇÃO DA INTEGRAÇÃO:
# - exibir_detalhes_proposicao() recebe dados do Senado via parâmetro
# - Dados do Senado (órgão, relator, situação) agora aparecem no detalhe
# - Removido expander separado "Detalhes do Senado Federal"
# - Tramitações unificadas Câmara + Senado na mesma lista
# - Foto do relator do Senado quando matéria está lá
#
# ALTERAÇÕES v32.0 - INTEGRAÇÃO TOTAL:
# - AUTOMÁTICO: Detecta se matéria está no Senado pela situação
# - SEM CHECKBOX: Tudo automático, não precisa marcar nada
# - ENDPOINT ÚNICO: /dadosabertos/processo/{codigo} retorna TUDO
# - TRAMITAÇÕES UNIFICADAS: Câmara + Senado na mesma lista, por data
# - FOTO DO RELATOR: Automática do Senado quando matéria está lá
# - DETALHAMENTO ÚNICO: Uma visão integrada da matéria
# - ÓRGÃO/RELATOR: Exibe do Senado automaticamente quando aplicável
#
# Fluxo: Matéria com "Apreciação pelo Senado" → busca automática no Senado
#        → exibe dados do Senado nas colunas Órgão/Relator
#        → tramitações unificadas no detalhe
#
# ALTERAÇÕES v31.1:
# - Busca RELATOR do Senado (não mostra mais relator da Câmara para matérias no Senado)
# - Busca ÓRGÃO/COMISSÃO atual do Senado (ex: CAE, CCJ)
# - Busca últimas 10 MOVIMENTAÇÕES do Senado
# - Novos campos: Relator_Senado, Orgao_Senado_Sigla, Orgao_Senado_Nome, UltimasMov_Senado
# - Abas 5 e 6 mostram dados do Senado quando checkbox ativado
# - Expander com detalhes e movimentações do Senado
# - Cache de 6 horas para todas as consultas ao Senado
# - Logs completos no console para debug
#
# ALTERAÇÕES v31.0:
# - Removida aba separada "Senado Federal" (dados exibidos nas Abas 5 e 6)
# - Consulta ao Senado SOMENTE quando situação = "Apreciação pelo Senado Federal"
# - Número do projeto: IDÊNTICO na Câmara e no Senado (não existe conversão)
# - Link direto para matéria no Senado (não link de busca)
# - Endpoint correto: /dadosabertos/materia/{sigla}/{numero}/{ano} (XML)

# ============================================================
# FUNÇÕES DE INTEGRAÇÃO COM SENADO FEDERAL - v34
# Monitora proposições da Julia Zanatta que estão em
# "Apreciação pelo Senado Federal"
# ============================================================
from core.utils import (
    # text_utils
    sanitize_text_pdf,
    normalize_text,
    party_norm,
    normalize_ministerio,
    canonical_situacao,

    # date_utils
    TZ_BRASILIA,
    get_brasilia_now,
    parse_dt,
    fmt_dt_br,
    days_since,
    proximo_dia_util,
    ajustar_para_dia_util,
    calcular_prazo_ric,
    contar_dias_uteis,
    parse_prazo_resposta_ric,

    # formatters
    format_sigla_num_ano,
    format_relator_text,
    is_comissao_estrategica,
    _verificar_relator_adversario,
    _obter_situacao_com_fallback,
    _categorizar_situacao_para_ordenacao,

    # links
    camara_link_tramitacao,
    camara_link_deputado,
    extract_id_from_uri,

    # xlsx/pdf
    to_xlsx_bytes,
    to_pdf_bytes,
    to_pdf_linha_do_tempo,
    to_pdf_autoria_relatoria,
    to_pdf_comissoes_estrategicas,
    to_pdf_palavras_chave,
    to_pdf_rics_por_status,
)

from core.services.camara_service import CamaraService
from core.services.senado_service import SenadoService

from modules.tabs.tab1_dashboard import render_tab1
from modules.tabs.tab7_rics import render_tab7
from core.data_provider import get_provider


from core.state import init_state

import re
from typing import Optional, Dict, List, Tuple
# IMPORTANTE: o Streamlit precisa estar importado ANTES do primeiro @st.cache_data

import streamlit as st

from core.data_provider import DataProvider

# RE-EXPORTS: core/utils → data_provider compatibility
from core.utils.formatters import format_sigla_num_ano
from core.utils.formatters import format_relator_text
from core.utils.text_utils import canonical_situacao
from core.utils.date_utils import parse_prazo_resposta_ric
from core.utils.links import camara_link_deputado


@st.cache_resource(show_spinner=False)
def get_provider() -> DataProvider:
    """Uma instância do DataProvider por sessão."""
    return DataProvider()


init_state(st)


import pandas as pd
import datetime
from datetime import timezone
import requests
import time
import json
import concurrent.futures
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import matplotlib
import base64

# ====================================================================
# GATE DE CONTROLE - SENADO APENAS NA ABA 5
# ====================================================================
import streamlit as st

def _set_aba_atual(aba_num):
    """Define qual aba está ativa"""
    if "aba_atual_senado" not in st.session_state:
        st.session_state["aba_atual_senado"] = None
    st.session_state["aba_atual_senado"] = aba_num

# ============================================================
# SENADO — importado de core/services/senado_integration
# ============================================================
from core.services.senado_integration import (
    pode_chamar_senado as _pode_chamar_senado,
    extrair_numero_pl_camera,
    verificar_se_foi_para_senado,
    buscar_tramitacao_senado_mesmo_numero,
    buscar_detalhes_senado,
    buscar_movimentacoes_senado,
    buscar_status_senado_por_processo,
    unificar_tramitacoes_camara_senado,
    buscar_codigo_senador_por_nome,
    get_foto_senador,
    enriquecer_proposicao_com_senado,
)

# Certificados SSL: em alguns ambientes (ex.: Streamlit Cloud), a cadeia de CAs do sistema pode não estar disponível.
# Usamos o bundle do certifi quando possível para evitar SSL: CERTIFICATE_VERIFY_FAILED.
try:
    import certifi  # type: ignore
    _REQUESTS_VERIFY = certifi.where()
except Exception:
    _REQUESTS_VERIFY = True

matplotlib.use('Agg')  # Backend não-interativo


# Função para cadastrar email via GitHub API

# ============================================================
# NOTIFICAÇÃO — importado de core/services/notificacao
# ============================================================
from core.services.notificacao import (
    PDF_AVAILABLE,
    GSHEETS_AVAILABLE,
    cadastrar_email_github,
    listar_emails_cadastrados,
    enviar_telegram,
    registrar_gsheets,
    registrar_download_gsheets,
    registrar_download,
    registrar_login,
    telegram_enviar_mensagem,
)


# ============================================================
# PROPOSIÇÃO — importado de core/services/proposicao
# ============================================================
from core.services.proposicao import (
    validar_resposta_api,
    _request_json,
    safe_get,
    fetch_proposicao_completa,
    get_tramitacoes_ultimas10,
    fetch_relator_atual,
    fetch_proposicao_info,
    fetch_lista_proposicoes_autoria_geral,
    buscar_proposicao_direta,
    parse_proposicao_input,
    fetch_rics_por_autor,
    fetch_lista_proposicoes_autoria,
    build_status_map,
)

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
    st.session_state.usuario_logado = None

if not st.session_state.autenticado:
    # CSS para tela de login profissional
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .login-container {
        background: white;
        padding: 3rem 2rem;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        max-width: 450px;
        margin: 4rem auto;
    }
    .login-icon {
        text-align: center;
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .login-title {
        text-align: center;
        color: #2d3748;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .login-subtitle {
        text-align: center;
        color: #FFD700;
        font-size: 1rem;
        margin-bottom: 2rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    .stTextInput input {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 12px;
        font-size: 1rem;
    }
    .stTextInput input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
    }
    .block-container {
        padding-top: 2rem;
    }
    .login-footer {
        text-align: center;
        color: white;
        margin-top: 2rem;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-icon">🏛️</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Monitor Parlamentar</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Deputada Júlia Zanatta</div>', unsafe_allow_html=True)
    
    # Configuração de autenticação
    auth_config = st.secrets.get("auth", {})
    usuarios_config = auth_config.get("usuarios", {})
    senhas_lista = list(auth_config.get("senhas", []))
    senha_unica = auth_config.get("senha")
    
    if not usuarios_config and not senhas_lista and not senha_unica:
        st.error("Erro de configuração: defina [auth.usuarios], [auth].senhas ou [auth].senha em Settings → Secrets.")
        st.stop()
    
    with st.form("login_form", clear_on_submit=False):
        usuario_input = st.text_input(
            "👤 Usuário",
            placeholder="Digite seu usuário",
            key="input_usuario"
        )
        
        senha = st.text_input(
            "🔒 Senha",
            type="password",
            placeholder="Digite sua senha",
            key="input_senha"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
        
        if submit:
            # v39: OBRIGATÓRIO informar usuário E senha
            if not usuario_input or not usuario_input.strip():
                st.error("⚠️ Por favor, informe seu usuário")
            elif not senha:
                st.error("⚠️ Por favor, preencha a senha")
            else:
                usuario_encontrado = None
                autenticado = False
                
                # Verificar usuários nomeados
                for nome_usuario, senha_usuario in usuarios_config.items():
                    if senha == senha_usuario:
                        usuario_encontrado = nome_usuario
                        autenticado = True
                        break
                
                # Verificar lista de senhas (usar usuario_input informado)
                if not autenticado and senha in senhas_lista:
                    usuario_encontrado = usuario_input.strip()
                    autenticado = True
                
                # Verificar senha única (usar usuario_input informado)
                if not autenticado and senha_unica and senha == senha_unica:
                    usuario_encontrado = usuario_input.strip()
                    autenticado = True
                
                if autenticado:
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = usuario_encontrado
                    
                    # Registrar login
                    registrar_login(usuario_encontrado)
                    
                    st.success("✅ Login realizado com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta")
    
    st.markdown("""
    <div class="login-footer">
        💡 <b>Desenvolvido por Lucas Pinheiro</b><br>
        Gabinete da Deputada Júlia Zanatta
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()


# ============================================================
# TIMEZONE DE BRASÍLIA
# ============================================================

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


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

# ============================================================
# WORKAROUND: Proposições faltantes na API da Câmara
# ============================================================
# A API da Câmara (endpoint idDeputadoAutor) não retorna algumas
# proposições que são OFICIALMENTE de autoria da deputada.
# 
# Exemplo: PL 321/2023 (ID 2347150)
# - Página oficial confirma: "Autor: Julia Zanatta - PL/SC"
# - URL: https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2347150
# - Mas a API NÃO retorna esse PL quando consultamos por idDeputadoAutor=220559
#
# Este dicionário serve como FALLBACK para garantir monitoramento correto.
# Chave: ID do deputado(a)
# Valor: Lista de dicionários com dados das proposições faltantes
# ============================================================

# ============================================================
# APENSADOS — importado de core/services/apensados
# ============================================================
from core.services.apensados import (
    PROPOSICOES_FALTANTES_API,
    MAPEAMENTO_APENSADOS_COMPLETO,
    MAPEAMENTO_APENSADOS,
    buscar_id_proposicao,
    buscar_projetos_apensados_completo,
    buscar_projetos_apensados_automatico,
    fetch_proposicao_relacionadas,
    get_proposicao_principal_id,
    get_proposicao_id_from_item,
)


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


_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)

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


def exibir_detalhes_proposicao(selected_id: str, key_prefix: str = "", senado_data: dict = None):
    """
    Função reutilizável para exibir detalhes completos de uma proposição.
    
    Args:
        selected_id: ID da proposição na Câmara
        key_prefix: Prefixo para keys do Streamlit
        senado_data: Dict com dados do Senado (opcional) - se fornecido, usa esses dados
    """
    with st.spinner("Carregando informações completas..."):
        dados_completos = fetch_proposicao_completa(selected_id)
        
        prop = dados_completos.copy()  # alias para compatibilidade
        
        # INTEGRAÇÃO v32.0: Mesclar dados do Senado se fornecidos
        if senado_data:
            prop.update(senado_data)
        
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
        
        # INTEGRAÇÃO v32.0: Se estiver no Senado, unificar tramitações
        no_senado_check = bool(prop.get("no_senado") or prop.get("No Senado?") or prop.get("No Senado"))
        if no_senado_check:
            id_proc_sen = prop.get("id_processo_senado", "")
            codigo_sen = prop.get("codigo_materia_senado", "")
            if id_proc_sen or codigo_sen:
                movs_senado = buscar_movimentacoes_senado(
                    codigo_sen, 
                    id_processo_senado=id_proc_sen, 
                    limite=10, 
                    debug=False
                )
                if movs_senado:
                    df_tram10 = unificar_tramitacoes_camara_senado(df_tram10, movs_senado, limite=10)
        
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
    
    # Se estiver no Senado, mostrar contexto do Senado (órgão/situação/relator)
    # v33 CORRIGIDO: Verificar também pela situação da Câmara
    no_senado_flag = bool(prop.get("no_senado") or prop.get("No Senado?") or prop.get("No Senado"))
    
    # v33: Verificação adicional pela situação da Câmara
    if not no_senado_flag:
        situacao_camara = (situacao or "").lower()
        if verificar_se_foi_para_senado(situacao, despacho):
            no_senado_flag = True
            # Buscar dados do Senado se não foram passados
            if not prop.get("codigo_materia_senado"):
                tipo = status.get("sigla", "")
                numero = status.get("numero", "")
                ano = status.get("ano", "")
                if tipo and numero and ano:
                    dados_senado = buscar_tramitacao_senado_mesmo_numero(tipo, str(numero), str(ano), debug=False)
                    if dados_senado:
                        prop["codigo_materia_senado"] = dados_senado.get("codigo_senado", "")
                        prop["id_processo_senado"] = dados_senado.get("id_processo_senado", "")
                        prop["situacao_senado"] = dados_senado.get("situacao_senado", "")
                        prop["url_senado"] = dados_senado.get("url_senado", "")
                        
                        # Buscar status detalhado do Senado
                        id_proc_sen = dados_senado.get("id_processo_senado", "")
                        if id_proc_sen:
                            status_sen = buscar_status_senado_por_processo(id_proc_sen, debug=False)
                            if status_sen:
                                if status_sen.get("situacao_senado"):
                                    prop["situacao_senado"] = status_sen.get("situacao_senado", "")
                                if status_sen.get("orgao_senado_sigla"):
                                    prop["Orgao_Senado_Sigla"] = status_sen.get("orgao_senado_sigla", "")
                                if status_sen.get("orgao_senado_nome"):
                                    prop["Orgao_Senado_Nome"] = status_sen.get("orgao_senado_nome", "")
                            
                            # Buscar relator do Senado
                            rel_sen_dict = buscar_detalhes_senado(
                                codigo_materia=prop.get("codigo_materia_senado", ""),
                                id_processo=prop.get("id_processo_senado", ""),
                                debug=False
                            )
                            
                            if rel_sen_dict and rel_sen_dict.get("relator_senado"):
                                prop["Relator_Senado"] = rel_sen_dict.get("relator_senado", "")
                            
                            # Buscar movimentações
                            movs = buscar_movimentacoes_senado(prop.get("codigo_materia_senado", ""), id_processo_senado=id_proc_sen, limite=10, debug=False)
                            if movs:
                                linhas_movs = []
                                for m in movs[:5]:
                                    data_mov = m.get("data", "")
                                    orgao_mov = m.get("orgao", "")
                                    desc_mov = m.get("descricao", "")[:80]
                                    linhas_movs.append(f"{data_mov} | {orgao_mov} | {desc_mov}")
                                prop["UltimasMov_Senado"] = "\n".join(linhas_movs)
    
    if no_senado_flag:
        # Órgão do Senado
        orgao_sen = (prop.get("Orgao_Senado_Sigla") or "").strip()
        if not orgao_sen:
            # Tentar extrair das movimentações
            movs = str(prop.get("UltimasMov_Senado", ""))
            if movs and " | " in movs:
                partes = movs.split("\n")[0].split(" | ")
                if len(partes) >= 2 and partes[1].strip():
                    orgao_sen = partes[1].strip()
        if not orgao_sen:
            orgao_sen = "MESA"  # Padrão para proposições recém-chegadas
        org_sigla = orgao_sen
        
        # Situação do Senado
        situacao_sen = (prop.get("situacao_senado") or "").strip()
        if situacao_sen:
            situacao = f"🏛️ {situacao_sen}"
        else:
            situacao = "🏛️ AGUARDANDO DESPACHO"

    st.markdown(f"**Órgão:** {org_sigla}")
    st.markdown(f"**Situação atual:** {situacao}")
    
    
    # Relator: se no Senado, preferir Relator_Senado COM FOTO
    # v33 CORRIGIDO: Se está no Senado mas não tem relator, mostrar "—" (não o da Câmara)
    if no_senado_flag:
        relator_senado_txt = (prop.get('Relator_Senado') or '').strip()
        
        if relator_senado_txt:
            # Extrair nome do relator (antes do parêntese)
            relator_nome_sen = relator_senado_txt.split('(')[0].strip()
            
            # Buscar foto do senador
            foto_senador_url = get_foto_senador(relator_nome_sen)
            
            if foto_senador_url:
                col_foto_sen, col_info_sen = st.columns([1, 3])
                with col_foto_sen:
                    try:
                        st.image(foto_senador_url, width=120, caption=relator_nome_sen)
                    except:
                        st.markdown("📷")
                with col_info_sen:
                    st.markdown("**Relator(a):**")
                    # Link para o senador no site do Senado
                    st.markdown(f"**{relator_senado_txt}**")
                    st.caption("🏛️ Tramitando no Senado Federal")
            else:
                st.markdown("**Relator(a):**")
                st.markdown(f"**{relator_senado_txt}**")
                st.caption("🏛️ Tramitando no Senado Federal")
        else:
            # Está no Senado mas ainda não tem relator designado
            st.markdown("**Relator(a):** —")
            st.caption("🏛️ Tramitando no Senado Federal (aguardando designação de relator)")
        
        relator = None  # evita render do relator da Câmara

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
    
    # INTEGRAÇÃO v32.1: Métricas usando dados do Senado quando disponível
    # datetime já importado no topo
    
    data_status_exibir = status_dt
    ultima_mov_exibir = ultima_dt
    parado_dias_exibir = parado_dias
    
    if no_senado_flag and prop.get("UltimasMov_Senado"):
        movs = str(prop.get("UltimasMov_Senado", ""))
        if movs and movs != "Sem movimentações disponíveis":
            primeira = movs.split("\n")[0] if "\n" in movs else movs
            partes = primeira.split(" | ")
            if partes:
                data_str = partes[0].strip()
                for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                    try:
                        dt_senado = datetime.datetime.strptime(data_str[:16], fmt)
                        ultima_mov_exibir = dt_senado
                        data_status_exibir = dt_senado
                        parado_dias_exibir = (datetime.datetime.now() - dt_senado).days
                        break
                    except:
                        continue
    
    c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
    c1.metric("Data do Status", fmt_dt_br(data_status_exibir))
    c2.metric("Última mov.", fmt_dt_br(ultima_mov_exibir))
    c3.metric("Parado há", f"{parado_dias_exibir} dias" if isinstance(parado_dias_exibir, int) else "—")
    
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

    # INTEGRAÇÃO v32.1: Último andamento do Senado quando disponível
    if no_senado_flag and prop.get("UltimasMov_Senado"):
        movs = str(prop.get("UltimasMov_Senado", ""))
        if movs and movs != "Sem movimentações disponíveis":
            primeira = movs.split("\n")[0] if "\n" in movs else movs
            partes = primeira.split(" | ")
            if len(partes) >= 3:
                andamento_senado = partes[2]
                st.markdown("**Último andamento**")
                st.write(andamento_senado)
            else:
                st.markdown("**Último andamento**")
                st.write(andamento)
        else:
            st.markdown("**Último andamento**")
            st.write(andamento)
    else:
        st.markdown("**Último andamento**")
        st.write(andamento)

    # Despacho só mostra se for da Câmara (Senado não tem esse campo)
    if despacho and not no_senado_flag:
        st.markdown("**Despacho (chave para onde foi)**")
        st.write(despacho)

    if status.get("urlInteiroTeor"):
        st.markdown("**Inteiro teor**")
        st.write(status["urlInteiroTeor"])

    # Links de tramitação - integrado Câmara + Senado
    col_link_cam, col_link_sen = st.columns(2)
    with col_link_cam:
        st.markdown(f"[🏛️ Tramitação na Câmara]({camara_link_tramitacao(selected_id)})")
    with col_link_sen:
        if no_senado_flag and prop.get("url_senado"):
            st.markdown(f"[🏛️ Tramitação no Senado]({prop.get('url_senado')})")

    st.markdown("---")
    st.markdown("### 🧠 Estratégia")
    
    df_estr = montar_estrategia_tabela(situacao, relator_alerta=alerta_relator)
    st.dataframe(df_estr, use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # Verificar se tem dados do Senado para indicar que é unificado
    # no_senado_flag foi definido acima na mesma função
    if no_senado_flag:
        st.markdown("### 🕒 Linha do Tempo Unificada (Câmara + Senado)")
        st.caption("🏛️ CD = Câmara dos Deputados | 🏛️ SF = Senado Federal")
    else:
        st.markdown("### 🕒 Linha do Tempo (últimas 10 movimentações)")

    if df_tram10.empty:
        st.info("Sem tramitações retornadas.")
    else:
        st.dataframe(df_tram10, use_container_width=True, hide_index=True)

        col_xlsx, col_pdf = st.columns(2)
        with col_xlsx:
            try:
                bytes_out, mime, ext = to_xlsx_bytes(df_tram10, "LinhaDoTempo_10")
                
                # Registrar download ao clicar
                if st.download_button(
                    f"⬇️ Baixar XLSX",
                    data=bytes_out,
                    file_name=f"linha_do_tempo_10_{selected_id}.{ext}",
                    mime=mime,
                    key=f"{key_prefix}_download_timeline_xlsx_{selected_id}"
                ):
                    registrar_download("XLSX Linha do Tempo", proposicao_fmt)
            except Exception as e:
                st.error(f"Erro ao gerar XLSX: {e}")
        with col_pdf:
            try:
                # Usar nova função específica para linha do tempo
                proposicao_info = {
                    "proposicao": proposicao_fmt,
                    "situacao": situacao,
                    "orgao": org_sigla,
                    "regime": "",  # Pode ser adicionado futuramente se API fornecer
                    "id": selected_id
                }
                pdf_bytes, pdf_mime, pdf_ext = to_pdf_linha_do_tempo(df_tram10, proposicao_info)
                
                # Registrar download ao clicar
                if st.download_button(
                    f"⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"linha_do_tempo_10_{selected_id}.{pdf_ext}",
                    mime=pdf_mime,
                    key=f"{key_prefix}_download_timeline_pdf_{selected_id}"
                ):
                    registrar_download("PDF Linha do Tempo", proposicao_fmt)
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
    st.caption("v50 ⚠️ - SISTEMA EM INTEGRAÇÃO E MANUTENÇÃO - PODE FICAR INSTÁVEL")

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
    # ABAS REORGANIZADAS (9 abas - com nova aba de Projetos Apensados)
    # Dados do Senado são exibidos nas Abas 5 e 6 quando aplicável
    # ============================================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "1️⃣ Apresentação",
        "2️⃣ Autoria & Relatoria na pauta",
        "3️⃣ Palavras-chave na pauta",
        "4️⃣ Comissões estratégicas",
        "5️⃣ Buscar Proposição Específica",
        "6️⃣ Matérias por situação atual",
        "7️⃣ RICs (Requerimentos de Informação)",
        "📎 Projetos Apensados",
        "📧 Receber Notificações"
        
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
        _set_aba_atual(1)
        
        provider = get_provider()
        perfil = provider.get_perfil_deputada()
        
        render_tab1(provider)
        

    # ============================================================
    # ABA 2 - AUTORIA & RELATORIA NA PAUTA - OTIMIZADA
    # ============================================================
    with tab2:
        _set_aba_atual(2)
        from modules.tabs.tab2_pauta import render_tab2
        render_tab2(provider, exibir_detalhes_proposicao, id_deputada)
               
        
# ============================================================
    # ABA 3 - PALAVRAS-CHAVE
    # ============================================================
    with tab3:
        _set_aba_atual(3)
        from modules.tabs.tab3_palavras_chave import render_tab3
        render_tab3(provider, id_deputada)
        
        
# ============================================================
    # ABA 4 - COMISSÕES ESTRATÉGICAS
    # ============================================================
    with tab4:
        _set_aba_atual(4)
        from modules.tabs.tab4_comissoes import render_tab4
        render_tab4(provider, id_deputada)
        
# ============================================================
    # ABA 5 - BUSCAR PROPOSIÇÃO ESPECÍFICA (LIMPA)
    # ============================================================
    with tab5:
        _set_aba_atual(5)
        from modules.tabs.tab5_buscar import render_tab5
        render_tab5(provider, exibir_detalhes_proposicao, id_deputada)
        
    # ============================================================
    # ABA 6 - MATÉRIAS POR SITUAÇÃO ATUAL (separada)
    # ============================================================
    with tab6:
        _set_aba_atual(6)
        from modules.tabs.tab6_situacao import render_tab6
        render_tab6(provider, exibir_detalhes_proposicao, id_deputada)
        
    # ============================================================
    # ABA 7 - RICs (MÓDULO MIGRADO)
    # ============================================================
    with tab7:
        _set_aba_atual(7)
        provider = get_provider()
        render_tab7(provider, id_deputada)


    # ============================================================
    # ABA 8 - PROJETOS APENSADOS
    # ============================================================
    with tab8:
        _set_aba_atual(8)
        from modules.tabs.tab8_apensados import render_tab8
        render_tab8(provider, exibir_detalhes_proposicao, id_deputada)

    # ============================================================
    # ABA 9 - RECEBER NOTIFICAÇÕES
    # ============================================================
    with tab9:
        _set_aba_atual(9)
        from modules.tabs.tab9_notificacao import render_tab9
        render_tab9()        

        st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")

    st.markdown("---")

if __name__ == "__main__":
    main()
    
    # ============================================================
    # NOTA:
    # FORAM EXTRAÍDAS E INTEGRADAS TODAS AS ABAS.
    # ============================================================