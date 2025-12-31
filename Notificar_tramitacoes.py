#!/usr/bin/env python3
"""
Script de automação para notificações de tramitações via Telegram.
VERSÃO CORRIGIDA - Comparação de datas simplificada

Uso:
    python Notificar_tramitacoes.py

Configuração via variáveis de ambiente:
    TELEGRAM_BOT_TOKEN - Token do bot do Telegram
    TELEGRAM_CHAT_ID - ID do chat para enviar notificações (pode ser grupo, ex: -5150040677)
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
HEADERS = {"User-Agent": "MonitorZanatta/AutoNotify (github-actions)"}

# Variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DEPUTADA_ID = os.environ.get("DEPUTADA_ID", "220559")
HORAS_VERIFICAR = int(os.environ.get("HORAS_VERIFICAR", "24"))


def get_data_hora_brasilia():
    """Retorna data/hora atual (sem timezone para simplificar)."""
    # Ajusta para Brasília (UTC-3)
    utc_now = datetime.datetime.utcnow()
    brasilia_now = utc_now - datetime.timedelta(hours=3)
    return brasilia_now


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
        print(f"❌ Exceção: {e}")
        return False


def buscar_proposicoes_deputada(id_deputada: str) -> set:
    """Busca IDs de proposições de autoria e relatoria do deputado."""
    ids = set()
    
    # Autoria
    try:
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": id_deputada,
            "itens": 100,
            "ordem": "DESC",
            "ordenarPor": "id"
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            for p in dados:
                if p.get("id"):
                    ids.add(str(p["id"]))
            print(f"✓ {len(dados)} proposições de autoria")
    except Exception as e:
        print(f"❌ Erro ao buscar autoria: {e}")
    
    # Relatoria
    try:
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoRelator": id_deputada,
            "itens": 100,
            "ordem": "DESC",
            "ordenarPor": "id"
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            for p in dados:
                if p.get("id"):
                    ids.add(str(p["id"]))
            print(f"✓ {len(dados)} proposições como relatora")
    except Exception as e:
        print(f"❌ Erro ao buscar relatoria: {e}")
    
    return ids


def buscar_info_proposicao(id_prop: str) -> dict:
    """Busca informações de uma proposição."""
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


def buscar_tramitacoes_recentes(id_prop: str, data_corte: datetime.datetime) -> list:
    """
    Busca tramitações de uma proposição mais recentes que data_corte.
    Usa comparação SIMPLES de datas (só YYYY-MM-DD).
    """
    tramitacoes_novas = []
    
    try:
        url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        
        dados = resp.json().get("dados", [])
        
        # Data de corte como string YYYY-MM-DD para comparação simples
        data_corte_str = data_corte.strftime("%Y-%m-%d")
        
        for tram in dados[:10]:  # Só verifica as 10 mais recentes
            data_hora = tram.get("dataHora", "")
            
            if data_hora and len(data_hora) >= 10:
                # Pega só a parte da data (YYYY-MM-DD)
                data_tram_str = data_hora[:10]
                
                # Comparação simples de strings (funciona porque é formato ISO)
                if data_tram_str >= data_corte_str:
                    tramitacoes_novas.append(tram)
        
    except Exception as e:
        print(f"   Erro ao buscar tramitações de {id_prop}: {e}")
    
    return tramitacoes_novas


def formatar_mensagem(proposicao: dict, tramitacoes: list) -> str:
    """Formata mensagem de notificação."""
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
    print("🔔 Monitor de Tramitações - Notificador Automático")
    print("=" * 60)
    print(f"📅 Data/hora: {agora.strftime('%d/%m/%Y %H:%M')} (Brasília)")
    print(f"🔍 Verificando últimas {HORAS_VERIFICAR} horas")
    print(f"👤 Deputada ID: {DEPUTADA_ID}")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print()
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Variáveis de ambiente não configuradas!")
        print("   Necessário: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
        sys.exit(1)
    
    # Data de corte
    data_corte = agora - datetime.timedelta(hours=HORAS_VERIFICAR)
    print(f"📆 Data de corte: {data_corte.strftime('%d/%m/%Y %H:%M')}")
    print()
    
    # Coletar proposições
    print("📥 Coletando proposições...")
    ids_monitorar = buscar_proposicoes_deputada(DEPUTADA_ID)
    
    if not ids_monitorar:
        print("❌ Nenhuma proposição encontrada!")
        sys.exit(1)
    
    # Ordenar por ID decrescente (mais recentes primeiro) e limitar
    ids_ordenados = sorted(ids_monitorar, key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
    ids_verificar = ids_ordenados[:100]  # Máximo 100
    
    print(f"📋 Total: {len(ids_monitorar)} proposições encontradas")
    print(f"🔍 Verificando as {len(ids_verificar)} mais recentes...")
    print()
    
    # Verificar tramitações
    print("🔍 Buscando tramitações recentes...")
    notificacoes_enviadas = 0
    props_com_novidade = []
    erros = 0
    
    for i, id_prop in enumerate(ids_verificar):
        # Mostra progresso a cada 20
        if (i + 1) % 20 == 0:
            print(f"   ... {i + 1}/{len(ids_verificar)} verificadas")
        
        tramitacoes = buscar_tramitacoes_recentes(id_prop, data_corte)
        
        if tramitacoes:
            info = buscar_info_proposicao(id_prop)
            if info:
                titulo = f"{info.get('sigla')} {info.get('numero')}/{info.get('ano')}"
                print(f"   ✨ Novidade encontrada: {titulo}")
                
                msg = formatar_mensagem(info, tramitacoes)
                if telegram_enviar(msg):
                    notificacoes_enviadas += 1
                    props_com_novidade.append(titulo)
                else:
                    erros += 1
                
                time.sleep(0.5)  # Evitar rate limit
    
    print()
    print("=" * 60)
    print("✅ Concluído!")
    print(f"   - Proposições verificadas: {len(ids_verificar)}")
    print(f"   - Notificações enviadas: {notificacoes_enviadas}")
    print(f"   - Erros: {erros}")
    
    if props_com_novidade:
        print(f"   - Proposições notificadas:")
        for p in props_com_novidade:
            print(f"     • {p}")
    
    print("=" * 60)
    
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main())