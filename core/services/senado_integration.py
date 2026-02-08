# core/services/senado_integration.py
"""
Serviço de Integração com Senado Federal

Este módulo contém TODA a lógica de integração com a API do Senado Federal.

IMPORTANTE: Apenas a Tab 5 (Buscar Proposição) tem acesso ao Senado!
O gate de segurança garante que outras abas não façam chamadas desnecessárias.

APIs utilizadas:
- https://legis.senado.leg.br/dadosabertos/processo
- https://legis.senado.leg.br/dadosabertos/processo/relatoria
- https://legis.senado.leg.br/dadosabertos/processo/{id}

Funcionalidades:
- Busca de tramitação no Senado
- Busca de relatorias e órgãos
- Busca de movimentações (informes legislativos)
- Busca de status atual
- Enriquecimento de proposições com dados do Senado
- Cache inteligente
- Processamento em lote

Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import re
import json
import datetime
import time
import xml.etree.ElementTree as ET

import streamlit as st
import requests
import pandas as pd

# Importar configuração de SSL
try:
    import certifi
    _REQUESTS_VERIFY = certifi.where()
except ImportError:
    _REQUESTS_VERIFY = True


# ============================================================
# GATE DE SEGURANÇA - APENAS TAB 5
# ============================================================

def pode_chamar_senado() -> bool:
    """
    Gate de segurança: Apenas Tab 5 pode chamar Senado.
    
    IMPORTANTE: Evita que outras abas façam chamadas
    desnecessárias à API do Senado.
    
    Returns:
        True se estamos na aba 5, False caso contrário
    """
    aba_atual = st.session_state.get("aba_atual_senado", None)
    return aba_atual == 5


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def extrair_numero_pl_camera(proposicao: str) -> Optional[Tuple[str, str, str]]:
    """
    Extrai tipo, número e ano de uma proposição.
    
    Exemplo: "PLP 223/2023" → ("PLP", "223", "2023")
    
    Args:
        proposicao: String da proposição (ex: "PL 123/2024")
        
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


# ============================================================
# FUNÇÕES DE BUSCA NO SENADO
# ============================================================

@st.cache_data(ttl=21600, show_spinner=False)  # TTL de 6 horas
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

    ENDPOINT (JSON, Swagger): 
    https://legis.senado.leg.br/dadosabertos/processo?sigla=...&numero=...&ano=...&v=1

    Args:
        tipo: Sigla (PL, PLP, PEC, etc.)
        numero: Número
        ano: Ano (4 dígitos)
        debug: Modo debug

    Returns:
        Dict com dados do Senado ou None se não encontrado
        
    Retorno contém:
      - codigo_senado (CodigoMateria)
      - id_processo_senado
      - situacao_senado (se disponível no retorno)
      - url_senado (deep link direto na matéria do portal www25)
      - tipo_senado / numero_senado / ano_senado (iguais aos informados)
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

        # Pode vir como lista JSON (padrão) ou, em raros casos, outro formato
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
    Busca Relator e Órgão atuais no SENADO pelo CodigoMateria ou idProcesso.

    Usa o endpoint: /dadosabertos/processo/relatoria

    Args:
        codigo_materia: Código da matéria no Senado
        id_processo: ID do processo no Senado (preferencial)
        debug: Modo debug
        
    Returns:
        Dict com dados do relator e órgão ou None
        
    Retorna dict com:
      - relator_senado (ex: "Izalci Lucas (PL/DF)")
      - relator_nome, relator_partido, relator_uf
      - orgao_senado_sigla (ex: "CAE"), orgao_senado_nome
    """
    # Preferir idProcesso
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

    # Usar idProcesso quando disponível (mais confiável)
    if id_processo:
        url = f"https://legis.senado.leg.br/dadosabertos/processo/relatoria?idProcesso={id_processo}"
    else:
        data_ref = datetime.date.today().isoformat()
        url = (
            f"https://legis.senado.leg.br/dadosabertos/processo/relatoria"
            f"?codigoMateria={codigo_materia}&dataReferencia={data_ref}&v=1"
        )

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

    # Tentar JSON primeiro
    dados = None
    try:
        dados = resp.json()
    except Exception:
        dados = None

    relatorias = []
    if isinstance(dados, list):
        relatorias = dados
    elif isinstance(dados, dict):
        # Algumas respostas podem vir aninhadas
        for k in ("relatorias", "Relatorias", "items", "data"):
            v = dados.get(k)
            if isinstance(v, list):
                relatorias = v
                break

    # Fallback XML
    if not relatorias:
        try:
            root = ET.fromstring(resp.content)
            
            def strip_ns(tag):
                return tag.split("}", 1)[-1] if "}" in tag else tag

            rel_nodes = []
            for el in root.iter():
                if strip_ns(el.tag).lower() in ("relatoria", "relator"):
                    rel_nodes.append(el)

            for el in rel_nodes:
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
        # ============================================================
        # FALLBACK: endpoint /materia/relatorias/{codigoMateria}
        # Confirmado retornando dados reais (ex: Izalci Lucas / PLP 223/2023)
        # ============================================================
        if codigo_materia:
            url_fb = f"https://legis.senado.leg.br/dadosabertos/materia/relatorias/{codigo_materia}"
            print(f"[SENADO-RELATORIA] Tentando fallback: {url_fb}")
            if debug:
                st.write(f"🔎 Fallback relatoria: {url_fb}")
            try:
                resp_fb = requests.get(
                    url_fb, timeout=20,
                    headers={"User-Agent": "Monitor-Zanatta/1.0", "Accept": "application/json"},
                    verify=_REQUESTS_VERIFY,
                )
                if resp_fb.status_code == 200 and resp_fb.content:
                    # --- JSON ---
                    try:
                        d2 = resp_fb.json()
                    except Exception:
                        d2 = None
                    
                    if isinstance(d2, dict):
                        container = (
                            (d2.get("MateriaRelatorias") or d2).get("Relatorias") or
                            (d2.get("MateriaRelatorias") or d2).get("relatorias") or {}
                        )
                        rels = container.get("Relatoria") or container.get("relatoria") or []
                        if isinstance(rels, dict):
                            rels = [rels]
                        for ri in rels:
                            if not isinstance(ri, dict):
                                continue
                            ident = ri.get("IdentificacaoParlamentar") or ri
                            nome_p = (
                                ident.get("NomeParlamentar") or
                                ri.get("nomeParlamentar") or ""
                            ).strip()
                            if nome_p:
                                relatorias.append({
                                    "dataDestituicao": ri.get("DataDestituicao") or ri.get("dataDestituicao"),
                                    "descricaoTipoRelator": ri.get("DescricaoTipoRelator") or ri.get("descricaoTipoRelator"),
                                    "dataDesignacao": ri.get("DataDesignacao") or ri.get("dataDesignacao"),
                                    "nomeParlamentar": nome_p,
                                    "siglaPartidoParlamentar": (
                                        ident.get("SiglaPartidoParlamentar") or
                                        ri.get("siglaPartidoParlamentar") or ""
                                    ).strip(),
                                    "ufParlamentar": (
                                        ident.get("UfParlamentar") or
                                        ri.get("ufParlamentar") or ""
                                    ).strip(),
                                    "siglaColegiado": (ri.get("SiglaColegiado") or ri.get("siglaColegiado") or "").strip(),
                                    "nomeColegiado": (ri.get("NomeColegiado") or ri.get("nomeColegiado") or "").strip(),
                                })
                    
                    # --- XML fallback ---
                    if not relatorias:
                        try:
                            root_fb = ET.fromstring(resp_fb.content)
                            def _sn(tag):
                                return tag.split("}", 1)[-1] if "}" in tag else tag
                            for el in root_fb.iter():
                                if _sn(el.tag).lower() == "relatoria":
                                    vals = {}
                                    for ch in el.iter():
                                        t = _sn(ch.tag)
                                        if ch.text and ch.text.strip():
                                            vals[t] = ch.text.strip()
                                    n = vals.get("NomeParlamentar") or vals.get("nomeParlamentar")
                                    if n:
                                        relatorias.append({
                                            "dataDestituicao": vals.get("DataDestituicao") or vals.get("dataDestituicao"),
                                            "descricaoTipoRelator": vals.get("DescricaoTipoRelator") or vals.get("descricaoTipoRelator"),
                                            "dataDesignacao": vals.get("DataDesignacao") or vals.get("dataDesignacao"),
                                            "nomeParlamentar": n.strip(),
                                            "siglaPartidoParlamentar": (vals.get("SiglaPartidoParlamentar") or vals.get("siglaPartidoParlamentar") or "").strip(),
                                            "ufParlamentar": (vals.get("UfParlamentar") or vals.get("ufParlamentar") or "").strip(),
                                            "siglaColegiado": (vals.get("SiglaColegiado") or vals.get("siglaColegiado") or "").strip(),
                                            "nomeColegiado": (vals.get("NomeColegiado") or vals.get("nomeColegiado") or "").strip(),
                                        })
                        except Exception:
                            pass
                    
                    if relatorias:
                        print(f"[SENADO-RELATORIA] ✅ Fallback encontrou {len(relatorias)} relatoria(s)")
            except Exception as e_fb:
                print(f"[SENADO-RELATORIA] Fallback falhou: {e_fb}")

    if not relatorias:
        print(f"[SENADO-RELATORIA] ⚠️ Nenhuma relatoria encontrada")
        return resultado

    # Escolher relatoria "ativa"
    def is_active(r):
        dd = r.get("dataDestituicao")
        return dd in (None, "", "null")

    candidatas = [r for r in relatorias if is_active(r)]
    if not candidatas:
        candidatas = relatorias

    relator_cands = [r for r in candidatas if (r.get("descricaoTipoRelator") or "").lower() == "relator"]
    if relator_cands:
        candidatas = relator_cands

    # Ordenar por dataDesignacao (mais recente primeiro)
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
    Busca as últimas movimentações (informes legislativos) do Senado.

    Endpoint: GET https://legis.senado.leg.br/dadosabertos/processo/{id}?v=1

    Args:
        codigo_materia: Código da matéria (não usado, mantido para compatibilidade)
        id_processo_senado: ID do processo no Senado
        limite: Número máximo de movimentações
        debug: Modo debug
        
    Returns:
        Lista de dicts com movimentações
        
    Cada dict contém:
      - data: Data formatada (DD/MM/YYYY)
      - hora: Hora (HH:MM)
      - orgao: Sigla do órgão
      - descricao: Descrição da movimentação
    """
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

    # Tentar JSON
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

    # Fallback XML
    if not informes:
        try:
            root = ET.fromstring(resp.content)
            informes_xml = root.findall(".//informesLegislativos//informeLegislativo")
            for it in informes_xml:
                data_txt = (it.findtext("data") or "").strip()
                desc = (it.findtext("descricao") or "").strip()
                coleg_sigla = (it.findtext(".//colegiado/sigla") or "").strip()
                informes.append({
                    "data": data_txt,
                    "descricao": desc,
                    "colegiado": {"sigla": coleg_sigla}
                })
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
            sort_key = datetime.datetime.min

        movs.append({
            "data": data_br,
            "hora": hora,
            "orgao": org_sigla,
            "descricao": desc,
            "_sort": sort_key
        })

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
    Obtém SITUAÇÃO ATUAL e ÓRGÃO ATUAL no Senado.
    
    Endpoint: GET https://legis.senado.leg.br/dadosabertos/processo/{id}?v=1

    Args:
        id_processo_senado: ID do processo no Senado
        debug: Modo debug
        
    Returns:
        Dict com situação e órgão atual
        
    Retorna dict:
      - situacao_senado: Descrição da situação atual
      - orgao_senado_sigla: Sigla do órgão
      - orgao_senado_nome: Nome do órgão
    """
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


# ============================================================
# ENRIQUECIMENTO DE PROPOSIÇÕES
# ============================================================

def enriquecer_proposicao_com_senado(proposicao_dict: Dict, debug: bool = False) -> Dict:
    """
    Adiciona informações do Senado a uma proposição da Câmara.
    
    REGRA DE NEGÓCIO: Só consulta o Senado se a situação for "Apreciação pelo Senado Federal".
    IMPORTANTE: O número da Câmara é IGUAL ao número do Senado (não existe conversão).
    
    Args:
        proposicao_dict: Dicionário com dados da proposição da Câmara
        debug: Modo debug
        
    Returns:
        Dicionário enriquecido com dados do Senado (colunas originais preservadas)
        
    Campos adicionados:
    - no_senado: bool
    - codigo_materia_senado: str (CodigoMateria)
    - id_processo_senado: str
    - situacao_senado: str
    - url_senado: str (deep link)
    - tipo_numero_senado: str
    - Relator_Senado: str (relator formatado do Senado)
    - Orgao_Senado_Sigla: str
    - Orgao_Senado_Nome: str
    - UltimasMov_Senado: str (movimentações formatadas)
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
    resultado["id_processo_senado"] = ""
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
        resultado["id_processo_senado"] = dados_senado.get("id_processo_senado", "")
        resultado["situacao_senado"] = dados_senado.get("situacao_senado", "")
        resultado["url_senado"] = dados_senado.get("url_senado", "")
        resultado["tipo_numero_senado"] = (
            f"{dados_senado.get('tipo_senado', '')} "
            f"{dados_senado.get('numero_senado', '')}/"
            f"{dados_senado.get('ano_senado', '')}"
        ).strip()
        codigo_materia = dados_senado.get("codigo_senado", "")
        
        # 1.1 Buscar status atual e movimentações do Senado
        id_proc_sen = dados_senado.get("id_processo_senado", "")
        if id_proc_sen:
            status_sen = buscar_status_senado_por_processo(id_proc_sen, debug=debug)
            if status_sen:
                # Situação atual no Senado
                if status_sen.get("situacao_senado"):
                    resultado["situacao_senado"] = status_sen.get("situacao_senado", "")
                # Órgão atual (Senado)
                if status_sen.get("orgao_senado_sigla"):
                    resultado["Orgao_Senado_Sigla"] = status_sen.get("orgao_senado_sigla", "")
                if status_sen.get("orgao_senado_nome"):
                    resultado["Orgao_Senado_Nome"] = status_sen.get("orgao_senado_nome", "")

            movs = buscar_movimentacoes_senado(
                codigo_materia,
                id_processo_senado=id_proc_sen,
                limite=10,
                debug=debug
            )
            if movs:
                # Texto pronto para expander
                linhas = []
                for mv in movs:
                    linhas.append(
                        f"{mv.get('data','')} {mv.get('hora','')}".strip() + 
                        " | " + (mv.get('orgao','') or "—") + 
                        " | " + (mv.get('descricao','') or "")
                    )
                resultado["UltimasMov_Senado"] = "\n".join(linhas)

        # 2. Buscar detalhes em endpoints separados (/relatorias)
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


def processar_lista_com_senado(
    df_proposicoes: pd.DataFrame,
    debug: bool = False,
    mostrar_progresso: bool = True
) -> pd.DataFrame:
    """
    Processa lista de proposições e enriquece com dados do Senado quando necessário.
    
    IMPORTANTE: APENAS ABA 5 PODE CHAMAR ESTA FUNÇÃO.
    
    Args:
        df_proposicoes: DataFrame com proposições da Câmara
        debug: Modo debug
        mostrar_progresso: Mostrar barra de progresso
        
    Returns:
        DataFrame enriquecido (colunas originais + colunas do Senado)
        
    REGRA: Só consulta o Senado para proposições com situação "Apreciação pelo Senado Federal".
    IMPORTANTE: Preserva TODAS as colunas originais do DataFrame!
    """
    # ============================================================
    # GATE: Apenas Aba 5 pode chamar
    # ============================================================
    if not pode_chamar_senado():
        import inspect
        caller = inspect.stack()[1]
        print(f"[SENADO-GATE] ❌ BLOQUEADO - Chamada de {caller.function} (linha {caller.lineno})")
        print(f"[SENADO-GATE] ℹ️ Senado só permitido na Aba 5. Aba atual: {st.session_state.get('aba_atual_senado', None)}")
        # Retornar DataFrame sem modificações
        return df_proposicoes.copy() if not df_proposicoes.empty else df_proposicoes
    
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
                time.sleep(0.1)  # Rate limiting
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


# ============================================================
# FUNÇÕES DE APOIO — FOTO, CÓDIGO, UNIFICAÇÃO
# Adicionadas v50 (extraídas do monólito)
# ============================================================

def buscar_codigo_senador_por_nome(nome_senador: str) -> Optional[str]:
    """
    Busca o código do senador pelo nome para obter a foto.
    
    Endpoint: https://legis.senado.leg.br/dadosabertos/senador/lista/atual
    
    Returns:
        Código do senador ou None
    """
    if not nome_senador:
        return None
    
    nome_busca = nome_senador.lower().strip()
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
    """
    if not codigo_senador and nome_senador:
        codigo_senador = buscar_codigo_senador_por_nome(nome_senador)
    
    if codigo_senador:
        return f"https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo_senador}.jpg"
    
    return None


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
    todas_tramitacoes = []
    
    # Processar tramitações da Câmara
    if not df_tramitacoes_camara.empty:
        for _, row in df_tramitacoes_camara.iterrows():
            data_str = str(row.get("Data", "") or row.get("data", ""))
            hora_str = str(row.get("Hora", "") or row.get("hora", "") or "")
            descricao = str(
                row.get("Tramitação", "") or row.get("Descrição", "")
                or row.get("descricao", "") or row.get("descricaoTramitacao", "")
            )
            orgao = str(row.get("Órgão", "") or row.get("orgao", "") or row.get("siglaOrgao", ""))
            
            dt_sort = None
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    dt_sort = datetime.datetime.strptime(data_str[:19], fmt)
                    break
                except Exception:
                    continue
            
            todas_tramitacoes.append({
                "Data": data_str,
                "Hora": hora_str,
                "Casa": "🏛️ CD",
                "Órgão": orgao,
                "Tramitação": descricao[:200] if descricao else "",
                "_sort": dt_sort or datetime.datetime.min
            })
    
    # Processar movimentações do Senado
    for mov in movimentacoes_senado:
        data_str = mov.get("data", "")
        hora = mov.get("hora", "")
        orgao = mov.get("orgao", "")
        descricao = mov.get("descricao", "")
        
        dt_sort = None
        data_completa = f"{data_str} {hora}".strip() if hora else data_str
        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt_sort = datetime.datetime.strptime(data_completa[:16], fmt)
                break
            except Exception:
                continue
        
        todas_tramitacoes.append({
            "Data": data_str,
            "Hora": hora,
            "Casa": "🏛️ SF",
            "Órgão": orgao,
            "Tramitação": descricao[:200] if descricao else "",
            "_sort": dt_sort or datetime.datetime.min
        })
    
    if not todas_tramitacoes:
        return pd.DataFrame()
    
    df = pd.DataFrame(todas_tramitacoes)
    df = df.sort_values("_sort", ascending=False)
    df = df.drop(columns=["_sort"])
    df = df.head(limite)
    
    cols_order = ["Data", "Hora", "Casa", "Órgão", "Tramitação"]
    df = df[[c for c in cols_order if c in df.columns]]
    
    return df
