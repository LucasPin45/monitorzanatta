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
# FUNÇÕES - API SENADO
# ============================================================

def verificar_se_foi_para_senado(situacao_atual: str, despacho: str = "") -> bool:
    """
    Verifica se a proposição está em apreciação pelo Senado Federal.
    """
    texto_completo = f"{situacao_atual} {despacho}".lower()
    
    indicadores = [
        "apreciação pelo senado federal",
        "apreciacao pelo senado federal",
        "apreciação pelo senado",
        "apreciacao pelo senado",
        "aguardando apreciação pelo senado",
        "aguardando apreciacao pelo senado",
        "para apreciação do senado",
        "para apreciacao do senado",
        "remetida ao senado federal",
        "remetido ao senado federal",
        "remessa ao senado federal",
        "enviada ao senado federal",
        "enviado ao senado federal",
        "encaminhada ao senado federal",
        "encaminhado ao senado federal",
        "tramitando no senado",
        "em tramitação no senado",
        "tramitação no senado",
        "à mesa do senado",
        "ao senado federal",
        "ofício de remessa ao senado",
        "sgm-p",
    ]
    
    return any(indicador in texto_completo for indicador in indicadores)


def buscar_situacao_camara(proposicao_id):
    """Busca a situação atual da proposição na Câmara."""
    url = f"{BASE_URL}/proposicoes/{proposicao_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        dados = data.get("dados", {})
        status = dados.get("statusProposicao", {})
        return {
            "situacao": status.get("descricaoSituacao", ""),
            "despacho": status.get("despacho", ""),
            "orgao": status.get("siglaOrgao", "")
        }
    except Exception:
        return {"situacao": "", "despacho": "", "orgao": ""}


def buscar_dados_senado(tipo: str, numero: str, ano: str):
    """
    Busca dados básicos de uma proposição no Senado.
    Retorna dict com código da matéria, id do processo, situação, url.
    """
    tipo_norm = (tipo or "").strip().upper()
    numero_norm = (numero or "").strip()
    ano_norm = (ano or "").strip()
    
    if not (tipo_norm and numero_norm and ano_norm):
        return None
    
    url = f"{SENADO_BASE_URL}/processo?sigla={tipo_norm}&numero={numero_norm}&ano={ano_norm}&v=1"
    
    try:
        resp = requests.get(url, headers=HEADERS_SENADO, timeout=20)
        
        if resp.status_code == 404:
            return None
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        
        if not data:
            return None
        
        itens = data if isinstance(data, list) else [data]
        
        identificacao_alvo = f"{tipo_norm} {numero_norm}/{ano_norm}"
        escolhido = None
        for it in itens:
            ident = (it.get("identificacao") or "").strip()
            if ident.upper() == identificacao_alvo.upper():
                escolhido = it
                break
        if escolhido is None:
            escolhido = itens[0]
        
        codigo_materia = str(escolhido.get("codigoMateria") or "").strip()
        id_processo = str(escolhido.get("id") or "").strip()
        
        if not codigo_materia:
            return None
        
        url_deep = f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo_materia}"
        
        return {
            "codigo_materia": codigo_materia,
            "id_processo": id_processo,
            "url_senado": url_deep,
        }
    
    except Exception as e:
        print(f"   ⚠️ Erro ao consultar Senado: {e}")
        return None


def buscar_movimentacoes_senado(id_processo: str, limite: int = 10):
    """
    Busca movimentações de uma proposição no Senado.
    Retorna lista de movimentações ordenadas por data (mais recente primeiro).
    """
    if not id_processo:
        return []
    
    url = f"{SENADO_BASE_URL}/processo/{id_processo}/movimentacoes?v=1"
    
    try:
        resp = requests.get(url, headers=HEADERS_SENADO, timeout=20)
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        
        if not data:
            return []
        
        movimentacoes = data if isinstance(data, list) else [data]
        
        # Ordenar por data (mais recente primeiro)
        def parse_data(mov):
            data_str = mov.get("data") or mov.get("dataMovimento") or ""
            try:
                return datetime.fromisoformat(data_str.replace("Z", ""))
            except:
                return datetime.min
        
        movimentacoes_ordenadas = sorted(movimentacoes, key=parse_data, reverse=True)
        
        return movimentacoes_ordenadas[:limite]
    
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar movimentações Senado: {e}")
        return []


def tramitacao_senado_recente(movimentacao: dict, horas: int = 48) -> bool:
    """Verifica se uma movimentação do Senado é recente."""
    if not movimentacao:
        return False
    
    data_str = movimentacao.get("data") or movimentacao.get("dataMovimento") or ""
    
    if not data_str:
        return False
    
    try:
        # Tentar diferentes formatos
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                data_mov = datetime.strptime(data_str[:19], fmt)
                break
            except:
                continue
        else:
            data_mov = datetime.strptime(data_str[:10], "%Y-%m-%d")
        
        agora = datetime.now()
        diferenca = agora - data_mov
        return diferenca.total_seconds() <= (horas * 3600)
    
    except Exception:
        return False


def buscar_proposicoes_no_senado(ids_autoria):
    """
    Busca proposições da deputada que estão no Senado e têm movimentações recentes.
    Retorna lista de dicts com dados da proposição e movimentação.
    """
    proposicoes_senado = []
    
    for prop_id in ids_autoria:
        try:
            # Buscar informações da proposição
            prop_info = fetch_proposicao_info(prop_id)
            if not prop_info:
                continue
            
            # Verificar se está no Senado
            situacao_camara = buscar_situacao_camara(prop_id)
            if not verificar_se_foi_para_senado(
                situacao_camara.get("situacao", ""), 
                situacao_camara.get("despacho", "")
            ):
                continue
            
            # Buscar dados do Senado
            dados_senado = buscar_dados_senado(
                prop_info.get("siglaTipo", ""),
                str(prop_info.get("numero", "")),
                str(prop_info.get("ano", ""))
            )
            
            if not dados_senado or not dados_senado.get("id_processo"):
                continue
            
            # Buscar movimentações do Senado
            movimentacoes = buscar_movimentacoes_senado(dados_senado["id_processo"], limite=5)
            
            # Verificar se há movimentações recentes
            for mov in movimentacoes:
                if tramitacao_senado_recente(mov, horas=48):
                    proposicoes_senado.append({
                        "prop_id": prop_id,
                        "tipo": prop_info.get("siglaTipo", ""),
                        "numero": prop_info.get("numero", ""),
                        "ano": prop_info.get("ano", ""),
                        "movimentacao": mov,
                        "dados_senado": dados_senado,
                        "prop_info": prop_info
                    })
                    break  # Só adiciona a movimentação mais recente
            
            time.sleep(0.15)
        
        except Exception as e:
            print(f"   ⚠️ Erro ao processar proposição {prop_id}: {e}")
            continue
    
    return proposicoes_senado


# ============================================================
# FORMATAÇÃO DE MENSAGENS
# ============================================================

def formatar_mensagem_bom_dia():
    return """☀️ <b>Bom dia!</b>

Sou o <b>Monitor de Pautas</b>, sistema que busca matérias de interesse nas pautas das comissões.

🔍 <b>O que monitoro:</b>
• 📝 Projetos de <b>autoria</b> da deputada
• 📋 Projetos com <b>relatoria</b> da deputada
• 🔑 Matérias com <b>palavras-chave</b>
• 🔵 Tramitações no <b>Senado</b>

Ao longo do dia, enviarei notificações a cada novidade encontrada.

Boa semana! 🚀"""


def formatar_mensagem_recesso():
    data_retorno = get_data_retorno_sessao()
    return f"""🏖️ <b>Congresso em Recesso</b>

O Congresso Nacional está em recesso parlamentar.

📅 <b>Retorno previsto:</b> {data_retorno}

Durante o recesso, não há atividades de plenário e comissões, portanto não há pautas para monitorar.

O monitoramento será retomado automaticamente quando as sessões voltarem. 🇧🇷"""


def formatar_mensagem_sem_novidades_completa():
    return """✅ <b>Tudo tranquilo por aqui!</b>

Fiz uma varredura nas pautas das próximas sessões e não encontrei:
• Novos projetos de autoria
• Novos projetos com relatoria
• Novas matérias com palavras-chave
• Novas movimentações no Senado

Continuo monitorando e aviso assim que aparecer algo! 👀"""


def formatar_mensagem_sem_novidades_curta():
    return "✅ Sem novidades no momento."


def formatar_mensagem_resumo_dia(resumo):
    tramitacoes = resumo.get("tramitacoes", [])
    por_categoria = resumo.get("por_categoria", {})
    
    if not tramitacoes:
        return """🌙 <b>Resumo do Dia</b>

Hoje não foram identificadas novas matérias nas pautas monitoradas.

Continue acompanhando pelo painel: """ + LINK_PAINEL
    
    texto = "🌙 <b>Resumo do Dia</b>\n\n"
    texto += f"📊 <b>{len(tramitacoes)} matéria(s) identificada(s) hoje:</b>\n\n"
    
    for categoria, itens in sorted(por_categoria.items()):
        texto += f"<b>{categoria}</b>\n"
        for sigla in sorted(itens):
            texto += f"  • {sigla}\n"
        texto += "\n"
    
    texto += f"\n📊 Acompanhe em tempo real: {LINK_PAINEL}"
    return texto


def formatar_mensagem_novidade(evento, item, prop_info, palavras_encontradas):
    evento_data = evento.get("dataHoraInicio", "")[:10]
    evento_data_br = ""
    if evento_data:
        try:
            dt = datetime.strptime(evento_data, "%Y-%m-%d")
            evento_data_br = dt.strftime("%d/%m/%Y")
        except:
            evento_data_br = evento_data
    
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "Comissão")
    descricao_evento = evento.get("descricao", "Sessão")
    
    if prop_info:
        sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
        ementa = prop_info.get("ementa", "")[:300]
        url_prop = prop_info.get("uri", "")
        autor = prop_info.get("uriAutores", "")
    else:
        sigla = item.get("titulo", "Item")[:50]
        ementa = item.get("descricao", "")[:300]
        url_prop = ""
        autor = ""
    
    categorias = list(set([cat for _, cat in palavras_encontradas]))
    palavras_lista = ", ".join([palavra for palavra, _ in palavras_encontradas[:5]])
    
    texto = f"""🔑 <b>PALAVRA-CHAVE NA PAUTA</b>

📄 <b>{escapar_html(sigla)}</b>

📋 <b>Categorias:</b> {escapar_html(', '.join(categorias))}
🔎 <b>Termos:</b> {escapar_html(palavras_lista)}

📅 <b>Sessão:</b> {escapar_html(evento_data_br)}
🏛️ <b>Órgão:</b> {escapar_html(orgao)}
📌 <b>Evento:</b> {escapar_html(descricao_evento)}

📝 <b>Ementa:</b> {escapar_html(ementa)}"""
    
    if url_prop:
        texto += f"\n\n🔗 <a href='{url_prop}'>Ver proposição</a>"
    
    return texto


def formatar_mensagem_autoria(evento, prop_info):
    evento_data = evento.get("dataHoraInicio", "")[:10]
    evento_data_br = ""
    if evento_data:
        try:
            dt = datetime.strptime(evento_data, "%Y-%m-%d")
            evento_data_br = dt.strftime("%d/%m/%Y")
        except:
            evento_data_br = evento_data
    
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "Comissão")
    descricao_evento = evento.get("descricao", "Sessão")
    
    sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
    ementa = prop_info.get("ementa", "")[:300]
    url_prop = prop_info.get("uri", "")
    
    texto = f"""📝 <b>AUTORIA NA PAUTA</b>

📄 <b>{escapar_html(sigla)}</b>

📅 <b>Sessão:</b> {escapar_html(evento_data_br)}
🏛️ <b>Órgão:</b> {escapar_html(orgao)}
📌 <b>Evento:</b> {escapar_html(descricao_evento)}

📝 <b>Ementa:</b> {escapar_html(ementa)}"""
    
    if url_prop:
        texto += f"\n\n🔗 <a href='{url_prop}'>Ver proposição</a>"
    
    return texto


def formatar_mensagem_relatoria(evento, prop_info):
    evento_data = evento.get("dataHoraInicio", "")[:10]
    evento_data_br = ""
    if evento_data:
        try:
            dt = datetime.strptime(evento_data, "%Y-%m-%d")
            evento_data_br = dt.strftime("%d/%m/%Y")
        except:
            evento_data_br = evento_data
    
    orgao = evento.get("orgaos", [{}])[0].get("sigla", "Comissão")
    descricao_evento = evento.get("descricao", "Sessão")
    
    sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
    ementa = prop_info.get("ementa", "")[:300]
    url_prop = prop_info.get("uri", "")
    
    texto = f"""📋 <b>RELATORIA NA PAUTA</b>

📄 <b>{escapar_html(sigla)}</b>

📅 <b>Sessão:</b> {escapar_html(evento_data_br)}
🏛️ <b>Órgão:</b> {escapar_html(orgao)}
📌 <b>Evento:</b> {escapar_html(descricao_evento)}

📝 <b>Ementa:</b> {escapar_html(ementa)}"""
    
    if url_prop:
        texto += f"\n\n🔗 <a href='{url_prop}'>Ver proposição</a>"
    
    return texto


def formatar_mensagem_senado(prop_data):
    """Formata mensagem para movimentação no Senado."""
    prop_info = prop_data.get("prop_info", {})
    movimentacao = prop_data.get("movimentacao", {})
    dados_senado = prop_data.get("dados_senado", {})
    
    sigla = f"{prop_info.get('siglaTipo', '')} {prop_info.get('numero', '')}/{prop_info.get('ano', '')}"
    ementa = prop_info.get("ementa", "")[:300]
    
    data_mov = movimentacao.get("data") or movimentacao.get("dataMovimento") or ""
    data_mov_br = ""
    if data_mov:
        try:
            dt = datetime.fromisoformat(data_mov.replace("Z", ""))
            data_mov_br = dt.strftime("%d/%m/%Y")
        except:
            data_mov_br = data_mov[:10]
    
    descricao_mov = movimentacao.get("descricao") or movimentacao.get("texto") or "Movimentação"
    url_senado = dados_senado.get("url_senado", "")
    
    texto = f"""🔵 <b>ZANATTA NO SENADO</b>

📄 <b>{escapar_html(sigla)}</b>

📅 <b>Data:</b> {escapar_html(data_mov_br)}
📝 <b>Movimentação:</b> {escapar_html(descricao_mov[:200])}

💡 <b>Ementa:</b> {escapar_html(ementa)}"""
    
    if url_senado:
        texto += f"\n\n🔗 <a href='{url_senado}'>Ver no Senado</a>"
    
    return texto


def telegram_para_email_html(mensagem_telegram, assunto):
    corpo = mensagem_telegram.replace("\n", "<br>")
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{assunto}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" style="width: 600px; max-width: 100%; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px;">
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
