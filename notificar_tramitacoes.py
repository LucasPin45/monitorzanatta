#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_tramitacoes.py
========================================
Script para verificar novas tramitações e enviar notificações via Telegram
Busca todas as proposições do último ano e compara com as últimas 48h
Formato de mensagem: Monitor Parlamentar Informa
"""

import os
import sys
import requests
import time
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/24.0 (gabinete-julia-zanatta)"}

DEPUTADA_ID = 220559  # Júlia Zanatta
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def buscar_proposicoes_ultimo_ano(deputado_id):
    """Busca TODAS as proposições do último ano (autoria)"""
    
    # Usar data de ontem como fim para evitar problemas com fuso horário
    data_fim = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    data_inicio = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    print(f"🔍 Buscando proposições desde: {data_inicio}")
    print(f"📅 Até: {data_fim}")
    
    proposicoes = []
    pagina = 1
    
    while True:
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": deputado_id,
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "ordem": "DESC",
            "ordenarPor": "id",
            "pagina": pagina,
            "itens": 100
        }
        
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            
            # Se der erro 400, tentar sem dataFim
            if resp.status_code == 400:
                print(f"⚠️ Erro 400 na API, tentando sem dataFim...")
                params.pop("dataFim", None)
                resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("dados"):
                break
                
            proposicoes.extend(data["dados"])
            print(f"   Página {pagina}: {len(data['dados'])} proposições")
            
            # Verificar se há mais páginas
            links = data.get("links", [])
            tem_proxima = any(link.get("rel") == "next" for link in links)
            
            if not tem_proxima:
                break
                
            pagina += 1
            time.sleep(0.3)  # Rate limit
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Erro HTTP ao buscar proposições (página {pagina}): {e}")
            break
        except Exception as e:
            print(f"❌ Erro ao buscar proposições (página {pagina}): {e}")
            break
    
    print(f"✅ Total de proposições encontradas: {len(proposicoes)}")
    return proposicoes


def buscar_ultima_tramitacao(proposicao_id):
    """Busca a última tramitação de uma proposição"""
    
    # Endpoint simples sem parâmetros problemáticos
    url = f"{BASE_URL}/proposicoes/{proposicao_id}/tramitacoes"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        tramitacoes = data.get("dados", [])
        
        if tramitacoes:
            # Ordenar por data e pegar a mais recente
            tramitacoes_ordenadas = sorted(
                tramitacoes,
                key=lambda x: x.get("dataHora", ""),
                reverse=True
            )
            return tramitacoes_ordenadas[0]
            
    except Exception as e:
        # Silenciar erros individuais para não poluir o log
        pass
    
    return None


def tramitacao_recente(tramitacao, horas=48):
    """Verifica se a tramitação é das últimas X horas (padrão 48h para maior cobertura)"""
    
    if not tramitacao or not tramitacao.get("dataHora"):
        return False
    
    try:
        # Data da tramitação (formato: "2025-12-29T14:57:00")
        data_tram = tramitacao["dataHora"][:10]  # Pega só YYYY-MM-DD
        
        # Data de corte (48h atrás)
        data_corte = (datetime.now() - timedelta(hours=horas)).strftime("%Y-%m-%d")
        
        # Comparação simples de strings
        return data_tram >= data_corte
        
    except Exception as e:
        return False


def formatar_mensagem(proposicao, tramitacao):
    """Formata mensagem para o Telegram"""
    
    sigla = proposicao.get("siglaTipo", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = proposicao.get("ementa", "")
    
    # Limitar ementa em 200 caracteres
    if len(ementa) > 200:
        ementa = ementa[:197] + "..."
    
    # Data no formato DD/MM/YYYY
    data_tram = tramitacao.get("dataHora", "")
    if data_tram:
        try:
            dt = datetime.fromisoformat(data_tram.replace("Z", ""))
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = data_tram[:10]
    else:
        data_formatada = "Data não disponível"
    
    # Descrição da tramitação
    descricao = tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
    
    # Link da tramitação
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={proposicao['id']}"
    
    # Montar mensagem
    mensagem = f"""📢 <b>Monitor Parlamentar Informa:</b>

Houve nova movimentação!

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

📅 {data_formatada} → {descricao}

🔗 <a href="{link}">Ver tramitação completa</a>"""
    
    return mensagem


def enviar_telegram(mensagem):
    """Envia mensagem para o Telegram"""
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados!")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print("✅ Mensagem enviada com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return False


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    """Verifica novas tramitações e notifica via Telegram"""
    
    print("=" * 60)
    print("🔔 MONITOR DE TRAMITAÇÕES - DEPUTADA JÚLIA ZANATTA")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
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
    
    # 1. Buscar proposições do último ano
    proposicoes = buscar_proposicoes_ultimo_ano(DEPUTADA_ID)
    
    if not proposicoes:
        print("⚠️ Nenhuma proposição encontrada")
        return
    
    # 2. Verificar tramitações recentes (últimas 48h)
    print("\n🔍 Verificando tramitações das últimas 48h...")
    print("   (isso pode levar alguns minutos...)\n")
    
    props_com_novidade = []
    erros = 0
    
    for i, prop in enumerate(proposicoes, 1):
        sigla_prop = f"{prop['siglaTipo']} {prop['numero']}/{prop['ano']}"
        
        # Mostrar progresso a cada 50 proposições
        if i % 50 == 0 or i == 1:
            print(f"📊 Progresso: {i}/{len(proposicoes)} proposições verificadas...")
        
        tramitacao = buscar_ultima_tramitacao(prop["id"])
        
        if tramitacao is None:
            erros += 1
            continue
        
        if tramitacao_recente(tramitacao, horas=48):
            print(f"   ✅ NOVA! {sigla_prop}")
            props_com_novidade.append({
                "proposicao": prop,
                "tramitacao": tramitacao
            })
        
        time.sleep(0.2)  # Rate limit mais suave
    
    # 3. Resumo
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Total verificadas: {len(proposicoes)}")
    print(f"   Com novidades: {len(props_com_novidade)}")
    print(f"   Erros de API: {erros}")
    print(f"{'=' * 60}")
    
    if not props_com_novidade:
        print("\n✅ Nenhuma novidade para notificar")
        return
    
    # 4. Enviar notificações
    print(f"\n📤 Enviando {len(props_com_novidade)} notificação(ões)...\n")
    
    enviadas = 0
    for item in props_com_novidade:
        mensagem = formatar_mensagem(item["proposicao"], item["tramitacao"])
        if enviar_telegram(mensagem):
            enviadas += 1
        time.sleep(1)  # Evitar flood no Telegram
    
    print(f"\n✅ Processo concluído! {enviadas} mensagens enviadas.")


if __name__ == "__main__":
    main()