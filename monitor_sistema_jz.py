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

def buscar_detalhes_senado(codigo_materia: str, debug: bool = False) -> Optional[Dict]:
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

    if not codigo_materia:
        return None

    resultado = {
        "relator_senado": "",
        "relator_nome": "",
        "relator_partido": "",
        "relator_uf": "",
        "orgao_senado_sigla": "",
        "orgao_senado_nome": "",
    }

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

def formatar_movimentacoes_senado(movimentacoes: List[Dict]) -> str:
    """
    Formata lista de movimentações em string para exibição.
    """
    if not movimentacoes:
        return "Sem movimentações disponíveis"


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
            detalhes = buscar_detalhes_senado(codigo_materia, debug=debug)
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


def processar_lista_com_senado(
    df_proposicoes: pd.DataFrame,
    debug: bool = False,
    mostrar_progresso: bool = True
) -> pd.DataFrame:
    """
    Processa lista de proposições e enriquece com dados do Senado quando necessário.
    APENAS ABA 5 PODE CHAMAR ESTA FUNÇÃO.
    """
    # ============================================================
    # GATE: Apenas Aba 5 pode chamar
    # ============================================================
    if not _pode_chamar_senado():
        import inspect
        caller = inspect.stack()[1]
        print(f"[SENADO-GATE] ❌ BLOQUEADO - Chamada de {caller.function} (linha {caller.lineno})")
        print(f"[SENADO-GATE] ℹ️ Senado só permitido na Aba 5. Aba atual: {st.session_state.get('aba_atual_senado', None)}")
        # Retornar DataFrame sem modificações
        return df_proposicoes.copy() if not df_proposicoes.empty else df_proposicoes
    
    # Docstring da função
    """
    Processa um DataFrame de proposições, adicionando informações do Senado.
    
    REGRA: Só consulta o Senado para proposições com situação "Apreciação pelo Senado Federal".
    IMPORTANTE: Preserva TODAS as colunas originais do DataFrame!
    
    Args:
        df_proposicoes: DataFrame com proposições da Câmara
        debug: Modo debug
        mostrar_progresso: Mostrar barra de progresso
        
    Returns:
        DataFrame enriquecido (colunas originais + colunas do Senado)
    """
    if df_proposicoes.empty:
        return df_proposicoes
    
    # IMPORTANTE: Guardar lista de colunas originais
    colunas_originais = df_proposicoes.columns.tolist()
    
    # Converter para lista de dicts
    proposicoes_list = df_proposicoes.to_dict('records')
    
    # Processar
    if mostrar_progresso and len(proposicoes_list) > 1:
        progress_bar = st.progress(0)
        status_text = st.empty()
    else:
        progress_bar = None
        status_text = None
    
    proposicoes_enriquecidas = []
    total = len(proposicoes_list)
    erros_api = 0
    
    for i, prop in enumerate(proposicoes_list):
        try:
            if progress_bar:
                progress_bar.progress((i + 1) / total)
                status_text.text(f"Verificando proposição {i+1} de {total}...")
            
            prop_enriquecida = enriquecer_proposicao_com_senado(prop, debug=debug)
            proposicoes_enriquecidas.append(prop_enriquecida)
            
            if i < total - 1:
                time.sleep(0.1)
        except Exception as e:
            # LOG: Erro ao processar proposição específica
            print(f"[SENADO] ❌ Erro ao processar proposição {i+1}: {str(e)}")
            erros_api += 1
            # Adiciona a proposição original sem dados do Senado
            prop_original = prop.copy()
            prop_original["no_senado"] = False
            prop_original["situacao_senado"] = "Sem dados do Senado (falha na consulta)"
            prop_original["url_senado"] = ""
            prop_original["tipo_numero_senado"] = ""
            proposicoes_enriquecidas.append(prop_original)
    
    if progress_bar:
        progress_bar.empty()
        status_text.empty()
    
    # Converter de volta
    df_enriquecido = pd.DataFrame(proposicoes_enriquecidas)
    
    # IMPORTANTE: Garantir que todas as colunas originais estão presentes
    for col in colunas_originais:
        if col not in df_enriquecido.columns:
            df_enriquecido[col] = ""
    
    # Contar
    if "no_senado" in df_enriquecido.columns:
        total_senado = df_enriquecido["no_senado"].sum()
        if total_senado > 0:
            st.success(f"✅ {total_senado} proposição(ões) encontrada(s) tramitando no Senado")
        else:
            st.info("ℹ️ Nenhuma proposição encontrada no Senado")
    
    # Informar sobre erros
    if erros_api > 0:
        st.warning(f"⚠️ {erros_api} proposição(ões) com falha na consulta ao Senado")
    
    return df_enriquecido

# Fim das funções de integração com Senado Federal

# ============================================================
# Monitor Legislativo – Dep. Júlia Zanatta (Streamlit)
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
# - Monitoramento de logins (Telegram + Google Sheets)
# - Suporte a múltiplas senhas por usuário
# - [v27] PDF Linha do Tempo com identificação da matéria no topo
# - [v27] Situação removida dos blocos individuais (fica só no cabeçalho)
# - [v27] Registro de downloads de relatórios (Telegram + Google Sheets)
# - [v29] Aviso de manutenção removido (sistema normalizado)
# - [v30] 🎨 TELA DE LOGIN PROFISSIONAL com design moderno e gradiente
# - [v30] 🏛️ INTEGRAÇÃO COMPLETA COM API DO SENADO FEDERAL  
# - [v30] 📊 NOVA ABA: Monitoramento de matérias no Senado
# - [v30] 🔍 Busca por menções, autoria e palavras-chave no Senado
# - [v30] 📈 Filtros avançados e exportação (CSV/Excel) para dados do Senado
# - [v30.1] 🔧 AUDITORIA COMPLETA: Tratamento robusto de erros API Senado
# - [v30.1] ✅ Validação de respostas, timeouts, mensagens claras, modo debug
# ============================================================


matplotlib.use('Agg')  # Backend não-interativo



# Função para cadastrar email via GitHub API
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


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_materias_senado(termo_busca: str = "Julia Zanatta", limite: int = 50, debug: bool = False) -> pd.DataFrame:
    """
    Busca matérias no Senado Federal que mencionam o termo especificado.
    VERSÃO AUDITADA E CORRIGIDA com tratamento robusto de erros.
    
    Args:
        termo_busca: Termo para buscar (padrão: "Julia Zanatta")
        limite: Número máximo de resultados
        debug: Se True, mostra mensagens de debug
        
    Returns:
        DataFrame com as matérias encontradas (vazio se nenhuma encontrada ou erro)
    """
    if debug:
        st.info(f"🔍 Debug: Buscando '{termo_busca}' no Senado...")
    
    try:
        url = "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista"
        
        params = {
            "texto": termo_busca,
            "tramitando": "S",
            "formato": "json"
        }
        
        if debug:
            st.write(f"URL: {url}")
            st.write(f"Params: {params}")
        
        # Fazer requisição com timeout adequado
        try:
            response = requests.get(url, params=params, timeout=30, headers={
                'User-Agent': 'Monitor-Zanatta/1.0',
                'Accept': 'application/json'
            })
        except requests.exceptions.Timeout:
            st.warning("⏱️ A API do Senado demorou muito para responder. Tente novamente.")
            return pd.DataFrame()
        except requests.exceptions.ConnectionError:
            st.warning("🌐 Não foi possível conectar à API do Senado. Verifique sua conexão.")
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"❌ Erro de conexão: {str(e)}")
            return pd.DataFrame()
        
        # Validar resposta
        valida, msg_erro = validar_resposta_api(response)
        if not valida:
            st.warning(f"⚠️ Problema com a resposta da API: {msg_erro}")
            if debug:
                st.write(f"Status: {response.status_code}")
                st.write(f"Headers: {dict(response.headers)}")
                st.write(f"Content (primeiros 500 chars): {response.text[:500]}")
            return pd.DataFrame()
        
        # Parsear JSON
        try:
            data = response.json()
        except ValueError as e:
            st.warning(f"❌ Erro ao processar resposta do Senado: {str(e)}")
            return pd.DataFrame()
        
        if debug:
            st.write(f"Estrutura JSON recebida: {list(data.keys())}")
        
        # Processar resultados
        materias = []
        
        # Verificar estrutura esperada
        if "PesquisaBasicaMateria" not in data:
            st.info("ℹ️ A API do Senado não retornou resultados no formato esperado.")
            if debug:
                st.json(data)
            return pd.DataFrame()
        
        pesquisa = data["PesquisaBasicaMateria"]
        
        # Verificar se há matérias
        if "Materias" not in pesquisa:
            st.info(f"ℹ️ Nenhuma matéria encontrada para '{termo_busca}'")
            return pd.DataFrame()
        
        if "Materia" not in pesquisa["Materias"]:
            st.info(f"ℹ️ Nenhuma matéria encontrada para '{termo_busca}'")
            return pd.DataFrame()
        
        materias_raw = pesquisa["Materias"]["Materia"]
        
        # Garantir que é lista
        if not isinstance(materias_raw, list):
            materias_raw = [materias_raw]
        
        if debug:
            st.write(f"Total de matérias encontradas: {len(materias_raw)}")
        
        # Processar cada matéria
        for i, m in enumerate(materias_raw[:limite]):
            try:
                identificacao = m.get("IdentificacaoMateria", {})
                dados_basicos = m.get("DadosBasicosMateria", {})
                
                # Extrair autoria com segurança
                autoria = dados_basicos.get("AutoriaPrincipal", {})
                nome_autor = ""
                if isinstance(autoria, dict):
                    nome_autor = autoria.get("NomeAutor", "")
                
                materia_info = {
                    "Codigo": str(identificacao.get("CodigoMateria", "")),
                    "Sigla": str(identificacao.get("SiglaSubtipoMateria", "")).upper(),
                    "Numero": str(identificacao.get("NumeroMateria", "")),
                    "Ano": str(identificacao.get("AnoMateria", "")),
                    "Ementa": str(dados_basicos.get("EmentaMateria", ""))[:500],  # Limitar tamanho
                    "Autor": nome_autor,
                    "Data": str(dados_basicos.get("DataApresentacao", "")),
                    "Casa": str(dados_basicos.get("NomeCasaIdentificacaoMateria", "")),
                    "URL": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{identificacao.get('CodigoMateria', '')}"
                }
                
                materias.append(materia_info)
                
            except Exception as e:
                if debug:
                    st.warning(f"Erro ao processar matéria {i+1}: {str(e)}")
                continue
        
        # Verificar se encontrou algo
        if not materias:
            st.info(f"ℹ️ Nenhuma matéria processada com sucesso para '{termo_busca}'")
            return pd.DataFrame()
        
        # Criar DataFrame
        df = pd.DataFrame(materias)
        
        # Criar coluna de proposição
        if all(c in df.columns for c in ["Sigla", "Numero", "Ano"]):
            df["Proposicao"] = df["Sigla"] + " " + df["Numero"] + "/" + df["Ano"]
        
        if debug:
            st.success(f"✅ {len(df)} matérias processadas com sucesso")
        
        return df
        
    except Exception as e:
        # Erro genérico - não mostrar detalhes técnicos ao usuário
        st.error(f"❌ Erro inesperado ao buscar no Senado: {type(e).__name__}")
        if debug:
            st.exception(e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_autoria_senado(nome_autor: str = "Julia Zanatta", debug: bool = False) -> pd.DataFrame:
    """
    Busca proposições de autoria específica no Senado.
    VERSÃO AUDITADA E CORRIGIDA.
    
    Args:
        nome_autor: Nome do autor para buscar
        debug: Se True, mostra mensagens de debug
        
    Returns:
        DataFrame com proposições do autor
    """
    if debug:
        st.info(f"🔍 Debug: Buscando autoria de '{nome_autor}' no Senado...")
    
    try:
        url = "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista"
        
        params = {
            "autor": nome_autor,
            "tramitando": "S",
            "formato": "json"
        }
        
        # Fazer requisição
        try:
            response = requests.get(url, params=params, timeout=30, headers={
                'User-Agent': 'Monitor-Zanatta/1.0',
                'Accept': 'application/json'
            })
        except requests.exceptions.Timeout:
            st.warning("⏱️ A API do Senado demorou muito para responder.")
            return pd.DataFrame()
        except requests.exceptions.ConnectionError:
            st.warning("🌐 Não foi possível conectar à API do Senado.")
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"❌ Erro de conexão: {str(e)}")
            return pd.DataFrame()
        
        # Validar resposta
        valida, msg_erro = validar_resposta_api(response)
        if not valida:
            st.warning(f"⚠️ {msg_erro}")
            return pd.DataFrame()
        
        # Parsear JSON
        data = response.json()
        
        # Processar resultados (similar à função anterior)
        materias = []
        
        if "PesquisaBasicaMateria" not in data:
            st.info(f"ℹ️ Nenhuma proposição de autoria encontrada para '{nome_autor}'")
            return pd.DataFrame()
        
        pesquisa = data["PesquisaBasicaMateria"]
        
        if "Materias" not in pesquisa or "Materia" not in pesquisa["Materias"]:
            st.info(f"ℹ️ Nenhuma proposição de autoria encontrada para '{nome_autor}'")
            return pd.DataFrame()
        
        materias_raw = pesquisa["Materias"]["Materia"]
        
        if not isinstance(materias_raw, list):
            materias_raw = [materias_raw]
        
        for m in materias_raw:
            try:
                identificacao = m.get("IdentificacaoMateria", {})
                dados_basicos = m.get("DadosBasicosMateria", {})
                
                materia_info = {
                    "Codigo": str(identificacao.get("CodigoMateria", "")),
                    "Tipo": str(identificacao.get("SiglaSubtipoMateria", "")).upper(),
                    "Numero": str(identificacao.get("NumeroMateria", "")),
                    "Ano": str(identificacao.get("AnoMateria", "")),
                    "Ementa": str(dados_basicos.get("EmentaMateria", ""))[:500],
                    "Data": str(dados_basicos.get("DataApresentacao", "")),
                    "Situacao": str(dados_basicos.get("DescricaoIdentificacaoMateria", "")),
                    "URL": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{identificacao.get('CodigoMateria', '')}"
                }
                
                materias.append(materia_info)
            except Exception:
                continue
        
        if not materias:
            st.info(f"ℹ️ Nenhuma proposição de autoria processada para '{nome_autor}'")
            return pd.DataFrame()
        
        df = pd.DataFrame(materias)
        
        if all(c in df.columns for c in ["Tipo", "Numero", "Ano"]):
            df["Proposicao"] = df["Tipo"] + " " + df["Numero"] + "/" + df["Ano"]
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro inesperado: {type(e).__name__}")
        if debug:
            st.exception(e)
        return pd.DataFrame()


# Fim das funções corrigidas


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


def _legacy_get_brasilia_now():
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
        # === OUTROS PROJETOS FALTANTES ===
        {"id": "2347150", "siglaTipo": "PL", "numero": "321", "ano": "2023"},    # PL 321/2023 (no Senado)
        {"id": "2381193", "siglaTipo": "PL", "numero": "4045", "ano": "2023"},   # PL 4045/2023
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


def buscar_cadeia_apensamentos(id_proposicao: str, max_niveis: int = 10) -> list:
    """
    Busca a cadeia completa de apensamentos até o PL raiz.
    
    Ex: PL 2098/2024 → PL 5499/2020 → PL 5344/2020 → PL 10556/2018 (raiz)
    
    Returns:
        Lista de dicionários com {pl, id, situacao} de cada nível (incluindo o inicial)
    """
    
    cadeia = []
    id_atual = id_proposicao
    visitados = set()
    
    for nivel in range(max_niveis):
        if not id_atual or id_atual in visitados:
            break
        
        visitados.add(id_atual)
        
        try:
            # Buscar dados da proposição
            url = f"{BASE_URL}/proposicoes/{id_atual}"
            resp = requests.get(url, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
            
            if resp.status_code != 200:
                break
            
            dados = resp.json().get("dados", {})
            status = dados.get("statusProposicao", {})
            situacao = status.get("descricaoSituacao", "")
            
            sigla = dados.get("siglaTipo", "")
            numero = dados.get("numero", "")
            ano = dados.get("ano", "")
            pl_nome = f"{sigla} {numero}/{ano}"
            
            cadeia.append({
                "pl": pl_nome,
                "id": id_atual,
                "situacao": situacao,
                "nivel": nivel
            })
            
            # Verificar se está apensado a outro
            situacao_lower = situacao.lower()
            if "tramitando em conjunto" not in situacao_lower and "apensad" not in situacao_lower:
                # Este é o PL raiz - parar aqui
                print(f"[CADEIA] Nível {nivel}: {pl_nome} é o PL RAIZ (situação: {situacao[:50]})")
                break
            
            print(f"[CADEIA] Nível {nivel}: {pl_nome} está apensado, buscando próximo...")
            
            # Buscar o próximo nível - primeiro verificar se está no dicionário
            proximo_id = None
            
            if id_atual in MAPEAMENTO_APENSADOS:
                pl_pai = MAPEAMENTO_APENSADOS[id_atual]
                match = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_pai)
                if match:
                    proximo_id = buscar_id_proposicao(match.group(1), match.group(2), match.group(3))
                    if proximo_id:
                        print(f"[CADEIA]    → Próximo (dicionário): {pl_pai}")
            
            if not proximo_id:
                # Buscar nas tramitações
                url_tram = f"{BASE_URL}/proposicoes/{id_atual}/tramitacoes"
                resp_tram = requests.get(url_tram, params={"itens": 50, "ordem": "DESC"}, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
                
                if resp_tram.status_code == 200:
                    tramitacoes = resp_tram.json().get("dados", [])
                    
                    for tram in tramitacoes:
                        texto = " ".join([
                            str(tram.get("despacho", "") or ""),
                            str(tram.get("descricaoTramitacao", "") or ""),
                        ])
                        
                        # Procurar padrão "Apense-se à(ao) PL X"
                        patterns = [
                            r'[Aa]pense-se\s+[àa](?:\(ao\))?\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
                            r'[Aa]pensad[oa]\s+(?:à|ao|a)\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, texto, re.IGNORECASE)
                            if match:
                                tipo = match.group(1).upper()
                                num = match.group(2)
                                ano_pl = match.group(3)
                                pl_pai = f"{tipo} {num}/{ano_pl}"
                                
                                proximo_id = buscar_id_proposicao(tipo, num, ano_pl)
                                if proximo_id:
                                    print(f"[CADEIA]    → Próximo (tramitações): {pl_pai}")
                                    break
                        
                        if proximo_id:
                            break
            
            if proximo_id and proximo_id not in visitados:
                id_atual = proximo_id
            else:
                break
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"[CADEIA] Erro ao buscar nível {nivel}: {e}")
            break
    
    return cadeia


def buscar_dados_pl_raiz(id_raiz: str) -> dict:
    """
    Busca dados completos do PL raiz (última tramitação, relator, situação).
    """
    # datetime já importado no topo, timezone
    
    dados = {
        "situacao": "—",
        "orgao": "—",
        "relator": "—",
        "data_ultima_mov": "—",
        "dias_parado": 0,
        "ementa": "—",
    }
    
    if not id_raiz:
        return dados
    
    try:
        # Buscar dados básicos
        url = f"{BASE_URL}/proposicoes/{id_raiz}"
        resp = requests.get(url, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
        
        if resp.status_code == 200:
            prop = resp.json().get("dados", {})
            status = prop.get("statusProposicao", {})
            dados["situacao"] = status.get("descricaoSituacao", "—")
            dados["orgao"] = status.get("siglaOrgao", "—")
            dados["ementa"] = prop.get("ementa", "—")
            
            # Relator
            relator_nome = status.get("nomeRelator") or status.get("relator")
            if relator_nome:
                dados["relator"] = relator_nome
        
        # Buscar última tramitação
        url_tram = f"{BASE_URL}/proposicoes/{id_raiz}/tramitacoes"
        resp_tram = requests.get(url_tram, params={"itens": 1, "ordem": "DESC", "ordenarPor": "dataHora"}, headers=HEADERS, timeout=10, verify=_REQUESTS_VERIFY)
        
        if resp_tram.status_code == 200:
            tramitacoes = resp_tram.json().get("dados", [])
            if tramitacoes:
                data_hora = tramitacoes[0].get("dataHora", "")
                if data_hora:
                    try:
                        # Tentar diferentes formatos
                        if "T" in data_hora:
                            dt = datetime.datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                        else:
                            dt = datetime.datetime.strptime(data_hora[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        
                        dados["data_ultima_mov"] = dt.strftime("%d/%m/%Y")
                        agora = datetime.datetime.now(timezone.utc)
                        dados["dias_parado"] = (agora - dt).days
                    except:
                        dados["data_ultima_mov"] = data_hora[:10] if data_hora else "—"
    
    except Exception as e:
        print(f"[PL_RAIZ] Erro ao buscar dados: {e}")
    
    return dados


def extrair_pl_principal_do_texto(texto: str) -> dict:
    """
    Extrai o PL principal de um texto de despacho/tramitação.
    
    Args:
        texto: Texto contendo "Apense-se à(ao) PL X" ou similar
    
    Returns:
        Dict com {pl_principal, tipo, numero, ano} ou None
    """
    
    patterns = [
        r'[Aa]pense-se\s+[àa](?:\(ao\))?\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
        r'[Aa]pensad[oa]\s+(?:à|ao|a)\s*(?:\(ao\))?\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
        r'[Aa]pensad[oa]\s+[àa](?:\(ao\))?\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            tipo = match.group(1).upper()
            numero = match.group(2)
            ano = match.group(3)
            return {
                "pl_principal": f"{tipo} {numero}/{ano}",
                "tipo": tipo,
                "numero": numero,
                "ano": ano
            }
    
    return None


def buscar_pl_principal_nas_tramitacoes(prop_id: str) -> str:
    """
    Busca nas tramitações de uma proposição para encontrar o PL principal.
    
    Usa como fallback quando não existe no dicionário de mapeamentos.
    
    Returns:
        String com PL principal (ex: "PL 1234/2023") ou None
    """
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}/tramitacoes"
        params = {"itens": 30, "ordem": "DESC", "ordenarPor": "dataHora"}
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15, verify=_REQUESTS_VERIFY)
        
        if resp.status_code != 200:
            return None
        
        tramitacoes = resp.json().get("dados", [])
        
        for tram in tramitacoes:
            # Concatenar todos os campos de texto
            texto = " ".join([
                str(tram.get("despacho", "") or ""),
                str(tram.get("descricaoTramitacao", "") or ""),
                str(tram.get("descricaoSituacao", "") or ""),
            ])
            
            resultado = extrair_pl_principal_do_texto(texto)
            if resultado:
                return resultado["pl_principal"]
        
        return None
    
    except Exception as e:
        print(f"[APENSADOS] Erro ao buscar tramitações de {prop_id}: {e}")
        return None


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



def default_anos_sel(anos: list) -> list:
    """Define anos padrão do filtro garantindo que 2023 apareça (ex.: PL 321/2023).

    Regra: pega os 3 anos mais recentes disponíveis + 2023 (se existir no dataset).
    """
    anos_clean = [str(a).strip() for a in (anos or []) if str(a).strip().isdigit()]
    if not anos_clean:
        return []

    # Preferir anos mais recentes (do próprio dataset)
    anos_sorted = sorted(set(anos_clean), reverse=True)
    top3 = anos_sorted[:3]

    defaults = []
    for a in top3:
        if a in anos_sorted and a not in defaults:
            defaults.append(a)
    if "2023" in anos_sorted and "2023" not in defaults:
        defaults.append("2023")

    # fallback (nunca vazio)
    return defaults or (anos_sorted[:3] if len(anos_sorted) >= 3 else anos_sorted)
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


def _legacy_normalize_ministerio(texto: str) -> str:
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


def _legacy_canonical_situacao(situacao: str) -> str:
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

def _legacy_normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


def _legacy_format_sigla_num_ano(sigla, numero, ano) -> str:
    sigla = (sigla or "").strip()
    numero = (str(numero) or "").strip()
    ano = (str(ano) or "").strip()
    if sigla and numero and ano:
        return f"{sigla} {numero}/{ano}"
    return ""


def _legacy_extract_id_from_uri(uri: str):
    if not uri:
        return None
    try:
        path = urlparse(uri).path.rstrip("/")
        return path.split("/")[-1]
    except Exception:
        return None


def _legacy_is_comissao_estrategica(sigla_orgao, lista_siglas):
    if not sigla_orgao:
        return False
    return sigla_orgao.upper() in [s.upper() for s in lista_siglas]


def _legacy_parse_dt(iso_str: str):
    return pd.to_datetime(iso_str, errors="coerce", utc=False)


def _legacy_days_since(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return None
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    today = pd.Timestamp(datetime.date.today())
    return int((today - d.normalize()).days)


def _legacy_fmt_dt_br(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return "—"
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    return d.strftime("%d/%m/%Y %H:%M")


def _legacy_camara_link_tramitacao(id_proposicao: str) -> str:
    pid = str(id_proposicao).strip()
    return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"


def _legacy_camara_link_deputado(id_deputado: str) -> str:
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

def _legacy_proximo_dia_util(dt: datetime.date) -> datetime.date:
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


def _legacy_ajustar_para_dia_util(dt: datetime.date) -> datetime.date:
    """
    Se a data cair em fim de semana, retorna o próximo dia útil.
    Caso contrário, retorna a própria data.
    """
    if dt is None:
        return None
    while dt.weekday() in (5, 6):
        dt += datetime.timedelta(days=1)
    return dt


def _legacy_calcular_prazo_ric(data_remessa: datetime.date) -> tuple:
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


def _legacy_contar_dias_uteis(data_inicio: datetime.date, data_fim: datetime.date) -> int:
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


def _legacy_parse_prazo_resposta_ric(tramitacoes: list, situacao_atual: str = "") -> dict:
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


def _legacy_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> tuple[bytes, str, str]:
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


def _legacy_sanitize_text_pdf(text: str) -> str:
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


def _legacy_verificar_relator_adversario(relator_str: str) -> tuple:
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


def _legacy_obter_situacao_com_fallback(row: pd.Series) -> str:
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


def _legacy_categorizar_situacao_para_ordenacao(situacao: str) -> tuple:
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
    # 2. Aguardando Parecer
    if 'aguardando parecer' in s:
        return (2, "Aguardando Parecer", situacao)
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


def _legacy_to_pdf_bytes(df: pd.DataFrame, subtitulo: str = "Relatório") -> tuple:
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


def _legacy_to_pdf_linha_do_tempo(df: pd.DataFrame, proposicao_info: dict) -> tuple:
    """
    Exporta DataFrame de linha do tempo para PDF com cabeçalho destacando a proposição.
    
    Args:
        df: DataFrame com as tramitações (Data, Hora, Órgão, Tramitação)
        proposicao_info: Dict com informações da proposição:
            - proposicao: "PL 5701/2025"
            - situacao: "Aguardando Designação de Relator(a)"
            - orgao: "CFT"
            - regime: "Ordinário" (opcional)
            - id: "2582078"
    
    Returns:
        tuple: (bytes, mime_type, extensão)
    """
    try:
        from fpdf import FPDF
        
        proposicao = proposicao_info.get("proposicao", "")
        situacao = proposicao_info.get("situacao", "—")
        orgao = proposicao_info.get("orgao", "—")
        regime = proposicao_info.get("regime", "")
        prop_id = proposicao_info.get("id", "")
        
        class RelatorioLinhaDoTempoPDF(FPDF):
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
        
        pdf = RelatorioLinhaDoTempoPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Título: Linha do Tempo
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, f"Linha do Tempo - ID {prop_id}", ln=True, align='C')
        
        # Data de geração
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # Fonte
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Ultima tramitacao (mais recente primeiro)", ln=True, align='C')
        
        # Linha separadora
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # ============================================================
        # BLOCO DE IDENTIFICAÇÃO DA MATÉRIA (EM DESTAQUE)
        # ============================================================
        
        # Proposição (destaque principal)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, sanitize_text_pdf(proposicao) if proposicao else "—", ln=True, align='C')
        
        # Situação atual (em destaque)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Situacao atual:", ln=True, align='C')
        
        # Cor da situação baseada no texto
        pdf.set_font('Helvetica', 'B', 11)
        if 'Arquiv' in situacao:
            pdf.set_text_color(150, 50, 50)  # Vermelho
        elif 'Pronta' in situacao or 'Sancion' in situacao:
            pdf.set_text_color(50, 150, 50)  # Verde
        elif 'Aguardando' in situacao:
            pdf.set_text_color(50, 50, 150)  # Azul
        else:
            pdf.set_text_color(80, 80, 80)  # Cinza
        pdf.cell(0, 7, sanitize_text_pdf(situacao)[:80], ln=True, align='C')
        
        # Órgão atual
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Orgao: {sanitize_text_pdf(orgao)}", ln=True, align='C')
        
        # Regime de tramitação (se disponível)
        if regime:
            pdf.cell(0, 6, f"Regime: {sanitize_text_pdf(regime)}", ln=True, align='C')
        
        pdf.ln(4)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # ============================================================
        # TRAMITAÇÕES (SEM CAMPO "SITUAÇÃO" EM CADA BLOCO)
        # ============================================================
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True)
        pdf.ln(3)
        
        for idx, (_, row) in enumerate(df.iterrows()):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(30)
            
            # Número do registro (badge)
            pdf.set_fill_color(0, 51, 102)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(8, 6, str(idx + 1), fill=True, align='C')
            pdf.ln(8)
            
            pdf.set_x(20)
            
            # Última tramitação (data/hora)
            data_val = row.get("Data", "—")
            hora_val = row.get("Hora", "")
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(35, 5, "Ultima tramitacao: ", ln=False)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(0, 0, 0)
            data_hora_str = f"{data_val}"
            if hora_val:
                data_hora_str += f" {hora_val}"
            pdf.cell(0, 5, sanitize_text_pdf(data_hora_str)[:30], ln=True)
            pdf.set_x(20)
            
            # Calcular "Parado há (dias)" baseado na data
            dias_parado = None
            try:
                if data_val and data_val != "—":
                    dt_tram = datetime.datetime.strptime(data_val, "%d/%m/%Y")
                    hoje = datetime.datetime.now()
                    dias_parado = (hoje - dt_tram).days
            except:
                pass
            
            if dias_parado is not None:
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(28, 5, "Parado ha (dias): ", ln=False)
                pdf.set_font('Helvetica', 'B', 9)
                if dias_parado >= 30:
                    pdf.set_text_color(180, 50, 50)  # Vermelho
                elif dias_parado >= 15:
                    pdf.set_text_color(200, 120, 0)  # Laranja
                elif dias_parado >= 7:
                    pdf.set_text_color(180, 180, 0)  # Amarelo
                else:
                    pdf.set_text_color(50, 150, 50)  # Verde
                pdf.cell(0, 5, str(dias_parado), ln=True)
                pdf.set_x(20)
            
            # Órgão
            orgao_val = row.get("Órgão", "—")
            if orgao_val and orgao_val != "—":
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(15, 5, "Orgao: ", ln=False)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, sanitize_text_pdf(str(orgao_val))[:50], ln=True)
                pdf.set_x(20)
            
            # Relator - mantido como "Sem relator designado" por padrão na linha do tempo
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 5, "Relator(a): ", ln=False)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, "Sem relator designado", ln=True)
            pdf.set_x(20)
            
            # Descrição da tramitação (se houver)
            tramitacao = row.get("Tramitação", "")
            if tramitacao and str(tramitacao).strip():
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(22, 5, "Tramitacao: ", ln=False)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(60, 60, 60)
                
                # Quebrar texto longo
                texto_tram = sanitize_text_pdf(str(tramitacao))[:200]
                pdf.multi_cell(160, 4, texto_tram)
            
            pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except ImportError:
        raise Exception("Biblioteca fpdf2 não disponível. Instale com: pip install fpdf2")
    except Exception as e:
        import traceback
        raise Exception(f"Erro ao gerar PDF da Linha do Tempo: {str(e)} | Traceback: {traceback.format_exc()}")


def _legacy_to_pdf_autoria_relatoria(df: pd.DataFrame) -> tuple[bytes, str, str]:
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


def _legacy_to_pdf_comissoes_estrategicas(df: pd.DataFrame) -> tuple[bytes, str, str]:
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


def _legacy_to_pdf_palavras_chave(df: pd.DataFrame) -> tuple[bytes, str, str]:
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


def _legacy_to_pdf_rics_por_status(df: pd.DataFrame, titulo: str = "RICs - Requerimentos de Informação") -> tuple[bytes, str, str]:
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


def _legacy_party_norm(sigla: str) -> str:
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


# ============================================================
# APENSAÇÕES / TRAMITAÇÃO EM CONJUNTO — utilitários
# ============================================================
@st.cache_data(show_spinner=False, ttl=1800)
def fetch_proposicao_relacionadas(id_proposicao: str) -> list:
    """Retorna relações/apensações da proposição (API Câmara /relacionadas)."""
    if not id_proposicao:
        return []
    url = f"{BASE_URL}/proposicoes/{id_proposicao}/relacionadas"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("dados", []) or []
        return []
    except Exception:
        return []


def get_proposicao_principal_id(id_proposicao: str):
    """Descobre a proposição principal à qual esta está apensada (se houver)."""
    dados = fetch_proposicao_relacionadas(str(id_proposicao))
    if not dados:
        return None

    # Preferir campos explícitos de principal
    for item in dados:
        prop_princ = item.get("proposicaoPrincipal") or item.get("proposicao_principal")
        if isinstance(prop_princ, dict):
            uri = prop_princ.get("uri") or prop_princ.get("uriProposicao") or prop_princ.get("uriProposicaoPrincipal")
            if uri:
                pid = extract_id_from_uri(uri)
                if pid:
                    return pid

        for chave_uri in ("uriProposicaoPrincipal", "uriProposicao_principal", "uriPrincipal"):
            if item.get(chave_uri):
                pid = extract_id_from_uri(item.get(chave_uri))
                if pid:
                    return pid

    # Fallback: usar helper genérico (melhor que ficar em branco)
    for item in dados:
        pid = get_proposicao_id_from_item(item)
        if pid:
            return pid

    return None


def _legacy_format_sigla_num_ano(relator_info: dict) -> tuple[str, str]:
    """Formata relator para 'Nome (PART/UF)'. Retorna (texto, id)."""
    if not relator_info or not isinstance(relator_info, dict) or not relator_info.get("nome"):
        return ("", "")
    nome = str(relator_info.get("nome", "")).strip()
    partido = str(relator_info.get("partido", "") or "").strip()
    uf = str(relator_info.get("uf", "") or "").strip()
    relator_id = str(relator_info.get("id_deputado", "") or "")
    if partido or uf:
        txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
    else:
        txt = nome
    return (txt, relator_id)

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

    # WORKAROUND v33: Adicionar proposições que a API não retorna (bug da Câmara)
    id_str = str(id_deputada)
    if id_str in PROPOSICOES_FALTANTES_API:
        ids_existentes = {r["id"] for r in rows}
        for prop_faltante in PROPOSICOES_FALTANTES_API[id_str]:
            if prop_faltante["id"] not in ids_existentes:
                rows.append(prop_faltante)
                print(f"[API-WORKAROUND] ✅ Adicionada proposição faltante: {prop_faltante['siglaTipo']} {prop_faltante['numero']}/{prop_faltante['ano']} (ID {prop_faltante['id']})")

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Proposicao"] = df.apply(lambda r: format_sigla_num_ano(r["siglaTipo"], r["numero"], r["ano"]), axis=1)
    return df


@st.cache_data(show_spinner=False, ttl=1800)
def buscar_proposicao_direta(sigla_tipo: str, numero: str, ano: str) -> Optional[Dict]:
    """
    Busca proposição diretamente na API da Câmara por sigla/número/ano.
    Não depende de autoria - busca QUALQUER proposição.
    
    NOVO v32.2: Permite buscar proposições que a deputada acompanha
    mas não é autora.
    
    Args:
        sigla_tipo: PL, PLP, PEC, etc.
        numero: Número da proposição
        ano: Ano (4 dígitos)
        
    Returns:
        Dict com dados da proposição ou None
    """
    
    sigla = (sigla_tipo or "").strip().upper()
    num = (numero or "").strip()
    ano_str = (ano or "").strip()
    
    if not (sigla and num and ano_str):
        return None
    
    url = f"{BASE_URL}/proposicoes"
    params = {
        "siglaTipo": sigla,
        "numero": num,
        "ano": ano_str,
        "itens": 5,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        dados = data.get("dados", [])
        
        if not dados:
            return None
        
        # Pegar o primeiro resultado que bate exatamente
        for d in dados:
            if (str(d.get("numero", "")).strip() == num and 
                str(d.get("ano", "")).strip() == ano_str and
                (d.get("siglaTipo", "")).strip().upper() == sigla):
                return {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                    "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
                }
        
        # Se não achou exato, retorna o primeiro
        d = dados[0]
        return {
            "id": str(d.get("id") or ""),
            "siglaTipo": (d.get("siglaTipo") or "").strip(),
            "numero": str(d.get("numero") or "").strip(),
            "ano": str(d.get("ano") or "").strip(),
            "ementa": (d.get("ementa") or "").strip(),
            "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
        }
        
    except Exception as e:
        print(f"[BUSCA-DIRETA] Erro: {e}")
        return None


def parse_proposicao_input(texto: str) -> Optional[Tuple[str, str, str]]:
    """
    Extrai sigla, número e ano de uma string de proposição.
    
    Exemplos aceitos:
    - "PL 321/2023"
    - "PL321/2023" 
    - "pl 321 2023"
    - "PLP 223/2023"
    
    Returns:
        Tuple (sigla, numero, ano) ou None
    """
    
    texto = (texto or "").strip().upper()
    if not texto:
        return None
    
    # Padrão: SIGLA NUMERO/ANO ou SIGLA NUMERO ANO
    padrao = r"^(PL|PLP|PEC|PDL|PRC|PLV|MPV|RIC|REQ|PDS|PRS)\s*(\d+)\s*[/\s]\s*(\d{4})$"
    match = re.match(padrao, texto)
    
    if match:
        return (match.group(1), match.group(2), match.group(3))
    
    return None


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

    # ------------------------------------------------------------
    # Normalizações pedidas pelo gabinete (sem mudar a estrutura):
    # - Unificar 'Aguardando Parecer do Relator(a)' -> 'Aguardando Parecer'
    # - Situações internas/ambiguas -> 'Em providência Interna'
    # - Quando 'Aguardando Designação de Relator(a)', preencher Relator(a) com 'Aguardando'
    # ------------------------------------------------------------
    _SITUACOES_INTERNA = {
        "Despacho de Apensação",
        "Distribuição",
        "Publicação de Despacho",
        "Notificacao para Publicação Intermediária",
        "Notificações",
        "Ratificação de Parecer",
    }
    # Unificar variações
    df["Situação atual"] = df["Situação atual"].replace({
        "Aguardando Parecer do Relator(a)": "Aguardando Parecer",
        "Aguardando Parecer do Relator(a).": "Aguardando Parecer",
    })
    df.loc[df["Situação atual"].astype(str).str.startswith("Aguardando Parecer", na=False), "Situação atual"] = "Aguardando Parecer"
    # Tratar marcadores vazios/traços como interno
    def _is_blankish(v):
        if pd.isna(v):
            return True
        s = str(v).strip()
        return s in ("", "-", "—", "–")
    df.loc[df["Situação atual"].apply(_is_blankish), "Situação atual"] = "Em providência Interna"
    df.loc[df["Situação atual"].isin(_SITUACOES_INTERNA), "Situação atual"] = "Em providência Interna"

    # Preencher relator quando aguardando designação
    mask_aguardando_relator = df["Situação atual"].isin([
        "Aguardando Designação de Relator(a)",
        "Aguardando Designacao de Relator(a)",
    ])
    df.loc[mask_aguardando_relator & df["Relator(a)"].apply(_is_blankish), "Relator(a)"] = "Aguardando"

    # Preencher relator para "Tramitando em Conjunto" buscando a proposição principal (apensada)
    mask_conjunto = df["Situação atual"].eq("Tramitando em Conjunto")
    if mask_conjunto.any():
        def _fill_relator_conjunto(row):
            if not _is_blankish(row.get("Relator(a)", "")):
                return row.get("Relator(a)", "—")
            pid = str(row.get("id", "") or "").strip()
            if not pid:
                return row.get("Relator(a)", "—")
            principal_id = get_proposicao_principal_id(pid)
            if not principal_id or str(principal_id) == pid:
                return row.get("Relator(a)", "—")
            dados_principal = fetch_proposicao_completa(str(principal_id))
            rel_txt, _ = format_relator_text(dados_principal.get("relator", {}) or {})
            return rel_txt if rel_txt else row.get("Relator(a)", "—")
        df.loc[mask_conjunto, "Relator(a)"] = df.loc[mask_conjunto].apply(_fill_relator_conjunto, axis=1)

    
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
                            rel_sen_dict = buscar_detalhes_senado(prop.get("codigo_materia_senado", ""), debug=False)
                            if rel_sen:
                                prop["Relator_Senado"] = rel_sen
                            
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
        "📧 Receber Notificações",
        "📎 Projetos Apensados"
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
        
        st.title("📊 Dashboard Executivo")
       

        
        # ============================================================
        # HEADER SIMPLES (sem foto)
        # ============================================================
        st.markdown(f"### {nome_deputada}")
        st.markdown(f"**Partido:** {partido_deputada} | **UF:** {uf_deputada}")
        st.markdown(f"🕐 **Última atualização:** {get_brasilia_now().strftime('%d/%m/%Y às %H:%M:%S')}")
        
        st.markdown("---")
        
        # ============================================================
        # v38: CARREGAMENTO AUTOMÁTICO (sem botão "Carregar Dashboard")
        # A função fetch_lista_proposicoes_autoria já tem @st.cache_data
        # ============================================================
        
        # Inicializar cache no session_state
        if "props_autoria_aba1_cache" not in st.session_state:
            st.session_state["props_autoria_aba1_cache"] = None
        
        col_info1, col_refresh1 = st.columns([3, 1])
        with col_info1:
            st.caption("💡 **Dashboard carrega automaticamente.** Clique em 'Atualizar' para forçar recarga.")
        with col_refresh1:
            btn_atualizar_aba1 = st.button("🔄 Atualizar", key="btn_refresh_aba1")
        
        # Carregar automaticamente se cache vazio OU se botão foi clicado
        precisa_carregar_aba1 = st.session_state["props_autoria_aba1_cache"] is None or btn_atualizar_aba1
        
        props_autoria = []
        
        if precisa_carregar_aba1:
            with st.spinner("📊 Carregando métricas do dashboard..."):
                try:
                    # Usar função que já existe no código (tem @st.cache_data)
                    df_props = fetch_lista_proposicoes_autoria(id_deputada)
                
                    if df_props.empty:
                        props_autoria = []
                    else:
                        props_autoria = df_props.to_dict('records')
                    
                    # Salvar no cache do session_state
                    st.session_state["props_autoria_aba1_cache"] = props_autoria
                    
                    if btn_atualizar_aba1:
                        st.success(f"✅ Dashboard atualizado! {len(props_autoria)} proposições carregadas.")
                
                except Exception as e:
                    st.error(f"⚠️ Erro ao carregar métricas: {e}")
                    props_autoria = []
                    st.session_state["props_autoria_aba1_cache"] = []
        else:
            # Usar cache existente
            props_autoria = st.session_state["props_autoria_aba1_cache"] or []
        
        # ============================================================
        # CARDS DE MÉTRICAS (KPIs)
        # ============================================================
        st.markdown("### 📈 Visão Geral")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Contar por tipo primeiro para usar em todos os cards
        tipos_count = provider.contar_tipos(props_autoria)

        
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
        _set_aba_atual(2)
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
        dt_range_saved = st.session_state.get("dt_range_tab2_saved")

        if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
            dt_inicio, dt_fim = dt_inicio_t2, dt_fim_t2
        else:
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
# ============================================================
    # ABA 3 - PALAVRAS-CHAVE
    # ============================================================
    with tab3:
        _set_aba_atual(3)
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
                value=(st.session_state.get("palavras_t3") or "\n".join(PALAVRAS_CHAVE_PADRAO)),
                height=100,
                key="palavras_input_t3"
            )
            palavras_chave_t3 = [p.strip() for p in (palavras_str_t3 or "").splitlines() if p.strip()]
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
        dt_range_saved = st.session_state.get("dt_range_tab3_saved")

        if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
            dt_inicio, dt_fim = dt_inicio_t3, dt_fim_t3
        else:
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
                    st.success(
                        f"🔍 **{len(df_props)} matérias** com palavras-chave encontradas em "
                        f"**{df_props['Comissão'].nunique()} comissões**!"
                    )

                    # Converter Data para datetime
                    df_props["Data_dt"] = pd.to_datetime(
                        df_props["Data"],
                        dayfirst=True,
                        errors="coerce"
                    )

                    df_props_valid = df_props[df_props["Data_dt"].notna()].copy()
                    df_props_valid["Dia"] = df_props_valid["Data_dt"].dt.date

                    por_dia = (
                        df_props_valid
                        .groupby("Dia")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Dia")
                    )

                    st.caption("📊 Matérias com palavras-chave por dia")
                    st.dataframe(por_dia, use_container_width=True, hide_index=True)

                    # Exibir tabela principal
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
                            "⬇️ XLSX",
                            data=data_bytes,
                            file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{ext}",
                            mime=mime,
                            key="download_kw_xlsx"
                        )
                    with col_p2:
                        # Usar df_kw para PDF (tem todas as colunas necessárias)
                        pdf_bytes, pdf_mime, pdf_ext = to_pdf_palavras_chave(df_kw)
                        st.download_button(
                            "⬇️ PDF",
                            data=pdf_bytes,
                            file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                            mime=pdf_mime,
                            key="download_kw_pdf"
                        )
# ============================================================
    # ABA 4 - COMISSÕES ESTRATÉGICAS
    # ============================================================
    with tab4:
        _set_aba_atual(4)
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
            comissoes_t4 = [c.strip().upper() for c in (comissoes_str_t4 or "").split(",") if c.strip()]
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
        dt_range_saved = st.session_state.get("dt_range_tab4_saved")

        if not dt_range_saved or not isinstance(dt_range_saved, (tuple, list)) or len(dt_range_saved) != 2:
            dt_inicio, dt_fim = dt_inicio_t4, dt_fim_t4
        else:
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
# ============================================================
    # ABA 5 - BUSCAR PROPOSIÇÃO ESPECÍFICA (LIMPA)
    # ============================================================
    with tab5:
        _set_aba_atual(5)
        st.markdown("### 🔍 Buscar Proposição Específica")
        
        st.info("💡 **Dica:** Use os filtros de ano e tipo para encontrar proposições específicas. Clique em uma proposição na tabela para ver detalhes completos, tramitação e estratégia.")
        
        st.caption("Busque proposições de autoria da deputada e veja detalhes completos")

        # Botão de limpar cache
        col_cache, col_refresh5 = st.columns([1, 1])
        with col_cache:
            if st.button("🧹 Limpar cache", key="limpar_cache_tab5"):
                fetch_proposicao_completa.clear()
                fetch_lista_proposicoes_autoria_geral.clear()
                fetch_rics_por_autor.clear()
                fetch_lista_proposicoes_autoria.clear()
                build_status_map.clear()
                st.session_state.pop("df_status_last", None)
                st.session_state.pop("df_todas_enriquecido_tab5", None)  # Limpar cache do dataset enriquecido também
                st.session_state.pop("props_aba5_cache", None)  # v39: Limpar cache da aba 5
                st.success("✅ Cache limpo! Recarregando...")
                st.rerun()  # Forçar recarga da página
        
        with col_refresh5:
            btn_refresh_aba5 = st.button("🔄 Atualizar", key="btn_refresh_aba5")

        # v39: Cache e carregamento automático (sem botão "Carregar")
        if "props_aba5_cache" not in st.session_state:
            st.session_state["props_aba5_cache"] = None
        
        # Carregar automaticamente se cache vazio OU se botão foi clicado
        precisa_carregar_aba5 = st.session_state["props_aba5_cache"] is None or btn_refresh_aba5
        
        # Inicializar variável
        df_aut = pd.DataFrame()
        
        if precisa_carregar_aba5:
            # Carrega proposições automaticamente
            with st.spinner("Carregando proposições de autoria..."):
                df_aut = fetch_lista_proposicoes_autoria(id_deputada)
                st.session_state["props_aba5_cache"] = df_aut
                if btn_refresh_aba5:
                    st.success("✅ Dados atualizados!")
        else:
            # Usar cache existente
            df_aut = st.session_state["props_aba5_cache"]
            if df_aut is None:
                df_aut = pd.DataFrame()

        # Variáveis para o chat (definidas antes do if/else para estarem disponíveis depois)
        filtro_busca_atual = ""
        
        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
        else:
            df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

            # Filtros básicos
            st.markdown("#### 🗂️ Filtros de Proposições")
            col_ano, col_tipo = st.columns([1, 1])
            with col_ano:
                anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
                anos_sel = st.multiselect("Ano", options=anos, default=default_anos_sel(anos), key="anos_tab5")
            with col_tipo:
                tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
                tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos, key="tipos_tab5")

            df_base = df_aut.copy()
            if anos_sel:
                df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
            if tipos_sel:
                df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()

            # INTEGRAÇÃO SENADO AUTOMÁTICA (v32.0)
            # Sempre processa - a função só busca efetivamente se situação indica Senado
            col_sen5, col_dbg5 = st.columns([4, 1])
            with col_sen5:
                st.info("🏛️ Integração Senado: **Automática** - detecta quando matéria está no Senado")
            with col_dbg5:
                if st.session_state.get("usuario_logado", "").lower() == "admin":
                    debug_senado_5 = st.checkbox("🔧 Debug", value=False, key="debug_senado_5")
                else:
                    debug_senado_5 = False
            
            # Sempre ativo (automático)
            incluir_senado_tab5 = True

            st.markdown("---")

            # Campo de busca - SOMENTE proposições de autoria (v33)
            q = st.text_input(
                "Filtrar proposições de autoria",
                value="",
                placeholder="Ex.: PL 321/2023 | 'pix' | 'conanda' | 'oab'",
                help="Busca entre as proposições de AUTORIA da deputada. Use sigla/número/ano ou palavras da ementa.",
                key="busca_tab5"
            )

            # v33: APENAS busca textual nas proposições de autoria
            # Removida funcionalidade de busca direta de outras proposições
            if q.strip():
                qn = normalize_text(q)
                df_busca_completa = df_aut.copy()
                df_busca_completa["_search"] = (df_busca_completa["Proposicao"].fillna("").astype(str) + " " + df_busca_completa["ementa"].fillna("").astype(str)).apply(normalize_text)
                df_rast = df_busca_completa[df_busca_completa["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")
                
                if df_rast.empty:
                    st.warning(f"⚠️ Nenhuma proposição de autoria encontrada com '{q}'")
                else:
                    st.caption(f"🔍 Encontrado(s) {len(df_rast)} resultado(s) entre as {len(df_aut)} proposições de autoria")
            else:
                df_rast = df_base.copy()

            # Verificar se tem resultados
            if df_rast.empty:
                st.info("Nenhuma proposição encontrada com os critérios informados.")
                df_rast_lim = pd.DataFrame()
                df_rast_enriched = pd.DataFrame()
                df_tbl = pd.DataFrame()
            else:
                df_rast_lim = df_rast.head(400).copy()
                
                with st.spinner("Carregando status das proposições..."):
                    ids_r = df_rast_lim["id"].astype(str).tolist()
                    status_map_r = build_status_map(ids_r)
                    
                    # DEBUG: Verificar se status_map tem dados
                    ids_com_situacao = sum(1 for k, v in status_map_r.items() if v.get("situacao"))
                    ids_com_orgao = sum(1 for k, v in status_map_r.items() if v.get("siglaOrgao"))
                    
                    if ids_com_situacao < len(ids_r) // 2:
                        st.warning(f"⚠️ API retornou poucos dados: Situação em {ids_com_situacao}/{len(ids_r)}, Órgão em {ids_com_orgao}/{len(ids_r)}")
                    
                    df_rast_enriched = enrich_with_status(df_rast_lim, status_map_r)

                df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)

            st.caption(f"Resultados: {len(df_rast_enriched) if not df_rast_enriched.empty else 0} proposições")

            # Só continua se tiver dados
            if not df_rast_enriched.empty:
                df_tbl = df_rast_enriched.rename(
                    columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
                ).copy()
                
                df_tbl["Último andamento"] = df_rast_enriched["Andamento (status)"]
                df_tbl["Parado (dias)"] = df_rast_enriched.get("Parado (dias)", pd.Series([None]*len(df_rast_enriched)))
                df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)
            
                # Criar coluna Alerta ANTES de processar Senado (importante!)
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
                # SENADO: AUTOMÁTICO PARA PROPOSIÇÕES EM APRECIAÇÃO NO SENADO
                # v37 - Cache incremental, sem botão, exclui RICs
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
                    
                    # Exibir tabela limpa com dados do Senado
                    colunas_senado = ["Proposição", "Tipo", "Situação atual", "Órgão (sigla)", "Relator(a)", 
                                      "Último andamento", "Data do status", "Parado (dias)"]
                    
                    # Adicionar colunas do Senado se existirem
                    for col in ["Relator_Senado", "Orgao_Senado_Sigla", "situacao_senado"]:
                        if col in df_no_senado.columns:
                            colunas_senado.append(col)
                    
                    colunas_exibir = [c for c in colunas_senado if c in df_no_senado.columns]
                    
                    st.dataframe(
                        df_no_senado[colunas_exibir],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                
                # Mostrar TODAS as proposições na tabela principal
                st.markdown("#### 📋 Proposições encontradas")
                st.caption(f"Mostrando {min(20, len(df_tbl))} de {len(df_tbl)} resultados")
                
                # Colunas dinâmicas - incluir dados do Senado quando checkbox marcado
                if incluir_senado_tab5 and "no_senado" in df_tbl.columns:
                    # Substituir Relator e Órgão pelos dados do Senado quando disponíveis
                    if "Relator_Senado" in df_tbl.columns:
                        # v33 CORRIGIDO: Se está no Senado, SEMPRE usa dados do Senado
                        # (mesmo que vazios, para não mostrar relator antigo da Câmara)
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
                                    # Tentar pegar do último andamento se disponível
                                    movs = str(row.get("UltimasMov_Senado", ""))
                                    if movs and " | " in movs:
                                        partes = movs.split("\n")[0].split(" | ")
                                        if len(partes) >= 2 and partes[1].strip():
                                            return partes[1].strip()
                                    return "MESA"  # Padrão quando ainda não foi distribuído
                            return row.get("Órgão (sigla)", "")
                        
                        df_tbl["Relator_Exibido"] = df_tbl.apply(get_relator_integrado, axis=1)
                        df_tbl["Orgao_Exibido"] = df_tbl.apply(get_orgao_integrado, axis=1)
                    
                    # NOVO v32.1: Atualizar Último andamento, Data e Parado com dados do Senado
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
                        # datetime já importado no topo
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
                    
                    # v33: IMPORTANTE - Atualizar "Situação atual" com status do SENADO
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
            _debug_orgao = df_tbl["Órgão (sigla)"].dropna().astype(str) if "Órgão (sigla)" in df_tbl.columns else pd.Series()
            _debug_orgao_ok = (_debug_orgao != "").sum() if len(_debug_orgao) > 0 else 0
            
            if _debug_situacao_ok == 0 or _debug_orgao_ok == 0:
                st.warning(f"⚠️ DEBUG: Dados incompletos! Situação: {_debug_situacao_ok}/{len(df_tbl)}, Órgão: {_debug_orgao_ok}/{len(df_tbl)}")
            
            # IMPORTANTE: Variável local para passar DIRETAMENTE ao chat (não via session_state)
            filtro_busca_atual = q
            
            # Também salvar no session_state para backup
            st.session_state["filtro_busca_tab5"] = q
            
            # Também salvar o DataFrame COMPLETO COM STATUS para quando não houver filtro
            # IMPORTANTE: Precisamos enriquecer TODAS as proposições com Situação e Órgão
            df_existente = st.session_state.get("df_todas_enriquecido_tab5", pd.DataFrame())
            precisa_recriar = (
                df_existente.empty or 
                len(df_existente) != len(df_aut) or
                "Situação atual" not in df_existente.columns  # Força recriação se não tem colunas
            )
            
            if precisa_recriar:
                with st.spinner("Preparando base completa (primeira vez)..."):
                    # Enriquecer TODAS as proposições com status
                    df_aut_completo = df_aut.copy()
                    ids_todas = df_aut_completo["id"].astype(str).tolist()
                    
                    # Buscar status de todas (pode demorar um pouco na primeira vez, mas fica em cache)
                    status_map_todas = build_status_map(ids_todas)
                    df_aut_enriquecido = enrich_with_status(df_aut_completo, status_map_todas)
                    
                    # Renomear colunas
                    df_aut_enriquecido = df_aut_enriquecido.rename(
                        columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
                    )
                    
                    st.session_state["df_todas_enriquecido_tab5"] = df_aut_enriquecido
            
            # Configurar colunas de exibição com rótulos melhores quando Senado ativo
            column_config_base = {
                "Alerta": st.column_config.TextColumn("", width="small", help="Urgência"),
                "LinkTramitacao": st.column_config.LinkColumn("🏛️ Câmara", display_text="Abrir"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            }
            
            if incluir_senado_tab5 and "no_senado" in df_tbl.columns:
                column_config_base.update({
                    "Orgao_Exibido": st.column_config.TextColumn("Órgão", width="medium", help="Órgão atual (Câmara ou Senado)"),
                    "Relator_Exibido": st.column_config.TextColumn("Relator", width="medium", help="Relator atual (Câmara ou Senado)"),
                    "no_senado": st.column_config.CheckboxColumn("No Senado?", width="small"),
                    "codigo_materia_senado": st.column_config.TextColumn("Código Matéria", width="small", help="Código interno da matéria no Senado"),
                    "tipo_numero_senado": st.column_config.TextColumn("Nº Senado", width="medium"),
                    "situacao_senado": st.column_config.TextColumn("Situação Senado", width="medium"),
                    "url_senado": st.column_config.LinkColumn("🏛️ Senado", display_text="Abrir", help="Clique para abrir a página da matéria no Senado"),
                })
            
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
            
            # REMOVIDO v32.0: Expander separado do Senado
            # Os dados do Senado agora são exibidos INTEGRADOS nos detalhes da proposição
            
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
            senado_data_row = None
            try:
                if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                    row_idx = sel["selection"]["rows"][0]
                    row_data = df_tbl.iloc[row_idx]
                    selected_id = str(row_data["ID"])
                    
                    # v33 CORRIGIDO: Extrair dados do Senado corretamente (pandas Series)
                    # Usar .get() com fallback seguro e converter para tipos Python nativos
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
                exibir_detalhes_proposicao(selected_id, key_prefix="tab5", senado_data=senado_data_row)
        st.markdown("---")
        # IMPORTANTE: Ler o filtro DIRETAMENTE do widget de busca (key="busca_tab5")
        # Isso garante que o filtro esteja sempre sincronizado
        
        filtro_busca = st.session_state.get("busca_tab5", "")
        
        # DEBUG: Mostrar filtro sendo usado
        st.caption(f"🔎 Filtro atual: **'{filtro_busca}'**" if filtro_busca else "🔎 Sem filtro ativo")
        
        # Usar o DataFrame COMPLETO enriquecido (com Situação e Órgão)
        df_view_tab5 = st.session_state.get("df_todas_enriquecido_tab5", pd.DataFrame())
        if df_view_tab5.empty:
            pass
        if filtro_busca and not df_view_tab5.empty:
            busca = filtro_busca.strip().lower()
            if busca:
                # Aplicar filtro
                def normalizar_busca(txt):
                    if pd.isna(txt):
                        return ""
                    txt = str(txt).lower()
                    txt = unicodedata.normalize('NFD', txt)
                    txt = ''.join(c for c in txt if unicodedata.category(c) != 'Mn')
                    return txt
                
                # Determinar colunas
                col_prop = "Proposição" if "Proposição" in df_view_tab5.columns else "Proposicao"
                col_ementa = "Ementa" if "Ementa" in df_view_tab5.columns else "ementa"
                
                df_view_tab5 = df_view_tab5.copy()
                df_view_tab5["_busca_tmp"] = (
                    df_view_tab5[col_prop].fillna("").astype(str) + " " + 
                    df_view_tab5[col_ementa].fillna("").astype(str)
                ).apply(normalizar_busca)
                
                busca_norm = normalizar_busca(busca)
                df_view_tab5 = df_view_tab5[df_view_tab5["_busca_tmp"].str.contains(busca_norm, na=False)]
                df_view_tab5 = df_view_tab5.drop(columns=["_busca_tmp"], errors="ignore")
                
        
        # DEBUG info
        if not df_view_tab5.empty:
            colunas = list(df_view_tab5.columns)
            tem_situacao = "Situação atual" in colunas
            tem_orgao = "Órgão (sigla)" in colunas
            
            # Verificar se tem dados nas colunas
            if tem_situacao:
                situacao_valores = df_view_tab5["Situação atual"].dropna().astype(str)
                situacao_nao_vazio = situacao_valores[situacao_valores != ""].count()
            else:
                situacao_nao_vazio = 0
                
            if tem_orgao:
                orgao_valores = df_view_tab5["Órgão (sigla)"].dropna().astype(str)
                orgao_nao_vazio = orgao_valores[orgao_valores != ""].count()
            else:
                orgao_nao_vazio = 0
            
            total = len(df_view_tab5)
            
            if filtro_busca:
            
                pass
            
            else:
            
                pass
            # Mostrar status dos dados
            st.caption(f"📊 Dados disponíveis: Situação em **{situacao_nao_vazio}/{total}** | Órgão em **{orgao_nao_vazio}/{total}**")
            
            # Se dados estão vazios, mostrar alerta
            if situacao_nao_vazio == 0 or orgao_nao_vazio == 0:
                st.error("⚠️ **DADOS VAZIOS!** Clique em '🧹 Limpar cache' acima e aguarde recarregar.")
            
            # DEBUG: Mostrar amostra dos dados
        else:
            st.info("💡 Use o campo 'Filtrar proposições' acima para buscar.")
        
        # Garantir que selected_id existe
        sel_id_tab5 = selected_id if 'selected_id' in dir() and selected_id else None

    # ============================================================
    # ABA 6 - MATÉRIAS POR SITUAÇÃO ATUAL (separada)
    # ============================================================
    with tab6:
        _set_aba_atual(6)
        st.markdown("### 📊 Matérias por situação atual")
        
        st.info("💡 **Dica:** Visualize a carteira completa de proposições por situação de tramitação. Use os filtros para segmentar por ano, tipo, órgão e tema. Clique em uma proposição para ver detalhes.")
        
        st.caption("Análise da carteira de proposições por status de tramitação")

        # ============================================================
        # v37: CARREGAMENTO AUTOMÁTICO (sem botão)
        # ============================================================
        # Inicializar cache
        if "df_aut6_cache" not in st.session_state:
            st.session_state["df_aut6_cache"] = pd.DataFrame()
        
        col_info6, col_refresh6 = st.columns([3, 1])
        with col_info6:
            st.caption("💡 **Matérias carregam automaticamente.** Clique em 'Atualizar' para forçar recarga.")
        with col_refresh6:
            btn_atualizar_aba6 = st.button("🔄 Atualizar", key="btn_refresh_aba6")
        
        # Carregar automaticamente se cache vazio OU se botão foi clicado
        precisa_carregar6 = st.session_state["df_aut6_cache"].empty or btn_atualizar_aba6
        
        if precisa_carregar6:
            with st.spinner("Carregando proposições de autoria..."):
                df_aut6 = fetch_lista_proposicoes_autoria(id_deputada)
                st.session_state["df_aut6_cache"] = df_aut6
                if btn_atualizar_aba6:
                    st.success(f"✅ {len(df_aut6)} proposições atualizadas!")
        else:
            df_aut6 = st.session_state["df_aut6_cache"]

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

            # INTEGRAÇÃO SENADO AUTOMÁTICA (v32.0)
            # Sempre processa - a função só busca efetivamente se situação indica Senado
            col_sen6, col_dbg6 = st.columns([4, 1])
            with col_sen6:
                st.info("🏛️ Integração Senado: **Automática** - detecta quando matéria está no Senado")
            with col_dbg6:
                if st.session_state.get("usuario_logado", "").lower() == "admin":
                    debug_senado_6 = st.checkbox("🔧 Debug", value=False, key="debug_senado_6")
                else:
                    debug_senado_6 = False
            
            # Sempre ativo (automático)
            incluir_senado_tab6 = True

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
                    
                    # DESABILITADO - Senado apenas na Aba 5
                    # # Processar com Senado
                    #                     if incluir_senado_tab6:
                    #                         with st.spinner("🔍 Buscando tramitação no Senado..."):
                    #                             df_status_view = processar_lista_com_senado(
                    #                                 df_status_view,
                    #                                 debug=debug_senado_6,
                    #                                 mostrar_progresso=len(df_status_view) > 3
                    #                             )
                    #                     
                    #                     st.session_state["df_status_last"] = df_status_view

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

                # Quando Senado habilitado, substituir Relator e Órgão pelos dados do Senado
                if incluir_senado_tab6 and "no_senado" in df_tbl_status.columns:
                    # Criar colunas que mostram dados do Senado quando disponíveis
                    if "Relator_Senado" in df_tbl_status.columns:
                        # v33 CORRIGIDO: Se está no Senado, SEMPRE usa dados do Senado
                        def get_relator_integrado_tab6(row):
                            if row.get("no_senado"):
                                relator_senado = row.get("Relator_Senado", "")
                                if relator_senado and relator_senado.strip():
                                    return relator_senado
                                else:
                                    return "—"  # Sem relator no Senado ainda
                            return row.get("Relator(a)", "—")
                        
                        def get_orgao_integrado_tab6(row):
                            if row.get("no_senado"):
                                orgao_senado = row.get("Orgao_Senado_Sigla", "")
                                if orgao_senado and orgao_senado.strip():
                                    return orgao_senado
                                else:
                                    # Tentar pegar do último andamento se disponível
                                    movs = str(row.get("UltimasMov_Senado", ""))
                                    if movs and " | " in movs:
                                        partes = movs.split("\n")[0].split(" | ")
                                        if len(partes) >= 2 and partes[1].strip():
                                            return partes[1].strip()
                                    return "MESA"  # Padrão quando ainda não foi distribuído
                            return row.get("Órgão (sigla)", "")
                        
                        df_tbl_status["Relator_Exibido"] = df_tbl_status.apply(get_relator_integrado_tab6, axis=1)
                        df_tbl_status["Orgao_Exibido"] = df_tbl_status.apply(get_orgao_integrado_tab6, axis=1)
                        
                        # NOVO v32.1: Atualizar Última tramitação e Parado há com dados do Senado
                        def get_ultima_tram_integrado_tab6(row):
                            if row.get("no_senado") and row.get("UltimasMov_Senado"):
                                movs = str(row.get("UltimasMov_Senado", ""))
                                if movs and movs != "Sem movimentações disponíveis":
                                    primeira = movs.split("\n")[0] if "\n" in movs else movs
                                    partes = primeira.split(" | ")
                                    if len(partes) >= 3:
                                        return partes[2][:60]
                            return row.get("Última tramitação", "") or ""
                        
                        def get_parado_integrado_tab6(row):
                            # datetime já importado no topo
                            if row.get("no_senado") and row.get("UltimasMov_Senado"):
                                movs = str(row.get("UltimasMov_Senado", ""))
                                if movs and movs != "Sem movimentações disponíveis":
                                    primeira = movs.split("\n")[0] if "\n" in movs else movs
                                    partes = primeira.split(" | ")
                                    if partes:
                                        data_str = partes[0].strip()
                                        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                                            try:
                                                dt = datetime.datetime.strptime(data_str[:16], fmt)
                                                dias = (datetime.datetime.now() - dt).days
                                                return f"{dias}d"
                                            except:
                                                continue
                            return row.get("Parado há", "")
                        
                        df_tbl_status["Última tramitação"] = df_tbl_status.apply(get_ultima_tram_integrado_tab6, axis=1)
                        df_tbl_status["Parado há"] = df_tbl_status.apply(get_parado_integrado_tab6, axis=1)
                        
                        # v33: IMPORTANTE - Atualizar "Situação atual" com status do SENADO
                        def get_situacao_integrada_tab6(row):
                            if row.get("no_senado"):
                                sit_senado = row.get("situacao_senado", "")
                                if sit_senado and sit_senado.strip():
                                    return f"🏛️ {sit_senado}"  # Emoji indica Senado
                            return row.get("Situação atual", "")
                        
                        df_tbl_status["Situação atual"] = df_tbl_status.apply(get_situacao_integrada_tab6, axis=1)
                        
                    else:
                        df_tbl_status["Relator_Exibido"] = df_tbl_status.get("Relator(a)", "—")
                        df_tbl_status["Orgao_Exibido"] = df_tbl_status.get("Órgão (sigla)", "")
                    
                    show_cols = [
                        "Proposição", "Tipo", "Ano", "Situação atual", "Orgao_Exibido", "Relator_Exibido",
                        "Última tramitação", "Sinal", "Parado há", "Tema", 
                        "no_senado", "url_senado",
                        "id", "LinkTramitacao", "LinkRelator", "Ementa", "id_processo_senado", "codigo_materia_senado"
                    ]
                else:
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
                    
                    # Configurar colunas de exibição
                    column_config_tab6 = {
                        "LinkTramitacao": st.column_config.LinkColumn("Link Tramitação", display_text="abrir"),
                        "LinkRelator": st.column_config.LinkColumn("Link Relator", display_text="ver"),
                        "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                        "Última tramitação": st.column_config.TextColumn("Última tramitação", width="small"),
                    }
                    
                    if incluir_senado_tab6 and "no_senado" in df_tbl_status.columns:
                        column_config_tab6.update({
                            "Orgao_Exibido": st.column_config.TextColumn("Órgão", width="medium", help="Órgão atual (Câmara ou Senado)"),
                            "Relator_Exibido": st.column_config.TextColumn("Relator", width="medium", help="Relator atual (Câmara ou Senado)"),
                            "no_senado": st.column_config.CheckboxColumn("No Senado?", width="small"),
                            "codigo_materia_senado": st.column_config.TextColumn("Código", width="small", help="Código interno da matéria no Senado"),
                            "tipo_numero_senado": st.column_config.TextColumn("Nº Senado", width="medium"),
                            "situacao_senado": st.column_config.TextColumn("Situação Senado", width="medium"),
                            "url_senado": st.column_config.LinkColumn("🏛️ Senado", display_text="Abrir", help="Clique para abrir a página da matéria no Senado"),
                        })
                    else:
                        column_config_tab6.update({
                            "Relator(a)": st.column_config.TextColumn("Relator(a)", width="medium"),
                        })
                    
                    st.dataframe(
                        df_tbl_status[show_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config=column_config_tab6,
                    )
                
                # Seção especial para detalhes do Senado
                # REMOVIDO v32.0: Expander separado do Senado
                # Os dados do Senado agora são exibidos INTEGRADOS nos detalhes da proposição
                
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
# ============================================================
    # ABA 7 - RICs (REQUERIMENTOS DE INFORMAÇÃO)
    # ============================================================
    with tab7:
        _set_aba_atual(7)
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
        # v37: CARREGAMENTO AUTOMÁTICO DE RICs (sem botão)
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
                # Buscar RICs
                df_rics_base = fetch_rics_por_autor(id_deputada)
                
                if df_rics_base.empty:
                    st.warning("Nenhum RIC encontrado.")
                    st.session_state["df_rics_completo"] = pd.DataFrame()
                else:
                    # Buscar status completo de cada RIC
                    ids_rics = df_rics_base["id"].astype(str).tolist()
                    status_map_rics = build_status_map(ids_rics)
                    
                    # Enriquecer com status
                    df_rics_enriquecido = enrich_with_status(df_rics_base, status_map_rics)
                    
                    st.session_state["df_rics_completo"] = df_rics_enriquecido
                    registrar_atualizacao("rics")
                    
                    if btn_atualizar_rics:
                        st.success(f"✅ {len(df_rics_enriquecido)} RICs atualizados!")
        
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

        st.markdown("---")
        st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")


    # ============================================================
    # ABA 8 - RECEBER NOTIFICAÇÕES
    # ============================================================
    with tab8:
        _set_aba_atual(8)
        st.title("📧 Receber Notificações por Email")

        st.markdown("""
        ### 📬 Cadastre-se para receber alertas

        Receba notificações por email sempre que houver:
        - 📄 **Nova tramitação** em matérias da Dep. Júlia Zanatta
        - 📋 **Matéria na pauta** de comissões (autoria ou relatoria)
        - 🔑 **Palavras-chave** de interesse nas pautas
        - 🌙 **Resumo do dia** com todas as movimentações

        ---
        """)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("✍️ Cadastrar Email")

            with st.form("form_cadastro_email", clear_on_submit=True):
                novo_email = st.text_input(
                    "Seu email",
                    placeholder="exemplo@email.com",
                    help="Digite seu email para receber as notificações"
                )

                aceite = st.checkbox(
                    "Concordo em receber notificações do Monitor Parlamentar",
                    value=False
                )

                submitted = st.form_submit_button("📩 Cadastrar", type="primary")

                if submitted:
                    if not novo_email:
                        st.error("Por favor, digite seu email")
                    elif not aceite:
                        st.warning("Por favor, marque a caixa de concordância")
                    else:
                        with st.spinner("Cadastrando..."):
                            sucesso, mensagem = cadastrar_email_github(novo_email.strip())

                        if sucesso:
                            st.success(f"✅ {mensagem}")
                            st.balloons()
                        else:
                            st.error(f"❌ {mensagem}")

        with col2:
            st.subheader("ℹ️ Informações")

            st.info("""
            **O que você vai receber:**

            📌 Emails apenas quando houver movimentação relevante

            📌 Resumo diário às 20:30

            📌 Link para o painel em cada email
            """)

        st.markdown("---")

        # Mostrar emails cadastrados (apenas para admin)
        if st.session_state.get("usuario_logado") == "admin":
            with st.expander("👑 Emails cadastrados (Admin)"):
                emails = listar_emails_cadastrados()
                if emails:
                    for i, email in enumerate(emails, 1):
                        st.write(f"{i}. {email}")
                    st.caption(f"Total: {len(emails)} emails cadastrados")
                else:
                    st.write("Nenhum email cadastrado ainda")

        st.markdown("---")

        st.markdown("""
        ### 🔗 Outras formas de acompanhar

        <table style="width:100%">
        <tr>
            <td style="text-align:center; padding:20px;">
                <a href="https://t.me/+seu_grupo_telegram" target="_blank">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="50">
                    <br><b>Grupo Telegram</b>
                </a>
            </td>
            <td style="text-align:center; padding:20px;">
                <a href="https://monitorzanatta.streamlit.app" target="_blank">
                    <img src="https://streamlit.io/images/brand/streamlit-mark-color.png" width="50">
                    <br><b>Painel Web</b>
                </a>
            </td>
        </tr>
        </table>
        """, unsafe_allow_html=True)



    # ============================================================
    # NOTA: A aba do Senado foi removida conforme especificação.
    # Os dados do Senado são exibidos nas Abas 5 e 6 apenas quando
    # a situação da proposição for "Apreciação pelo Senado Federal".
    # ============================================================

    # ============================================================
    # ============================================================
    # ABA 9 - PROJETOS APENSADOS (v36 - COMPLETA COM SELEÇÃO)
    # ============================================================
    with tab9:
        _set_aba_atual(9)
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
        
        # ============================================================
        # v37: CACHE INTELIGENTE - Separar detecção pesada da UI
        # A detecção roda UMA VEZ e é armazenada em session_state
        # Checkboxes e interações NÃO disparam recálculo
        # ============================================================
        
        # Inicializar cache de projetos apensados
        if "projetos_apensados_cache" not in st.session_state:
            st.session_state["projetos_apensados_cache"] = None
        
        col_info, col_refresh = st.columns([3, 1])
        with col_info:
            st.caption("💡 **Projetos apensados carregam automaticamente.** Clique em 'Atualizar' para forçar recarga.")
        with col_refresh:
            btn_atualizar_apensados = st.button("🔄 Atualizar", key="btn_refresh_apensados")
        
        # Carregar automaticamente se cache vazio OU se botão foi clicado
        precisa_carregar = st.session_state["projetos_apensados_cache"] is None or btn_atualizar_apensados
        
        if precisa_carregar:
            with st.spinner("🔍 Detectando projetos apensados e buscando cadeia completa..."):
                # Usar função de detecção (que agora tem @st.cache_data)
                projetos_apensados_raw = buscar_projetos_apensados_automatico(id_deputada)
                
                if not projetos_apensados_raw:
                    st.session_state["projetos_apensados_cache"] = []
                else:
                    # ============================================================
                    # ORDENAR POR DATA MAIS RECENTE PRIMEIRO
                    # ============================================================
                    def parse_data_br(data_str):
                        """Converte DD/MM/YYYY para datetime"""
                        try:
                            if data_str and data_str != "—":
                                return datetime.datetime.strptime(data_str, "%d/%m/%Y")
                            return datetime.datetime.min
                        except:
                            return datetime.datetime.min
                    
                    # Ordenar do mais recente para o mais antigo
                    projetos_ordenados = sorted(
                        projetos_apensados_raw,
                        key=lambda x: parse_data_br(x.get("data_ultima_mov", "—")),
                        reverse=True
                    )
                    
                    # Adicionar row_id estável para seleção
                    for idx, p in enumerate(projetos_ordenados):
                        p["__row_id"] = f"{p.get('id_zanatta', '')}_{idx}"
                    
                    # Salvar no cache
                    st.session_state["projetos_apensados_cache"] = projetos_ordenados
                    
                    if btn_atualizar_apensados:
                        st.success(f"✅ {len(projetos_ordenados)} projetos apensados atualizados!")
        
        # Usar dados do cache (NÃO recalcula em cada rerun)
        projetos_apensados = st.session_state.get("projetos_apensados_cache", [])
        
        if not projetos_apensados:
            st.warning("Nenhum projeto apensado encontrado ou erro na detecção.")
            st.info("💡 Isso pode significar que nenhum projeto da deputada está apensado no momento.")
        else:
            # ============================================================
            # MÉTRICAS (usando dados do PL RAIZ) - só renderiza, não recalcula
            # ============================================================
            st.markdown("### 📊 Resumo")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de PLs Apensados", len(projetos_apensados))
            
            with col2:
                aguardando_parecer = len([p for p in projetos_apensados 
                    if "Aguardando Parecer" in p.get("situacao_raiz", "")])
                st.metric("Aguardando Parecer", aguardando_parecer)
            
            with col3:
                aguardando_relator = len([p for p in projetos_apensados 
                    if "Designação de Relator" in p.get("situacao_raiz", "")])
                st.metric("Aguardando Relator", aguardando_relator)
            
            with col4:
                pronta = len([p for p in projetos_apensados 
                    if "Pronta para Pauta" in p.get("situacao_raiz", "")])
                st.metric("Pronta para Pauta", pronta, delta="⚠️ Atenção!" if pronta > 0 else None)
            
            st.markdown("---")
            
            # ============================================================
            # TABELA PRINCIPAL (usando dados do PL RAIZ)
            # ============================================================
            st.markdown("### 📋 Projetos Apensados Detectados")
            st.caption("👆 Clique em um projeto para ver detalhes completos")
            
            # Preparar dados para tabela
            dados_tabela = []
            for p in projetos_apensados:
                # Formatar "Parado há X dias" - DADOS DO PL RAIZ
                dias = p.get("dias_parado", -1)
                
                if dias < 0:
                    # Erro ao obter data
                    parado_str = "—"
                elif dias == 0:
                    parado_str = "Hoje"
                elif dias == 1:
                    parado_str = "1 dia"
                elif dias < 30:
                    parado_str = f"{dias} dias"
                elif dias < 365:
                    meses = dias // 30
                    parado_str = f"{meses} {'mês' if meses == 1 else 'meses'}"
                else:
                    anos_calc = dias // 365
                    parado_str = f"{anos_calc} {'ano' if anos_calc == 1 else 'anos'}"
                
                # ============================================================
                # v40: CORREÇÃO - Padronizar emoji IGUAL ao padrão do sistema
                # 🚨 = ≤2 dias (URGENTÍSSIMO)
                # ⚠️ = ≤5 dias (URGENTE)  
                # 🔔 = ≤15 dias (Recente)
                # (vazio) = >15 dias
                # ============================================================
                situacao_raiz = p.get("situacao_raiz", "")
                if dias < 0:
                    sinal = "—"
                elif dias <= 2:
                    sinal = "🚨"
                elif dias <= 5:
                    sinal = "⚠️"
                elif dias <= 15:
                    sinal = "🔔"
                else:
                    sinal = ""  # Mais de 15 dias, sem alerta
                
                # Construir cadeia para exibição
                cadeia = p.get("cadeia_apensamento", [])
                if cadeia and len(cadeia) > 1:
                    cadeia_str = " → ".join([c.get("pl", "") for c in cadeia])
                else:
                    cadeia_str = p.get("pl_principal", "")
                
                dados_tabela.append({
                    "": False,  # Checkbox
                    "__row_id": p.get("__row_id", ""),  # ID estável
                    "Sinal": sinal,  # v40: Padronizado
                    "PL Zanatta": p.get("pl_zanatta", ""),
                    "PL Raiz": p.get("pl_raiz", ""),
                    "Situação": situacao_raiz[:50] + ("..." if len(situacao_raiz) > 50 else ""),
                    "Órgão": p.get("orgao_raiz", ""),
                    "Relator": p.get("relator_raiz", "—")[:30],
                    "Parado há": parado_str,
                    "Última Mov.": p.get("data_ultima_mov", "—"),
                    "id_raiz": p.get("id_raiz", ""),
                    "id_zanatta": p.get("id_zanatta", ""),
                    "cadeia": cadeia_str,
                })
            
            df_tabela = pd.DataFrame(dados_tabela)
            
            # v39: Implementar seleção ÚNICA (single-select)
            # Inicializar session_state para tracking da seleção
            if "apensados_selecionado_id" not in st.session_state:
                st.session_state["apensados_selecionado_id"] = None
            
            # Criar cópia do df com checkbox baseado na seleção atual
            df_display = df_tabela.copy()
            selecionado_atual = st.session_state.get("apensados_selecionado_id", None)
            
            # Marcar apenas o item selecionado atualmente
            df_display[""] = df_display["__row_id"] == selecionado_atual
            
            # Editor de dados com checkboxes
            edited_df = st.data_editor(
                df_display[["", "__row_id", "Sinal", "PL Zanatta", "PL Raiz", "Situação", "Órgão", "Relator", "Parado há", "Última Mov."]],
                disabled=["__row_id", "Sinal", "PL Zanatta", "PL Raiz", "Situação", "Órgão", "Relator", "Parado há", "Última Mov."],
                hide_index=True,
                use_container_width=True,
                height=400,
                column_config={
                    "": st.column_config.CheckboxColumn("Sel.", default=False, width="small"),
                    "__row_id": None,  # Ocultar coluna ID
                    "Sinal": st.column_config.TextColumn("Sinal", width="small"),
                    "Relator": st.column_config.TextColumn("Relator", width="medium"),
                    "Parado há": st.column_config.TextColumn("Parado há", width="small"),
                },
                key="editor_apensados"
            )

            # Legenda - v40: Padronizada igual ao padrão do sistema
            st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")

            # v39: Detectar nova seleção e manter ÚNICO
            novos_selecionados = edited_df[edited_df[""] == True]["__row_id"].tolist()
            
            # Se o usuário marcou um novo item
            if novos_selecionados:
                # Se já tinha um selecionado e outro foi marcado, usar o NOVO
                if len(novos_selecionados) > 1:
                    # Encontrar qual é o novo (diferente do anterior)
                    for row_id in novos_selecionados:
                        if row_id != selecionado_atual:
                            st.session_state["apensados_selecionado_id"] = row_id
                            st.rerun()  # Forçar re-renderização com novo único selecionado
                else:
                    # Apenas um selecionado
                    if novos_selecionados[0] != selecionado_atual:
                        st.session_state["apensados_selecionado_id"] = novos_selecionados[0]
            else:
                # Nenhum selecionado - desmarcar
                if selecionado_atual is not None:
                    st.session_state["apensados_selecionado_id"] = None
            
            # Buscar item selecionado final
            row_id_selecionado = st.session_state.get("apensados_selecionado_id", None)
            selecionados = df_tabela[df_tabela["__row_id"] == row_id_selecionado] if row_id_selecionado else pd.DataFrame()
            
            if len(selecionados) > 0:
                st.info(f"✅ 1 projeto selecionado")
                
                # Botões de ação
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    if st.button("📋 Copiar PL Raiz", key="copiar_raiz_sel"):
                        pls_sel = "\n".join([f"{row['PL Raiz']}" for _, row in selecionados.iterrows()])
                        st.code(pls_sel, language="text")
                
                with col_a2:
                    if st.button("🔗 Abrir Link", key="abrir_links_sel"):
                        for _, row in selecionados.iterrows():
                            link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={row['id_raiz']}"
                            st.markdown(f"[🔗 {row['PL Raiz']}]({link})")
                
                with col_a3:
                    if st.button("⬇️ Baixar", key="download_sel"):
                        bytes_sel, mime_sel, ext_sel = to_xlsx_bytes(selecionados, "Selecionados")
                        st.download_button(
                            "📥 Download XLSX",
                            data=bytes_sel,
                            file_name=f"apensados_selecionados.{ext_sel}",
                            mime=mime_sel,
                        )
            
            st.markdown("---")
            
            # ============================================================
            # DETALHES DOS PROJETOS (em expanders clicáveis)
            # ============================================================
            st.markdown("### 🔍 Detalhes dos Projetos")
            st.caption("Clique em um projeto para ver detalhes completos")
            
            # MODIFICADO: Só mostrar detalhes dos selecionados
            # Filtrar apenas projetos selecionados (baseado nos checkboxes marcados)
            ids_selecionados_detalhes = df_tabela.loc[edited_df[""].to_numpy(), "__row_id"].tolist()
            projetos_selecionados = [p for p in projetos_apensados if p.get("__row_id", "") in ids_selecionados_detalhes]

            if not projetos_selecionados:
                st.info("👆 **Selecione projetos acima** marcando os checkboxes para ver detalhes completos e tramitações")
            else:
                st.success(f"📋 Exibindo detalhes de **{len(projetos_selecionados)} projeto(s)** selecionado(s)")

            for ap in projetos_selecionados:
                situacao_raiz = ap.get("situacao_raiz", "")
                dias = ap.get("dias_parado", 0)
                
                # Formatar dias parado
                if dias == 0:
                    parado_str = "Hoje"
                elif dias == 1:
                    parado_str = "1 dia"
                elif dias < 30:
                    parado_str = f"{dias} dias"
                elif dias < 365:
                    meses = dias // 30
                    parado_str = f"{meses} {'mês' if meses == 1 else 'meses'}"
                else:
                    anos_p = dias // 365
                    parado_str = f"{anos_p} {'ano' if anos_p == 1 else 'anos'}"
                
                # v40: Ícone padronizado IGUAL ao padrão do sistema
                # 🚨 = ≤2 dias (URGENTÍSSIMO)
                # ⚠️ = ≤5 dias (URGENTE)  
                # 🔔 = ≤15 dias (Recente)
                if dias < 0:
                    icone = "—"
                elif dias <= 2:
                    icone = "🚨"
                elif dias <= 5:
                    icone = "⚠️"
                elif dias <= 15:
                    icone = "🔔"
                else:
                    icone = "📋"  # Sem urgência
                
                key_unica = ap.get('id_zanatta', '') or ap.get('pl_zanatta', '').replace(' ', '_').replace('/', '_')
                
                # Construir cadeia para exibição no título
                cadeia = ap.get("cadeia_apensamento", [])
                if cadeia and len(cadeia) > 1:
                    cadeia_resumo = f" → ... → {ap.get('pl_raiz', '')}"
                else:
                    cadeia_resumo = f" → {ap.get('pl_principal', '')}"
                
                # EXPANDER clicável (padrão do sistema)
                with st.expander(f"{icone} {ap['pl_zanatta']}{cadeia_resumo} | ⏱️ {parado_str}", expanded=False):
                    
                    # Cadeia completa de apensamento
                    if cadeia and len(cadeia) > 1:
                        cadeia_str = " → ".join([c.get("pl", "") for c in cadeia])
                        st.info(f"📎 **Cadeia de apensamento:** {ap['pl_zanatta']} → {cadeia_str}")
                    
                    st.markdown("---")
                    
                    # Layout principal: 4 colunas (autor + zanatta + raiz + foto_relator)
                    col_foto, col_zanatta, col_raiz, col_foto_relator = st.columns([1, 2, 2, 1])
                    
                    with col_foto:
                        foto_url = ap.get("foto_autor", "")
                        if foto_url:
                            st.image(foto_url, width=100)
                        st.caption(f"**{ap.get('autor_principal', '—')}**")
                        st.caption("Autor do PL Principal")
                    
                    with col_zanatta:
                        st.markdown("**📌 Projeto da Deputada**")
                        st.markdown(f"### {ap['pl_zanatta']}")
                        st.caption(ap.get('ementa_zanatta', '')[:150] + "..." if len(ap.get('ementa_zanatta', '')) > 150 else ap.get('ementa_zanatta', ''))
                        st.markdown(f"[🔗 Ver PL](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={ap.get('id_zanatta', '')})")
                    
                    with col_raiz:
                        st.markdown("**🎯 PL RAIZ (onde tramita)**")
                        st.markdown(f"### {ap.get('pl_raiz', ap.get('pl_principal', ''))}")
                        
                        st.markdown(f"🏛️ **Órgão:** {ap.get('orgao_raiz', '—')}")
                        st.markdown(f"👨‍⚖️ **Relator:** {ap.get('relator_raiz', '—')}")
                        st.markdown(f"📅 **Última mov.:** {ap.get('data_ultima_mov', '—')}")
                        st.markdown(f"⏱️ **Parado há:** {parado_str}")
                        
                        st.markdown(f"[🔗 Ver PL Raiz](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={ap.get('id_raiz', '')})")
                    
                    with col_foto_relator:
                        # v39: Buscar e exibir foto do relator do PL Raiz
                        relator_nome = ap.get('relator_raiz', '—')
                        if relator_nome and relator_nome != '—':
                            # Tentar buscar ID do relator para foto
                            try:
                                rel_dict = fetch_relator_atual(ap.get('id_raiz', ''))
                                rel_id = rel_dict.get("id") if rel_dict else None
                                if rel_id:
                                    foto_relator_url = f"https://www.camara.leg.br/internet/deputado/bandep/{rel_id}.jpg"
                                    st.image(foto_relator_url, width=100)
                                    st.caption(f"**Relator(a)**")
                                else:
                                    st.markdown("")  # Placeholder
                                    st.caption("Relator(a)")
                            except:
                                st.markdown("")  # Manter layout se foto não carregar
                                st.caption("Relator(a)")
                        else:
                            st.markdown("*Sem relator*")
                            st.caption("designado")
                    
                    st.markdown("---")
                    
                    # Situação atual do PL RAIZ
                    st.markdown(f"**📊 Situação atual (PL Raiz):** {situacao_raiz}")
                    
                    # Ementa do PL Raiz
                    ementa_raiz = ap.get("ementa_raiz", ap.get("ementa_principal", "—"))
                    st.markdown(f"**📝 Ementa:** {ementa_raiz[:300]}...")
                    
                    # Botão para carregar tramitações do PL RAIZ
                    if st.button(f"🔄 Ver tramitações do PL Raiz", key=f"btn_tram_{key_unica}"):
                        exibir_detalhes_proposicao(ap.get('id_raiz', ''), key_prefix=f"apensado_{key_unica}")
            
            st.markdown("---")
            
            # ============================================================
            # DOWNLOADS
            # ============================================================
            st.markdown("### ⬇️ Downloads")
            
            # Preparar DataFrame completo para download
            df_download = pd.DataFrame(projetos_apensados)
            df_download = df_download.rename(columns={
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
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                bytes_out, mime, ext = to_xlsx_bytes(df_download, "Projetos_Apensados")
                st.download_button(
                    "⬇️ XLSX",
                    data=bytes_out,
                    file_name=f"projetos_apensados_zanatta.{ext}",
                    mime=mime,
                    key="download_apensados_xlsx"
                )
            
            with col_dl2:
                # v40: Adicionar download de PDF
                try:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_download, "Projetos Apensados - Dep. Julia Zanatta")
                    st.download_button(
                        "⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"projetos_apensados_zanatta.{pdf_ext}",
                        mime=pdf_mime,
                        key="download_apensados_pdf"
                    )
                except Exception as e:
                    st.caption(f"PDF indisponível: {e}")
            
            st.markdown("---")
            
            # Info
            st.info(f"""
            **📊 Estatísticas da detecção:**
            - Total de projetos apensados encontrados: **{len(projetos_apensados)}**
            - Mapeamentos no dicionário: **{len(MAPEAMENTO_APENSADOS)}**
            - Projetos no cadastro manual: **{len(PROPOSICOES_FALTANTES_API.get('220559', []))}**
            - Ordenação: **Do mais recente para o mais antigo**
            """)
        
        st.markdown("---")
        st.caption("Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")

    st.markdown("---")

if __name__ == "__main__":
    main()