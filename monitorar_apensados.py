#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitorar_apensados.py
========================================
Monitor de tramitações dos PLs RAIZ que têm projetos da 
Deputada Júlia Zanatta apensados.

Este robô NÃO monitora os PLs da deputada (que não tramitam mais),
mas sim os PLs RAIZ da cadeia de apensamentos.

✅ DETECÇÃO AUTOMÁTICA com CADEIA COMPLETA!

Exemplo de cadeia:
  PL 2098/2024 (Zanatta) → PL 5499/2020 → PL 5344/2020 → PL 10556/2018 (RAIZ)
  O robô monitora o PL 10556/2018 (onde tramita de verdade)

Horário: 08:00 às 20:00 (Brasília) - Segunda a Sexta
Frequência: A cada 3 horas (via GitHub Actions)

v3.0 - 27/01/2026 - Cadeia completa de apensamentos + PL raiz
"""

import os
import sys
import json
import html
import re
import requests
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorApensadosZanatta/3.0 (gabinete-julia-zanatta)"}

DEPUTADA_ID = 220559  # Júlia Zanatta

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Arquivo para guardar estado entre execuções
ESTADO_FILE = Path("estado_apensados.json")

# Arquivo para guardar histórico de notificações
HISTORICO_FILE = Path("historico_apensados.json")

# ============================================================
# MAPEAMENTO COMPLETO - PL RAIZ
# ============================================================
# Formato: {id: {"principal": "PL X", "raiz": "PL Y", "cadeia": ["PL A", ...]}}
MAPEAMENTO_APENSADOS_COMPLETO = {
    "2361454": {"principal": "PL 1620/2023", "raiz": "PL 1620/2023", "cadeia": ["PL 1620/2023"]},
    "2361794": {"principal": "PL 2782/2022", "raiz": "PL 2782/2022", "cadeia": ["PL 2782/2022"]},
    "2365600": {"principal": "PL 9417/2017", "raiz": "PL 9417/2017", "cadeia": ["PL 9417/2017"]},
    "2381193": {"principal": "PL 3593/2020", "raiz": "PL 3593/2020", "cadeia": ["PL 3593/2020"]},
    "2396351": {"principal": "PL 5065/2016", "raiz": "PL 5065/2016", "cadeia": ["PL 5065/2016"]},
    "2399426": {"principal": "PL 736/2022", "raiz": "PL 736/2022", "cadeia": ["PL 736/2022"]},
    "2423254": {"principal": "PL 776/2024", "raiz": "PL 776/2024", "cadeia": ["PL 776/2024"]},
    "2436763": {"principal": "PL 5499/2020", "raiz": "PL 10556/2018", "cadeia": ["PL 5499/2020", "PL 5344/2020", "PL 10556/2018"]},
    "2455562": {"principal": "PL 2829/2023", "raiz": "PL 2829/2023", "cadeia": ["PL 2829/2023"]},
    "2455568": {"principal": "PL 4068/2020", "raiz": "PL 4068/2020", "cadeia": ["PL 4068/2020"]},
    "2462038": {"principal": "PL 1036/2019", "raiz": "PL 1036/2019", "cadeia": ["PL 1036/2019"]},
    "2485135": {"principal": "PL 606/2022", "raiz": "PL 606/2022", "cadeia": ["PL 606/2022"]},
    "2531615": {"principal": "PL 2617/2025", "raiz": "PL 2617/2025", "cadeia": ["PL 2617/2025"]},
    "2567301": {"principal": "PL 1500/2025", "raiz": "PL 1500/2025", "cadeia": ["PL 1500/2025"]},
    "2570510": {"principal": "PL 503/2025", "raiz": "PL 503/2025", "cadeia": ["PL 503/2025"]},
    "2571359": {"principal": "PL 6198/2023", "raiz": "PL 6198/2023", "cadeia": ["PL 6198/2023"]},
    "2372482": {"principal": "PLP 316/2016", "raiz": "PLP 316/2016", "cadeia": ["PLP 316/2016"]},
    "2390310": {"principal": "PLP 156/2012", "raiz": "PLP 156/2012", "cadeia": ["PLP 156/2012"]},
    "2439451": {"principal": "PL 4019/2021", "raiz": "PL 4019/2021", "cadeia": ["PL 4019/2021"]},
    "2483453": {"principal": "PLP 235/2024", "raiz": "PLP 235/2024", "cadeia": ["PLP 235/2024"]},
    "2482260": {"principal": "PDL 3/2025", "raiz": "PDL 3/2025", "cadeia": ["PDL 3/2025"]},
    "2482169": {"principal": "PDL 3/2025", "raiz": "PDL 3/2025", "cadeia": ["PDL 3/2025"]},
    "2374405": {"principal": "PDL 174/2023", "raiz": "PDL 174/2023", "cadeia": ["PDL 174/2023"]},
    "2374340": {"principal": "PDL 174/2023", "raiz": "PDL 174/2023", "cadeia": ["PDL 174/2023"]},
    "2419264": {"principal": "PDL 3/2024", "raiz": "PDL 3/2024", "cadeia": ["PDL 3/2024"]},
    "2375447": {"principal": "PDL 183/2023", "raiz": "PDL 183/2023", "cadeia": ["PDL 183/2023"]},
    "2456691": {"principal": "PDL 285/2024", "raiz": "PDL 285/2024", "cadeia": ["PDL 285/2024"]},
    "2390075": {"principal": "PDL 302/2023", "raiz": "PDL 302/2023", "cadeia": ["PDL 302/2023"]},
    "2448732": {"principal": "PEC 8/2021", "raiz": "PEC 8/2021", "cadeia": ["PEC 8/2021"]},
}

MAPEAMENTO_APENSADOS = {k: v["principal"] for k, v in MAPEAMENTO_APENSADOS_COMPLETO.items()}

# ============================================================
# PROPOSIÇÕES FALTANTES (que a API não retorna corretamente)
# ============================================================
PROPOSICOES_FALTANTES_API = {
    "220559": [  # Julia Zanatta
        {"id": "2347150", "siglaTipo": "PL", "numero": "321", "ano": "2023", "ementa": "Altera dispositivos da Lei nº 9.394"},
        {"id": "2361454", "siglaTipo": "PL", "numero": "2472", "ano": "2023", "ementa": "Acompanhante escolas TEA"},
        {"id": "2361794", "siglaTipo": "PL", "numero": "2501", "ano": "2023", "ementa": "Crime de censura"},
        {"id": "2365600", "siglaTipo": "PL", "numero": "2815", "ano": "2023", "ementa": "Bagagem de mão aeronaves"},
        {"id": "2381193", "siglaTipo": "PL", "numero": "4045", "ano": "2023", "ementa": "Impedimento OAB/STF"},
        {"id": "2396351", "siglaTipo": "PL", "numero": "5021", "ano": "2023", "ementa": "Organizações terroristas"},
        {"id": "2399426", "siglaTipo": "PL", "numero": "5198", "ano": "2023", "ementa": "ONGs estrangeiras"},
        {"id": "2372482", "siglaTipo": "PLP", "numero": "141", "ano": "2023", "ementa": "Inelegibilidade"},
        {"id": "2374405", "siglaTipo": "PDL", "numero": "194", "ano": "2023", "ementa": "Susta Decreto armas"},
        {"id": "2374340", "siglaTipo": "PDL", "numero": "189", "ano": "2023", "ementa": "Susta Decreto armas"},
        {"id": "2375447", "siglaTipo": "PDL", "numero": "209", "ano": "2023", "ementa": "Susta Resolução ANS"},
        {"id": "2390075", "siglaTipo": "PDL", "numero": "337", "ano": "2023", "ementa": "Susta Resolução CONAMA"},
        {"id": "2390310", "siglaTipo": "PLP", "numero": "178", "ano": "2023", "ementa": "Coautoria"},
        {"id": "2419264", "siglaTipo": "PDL", "numero": "30", "ano": "2024", "ementa": "Susta Resolução TSE"},
        {"id": "2423254", "siglaTipo": "PL", "numero": "955", "ano": "2024", "ementa": "Vacinação"},
        {"id": "2436763", "siglaTipo": "PL", "numero": "2098", "ano": "2024", "ementa": "Produtos alimentícios"},
        {"id": "2439451", "siglaTipo": "PL", "numero": "2286", "ano": "2024", "ementa": "Coautoria"},
        {"id": "2448732", "siglaTipo": "PEC", "numero": "28", "ano": "2024", "ementa": "Mandado segurança coletivo"},
        {"id": "2455562", "siglaTipo": "PL", "numero": "3338", "ano": "2024", "ementa": "Direito dos pais"},
        {"id": "2455568", "siglaTipo": "PL", "numero": "3341", "ano": "2024", "ementa": "Moeda digital DREX"},
        {"id": "2456691", "siglaTipo": "PDL", "numero": "348", "ano": "2024", "ementa": "Susta IN banheiros"},
        {"id": "2462038", "siglaTipo": "PL", "numero": "3887", "ano": "2024", "ementa": "CLT contribuição sindical"},
        {"id": "2482169", "siglaTipo": "PDL", "numero": "16", "ano": "2025", "ementa": "Susta Decreto PIX"},
        {"id": "2482260", "siglaTipo": "PDL", "numero": "24", "ano": "2025", "ementa": "Susta Decreto PIX"},
        {"id": "2483453", "siglaTipo": "PLP", "numero": "19", "ano": "2025", "ementa": "Sigilo financeiro"},
        {"id": "2485135", "siglaTipo": "PL", "numero": "623", "ano": "2025", "ementa": "CPC"},
    ]
}


# ============================================================
# FUNÇÕES DE CADEIA DE APENSAMENTOS
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
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            if dados:
                return str(dados[0].get("id", ""))
    except:
        pass
    
    return ""


def buscar_pl_principal_nas_tramitacoes(prop_id: str) -> str:
    """Busca o PL principal nas tramitações de uma proposição"""
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}/tramitacoes"
        params = {"itens": 30, "ordem": "DESC"}
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            tramitacoes = resp.json().get("dados", [])
            
            for tram in tramitacoes:
                texto = " ".join([
                    str(tram.get("despacho", "") or ""),
                    str(tram.get("descricaoTramitacao", "") or ""),
                ])
                
                patterns = [
                    r'[Aa]pense-se\s+[àa](?:\(ao\))?\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
                    r'[Aa]pensad[oa]\s+(?:à|ao|a)\s*([A-Z]{2,4})[\s\-]*(\d+)/(\d{4})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, texto, re.IGNORECASE)
                    if match:
                        tipo = match.group(1).upper()
                        numero = match.group(2)
                        ano = match.group(3)
                        return f"{tipo} {numero}/{ano}"
    except:
        pass
    
    return None


def buscar_cadeia_apensamentos(id_proposicao: str, max_niveis: int = 10) -> list:
    """
    Busca a cadeia completa de apensamentos até o PL raiz.
    
    Ex: PL 5499/2020 → PL 5344/2020 → PL 10556/2018 (raiz)
    
    Returns:
        Lista de dicionários com {pl, id, situacao} de cada nível
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
            resp = requests.get(url, headers=HEADERS, timeout=10)
            
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
                # Este é o PL raiz
                print(f"[CADEIA] Nível {nivel}: {pl_nome} é o PL RAIZ")
                break
            
            # Buscar o próximo nível
            proximo_id = None
            
            # Primeiro verificar no dicionário
            if id_atual in MAPEAMENTO_APENSADOS:
                pl_pai = MAPEAMENTO_APENSADOS[id_atual]
                match = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_pai)
                if match:
                    proximo_id = buscar_id_proposicao(match.group(1), match.group(2), match.group(3))
            
            if not proximo_id:
                # Buscar nas tramitações
                pl_pai = buscar_pl_principal_nas_tramitacoes(id_atual)
                if pl_pai:
                    match = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_pai)
                    if match:
                        proximo_id = buscar_id_proposicao(match.group(1), match.group(2), match.group(3))
            
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
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
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
        resp_tram = requests.get(url_tram, params={"itens": 1, "ordem": "DESC"}, headers=HEADERS, timeout=10)
        
        if resp_tram.status_code == 200:
            tramitacoes = resp_tram.json().get("dados", [])
            if tramitacoes:
                data_hora = tramitacoes[0].get("dataHora", "")
                if data_hora:
                    try:
                        if "T" in data_hora:
                            dt = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                        else:
                            dt = datetime.strptime(data_hora[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        
                        dados["data_ultima_mov"] = dt.strftime("%d/%m/%Y")
                        agora = datetime.now(timezone.utc)
                        dados["dias_parado"] = (agora - dt).days
                    except:
                        dados["data_ultima_mov"] = data_hora[:10] if data_hora else "—"
    
    except Exception as e:
        print(f"[PL_RAIZ] Erro ao buscar dados: {e}")
    
    return dados


# ============================================================
# DETECÇÃO DE PROJETOS APENSADOS COM CADEIA COMPLETA
# ============================================================

def buscar_projetos_apensados_automatico() -> list:
    """
    Busca projetos da deputada que estão apensados usando MAPEAMENTO COMPLETO.
    
    Vai direto para o PL RAIZ (sem precisar seguir cadeia dinamicamente).
    
    Returns:
        Lista de dicionários com dados para monitoramento
    """
    print("[APENSADOS] Usando mapeamento completo (v3.0)...")
    
    projetos_apensados = []
    
    try:
        # 1. Buscar todas as proposições da deputada
        todas_props = []
        tipos = ["PL", "PLP", "PDL", "PEC", "PRC"]
        
        for tipo in tipos:
            url = f"{BASE_URL}/proposicoes"
            params = {
                "idDeputadoAutor": DEPUTADA_ID,
                "siglaTipo": tipo,
                "dataApresentacaoInicio": "2023-01-01",
                "itens": 100,
                "ordem": "DESC",
                "ordenarPor": "dataApresentacao"
            }
            
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    dados = resp.json().get("dados", [])
                    todas_props.extend(dados)
            except Exception as e:
                print(f"[APENSADOS] Erro ao buscar {tipo}: {e}")
            
            time.sleep(0.2)
        
        # Adicionar proposições faltantes
        id_str = str(DEPUTADA_ID)
        if id_str in PROPOSICOES_FALTANTES_API:
            for prop_faltante in PROPOSICOES_FALTANTES_API[id_str]:
                ids_existentes = [str(p.get("id")) for p in todas_props]
                if str(prop_faltante.get("id")) not in ids_existentes:
                    todas_props.append(prop_faltante)
        
        print(f"[APENSADOS] Total de proposições: {len(todas_props)}")
        
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
                
                # Buscar ID do PL RAIZ
                match_raiz = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_raiz)
                id_raiz = ""
                if match_raiz:
                    id_raiz = buscar_id_proposicao(match_raiz.group(1), match_raiz.group(2), match_raiz.group(3))
                
                if id_raiz:
                    projetos_apensados.append({
                        "pl": pl_raiz,
                        "id": id_raiz,
                        "tema": ementa[:80] + "..." if len(ementa) > 80 else ementa,
                        "pl_zanatta": prop_nome,
                        "pl_principal": pl_principal,
                        "cadeia": cadeia,
                    })
            
            time.sleep(0.1)
        
        # Remover duplicatas (PLs Zanatta diferentes podem ter mesmo PL raiz)
        pls_raiz_unicos = {}
        for p in projetos_apensados:
            id_raiz = p.get("id", "")
            if id_raiz not in pls_raiz_unicos:
                pls_raiz_unicos[id_raiz] = p
            else:
                existing = pls_raiz_unicos[id_raiz]
                if "pls_zanatta" not in existing:
                    existing["pls_zanatta"] = [existing.get("pl_zanatta", "")]
                existing["pls_zanatta"].append(p.get("pl_zanatta", ""))
        
        projetos_unicos = list(pls_raiz_unicos.values())
        
        print(f"[APENSADOS] ✅ {len(projetos_unicos)} PLs raiz para monitorar")
        
        return projetos_unicos
    
    except Exception as e:
        print(f"[APENSADOS] ❌ Erro: {e}")
        return []


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_brasilia_tz():
    """Retorna o timezone de Brasília"""
    return timezone(timedelta(hours=-3))


def obter_data_hora_brasilia():
    """Retorna data e hora atual em Brasília formatada"""
    agora = datetime.now(get_brasilia_tz())
    return agora.strftime("%d/%m/%Y às %H:%M")


def carregar_estado():
    """Carrega estado da última execução"""
    if ESTADO_FILE.exists():
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def salvar_estado(teve_novidade: bool):
    """Salva estado da execução atual"""
    estado = {
        "ultima_execucao": datetime.now(get_brasilia_tz()).isoformat(),
        "ultima_novidade": teve_novidade
    }
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def carregar_historico():
    """Carrega histórico de tramitações já notificadas"""
    if HISTORICO_FILE.exists():
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"notificados": []}
    return {"notificados": []}


def salvar_historico(historico: dict):
    """Salva histórico de tramitações notificadas"""
    if len(historico.get("notificados", [])) > 1000:
        historico["notificados"] = historico["notificados"][-500:]
    
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def gerar_hash_tramitacao(prop_id: str, data: str, descricao: str) -> str:
    """Gera hash único para identificar uma tramitação"""
    texto = f"{prop_id}|{data}|{descricao[:100]}"
    return str(hash(texto))


def buscar_ultima_tramitacao(prop_id: str) -> dict:
    """Busca a última tramitação de uma proposição"""
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}/tramitacoes"
        params = {"itens": 1, "ordem": "DESC", "ordenarPor": "dataHora"}
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            if dados:
                return dados[0]
        return None
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar tramitação: {e}")
        return None


def buscar_dados_proposicao(prop_id: str) -> dict:
    """Busca dados básicos de uma proposição"""
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            return resp.json().get("dados", {})
        return {}
    except:
        return {}


# ============================================================
# ENVIO DE NOTIFICAÇÕES
# ============================================================

def enviar_telegram(mensagem: str, parse_mode: str = "HTML") -> bool:
    """Envia mensagem para o Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Token ou Chat ID não configurado")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        resp = requests.post(url, json=payload, timeout=30)
        
        if resp.status_code == 200:
            print("[TELEGRAM] ✅ Mensagem enviada com sucesso")
            return True
        else:
            print(f"[TELEGRAM] ❌ Erro: {resp.status_code} - {resp.text}")
            return False
    
    except Exception as e:
        print(f"[TELEGRAM] ❌ Exceção: {e}")
        return False


def formatar_mensagem_tramitacao(proj: dict, tram: dict, dados_prop: dict) -> str:
    """Formata mensagem de tramitação para o Telegram"""
    
    # Dados básicos
    pl = proj.get("pl", "—")
    pl_zanatta = proj.get("pl_zanatta", "")
    pls_zanatta = proj.get("pls_zanatta", [pl_zanatta] if pl_zanatta else [])
    tema = proj.get("tema", "")
    prop_id = proj.get("id", "")
    
    # Dados da tramitação
    data_hora = tram.get("dataHora", "")
    orgao = tram.get("siglaOrgao", "—")
    despacho = tram.get("despacho", "")
    descricao = tram.get("descricaoTramitacao", "")
    
    # Formatar data
    data_fmt = "—"
    if data_hora:
        try:
            dt = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
            data_fmt = dt.strftime("%d/%m/%Y %H:%M")
        except:
            data_fmt = data_hora[:16] if data_hora else "—"
    
    # Status atual
    status = dados_prop.get("statusProposicao", {})
    situacao = status.get("descricaoSituacao", "—")
    
    # Determinar urgência
    urgencia = ""
    situacao_lower = situacao.lower()
    despacho_lower = despacho.lower() if despacho else ""
    
    if "pronta para pauta" in situacao_lower:
        urgencia = "🔴 PRONTA PARA PAUTA"
    elif "designad" in despacho_lower and "relator" in despacho_lower:
        urgencia = "⚠️ RELATOR DESIGNADO"
    elif "aprovad" in despacho_lower:
        urgencia = "✅ APROVADO"
    elif "rejeitad" in despacho_lower:
        urgencia = "❌ REJEITADO"
    elif "parecer" in despacho_lower:
        urgencia = "📋 PARECER"
    
    # Link
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
    
    # PLs da Zanatta afetados
    if len(pls_zanatta) > 1:
        pls_str = ", ".join(pls_zanatta)
        zanatta_info = f"📌 PLs da Deputada: {pls_str}"
    else:
        zanatta_info = f"📌 PL da Deputada: {pls_zanatta[0] if pls_zanatta else pl_zanatta}"
    
    # Montar mensagem
    msg = f"""📎 <b>MOVIMENTAÇÃO - PL RAIZ</b>

<b>{pl}</b>
{zanatta_info}

{urgencia}

📅 <b>Data:</b> {data_fmt}
🏛️ <b>Órgão:</b> {orgao}
📊 <b>Situação:</b> {situacao}

📝 <b>Tramitação:</b>
{descricao}

💬 <b>Despacho:</b>
{despacho if despacho else "—"}

🔗 <a href="{link}">Ver tramitação completa</a>
"""
    
    return msg


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    """Função principal do monitor"""
    
    print("=" * 60)
    print("🔄 MONITOR DE APENSADOS v3.0 - CADEIA COMPLETA")
    print(f"⏰ {obter_data_hora_brasilia()}")
    print("=" * 60)
    
    # Verificar credenciais
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM não configurado - executando em modo teste")
    
    # Carregar histórico
    historico = carregar_historico()
    notificados = set(historico.get("notificados", []))
    
    # Detectar projetos apensados com cadeia completa
    projetos = buscar_projetos_apensados_automatico()
    
    if not projetos:
        print("⚠️ Nenhum projeto apensado encontrado")
        salvar_estado(False)
        return
    
    print(f"\n📋 Monitorando {len(projetos)} PLs RAIZ")
    print("-" * 40)
    
    novidades = []
    
    # Verificar cada PL RAIZ
    for proj in projetos:
        pl = proj.get("pl", "")
        prop_id = proj.get("id", "")
        
        print(f"\n🔍 Verificando: {pl} (ID: {prop_id})")
        
        # Buscar última tramitação
        tram = buscar_ultima_tramitacao(prop_id)
        
        if not tram:
            print(f"   ⚠️ Sem tramitações")
            continue
        
        # Gerar hash para identificar
        data = tram.get("dataHora", "")
        descricao = tram.get("descricaoTramitacao", "")
        hash_tram = gerar_hash_tramitacao(prop_id, data, descricao)
        
        # Verificar se já foi notificado
        if hash_tram in notificados:
            print(f"   ✅ Já notificado anteriormente")
            continue
        
        # Verificar se é recente (últimas 24h)
        if data:
            try:
                dt = datetime.fromisoformat(data.replace("Z", "+00:00"))
                agora = datetime.now(timezone.utc)
                diff = agora - dt
                
                if diff.total_seconds() > 86400:  # Mais de 24h
                    print(f"   ⏰ Tramitação antiga ({diff.days} dias)")
                    continue
            except:
                pass
        
        # Nova tramitação!
        print(f"   🆕 NOVA TRAMITAÇÃO!")
        
        # Buscar dados completos
        dados_prop = buscar_dados_proposicao(prop_id)
        
        # Formatar e enviar
        mensagem = formatar_mensagem_tramitacao(proj, tram, dados_prop)
        
        if enviar_telegram(mensagem):
            notificados.add(hash_tram)
            novidades.append(pl)
        
        time.sleep(1)  # Rate limit
    
    # Salvar histórico
    historico["notificados"] = list(notificados)
    salvar_historico(historico)
    
    # Salvar estado
    teve_novidade = len(novidades) > 0
    salvar_estado(teve_novidade)
    
    # Resumo
    print("\n" + "=" * 60)
    if novidades:
        print(f"✅ {len(novidades)} novidade(s) notificada(s):")
        for n in novidades:
            print(f"   - {n}")
    else:
        print("✅ Nenhuma novidade encontrada")
    print("=" * 60)


if __name__ == "__main__":
    main()
