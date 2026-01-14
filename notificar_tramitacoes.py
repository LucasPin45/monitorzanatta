#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_tramitacoes.py
========================================
Monitor de tramitações da Deputada Júlia Zanatta
Verifica novas movimentações e notifica via Telegram + Email

Tipos monitorados: PL, PLP, PDL, RIC, REQ, PRL
Período: Desde 2023 (início do mandato)
Horário: 08:00 às 20:00 (Brasília) - Segunda a Sexta

v4: 
- Adicionado suporte a notificações por EMAIL
- Ambos os canais (Telegram + Email) são notificados
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

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/24.0 (gabinete-julia-zanatta)"}

DEPUTADA_ID = 220559  # Júlia Zanatta

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Email (SMTP)
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")  # email que envia
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # senha de app (não a senha normal!)
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")  # emails separados por vírgula

# Controle de canais habilitados
NOTIFICAR_TELEGRAM = os.getenv("NOTIFICAR_TELEGRAM", "true").lower() == "true"
NOTIFICAR_EMAIL = os.getenv("NOTIFICAR_EMAIL", "true").lower() == "true"

# Modo de execução (bom_dia, varredura, resumo)
MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# Tipos de proposição a monitorar
TIPOS_MONITORADOS = ["PL", "PLP", "PDL", "RIC", "REQ", "PRL"]

# Data de início do mandato
DATA_INICIO_MANDATO = "2023-02-01"

# Arquivo para guardar estado entre execuções
ESTADO_FILE = Path("estado_monitor.json")

# Arquivo para guardar histórico de notificações enviadas
HISTORICO_FILE = Path("historico_notificacoes.json")

# Arquivo para guardar tramitações do dia (para resumo)
RESUMO_DIA_FILE = Path("resumo_dia.json")

# Dias para manter histórico (evita crescer indefinidamente)
DIAS_MANTER_HISTORICO = 7

# Fuso horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

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
# GERENCIAMENTO DE HISTÓRICO DE NOTIFICAÇÕES
# ============================================================

def carregar_historico():
    """Carrega o histórico de notificações já enviadas"""
    try:
        if HISTORICO_FILE.exists():
            with open(HISTORICO_FILE, "r") as f:
                historico = json.load(f)
                print(f"📂 Histórico carregado: {len(historico.get('notificadas', []))} tramitações registradas")
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
    """Remove entradas antigas do histórico para não crescer indefinidamente"""
    agora = datetime.now(FUSO_BRASILIA)
    data_corte = (agora - timedelta(days=DIAS_MANTER_HISTORICO)).isoformat()
    
    notificadas_original = len(historico.get("notificadas", []))
    
    # Filtrar apenas as entradas recentes
    historico["notificadas"] = [
        item for item in historico.get("notificadas", [])
        if item.get("registrado_em", "") >= data_corte
    ]
    
    removidas = notificadas_original - len(historico["notificadas"])
    if removidas > 0:
        print(f"🧹 Limpeza do histórico: {removidas} entradas antigas removidas")
    
    historico["ultima_limpeza"] = agora.isoformat()
    return historico


def gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao):
    """
    Gera uma chave única para identificar uma tramitação específica.
    Formato: {proposicao_id}_{data_hora_tramitacao}
    """
    # Normaliza a data/hora para evitar variações
    data_normalizada = str(data_hora_tramitacao)[:19] if data_hora_tramitacao else "sem_data"
    return f"{proposicao_id}_{data_normalizada}"


def ja_foi_notificada(historico, proposicao_id, data_hora_tramitacao):
    """Verifica se uma tramitação já foi notificada anteriormente"""
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao)
    
    for item in historico.get("notificadas", []):
        if item.get("chave") == chave:
            return True
    
    return False


def registrar_notificacao(historico, proposicao_id, data_hora_tramitacao, sigla_proposicao):
    """Registra uma tramitação como notificada"""
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao)
    agora = datetime.now(FUSO_BRASILIA).isoformat()
    
    historico["notificadas"].append({
        "chave": chave,
        "proposicao_id": proposicao_id,
        "sigla": sigla_proposicao,
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
                print(f"📂 Resumo do dia carregado: {len(resumo.get('tramitacoes', []))} tramitações")
                return resumo
    except Exception as e:
        print(f"⚠️ Erro ao carregar resumo do dia: {e}")
    
    return {"data": None, "tramitacoes": []}


def salvar_resumo_dia(resumo):
    """Salva as tramitações do dia"""
    try:
        with open(RESUMO_DIA_FILE, "w") as f:
            json.dump(resumo, f, indent=2)
        print(f"💾 Resumo do dia salvo: {len(resumo.get('tramitacoes', []))} tramitações")
    except Exception as e:
        print(f"⚠️ Erro ao salvar resumo do dia: {e}")


def inicializar_resumo_dia():
    """Inicializa/reseta o resumo do dia (chamado no bom dia)"""
    agora = datetime.now(FUSO_BRASILIA)
    resumo = {
        "data": agora.strftime("%Y-%m-%d"),
        "tramitacoes": []
    }
    salvar_resumo_dia(resumo)
    return resumo


def adicionar_ao_resumo(resumo, sigla_proposicao):
    """Adiciona uma tramitação ao resumo do dia"""
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    
    # Se mudou o dia, reinicia o resumo
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": []}
    
    # Evita duplicatas no resumo do dia
    if sigla_proposicao not in resumo["tramitacoes"]:
        resumo["tramitacoes"].append(sigla_proposicao)
    
    return resumo


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar_html(texto):
    """
    Escapa caracteres especiais para evitar erro 400 no Telegram.
    Caracteres como <, >, & quebram o parse_mode=HTML.
    """
    if not texto:
        return ""
    return html.escape(str(texto))


def obter_data_hora_brasilia():
    """Retorna data e hora no fuso de Brasília"""
    agora_utc = datetime.now(timezone.utc)
    agora_brasilia = agora_utc.astimezone(FUSO_BRASILIA)
    return agora_brasilia.strftime("%d/%m/%Y às %H:%M")


def buscar_proposicoes_por_tipo(deputado_id, sigla_tipo):
    """Busca TODAS as proposições de um tipo específico desde o início do mandato"""
    
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
            tem_proxima = any(link.get("rel") == "next" for link in links)
            
            if not tem_proxima:
                break
                
            pagina += 1
            time.sleep(0.2)
            
        except Exception as e:
            print(f"   ⚠️ Erro ao buscar {sigla_tipo}: {e}")
            break
    
    return proposicoes


def buscar_todas_proposicoes(deputado_id):
    """Busca proposições de todos os tipos monitorados desde 2023"""
    
    print(f"🔍 Buscando proposições dos tipos: {', '.join(TIPOS_MONITORADOS)}")
    print(f"📅 Período: desde {DATA_INICIO_MANDATO} (início do mandato)")
    print()
    
    todas_proposicoes = []
    
    for tipo in TIPOS_MONITORADOS:
        props = buscar_proposicoes_por_tipo(deputado_id, tipo)
        print(f"   {tipo}: {len(props)} proposições")
        todas_proposicoes.extend(props)
        time.sleep(0.3)
    
    print(f"\n✅ Total de proposições a verificar: {len(todas_proposicoes)}")
    return todas_proposicoes


def buscar_ultima_tramitacao(proposicao_id):
    """Busca a última tramitação de uma proposição"""
    
    url = f"{BASE_URL}/proposicoes/{proposicao_id}/tramitacoes"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        tramitacoes = data.get("dados", [])
        
        if tramitacoes:
            tramitacoes_ordenadas = sorted(
                tramitacoes,
                key=lambda x: x.get("dataHora", ""),
                reverse=True
            )
            return tramitacoes_ordenadas[0]
            
    except Exception:
        pass
    
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
# FORMATAÇÃO DE MENSAGENS (Telegram HTML)
# ============================================================

def formatar_mensagem_novidade(proposicao, tramitacao):
    """Formata mensagem de nova tramitação com escape de HTML"""
    
    # Dados básicos (não precisam de escape - são controlados)
    sigla = proposicao.get("siglaTipo", "")
    numero = proposicao.get("numero", "")
    ano = proposicao.get("ano", "")
    
    # Dados que PRECISAM de escape (vêm da API e podem ter caracteres especiais)
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
    
    # Descrição também precisa de escape
    descricao_raw = tramitacao.get("despacho", "") or tramitacao.get("descricaoTramitacao", "")
    descricao = escapar_html(descricao_raw)
    
    link = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={proposicao['id']}"
    
    data_hora_varredura = obter_data_hora_brasilia()
    
    mensagem = f"""📢 <b>Monitor Parlamentar Informa:</b>

Houve nova movimentação!

📄 <b>{sigla} {numero}/{ano}</b>
{ementa}

📅 {data_formatada} → {descricao}

🔗 <a href="{link}">Ver tramitação completa</a>

⏰ <i>Varredura realizada em {data_hora_varredura}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_completa():
    """Formata mensagem completa quando não há novidades"""
    
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""🔍 <b>Monitor Parlamentar Informa:</b>

Na última varredura não foram encontradas tramitações recentes em matérias da Dep. Júlia Zanatta.

Mas continue atento! 👀

⏰ <i>Varredura realizada em {data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_sem_novidades_curta():
    """Formata mensagem curta quando não há novidades"""
    
    data_hora = obter_data_hora_brasilia()
    
    mensagem = f"""🔍 Ainda sem novidades em matérias da Dep. Júlia Zanatta.

⏰ <i>{data_hora}</i>"""
    
    return mensagem


def formatar_mensagem_bom_dia():
    """Formata mensagem de bom dia"""
    
    mensagem = """☀️ <b>Bom dia!</b>

Sou <b>MoniParBot</b>, ou Robô do Monitor Parlamentar, sistema criado para monitorar as matérias legislativas de autoria da Deputada Júlia Zanatta, a Deputada pronta para combate! 💪

Ao longo do dia, faremos uma varredura de 2 em 2h para identificar movimentações nas matérias da Deputada. Quando encontrada, será notificada. Quando não encontrada, será avisado que não foi encontrada.

Até daqui a pouco! 🔍"""
    
    return mensagem


def formatar_mensagem_resumo_dia(tramitacoes):
    """Formata mensagem de resumo do dia"""
    
    quantidade = len(tramitacoes)
    
    if quantidade == 0:
        mensagem = """🌙 <b>Resumo do dia:</b>

Hoje não foram identificadas tramitações em matérias da Dep. Júlia Zanatta.

Até amanhã! 👋"""
    
    elif quantidade == 1:
        lista = f"• {tramitacoes[0]}"
        mensagem = f"""🌙 <b>Resumo do dia:</b>

Hoje foi identificada <b>1 tramitação</b>. Na seguinte matéria:

{lista}

Até amanhã! 👋"""
    
    else:
        lista = "\n".join([f"• {t}" for t in tramitacoes])
        mensagem = f"""🌙 <b>Resumo do dia:</b>

Hoje foram identificadas <b>{quantidade} tramitações</b>. Nas seguintes matérias:

{lista}

Até amanhã! 👋"""
    
    return mensagem


# ============================================================
# CONVERSÃO TELEGRAM HTML → EMAIL HTML
# ============================================================

def telegram_para_email_html(mensagem_telegram, assunto):
    """
    Converte uma mensagem formatada para Telegram (HTML simples)
    em um email HTML bonito e responsivo.
    """
    
    # Converte quebras de linha para <br>
    corpo = mensagem_telegram.replace("\n", "<br>")
    
    # Template de email responsivo
    email_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{assunto}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 25px 30px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 600;">
                                🏛️ Monitor Parlamentar
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
                            <p style="margin: 0; color: #6c757d; font-size: 12px; text-align: center;">
                                📧 Esta é uma notificação automática do Monitor Parlamentar<br>
                                Sistema de acompanhamento legislativo
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return email_html


def extrair_texto_plano(mensagem_telegram):
    """
    Extrai texto plano de uma mensagem HTML do Telegram.
    Usado como fallback para clientes de email que não suportam HTML.
    """
    import re
    
    # Remove tags HTML
    texto = re.sub(r'<[^>]+>', '', mensagem_telegram)
    
    # Substitui entidades HTML comuns
    texto = texto.replace('&amp;', '&')
    texto = texto.replace('&lt;', '<')
    texto = texto.replace('&gt;', '>')
    texto = texto.replace('&quot;', '"')
    
    return texto


# ============================================================
# ENVIO DE NOTIFICAÇÕES
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
        print("✅ Telegram: Mensagem enviada com sucesso!")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Telegram: Erro ao enviar mensagem: {e}")
        # Log adicional para debug
        try:
            error_detail = resp.json()
            print(f"   Detalhe do erro: {error_detail}")
        except:
            print(f"   Response: {resp.text}")
        return False
    except Exception as e:
        print(f"❌ Telegram: Erro ao enviar mensagem: {e}")
        return False


def enviar_email(mensagem_telegram, assunto):
    """
    Envia email usando SMTP.
    Converte a mensagem do formato Telegram para email HTML.
    """
    
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENTS:
        print("⚠️ Email: Configuração incompleta (EMAIL_SENDER, EMAIL_PASSWORD ou EMAIL_RECIPIENTS)")
        return False
    
    # Lista de destinatários
    recipients = [e.strip() for e in EMAIL_RECIPIENTS.split(",") if e.strip()]
    
    if not recipients:
        print("⚠️ Email: Nenhum destinatário configurado")
        return False
    
    # Criar mensagem
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"Monitor Parlamentar <{EMAIL_SENDER}>"
    msg["To"] = ", ".join(recipients)
    
    # Versão texto plano (fallback)
    texto_plano = extrair_texto_plano(mensagem_telegram)
    parte_texto = MIMEText(texto_plano, "plain", "utf-8")
    
    # Versão HTML
    html_email = telegram_para_email_html(mensagem_telegram, assunto)
    parte_html = MIMEText(html_email, "html", "utf-8")
    
    # Adiciona as partes (texto primeiro, HTML depois - prioridade)
    msg.attach(parte_texto)
    msg.attach(parte_html)
    
    try:
        # Conexão segura com SMTP
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
        print("❌ Email: Falha na autenticação. Verifique EMAIL_SENDER e EMAIL_PASSWORD")
        print("   Dica: Para Gmail, use uma 'Senha de App' em vez da senha normal")
        return False
    except Exception as e:
        print(f"❌ Email: Erro ao enviar: {e}")
        return False


def notificar(mensagem, assunto="Monitor Parlamentar - Notificação"):
    """
    Envia notificação para todos os canais habilitados (Telegram e/ou Email).
    Retorna True se pelo menos um canal teve sucesso.
    """
    
    resultados = []
    
    # Telegram
    if NOTIFICAR_TELEGRAM:
        resultado_telegram = enviar_telegram(mensagem)
        resultados.append(("Telegram", resultado_telegram))
    else:
        print("⏭️ Telegram: Desabilitado")
    
    # Email
    if NOTIFICAR_EMAIL:
        resultado_email = enviar_email(mensagem, assunto)
        resultados.append(("Email", resultado_email))
    else:
        print("⏭️ Email: Desabilitado")
    
    # Retorna True se pelo menos um canal teve sucesso
    return any(r[1] for r in resultados)


# ============================================================
# FUNÇÕES DE MODO DE EXECUÇÃO
# ============================================================

def executar_bom_dia():
    """Envia mensagem de bom dia e reseta o resumo do dia"""
    
    print("☀️ MODO: BOM DIA")
    print("=" * 60)
    
    # Resetar resumo do dia
    inicializar_resumo_dia()
    print("📋 Resumo do dia inicializado")
    
    # Enviar mensagem de bom dia
    mensagem = formatar_mensagem_bom_dia()
    notificar(mensagem, assunto="☀️ Monitor Parlamentar - Bom Dia!")
    
    print("\n✅ Bom dia enviado!")


def executar_resumo_dia():
    """Envia resumo das tramitações do dia"""
    
    print("🌙 MODO: RESUMO DO DIA")
    print("=" * 60)
    
    # Carregar resumo do dia
    resumo = carregar_resumo_dia()
    tramitacoes = resumo.get("tramitacoes", [])
    
    print(f"📊 Tramitações do dia: {len(tramitacoes)}")
    for t in tramitacoes:
        print(f"   • {t}")
    
    # Enviar mensagem de resumo
    mensagem = formatar_mensagem_resumo_dia(tramitacoes)
    notificar(mensagem, assunto="🌙 Monitor Parlamentar - Resumo do Dia")
    
    print("\n✅ Resumo do dia enviado!")


def executar_varredura():
    """Executa varredura normal de tramitações"""
    
    data_hora_brasilia = obter_data_hora_brasilia()
    
    print("🔍 MODO: VARREDURA")
    print("=" * 60)
    print(f"📅 Data/Hora (Brasília): {data_hora_brasilia}")
    print()
    
    # Carregar estado da última execução
    estado = carregar_estado()
    ultima_teve_novidade = estado.get("ultima_novidade", True)
    
    # Carregar histórico de notificações
    historico = carregar_historico()
    historico = limpar_historico_antigo(historico)
    
    # Carregar resumo do dia
    resumo = carregar_resumo_dia()
    
    # Verificar se é um novo dia (e resetar resumo se necessário)
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        print("📋 Novo dia detectado - inicializando resumo")
        resumo = {"data": data_hoje, "tramitacoes": []}
    
    # 1. Buscar proposições
    proposicoes = buscar_todas_proposicoes(DEPUTADA_ID)
    
    if not proposicoes:
        print("⚠️ Nenhuma proposição encontrada")
        if ultima_teve_novidade:
            notificar(formatar_mensagem_sem_novidades_completa(), "🔍 Monitor Parlamentar - Varredura")
        else:
            notificar(formatar_mensagem_sem_novidades_curta(), "🔍 Monitor Parlamentar - Varredura")
        salvar_estado(False)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        return
    
    # 2. Verificar tramitações recentes
    print("\n🔍 Verificando tramitações das últimas 48h...\n")
    
    props_com_novidade = []
    props_ja_notificadas = 0
    erros = 0
    
    for i, prop in enumerate(proposicoes, 1):
        sigla_prop = f"{prop['siglaTipo']} {prop['numero']}/{prop['ano']}"
        
        if i % 25 == 0 or i == 1:
            print(f"📊 Progresso: {i}/{len(proposicoes)}...")
        
        tramitacao = buscar_ultima_tramitacao(prop["id"])
        
        if tramitacao is None:
            erros += 1
            continue
        
        if tramitacao_recente(tramitacao, horas=48):
            # VERIFICAR SE JÁ FOI NOTIFICADA
            data_hora_tram = tramitacao.get("dataHora", "")
            
            if ja_foi_notificada(historico, prop["id"], data_hora_tram):
                print(f"   ⏭️ JÁ NOTIFICADA: {sigla_prop}")
                props_ja_notificadas += 1
            else:
                print(f"   ✅ NOVA! {sigla_prop}")
                props_com_novidade.append({
                    "proposicao": prop,
                    "tramitacao": tramitacao,
                    "sigla": sigla_prop
                })
        
        time.sleep(0.15)
    
    # 3. Resumo
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Total verificadas: {len(proposicoes)}")
    print(f"   Com novidades (novas): {len(props_com_novidade)}")
    print(f"   Já notificadas anteriormente: {props_ja_notificadas}")
    print(f"   Erros de API: {erros}")
    print(f"{'=' * 60}")
    
    # 4. Enviar notificações
    if props_com_novidade:
        print(f"\n📤 Enviando {len(props_com_novidade)} notificação(ões)...\n")
        
        enviadas = 0
        for item in props_com_novidade:
            mensagem = formatar_mensagem_novidade(item["proposicao"], item["tramitacao"])
            assunto = f"📢 Nova Tramitação: {item['sigla']}"
            
            if notificar(mensagem, assunto):
                # Registrar no histórico após envio bem-sucedido
                historico = registrar_notificacao(
                    historico,
                    item["proposicao"]["id"],
                    item["tramitacao"].get("dataHora", ""),
                    item["sigla"]
                )
                # Adicionar ao resumo do dia
                resumo = adicionar_ao_resumo(resumo, item["sigla"])
                enviadas += 1
            time.sleep(1)
        
        salvar_estado(True)
        salvar_historico(historico)
        salvar_resumo_dia(resumo)
        print(f"\n✅ Processo concluído! {enviadas} mensagens enviadas.")
    
    else:
        print("\n📤 Enviando mensagem de status...")
        
        if ultima_teve_novidade:
            print("   → Mensagem COMPLETA (primeira do ciclo)")
            notificar(formatar_mensagem_sem_novidades_completa(), "🔍 Monitor Parlamentar - Varredura")
        else:
            print("   → Mensagem CURTA (continuação)")
            notificar(formatar_mensagem_sem_novidades_curta(), "🔍 Monitor Parlamentar - Varredura")
        
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
    print("🤖 MONIPARBOT - MONITOR PARLAMENTAR")
    print("    Deputada Júlia Zanatta")
    print("=" * 60)
    print()
    
    # Status dos canais de notificação
    print("📡 CANAIS DE NOTIFICAÇÃO:")
    
    # Telegram
    if NOTIFICAR_TELEGRAM:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            print(f"   ✅ Telegram: Habilitado (Token: {TELEGRAM_BOT_TOKEN[:10]}...)")
        else:
            print("   ⚠️ Telegram: Habilitado mas credenciais faltando!")
    else:
        print("   ⏭️ Telegram: Desabilitado")
    
    # Email
    if NOTIFICAR_EMAIL:
        if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENTS:
            recipients = EMAIL_RECIPIENTS.split(",")
            print(f"   ✅ Email: Habilitado ({len(recipients)} destinatário(s))")
        else:
            print("   ⚠️ Email: Habilitado mas configuração incompleta!")
    else:
        print("   ⏭️ Email: Desabilitado")
    
    print(f"\n📋 Modo de execução: {MODO_EXECUCAO}")
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