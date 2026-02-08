# core/services/apensados.py
"""
Serviço de Apensados — Gestão de Proposições Apensadas

Contém toda a lógica de busca e mapeamento de proposições
apensadas (tramitando em conjunto) na Câmara dos Deputados.

Extraído do monólito v50.

Funcionalidades:
- Mapeamento estático de apensamentos (MAPEAMENTO_APENSADOS_COMPLETO)
- Proposições faltantes na API (PROPOSICOES_FALTANTES_API)
- Busca dinâmica de apensamentos via API
- Descoberta de proposição principal
"""
from __future__ import annotations

from typing import Dict, List, Optional
import re
import time
import datetime
from datetime import timezone

import streamlit as st
import requests
import pandas as pd

from core.utils.links import extract_id_from_uri

# ============================================================
# CONFIGURAÇÃO
# ============================================================
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)"}

try:
    import certifi
    _REQUESTS_VERIFY = certifi.where()
except ImportError:
    _REQUESTS_VERIFY = True


# ============================================================
# CONSTANTES — MAPEAMENTO DE APENSADOS
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

MAPEAMENTO_APENSADOS = {k: v["principal"] for k, v in MAPEAMENTO_APENSADOS_COMPLETO.items()}




# ============================================================
# FUNÇÕES DE BUSCA — API DA CÂMARA
# ============================================================

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
    # Lazy imports para evitar dependência circular com o monólito
    from monitor_sistema_jz import fetch_proposicao_completa, fetch_relator_atual
    
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
# FUNÇÕES DE RELAÇÃO — PROPOSIÇÃO PRINCIPAL
# ============================================================

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


