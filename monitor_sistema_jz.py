# monitor_sistema_jz.py - v41 PADRONIZAÇÃO FINAL UX
# 
# ALTERAÇÕES v41 - Dividir para Conquistar:
# Dividir as abas em um sistema só para não ter um monstro de mais de 10000 linhas
#
# ALTERAÇÕES v40 - PADRONIZAÇÃO FINAL UX:
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

def _pode_chamar_senado():
    """Retorna True apenas se estamos na Aba 5"""
    aba_atual = st.session_state.get("aba_atual_senado", None)
    return aba_atual == 5


# Certificados SSL: em alguns ambientes (ex.: Streamlit Cloud), a cadeia de CAs do sistema pode não estar disponível.
# Usamos o bundle do certifi quando possível para evitar SSL: CERTIFICATE_VERIFY_FAILED.
try:
    import certifi  # type: ignore
    _REQUESTS_VERIFY = certifi.where()
except Exception:
    _REQUESTS_VERIFY = True
def extrair_numero_pl_camera(proposicao: str) -> Optional[Tuple[str, str, str]]:
    """
    Extrai tipo, número e ano de uma proposição.
    
    Exemplo: "PLP 223/2023" → ("PLP", "223", "2023")
    
    Returns:
        (tipo, numero, ano) ou None se inválido
    """
    proposicao = proposicao.strip().upper()
    match = re.match(r"([A-Z]+)\s+(\d+)/(\d{4})", proposicao)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


def verificar_se_foi_para_senado(situacao_atual: str, despacho: str = "") -> bool:
    """
    Verifica se a proposição está em apreciação pelo Senado Federal.
    
    REGRA DE NEGÓCIO: Como a Deputada Júlia Zanatta é deputada federal,
    só consultamos o Senado quando o status indicar CLARAMENTE que a 
    matéria está em "Apreciação pelo Senado Federal" ou variações equivalentes.
    
    Args:
        situacao_atual: Situação atual da proposição na Câmara
        despacho: Último despacho (opcional)
        
    Returns:
        True se está em apreciação pelo Senado Federal
    """
    texto_completo = f"{situacao_atual} {despacho}".lower()
    
    # Lista de indicadores - EXPANDIDA v32.2 para cobrir mais casos
    indicadores = [
        # Situações padrão
        "apreciação pelo senado federal",
        "apreciacao pelo senado federal",
        "apreciação pelo senado",
        "apreciacao pelo senado",
        "aguardando apreciação pelo senado",
        "aguardando apreciacao pelo senado",
        "para apreciação do senado",
        "para apreciacao do senado",
        # Situações adicionais - matéria remetida/enviada
        "remetida ao senado federal",
        "remetido ao senado federal",
        "remessa ao senado federal",
        "enviada ao senado federal",
        "enviado ao senado federal",
        "encaminhada ao senado federal",
        "encaminhado ao senado federal",
        # Situações de tramitação
        "tramitando no senado",
        "em tramitação no senado",
        "tramitação no senado",
        # Despachos comuns
        "à mesa do senado",
        "ao senado federal",
        "ofício de remessa ao senado",
        "sgm-p",  # Sigla de remessa ao Senado
    ]
    
    return any(indicador in texto_completo for indicador in indicadores)


@st.cache_data(ttl=21600, show_spinner=False)  # TTL de 6 horas (21600 segundos)
def buscar_tramitacao_senado_mesmo_numero(
    tipo: str,
    numero: str,
    ano: str,
    debug: bool = False
) -> Optional[Dict]:
    """
    Busca a tramitação no Senado usando EXATAMENTE o MESMO número da Câmara.

    REGRA FUNDAMENTAL: o número do projeto é IDÊNTICO na Câmara e no Senado.
    Exemplo: PLP 223/2023 na Câmara → PLP 223/2023 no Senado.
    NÃO existe numeração diferente.

    ENDPOINT (JSON, Swagger): https://legis.senado.leg.br/dadosabertos/processo?sigla=...&numero=...&ano=...&v=1

    Retorna um dict padronizado com:
      - codigo_senado (CodigoMateria)
      - situacao_senado (se disponível no retorno)
      - url_senado (deep link direto na matéria do portal www25)
      - tipo_senado / numero_senado / ano_senado (iguais aos informados)

    Args:
        tipo: Sigla (PL, PLP, PEC, etc.)
        numero: Número
        ano: Ano (4 dígitos)
        debug: Modo debug

    Returns:
        Dict com dados do Senado ou None se não encontrado
    """

    tipo_norm = (tipo or "").strip().upper()
    numero_norm = (numero or "").strip()
    ano_norm = (ano or "").strip()

    if not (tipo_norm and numero_norm and ano_norm):
        return None

    # Endpoint correto (Swagger /processo)
    url = (
        "https://legis.senado.leg.br/dadosabertos/processo"
        f"?sigla={tipo_norm}&numero={numero_norm}&ano={ano_norm}&v=1"
    )

    identificacao_alvo = f"{tipo_norm} {numero_norm}/{ano_norm}"

    print(f"[SENADO] ========================================")
    print(f"[SENADO] Buscando (processo): {identificacao_alvo}")
    print(f"[SENADO] URL: {url}")

    if debug:
        st.write(f"🔍 Buscando no Senado (processo): {identificacao_alvo}")
        st.write(f"URL: {url}")

    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Monitor-Zanatta/1.0",
                "Accept": "application/json",
            },
            verify=_REQUESTS_VERIFY,
        )

        print(f"[SENADO] Status HTTP: {resp.status_code}")

        if resp.status_code == 404:
            print("[SENADO] ℹ️ Não encontrado (404)")
            return None

        if resp.status_code != 200:
            print(f"[SENADO] ❌ HTTP {resp.status_code} (não-200)")
            if debug:
                st.warning(f"Senado retornou HTTP {resp.status_code}")
            return None

        # Pode vir como lista JSON (padrão) ou, em raros casos, outro formato.
        try:
            data = resp.json()
        except Exception:
            # fallback: tentar carregar manualmente
            data = json.loads(resp.text)

        if not data:
            print("[SENADO] ℹ️ Resposta vazia ([]/null)")
            return None

        # Normalizar lista
        itens = data if isinstance(data, list) else [data]

        escolhido = None
        for it in itens:
            ident = (it.get("identificacao") or "").strip()
            if ident.upper() == identificacao_alvo.upper():
                escolhido = it
                break
        if escolhido is None:
            escolhido = itens[0]

        codigo_materia = str(escolhido.get("codigoMateria") or "").strip()
        id_processo = str(escolhido.get("id") or "").strip()
        situacao = (
            str(escolhido.get("situacao") or escolhido.get("situacaoAtual") or "").strip()
            if isinstance(escolhido, dict)
            else ""
        )

        if not codigo_materia:
            print("[SENADO] ❌ Resposta sem codigoMateria")
            if debug:
                st.error("Resposta do Senado sem 'codigoMateria'")
            return None

        url_deep = f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo_materia}"

        print(f"[SENADO] ✅ codigoMateria={codigo_materia} | identificacao={escolhido.get('identificacao')}")
        print(f"[SENADO] ✅ url_deep={url_deep}")

        return {
            "tipo_senado": tipo_norm,
            "numero_senado": numero_norm,
            "ano_senado": ano_norm,
            "codigo_senado": codigo_materia,
            "id_processo_senado": id_processo,
            "situacao_senado": situacao,
            "url_senado": url_deep,
        }

    except Exception as e:
        print(f"[SENADO] ❌ Erro ao consultar Senado (processo): {e}")
        if debug:
            st.error(f"Erro ao consultar Senado: {e}")
        return None

def buscar_detalhes_senado(codigo_materia: str = "", id_processo: str = "", debug: bool = False) -> Optional[Dict]:
    """
    Busca Relator e Órgão atuais no SENADO pelo CodigoMateria.

    Correção:
    - NÃO usar /materia/{codigo}/relatorias nem /materia/{codigo}/situacao (podem não existir).
    - Usar o endpoint do Swagger: /dadosabertos/processo/relatoria?codigoMateria=...

    Retorna dict com:
      - relator_senado (ex: "Izalci Lucas (PL/DF)")
      - relator_nome, relator_partido, relator_uf
      - orgao_senado_sigla (ex: "CAE"), orgao_senado_nome
    """
    import xml.etree.ElementTree as ET
    # datetime já importado no topo

    if not (codigo_materia or id_processo):
        return None

    resultado = {
        "relator_senado": "",
        "relator_nome": "",
        "relator_partido": "",
        "relator_uf": "",
        "orgao_senado_sigla": "",
        "orgao_senado_nome": "",
    }
    if id_processo:
        url = f"https://legis.senado.leg.br/dadosabertos/processo/relatoria?idProcesso={id_processo}"
    else:
        data_ref = datetime.date.today().isoformat()
        url = f"https://legis.senado.leg.br/dadosabertos/processo/relatoria?codigoMateria={codigo_materia}&dataReferencia={data_ref}&v=1"

    # Endpoint (Swagger) — aceita codigoMateria e (opcional) dataReferencia
    # Alguns ambientes ignoram Accept e retornam XML; suportar ambos.
    data_ref = datetime.date.today().isoformat()
    url = f"https://legis.senado.leg.br/dadosabertos/processo/relatoria?codigoMateria={codigo_materia}&dataReferencia={data_ref}&v=1"

    print(f"[SENADO-RELATORIA] Buscando relatoria: {url}")
    if debug:
        st.write(f"🔎 Buscando relatoria (Senado): {url}")

    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Monitor-Zanatta/1.0", "Accept": "application/json"},
            verify=_REQUESTS_VERIFY,
        )
    except Exception as e:
        print(f"[SENADO-RELATORIA] ERRO request: {e}")
        if debug:
            st.error(f"Erro consultando relatoria do Senado: {e}")
        return resultado

    print(f"[SENADO-RELATORIA] Status HTTP: {resp.status_code}")
    if resp.status_code != 200 or not resp.content:
        return resultado

    # ---------- 1) Tentar JSON ----------
    dados = None
    try:
        dados = resp.json()
    except Exception:
        dados = None

    relatorias = []
    if isinstance(dados, list):
        relatorias = dados
    elif isinstance(dados, dict):
        # algumas respostas podem vir aninhadas; tentar chaves comuns
        for k in ("relatorias", "Relatorias", "items", "data"):
            v = dados.get(k)
            if isinstance(v, list):
                relatorias = v
                break

    # ---------- 2) Fallback XML ----------
    if not relatorias:
        try:
            root = ET.fromstring(resp.content)
            # Estrutura típica: <relatorias><relatoria>...</relatoria></relatorias>
            # Aceitar namespaces variados.
            def strip_ns(tag):
                return tag.split("}", 1)[-1] if "}" in tag else tag

            rel_nodes = []
            for el in root.iter():
                if strip_ns(el.tag).lower() in ("relatoria", "relator"):
                    rel_nodes.append(el)

            # Se achou nós "relatoria", extrair campos mínimos
            for el in rel_nodes:
                # pega valores por tag (sem namespace)
                values = {}
                for child in el.iter():
                    t = strip_ns(child.tag)
                    if child.text and child.text.strip():
                        values[t] = child.text.strip()

                if values:
                    relatorias.append({
                        "dataDestituicao": values.get("dataDestituicao") or values.get("DataDestituicao"),
                        "descricaoTipoRelator": values.get("descricaoTipoRelator") or values.get("DescricaoTipoRelator"),
                        "dataDesignacao": values.get("dataDesignacao") or values.get("DataDesignacao"),
                        "nomeParlamentar": values.get("nomeParlamentar") or values.get("NomeParlamentar"),
                        "siglaPartidoParlamentar": values.get("siglaPartidoParlamentar") or values.get("SiglaPartidoParlamentar"),
                        "ufParlamentar": values.get("ufParlamentar") or values.get("UfParlamentar"),
                        "siglaColegiado": values.get("siglaColegiado") or values.get("SiglaColegiado"),
                        "nomeColegiado": values.get("nomeColegiado") or values.get("NomeColegiado"),
                    })
        except Exception as e:
            print(f"[SENADO-RELATORIA] Falha parse XML: {e}")

    if not relatorias:
        return resultado

    # ---------- Escolher relatoria "ativa" ----------
    # Preferir: dataDestituicao == None e descricaoTipoRelator == "Relator"
    def is_active(r):
        dd = r.get("dataDestituicao")
        return dd in (None, "", "null")

    candidatas = [r for r in relatorias if is_active(r)]
    if not candidatas:
        candidatas = relatorias

    relator_cands = [r for r in candidatas if (r.get("descricaoTipoRelator") or "").lower() == "relator"]
    if relator_cands:
        candidatas = relator_cands

    # Ordenar por dataDesignacao (mais recente primeiro) quando possível
    def key_data(r):
        return (r.get("dataDesignacao") or "").strip()

    candidatas.sort(key=key_data, reverse=True)
    atual = candidatas[0] if candidatas else None
    if not atual:
        return resultado

    nome = (atual.get("nomeParlamentar") or "").strip()
    partido = (atual.get("siglaPartidoParlamentar") or "").strip()
    uf = (atual.get("ufParlamentar") or "").strip()
    sigla_col = (atual.get("siglaColegiado") or "").strip()
    nome_col = (atual.get("nomeColegiado") or "").strip()

    resultado["relator_nome"] = nome
    resultado["relator_partido"] = partido
    resultado["relator_uf"] = uf
    resultado["orgao_senado_sigla"] = sigla_col
    resultado["orgao_senado_nome"] = nome_col

    if nome:
        if partido and uf:
            resultado["relator_senado"] = f"{nome} ({partido}/{uf})"
        elif partido:
            resultado["relator_senado"] = f"{nome} ({partido})"
        else:
            resultado["relator_senado"] = nome

    if debug:
        st.write(f"✅ Relator (Senado): {resultado['relator_senado'] or 'não encontrado'}")
        st.write(f"✅ Órgão (Senado): {resultado['orgao_senado_sigla'] or '—'} {resultado['orgao_senado_nome'] or ''}".strip())

    return resultado

def buscar_movimentacoes_senado(
    codigo_materia: str,
    id_processo_senado: str = "",
    limite: int = 10,
    debug: bool = False
) -> List[Dict]:
    """
    Busca as últimas movimentações (informes legislativos) do Senado de forma robusta.

    Fonte principal (Swagger):
      GET https://legis.senado.leg.br/dadosabertos/processo/{id}?v=1

    Onde {id} é o id do processo (vem no retorno do /processo?sigla=...).
    A resposta normalmente vem em JSON, mas pode vir em XML mesmo com Accept: application/json.
    """
    import xml.etree.ElementTree as ET
    # datetime já importado no topo

    if not id_processo_senado:
        return []

    url = f"https://legis.senado.leg.br/dadosabertos/processo/{id_processo_senado}?v=1"
    print(f"[SENADO-PROCESSO] Buscando processo (movimentações): {url}")
    if debug:
        st.write(f"🔎 Buscando processo (Senado): {url}")

    try:
        resp = requests.get(
            url,
            timeout=25,
            headers={"User-Agent": "Monitor-Zanatta/1.0", "Accept": "application/json"},
            verify=_REQUESTS_VERIFY,
        )
    except Exception as e:
        print(f"[SENADO-PROCESSO] ERRO request: {e}")
        if debug:
            st.error(f"Erro consultando processo do Senado: {e}")
        return []

    if resp.status_code != 200 or not resp.content:
        return []

    # ---------- JSON ----------
    informes = []
    try:
        proc = resp.json()
    except Exception:
        proc = None

    if isinstance(proc, dict):
        try:
            autuacoes = proc.get("autuacoes") or []
            if autuacoes and isinstance(autuacoes, list):
                informes = autuacoes[0].get("informesLegislativos") or []
        except Exception:
            informes = []

    # ---------- XML fallback ----------
    if not informes:
        try:
            root = ET.fromstring(resp.content)
            informes_xml = root.findall(".//informesLegislativos//informeLegislativo")
            for it in informes_xml:
                data_txt = (it.findtext("data") or "").strip()
                desc = (it.findtext("descricao") or "").strip()
                coleg_sigla = (it.findtext(".//colegiado/sigla") or "").strip()
                informes.append({"data": data_txt, "descricao": desc, "colegiado": {"sigla": coleg_sigla}})
        except Exception:
            informes = []

    movs = []
    for it in informes:
        data_txt = (it.get("data") or "").strip()
        desc = (it.get("descricao") or "").strip()
        org_sigla = ""
        coleg = it.get("colegiado") or {}
        if isinstance(coleg, dict):
            org_sigla = (coleg.get("sigla") or "").strip()

        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                dt = datetime.datetime.strptime(data_txt[:26], fmt)
                break
            except Exception:
                continue

        if dt:
            data_br = dt.strftime("%d/%m/%Y")
            hora = dt.strftime("%H:%M")
            sort_key = dt
        else:
            data_br = data_txt
            hora = ""
            sort_key = datetime.min

        movs.append({"data": data_br, "hora": hora, "orgao": org_sigla, "descricao": desc, "_sort": sort_key})

    movs.sort(key=lambda x: x.get("_sort"), reverse=True)
    movs = movs[:limite]
    for m in movs:
        m.pop("_sort", None)
    return movs


def buscar_status_senado_por_processo(
    id_processo_senado: str,
    debug: bool = False
) -> Dict:
    """
    Obtém SITUAÇÃO ATUAL e ÓRGÃO ATUAL no Senado via:
      GET https://legis.senado.leg.br/dadosabertos/processo/{id}?v=1

    Retorna dict:
      - situacao_senado
      - orgao_senado_sigla
      - orgao_senado_nome
    """
    import xml.etree.ElementTree as ET

    out = {"situacao_senado": "", "orgao_senado_sigla": "", "orgao_senado_nome": ""}
    if not id_processo_senado:
        return out

    url = f"https://legis.senado.leg.br/dadosabertos/processo/{id_processo_senado}?v=1"
    print(f"[SENADO-PROCESSO] Buscando processo (status): {url}")
    if debug:
        st.write(f"🔎 Buscando processo (status Senado): {url}")

    try:
        resp = requests.get(
            url,
            timeout=25,
            headers={"User-Agent": "Monitor-Zanatta/1.0", "Accept": "application/json"},
            verify=_REQUESTS_VERIFY,
        )
    except Exception as e:
        print(f"[SENADO-PROCESSO] ERRO request: {e}")
        if debug:
            st.error(f"Erro consultando processo do Senado: {e}")
        return out

    if resp.status_code != 200 or not resp.content:
        return out

    # JSON primeiro
    try:
        proc = resp.json()
    except Exception:
        proc = None

    if isinstance(proc, dict):
        autuacoes = proc.get("autuacoes") or []
        if autuacoes and isinstance(autuacoes, list):
            a0 = autuacoes[0] or {}
            out["orgao_senado_sigla"] = (a0.get("siglaColegiadoControleAtual") or "").strip()
            out["orgao_senado_nome"] = (a0.get("nomeColegiadoControleAtual") or "").strip()

            situacoes = a0.get("situacoes") or []
            if isinstance(situacoes, list) and situacoes:
                ativa = None
                for s in reversed(situacoes):
                    if not s.get("fim"):
                        ativa = s
                        break
                if not ativa:
                    ativa = situacoes[-1]
                out["situacao_senado"] = (ativa.get("descricao") or "").strip()
        return out

    # XML fallback
    try:
        root = ET.fromstring(resp.content)
        out["orgao_senado_sigla"] = (root.findtext(".//autuacao/siglaColegiadoControleAtual") or "").strip()
        out["orgao_senado_nome"] = (root.findtext(".//autuacao/nomeColegiadoControleAtual") or "").strip()

        situacoes = root.findall(".//autuacao/situacoes/situacao")
        if situacoes:
            ativa = None
            for s in reversed(situacoes):
                fim = (s.findtext("fim") or "").strip()
                if not fim:
                    ativa = s
                    break
            if not ativa:
                ativa = situacoes[-1]
            out["situacao_senado"] = (ativa.findtext("descricao") or "").strip()
    except Exception:
        pass

    return out

def unificar_tramitacoes_camara_senado(
    df_tramitacoes_camara: pd.DataFrame,
    movimentacoes_senado: List[Dict],
    limite: int = 10
) -> pd.DataFrame:
    """
    Unifica tramitações da Câmara e Senado em uma única lista ordenada por data.
    
    Args:
        df_tramitacoes_camara: DataFrame com tramitações da Câmara
        movimentacoes_senado: Lista de dicts com movimentações do Senado
        limite: Número máximo de tramitações a retornar
        
    Returns:
        DataFrame unificado com coluna 'Casa' indicando origem
    """
    # datetime já importado no topo
    
    todas_tramitacoes = []
    
    # Processar tramitações da Câmara
    if not df_tramitacoes_camara.empty:
        for _, row in df_tramitacoes_camara.iterrows():
            data_str = str(row.get("Data", "") or row.get("data", ""))
            hora_str = str(row.get("Hora", "") or row.get("hora", "") or "")
            # Aceitar tanto "Tramitação" quanto "Descrição"
            descricao = str(row.get("Tramitação", "") or row.get("Descrição", "") or row.get("descricao", "") or row.get("descricaoTramitacao", ""))
            orgao = str(row.get("Órgão", "") or row.get("orgao", "") or row.get("siglaOrgao", ""))
            
            # Parsear data
            dt_sort = None
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    dt_sort = datetime.datetime.strptime(data_str[:19], fmt)
                    break
                except:
                    continue
            
            todas_tramitacoes.append({
                "Data": data_str,
                "Hora": hora_str,
                "Casa": "🏛️ CD",  # Câmara dos Deputados
                "Órgão": orgao,
                "Tramitação": descricao[:200] if descricao else "",
                "_sort": dt_sort or datetime.min
            })
    
    # Processar movimentações do Senado
    for mov in movimentacoes_senado:
        data_str = mov.get("data", "")
        hora = mov.get("hora", "")
        orgao = mov.get("orgao", "")
        descricao = mov.get("descricao", "")
        
        # Parsear data para ordenação
        dt_sort = None
        data_completa = f"{data_str} {hora}".strip() if hora else data_str
        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt_sort = datetime.datetime.strptime(data_completa[:16], fmt)
                break
            except:
                continue
        
        todas_tramitacoes.append({
            "Data": data_str,
            "Hora": hora,
            "Casa": "🏛️ SF",  # Senado Federal
            "Órgão": orgao,
            "Tramitação": descricao[:200] if descricao else "",
            "_sort": dt_sort or datetime.min
        })
    
    if not todas_tramitacoes:
        return pd.DataFrame()
    
    # Criar DataFrame e ordenar por data (mais recente primeiro)
    df = pd.DataFrame(todas_tramitacoes)
    df = df.sort_values("_sort", ascending=False)
    df = df.drop(columns=["_sort"])
    df = df.head(limite)
    
    # Reordenar colunas
    cols_order = ["Data", "Hora", "Casa", "Órgão", "Tramitação"]
    df = df[[c for c in cols_order if c in df.columns]]
    
    return df


@st.cache_data(ttl=86400, show_spinner=False)  # Cache de 24h
def buscar_codigo_senador_por_nome(nome_senador: str) -> Optional[str]:
    """
    Busca o código do senador pelo nome para obter a foto.
    
    Endpoint: https://legis.senado.leg.br/dadosabertos/senador/lista/atual
    
    Returns:
        Código do senador ou None
    """
    
    if not nome_senador:
        return None
    
    # Normalizar nome para busca
    nome_busca = nome_senador.lower().strip()
    # Remover "Senador " ou "Senadora " do início
    for prefixo in ["senador ", "senadora "]:
        if nome_busca.startswith(prefixo):
            nome_busca = nome_busca[len(prefixo):]
    
    url = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"
    
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Monitor-Zanatta/1.0", "Accept": "application/json"},
            verify=_REQUESTS_VERIFY,
        )
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        
        # Estrutura: {"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": [...]}}}
        parlamentares = []
        if isinstance(data, dict):
            lista = data.get("ListaParlamentarEmExercicio", {})
            parls = lista.get("Parlamentares", {})
            parlamentares = parls.get("Parlamentar", [])
            if not isinstance(parlamentares, list):
                parlamentares = [parlamentares] if parlamentares else []
        
        for p in parlamentares:
            ident = p.get("IdentificacaoParlamentar", {})
            nome_parl = (ident.get("NomeParlamentar") or "").lower()
            nome_completo = (ident.get("NomeCompletoParlamentar") or "").lower()
            codigo = ident.get("CodigoParlamentar")
            
            # Comparar com nome buscado
            if nome_busca in nome_parl or nome_busca in nome_completo or nome_parl in nome_busca:
                return str(codigo)
        
        return None
        
    except Exception as e:
        print(f"[SENADOR-FOTO] Erro ao buscar código: {e}")
        return None


def get_foto_senador(nome_senador: str, codigo_senador: str = None) -> Optional[str]:
    """
    Retorna a URL da foto do senador.
    
    Tenta primeiro pelo código, depois busca pelo nome.
    
    Args:
        nome_senador: Nome do senador (ex: "Izalci Lucas")
        codigo_senador: Código do senador (opcional)
        
    Returns:
        URL da foto ou None
    """
    if not codigo_senador and nome_senador:
        codigo_senador = buscar_codigo_senador_por_nome(nome_senador)
    
    if codigo_senador:
        # URL padrão de fotos do Senado
        return f"https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo_senador}.jpg"
    
    return None
    
    linhas = []
    for mov in movimentacoes:
        data = mov.get("data", "")
        descricao = mov.get("descricao", "")
        orgao = mov.get("orgao", "")
        
        if orgao:
            linha = f"• {data} [{orgao}]: {descricao}"
        else:
            linha = f"• {data}: {descricao}"
        
        linhas.append(linha)
    
    return "\n".join(linhas)


def enriquecer_proposicao_com_senado(proposicao_dict: Dict, debug: bool = False) -> Dict:
    """
    Adiciona informações do Senado a uma proposição da Câmara.
    
    REGRA DE NEGÓCIO: Só consulta o Senado se a situação for "Apreciação pelo Senado Federal".
    IMPORTANTE: O número da Câmara é IGUAL ao número do Senado (não existe conversão).
    
    Campos adicionados:
    - no_senado: bool
    - codigo_materia_senado: str (CodigoMateria)
    - situacao_senado: str
    - url_senado: str (deep link)
    - tipo_numero_senado: str
    - Relator_Senado: str (relator formatado do Senado)
    - Orgao_Senado_Sigla: str
    - Orgao_Senado_Nome: str
    - UltimasMov_Senado: str (movimentações formatadas)
    
    Args:
        proposicao_dict: Dicionário com dados da proposição da Câmara
        debug: Modo debug
        
    Returns:
        Dicionário enriquecido com dados do Senado (colunas originais preservadas)
    """
    # DETECTOR: Rastrear de onde vem a chamada
    import traceback
    import inspect
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    caller_name = caller_frame.f_code.co_name if caller_frame else "unknown"
    if caller_name != "processar_lista_com_senado":
        print(f"[SENADO-DEBUG] ⚠️ enriquecer_proposicao_com_senado chamado de: {caller_name}")
        # Imprimir stack trace reduzido
        stack = traceback.extract_stack()
        for frame_info in stack[-4:-1]:  # Últimas 3 chamadas
            print(f"[SENADO-DEBUG]    → {frame_info.filename.split('/')[-1]}:{frame_info.lineno} in {frame_info.name}")
    
    # Copiar dados originais (IMPORTANTE!)
    resultado = proposicao_dict.copy()
    
    # Inicializar campos do Senado
    resultado["no_senado"] = False
    resultado["codigo_materia_senado"] = ""
    resultado["id_processo_senado"] = ""  # NOVO v32.0
    resultado["situacao_senado"] = ""
    resultado["url_senado"] = ""
    resultado["tipo_numero_senado"] = ""
    resultado["Relator_Senado"] = ""
    resultado["Orgao_Senado_Sigla"] = ""
    resultado["Orgao_Senado_Nome"] = ""
    resultado["UltimasMov_Senado"] = ""
    
    # PRÉ-FILTRO: Só processar tipos que podem ir ao Senado
    proposicao_str = proposicao_dict.get("Proposição", "") or proposicao_dict.get("Proposicao", "")
    tipo_proposicao = proposicao_str.split()[0] if proposicao_str else ""
    
    # Tipos permitidos: PL, PLP, PEC, PDL (que podem ir ao Senado)
    # Não processar: RIC, PRC, REQ, INC, etc.
    TIPOS_PERMITIDOS_SENADO = {"PL", "PLP", "PEC", "PDL"}
    
    if tipo_proposicao not in TIPOS_PERMITIDOS_SENADO:
        # Não loga nada - silencioso para evitar poluição
        return resultado
    
    
    # Verificar se está em apreciação pelo Senado
    situacao = proposicao_dict.get("Situação atual", "")
    despacho = proposicao_dict.get("despacho", "")
    proposicao_str = proposicao_dict.get("Proposição", "") or proposicao_dict.get("Proposicao", "")
    
    if not verificar_se_foi_para_senado(situacao, despacho):
        # LOG: Não é para buscar no Senado
        print(f"[SENADO] ⏭️ IGNORANDO {proposicao_str} - situação '{situacao}' não requer busca no Senado")
        return resultado
    
    # LOG: Vai buscar no Senado
    print(f"[SENADO] 🔍 CONSULTANDO {proposicao_str} - situação '{situacao}' indica apreciação pelo Senado")
    
    # Extrair identificação da proposição
    if not proposicao_str:
        print(f"[SENADO] ⚠️ Proposição sem identificação, pulando...")
        return resultado
    
    partes = extrair_numero_pl_camera(proposicao_str)
    if not partes:
        print(f"[SENADO] ⚠️ Não foi possível extrair tipo/número/ano de '{proposicao_str}'")
        return resultado
    
    tipo, numero, ano = partes
    print(f"[SENADO] 📋 Usando MESMO número da Câmara: {tipo} {numero}/{ano}")
    
    # 1. Buscar dados básicos no Senado (código da matéria, situação, URL)
    dados_senado = buscar_tramitacao_senado_mesmo_numero(
        tipo, numero, ano, debug=debug
    )
    
    if dados_senado:
        resultado["no_senado"] = True
        resultado["codigo_materia_senado"] = dados_senado.get("codigo_senado", "")
        resultado["id_processo_senado"] = dados_senado.get("id_processo_senado", "")  # NOVO v32.0
        resultado["situacao_senado"] = dados_senado.get("situacao_senado", "")
        resultado["url_senado"] = dados_senado.get("url_senado", "")
        resultado["tipo_numero_senado"] = (
            f"{dados_senado.get('tipo_senado', '')} "
            f"{dados_senado.get('numero_senado', '')}/"
            f"{dados_senado.get('ano_senado', '')}"
        ).strip()
        codigo_materia = dados_senado.get("codigo_senado", "")
        # 1.1 Buscar status atual e movimentações do Senado via /processo/{id}
        id_proc_sen = dados_senado.get("id_processo_senado", "")
        if id_proc_sen:
            status_sen = buscar_status_senado_por_processo(id_proc_sen, debug=debug)
            if status_sen:
                # Situação atual no Senado (ex: "PRONTA PARA A PAUTA NA COMISSÃO")
                if status_sen.get("situacao_senado"):
                    resultado["situacao_senado"] = status_sen.get("situacao_senado", "")
                # Órgão atual (Senado) — pode sobrescrever o do endpoint de relatoria
                if status_sen.get("orgao_senado_sigla"):
                    resultado["Orgao_Senado_Sigla"] = status_sen.get("orgao_senado_sigla", "")
                if status_sen.get("orgao_senado_nome"):
                    resultado["Orgao_Senado_Nome"] = status_sen.get("orgao_senado_nome", "")

            movs = buscar_movimentacoes_senado(codigo_materia, id_processo_senado=id_proc_sen, limite=10, debug=debug)
            if movs:
                # Texto pronto para expander
                linhas = []
                for mv in movs:
                    linhas.append(f"{mv.get('data','')} {mv.get('hora','')}".strip() + " | " + (mv.get('orgao','') or "—") + " | " + (mv.get('descricao','') or ""))
                resultado["UltimasMov_Senado"] = "\n".join(linhas)

        # 2. Buscar detalhes em endpoints separados (/relatorias e /situacao)
        codigo_materia = dados_senado.get("codigo_senado", "")
        if codigo_materia:
            detalhes = buscar_detalhes_senado(
                codigo_materia=codigo_materia,
                id_processo=id_proc_sen,
                debug=debug
            )
            
            if detalhes:
                resultado["Relator_Senado"] = detalhes.get("relator_senado", "")
                resultado["Orgao_Senado_Sigla"] = detalhes.get("orgao_senado_sigla", "")
                resultado["Orgao_Senado_Nome"] = detalhes.get("orgao_senado_nome", "")
        
        if debug:
            st.success(f"✅ {proposicao_str} encontrado no Senado")
            st.write(f"Relator Senado: {resultado['Relator_Senado'] or 'não encontrado'}")
            st.write(f"Órgão Senado: {resultado['Orgao_Senado_Sigla'] or 'não encontrado'}")
    else:
        print(f"[SENADO] ℹ️ {proposicao_str} não encontrado no Senado (pode não ter chegado ainda)")
    
    return resultado


def cadastrar_email_github(novo_email: str) -> tuple[bool, str]:
    """
    Adiciona um novo email à lista de destinatários no repositório GitHub.
    Atualiza o arquivo emails_cadastrados.json no repositório.

    Retorna: (sucesso: bool, mensagem: str)
    """
    try:
        # Configurações do GitHub (adicionar em st.secrets)
        github_config = st.secrets.get("github", {})
        token = github_config.get("token")  # Personal Access Token
        repo = github_config.get("repo", "LucasPin45/monitorzanatta")

        if not token:
            return False, "Token do GitHub não configurado"

        # Validar email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", novo_email):
            return False, "Email inválido"

        # URL da API do GitHub
        api_url = f"https://api.github.com/repos/{repo}/contents/emails_cadastrados.json"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Buscar arquivo atual
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Arquivo existe - atualizar
            data = response.json()
            sha = data["sha"]
            content = base64.b64decode(data["content"]).decode("utf-8")
            emails_data = json.loads(content)
        elif response.status_code == 404:
            # Arquivo não existe - criar
            sha = None
            emails_data = {"emails": [], "ultima_atualizacao": None}
        else:
            return False, f"Erro ao acessar GitHub: {response.status_code}"

        # Verificar se email já está cadastrado
        if novo_email.lower() in [e.lower() for e in emails_data.get("emails", [])]:
            return False, "Este email já está cadastrado"

        # Adicionar novo email
        emails_data["emails"].append(novo_email)
        emails_data["ultima_atualizacao"] = datetime.datetime.now().isoformat()

        # Preparar conteúdo para upload
        new_content = json.dumps(emails_data, indent=2, ensure_ascii=False)
        new_content_b64 = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        # Fazer commit
        commit_data = {
            "message": f"📧 Novo email cadastrado via painel",
            "content": new_content_b64,
            "branch": "main"
        }

        if sha:
            commit_data["sha"] = sha

        response = requests.put(api_url, headers=headers, json=commit_data, timeout=10)

        if response.status_code in [200, 201]:
            return True, f"Email {novo_email} cadastrado com sucesso!"
        else:
            return False, f"Erro ao salvar: {response.status_code}"

    except Exception as e:
        return False, f"Erro: {str(e)}"


def listar_emails_cadastrados() -> list:
    """
    Lista os emails cadastrados no arquivo emails_cadastrados.json
    """
    try:
        github_config = st.secrets.get("github", {})
        token = github_config.get("token")
        repo = github_config.get("repo", "LucasPin45/monitorzanatta")

        if not token:
            return []

        api_url = f"https://api.github.com/repos/{repo}/contents/emails_cadastrados.json"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            emails_data = json.loads(content)
            return emails_data.get("emails", [])

        return []

    except Exception:
        return []


# Tentar importar biblioteca de PDF (opcional)
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

# Tentar importar biblioteca do Google Sheets (opcional)
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False


# ============================================================
# FUNÇÕES DE MONITORAMENTO DE LOGIN (Telegram + Google Sheets)
# ============================================================

def enviar_telegram(mensagem: str) -> bool:
    """
    Envia mensagem para o Telegram.
    Retorna True se enviou com sucesso, False caso contrário.
    """
    try:
        telegram_config = st.secrets.get("telegram", {})
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        
        if not bot_token or not chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def registrar_gsheets(usuario: str, data_hora: str, ip: str = "N/A") -> bool:
    """
    Registra login no Google Sheets.
    Retorna True se registrou com sucesso, False caso contrário.
    """
    if not GSHEETS_AVAILABLE:
        return False
    
    try:
        gsheets_config = st.secrets.get("gsheets", {})
        spreadsheet_id = gsheets_config.get("spreadsheet_id")
        credentials_json = gsheets_config.get("credentials")
        
        if not spreadsheet_id or not credentials_json:
            return False
        
        # Carregar credenciais
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = dict(credentials_json)
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # Dados a inserir
        valores = [[data_hora, usuario, ip]]
        
        body = {"values": valores}
        
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A:C",  # Colunas: Data/Hora, Usuário, IP
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        return True
    except Exception:
        return False


def registrar_download_gsheets(usuario: str, data_hora: str, tipo_relatorio: str, proposicao: str = "") -> bool:
    """
    Registra download de relatório no Google Sheets (aba Downloads).
    Retorna True se registrou com sucesso, False caso contrário.
    """
    if not GSHEETS_AVAILABLE:
        return False
    
    try:
        gsheets_config = st.secrets.get("gsheets", {})
        spreadsheet_id = gsheets_config.get("spreadsheet_id")
        credentials_json = gsheets_config.get("credentials")
        
        if not spreadsheet_id or not credentials_json:
            return False
        
        # Carregar credenciais
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = dict(credentials_json)
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # Dados a inserir: Data/Hora, Usuário, Tipo de Relatório, Proposição
        valores = [[data_hora, usuario, tipo_relatorio, proposicao]]
        
        body = {"values": valores}
        
        # Registrar na aba "Downloads" (será criada automaticamente se não existir)
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Downloads!A:D",  # Aba: Downloads | Colunas: Data/Hora, Usuário, Tipo, Proposição
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        return True
    except Exception:
        return False


def registrar_download(tipo_relatorio: str, proposicao: str = ""):
    """
    Registra o download de relatório no Telegram e Google Sheets.
    Executado em background para não travar a interface.
    
    Args:
        tipo_relatorio: Ex: "PDF Linha do Tempo", "XLSX Linha do Tempo", "PDF Matérias"
        proposicao: Ex: "PL 5701/2025"
    """
    try:
        # Obter usuário logado
        usuario = st.session_state.get("usuario_logado", "Desconhecido")
        
        # Obter data/hora de Brasília
        tz_brasilia = ZoneInfo("America/Sao_Paulo")
        agora = datetime.datetime.now(tz_brasilia)
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        # Mensagem para o Telegram
        mensagem = (
            f"📥 <b>Download de Relatório</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"📄 <b>Tipo:</b> {tipo_relatorio}\n"
        )
        if proposicao:
            mensagem += f"📋 <b>Proposição:</b> {proposicao}\n"
        mensagem += f"📅 <b>Data/Hora:</b> {data_hora_str}"
        
        # Enviar notificação Telegram
        enviar_telegram(mensagem)
        
        # Registrar no Google Sheets
        registrar_download_gsheets(usuario, data_hora_str, tipo_relatorio, proposicao)
        
    except Exception:
        # Silenciosamente ignora erros para não travar a interface
        pass


def registrar_login(usuario: str):
    """
    Registra o login do usuário no Telegram e Google Sheets.
    Executado em background para não travar a interface.
    """
    try:
        # Obter data/hora de Brasília
        tz_brasilia = ZoneInfo("America/Sao_Paulo")
        agora = datetime.datetime.now(tz_brasilia)
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        # Tentar obter IP (pode não funcionar em todos os ambientes)
        ip = "N/A"
        try:
            # No Streamlit Cloud, headers podem ter o IP
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                ip = st.context.headers.get("x-forwarded-for", "N/A")
        except Exception:
            pass
        
        # Mensagem para o Telegram
        mensagem = (
            f"🔐 <b>Login no Monitor Zanatta</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"📅 <b>Data/Hora:</b> {data_hora_str}\n"
            f"🌐 <b>IP:</b> {ip}"
        )
        
        # Enviar notificação Telegram
        enviar_telegram(mensagem)
        
        # Registrar no Google Sheets
        registrar_gsheets(usuario, data_hora_str, ip)
        
    except Exception:
        # Silenciosamente ignora erros para não travar o login
        pass


# ============================================================
# FUNÇÕES DE INTEGRAÇÃO COM API DO SENADO FEDERAL - v30.1 CORRIGIDA
# Versão com tratamento robusto de erros e debug
# ============================================================


def validar_resposta_api(response) -> tuple[bool, str]:
    """
    Valida se a resposta da API é válida.
    
    Returns:
        (valida: bool, mensagem_erro: str)
    """
    # Verificar status code
    if response.status_code != 200:
        return False, f"API retornou status {response.status_code}"
    
    # Verificar content-type
    content_type = response.headers.get('content-type', '')
    if 'json' not in content_type.lower() and 'application/json' not in content_type.lower():
        # Se não for JSON, pode ser HTML de erro
        if 'html' in content_type.lower():
            return False, "API retornou HTML ao invés de JSON (possível erro do servidor)"
        return False, f"Tipo de conteúdo inesperado: {content_type}"
    
    # Verificar se tem conteúdo
    if not response.text or len(response.text.strip()) == 0:
        return False, "API retornou resposta vazia"
    
    # Verificar se é JSON válido
    try:
        response.json()
        return True, ""
    except ValueError as e:
        return False, f"Resposta não é JSON válido: {str(e)}"


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
PROPOSICOES_FALTANTES_API = {
    "220559": [  # Julia Zanatta - Projetos que a API não retorna corretamente
        
        # === PROJETOS NO SENADO (PRINCIPAIS) ===
        {
            "id": "2347150",
            "siglaTipo": "PL",
            "numero": "321",
            "ano": "2023",
            "ementa": "Altera o Decreto-Lei nº 3.689, de 3 de outubro de 1941 (Código de Processo Penal), para prever a realização da audiência de custódia por videoconferência."
        },
        {
            "id": "2397890",
            "siglaTipo": "PLP",
            "numero": "223",
            "ano": "2023",
            "ementa": "Altera a Lei Complementar 123, de 14 de dezembro de 2006, para dispor sobre a prorrogação do prazo para o recolhimento de impostos para as Microempresas e Empresas de Pequeno Porte, em situação de decretação de estado de calamidade pública estadual ou distrital."
        },
        
        # === OUTROS PROJETOS FALTANTES ===
        {"id": "2381193", "siglaTipo": "PL", "numero": "4045", "ano": "2023"},   # PL 4045/2023
        
        # === PROJETOS APENSADOS (24 total) ===
        {"id": "2570510", "siglaTipo": "PL", "numero": "5072", "ano": "2025"},   # PL 5072/2025
        {"id": "2571359", "siglaTipo": "PL", "numero": "5128", "ano": "2025"},   # PL 5128/2025
        {"id": "2483453", "siglaTipo": "PLP", "numero": "19", "ano": "2025"},    # PLP 19/2025
        {"id": "2455568", "siglaTipo": "PL", "numero": "3341", "ano": "2024"},   # PL 3341/2024
        {"id": "2436763", "siglaTipo": "PL", "numero": "2098", "ano": "2024"},   # PL 2098/2024
        {"id": "2455562", "siglaTipo": "PL", "numero": "3338", "ano": "2024"},   # PL 3338/2024
        {"id": "2482260", "siglaTipo": "PDL", "numero": "24", "ano": "2025"},    # PDL 24/2025
        {"id": "2482169", "siglaTipo": "PDL", "numero": "16", "ano": "2025"},    # PDL 16/2025
        {"id": "2567301", "siglaTipo": "PL", "numero": "4954", "ano": "2025"},   # PL 4954/2025
        {"id": "2531615", "siglaTipo": "PL", "numero": "3222", "ano": "2025"},   # PL 3222/2025
        {"id": "2372482", "siglaTipo": "PLP", "numero": "141", "ano": "2023"},   # PLP 141/2023
        {"id": "2399426", "siglaTipo": "PL", "numero": "5198", "ano": "2023"},   # PL 5198/2023
        {"id": "2423254", "siglaTipo": "PL", "numero": "955", "ano": "2024"},    # PL 955/2024
        {"id": "2374405", "siglaTipo": "PDL", "numero": "194", "ano": "2023"},   # PDL 194/2023
        {"id": "2374340", "siglaTipo": "PDL", "numero": "189", "ano": "2023"},   # PDL 189/2023
        {"id": "2485135", "siglaTipo": "PL", "numero": "623", "ano": "2025"},    # PL 623/2025
        {"id": "2419264", "siglaTipo": "PDL", "numero": "30", "ano": "2024"},    # PDL 30/2024
        {"id": "2375447", "siglaTipo": "PDL", "numero": "209", "ano": "2023"},   # PDL 209/2023
        {"id": "2456691", "siglaTipo": "PDL", "numero": "348", "ano": "2024"},   # PDL 348/2024
        {"id": "2462038", "siglaTipo": "PL", "numero": "3887", "ano": "2024"},   # PL 3887/2024
        {"id": "2448732", "siglaTipo": "PEC", "numero": "28", "ano": "2024"},    # PEC 28/2024
        {"id": "2390075", "siglaTipo": "PDL", "numero": "337", "ano": "2023"},   # PDL 337/2023
        {"id": "2361454", "siglaTipo": "PL", "numero": "2472", "ano": "2023"},   # PL 2472/2023
        {"id": "2365600", "siglaTipo": "PL", "numero": "2815", "ano": "2023"},   # PL 2815/2023
    ]
}

# ============================================================
# PROJETOS APENSADOS - v35.1 (MAPEAMENTO COMPLETO)
# ============================================================
# Mapeamento DIRETO para o PL RAIZ (onde tramita de verdade)
# Inclui: PL principal imediato, PL raiz, e cadeia completa
# ============================================================

# Mapeamento principal: ID da proposição Zanatta → dados completos
# Formato: {id: {"principal": "PL X", "raiz": "PL Y", "cadeia": ["PL A", "PL B", ...]}}
MAPEAMENTO_APENSADOS_COMPLETO = {
    # === PLs ===
    "2361454": {  # PL 2472/2023 - TEA/Acompanhante escolas
        "principal": "PL 1620/2023",
        "raiz": "PL 1620/2023",
        "cadeia": ["PL 1620/2023"],
    },
    "2361794": {  # PL 2501/2023 - Crime de censura
        "principal": "PL 2782/2022",
        "raiz": "PL 2782/2022",
        "cadeia": ["PL 2782/2022"],
    },
    "2365600": {  # PL 2815/2023 - Bagagem de mão
        "principal": "PL 9417/2017",
        "raiz": "PL 9417/2017",
        "cadeia": ["PL 9417/2017"],
    },
    "2381193": {  # PL 4045/2023 - OAB/STF
        "principal": "PL 3593/2020",
        "raiz": "PL 3593/2020",
        "cadeia": ["PL 3593/2020"],
    },
    "2396351": {  # PL 5021/2023 - Organizações terroristas
        "principal": "PL 5065/2016",
        "raiz": "PL 5065/2016",
        "cadeia": ["PL 5065/2016"],
    },
    "2399426": {  # PL 5198/2023 - ONGs estrangeiras (CADEIA CORRIGIDA!)
        "principal": "PL 736/2022",
        "raiz": "PL 4953/2016",  # ← RAIZ REAL (não é o 736/2022!)
        "cadeia": ["PL 736/2022", "PL 4953/2016"],
    },
    "2423254": {  # PL 955/2024 - Vacinação
        "principal": "PL 776/2024",
        "raiz": "PL 776/2024",
        "cadeia": ["PL 776/2024"],
    },
    "2436763": {  # PL 2098/2024 - Produtos alimentícios (CADEIA LONGA!)
        "principal": "PL 5499/2020",
        "raiz": "PL 10556/2018",  # ← RAIZ REAL
        "cadeia": ["PL 5499/2020", "PL 5344/2020", "PL 10556/2018"],
    },
    "2455562": {  # PL 3338/2024 - Direito dos pais
        "principal": "PL 2829/2023",
        "raiz": "PL 2829/2023",
        "cadeia": ["PL 2829/2023"],
    },
    "2455568": {  # PL 3341/2024 - Moeda digital/DREX
        "principal": "PL 4068/2020",
        "raiz": "PL 4068/2020",
        "cadeia": ["PL 4068/2020"],
    },
    "2462038": {  # PL 3887/2024 - CLT/Contribuição sindical
        "principal": "PL 1036/2019",
        "raiz": "PL 1036/2019",
        "cadeia": ["PL 1036/2019"],
    },
    "2485135": {  # PL 623/2025 - CPC
        "principal": "PL 606/2022",
        "raiz": "PL 606/2022",
        "cadeia": ["PL 606/2022"],
    },
    "2531615": {  # PL 3222/2025 - Prisão preventiva
        "principal": "PL 2617/2025",
        "raiz": "PL 2617/2025",
        "cadeia": ["PL 2617/2025"],
    },
    "2567301": {  # PL 4954/2025 - Maria da Penha masculina
        "principal": "PL 1500/2025",
        "raiz": "PL 1500/2025",
        "cadeia": ["PL 1500/2025"],
    },
    "2570510": {  # PL 5072/2025 - Paternidade socioafetiva
        "principal": "PL 503/2025",
        "raiz": "PL 503/2025",
        "cadeia": ["PL 503/2025"],
    },
    "2571359": {  # PL 5128/2025 - Maria da Penha/Falsas denúncias
        "principal": "PL 6198/2023",
        "raiz": "PL 6198/2023",
        "cadeia": ["PL 6198/2023"],
    },
    # === PLPs ===
    "2372482": {  # PLP 141/2023 - Inelegibilidade
        "principal": "PLP 316/2016",
        "raiz": "PLP 316/2016",
        "cadeia": ["PLP 316/2016"],
    },
    "2390310": {  # PLP (coautoria)
        "principal": "PLP 156/2012",
        "raiz": "PLP 156/2012",
        "cadeia": ["PLP 156/2012"],
    },
    "2439451": {  # PL (coautoria)
        "principal": "PL 4019/2021",
        "raiz": "PL 4019/2021",
        "cadeia": ["PL 4019/2021"],
    },
    "2483453": {  # PLP 19/2025 - Sigilo financeiro
        "principal": "PLP 235/2024",
        "raiz": "PLP 235/2024",
        "cadeia": ["PLP 235/2024"],
    },
    # === PDLs ===
    "2482260": {  # PDL 24/2025 - Susta Decreto 12.341 (PIX)
        "principal": "PDL 3/2025",
        "raiz": "PDL 3/2025",
        "cadeia": ["PDL 3/2025"],
    },
    "2482169": {  # PDL 16/2025 - Susta Decreto 12.341 (PIX)
        "principal": "PDL 3/2025",
        "raiz": "PDL 3/2025",
        "cadeia": ["PDL 3/2025"],
    },
    "2374405": {  # PDL 194/2023 - Susta Decreto armas
        "principal": "PDL 174/2023",
        "raiz": "PDL 174/2023",
        "cadeia": ["PDL 174/2023"],
    },
    "2374340": {  # PDL 189/2023 - Susta Decreto armas
        "principal": "PDL 174/2023",
        "raiz": "PDL 174/2023",
        "cadeia": ["PDL 174/2023"],
    },
    "2419264": {  # PDL 30/2024 - Susta Resolução TSE
        "principal": "PDL 3/2024",
        "raiz": "PDL 3/2024",
        "cadeia": ["PDL 3/2024"],
    },
    "2375447": {  # PDL 209/2023 - Susta Resolução ANS
        "principal": "PDL 183/2023",
        "raiz": "PDL 183/2023",
        "cadeia": ["PDL 183/2023"],
    },
    "2456691": {  # PDL 348/2024 - Susta IN banheiros
        "principal": "PDL 285/2024",
        "raiz": "PDL 285/2024",
        "cadeia": ["PDL 285/2024"],
    },
    "2390075": {  # PDL 337/2023 - Susta Resolução CONAMA
        "principal": "PDL 302/2023",
        "raiz": "PDL 302/2023",
        "cadeia": ["PDL 302/2023"],
    },
    # === PECs ===
    "2448732": {  # PEC 28/2024 - Mandado de segurança coletivo
        "principal": "PEC 8/2021",
        "raiz": "PEC 8/2021",
        "cadeia": ["PEC 8/2021"],
    },
}

# Mapeamento simples (compatibilidade): ID → PL principal imediato
MAPEAMENTO_APENSADOS = {k: v["principal"] for k, v in MAPEAMENTO_APENSADOS_COMPLETO.items()}


def buscar_id_proposicao(sigla_tipo: str, numero: str, ano: str) -> str:
    """Busca o ID de uma proposição pelo tipo/número/ano"""
    try:
        url = f"{BASE_URL}/proposicoes"
        params = {
            "siglaTipo": sigla_tipo,
            "numero": numero,
            "ano": ano,
            "itens": 1
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
        
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            if dados:
                return str(dados[0].get("id", ""))
    except:
        pass
    
    return ""


@st.cache_data(show_spinner=False, ttl=1800)
def buscar_projetos_apensados_completo(id_deputado: int) -> list:
    """
    Busca todos os projetos da deputada que estão apensados.
    
    USA MAPEAMENTO COMPLETO: vai direto para o PL RAIZ!
    
    CACHED: TTL de 30 minutos para evitar recálculo em cada rerun.
    
    Returns:
        Lista de dicionários com dados dos projetos apensados
    """
    import time
    tempo_inicio = time.time()
    # datetime já importado no topo, timezone
    
    print(f"[APENSADOS] Buscando projetos apensados (v35.1 - mapeamento completo)...")
    
    projetos_apensados = []
    
    try:
        # 1. Buscar todas as proposições da deputada
        todas_props = []
        tipos = ["PL", "PLP", "PDL", "PEC", "PRC"]
        
        for tipo in tipos:
            url = f"{BASE_URL}/proposicoes"
            params = {
                "idDeputadoAutor": id_deputado,
                "siglaTipo": tipo,
                "dataApresentacaoInicio": "2023-01-01",
                "itens": 100,
                "ordem": "DESC",
                "ordenarPor": "dataApresentacao"
            }
            
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15, verify=_REQUESTS_VERIFY)
                if resp.status_code == 200:
                    dados = resp.json().get("dados", [])
                    todas_props.extend(dados)
            except Exception as e:
                print(f"[APENSADOS] Erro ao buscar {tipo}: {e}")
            
            time.sleep(0.2)
        
        # Adicionar proposições faltantes
        id_str = str(id_deputado)
        if id_str in PROPOSICOES_FALTANTES_API:
            for prop_faltante in PROPOSICOES_FALTANTES_API[id_str]:
                ids_existentes = [str(p.get("id")) for p in todas_props]
                if str(prop_faltante.get("id")) not in ids_existentes:
                    todas_props.append(prop_faltante)
        
        print(f"[APENSADOS] Total de proposições encontradas: {len(todas_props)}")
        
        # 2. Para cada proposição, verificar se está no mapeamento
        for prop in todas_props:
            prop_id = str(prop.get("id", ""))
            sigla = prop.get("siglaTipo", "")
            numero = prop.get("numero", "")
            ano = prop.get("ano", "")
            ementa = prop.get("ementa", "")
            
            prop_nome = f"{sigla} {numero}/{ano}"
            
            # Verificar se está no mapeamento completo
            if prop_id in MAPEAMENTO_APENSADOS_COMPLETO:
                mapeamento = MAPEAMENTO_APENSADOS_COMPLETO[prop_id]
                pl_principal = mapeamento.get("principal", "")
                pl_raiz = mapeamento.get("raiz", pl_principal)
                cadeia = mapeamento.get("cadeia", [pl_principal])
                
                print(f"[APENSADOS] ✅ {prop_nome} → RAIZ: {pl_raiz}")
                if len(cadeia) > 1:
                    print(f"[APENSADOS]    Cadeia: {prop_nome} → " + " → ".join(cadeia))
                
                # Buscar ID do PL RAIZ
                match_raiz = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_raiz)
                id_raiz = ""
                if match_raiz:
                    id_raiz = buscar_id_proposicao(match_raiz.group(1), match_raiz.group(2), match_raiz.group(3))
                
                # Buscar ID do PL principal (para autor)
                match_principal = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_principal)
                id_principal = ""
                if match_principal:
                    id_principal = buscar_id_proposicao(match_principal.group(1), match_principal.group(2), match_principal.group(3))
                
                # Buscar dados do PL RAIZ
                situacao_raiz = "—"
                orgao_raiz = "—"
                relator_raiz = "—"
                ementa_raiz = "—"
                data_ultima_mov = "—"
                dias_parado = -1  # -1 = erro/sem dados (vai virar "—")
                
                if id_raiz:
                    try:
                        # Dados básicos do RAIZ
                        url_raiz = f"{BASE_URL}/proposicoes/{id_raiz}"
                        resp_raiz = requests.get(url_raiz, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
                        if resp_raiz.status_code == 200:
                            dados_raiz = resp_raiz.json().get("dados", {})
                            status_raiz = dados_raiz.get("statusProposicao", {})
                            situacao_raiz = status_raiz.get("descricaoSituacao", "—")
                            orgao_raiz = status_raiz.get("siglaOrgao", "—")
                            ementa_raiz = dados_raiz.get("ementa", "—")
                            relator_raiz = status_raiz.get("nomeRelator") or status_raiz.get("relator") or "—"
                            print(f"[APENSADOS]    Status RAIZ: situação={situacao_raiz[:40]}, órgão={orgao_raiz}, relator={relator_raiz[:30] if relator_raiz != '—' else '(vazio)'}")
                            
                            # Fallback: se relator vazio, buscar via fetch_relator_atual
                            if relator_raiz == "—" and id_raiz:
                                try:
                                    rel_dict = fetch_relator_atual(id_raiz)
                                    if rel_dict and rel_dict.get("nome"):
                                        nome = rel_dict.get("nome", "")
                                        partido = rel_dict.get("partido", "")
                                        uf = rel_dict.get("uf", "")
                                        if partido and uf:
                                            relator_raiz = f"{nome} ({partido}/{uf})"
                                        else:
                                            relator_raiz = nome
                                except:
                                    pass
                        
                        # Última tramitação do RAIZ - usando fetch_proposicao_completa
                        # v38: CORRIGIDO - Ordenar por data e filtrar "Apresentação"
                        try:
                            dados_raiz = fetch_proposicao_completa(id_raiz)
                            trams = dados_raiz.get("tramitacoes", [])
                            if trams:
                                # ============================================================
                                # v38: CORREÇÃO CRÍTICA - Encontrar a tramitação MAIS RECENTE
                                # 1. Filtrar fora eventos de "Apresentação" (são apenas protocolo)
                                # 2. Ordenar por dataHora DESC (mais recente primeiro)
                                # 3. Pegar a primeira após filtro/ordenação
                                # ============================================================
                                
                                def parse_data_tramitacao(data_hora):
                                    """Parse robusto de data ISO com timezone"""
                                    if not data_hora:
                                        return None
                                    try:
                                        if "T" in data_hora:
                                            if data_hora.endswith("Z"):
                                                return datetime.datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                                            elif "+" in data_hora or data_hora.count("-") > 2:
                                                return datetime.datetime.fromisoformat(data_hora)
                                            else:
                                                return datetime.datetime.fromisoformat(data_hora).replace(tzinfo=timezone.utc)
                                        else:
                                            return datetime.datetime.strptime(data_hora[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                    except:
                                        return None
                                
                                def is_apresentacao(descricao):
                                    """Verifica se é evento de apresentação/protocolo inicial"""
                                    if not descricao:
                                        return False
                                    desc_lower = descricao.lower()
                                    termos_apresentacao = [
                                        "apresentação", "apresentacao",
                                        "protocolado", "protocolada",
                                        "recebimento e leitura",
                                        "leitura e publicação"
                                    ]
                                    return any(termo in desc_lower for termo in termos_apresentacao)
                                
                                # Adicionar data parseada a cada tramitação
                                trams_com_data = []
                                for t in trams:
                                    dt_parsed = parse_data_tramitacao(t.get("dataHora", ""))
                                    if dt_parsed:
                                        trams_com_data.append({
                                            "dt": dt_parsed,
                                            "dataHora": t.get("dataHora", ""),
                                            "descricao": t.get("descricaoTramitacao", "") or t.get("despacho", "") or ""
                                        })
                                
                                # Ordenar por data DESC (mais recente primeiro)
                                trams_com_data.sort(key=lambda x: x["dt"], reverse=True)
                                
                                # Filtrar eventos de "Apresentação" - pegar apenas tramitações reais
                                trams_filtradas = [t for t in trams_com_data if not is_apresentacao(t["descricao"])]
                                
                                # Se sobrou alguma após filtrar, usar a mais recente
                                # Se não sobrou nenhuma, usar a mais recente de todas (fallback)
                                if trams_filtradas:
                                    tramitacao_final = trams_filtradas[0]
                                    print(f"[APENSADOS]    📅 Usando tramitação real: {tramitacao_final['descricao'][:50]}...")
                                elif trams_com_data:
                                    tramitacao_final = trams_com_data[0]
                                    print(f"[APENSADOS]    ⚠️ Fallback para Apresentação: {tramitacao_final['descricao'][:50]}...")
                                else:
                                    tramitacao_final = None
                                
                                if tramitacao_final:
                                    dt = tramitacao_final["dt"]
                                    # Garantir que tem timezone
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    
                                    data_ultima_mov = dt.strftime("%d/%m/%Y")
                                    agora = datetime.datetime.now(timezone.utc)
                                    dias_parado = (agora - dt).days
                                    print(f"[APENSADOS]    ✅ Última mov: {data_ultima_mov} ({dias_parado} dias parado)")
                                else:
                                    print(f"[APENSADOS]    ⚠️ Sem tramitações válidas")
                                    data_ultima_mov = "—"
                                    dias_parado = -1
                            else:
                                print(f"[APENSADOS]    ⚠️ Sem tramitações para {pl_raiz}")
                                data_ultima_mov = "—"
                                dias_parado = -1
                        except Exception as e_tram:
                            print(f"[APENSADOS]    ❌ ERRO buscar tramitações: {e_tram}")
                            data_ultima_mov = "—"
                            dias_parado = -1
                    except Exception as e:
                        print(f"[APENSADOS]    ❌ ERRO buscar RAIZ {pl_raiz}: {e}")
                        data_ultima_mov = "—"
                        dias_parado = -1
                
                # Buscar autor e foto do PL principal
                autor_principal = "—"
                id_autor_principal = ""
                foto_autor = ""
                ementa_principal = "—"
                
                if id_principal:
                    try:
                        url_autores = f"{BASE_URL}/proposicoes/{id_principal}/autores"
                        resp_autores = requests.get(url_autores, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
                        if resp_autores.status_code == 200:
                            autores = resp_autores.json().get("dados", [])
                            if autores:
                                autor_principal = autores[0].get("nome", "—")
                                uri_autor = autores[0].get("uri", "")
                                if "/deputados/" in uri_autor:
                                    id_autor_principal = uri_autor.split("/deputados/")[-1].split("?")[0]
                                    if id_autor_principal:
                                        foto_autor = f"https://www.camara.leg.br/internet/deputado/bandep/{id_autor_principal}.jpg"
                        
                        url_det = f"{BASE_URL}/proposicoes/{id_principal}"
                        resp_det = requests.get(url_det, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
                        if resp_det.status_code == 200:
                            dados_det = resp_det.json().get("dados", {})
                            ementa_principal = dados_det.get("ementa", "—")
                    except:
                        pass
                
                # Buscar ementa da proposição Zanatta
                if not ementa:
                    try:
                        url_zanatta = f"{BASE_URL}/proposicoes/{prop_id}"
                        resp_zanatta = requests.get(url_zanatta, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
                        if resp_zanatta.status_code == 200:
                            ementa = resp_zanatta.json().get("dados", {}).get("ementa", "")
                    except:
                        pass
                
                # Construir cadeia formatada
                cadeia_formatada = [{"pl": pl, "id": ""} for pl in cadeia]
                
                projetos_apensados.append({
                    "pl_zanatta": prop_nome,
                    "id_zanatta": prop_id,
                    "ementa_zanatta": ementa[:200] + "..." if len(ementa) > 200 else ementa,
                    "pl_principal": pl_principal,
                    "id_principal": id_principal,
                    "autor_principal": autor_principal,
                    "id_autor_principal": id_autor_principal,
                    "foto_autor": foto_autor,
                    "ementa_principal": ementa_principal[:200] + "..." if len(ementa_principal) > 200 else ementa_principal,
                    "pl_raiz": pl_raiz,
                    "id_raiz": id_raiz,
                    "situacao_raiz": situacao_raiz,
                    "orgao_raiz": orgao_raiz,
                    "relator_raiz": relator_raiz,
                    "data_ultima_mov": data_ultima_mov,
                    "dias_parado": dias_parado,
                    "ementa_raiz": ementa_raiz[:200] if ementa_raiz else "—",
                    "cadeia_apensamento": cadeia_formatada,
                })
            else:
                # Verificar se está apensado mas não está no mapeamento
                try:
                    url_detalhe = f"{BASE_URL}/proposicoes/{prop_id}"
                    resp_det = requests.get(url_detalhe, headers=HEADERS, timeout=15, verify=_REQUESTS_VERIFY)
                    
                    if resp_det.status_code == 200:
                        dados_prop = resp_det.json().get("dados", {})
                        status = dados_prop.get("statusProposicao", {})
                        situacao = status.get("descricaoSituacao", "")
                        
                        situacao_lower = situacao.lower()
                        if "tramitando em conjunto" in situacao_lower or "apensad" in situacao_lower:
                            print(f"[APENSADOS] ⚠️ {prop_nome} NÃO ESTÁ NO MAPEAMENTO!")
                except:
                    pass
            
            time.sleep(0.1)
        
        print(f"[APENSADOS] ✅ Total: {len(projetos_apensados)}")
        tempo_total = time.time() - tempo_inicio
        print(f"[APENSADOS] ⏱️ Tempo total: {tempo_total:.1f}s para {len(projetos_apensados)} projetos")
        return projetos_apensados
    
    except Exception as e:
        print(f"[APENSADOS] ❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return []


# Alias para compatibilidade
def buscar_projetos_apensados_automatico(id_deputado: int) -> list:
    """Alias para buscar_projetos_apensados_completo"""
    return buscar_projetos_apensados_completo(id_deputado)





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


# ============================================================
# APENSAÇÕES / TRAMITAÇÃO EM CONJUNTO — utilitários
# ============================================================
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
    st.caption("v41⚠️ - SISTEMA EM INTEGRAÇÃO E MANUTENÇÃO - PODE FICAR INSTÁVEL")

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
    # ABA 8 - RECEBER NOTIFICAÇÕES Virou aba 9 com a integração 08/02/2026
    # ============================================================
    with tab9:
        _set_aba_atual(9)
        from modules.tabs.tab9_notificacao import render_tab9
        render_tab9()        

    # ============================================================
    # ============================================================
    # ABA 9 - PROJETOS APENSADOS - Virou aba 8 com a integração 08/02/2026
    # ============================================================
    with tab8:
        _set_aba_atual(8)
        from modules.tabs.tab8_apensados import render_tab8
        render_tab8(provider, exibir_detalhes_proposicao, id_deputada)
        
               
        st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")

    st.markdown("---")

if __name__ == "__main__":
    main()