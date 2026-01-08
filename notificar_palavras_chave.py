#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_palavras_chave.py
========================================
Monitor de PAUTAS por PALAVRAS-CHAVE
Busca eventos/pautas de comissões e notifica quando encontrar
matérias com palavras-chave de interesse.

v4: Estratégia baseada em EVENTOS (como o Monitor Zanatta)
- Busca eventos dos próximos 7 dias
- Analisa pautas de cada evento
- Filtra por palavras-chave
"""

import os
import sys
import json
import html
import requests
import time
import unicodedata
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorPalavrasChave/2.0 (gabinete-julia-zanatta)"}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_PALAVRAS")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PALAVRAS")

# Fallback para tokens gerais
if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# ============================================================
# DADOS DA DEPUTADA
# ============================================================

DEPUTADA_ID = 220559
DEPUTADA_NOME = "Zanatta"
DEPUTADA_PARTIDO = "PL"
DEPUTADA_UF = "SC"

# ============================================================
# PALAVRAS-CHAVE DE INTERESSE
# ============================================================

PALAVRAS_CHAVE = {
    "Armas e Segurança": [
        "arma", "armas", "armamento", "munição", "cac", "atirador",
        "caçador", "colecionador", "porte", "legítima defesa",
        "estatuto do desarmamento", "defesa pessoal"
    ],
    "Saúde - Vacinas": [
        "vacina", "vacinas", "vacinação", "imunização", "imunizante",
        "passaporte vacinal", "obrigatoriedade vacinal"
    ],
    "Vida e Família": [
        "aborto", "nascituro", "interrupção da gravidez",
        "conanda", "eca", "ideologia de gênero", "transgênero"
    ],
    "Economia Digital e Tributos": [
        "pix", "drex", "moeda digital", "criptomoeda",
        "imposto de renda", "irpf", "sigilo bancário"
    ],
    "Liberdade de Expressão": [
        "censura", "liberdade de expressão", "fake news",
        "pl das fake news", "regulamentação da internet"
    ],
    "Agro e Propriedade Rural": [
        "invasão de terra", "mst", "reforma agrária",
        "terra indígena", "demarcação", "agrotóxico"
    ],
    "Educação": [
        "homeschool", "educação domiciliar", "escola sem partido",
        "doutrinação"
    ],
    "Outros Temas": [
        "zanatta", "privatização", "estatal"
    ]
}

# Arquivos de estado
ESTADO_FILE = Path("estado_palavras_chave.json")
HISTORICO_FILE = Path("historico_palavras_chave.json")
RESUMO_DIA_FILE = Path("resumo_palavras_chave.json")

DIAS_MANTER_HISTORICO = 7
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# ============================================================
# RECESSO PARLAMENTAR
# ============================================================
# Dez 23 a Jan 31 (fim de ano)
# Jul 18 a Jul 31 (meio de ano - aproximado)

def esta_em_recesso():
    """Verifica se estamos em período de recesso parlamentar"""
    agora = datetime.now(FUSO_BRASILIA)
    mes = agora.month
    dia = agora.day
    
    # Recesso de fim de ano: 23/dez a 31/jan
    if mes == 12 and dia >= 23:
        return True
    if mes == 1:
        return True
    
    # Recesso de meio de ano: 18/jul a 31/jul
    if mes == 7 and dia >= 18:
        return True
    
    return False


def get_data_retorno_sessao():
    """Retorna a data prevista de retorno da sessão legislativa"""
    agora = datetime.now(FUSO_BRASILIA)
    mes = agora.month
    
    if mes == 12 or mes == 1:
        # Recesso de fim de ano -> volta em 02/fev
        ano = agora.year if mes == 12 else agora.year
        if mes == 12:
            ano += 1
        return f"02/02/{ano}"
    elif mes == 7:
        # Recesso de meio de ano -> volta em 01/ago
        return f"01/08/{agora.year}"
    
    return "em breve"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalize_text(texto):
    """Remove acentos e converte para minúsculas"""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto


def escapar_html(texto):
    """Escapa caracteres especiais para Telegram"""
    if not texto:
        return ""
    return html.escape(str(texto))


def obter_data_hora_brasilia():
    """Retorna data/hora formatada no fuso de Brasília"""
    agora = datetime.now(FUSO_BRASILIA)
    return agora.strftime("%d/%m/%Y às %H:%M")


# ============================================================
# GERENCIAMENTO DE ESTADO E HISTÓRICO
# ============================================================

def carregar_estado():
    try:
        if ESTADO_FILE.exists():
            with open(ESTADO_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"ultima_novidade": True}


def salvar_estado(teve_novidade):
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump({"ultima_novidade": teve_novidade}, f)
    except Exception:
        pass


def carregar_historico():
    try:
        if HISTORICO_FILE.exists():
            with open(HISTORICO_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"notificadas": [], "ultima_limpeza": None}


def salvar_historico(historico):
    try:
        with open(HISTORICO_FILE, "w") as f:
            json.dump(historico, f, indent=2)
    except Exception:
        pass


def limpar_historico_antigo(historico):
    agora = datetime.now(FUSO_BRASILIA)
    data_corte = (agora - timedelta(days=DIAS_MANTER_HISTORICO)).isoformat()
    
    historico["notificadas"] = [
        item for item in historico.get("notificadas", [])
        if item.get("registrado_em", "") >= data_corte
    ]
    historico["ultima_limpeza"] = agora.isoformat()
    return historico


def gerar_chave_item(evento_id, prop_id):
    """Chave única: evento + proposição"""
    return f"pc_{evento_id}_{prop_id}"


def ja_foi_notificada(historico, evento_id, prop_id):
    chave = gerar_chave_item(evento_id, prop_id)
    return any(item.get("chave") == chave for item in historico.get("notificadas", []))


def registrar_notificacao(historico, evento_id, prop_id, sigla, categoria):
    chave = gerar_chave_item(evento_id, prop_id)
    agora = datetime.now(FUSO_BRASILIA).isoformat()
    historico["notificadas"].append({
        "chave": chave,
        "sigla": sigla,
        "categoria": categoria,
        "registrado_em": agora
    })
    return historico


def carregar_resumo_dia():
    try:
        if RESUMO_DIA_FILE.exists():
            with open(RESUMO_DIA_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"data": None, "tramitacoes": [], "por_categoria": {}}


def salvar_resumo_dia(resumo):
    try:
        with open(RESUMO_DIA_FILE, "w") as f:
            json.dump(resumo, f, indent=2)
    except Exception:
        pass


def inicializar_resumo_dia():
    agora = datetime.now(FUSO_BRASILIA)
    resumo = {"data": agora.strftime("%Y-%m-%d"), "tramitacoes": [], "por_categoria": {}}
    salvar_resumo_dia(resumo)
    return resumo


def adicionar_ao_resumo(resumo, sigla, categoria):
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": [], "por_categoria": {}}
    
    if sigla not in resumo["tramitacoes"]:
        resumo["tramitacoes"].append(sigla)
        if categoria not in resumo["por_categoria"]:
            resumo["por_categoria"][categoria] = []
        resumo["por_categoria"][categoria].append(sigla)
    
    return resumo


# ============================================================
# API DA CÂMARA - EVENTOS E PAUTAS
# ============================================================

def safe_get(url, params=None, timeout=30):
    """GET com tratamento de erros"""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None


def fetch_eventos(start_date, end_date):
    """Busca eventos (reuniões de comissões) no período"""
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
        if not data:
            break
        
        dados = data.get("dados", [])
        if not dados:
            break
        
        eventos.extend(dados)
        
        links = data.get("links", [])
        if not any(link.get("rel") == "next" for link in links):
            break
        
        pagina += 1
        time.sleep(0.1)
    
    return eventos


def fetch_pauta_evento(event_id):
    """Busca a pauta de um evento"""
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    if not data:
        return []
    return data.get("dados", [])


def get_proposicao_id_from_item(item):
    """Extrai ID da proposição de um item da pauta"""
    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_"],
        ["proposicaoPrincipal"],
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
    
    # Tentar extrair de codProposicao
    cod = item.get("codProposicao") or item.get("idProposicao")
    if cod:
        return str(cod)
    
    return None


def fetch_proposicao_info(prop_id):
    """Busca informações de uma proposição"""
    data = safe_get(f"{BASE_URL}/proposicoes/{prop_id}")
    if not data:
        return None
    return data.get("dados", {})


def fetch_ids_autoria_deputada(id_deputada):
    """Busca todos os IDs de proposições de autoria da deputada"""
    ids = set()
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "ASC", "ordenarPor": "id"}
    
    print(f"   📋 Buscando proposições de autoria da deputada...")
    
    while True:
        data = safe_get(url, params=params)
        if not data:
            break
        
        for d in data.get("dados", []):
            if d.get("id"):
                ids.add(str(d["id"]))
        
        # Próxima página
        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        
        if not next_link:
            break
        
        url = next_link
        params = {}
        time.sleep(0.1)
    
    print(f"   ✅ {len(ids)} proposições de autoria encontradas")
    return ids


def verificar_relatoria_deputada(item):
    """Verifica se a deputada é relatora do item da pauta"""
    relator = item.get("relator") or {}
    nome = relator.get("nome") or ""
    partido = relator.get("siglaPartido") or ""
    uf = relator.get("siglaUf") or ""
    
    # Verificar se o nome contém "Zanatta"
    if normalize_text(DEPUTADA_NOME) not in normalize_text(nome):
        return False
    
    # Verificar partido se disponível
    if partido and normalize_text(DEPUTADA_PARTIDO) != normalize_text(partido):
        return False
    
    # Verificar UF se disponível
    if uf and normalize_text(DEPUTADA_UF) != normalize_text(uf):
        return False
    
    return True


# ============================================================
# BUSCA DE PALAVRAS-CHAVE
# ============================================================

def preparar_palavras_chave():
    """Prepara lista normalizada de palavras-chave"""
    palavras_norm = []
    for categoria, palavras in PALAVRAS_CHAVE.items():
        for palavra in palavras:
            if palavra.strip():
                palavras_norm.append((normalize_text(palavra), palavra, categoria))
    return palavras_norm


def buscar_palavras_no_item(item, palavras_normalizadas, prop_info=None):
    """
    Busca palavras-chave na ementa e descrição do item.
    Retorna lista de (palavra_original, categoria)
    """
    textos = []
    
    # Campos do item da pauta
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        v = item.get(chave)
        if v:
            textos.append(str(v))
    
    # Campos da proposição interna
    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop.get(chave)
        if v:
            textos.append(str(v))
    
    # Proposição relacionada
    prop_rel = item.get("proposicaoRelacionada") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop_rel.get(chave)
        if v:
            textos.append(str(v))
    
    # Info da proposição buscada na API
    if prop_info:
        if prop_info.get("ementa"):
            textos.append(prop_info["ementa"])
    
    texto_norm = normalize_text(" ".join(textos))
    encontradas = []
    palavras_ja = set()
    
    for kw_norm, kw_original, categoria in palavras_normalizadas:
        if not kw_norm or kw_norm in palavras_ja:
            continue
        
        # Regex com word boundary para palavra inteira
        pattern = r'\b' + re.escape(kw_norm) + r'\b'
        if re.search(pattern, texto_norm):
            encontradas.append((kw_original, categoria))
            palavras_ja.add(kw_norm)
    
    return encontradas


# ============================================================
# FORMATAÇÃO DE MENSAGENS
# ============================================================

def formatar_mensagem_bom_dia():
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""📢 <b>Monitor Parlamentar Informa:</b>

☀️ Bom dia! Monitorando pautas das comissões.

📋 <b>Monitoramento ativo:</b>
• Matérias de <b>autoria</b> da Dep. Zanatta
• Matérias com <b>relatoria</b> da Dep. Zanatta
• Matérias com <b>palavras-chave</b> de interesse

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_novidade(evento, item, prop_info, palavras_encontradas):
    """Formata mensagem de matéria encontrada com palavra-chave"""
    
    # Dados do evento
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "")
    data_evento = evento.get("dataHoraInicio", "")[:10]
    if data_evento:
        try:
            dt = datetime.fromisoformat(data_evento)
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = data_evento
    else:
        data_formatada = "Data não informada"
    
    # Dados da proposição
    if prop_info:
        sigla = prop_info.get("siglaTipo", "")
        numero = prop_info.get("numero", "")
        ano = prop_info.get("ano", "")
        ementa = escapar_html(prop_info.get("ementa", ""))
        prop_id = prop_info.get("id", "")
    else:
        sigla = item.get("siglaTipo", "") or item.get("proposicao", {}).get("siglaTipo", "")
        numero = item.get("numero", "") or item.get("proposicao", {}).get("numero", "")
        ano = item.get("ano", "") or item.get("proposicao", {}).get("ano", "")
        ementa = escapar_html(item.get("ementa", "") or item.get("titulo", ""))
        prop_id = get_proposicao_id_from_item(item)
    
    if len(ementa) > 250:
        ementa = ementa[:247] + "..."
    
    # Palavras-chave agrupadas por categoria
    por_categoria = {}
    for palavra, categoria in palavras_encontradas:
        if categoria not in por_categoria:
            por_categoria[categoria] = []
        por_categoria[categoria].append(palavra)
    
    palavras_texto = []
    for cat, palavras in por_categoria.items():
        palavras_texto.append(f"<b>{cat}:</b> {', '.join(palavras)}")
    palavras_str = "\n".join(palavras_texto)
    
    # Link
    if prop_id:
        link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
    else:
        link = ""
    
    data_hora = obter_data_hora_brasilia()
    
    link_texto = f'\n🔗 <a href="{link}">Ver tramitação</a>' if link else ""
    
    mensagem = f"""📢 <b>Monitor Parlamentar Informa:</b>

🔑 <b>Palavra-chave na Pauta!</b>

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏛️ <b>Comissão:</b> {orgao}
📅 <b>Data:</b> {data_formatada}

🏷️ <b>Palavras encontradas:</b>
{palavras_str}{link_texto}

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_completa():
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""📢 <b>Monitor Parlamentar Informa:</b>

Não foram encontradas matérias de interesse nas pautas (autoria, relatoria ou palavras-chave).

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_curta():
    data_hora = obter_data_hora_brasilia()
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

Sem novidades nas pautas.

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_recesso():
    """Mensagem durante o recesso parlamentar"""
    data_hora = obter_data_hora_brasilia()
    data_retorno = get_data_retorno_sessao()
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

🏖️ <b>Recesso Parlamentar</b>

O Congresso está em recesso. Não há reuniões de comissões neste período.

📅 <b>Previsão de retorno:</b> {data_retorno}

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_autoria(evento, prop_info):
    """Formata mensagem quando matéria de AUTORIA entra na pauta"""
    
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "")
    data_evento = evento.get("dataHoraInicio", "")[:10]
    if data_evento:
        try:
            dt = datetime.fromisoformat(data_evento)
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = data_evento
    else:
        data_formatada = "Data não informada"
    
    sigla = prop_info.get("siglaTipo", "")
    numero = prop_info.get("numero", "")
    ano = prop_info.get("ano", "")
    ementa = escapar_html(prop_info.get("ementa", ""))
    prop_id = prop_info.get("id", "")
    
    if len(ementa) > 250:
        ementa = ementa[:247] + "..."
    
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}" if prop_id else ""
    link_texto = f'\n🔗 <a href="{link}">Ver tramitação</a>' if link else ""
    
    data_hora = obter_data_hora_brasilia()
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

📝 <b>Matéria de AUTORIA na Pauta!</b>

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏛️ <b>Comissão:</b> {orgao}
📅 <b>Data:</b> {data_formatada}

👤 <b>Autoria:</b> Dep. Júlia Zanatta (PL-SC){link_texto}

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_relatoria(evento, prop_info):
    """Formata mensagem quando deputada é RELATORA de matéria na pauta"""
    
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "")
    data_evento = evento.get("dataHoraInicio", "")[:10]
    if data_evento:
        try:
            dt = datetime.fromisoformat(data_evento)
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = data_evento
    else:
        data_formatada = "Data não informada"
    
    sigla = prop_info.get("siglaTipo", "")
    numero = prop_info.get("numero", "")
    ano = prop_info.get("ano", "")
    ementa = escapar_html(prop_info.get("ementa", ""))
    prop_id = prop_info.get("id", "")
    
    if len(ementa) > 250:
        ementa = ementa[:247] + "..."
    
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}" if prop_id else ""
    link_texto = f'\n🔗 <a href="{link}">Ver tramitação</a>' if link else ""
    
    data_hora = obter_data_hora_brasilia()
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

📋 <b>RELATORIA na Pauta!</b>

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏛️ <b>Comissão:</b> {orgao}
📅 <b>Data:</b> {data_formatada}

👩‍⚖️ <b>Relatora:</b> Dep. Júlia Zanatta (PL-SC){link_texto}

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_resumo_dia(resumo):
    data_hora = obter_data_hora_brasilia()
    
    tramitacoes = resumo.get("tramitacoes", [])
    por_categoria = resumo.get("por_categoria", {})
    total = len(tramitacoes)
    
    if total == 0:
        return f"""📢 <b>Monitor Parlamentar Informa:</b>

🌙 <b>Resumo do Dia</b>

Hoje não houve matérias de interesse nas pautas.

⏰ <i>{data_hora}</i>"""
    
    # Separar por tipo
    autoria = por_categoria.get("Autoria", [])
    relatoria = por_categoria.get("Relatoria", [])
    
    # Palavras-chave (todas as outras categorias)
    palavras_categorias = {k: v for k, v in por_categoria.items() if k not in ["Autoria", "Relatoria"]}
    
    detalhes = []
    
    if autoria:
        detalhes.append(f"📝 <b>Autoria:</b> {', '.join(autoria[:5])}")
    
    if relatoria:
        detalhes.append(f"📋 <b>Relatoria:</b> {', '.join(relatoria[:5])}")
    
    for categoria, props in palavras_categorias.items():
        if props:
            props_texto = ", ".join(props[:3])
            if len(props) > 3:
                props_texto += f" (+{len(props)-3})"
            detalhes.append(f"🔑 <b>{categoria}:</b> {props_texto}")
    
    detalhes_str = "\n".join(detalhes)
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

🌙 <b>Resumo do Dia</b>

📊 <b>Total:</b> {total} matéria(s)

{detalhes_str}

⏰ <i>{data_hora}</i>"""


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensagem):
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
        print("✅ Mensagem enviada!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        return False


# ============================================================
# FUNÇÕES DE EXECUÇÃO
# ============================================================

def executar_bom_dia():
    print("☀️ MODO: BOM DIA")
    
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO - sem mensagem de bom dia")
        print("   Mensagem será enviada apenas no resumo do dia.")
        return
    
    inicializar_resumo_dia()
    enviar_telegram(formatar_mensagem_bom_dia())
    print("✅ Bom dia enviado!")


def executar_resumo_dia():
    print("🌙 MODO: RESUMO DO DIA")
    
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO")
        enviar_telegram(formatar_mensagem_recesso())
        print("✅ Mensagem de recesso enviada!")
        return
    
    resumo = carregar_resumo_dia()
    print(f"📊 Tramitações do dia: {len(resumo.get('tramitacoes', []))}")
    enviar_telegram(formatar_mensagem_resumo_dia(resumo))
    print("✅ Resumo enviado!")


def executar_varredura():
    data_hora = obter_data_hora_brasilia()
    
    print("🔍 MODO: VARREDURA PALAVRAS-CHAVE + AUTORIA/RELATORIA")
    print("=" * 60)
    print(f"📅 Data/Hora: {data_hora}")
    print()
    
    # Verificar se está em recesso
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO - pulando varredura")
        print("   Não há reuniões de comissões neste período.")
        print("✅ Nenhuma ação necessária.")
        return
    
    # Carregar estados
    estado = carregar_estado()
    ultima_teve_novidade = estado.get("ultima_novidade", True)
    
    historico = carregar_historico()
    historico = limpar_historico_antigo(historico)
    print(f"📂 Histórico: {len(historico.get('notificadas', []))} itens")
    
    resumo = carregar_resumo_dia()
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": [], "por_categoria": {}}
    
    # Preparar palavras-chave
    palavras_norm = preparar_palavras_chave()
    print(f"🔑 Palavras-chave: {len(palavras_norm)} termos")
    
    # Buscar IDs de proposições de autoria da deputada
    ids_autoria = fetch_ids_autoria_deputada(DEPUTADA_ID)
    
    # Buscar eventos dos próximos 7 dias
    start_date = agora
    end_date = agora + timedelta(days=7)
    
    print(f"\n📆 Buscando eventos de {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}...")
    eventos = fetch_eventos(start_date, end_date)
    print(f"✅ {len(eventos)} eventos encontrados")
    
    if not eventos:
        print("⚠️ Nenhum evento encontrado")
        if ultima_teve_novidade:
            enviar_telegram(formatar_mensagem_sem_novidades_completa())
        else:
            enviar_telegram(formatar_mensagem_sem_novidades_curta())
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        return
    
    # Analisar pautas
    print("\n🔍 Analisando pautas...\n")
    
    itens_palavras_chave = []
    itens_autoria = []
    itens_relatoria = []
    itens_ja_notificados = 0
    total_itens_pauta = 0
    
    for i, evento in enumerate(eventos, 1):
        evento_id = evento.get("id")
        orgao = evento.get("orgaos", [{}])[0].get("sigla", "?")
        
        if i % 20 == 0 or i == 1:
            print(f"📊 Progresso: {i}/{len(eventos)} eventos...")
        
        # Buscar pauta do evento
        pauta = fetch_pauta_evento(evento_id)
        if not pauta:
            continue
        
        total_itens_pauta += len(pauta)
        
        for item in pauta:
            prop_id = get_proposicao_id_from_item(item)
            
            # Buscar info da proposição para ter ementa completa
            prop_info = None
            if prop_id:
                prop_info = fetch_proposicao_info(prop_id)
            
            # Verificar AUTORIA
            is_autoria = prop_id and prop_id in ids_autoria
            
            # Verificar RELATORIA
            is_relatoria = verificar_relatoria_deputada(item)
            
            # Verificar PALAVRAS-CHAVE
            palavras_encontradas = buscar_palavras_no_item(item, palavras_norm, prop_info)
            
            # Se não tem nenhum interesse, pular
            if not (is_autoria or is_relatoria or palavras_encontradas):
                continue
            
            # Montar sigla
            if prop_info:
                sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
            else:
                sigla = item.get("titulo", "Item")[:30]
            
            # Verificar se já notificou (chave única por tipo)
            chave_base = f"{evento_id}_{prop_id or 'sem_id'}"
            
            # AUTORIA
            if is_autoria:
                chave_autoria = f"autoria_{chave_base}"
                if ja_foi_notificada(historico, "autoria", chave_autoria):
                    itens_ja_notificados += 1
                else:
                    print(f"   📝 AUTORIA: {sigla} em {orgao}")
                    itens_autoria.append({
                        "evento": evento,
                        "item": item,
                        "prop_info": prop_info,
                        "prop_id": prop_id,
                        "sigla": sigla,
                        "chave": chave_autoria
                    })
            
            # RELATORIA
            if is_relatoria:
                chave_relatoria = f"relatoria_{chave_base}"
                if ja_foi_notificada(historico, "relatoria", chave_relatoria):
                    itens_ja_notificados += 1
                else:
                    print(f"   📋 RELATORIA: {sigla} em {orgao}")
                    itens_relatoria.append({
                        "evento": evento,
                        "item": item,
                        "prop_info": prop_info,
                        "prop_id": prop_id,
                        "sigla": sigla,
                        "chave": chave_relatoria
                    })
            
            # PALAVRAS-CHAVE
            if palavras_encontradas:
                chave_palavras = f"palavras_{chave_base}"
                if ja_foi_notificada(historico, "palavras", chave_palavras):
                    itens_ja_notificados += 1
                else:
                    categoria_principal = palavras_encontradas[0][1]
                    print(f"   🔑 PALAVRAS: {sigla} em {orgao} - {[p[0] for p in palavras_encontradas]}")
                    itens_palavras_chave.append({
                        "evento": evento,
                        "item": item,
                        "prop_info": prop_info,
                        "prop_id": prop_id,
                        "palavras": palavras_encontradas,
                        "sigla": sigla,
                        "categoria": categoria_principal,
                        "chave": chave_palavras
                    })
        
        time.sleep(0.1)
    
    # Resumo
    total_novos = len(itens_autoria) + len(itens_relatoria) + len(itens_palavras_chave)
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Eventos analisados: {len(eventos)}")
    print(f"   Itens de pauta: {total_itens_pauta}")
    print(f"   AUTORIA (novos): {len(itens_autoria)}")
    print(f"   RELATORIA (novos): {len(itens_relatoria)}")
    print(f"   PALAVRAS-CHAVE (novos): {len(itens_palavras_chave)}")
    print(f"   Já notificados: {itens_ja_notificados}")
    print(f"{'=' * 60}")
    
    # Enviar notificações
    enviadas = 0
    
    # 1. Notificações de AUTORIA (prioridade alta)
    if itens_autoria:
        print(f"\n📤 Enviando {len(itens_autoria)} notificação(ões) de AUTORIA...\n")
        for item_data in itens_autoria:
            mensagem = formatar_mensagem_autoria(
                item_data["evento"],
                item_data["prop_info"] or {}
            )
            if enviar_telegram(mensagem):
                historico = registrar_notificacao(
                    historico,
                    "autoria",
                    item_data["chave"],
                    item_data["sigla"],
                    "Autoria"
                )
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], "Autoria")
                enviadas += 1
            time.sleep(1)
    
    # 2. Notificações de RELATORIA (prioridade alta)
    if itens_relatoria:
        print(f"\n📤 Enviando {len(itens_relatoria)} notificação(ões) de RELATORIA...\n")
        for item_data in itens_relatoria:
            mensagem = formatar_mensagem_relatoria(
                item_data["evento"],
                item_data["prop_info"] or {}
            )
            if enviar_telegram(mensagem):
                historico = registrar_notificacao(
                    historico,
                    "relatoria",
                    item_data["chave"],
                    item_data["sigla"],
                    "Relatoria"
                )
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], "Relatoria")
                enviadas += 1
            time.sleep(1)
    
    # 3. Notificações de PALAVRAS-CHAVE
    if itens_palavras_chave:
        print(f"\n📤 Enviando {len(itens_palavras_chave)} notificação(ões) de PALAVRAS-CHAVE...\n")
        for item_data in itens_palavras_chave:
            mensagem = formatar_mensagem_novidade(
                item_data["evento"],
                item_data["item"],
                item_data["prop_info"],
                item_data["palavras"]
            )
            if enviar_telegram(mensagem):
                historico = registrar_notificacao(
                    historico,
                    "palavras",
                    item_data["chave"],
                    item_data["sigla"],
                    item_data["categoria"]
                )
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], item_data["categoria"])
                enviadas += 1
            time.sleep(1)
    
    # Se não teve nenhuma novidade
    if total_novos == 0:
        print("\n📤 Enviando mensagem de status...")
        if ultima_teve_novidade:
            enviar_telegram(formatar_mensagem_sem_novidades_completa())
        else:
            enviar_telegram(formatar_mensagem_sem_novidades_curta())
    
    # Salvar estados
    salvar_estado(total_novos > 0)
    salvar_historico(historico)
    salvar_resumo_dia(resumo)
    
    print(f"\n✅ {enviadas} mensagens enviadas!")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🔑 MONITOR DE PAUTAS v5")
    print("    Autoria + Relatoria + Palavras-chave")
    print("=" * 60)
    print()
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN não configurado!")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID não configurado!")
        sys.exit(1)
    
    print(f"✅ Bot Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"📋 Modo: {MODO_EXECUCAO}")
    print()
    
    if MODO_EXECUCAO == "bom_dia":
        executar_bom_dia()
    elif MODO_EXECUCAO == "resumo":
        executar_resumo_dia()
    else:
        executar_varredura()


if __name__ == "__main__":
    main()