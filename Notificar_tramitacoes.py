#!/usr/bin/env python3
"""
Script de automação para notificações de tramitações via Telegram.
VERSÃO 3 - Busca TODAS as proposições com paginação

Uso:
    python Notificar_tramitacoes.py

Configuração via variáveis de ambiente:
    TELEGRAM_BOT_TOKEN - Token do bot do Telegram
    TELEGRAM_CHAT_ID - ID do chat para enviar notificações
    DEPUTADA_ID - ID da deputada na API da Câmara (default: 220559)
    HORAS_VERIFICAR - Quantas horas para trás verificar (default: 24)
"""

import os
import sys
import datetime
import time
import requests

# Configurações
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/AutoNotify-v3 (github-actions)"}

# Variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DEPUTADA_ID = os.environ.get("DEPUTADA_ID", "220559")
HORAS_VERIFICAR = int(os.environ.get("HORAS_VERIFICAR", "24"))


def get_data_hora_brasilia():
    """Retorna data/hora atual ajustada para Brasília (UTC-3)."""
    utc_now = datetime.datetime.utcnow()
    return utc_now - datetime.timedelta(hours=3)


def telegram_enviar(mensagem: str) -> bool:
    """Envia mensagem via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurado")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get("ok"):
            return True
        else:
            print(f"❌ Erro Telegram: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Exceção Telegram: {e}")
        return False


def buscar_todas_proposicoes_deputada(id_deputada: str, data_inicio: str = None) -> set:
    """
    Busca TODAS as proposições de autoria do deputado usando paginação.
    Se data_inicio for fornecido, filtra por proposições apresentadas desde essa data.
    """
    ids = set()
    pagina = 1
    max_paginas = 20  # Limita a 20 páginas (2000 proposições)
    
    print(f"📥 Buscando proposições de autoria...")
    
    while pagina <= max_paginas:
        try:
            url = f"{BASE_URL}/proposicoes"
            params = {
                "idDeputadoAutor": id_deputada,
                "itens": 100,
                "pagina": pagina,
                "ordem": "DESC",
                "ordenarPor": "id"
            }
            
            # Se tiver data de início, adiciona filtro
            if data_inicio:
                params["dataApresentacaoInicio"] = data_inicio
            
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            
            if resp.status_code != 200:
                print(f"   Página {pagina}: erro {resp.status_code}")
                break
            
            dados = resp.json().get("dados", [])
            
            if not dados:
                break  # Não há mais dados
            
            for p in dados:
                if p.get("id"):
                    ids.add(str(p["id"]))
            
            print(f"   Página {pagina}: +{len(dados)} proposições (total: {len(ids)})")
            
            # Se retornou menos que 100, é a última página
            if len(dados) < 100:
                break
            
            pagina += 1
            time.sleep(0.2)  # Pequena pausa entre requisições
            
        except Exception as e:
            print(f"   Erro na página {pagina}: {e}")
            break
    
    return ids


def buscar_tramitacoes_recentes(id_prop: str, data_corte_str: str) -> list:
    """
    Busca tramitações de uma proposição mais recentes que data_corte.
    Retorna lista de tramitações com data >= data_corte_str (formato YYYY-MM-DD).
    """
    tramitacoes_novas = []
    
    try:
        url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code != 200:
            return []
        
        dados = resp.json().get("dados", [])
        
        for tram in dados[:10]:  # Verifica as 10 mais recentes
            data_hora = tram.get("dataHora", "")
            
            if data_hora and len(data_hora) >= 10:
                data_tram_str = data_hora[:10]  # YYYY-MM-DD
                
                # Comparação simples de strings ISO
                if data_tram_str >= data_corte_str:
                    tramitacoes_novas.append(tram)
        
    except Exception as e:
        pass  # Silencia erros individuais
    
    return tramitacoes_novas


def buscar_info_proposicao(id_prop: str) -> dict:
    """Busca informações básicas de uma proposição."""
    try:
        url = f"{BASE_URL}/proposicoes/{id_prop}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            dados = resp.json().get("dados", {})
            return {
                "id": id_prop,
                "sigla": dados.get("siglaTipo", ""),
                "numero": dados.get("numero", ""),
                "ano": dados.get("ano", ""),
                "ementa": (dados.get("ementa", "") or "")[:200]
            }
    except:
        pass
    return {}


def formatar_mensagem(proposicao: dict, tramitacoes: list) -> str:
    """Formata mensagem de notificação para o Telegram."""
    sigla = proposicao.get("sigla", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = proposicao.get("ementa", "")
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
    
    for tram in tramitacoes[:3]:
        data = tram.get("dataHora", "")[:10] if tram.get("dataHora") else ""
        despacho = (tram.get("despacho", "") or tram.get("descricaoSituacao", "") or "")[:150]
        
        # Formata data para DD/MM/YYYY
        if data and len(data) == 10:
            try:
                dt = datetime.datetime.strptime(data, "%Y-%m-%d")
                data = dt.strftime("%d/%m/%Y")
            except:
                pass
        
        if data:
            linhas.append(f"📅 <b>{data}</b>")
        if despacho:
            linhas.append(f"→ {despacho}")
        linhas.append("")
    
    if id_prop:
        link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_prop}"
        linhas.append(f"🔗 <a href='{link}'>Ver tramitação completa</a>")
    
    return "\n".join(linhas)


def main():
    agora = get_data_hora_brasilia()
    
    print("=" * 60)
    print("🔔 Monitor de Tramitações - Notificador Automático v3")
    print("=" * 60)
    print(f"📅 Data/hora: {agora.strftime('%d/%m/%Y %H:%M')} (Brasília)")
    print(f"🔍 Verificando últimas {HORAS_VERIFICAR} horas")
    print(f"👤 Deputada ID: {DEPUTADA_ID}")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print()
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Variáveis de ambiente não configuradas!")
        sys.exit(1)
    
    # Data de corte para tramitações
    data_corte = agora - datetime.timedelta(hours=HORAS_VERIFICAR)
    data_corte_str = data_corte.strftime("%Y-%m-%d")
    
    print(f"📆 Data de corte: {data_corte.strftime('%d/%m/%Y')} ({data_corte_str})")
    print()
    
    # Buscar proposições apresentadas no último ano (para otimizar)
    um_ano_atras = (agora - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    # Coletar proposições
    ids_monitorar = buscar_todas_proposicoes_deputada(DEPUTADA_ID, um_ano_atras)
    
    if not ids_monitorar:
        print("❌ Nenhuma proposição encontrada!")
        sys.exit(1)
    
    print()
    print(f"📋 Total: {len(ids_monitorar)} proposições do último ano")
    print()
    
    # Verificar tramitações
    print("🔍 Verificando tramitações recentes...")
    notificacoes_enviadas = 0
    props_com_novidade = []
    total_verificadas = 0
    
    for i, id_prop in enumerate(ids_monitorar):
        total_verificadas += 1
        
        # Mostra progresso a cada 50
        if (i + 1) % 50 == 0:
            print(f"   ... {i + 1}/{len(ids_monitorar)} verificadas")
        
        tramitacoes = buscar_tramitacoes_recentes(id_prop, data_corte_str)
        
        if tramitacoes:
            info = buscar_info_proposicao(id_prop)
            if info and info.get("sigla"):
                titulo = f"{info['sigla']} {info['numero']}/{info['ano']}"
                data_tram = tramitacoes[0].get("dataHora", "")[:10]
                print(f"   ✨ NOVIDADE: {titulo} (tramitação em {data_tram})")
                
                msg = formatar_mensagem(info, tramitacoes)
                if telegram_enviar(msg):
                    notificacoes_enviadas += 1
                    props_com_novidade.append(titulo)
                
                time.sleep(0.5)  # Evitar rate limit do Telegram
    
    print()
    print("=" * 60)
    print("✅ Concluído!")
    print(f"   - Proposições verificadas: {total_verificadas}")
    print(f"   - Com tramitação recente: {len(props_com_novidade)}")
    print(f"   - Notificações enviadas: {notificacoes_enviadas}")
    
    if props_com_novidade:
        print(f"   - Proposições notificadas:")
        for p in props_com_novidade:
            print(f"     • {p}")
    else:
        print(f"   ℹ️  Nenhuma tramitação encontrada desde {data_corte.strftime('%d/%m/%Y')}")
    
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())