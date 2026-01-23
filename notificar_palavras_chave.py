#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_palavras_chave.py
========================================
Monitor de PAUTAS por PALAVRAS-CHAVE

v7: 
- INTEGRAÇÃO COM SENADO
- Quando projeto está no Senado: 🔵 ZANATTA NO SENADO
- Monitora movimentações de proposições no Senado 
- Lógica diferenciada Telegram vs Email
- Email só recebe: matérias encontradas + resumo do dia
- Telegram recebe tudo
- Link do painel nos emails
"""

import os
import sys
import json
import html
import requests
import time
import unicodedata
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorPalavrasChave/2.0 (gabinete-julia-zanatta)"}
SENADO_BASE_URL = "https://legis.senado.leg.br/dadosabertos"
HEADERS_SENADO = {"User-Agent": "MonitorPalavrasChave/2.0", "Accept": "application/json"}


LINK_PAINEL = "https://monitorzanatta.streamlit.app/"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_PALAVRAS")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PALAVRAS")

if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Email (SMTP)
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Carregar emails do arquivo JSON (cadastrados via painel)
def carregar_emails_cadastrados():
    """Carrega emails do arquivo emails_cadastrados.json"""
    try:
        arquivo = Path("emails_cadastrados.json")
        if arquivo.exists():
            with open(arquivo, "r") as f:
                data = json.load(f)
                return data.get("emails", [])
    except:
        pass
    return []

# Combinar emails do secret + arquivo JSON
EMAIL_RECIPIENTS_BASE = os.getenv("EMAIL_RECIPIENTS_PALAVRAS", os.getenv("EMAIL_RECIPIENTS", ""))
EMAIL_RECIPIENTS_ARQUIVO = carregar_emails_cadastrados()
_emails_base = [e.strip() for e in EMAIL_RECIPIENTS_BASE.split(",") if e.strip()]
_todos_emails = list(set(_emails_base + EMAIL_RECIPIENTS_ARQUIVO))
EMAIL_RECIPIENTS = ",".join(_todos_emails)

# Controle de canais
NOTIFICAR_TELEGRAM = os.getenv("NOTIFICAR_TELEGRAM", "true").lower() == "true"
NOTIFICAR_EMAIL = os.getenv("NOTIFICAR_EMAIL", "true").lower() == "true"

MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# Dados da deputada
DEPUTADA_ID = 220559
DEPUTADA_NOME = "Zanatta"
DEPUTADA_PARTIDO = "PL"
DEPUTADA_UF = "SC"

# Palavras-chave
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

def esta_em_recesso():
    agora = datetime.now(FUSO_BRASILIA)
    mes = agora.month
    dia = agora.day
    
    if mes == 12 and dia >= 23:
        return True
    if mes == 1:
        return True
    if mes == 7 and dia >= 18:
        return True
    return False


def get_data_retorno_sessao():
    agora = datetime.now(FUSO_BRASILIA)
    mes = agora.month
    
    if mes == 12 or mes == 1:
        ano = agora.year if mes == 12 else agora.year
        if mes == 12:
            ano += 1
        return f"02/02/{ano}"
    elif mes == 7:
        return f"01/08/{agora.year}"
    return "em breve"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalize_text(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto


def escapar_html(texto):
    if not texto:
        return ""
    return html.escape(str(texto))


def obter_data_hora_brasilia():
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
    except:
        pass
    return {"ultima_novidade": True}


def salvar_estado(teve_novidade):
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump({"ultima_novidade": teve_novidade}, f)
    except:
        pass


def carregar_historico():
    try:
        if HISTORICO_FILE.exists():
            with open(HISTORICO_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"notificadas": [], "ultima_limpeza": None}


def salvar_historico(historico):
    try:
        with open(HISTORICO_FILE, "w") as f:
            json.dump(historico, f, indent=2)
    except:
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
    except:
        pass
    return {"data": None, "tramitacoes": [], "por_categoria": {}}


def salvar_resumo_dia(resumo):
    try:
        with open(RESUMO_DIA_FILE, "w") as f:
            json.dump(resumo, f, indent=2)
    except:
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
# API DA CÂMARA
# ============================================================

def safe_get(url, params=None, timeout=30):
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except:
        return None


def fetch_eventos(start_date, end_date):
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
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    if not data:
        return []
    return data.get("dados", [])


def get_proposicao_id_from_item(item):
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
    cod = item.get("codProposicao") or item.get("idProposicao")
    if cod:
        return str(cod)
    return None


def fetch_proposicao_info(prop_id):
    data = safe_get(f"{BASE_URL}/proposicoes/{prop_id}")
    if not data:
        return None
    return data.get("dados", {})


def fetch_ids_autoria_deputada(id_deputada):
    ids = set()
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "ASC", "ordenarPor": "id"}
    print(f"   📋 Buscando proposições de autoria...")
    while True:
        data = safe_get(url, params=params)
        if not data:
            break
        for d in data.get("dados", []):
            if d.get("id"):
                ids.add(str(d["id"]))
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
    print(f"   ✅ {len(ids)} proposições de autoria")
    return ids


def verificar_relatoria_deputada(item):
    relator = item.get("relator") or {}
    nome = relator.get("nome") or ""
    if normalize_text(DEPUTADA_NOME) not in normalize_text(nome):
        return False
    partido = relator.get("siglaPartido") or ""
    if partido and normalize_text(DEPUTADA_PARTIDO) != normalize_text(partido):
        return False
    uf = relator.get("siglaUf") or ""
    if uf and normalize_text(DEPUTADA_UF) != normalize_text(uf):
        return False
    return True


def preparar_palavras_chave():
    palavras_norm = []
    for categoria, palavras in PALAVRAS_CHAVE.items():
        for palavra in palavras:
            if palavra.strip():
                palavras_norm.append((normalize_text(palavra), palavra, categoria))
    return palavras_norm


def buscar_palavras_no_item(item, palavras_normalizadas, prop_info=None):
    textos_busca = []
    textos_busca.append(item.get("titulo") or "")
    textos_busca.append(item.get("descricao") or "")
    if prop_info:
        textos_busca.append(prop_info.get("ementa") or "")
    texto_completo = normalize_text(" ".join(textos_busca))
    encontradas = []
    for palavra_norm, palavra_original, categoria in palavras_normalizadas:
        if palavra_norm in texto_completo:
            encontradas.append((palavra_original, categoria))
    return encontradas


# ============================================================
# FORMATAÇÃO DE MENSAGENS
# ============================================================

def formatar_mensagem_bom_dia():
    return """☀️ <b>Bom dia!</b>

Sou o <b>Monitor de Pautas</b>, sistema que busca matérias de interesse nas pautas das comissões.

📋 <b>O que monitoro:</b>
• Matérias de <b>autoria</b> da Dep. Júlia Zanatta
• Matérias onde ela é <b>relatora</b>
• Matérias com <b>palavras-chave</b> de interesse

Vamos acompanhar as pautas dos próximos 7 dias! 🔍"""


def formatar_mensagem_novidade(evento, item, prop_info, palavras_encontradas):
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
    
    if prop_info:
        sigla = prop_info.get("siglaTipo", "")
        numero = prop_info.get("numero", "")
        ano = prop_info.get("ano", "")
        ementa = escapar_html(prop_info.get("ementa", ""))
        prop_id = prop_info.get("id", "")
    else:
        sigla, numero, ano = "", "", ""
        ementa = escapar_html(item.get("titulo", ""))
        prop_id = None
    
    if len(ementa) > 250:
        ementa = ementa[:247] + "..."
    
    por_categoria = {}
    for palavra, categoria in palavras_encontradas:
        if categoria not in por_categoria:
            por_categoria[categoria] = []
        por_categoria[categoria].append(palavra)
    
    palavras_texto = []
    for cat, palavras in por_categoria.items():
        palavras_texto.append(f"<b>{cat}:</b> {', '.join(palavras)}")
    palavras_str = "\n".join(palavras_texto)
    
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}" if prop_id else ""
    link_texto = f'\n🔗 <a href="{link}">Ver tramitação</a>' if link else ""
    
    data_hora = obter_data_hora_brasilia()
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

🔑 <b>Palavra-chave na Pauta!</b>

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏛️ <b>Comissão:</b> {orgao}
📅 <b>Data:</b> {data_formatada}

🏷️ <b>Palavras encontradas:</b>
{palavras_str}{link_texto}

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_sem_novidades_completa():
    data_hora = obter_data_hora_brasilia()
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

Não foram encontradas matérias de interesse nas pautas.

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_sem_novidades_curta():
    data_hora = obter_data_hora_brasilia()
    return f"""📢 Sem novidades nas pautas.

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_recesso():
    data_hora = obter_data_hora_brasilia()
    data_retorno = get_data_retorno_sessao()
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

🏖️ <b>Recesso Parlamentar</b>

O Congresso está em recesso. Não há reuniões de comissões.

📅 <b>Previsão de retorno:</b> {data_retorno}

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_autoria(evento, prop_info):
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
    tramitacoes = resumo.get("tramitacoes", [])
    por_categoria = resumo.get("por_categoria", {})
    total = len(tramitacoes)
    data_hora = obter_data_hora_brasilia()
    
    if total == 0:
        return f"""📢 <b>Monitor Parlamentar Informa:</b>

🌙 <b>Resumo do Dia</b>

Não foram encontradas matérias de interesse nas pautas hoje.

⏰ <i>{data_hora}</i>"""
    
    detalhes = []
    for cat, itens in por_categoria.items():
        detalhes.append(f"<b>{cat}:</b> {len(itens)}")
    detalhes_str = "\n".join(detalhes)
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

🌙 <b>Resumo do Dia</b>

📊 <b>Total:</b> {total} matéria(s)

{detalhes_str}

⏰ <i>{data_hora}</i>"""


# ============================================================
# CONVERSÃO TELEGRAM HTML → EMAIL HTML
# ============================================================

def telegram_para_email_html(mensagem_telegram, assunto):
    corpo = mensagem_telegram.replace("\n", "<br>")
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #2d5016 0%, #4a7c23 100%); padding: 25px 30px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 600;">
                                🔑 Monitor de Pautas
                            </h1>
                            <p style="margin: 5px 0 0 0; color: #c8e6a5; font-size: 14px;">
                                Palavras-chave • Autoria • Relatoria
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; line-height: 1.6; color: #333333; font-size: 15px;">
                            {corpo}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 0 30px 25px 30px;">
                            <table role="presentation" style="width: 100%; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 8px; border-left: 4px solid #4caf50;">
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <p style="margin: 0 0 8px 0; color: #2e7d32; font-weight: 600; font-size: 14px;">
                                            📊 Acompanhe em tempo real
                                        </p>
                                        <p style="margin: 10px 0 0 0;">
                                            <a href="{LINK_PAINEL}" style="display: inline-block; background: #4caf50; color: white; padding: 8px 20px; border-radius: 5px; text-decoration: none; font-weight: 600; font-size: 13px;">
                                                🖥️ Abrir Painel
                                            </a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0; color: #6c757d; font-size: 12px; text-align: center;">
                                📧 Notificação automática do Monitor de Pautas<br>
                                <a href="{LINK_PAINEL}" style="color: #2d5a87;">monitorzanatta.streamlit.app</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def extrair_texto_plano(mensagem_telegram):
    texto = re.sub(r'<[^>]+>', '', mensagem_telegram)
    texto = texto.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return texto


# ============================================================
# ENVIO DE NOTIFICAÇÕES
# ============================================================

def enviar_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram: Credenciais faltando!")
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
        print("✅ Telegram: Mensagem enviada!")
        return True
    except Exception as e:
        print(f"❌ Telegram: Erro: {e}")
        return False


def enviar_email(mensagem_telegram, assunto):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENTS:
        print("⚠️ Email: Configuração incompleta")
        return False
    
    recipients = [e.strip() for e in EMAIL_RECIPIENTS.split(",") if e.strip()]
    if not recipients:
        print("⚠️ Email: Nenhum destinatário")
        return False
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"Monitor de Pautas <{EMAIL_SENDER}>"
    msg["To"] = ", ".join(recipients)
    
    texto_plano = extrair_texto_plano(mensagem_telegram)
    texto_plano += f"\n\n---\nAcesse o painel: {LINK_PAINEL}"
    msg.attach(MIMEText(texto_plano, "plain", "utf-8"))
    
    html_email = telegram_para_email_html(mensagem_telegram, assunto)
    msg.attach(MIMEText(html_email, "html", "utf-8"))
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        print(f"✅ Email: Enviado para {len(recipients)} destinatário(s)")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Email: Falha na autenticação")
        return False
    except Exception as e:
        print(f"❌ Email: Erro: {e}")
        return False


def notificar_telegram_apenas(mensagem):
    if NOTIFICAR_TELEGRAM:
        return enviar_telegram(mensagem)
    print("⏭️ Telegram: Desabilitado")
    return False


def notificar_ambos(mensagem, assunto):
    resultados = []
    if NOTIFICAR_TELEGRAM:
        resultados.append(enviar_telegram(mensagem))
    else:
        print("⏭️ Telegram: Desabilitado")
    if NOTIFICAR_EMAIL:
        resultados.append(enviar_email(mensagem, assunto))
    else:
        print("⏭️ Email: Desabilitado")
    return any(resultados)


# ============================================================
# FUNÇÕES DE EXECUÇÃO
# ============================================================

def executar_bom_dia():
    """Bom dia - APENAS TELEGRAM"""
    print("☀️ MODO: BOM DIA")
    
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO")
        return
    
    inicializar_resumo_dia()
    print("\n📤 Enviando bom dia (apenas Telegram)...")
    notificar_telegram_apenas(formatar_mensagem_bom_dia())
    print("✅ Bom dia enviado!")


def executar_resumo_dia():
    """Resumo - TELEGRAM + EMAIL"""
    print("🌙 MODO: RESUMO DO DIA")
    
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO")
        notificar_ambos(formatar_mensagem_recesso(), "🏖️ Monitor de Pautas - Recesso")
        return
    
    resumo = carregar_resumo_dia()
    print(f"📊 Tramitações: {len(resumo.get('tramitacoes', []))}")
    print("\n📤 Enviando resumo (Telegram + Email)...")
    notificar_ambos(formatar_mensagem_resumo_dia(resumo), "🌙 Monitor de Pautas - Resumo do Dia")
    print("✅ Resumo enviado!")


def executar_varredura():
    """Varredura - Email SÓ recebe se encontrar algo"""
    data_hora = obter_data_hora_brasilia()
    
    print("🔍 MODO: VARREDURA")
    print("=" * 60)
    print(f"📅 Data/Hora: {data_hora}")
    print()
    
    if esta_em_recesso():
        print("🏖️ Congresso em RECESSO - pulando varredura")
        return
    
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
    
    palavras_norm = preparar_palavras_chave()
    print(f"🔑 Palavras-chave: {len(palavras_norm)} termos")
    
    ids_autoria = fetch_ids_autoria_deputada(DEPUTADA_ID)
    
    start_date = agora
    end_date = agora + timedelta(days=7)
    
    print(f"\n📆 Buscando eventos de {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}...")
    eventos = fetch_eventos(start_date, end_date)
    print(f"✅ {len(eventos)} eventos encontrados")
    
    if not eventos:
        print("⚠️ Nenhum evento encontrado")
        print("\n📤 Enviando status (apenas Telegram)...")
        if ultima_teve_novidade:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_completa())
        else:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_curta())
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        return
    
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
        
        pauta = fetch_pauta_evento(evento_id)
        if not pauta:
            continue
        
        total_itens_pauta += len(pauta)
        
        for item in pauta:
            prop_id = get_proposicao_id_from_item(item)
            prop_info = None
            if prop_id:
                prop_info = fetch_proposicao_info(prop_id)
            
            is_autoria = prop_id and prop_id in ids_autoria
            is_relatoria = verificar_relatoria_deputada(item)
            palavras_encontradas = buscar_palavras_no_item(item, palavras_norm, prop_info)
            
            if not (is_autoria or is_relatoria or palavras_encontradas):
                continue
            
            if prop_info:
                sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
            else:
                sigla = item.get("titulo", "Item")[:30]
            
            chave_base = f"{evento_id}_{prop_id or 'sem_id'}"
            
            if is_autoria:
                chave_autoria = f"autoria_{chave_base}"
                if ja_foi_notificada(historico, "autoria", chave_autoria):
                    itens_ja_notificados += 1
                else:
                    print(f"   📝 AUTORIA: {sigla} em {orgao}")
                    itens_autoria.append({
                        "evento": evento, "item": item, "prop_info": prop_info,
                        "prop_id": prop_id, "sigla": sigla, "chave": chave_autoria
                    })
            
            if is_relatoria:
                chave_relatoria = f"relatoria_{chave_base}"
                if ja_foi_notificada(historico, "relatoria", chave_relatoria):
                    itens_ja_notificados += 1
                else:
                    print(f"   📋 RELATORIA: {sigla} em {orgao}")
                    itens_relatoria.append({
                        "evento": evento, "item": item, "prop_info": prop_info,
                        "prop_id": prop_id, "sigla": sigla, "chave": chave_relatoria
                    })
            
            if palavras_encontradas:
                chave_palavras = f"palavras_{chave_base}"
                if ja_foi_notificada(historico, "palavras", chave_palavras):
                    itens_ja_notificados += 1
                else:
                    categoria_principal = palavras_encontradas[0][1]
                    print(f"   🔑 PALAVRAS: {sigla} em {orgao}")
                    itens_palavras_chave.append({
                        "evento": evento, "item": item, "prop_info": prop_info,
                        "prop_id": prop_id, "palavras": palavras_encontradas,
                        "sigla": sigla, "categoria": categoria_principal,
                        "chave": chave_palavras
                    })
        
        time.sleep(0.1)
    
    # ====== PARTE 2: MOVIMENTAÇÕES NO SENADO ======
    print("\n🔵 Verificando movimentações no Senado...")
    itens_senado = []
    
    proposicoes_senado = buscar_proposicoes_no_senado(ids_autoria)
    
    for prop_data in proposicoes_senado:
        sigla = f"{prop_data['tipo']} {prop_data['numero']}/{prop_data['ano']}"
        chave_senado = f"senado_{prop_data['prop_id']}_{prop_data['movimentacao'].get('data', '')[:10]}"
        
        if ja_foi_notificada(historico, "senado", chave_senado):
            itens_ja_notificados += 1
        else:
            print(f"   🔵 SENADO: {sigla}")
            itens_senado.append({
                "prop_data": prop_data,
                "sigla": sigla,
                "chave": chave_senado
            })
    
    total_novos = len(itens_autoria) + len(itens_relatoria) + len(itens_palavras_chave) + len(itens_senado)
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Eventos: {len(eventos)}")
    print(f"   Itens de pauta: {total_itens_pauta}")
    print(f"   AUTORIA: {len(itens_autoria)}")
    print(f"   RELATORIA: {len(itens_relatoria)}")
    print(f"   PALAVRAS-CHAVE: {len(itens_palavras_chave)}")
    print(f"   🔵 SENADO: {len(itens_senado)}")
    print(f"   Já notificados: {itens_ja_notificados}")
    print(f"{'=' * 60}")
    
    enviadas = 0
    
    # AUTORIA - Telegram + Email
    if itens_autoria:
        print(f"\n📤 Enviando {len(itens_autoria)} de AUTORIA (Telegram + Email)...\n")
        for item_data in itens_autoria:
            mensagem = formatar_mensagem_autoria(item_data["evento"], item_data["prop_info"] or {})
            if notificar_ambos(mensagem, f"📝 Autoria na Pauta: {item_data['sigla']}"):
                historico = registrar_notificacao(historico, "autoria", item_data["chave"], item_data["sigla"], "Autoria")
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], "Autoria")
                enviadas += 1
            time.sleep(1)
    
    # RELATORIA - Telegram + Email
    if itens_relatoria:
        print(f"\n📤 Enviando {len(itens_relatoria)} de RELATORIA (Telegram + Email)...\n")
        for item_data in itens_relatoria:
            mensagem = formatar_mensagem_relatoria(item_data["evento"], item_data["prop_info"] or {})
            if notificar_ambos(mensagem, f"📋 Relatoria na Pauta: {item_data['sigla']}"):
                historico = registrar_notificacao(historico, "relatoria", item_data["chave"], item_data["sigla"], "Relatoria")
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], "Relatoria")
                enviadas += 1
            time.sleep(1)
    
    # PALAVRAS-CHAVE - Telegram + Email
    if itens_palavras_chave:
        print(f"\n📤 Enviando {len(itens_palavras_chave)} de PALAVRAS-CHAVE (Telegram + Email)...\n")
        for item_data in itens_palavras_chave:
            mensagem = formatar_mensagem_novidade(item_data["evento"], item_data["item"], item_data["prop_info"], item_data["palavras"])
            if notificar_ambos(mensagem, f"🔑 Palavra-chave: {item_data['sigla']}"):
                historico = registrar_notificacao(historico, "palavras", item_data["chave"], item_data["sigla"], item_data["categoria"])
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], item_data["categoria"])
                enviadas += 1
            time.sleep(1)
    
    # SENADO - Telegram + Email
    if itens_senado:
        print(f"\n📤 Enviando {len(itens_senado)} do SENADO (Telegram + Email)...\n")
        for item_data in itens_senado:
            mensagem = formatar_mensagem_senado(item_data["prop_data"])
            if notificar_ambos(mensagem, f"🔵 ZANATTA NO SENADO: {item_data['sigla']}"):
                historico = registrar_notificacao(historico, "senado", item_data["chave"], item_data["sigla"], "Senado")
                resumo = adicionar_ao_resumo(resumo, item_data["sigla"], "Senado")
                enviadas += 1
            time.sleep(1)
    
    # Se não teve nenhuma novidade - APENAS Telegram
    if total_novos == 0:
        print("\n📤 Enviando status (apenas Telegram)...")
        if ultima_teve_novidade:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_completa())
        else:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_curta())
    
    salvar_estado(total_novos > 0)
    salvar_historico(historico)
    salvar_resumo_dia(resumo)
    
    print(f"\n✅ {enviadas} mensagens enviadas!")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🔑 MONITOR DE PAUTAS v7")
    print("    Autoria + Relatoria + Palavras-chave")
    print("    📍 Câmara + 🔵 Senado")
    print("=" * 60)
    print()
    
    print("📡 CANAIS DE NOTIFICAÇÃO:")
    
    if NOTIFICAR_TELEGRAM:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            print(f"   ✅ Telegram: Habilitado")
        else:
            print("   ⚠️ Telegram: Credenciais faltando!")
    else:
        print("   ⏭️ Telegram: Desabilitado")
    
    if NOTIFICAR_EMAIL:
        if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENTS:
            recipients = EMAIL_RECIPIENTS.split(",")
            print(f"   ✅ Email: Habilitado ({len(recipients)} destinatário(s))")
        else:
            print("   ⚠️ Email: Configuração incompleta!")
    else:
        print("   ⏭️ Email: Desabilitado")
    
    print(f"\n📋 Modo: {MODO_EXECUCAO}")
    print()
    
    if MODO_EXECUCAO == "bom_dia":
        executar_bom_dia()
    elif MODO_EXECUCAO == "resumo":
        executar_resumo_dia()
    else:
        executar_varredura()


if __name__ == "__main__":
    main()