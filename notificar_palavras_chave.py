#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_palavras_chave.py
========================================
Monitor de tramitações por PALAVRAS-CHAVE
Busca proposições de TODOS os autores com tramitação recente
e notifica quando encontrar palavras-chave de interesse.

v1: Versão inicial
- Busca tramitações das últimas 48h de todos os projetos
- Filtra por palavras-chave na ementa ou despacho
- Controle de duplicatas
- Mensagem de bom dia / resumo
"""

import os
import sys
import json
import html
import requests
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorPalavrasChave/1.0 (gabinete-julia-zanatta)"}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_PALAVRAS")  # Token separado
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PALAVRAS")      # Chat separado (ou o mesmo)

# Se não tiver tokens específicos, usa os mesmos do outro bot
if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Modo de execução (bom_dia, varredura, resumo)
MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# ============================================================
# PALAVRAS-CHAVE DE INTERESSE
# ============================================================
# Organize por categoria para facilitar manutenção

PALAVRAS_CHAVE = {
    "Armas e Segurança": [
        "arma", "armas", "armamento", "munição", "cac", "atirador",
        "caçador", "colecionador", "porte", "posse de arma", "estatuto do desarmamento",
        "legítima defesa", "defesa pessoal"
    ],
    "Saúde - Vacinas": [
        "vacina", "vacinas", "vacinação", "imunização", "imunizante",
        "anvisa", "vigilância sanitária", "passaporte vacinal",
        "obrigatoriedade vacinal", "compulsória"
    ],
    "Vida e Família": [
        "aborto", "nascituro", "interrupção da gravidez", "gestação",
        "conanda", "eca", "estatuto da criança", "menor de idade",
        "ideologia de gênero", "gênero", "transgênero", "lgbtqia"
    ],
    "Economia Digital e Tributos": [
        "pix", "drex", "moeda digital", "criptomoeda", "bitcoin",
        "imposto de renda", "irpf", "tributação", "imposto sobre renda",
        "sigilo bancário", "sigilo fiscal", "receita federal"
    ],
    "Liberdade de Expressão": [
        "censura", "liberdade de expressão", "fake news", "desinformação",
        "redes sociais", "plataformas digitais", "moderação de conteúdo",
        "pl das fake news", "regulamentação da internet"
    ],
    "Agro e Propriedade Rural": [
        "invasão de terra", "mst", "reforma agrária", "demarcação",
        "terra indígena", "quilombola", "funai", "ibama", "desmatamento",
        "agrotóxico", "defensivo agrícola", "orgânico"
    ],
    "Educação": [
        "homeschool", "educação domiciliar", "escola sem partido",
        "doutrinação", "ideologia nas escolas", "material didático",
        "fundeb", "enem"
    ],
    "Outros Temas Estratégicos": [
        "bolsonaro", "zanatta", "direita", "conservador",
        "privatização", "estatal", "petrobras", "banco do brasil",
        "lula", "pt", "comunismo", "socialismo"
    ]
}

# Lista única para busca rápida (normalizada)
def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas"""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

PALAVRAS_NORMALIZADAS = {}
for categoria, palavras in PALAVRAS_CHAVE.items():
    for palavra in palavras:
        palavra_norm = normalizar_texto(palavra)
        PALAVRAS_NORMALIZADAS[palavra_norm] = {
            "original": palavra,
            "categoria": categoria
        }

# Tipos de proposição a monitorar
TIPOS_MONITORADOS = ["PL", "PLP", "PDL", "PEC", "MPV", "PRC", "PLV"]

# Arquivos de estado
ESTADO_FILE = Path("estado_palavras_chave.json")
HISTORICO_FILE = Path("historico_palavras_chave.json")
RESUMO_DIA_FILE = Path("resumo_palavras_chave.json")

# Dias para manter histórico
DIAS_MANTER_HISTORICO = 7

# Fuso horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Limite de proposições por busca (para não sobrecarregar)
MAX_PROPOSICOES_POR_BUSCA = 500


# ============================================================
# GERENCIAMENTO DE ESTADO
# ============================================================

def carregar_estado():
    """Carrega o estado da última execução"""
    try:
        if ESTADO_FILE.exists():
            with open(ESTADO_FILE, "r") as f:
                estado = json.load(f)
                print(f"📂 Estado carregado: {estado}")
                return estado
    except Exception as e:
        print(f"⚠️ Erro ao carregar estado: {e}")
    return {"ultima_novidade": True}


def salvar_estado(teve_novidade):
    """Salva o estado para a próxima execução"""
    estado = {"ultima_novidade": teve_novidade}
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump(estado, f)
        print(f"💾 Estado salvo: {estado}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar estado: {e}")


# ============================================================
# GERENCIAMENTO DE HISTÓRICO
# ============================================================

def carregar_historico():
    """Carrega o histórico de notificações já enviadas"""
    try:
        if HISTORICO_FILE.exists():
            with open(HISTORICO_FILE, "r") as f:
                historico = json.load(f)
                print(f"📂 Histórico: {len(historico.get('notificadas', []))} tramitações")
                return historico
    except Exception as e:
        print(f"⚠️ Erro ao carregar histórico: {e}")
    return {"notificadas": [], "ultima_limpeza": None}


def salvar_historico(historico):
    """Salva o histórico de notificações"""
    try:
        with open(HISTORICO_FILE, "w") as f:
            json.dump(historico, f, indent=2)
        print(f"💾 Histórico salvo: {len(historico.get('notificadas', []))} tramitações")
    except Exception as e:
        print(f"⚠️ Erro ao salvar histórico: {e}")


def limpar_historico_antigo(historico):
    """Remove entradas antigas do histórico"""
    agora = datetime.now(FUSO_BRASILIA)
    data_corte = (agora - timedelta(days=DIAS_MANTER_HISTORICO)).isoformat()
    
    notificadas_original = len(historico.get("notificadas", []))
    historico["notificadas"] = [
        item for item in historico.get("notificadas", [])
        if item.get("registrado_em", "") >= data_corte
    ]
    
    removidas = notificadas_original - len(historico["notificadas"])
    if removidas > 0:
        print(f"🧹 Limpeza: {removidas} entradas antigas removidas")
    
    historico["ultima_limpeza"] = agora.isoformat()
    return historico


def gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao):
    """Gera uma chave única para identificar uma tramitação"""
    data_normalizada = str(data_hora_tramitacao)[:19] if data_hora_tramitacao else "sem_data"
    return f"pc_{proposicao_id}_{data_normalizada}"


def ja_foi_notificada(historico, proposicao_id, data_hora_tramitacao):
    """Verifica se uma tramitação já foi notificada"""
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao)
    for item in historico.get("notificadas", []):
        if item.get("chave") == chave:
            return True
    return False


def registrar_notificacao(historico, proposicao_id, data_hora_tramitacao, sigla, categoria):
    """Registra uma tramitação como notificada"""
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao)
    agora = datetime.now(FUSO_BRASILIA).isoformat()
    
    historico["notificadas"].append({
        "chave": chave,
        "proposicao_id": proposicao_id,
        "sigla": sigla,
        "categoria": categoria,
        "data_tramitacao": str(data_hora_tramitacao)[:19] if data_hora_tramitacao else None,
        "registrado_em": agora
    })
    return historico


# ============================================================
# GERENCIAMENTO DO RESUMO DO DIA
# ============================================================

def carregar_resumo_dia():
    """Carrega as tramitações do dia atual"""
    try:
        if RESUMO_DIA_FILE.exists():
            with open(RESUMO_DIA_FILE, "r") as f:
                resumo = json.load(f)
                print(f"📂 Resumo do dia: {len(resumo.get('tramitacoes', []))} tramitações")
                return resumo
    except Exception as e:
        print(f"⚠️ Erro ao carregar resumo: {e}")
    return {"data": None, "tramitacoes": [], "por_categoria": {}}


def salvar_resumo_dia(resumo):
    """Salva as tramitações do dia"""
    try:
        with open(RESUMO_DIA_FILE, "w") as f:
            json.dump(resumo, f, indent=2)
        print(f"💾 Resumo salvo: {len(resumo.get('tramitacoes', []))} tramitações")
    except Exception as e:
        print(f"⚠️ Erro ao salvar resumo: {e}")


def inicializar_resumo_dia():
    """Inicializa/reseta o resumo do dia"""
    agora = datetime.now(FUSO_BRASILIA)
    resumo = {
        "data": agora.strftime("%Y-%m-%d"),
        "tramitacoes": [],
        "por_categoria": {}
    }
    salvar_resumo_dia(resumo)
    return resumo


def adicionar_ao_resumo(resumo, sigla_proposicao, categoria):
    """Adiciona uma tramitação ao resumo do dia"""
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": [], "por_categoria": {}}
    
    if sigla_proposicao not in resumo["tramitacoes"]:
        resumo["tramitacoes"].append(sigla_proposicao)
        
        if categoria not in resumo["por_categoria"]:
            resumo["por_categoria"][categoria] = []
        if sigla_proposicao not in resumo["por_categoria"][categoria]:
            resumo["por_categoria"][categoria].append(sigla_proposicao)
    
    return resumo


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar_html(texto):
    """Escapa caracteres especiais para evitar erro 400 no Telegram"""
    if not texto:
        return ""
    return html.escape(str(texto))


def obter_data_hora_brasilia():
    """Retorna data/hora formatada no fuso de Brasília"""
    agora = datetime.now(FUSO_BRASILIA)
    return agora.strftime("%d/%m/%Y às %H:%M")


def encontrar_palavras_chave(texto):
    """
    Encontra palavras-chave no texto.
    Retorna lista de dicts com: original, categoria
    """
    if not texto:
        return []
    
    texto_norm = normalizar_texto(texto)
    encontradas = []
    palavras_ja_encontradas = set()
    
    for palavra_norm, info in PALAVRAS_NORMALIZADAS.items():
        if palavra_norm in texto_norm and palavra_norm not in palavras_ja_encontradas:
            encontradas.append(info)
            palavras_ja_encontradas.add(palavra_norm)
    
    return encontradas


# ============================================================
# FUNÇÕES DA API DA CÂMARA
# ============================================================

def buscar_proposicoes_recentes(dias=2):
    """
    Busca proposições que tiveram tramitação nos últimos X dias.
    Usa o endpoint de proposições com filtro de data de tramitação.
    """
    proposicoes = []
    
    # Data de corte
    agora = datetime.now(FUSO_BRASILIA)
    data_inicio = (agora - timedelta(days=dias)).strftime("%Y-%m-%d")
    data_fim = agora.strftime("%Y-%m-%d")
    
    print(f"📆 Buscando tramitações de {data_inicio} a {data_fim}")
    
    for tipo in TIPOS_MONITORADOS:
        print(f"   🔍 Buscando {tipo}...")
        pagina = 1
        
        while True:
            url = f"{BASE_URL}/proposicoes"
            params = {
                "siglaTipo": tipo,
                "dataInicio": data_inicio,
                "dataFim": data_fim,
                "ordem": "DESC",
                "ordenarPor": "id",
                "pagina": pagina,
                "itens": 100
            }
            
            try:
                resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("dados", [])
                if not items:
                    break
                
                proposicoes.extend(items)
                print(f"      Página {pagina}: {len(items)} proposições")
                
                # Verificar se há mais páginas
                links = data.get("links", [])
                tem_proxima = any(l.get("rel") == "next" for l in links)
                
                if not tem_proxima or len(proposicoes) >= MAX_PROPOSICOES_POR_BUSCA:
                    break
                
                pagina += 1
                time.sleep(0.2)
                
            except Exception as e:
                print(f"      ❌ Erro: {e}")
                break
    
    print(f"✅ Total de proposições encontradas: {len(proposicoes)}")
    return proposicoes


def buscar_tramitacoes_recentes_global(horas=48):
    """
    Busca tramitações recentes de forma global.
    Alternativa: usar endpoint de eventos/tramitacoes se disponível.
    """
    # A API da Câmara não tem um endpoint direto para "todas as tramitações recentes"
    # Então precisamos buscar proposições e depois verificar suas tramitações
    return buscar_proposicoes_recentes(dias=2)


def buscar_ultima_tramitacao(proposicao_id):
    """Busca a última tramitação de uma proposição"""
    url = f"{BASE_URL}/proposicoes/{proposicao_id}/tramitacoes"
    # API não aceita ordenarPor - buscar todas e ordenar manualmente
    params = {"itens": 100}
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        tramitacoes = data.get("dados", [])
        
        if tramitacoes:
            # Ordenar por data (mais recente primeiro)
            tramitacoes_ordenadas = sorted(
                tramitacoes,
                key=lambda x: x.get("dataHora", ""),
                reverse=True
            )
            return tramitacoes_ordenadas[0]
    except Exception as e:
        # Não logar cada erro para não poluir o output
        pass
    
    return None


def buscar_detalhes_proposicao(proposicao_id):
    """Busca detalhes completos de uma proposição (inclui ementa)"""
    url = f"{BASE_URL}/proposicoes/{proposicao_id}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("dados", {})
    except Exception as e:
        print(f"⚠️ Erro ao buscar detalhes de {proposicao_id}: {e}")
    
    return None


def tramitacao_recente(tramitacao, horas=48):
    """Verifica se a tramitação é das últimas X horas"""
    if not tramitacao or not tramitacao.get("dataHora"):
        return False
    
    try:
        data_tram = tramitacao["dataHora"][:10]
        agora_brasilia = datetime.now(FUSO_BRASILIA)
        data_corte = (agora_brasilia - timedelta(hours=horas)).strftime("%Y-%m-%d")
        return data_tram >= data_corte
    except Exception:
        return False


# ============================================================
# FORMATAÇÃO DE MENSAGENS
# ============================================================

def formatar_mensagem_bom_dia():
    """Mensagem de bom dia"""
    data_hora = obter_data_hora_brasilia()
    
    # Lista de categorias monitoradas
    categorias = list(PALAVRAS_CHAVE.keys())
    categorias_texto = ", ".join(categorias[:4]) + "..."
    
    mensagem = f"""🔑 <b>Monitor de Palavras-chave Ativo!</b>

Bom dia! O monitoramento de tramitações por palavras-chave está iniciando.

📋 <b>Categorias monitoradas:</b>
• Armas e Segurança
• Saúde - Vacinas
• Vida e Família
• Economia Digital e Tributos
• Liberdade de Expressão
• E mais...

Você será notificado quando houver tramitações em matérias com essas palavras-chave.

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_novidade(proposicao, tramitacao, palavras_encontradas):
    """Formata mensagem de nova tramitação com palavra-chave"""
    
    sigla = proposicao.get("siglaTipo", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = escapar_html(proposicao.get("ementa", ""))
    
    if len(ementa) > 250:
        ementa = ementa[:247] + "..."
    
    # Data da tramitação
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
    descricao = escapar_html(
        tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
    )
    
    # Palavras-chave encontradas (agrupar por categoria)
    categorias = {}
    for p in palavras_encontradas:
        cat = p["categoria"]
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(p["original"])
    
    # Formatar palavras-chave
    palavras_texto = []
    for cat, palavras in categorias.items():
        palavras_texto.append(f"<b>{cat}:</b> {', '.join(palavras)}")
    palavras_str = "\n".join(palavras_texto)
    
    # Link da tramitação
    prop_id = proposicao.get("id", "")
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
    
    data_hora_varredura = obter_data_hora_brasilia()
    
    mensagem = f"""🔑 <b>Palavra-chave Detectada!</b>

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏷️ <b>Palavras encontradas:</b>
{palavras_str}

📅 {data_formatada} → {descricao}

🔗 <a href="{link}">Ver tramitação completa</a>

⏰ <i>Varredura: {data_hora_varredura}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_completa():
    """Mensagem completa quando não há novidades"""
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""🔑 <b>Monitor de Palavras-chave:</b>

Na última varredura não foram encontradas tramitações recentes com palavras-chave de interesse.

Continue atento! 👀

⏰ <i>Varredura: {data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_curta():
    """Mensagem curta quando não há novidades"""
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""🔑 Ainda sem novidades nas palavras-chave monitoradas.

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_resumo_dia(resumo):
    """Formata resumo das tramitações do dia"""
    data_hora = obter_data_hora_brasilia()
    
    tramitacoes = resumo.get("tramitacoes", [])
    por_categoria = resumo.get("por_categoria", {})
    total = len(tramitacoes)
    
    if total == 0:
        mensagem = f"""🌙 <b>Resumo do Dia - Palavras-chave</b>

Hoje não houve tramitações com palavras-chave de interesse.

Até amanhã! 👋

⏰ <i>{data_hora}</i>"""
    else:
        # Agrupar por categoria
        detalhes = []
        for categoria, props in por_categoria.items():
            if props:
                props_texto = ", ".join(props[:5])
                if len(props) > 5:
                    props_texto += f" (+{len(props)-5})"
                detalhes.append(f"• <b>{categoria}:</b> {props_texto}")
        
        detalhes_str = "\n".join(detalhes) if detalhes else "• Nenhuma categoria específica"
        
        mensagem = f"""🌙 <b>Resumo do Dia - Palavras-chave</b>

📊 <b>Total:</b> {total} tramitação(ões) com palavras-chave

<b>Por categoria:</b>
{detalhes_str}

Até amanhã! 👋

⏰ <i>{data_hora}</i>"""
    
    return mensagem


# ============================================================
# TELEGRAM
# ============================================================

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
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        try:
            error_detail = resp.json()
            print(f"   Detalhe: {error_detail}")
        except:
            print(f"   Response: {resp.text}")
        return False
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return False


# ============================================================
# FUNÇÕES DE MODO DE EXECUÇÃO
# ============================================================

def executar_bom_dia():
    """Envia mensagem de bom dia e reseta o resumo do dia"""
    print("☀️ MODO: BOM DIA")
    print("=" * 60)
    
    inicializar_resumo_dia()
    print("📋 Resumo do dia inicializado")
    
    mensagem = formatar_mensagem_bom_dia()
    enviar_telegram(mensagem)
    
    print("\n✅ Bom dia enviado!")


def executar_resumo_dia():
    """Envia resumo das tramitações do dia"""
    print("🌙 MODO: RESUMO DO DIA")
    print("=" * 60)
    
    resumo = carregar_resumo_dia()
    
    print(f"📊 Tramitações do dia: {len(resumo.get('tramitacoes', []))}")
    for cat, props in resumo.get("por_categoria", {}).items():
        print(f"   • {cat}: {len(props)}")
    
    mensagem = formatar_mensagem_resumo_dia(resumo)
    enviar_telegram(mensagem)
    
    print("\n✅ Resumo do dia enviado!")


def executar_varredura():
    """Executa varredura de tramitações por palavras-chave"""
    
    data_hora_brasilia = obter_data_hora_brasilia()
    
    print("🔍 MODO: VARREDURA PALAVRAS-CHAVE")
    print("=" * 60)
    print(f"📅 Data/Hora (Brasília): {data_hora_brasilia}")
    print()
    
    # Carregar estados
    estado = carregar_estado()
    ultima_teve_novidade = estado.get("ultima_novidade", True)
    
    historico = carregar_historico()
    historico = limpar_historico_antigo(historico)
    
    resumo = carregar_resumo_dia()
    
    # Verificar novo dia
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        print("📋 Novo dia - inicializando resumo")
        resumo = {"data": data_hoje, "tramitacoes": [], "por_categoria": {}}
    
    # 1. Buscar proposições recentes
    proposicoes = buscar_proposicoes_recentes(dias=2)
    
    if not proposicoes:
        print("⚠️ Nenhuma proposição encontrada")
        if ultima_teve_novidade:
            enviar_telegram(formatar_mensagem_sem_novidades_completa())
        else:
            enviar_telegram(formatar_mensagem_sem_novidades_curta())
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        return
    
    # 2. Verificar palavras-chave em cada proposição
    print("\n🔍 Analisando proposições...\n")
    
    props_com_palavra_chave = []
    props_ja_notificadas = 0
    analisadas = 0
    
    for i, prop in enumerate(proposicoes, 1):
        sigla_prop = f"{prop['siglaTipo']} {prop['numero']}/{prop['ano']}"
        
        if i % 50 == 0 or i == 1:
            print(f"📊 Progresso: {i}/{len(proposicoes)}...")
        
        # Buscar detalhes e tramitação
        detalhes = buscar_detalhes_proposicao(prop["id"])
        if not detalhes:
            continue
        
        tramitacao = buscar_ultima_tramitacao(prop["id"])
        if not tramitacao:
            continue
        
        analisadas += 1
        
        # Verificar se é tramitação recente
        if not tramitacao_recente(tramitacao, horas=48):
            continue
        
        # Juntar textos para busca de palavras-chave
        ementa = detalhes.get("ementa", "")
        despacho = tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
        texto_completo = f"{ementa} {despacho}"
        
        # Buscar palavras-chave
        palavras_encontradas = encontrar_palavras_chave(texto_completo)
        
        if palavras_encontradas:
            # Verificar se já foi notificada
            data_hora_tram = tramitacao.get("dataHora", "")
            
            if ja_foi_notificada(historico, prop["id"], data_hora_tram):
                print(f"   ⏭️ JÁ NOTIFICADA: {sigla_prop}")
                props_ja_notificadas += 1
            else:
                categorias = set(p["categoria"] for p in palavras_encontradas)
                print(f"   ✅ NOVA! {sigla_prop} [{', '.join(categorias)}]")
                
                props_com_palavra_chave.append({
                    "proposicao": detalhes,
                    "tramitacao": tramitacao,
                    "sigla": sigla_prop,
                    "palavras": palavras_encontradas,
                    "categoria": list(categorias)[0]  # Categoria principal
                })
        
        time.sleep(0.15)
    
    # 3. Resumo
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Total de proposições: {len(proposicoes)}")
    print(f"   Analisadas com sucesso: {analisadas}")
    print(f"   Com palavras-chave (novas): {len(props_com_palavra_chave)}")
    print(f"   Já notificadas anteriormente: {props_ja_notificadas}")
    print(f"{'=' * 60}")
    
    # 4. Enviar notificações
    if props_com_palavra_chave:
        print(f"\n📤 Enviando {len(props_com_palavra_chave)} notificação(ões)...\n")
        
        enviadas = 0
        for item in props_com_palavra_chave:
            mensagem = formatar_mensagem_novidade(
                item["proposicao"],
                item["tramitacao"],
                item["palavras"]
            )
            
            if enviar_telegram(mensagem):
                historico = registrar_notificacao(
                    historico,
                    item["proposicao"]["id"],
                    item["tramitacao"].get("dataHora", ""),
                    item["sigla"],
                    item["categoria"]
                )
                resumo = adicionar_ao_resumo(resumo, item["sigla"], item["categoria"])
                enviadas += 1
            
            time.sleep(1)  # Rate limit
        
        salvar_estado(True)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        print(f"\n✅ Processo concluído! {enviadas} mensagens enviadas.")
    
    else:
        print("\n📤 Enviando mensagem de status...")
        
        if ultima_teve_novidade:
            print("   → Mensagem COMPLETA")
            enviar_telegram(formatar_mensagem_sem_novidades_completa())
        else:
            print("   → Mensagem CURTA")
            enviar_telegram(formatar_mensagem_sem_novidades_curta())
        
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        print("\n✅ Processo concluído!")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    """Função principal - executa de acordo com o modo"""
    
    print("=" * 60)
    print("🔑 MONITOR DE PALAVRAS-CHAVE")
    print("    Tramitações por tema de interesse")
    print("=" * 60)
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
    print(f"📋 Modo de execução: {MODO_EXECUCAO}")
    print(f"📚 Palavras-chave: {len(PALAVRAS_NORMALIZADAS)} termos")
    print()
    
    # Executar de acordo com o modo
    if MODO_EXECUCAO == "bom_dia":
        executar_bom_dia()
    elif MODO_EXECUCAO == "resumo":
        executar_resumo_dia()
    else:
        executar_varredura()


if __name__ == "__main__":
    main()