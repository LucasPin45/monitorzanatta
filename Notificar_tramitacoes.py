#!/usr/bin/env python3
"""
Script de automação para notificações de tramitações via Telegram.
Pode ser executado via GitHub Actions, cron, ou manualmente.

Uso:
    python notificar_tramitacoes.py

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
from zoneinfo import ZoneInfo

# Configurações
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/AutoNotify (github-actions)"}
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")

# Variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DEPUTADA_ID = os.environ.get("DEPUTADA_ID", "220559")
HORAS_VERIFICAR = int(os.environ.get("HORAS_VERIFICAR", "24"))


def get_brasilia_now():
    return datetime.datetime.now(TZ_BRASILIA)


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


def buscar_proposicoes_autoria(id_deputada: str) -> list:
    """Busca IDs de proposições de autoria do deputado."""
    ids = []
    url = f"{BASE_URL}/proposicoes"
    params = {
        "idDeputadoAutor": id_deputada,
        "itens": 100,
        "ordem": "DESC",
        "ordenarPor": "id"
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            ids = [str(p.get("id")) for p in dados if p.get("id")]
            print(f"✓ {len(ids)} proposições de autoria encontradas")
    except Exception as e:
        print(f"❌ Erro ao buscar autoria: {e}")
    
    return ids


def buscar_proposicoes_relatoria(id_deputada: str) -> list:
    """Busca IDs de proposições onde o deputado é relator."""
    ids = []
    url = f"{BASE_URL}/proposicoes"
    params = {
        "idDeputadoRelator": id_deputada,
        "itens": 100,
        "ordem": "DESC",
        "ordenarPor": "id"
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            dados = resp.json().get("dados", [])
            ids = [str(p.get("id")) for p in dados if p.get("id")]
            print(f"✓ {len(ids)} proposições como relator(a) encontradas")
    except Exception as e:
        print(f"❌ Erro ao buscar relatoria: {e}")
    
    return ids


def buscar_info_proposicao(id_prop: str) -> dict:
    """Busca informações de uma proposição."""
    url = f"{BASE_URL}/proposicoes/{id_prop}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            dados = resp.json().get("dados", {})
            return {
                "id": id_prop,
                "sigla": dados.get("siglaTipo", ""),
                "numero": dados.get("numero", ""),
                "ano": dados.get("ano", ""),
                "ementa": dados.get("ementa", "")[:200]
            }
    except:
        pass
    return {}


def buscar_tramitacoes(id_prop: str, desde: datetime.datetime) -> list:
    """Busca tramitações de uma proposição desde uma data."""
    tramitacoes_novas = []
    url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        
        dados = resp.json().get("dados", [])
        
        for tram in dados:
            data_hora = tram.get("dataHora", "")
            if data_hora:
                try:
                    dt_tram = datetime.datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                    if dt_tram.tzinfo is None:
                        dt_tram = dt_tram.replace(tzinfo=TZ_BRASILIA)
                    
                    if dt_tram > desde:
                        tramitacoes_novas.append(tram)
                except:
                    pass
    except:
        pass
    
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


def main():
    print(f"=" * 50)
    print(f"🔔 Monitor de Tramitações - Notificador Automático")
    print(f"=" * 50)
    print(f"📅 {get_brasilia_now().strftime('%d/%m/%Y %H:%M')} (Brasília)")
    print(f"🔍 Verificando últimas {HORAS_VERIFICAR} horas")
    print(f"👤 Deputada ID: {DEPUTADA_ID}")
    print()
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Variáveis de ambiente não configuradas:")
        print("   - TELEGRAM_BOT_TOKEN")
        print("   - TELEGRAM_CHAT_ID")
        sys.exit(1)
    
    # Data de corte
    desde = get_brasilia_now() - datetime.timedelta(hours=HORAS_VERIFICAR)
    desde = desde.replace(tzinfo=TZ_BRASILIA)
    
    # Coletar proposições
    print("📥 Coletando proposições...")
    ids_monitorar = set()
    
    ids_autoria = buscar_proposicoes_autoria(DEPUTADA_ID)
    ids_monitorar.update(ids_autoria)
    
    ids_relatoria = buscar_proposicoes_relatoria(DEPUTADA_ID)
    ids_monitorar.update(ids_relatoria)
    
    print(f"📋 Total: {len(ids_monitorar)} proposições para verificar")
    print()
    
    # Verificar tramitações
    print("🔍 Verificando tramitações...")
    notificacoes_enviadas = 0
    erros = 0
    
    for i, id_prop in enumerate(list(ids_monitorar)[:100]):  # Limita a 100
        tramitacoes = buscar_tramitacoes(id_prop, desde)
        
        if tramitacoes:
            info = buscar_info_proposicao(id_prop)
            if info:
                msg = formatar_mensagem(info, tramitacoes)
                if telegram_enviar(msg):
                    titulo = f"{info.get('sigla')} {info.get('numero')}/{info.get('ano')}"
                    print(f"✅ Notificação enviada: {titulo}")
                    notificacoes_enviadas += 1
                else:
                    erros += 1
                
                time.sleep(0.5)  # Evitar rate limit
        
        # Progresso a cada 20
        if (i + 1) % 20 == 0:
            print(f"   ... {i + 1}/{len(ids_monitorar)} verificadas")
    
    print()
    print(f"=" * 50)
    print(f"✅ Concluído!")
    print(f"   - Notificações enviadas: {notificacoes_enviadas}")
    print(f"   - Erros: {erros}")
    print(f"=" * 50)
    
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main())