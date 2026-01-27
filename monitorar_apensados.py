#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitorar_apensados.py
========================================
Monitor de tramitações dos PLs PRINCIPAIS que têm projetos da 
Deputada Júlia Zanatta apensados.

Este robô NÃO monitora os PLs da deputada (que não tramitam mais),
mas sim os PLs PRINCIPAIS aos quais eles foram apensados.

✅ DETECÇÃO HÍBRIDA: 
   - Usa dicionário de mapeamentos conhecidos (confiável)
   - Tenta detectar novos via tramitações (automático)

Horário: 08:00 às 20:00 (Brasília) - Segunda a Sexta
Frequência: A cada 3 horas (via GitHub Actions)

v2.1 - 27/01/2026 - Detecção híbrida de apensados
"""

import os
import sys
import json
import html
import re
import hashlib
import requests
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorApensadosZanatta/2.1 (gabinete-julia-zanatta)"}

DEPUTADA_ID = 220559  # Júlia Zanatta

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Arquivo para guardar estado entre execuções
ESTADO_FILE = Path("estado_apensados.json")

# Arquivo para guardar histórico de notificações
HISTORICO_FILE = Path("historico_apensados.json")

# ============================================================
# PROPOSIÇÕES FALTANTES (que a API não retorna corretamente)
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
# MAPEAMENTO DE APENSADOS CONHECIDOS
# ============================================================
# Fonte: Relatório de Pesquisa da Câmara dos Deputados
# Formato: ID da proposição da deputada → PL principal

MAPEAMENTO_APENSADOS = {
    "2361454": "PL 1620/2023",      # PL 2472/2023 - TEA/Acompanhante escolas
    "2361794": "PL 2782/2022",      # PL 2501/2023 - Crime de censura
    "2365600": "PL 9417/2017",      # PL 2815/2023 - Bagagem de mão
    "2372482": "PLP 316/2016",      # PLP 141/2023 - Inelegibilidade
    "2381193": "PL 3593/2020",      # PL 4045/2023 - OAB/STF
    "2390310": "PLP 156/2012",      # PLP (coautoria) 
    "2396351": "PL 5065/2016",      # PL 5021/2023 - Organizações terroristas
    "2399426": "PL 736/2022",       # PL 5198/2023 - ONGs estrangeiras
    "2423254": "PL 776/2024",       # PL 955/2024 - Vacinação
    "2436763": "PL 5499/2020",      # PL 2098/2024 - Produtos alimentícios
    "2439451": "PL 4019/2021",      # PL (coautoria)
    "2455562": "PL 2829/2023",      # PL 3338/2024 - Direito dos pais
    "2455568": "PL 4068/2020",      # PL 3341/2024 - Moeda digital/DREX
    "2462038": "PL 1036/2019",      # PL 3887/2024 - CLT/Contribuição sindical
    "2483453": "PLP 235/2024",      # PLP 19/2025 - Sigilo financeiro
    "2485135": "PL 606/2022",       # PL 623/2025 - CPC
    "2531615": "PL 2617/2025",      # PL 3222/2025 - Prisão preventiva
    "2567301": "PL 1500/2025",      # PL 4954/2025 - Maria da Penha masculina
    "2570510": "PL 503/2025",       # PL 5072/2025 - Paternidade socioafetiva
    "2571359": "PL 6198/2023",      # PL 5128/2025 - Maria da Penha/Falsas denúncias
}


# ============================================================
# FUNÇÕES DE DETECÇÃO DE APENSADOS
# ============================================================

def extrair_pl_principal_do_texto(texto: str) -> str:
    """
    Extrai o PL principal de um texto de despacho/tramitação.
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
            return f"{tipo} {numero}/{ano}"
    
    return None


def buscar_pl_principal_nas_tramitacoes(prop_id: str) -> str:
    """
    Busca nas tramitações de uma proposição para encontrar o PL principal.
    """
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}/tramitacoes"
        params = {"itens": 30, "ordem": "DESC", "ordenarPor": "dataHora"}
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if resp.status_code != 200:
            return None
        
        tramitacoes = resp.json().get("dados", [])
        
        for tram in tramitacoes:
            texto = " ".join([
                str(tram.get("despacho", "") or ""),
                str(tram.get("descricaoTramitacao", "") or ""),
                str(tram.get("descricaoSituacao", "") or ""),
            ])
            
            resultado = extrair_pl_principal_do_texto(texto)
            if resultado:
                return resultado
        
        return None
    
    except Exception as e:
        print(f"[APENSADOS] Erro ao buscar tramitações de {prop_id}: {e}")
        return None


def buscar_id_proposicao(pl_str: str) -> str:
    """Busca o ID de uma proposição pelo formato 'PL 1234/2023'"""
    match = re.match(r'([A-Z]{2,4})\s*(\d+)/(\d{4})', pl_str)
    if not match:
        return ""
    
    sigla_tipo = match.group(1)
    numero = match.group(2)
    ano = match.group(3)
    
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


def buscar_projetos_apensados() -> list:
    """
    Busca todos os projetos da deputada que estão apensados.
    
    Usa abordagem HÍBRIDA:
    1. Identifica projetos com situação "Tramitando em Conjunto"
    2. Usa dicionário de mapeamentos para encontrar o PL principal
    3. Se não estiver no dicionário, tenta buscar nas tramitações
    """
    print("[APENSADOS] Buscando projetos apensados (modo híbrido)...")
    
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
        
        print(f"[APENSADOS] Total de proposições encontradas: {len(todas_props)}")
        
        # 2. Para cada proposição, verificar se está apensada
        for prop in todas_props:
            prop_id = str(prop.get("id", ""))
            sigla = prop.get("siglaTipo", "")
            numero = prop.get("numero", "")
            ano = prop.get("ano", "")
            ementa = prop.get("ementa", "")
            
            prop_nome = f"{sigla} {numero}/{ano}"
            
            # Buscar detalhes da proposição
            try:
                url_detalhe = f"{BASE_URL}/proposicoes/{prop_id}"
                resp_det = requests.get(url_detalhe, headers=HEADERS, timeout=15)
                
                if resp_det.status_code != 200:
                    continue
                
                dados_prop = resp_det.json().get("dados", {})
                status = dados_prop.get("statusProposicao", {})
                situacao = status.get("descricaoSituacao", "")
                
                # 3. Verificar se está apensada
                situacao_lower = situacao.lower()
                
                if "tramitando em conjunto" in situacao_lower or "apensad" in situacao_lower:
                    print(f"[APENSADOS] ✅ {prop_nome} está apensado")
                    
                    # 4. Encontrar o PL principal
                    pl_principal = None
                    fonte = ""
                    
                    # Primeiro: verificar no dicionário de mapeamentos
                    if prop_id in MAPEAMENTO_APENSADOS:
                        pl_principal = MAPEAMENTO_APENSADOS[prop_id]
                        fonte = "dicionário"
                    else:
                        # Fallback: buscar nas tramitações
                        pl_principal = buscar_pl_principal_nas_tramitacoes(prop_id)
                        fonte = "tramitações"
                    
                    if pl_principal:
                        print(f"[APENSADOS]    → PL Principal ({fonte}): {pl_principal}")
                        
                        # Buscar ID do PL principal
                        id_principal = buscar_id_proposicao(pl_principal)
                        
                        if id_principal:
                            # Buscar autor do PL principal
                            autor_principal = "—"
                            try:
                                url_autores = f"{BASE_URL}/proposicoes/{id_principal}/autores"
                                resp_autores = requests.get(url_autores, headers=HEADERS, timeout=10)
                                if resp_autores.status_code == 200:
                                    autores = resp_autores.json().get("dados", [])
                                    if autores:
                                        autor_principal = autores[0].get("nome", "—")
                            except:
                                pass
                            
                            projetos_apensados.append({
                                "pl": pl_principal,
                                "id": id_principal,
                                "tema": ementa[:80] + "..." if len(ementa) > 80 else ementa,
                                "pl_zanatta": prop_nome,
                                "autor_principal": autor_principal,
                            })
                    else:
                        print(f"[APENSADOS]    ⚠️ PL Principal não encontrado")
            
            except Exception as e:
                print(f"[APENSADOS] ⚠️ Erro ao verificar {prop_nome}: {e}")
            
            time.sleep(0.15)
        
        print(f"[APENSADOS] ✅ Total detectado: {len(projetos_apensados)} projetos apensados")
        
        return projetos_apensados
    
    except Exception as e:
        print(f"[APENSADOS] ❌ Erro geral: {e}")
        return []


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_data_hora_brasilia() -> str:
    """Retorna data/hora atual no fuso horário de Brasília"""
    tz_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(tz_brasilia)
    return agora.strftime("%d/%m/%Y às %H:%M")


def carregar_estado() -> dict:
    """Carrega estado da última execução"""
    if ESTADO_FILE.exists():
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"ultima_execucao": None, "ultima_novidade": True}


def salvar_estado(teve_novidade: bool):
    """Salva estado da execução atual"""
    estado = {
        "ultima_execucao": datetime.now(timezone.utc).isoformat(),
        "ultima_novidade": teve_novidade
    }
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def carregar_historico() -> dict:
    """Carrega histórico de notificações"""
    if HISTORICO_FILE.exists():
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"notificados": []}


def salvar_historico(historico: dict):
    """Salva histórico de notificações"""
    # Manter apenas os últimos 500 hashes
    if len(historico.get("notificados", [])) > 500:
        historico["notificados"] = historico["notificados"][-500:]
    
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def gerar_hash_tramitacao(prop_id: str, data: str, descricao: str) -> str:
    """Gera hash único para uma tramitação"""
    texto = f"{prop_id}|{data}|{descricao[:100]}"
    return hashlib.md5(texto.encode()).hexdigest()


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
    except Exception as e:
        print(f"[TRAMITAÇÃO] Erro ao buscar tramitação de {prop_id}: {e}")
    
    return None


def buscar_dados_proposicao(prop_id: str) -> dict:
    """Busca dados atualizados de uma proposição"""
    try:
        url = f"{BASE_URL}/proposicoes/{prop_id}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            return resp.json().get("dados", {})
    except:
        pass
    
    return {}


def tramitacao_recente(tramitacao: dict, horas: int = 48) -> bool:
    """Verifica se a tramitação é recente (últimas X horas)"""
    if not tramitacao:
        return False
    
    data_hora = tramitacao.get("dataHora")
    if not data_hora:
        return False
    
    try:
        dt = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
        agora = datetime.now(timezone.utc)
        diferenca = agora - dt
        
        return diferenca.total_seconds() < (horas * 3600)
    except:
        return False


# ============================================================
# FUNÇÕES DE TELEGRAM
# ============================================================

def enviar_telegram(mensagem: str) -> bool:
    """Envia mensagem via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Token ou Chat ID não configurado")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        resp = requests.post(url, json=payload, timeout=30)
        
        if resp.status_code == 200:
            print("[TELEGRAM] ✅ Mensagem enviada com sucesso")
            return True
        else:
            print(f"[TELEGRAM] ❌ Erro: {resp.status_code} - {resp.text}")
            return False
    
    except Exception as e:
        print(f"[TELEGRAM] ❌ Erro ao enviar: {e}")
        return False


def formatar_mensagem_novidade(pl_info: dict, tramitacao: dict, dados_prop: dict) -> str:
    """Formata mensagem de nova tramitação"""
    
    pl_principal = pl_info.get("pl", "—")
    pl_zanatta = pl_info.get("pl_zanatta", "—")
    tema = pl_info.get("tema", "—")
    autor_principal = pl_info.get("autor_principal", "—")
    prop_id = pl_info.get("id", "")
    
    # Dados da tramitação
    data_tram = tramitacao.get("dataHora", "")
    if data_tram:
        try:
            dt = datetime.fromisoformat(data_tram.replace("Z", "+00:00"))
            data_tram = dt.strftime("%d/%m/%Y")
        except:
            data_tram = data_tram[:10]
    
    orgao = tramitacao.get("siglaOrgao", "—")
    despacho = tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "—")
    
    # Situação atual
    situacao = "—"
    if dados_prop:
        status = dados_prop.get("statusProposicao", {})
        situacao = status.get("descricaoSituacao", "—")
    
    # Link
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
    
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""📎 <b>PROJETO APENSADO - Nova Movimentação!</b>

🎯 <b>PL Principal:</b> {html.escape(pl_principal)}
👤 <b>Autor:</b> {html.escape(autor_principal)}
📌 <b>Tema:</b> {html.escape(tema[:60])}...

📄 <b>PL da Dep. Zanatta apensado:</b> {html.escape(pl_zanatta)}

📅 {data_tram} | 🏛️ {html.escape(orgao)}
➡️ {html.escape(despacho[:200])}{"..." if len(despacho) > 200 else ""}

📊 <b>Situação atual:</b> {html.escape(situacao[:80])}

🔗 <a href="{link}">Ver tramitação completa</a>

⏰ <i>Varredura: {data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_completa(pls_monitorar: list) -> str:
    """Formata mensagem quando não há novidades (primeira vez)"""
    
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""🔍 <b>Monitor de Projetos Apensados</b>

Não foram encontradas tramitações recentes nos PLs principais que têm projetos da Dep. Júlia Zanatta apensados.

📎 <b>PLs Monitorados ({len(pls_monitorar)}):</b>
"""
    
    for pl_info in pls_monitorar[:10]:  # Limitar a 10 para não ficar muito longo
        mensagem += f"• {pl_info['pl']} ← {pl_info['pl_zanatta']}\n"
    
    if len(pls_monitorar) > 10:
        mensagem += f"... e mais {len(pls_monitorar) - 10} projetos\n"
    
    mensagem += f"""
Continue atento! 👀

⏰ <i>Varredura realizada em {data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_curta() -> str:
    """Formata mensagem curta quando não há novidades"""
    data_hora = obter_data_hora_brasilia()
    return f"🔍 Monitor de Apensados: Sem novidades | {data_hora}"


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    """Verifica novas tramitações nos PLs principais e notifica via Telegram"""
    
    data_hora_brasilia = obter_data_hora_brasilia()
    
    print("=" * 60)
    print("📎 MONITOR DE PROJETOS APENSADOS - DEP. JÚLIA ZANATTA")
    print("   (DETECÇÃO HÍBRIDA v2.1)")
    print("=" * 60)
    print(f"📅 Data/Hora (Brasília): {data_hora_brasilia}")
    print()
    
    # Verificar variáveis de ambiente
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERRO: TELEGRAM_BOT_TOKEN não configurado!")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        print("❌ ERRO: TELEGRAM_CHAT_ID não configurado!")
        sys.exit(1)
    
    print(f"✅ Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    print()
    
    # Carregar estado e histórico
    estado = carregar_estado()
    historico = carregar_historico()
    ultima_teve_novidade = estado.get("ultima_novidade", True)
    
    # ============================================================
    # DETECÇÃO DE PROJETOS APENSADOS
    # ============================================================
    print("🔍 Detectando projetos apensados...")
    print()
    
    pls_monitorar = buscar_projetos_apensados()
    
    if not pls_monitorar:
        print("⚠️ Nenhum projeto apensado encontrado!")
        enviar_telegram("🔍 Nenhum projeto apensado da Dep. Júlia Zanatta foi detectado nesta varredura.")
        salvar_estado(False)
        return
    
    print()
    print(f"📊 PLs principais a monitorar: {len(pls_monitorar)}")
    print()
    
    # Verificar tramitações de cada PL principal
    props_com_novidade = []
    erros = 0
    
    for i, pl_info in enumerate(pls_monitorar, 1):
        pl_nome = pl_info["pl"]
        prop_id = pl_info["id"]
        
        print(f"[{i}/{len(pls_monitorar)}] Verificando {pl_nome}...")
        
        # Buscar última tramitação
        tramitacao = buscar_ultima_tramitacao(prop_id)
        
        if tramitacao is None:
            print(f"   ⚠️ Não foi possível buscar tramitação")
            erros += 1
            time.sleep(0.3)
            continue
        
        # Verificar se é recente
        if tramitacao_recente(tramitacao, horas=48):
            # Verificar se já foi notificada
            hash_tram = gerar_hash_tramitacao(
                prop_id,
                tramitacao.get("dataHora", ""),
                tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
            )
            
            if hash_tram in historico.get("notificados", []):
                print(f"   ⏭️ Tramitação já notificada anteriormente")
            else:
                print(f"   ✅ NOVA TRAMITAÇÃO!")
                
                # Buscar dados da proposição
                dados_prop = buscar_dados_proposicao(prop_id)
                
                props_com_novidade.append({
                    "pl_info": pl_info,
                    "tramitacao": tramitacao,
                    "dados_prop": dados_prop,
                    "hash": hash_tram
                })
        else:
            print(f"   ⏸️ Sem tramitação recente")
        
        time.sleep(0.3)  # Rate limit
    
    print()
    print("=" * 60)
    
    # Processar novidades
    if props_com_novidade:
        print(f"📢 {len(props_com_novidade)} novidade(s) encontrada(s)!")
        print()
        
        for item in props_com_novidade:
            mensagem = formatar_mensagem_novidade(
                item["pl_info"],
                item["tramitacao"],
                item["dados_prop"]
            )
            
            if enviar_telegram(mensagem):
                # Adicionar ao histórico apenas se enviou com sucesso
                historico["notificados"].append(item["hash"])
            
            time.sleep(1)  # Delay entre mensagens
        
        # Salvar histórico e estado
        salvar_historico(historico)
        salvar_estado(True)
        
    else:
        print("📭 Nenhuma novidade encontrada.")
        
        # Enviar mensagem informando que não há novidades
        if ultima_teve_novidade:
            # Primeira vez sem novidades: mensagem completa
            enviar_telegram(formatar_mensagem_sem_novidades_completa(pls_monitorar))
        else:
            # Já não tinha novidades: mensagem curta
            enviar_telegram(formatar_mensagem_sem_novidades_curta())
        
        salvar_estado(False)
    
    print()
    print("=" * 60)
    print("✅ Verificação concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
