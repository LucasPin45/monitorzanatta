#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notificar_tramitacoes.py
========================================
Monitor de tramitações da Deputada Júlia Zanatta
Verifica novas movimentações e notifica via Telegram + Email

v6: 
- Modo aviso_manutencao: envia aviso quando Câmara está em manutenção
- Modo sistema_normalizado: envia aviso quando sistema volta ao normal
- Telegram + Email para ambos os avisos

v5: 
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

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"User-Agent": "MonitorZanatta/24.0 (gabinete-julia-zanatta)"}

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

# Incluir aviso de manutenção no resumo do dia (use "true" para ativar)
INCLUIR_AVISO_MANUTENCAO = os.getenv("INCLUIR_AVISO_MANUTENCAO", "false").lower() == "true"

# Modo de execução (bom_dia, varredura, resumo, aviso_manutencao, sistema_normalizado)
MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "varredura")

# Tipos de proposição a monitorar
TIPOS_MONITORADOS = ["PL", "PLP", "PDL", "RIC", "REQ", "PRL"]
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


def gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao):
    data_normalizada = str(data_hora_tramitacao)[:19] if data_hora_tramitacao else "sem_data"
    return f"{proposicao_id}_{data_normalizada}"


def ja_foi_notificada(historico, proposicao_id, data_hora_tramitacao):
    chave = gerar_chave_tramitacao(proposicao_id, data_hora_tramitacao)
    for item in historico.get("notificadas", []):
        if item.get("chave") == chave:
            return True
    return False


def registrar_notificacao(historico, proposicao_id, data_hora_tramitacao, sigla_proposicao):
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


def adicionar_ao_resumo(resumo, sigla_proposicao):
    agora = datetime.now(FUSO_BRASILIA)
    data_hoje = agora.strftime("%Y-%m-%d")
    if resumo.get("data") != data_hoje:
        resumo = {"data": data_hoje, "tramitacoes": []}
    if sigla_proposicao not in resumo["tramitacoes"]:
        resumo["tramitacoes"].append(sigla_proposicao)
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


def formatar_mensagem_sem_novidades_completa():
    data_hora = obter_data_hora_brasilia()
    return f"""🔍 <b>Monitor Parlamentar Informa:</b>

Na última varredura não foram encontradas tramitações recentes em matérias da Dep. Júlia Zanatta.

Mas continue atento! 👀

⏰ <i>Varredura: {data_hora}</i>"""


def formatar_mensagem_sem_novidades_curta():
    data_hora = obter_data_hora_brasilia()
    return f"""🔍 Ainda sem novidades em matérias da Dep. Júlia Zanatta.

⏰ <i>{data_hora}</i>"""


def formatar_mensagem_bom_dia():
    return """☀️ <b>Bom dia!</b>

Sou <b>MoniParBot</b>, o Robô do Monitor Parlamentar, sistema criado para monitorar as matérias legislativas de autoria da Deputada Júlia Zanatta, a Deputada pronta para combate! 💪

Ao longo do dia, faremos uma varredura de 2 em 2h para identificar movimentações nas matérias da Deputada. Quando encontrada, será notificada. Quando não encontrada, será avisado que não foi encontrada.

Até daqui a pouco! 🔍"""


def formatar_mensagem_resumo_dia(tramitacoes, incluir_aviso_manutencao=False):
    quantidade = len(tramitacoes)
    
    # Aviso de manutenção para adicionar ao final (se habilitado)
    aviso_manutencao = ""
    if incluir_aviso_manutencao:
        aviso_manutencao = """

━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>ATENÇÃO: Manutenção Programada</b>

A Câmara dos Deputados está realizando manutenção no banco de dados.

📅 <b>Início:</b> Sexta (17/01) às 18h
📅 <b>Retorno:</b> Final do domingo (19/01)

Durante este período, o Monitor pode apresentar dados indisponíveis.

🔄 Avisaremos quando tudo voltar ao normal!"""
    
    if quantidade == 0:
        return f"""🌙 <b>Resumo do dia:</b>

Hoje não foram identificadas tramitações em matérias da Dep. Júlia Zanatta.

Até amanhã! 👋{aviso_manutencao}"""
    
    elif quantidade == 1:
        lista = f"• {tramitacoes[0]}"
        return f"""🌙 <b>Resumo do dia:</b>

Hoje foi identificada <b>1 tramitação</b>. Na seguinte matéria:

{lista}

Até amanhã! 👋{aviso_manutencao}"""
    
    else:
        lista = "\n".join([f"• {t}" for t in tramitacoes])
        return f"""🌙 <b>Resumo do dia:</b>

Hoje foram identificadas <b>{quantidade} tramitações</b>. Nas seguintes matérias:

{lista}

Até amanhã! 👋{aviso_manutencao}"""


def formatar_mensagem_aviso_manutencao():
    """Formata mensagem de aviso de manutenção da Câmara"""
    return """⚠️ <b>AVISO: Sistemas da Câmara dos Deputados em Manutenção</b>

A Diretoria de Inovação e Tecnologia da Informação (Ditec) da Câmara dos Deputados informou que está realizando uma <b>atualização no ambiente tecnológico do serviço de bancos de dados</b>.

📅 <b>Início:</b> Sexta-feira (17/01) às 18h
📅 <b>Previsão de retorno:</b> Final do domingo (19/01)

Durante este período, o <b>Monitor Parlamentar da Dep. Júlia Zanatta</b> pode apresentar dados indisponíveis ou desatualizados, pois depende da API da Câmara.

🔄 O sistema voltará ao normal automaticamente após o término da manutenção.

📢 Avisaremos quando tudo estiver funcionando novamente!"""


def formatar_mensagem_sistema_normalizado():
    """Formata mensagem informando que o sistema voltou ao normal"""
    data_hora = obter_data_hora_brasilia()
    return f"""✅ <b>Sistemas da Câmara Normalizados!</b>

A manutenção programada da Câmara dos Deputados foi concluída.

O <b>Monitor Parlamentar da Dep. Júlia Zanatta</b> está funcionando normalmente! 🎉

🔍 As varreduras de tramitações foram retomadas.

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
                    <!-- Painel Link -->
                    <tr>
                        <td style="padding: 0 30px 25px 30px;">
                            <table role="presentation" style="width: 100%; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 8px; border-left: 4px solid #4caf50;">
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <p style="margin: 0 0 8px 0; color: #2e7d32; font-weight: 600; font-size: 14px;">
                                            📊 Acompanhe em tempo real
                                        </p>
                                        <p style="margin: 0; color: #555; font-size: 13px;">
                                            Acesse o painel completo do Monitor Parlamentar:
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
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0; color: #6c757d; font-size: 12px; text-align: center;">
                                📧 Notificação automática do Monitor Parlamentar<br>
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
    import re
    texto = re.sub(r'<[^>]+>', '', mensagem_telegram)
    texto = texto.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return texto


# ============================================================
# ENVIO DE NOTIFICAÇÕES
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
    msg["From"] = f"Monitor Parlamentar <{EMAIL_SENDER}>"
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
    
    if INCLUIR_AVISO_MANUTENCAO:
        print("⚠️ Aviso de manutenção será incluído no resumo")
    
    mensagem = formatar_mensagem_resumo_dia(tramitacoes, incluir_aviso_manutencao=INCLUIR_AVISO_MANUTENCAO)
    print("\n📤 Enviando resumo (Telegram + Email)...")
    notificar_ambos(mensagem, "🌙 Monitor Parlamentar - Resumo do Dia")
    
    print("\n✅ Resumo enviado!")


def executar_aviso_manutencao():
    """Aviso de manutenção - TELEGRAM + EMAIL"""
    print("⚠️ MODO: AVISO DE MANUTENÇÃO")
    print("=" * 60)
    
    mensagem = formatar_mensagem_aviso_manutencao()
    print("\n📤 Enviando aviso de manutenção (Telegram + Email)...")
    notificar_ambos(mensagem, "⚠️ Monitor Parlamentar - Aviso de Manutenção da Câmara")
    
    print("\n✅ Aviso de manutenção enviado!")


def executar_sistema_normalizado():
    """Aviso de sistema normalizado - TELEGRAM + EMAIL"""
    print("✅ MODO: SISTEMA NORMALIZADO")
    print("=" * 60)
    
    mensagem = formatar_mensagem_sistema_normalizado()
    print("\n📤 Enviando aviso de normalização (Telegram + Email)...")
    notificar_ambos(mensagem, "✅ Monitor Parlamentar - Sistema Normalizado")
    
    print("\n✅ Aviso de normalização enviado!")


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
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESUMO:")
    print(f"   Total verificadas: {len(proposicoes)}")
    print(f"   Com novidades: {len(props_com_novidade)}")
    print(f"   Já notificadas: {props_ja_notificadas}")
    print(f"   Erros API: {erros}")
    print(f"{'=' * 60}")
    
    if props_com_novidade:
        # ENCONTROU TRAMITAÇÃO - Telegram + Email
        print(f"\n📤 Enviando {len(props_com_novidade)} notificação(ões) (Telegram + Email)...\n")
        
        enviadas = 0
        for item in props_com_novidade:
            mensagem = formatar_mensagem_novidade(item["proposicao"], item["tramitacao"])
            assunto = f"📢 Nova Tramitação: {item['sigla']}"
            
            if notificar_ambos(mensagem, assunto):
                historico = registrar_notificacao(
                    historico,
                    item["proposicao"]["id"],
                    item["tramitacao"].get("dataHora", ""),
                    item["sigla"]
                )
                resumo = adicionar_ao_resumo(resumo, item["sigla"])
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
    print("🤖 MONIPARBOT - MONITOR PARLAMENTAR")
    print("    Deputada Júlia Zanatta")
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
    # - aviso_manutencao: Telegram + Email
    # - sistema_normalizado: Telegram + Email
    
    if MODO_EXECUCAO == "bom_dia":
        executar_bom_dia()
    elif MODO_EXECUCAO == "resumo":
        executar_resumo_dia()
    elif MODO_EXECUCAO == "aviso_manutencao":
        executar_aviso_manutencao()
    elif MODO_EXECUCAO == "sistema_normalizado":
        executar_sistema_normalizado()
    else:
        executar_varredura()


if __name__ == "__main__":
    main()
