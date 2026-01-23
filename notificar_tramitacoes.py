#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_tramitacoes.py
========================================
Monitor de tramitações da Deputada Júlia Zanatta
Verifica novas movimentações e notifica via Telegram + Email

v6: 
- INTEGRAÇÃO COM SENADO
- Quando projeto está no Senado: 🔵 ZANATTA NO SENADO
- Busca tramitações tanto da Câmara quanto do Senado
- Lógica diferenciada Telegram vs Email
- Email só recebe: tramitações encontradas + resumo do dia
- Telegram recebe tudo (bom dia, sem novidades, tramitações, resumo)
- Link do painel nos emails
"""

import os
import sys
import json
import html
import requests
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================

# APIs
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_BASE_URL = "https://legis.senado.leg.br/dadosabertos"
HEADERS = {"User-Agent": "MonitorZanatta/24.0 (gabinete-julia-zanatta)"}
HEADERS_SENADO = {"User-Agent": "MonitorZanatta/24.0", "Accept": "application/json"}

DEPUTADA_ID = 220559  # Júlia Zanatta

# Link do painel
LINK_PAINEL = "https://monitorzanatta.streamlit.app/"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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
EMAIL_RECIPIENTS_BASE = os.getenv("EMAIL_RECIPIENTS", "")
EMAIL_RECIPIENTS_ARQUIVO = carregar_emails_cadastrados()
_emails_base = [e.strip() for e in EMAIL_RECIPIENTS_BASE.split(",") if e.strip()]
_todos_emails = list(set(_emails_base + EMAIL_RECIPIENTS_ARQUIVO))  # Remove duplicatas
EMAIL_RECIPIENTS = ",".join(_todos_emails)

# Controle de canais habilitados
NOTIFICAR_TELEGRAM = os.getenv("NOTIFICAR_TELEGRAM", "true").lower() == "true"
NOTIFICAR_EMAIL = os.getenv("NOTIFICAR_EMAIL", "true").lower() == "true"

# Modo de execução (bom_dia, varredura, resumo)
MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# Tipos de proposição a monitorar
TIPOS_MONITORADOS = ["PL", "PLP", "PDL", "PEC", "RIC", "REQ", "PRL"]
DATA_INICIO_MANDATO = "2023-02-01"

# Arquivos de estado
ESTADO_FILE = Path("estado_monitor.json")
HISTORICO_FILE = Path("historico_notificacoes.json")
RESUMO_DIA_FILE = Path("resumo_dia.json")
DIAS_MANTER_HISTORICO = 7
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# ============================================================
# GERENCIAMENTO DE ESTADO
# ============================================================

def carregar_estado():
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
    estado = {"ultima_novidade": teve_novidade}
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump(estado, f)
        print(f"💾 Estado salvo: {estado}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar estado: {e}")


def carregar_historico():
    try:
        if HISTORICO_FILE.exists():
            with open(HISTORICO_FILE, "r") as f:
                historico = json.load(f)
                print(f"📂 Histórico carregado: {len(historico.get('notificadas', []))} tramitações")
                return historico
    except Exception as e:
        print(f"⚠️ Erro ao carregar histórico: {e}")
    return {"notificadas": [], "ultima_limpeza": None}


def salvar_historico(historico):
    try:
        with open(HISTORICO_FILE, "w") as f:
            json.dump(historico, f, indent=2)
        print(f"💾 Histórico salvo: {len(historico.get('notificadas', []))} tramitações")
    except Exception as e:
        print(f"⚠️ Erro ao salvar histórico: {e}")


def limpar_historico_antigo(historico):
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


def gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao, origem="camara"):
    data_normalizada = str(data_hora_tramitacao)[:19] if data_hora_tramitacao else "sem_data"
    return f"{origem}_{proposicao_id}_{data_normalizada}"


def ja_foi_notificada(historico, proposicao_id, data_hora_tramitacao, origem="camara"):
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao, origem)
    for item in historico.get("notificadas", []):
        if item.get("chave") == chave:
            return True
    return False


def registrar_notificacao(historico, proposicao_id, data_hora_tramitacao, sigla_proposicao, origem="camara"):
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao, origem)
    agora = datetime.now(FUSO_BRASILIA).isoformat()
    historico["notificadas"].append({
        "chave": chave,
        "proposicao_id": proposicao_id,
        "sigla": sigla_proposicao,
        "data_tramitacao": str(data_hora_tramitacao)[:19] if data_hora_tramitacao else None,
        "registrado_em": agora,
        "origem": origem
    })
    return historico


# ============================================================
# GERENCIAMENTO DO RESUMO DO DIA
# ============================================================

def carregar_resumo_dia():
    try:
        if RESUMO_DIA_FILE.exists():
            with open(RESUMO_DIA_FILE, "r") as f:
                resumo = json.load(f)
                print(f"📂 Resumo do dia: {len(resumo.get('tramitacoes', []))} tramitações")
                return resumo
    except Exception as e:
        print(f"⚠️ Erro ao carregar resumo: {e}")
    return {"data": None, "tramitacoes": []}


def salvar_resumo_dia(resumo):
    try:
        with open(RESUMO_DIA_FILE, "w") as f:
            json.dump(resumo, f, indent=2)
        print(f"💾 Resumo salvo: {len(resumo.get('tramitacoes', []))} tramitações")
    except Exception as e:
        print(f"⚠️ Erro ao salvar resumo: {e}")


def inicializar_resumo_dia():
    agora = datetime.now(FUSO_BRASILIA)
    resumo = {"data": agora.strftime("%Y-%m-%d"), "tramitacoes": []}
    salvar_resumo_dia(resumo)
    return resumo


def adicionar_ao_resumo(resumo, sigla_proposicao, no_senado=False):
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": []}
    
    # Adiciona marcador se for do Senado
    sigla_com_origem = f"🔵 {sigla_proposicao}" if no_senado else sigla_proposicao
    
    if sigla_com_origem not in resumo["tramitacoes"]:
        resumo["tramitacoes"].append(sigla_com_origem)
    return resumo


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar_html(texto):
    if not texto:
        return ""
    return html.escape(str(texto))


def obter_data_hora_brasilia():
    agora_utc = datetime.now(timezone.utc)
    agora_brasilia = agora_utc.astimezone(FUSO_BRASILIA)
    return agora_brasilia.strftime("%d/%m/%Y às %H:%M")


# ============================================================
# FUNÇÕES - VERIFICAÇÃO SENADO
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


# ============================================================
# FUNÇÕES - API SENADO
# ============================================================

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


def buscar_status_senado(id_processo: str):
    """
    Busca situação atual e órgão no Senado via /processo/{id}.
    """
    if not id_processo:
        return {"situacao": "", "orgao": ""}
    
    url = f"{SENADO_BASE_URL}/processo/{id_processo}?v=1"
    
    try:
        resp = requests.get(url, headers=HEADERS_SENADO, timeout=20)
        
        if resp.status_code != 200:
            return {"situacao": "", "orgao": ""}
        
        proc = resp.json()
        
        if isinstance(proc, dict):
            autuacoes = proc.get("autuacoes") or []
            if autuacoes and isinstance(autuacoes, list):
                a0 = autuacoes[0] or {}
                orgao = (a0.get("siglaColegiadoControleAtual") or "").strip()
                
                situacoes = a0.get("situacoes") or []
                situacao = ""
                if isinstance(situacoes, list) and situacoes:
                    ativa = None
                    for s in reversed(situacoes):
                        if not s.get("fim"):
                            ativa = s
                            break
                    if not ativa:
                        ativa = situacoes[-1]
                    situacao = (ativa.get("descricao") or "").strip()
                
                return {"situacao": situacao, "orgao": orgao}
        
        return {"situacao": "", "orgao": ""}
    
    except Exception:
        return {"situacao": "", "orgao": ""}


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


# ============================================================
# FUNÇÕES - API CÂMARA
# ============================================================

def buscar_proposicoes_por_tipo(deputado_id, sigla_tipo):
    proposicoes = []
    pagina = 1
    
    while True:
        url = f"{BASE_URL}/proposicoes"
        params = {
            "idDeputadoAutor": deputado_id,
            "siglaTipo": sigla_tipo,
            "dataInicio": DATA_INICIO_MANDATO,
            "ordem": "DESC",
            "ordenarPor": "id",
            "pagina": pagina,
            "itens": 100
        }
        
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("dados"):
                break
            proposicoes.extend(data["dados"])
            
            links = data.get("links", [])
            if not any(link.get("rel") == "next" for link in links):
                break
            pagina += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"   ⚠️ Erro ao buscar {sigla_tipo}: {e}")
            break
    
    return proposicoes


def buscar_todas_proposicoes(deputado_id):
    print(f"🔍 Buscando proposições: {', '.join(TIPOS_MONITORADOS)}")
    print(f"📅 Período: desde {DATA_INICIO_MANDATO}")
    print()
    
    todas_proposicoes = []
    for tipo in TIPOS_MONITORADOS:
        props = buscar_proposicoes_por_tipo(deputado_id, tipo)
        print(f"   {tipo}: {len(props)} proposições")
        todas_proposicoes.extend(props)
        time.sleep(0.3)
    
    print(f"\n✅ Total: {len(todas_proposicoes)} proposições")
    return todas_proposicoes


def buscar_ultima_tramitacao(proposicao_id):
    url = f"{BASE_URL}/proposicoes/{proposicao_id}/tramitacoes"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        tramitacoes = data.get("dados", [])
        if tramitacoes:
            tramitacoes_ordenadas = sorted(tramitacoes, key=lambda x: x.get("dataHora", ""), reverse=True)
            return tramitacoes_ordenadas[0]
    except Exception:
        pass
    return None


def tramitacao_recente(tramitacao, horas=48):
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
# FORMATAÇÃO DE MENSAGENS (Telegram HTML)
# ============================================================

def formatar_mensagem_novidade(proposicao, tramitacao):
    """Formata mensagem de tramitação da CÂMARA."""
    sigla = proposicao.get("siglaTipo", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = escapar_html(proposicao.get("ementa", ""))
    if len(ementa) > 200:
        ementa = ementa[:197] + "..."
    
    data_tram = tramitacao.get("dataHora", "")
    if data_tram:
        try:
            dt = datetime.fromisoformat(data_tram.replace("Z", ""))
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = data_tram[:10]
    else:
        data_formatada = "Data não disponível"
    
    descricao_raw = tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
    descricao = escapar_html(descricao_raw)
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={proposicao['id']}"
    data_hora_varredura = obter_data_hora_brasilia()
    
    return f"""📢 <b>Monitor Parlamentar Informa:</b>

Houve nova movimentação!

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

📅 {data_formatada} → {descricao}

🔗 <a href="{link}">Ver tramitação completa</a>

⏰ <i>Varredura: {data_hora_varredura}</i>"""


def formatar_mensagem_novidade_senado(proposicao, movimentacao, dados_senado, status_senado):
    """Formata mensagem de tramitação do SENADO com 🔵 ZANATTA NO SENADO."""
    sigla = proposicao.get("siglaTipo", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    ementa = escapar_html(proposicao.get("ementa", ""))
    if len(ementa) > 200:
        ementa = ementa[:197] + "..."
    
    # Data da movimentação
    data_mov = movimentacao.get("data") or movimentacao.get("dataMovimento") or ""
    if data_mov:
        try:
            dt = datetime.fromisoformat(data_mov.replace("Z", ""))
            data_formatada = dt.strftime("%d/%m/%Y %H:%M")
        except:
            data_formatada = data_mov[:10]
    else:
        data_formatada = "Data não disponível"
    
    # Descrição da movimentação
    descricao_raw = (
        movimentacao.get("descricao") or 
        movimentacao.get("textoMovimento") or 
        movimentacao.get("texto") or 
        "Movimentação registrada"
    )
    descricao = escapar_html(descricao_raw)
    if len(descricao) > 300:
        descricao = descricao[:297] + "..."
    
    # Órgão atual no Senado
    orgao = status_senado.get("orgao", "") or "—"
    situacao = status_senado.get("situacao", "") or "Em tramitação"
    
    # Link do Senado
    link_senado = dados_senado.get("url_senado", "")
    link_camara = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={proposicao['id']}"
    
    data_hora_varredura = obter_data_hora_brasilia()
    
    return f"""🔵 <b>ZANATTA NO SENADO</b>

📢 <b>Monitor Parlamentar Informa:</b>

Houve nova movimentação no <b>Senado Federal</b>!

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

🏛️ <b>Órgão:</b> {orgao}
📋 <b>Situação:</b> {situacao}

📅 {data_formatada}
➡️ {descricao}

🔗 <a href="{link_senado}">Tramitação no Senado</a>
🔗 <a href="{link_camara}">Tramitação na Câmara</a>

⏰ <i>Varredura: {data_hora_varredura}</i>"""


def formatar_mensagem_sem_novidades_completa():
    data_hora = obter_data_hora_brasilia()
    return f"""🔍 <b>Monitor Parlamentar Informa:</b>

Na última varredura não foram encontradas tramitações recentes em matérias da Dep. Júlia Zanatta (Câmara e Senado).

Mas continue atento! 👀

⏰ <i>Varredura: {data_hora}</i>"""


def formatar_mensagem_sem_novidades_curta():
    data_hora = obter_data_hora_brasilia()
    return f"""🔍 Ainda sem novidades em matérias da Dep. Júlia Zanatta.

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_bom_dia():
    return """☀️ <b>Bom dia!</b>

Sou <b>MoniParBot</b>, o Robô do Monitor Parlamentar, sistema criado para monitorar as matérias legislativas de autoria da Deputada Júlia Zanatta, a Deputada pronta para combate! 💪

Ao longo do dia, faremos uma varredura de 2 em 2h para identificar movimentações nas matérias da Deputada - tanto na <b>Câmara</b> quanto no <b>Senado</b> 🔵

Quando encontrada, será notificada. Quando não encontrada, será avisado que não foi encontrada.

Até daqui a pouco! 🔍"""


def formatar_mensagem_resumo_dia(tramitacoes):
    quantidade = len(tramitacoes)
    
    # Contar quantas são do Senado
    senado_count = sum(1 for t in tramitacoes if t.startswith("🔵"))
    
    if quantidade == 0:
        return """🌙 <b>Resumo do dia:</b>

Hoje não foram identificadas tramitações em matérias da Dep. Júlia Zanatta.

Até amanhã! 👋"""
    
    elif quantidade == 1:
        lista = f"• {tramitacoes[0]}"
        extra = " (no Senado)" if senado_count == 1 else ""
        return f"""🌙 <b>Resumo do dia:</b>

Hoje foi identificada <b>1 tramitação</b>{extra}. Na seguinte matéria:

{lista}

Até amanhã! 👋"""
    
    else:
        lista = "\n".join([f"• {t}" for t in tramitacoes])
        extra = f" ({senado_count} no Senado)" if senado_count > 0 else ""
        return f"""🌙 <b>Resumo do dia:</b>

Hoje foram identificadas <b>{quantidade} tramitações</b>{extra}. Nas seguintes matérias:

{lista}

Até amanhã! 👋"""


# ============================================================
# CONVERSÃO TELEGRAM HTML → EMAIL HTML
# ============================================================

def telegram_para_email_html(mensagem_telegram, assunto):
    corpo = mensagem_telegram.replace("\n", "<br>")
    
    # Cor do header baseada no conteúdo (azul para Senado)
    is_senado = "ZANATTA NO SENADO" in mensagem_telegram
    header_color = "#0066cc" if is_senado else "#1e3a5f"
    header_gradient = "linear-gradient(135deg, #0066cc 0%, #004499 100%)" if is_senado else "linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)"
    
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
                    <!-- Header -->
                    <tr>
                        <td style="background: {header_gradient}; padding: 25px 30px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 600;">
                                {"🔵 ZANATTA NO SENADO" if is_senado else "🏛️ Monitor Parlamentar"}
                            </h1>
                            <p style="margin: 5px 0 0 0; color: #b8d4e8; font-size: 14px;">
                                Dep. Júlia Zanatta (PL-SC)
                            </p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px; line-height: 1.6; color: #333333; font-size: 15px;">
                            {corpo}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0; color: #6c757d; font-size: 13px;">
                                📊 <a href="{LINK_PAINEL}" style="color: #0d6efd;">Acessar Painel Completo</a>
                            </p>
                            <p style="margin: 10px 0 0 0; color: #6c757d; font-size: 12px;">
                                Monitor Parlamentar - Gabinete Dep. Júlia Zanatta
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


# ============================================================
# FUNÇÕES DE ENVIO
# ============================================================

def enviar_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram: Credenciais não configuradas")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            print("✅ Telegram: Enviado com sucesso")
            return True
        else:
            print(f"❌ Telegram: Erro {resp.status_code}")
            return False
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
    
    html_body = telegram_para_email_html(mensagem_telegram, assunto)
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(recipients)
        
        parte_html = MIMEText(html_body, "html", "utf-8")
        msg.attach(parte_html)
        
        context = ssl.create_default_context()
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls(context=context)
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
    """Envia APENAS para Telegram"""
    if NOTIFICAR_TELEGRAM:
        return enviar_telegram(mensagem)
    print("⏭️ Telegram: Desabilitado")
    return False


def notificar_ambos(mensagem, assunto):
    """Envia para Telegram E Email"""
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
# FUNÇÕES DE MODO DE EXECUÇÃO
# ============================================================

def executar_bom_dia():
    """Bom dia - APENAS TELEGRAM (email não recebe)"""
    print("☀️ MODO: BOM DIA")
    print("=" * 60)
    
    inicializar_resumo_dia()
    print("📋 Resumo do dia inicializado")
    
    mensagem = formatar_mensagem_bom_dia()
    print("\n📤 Enviando bom dia (apenas Telegram)...")
    notificar_telegram_apenas(mensagem)
    
    print("\n✅ Bom dia enviado!")


def executar_resumo_dia():
    """Resumo do dia - TELEGRAM + EMAIL"""
    print("🌙 MODO: RESUMO DO DIA")
    print("=" * 60)
    
    resumo = carregar_resumo_dia()
    tramitacoes = resumo.get("tramitacoes", [])
    
    print(f"📊 Tramitações do dia: {len(tramitacoes)}")
    for t in tramitacoes:
        print(f"   • {t}")
    
    mensagem = formatar_mensagem_resumo_dia(tramitacoes)
    print("\n📤 Enviando resumo (Telegram + Email)...")
    notificar_ambos(mensagem, "🌙 Monitor Parlamentar - Resumo do Dia")
    
    print("\n✅ Resumo enviado!")


def executar_varredura():
    """Varredura - Email SÓ recebe se encontrar tramitação"""
    data_hora_brasilia = obter_data_hora_brasilia()
    
    print("🔍 MODO: VARREDURA")
    print("=" * 60)
    print(f"📅 Data/Hora: {data_hora_brasilia}")
    print()
    
    estado = carregar_estado()
    ultima_teve_novidade = estado.get("ultima_novidade", True)
    
    historico = carregar_historico()
    historico = limpar_historico_antigo(historico)
    
    resumo = carregar_resumo_dia()
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        print("📋 Novo dia - inicializando resumo")
        resumo = {"data": data_hoje, "tramitacoes": []}
    
    proposicoes = buscar_todas_proposicoes(DEPUTADA_ID)
    
    if not proposicoes:
        print("⚠️ Nenhuma proposição encontrada")
        print("\n📤 Enviando status (apenas Telegram)...")
        if ultima_teve_novidade:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_completa())
        else:
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_curta())
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        return
    
    print("\n🔍 Verificando tramitações das últimas 48h (Câmara + Senado)...\n")
    
    props_com_novidade_camara = []
    props_com_novidade_senado = []
    props_ja_notificadas = 0
    erros = 0
    props_no_senado = 0
    
    for i, prop in enumerate(proposicoes, 1):
        sigla_prop = f"{prop['siglaTipo']} {prop['numero']}/{prop['ano']}"
        
        if i % 25 == 0 or i == 1:
            print(f"📊 Progresso: {i}/{len(proposicoes)}...")
        
        # 1. Verificar tramitação na Câmara
        tramitacao = buscar_ultima_tramitacao(prop["id"])
        
        if tramitacao is None:
            erros += 1
        elif tramitacao_recente(tramitacao, horas=48):
            data_hora_tram = tramitacao.get("dataHora", "")
            
            if ja_foi_notificada(historico, prop["id"], data_hora_tram, "camara"):
                props_ja_notificadas += 1
            else:
                print(f"   ✅ NOVA (Câmara)! {sigla_prop}")
                props_com_novidade_camara.append({
                    "proposicao": prop,
                    "tramitacao": tramitacao,
                    "sigla": sigla_prop
                })
        
        # 2. Verificar se está no Senado
        situacao_camara = buscar_situacao_camara(prop["id"])
        if verificar_se_foi_para_senado(situacao_camara.get("situacao", ""), situacao_camara.get("despacho", "")):
            props_no_senado += 1
            
            # Buscar dados do Senado
            dados_senado = buscar_dados_senado(
                prop["siglaTipo"],
                str(prop["numero"]),
                str(prop["ano"])
            )
            
            if dados_senado and dados_senado.get("id_processo"):
                # Buscar movimentações do Senado
                movimentacoes = buscar_movimentacoes_senado(dados_senado["id_processo"], limite=5)
                
                for mov in movimentacoes:
                    if tramitacao_senado_recente(mov, horas=48):
                        data_mov = mov.get("data") or mov.get("dataMovimento") or ""
                        
                        if ja_foi_notificada(historico, prop["id"], data_mov, "senado"):
                            props_ja_notificadas += 1
                        else:
                            print(f"   🔵 NOVA (Senado)! {sigla_prop}")
                            status_senado = buscar_status_senado(dados_senado["id_processo"])
                            props_com_novidade_senado.append({
                                "proposicao": prop,
                                "movimentacao": mov,
                                "dados_senado": dados_senado,
                                "status_senado": status_senado,
                                "sigla": sigla_prop
                            })
                            break  # Só notifica a mais recente
        
        time.sleep(0.15)
    
    total_novidades = len(props_com_novidade_camara) + len(props_com_novidade_senado)
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Total verificadas: {len(proposicoes)}")
    print(f"   Tramitando no Senado: {props_no_senado}")
    print(f"   Novidades Câmara: {len(props_com_novidade_camara)}")
    print(f"   Novidades Senado: {len(props_com_novidade_senado)}")
    print(f"   Já notificadas: {props_ja_notificadas}")
    print(f"   Erros API: {erros}")
    print(f"{'=' * 60}")
    
    if total_novidades > 0:
        # ENCONTROU TRAMITAÇÃO - Telegram + Email
        print(f"\n📤 Enviando {total_novidades} notificação(ões) (Telegram + Email)...\n")
        
        enviadas = 0
        
        # Enviar novidades da Câmara
        for item in props_com_novidade_camara:
            mensagem = formatar_mensagem_novidade(item["proposicao"], item["tramitacao"])
            assunto = f"📢 Nova Tramitação: {item['sigla']}"
            
            if notificar_ambos(mensagem, assunto):
                historico = registrar_notificacao(
                    historico,
                    item["proposicao"]["id"],
                    item["tramitacao"].get("dataHora", ""),
                    item["sigla"],
                    "camara"
                )
                resumo = adicionar_ao_resumo(resumo, item["sigla"], no_senado=False)
                enviadas += 1
            time.sleep(1)
        
        # Enviar novidades do Senado
        for item in props_com_novidade_senado:
            mensagem = formatar_mensagem_novidade_senado(
                item["proposicao"],
                item["movimentacao"],
                item["dados_senado"],
                item["status_senado"]
            )
            assunto = f"🔵 ZANATTA NO SENADO: {item['sigla']}"
            
            if notificar_ambos(mensagem, assunto):
                data_mov = item["movimentacao"].get("data") or item["movimentacao"].get("dataMovimento") or ""
                historico = registrar_notificacao(
                    historico,
                    item["proposicao"]["id"],
                    data_mov,
                    item["sigla"],
                    "senado"
                )
                resumo = adicionar_ao_resumo(resumo, item["sigla"], no_senado=True)
                enviadas += 1
            time.sleep(1)
        
        salvar_estado(True)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        print(f"\n✅ Concluído! {enviadas} mensagens enviadas.")
    
    else:
        # SEM NOVIDADES - APENAS Telegram (email não recebe)
        print("\n📤 Enviando status (apenas Telegram)...")
        
        if ultima_teve_novidade:
            print("   → Mensagem COMPLETA")
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_completa())
        else:
            print("   → Mensagem CURTA")
            notificar_telegram_apenas(formatar_mensagem_sem_novidades_curta())
        
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        print("\n✅ Concluído!")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("🤖 MONIPARBOT - MONITOR PARLAMENTAR v6")
    print("    Deputada Júlia Zanatta")
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
    
    # Lógica:
    # - bom_dia: APENAS Telegram
    # - varredura COM novidade: Telegram + Email
    # - varredura SEM novidade: APENAS Telegram
    # - resumo: Telegram + Email
    
    if MODO_EXECUCAO == "bom_dia":
        executar_bom_dia()
    elif MODO_EXECUCAO == "resumo":
        executar_resumo_dia()
    else:
        executar_varredura()


if __name__ == "__main__":
    main()