# core/services/notificacao.py
"""
Serviço de Notificações — Email, Telegram, Google Sheets

Contém toda a lógica de:
- Cadastro de emails via GitHub API
- Envio de mensagens Telegram
- Registro de logins e downloads no Google Sheets
- Auditoria de uso do sistema

Extraído do monólito v50.
"""
from __future__ import annotations

import json
import base64
import datetime
from typing import Optional

import streamlit as st
import requests


# ============================================================
# IMPORTS OPCIONAIS
# ============================================================

# Tentar importar biblioteca de PDF (opcional)
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

# Tentar importar biblioteca do Google Sheets (opcional)
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False


# ============================================================
# EMAIL — CADASTRO VIA GITHUB API
# ============================================================

def cadastrar_email_github(novo_email: str) -> tuple[bool, str]:
    """
    Adiciona um novo email à lista de destinatários no repositório GitHub.
    Atualiza o arquivo emails_cadastrados.json no repositório.

    Retorna: (sucesso: bool, mensagem: str)
    """
    try:
        # Configurações do GitHub (adicionar em st.secrets)
        github_config = st.secrets.get("github", {})
        token = github_config.get("token")  # Personal Access Token
        repo = github_config.get("repo", "LucasPin45/monitorzanatta")

        if not token:
            return False, "Token do GitHub não configurado"

        # Validar email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", novo_email):
            return False, "Email inválido"

        # URL da API do GitHub
        api_url = f"https://api.github.com/repos/{repo}/contents/emails_cadastrados.json"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Buscar arquivo atual
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Arquivo existe - atualizar
            data = response.json()
            sha = data["sha"]
            content = base64.b64decode(data["content"]).decode("utf-8")
            emails_data = json.loads(content)
        elif response.status_code == 404:
            # Arquivo não existe - criar
            sha = None
            emails_data = {"emails": [], "ultima_atualizacao": None}
        else:
            return False, f"Erro ao acessar GitHub: {response.status_code}"

        # Verificar se email já está cadastrado
        if novo_email.lower() in [e.lower() for e in emails_data.get("emails", [])]:
            return False, "Este email já está cadastrado"

        # Adicionar novo email
        emails_data["emails"].append(novo_email)
        emails_data["ultima_atualizacao"] = datetime.datetime.now().isoformat()

        # Preparar conteúdo para upload
        new_content = json.dumps(emails_data, indent=2, ensure_ascii=False)
        new_content_b64 = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        # Fazer commit
        commit_data = {
            "message": f"📧 Novo email cadastrado via painel",
            "content": new_content_b64,
            "branch": "main"
        }

        if sha:
            commit_data["sha"] = sha

        response = requests.put(api_url, headers=headers, json=commit_data, timeout=10)

        if response.status_code in [200, 201]:
            return True, f"Email {novo_email} cadastrado com sucesso!"
        else:
            return False, f"Erro ao salvar: {response.status_code}"

    except Exception as e:
        return False, f"Erro: {str(e)}"



def listar_emails_cadastrados() -> list:
    """
    Lista os emails cadastrados no arquivo emails_cadastrados.json
    """
    try:
        github_config = st.secrets.get("github", {})
        token = github_config.get("token")
        repo = github_config.get("repo", "LucasPin45/monitorzanatta")

        if not token:
            return []

        api_url = f"https://api.github.com/repos/{repo}/contents/emails_cadastrados.json"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            emails_data = json.loads(content)
            return emails_data.get("emails", [])

        return []

    except Exception:
        return []




# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensagem: str) -> bool:
    """
    Envia mensagem para o Telegram.
    Retorna True se enviou com sucesso, False caso contrário.
    """
    try:
        telegram_config = st.secrets.get("telegram", {})
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        
        if not bot_token or not chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False




# ============================================================
# GOOGLE SHEETS — REGISTRO DE LOGIN E DOWNLOAD
# ============================================================

def registrar_gsheets(usuario: str, data_hora: str, ip: str = "N/A") -> bool:
    """
    Registra login no Google Sheets.
    Retorna True se registrou com sucesso, False caso contrário.
    """
    if not GSHEETS_AVAILABLE:
        return False
    
    try:
        gsheets_config = st.secrets.get("gsheets", {})
        spreadsheet_id = gsheets_config.get("spreadsheet_id")
        credentials_json = gsheets_config.get("credentials")
        
        if not spreadsheet_id or not credentials_json:
            return False
        
        # Carregar credenciais
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = dict(credentials_json)
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # Dados a inserir
        valores = [[data_hora, usuario, ip]]
        
        body = {"values": valores}
        
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A:C",  # Colunas: Data/Hora, Usuário, IP
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        return True
    except Exception:
        return False



def registrar_download_gsheets(usuario: str, data_hora: str, tipo_relatorio: str, proposicao: str = "") -> bool:
    """
    Registra download de relatório no Google Sheets (aba Downloads).
    Retorna True se registrou com sucesso, False caso contrário.
    """
    if not GSHEETS_AVAILABLE:
        return False
    
    try:
        gsheets_config = st.secrets.get("gsheets", {})
        spreadsheet_id = gsheets_config.get("spreadsheet_id")
        credentials_json = gsheets_config.get("credentials")
        
        if not spreadsheet_id or not credentials_json:
            return False
        
        # Carregar credenciais
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = dict(credentials_json)
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # Dados a inserir: Data/Hora, Usuário, Tipo de Relatório, Proposição
        valores = [[data_hora, usuario, tipo_relatorio, proposicao]]
        
        body = {"values": valores}
        
        # Registrar na aba "Downloads" (será criada automaticamente se não existir)
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Downloads!A:D",  # Aba: Downloads | Colunas: Data/Hora, Usuário, Tipo, Proposição
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        return True
    except Exception:
        return False



def registrar_download(tipo_relatorio: str, proposicao: str = ""):
    """
    Registra o download de relatório no Telegram e Google Sheets.
    Executado em background para não travar a interface.
    
    Args:
        tipo_relatorio: Ex: "PDF Linha do Tempo", "XLSX Linha do Tempo", "PDF Matérias"
        proposicao: Ex: "PL 5701/2025"
    """
    try:
        # Obter usuário logado
        usuario = st.session_state.get("usuario_logado", "Desconhecido")
        
        # Obter data/hora de Brasília
        tz_brasilia = ZoneInfo("America/Sao_Paulo")
        agora = datetime.datetime.now(tz_brasilia)
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        # Mensagem para o Telegram
        mensagem = (
            f"📥 <b>Download de Relatório</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"📄 <b>Tipo:</b> {tipo_relatorio}\n"
        )
        if proposicao:
            mensagem += f"📋 <b>Proposição:</b> {proposicao}\n"
        mensagem += f"📅 <b>Data/Hora:</b> {data_hora_str}"
        
        # Enviar notificação Telegram
        enviar_telegram(mensagem)
        
        # Registrar no Google Sheets
        registrar_download_gsheets(usuario, data_hora_str, tipo_relatorio, proposicao)
        
    except Exception:
        # Silenciosamente ignora erros para não travar a interface
        pass



def registrar_login(usuario: str):
    """
    Registra o login do usuário no Telegram e Google Sheets.
    Executado em background para não travar a interface.
    """
    try:
        # Obter data/hora de Brasília
        tz_brasilia = ZoneInfo("America/Sao_Paulo")
        agora = datetime.datetime.now(tz_brasilia)
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        # Tentar obter IP (pode não funcionar em todos os ambientes)
        ip = "N/A"
        try:
            # No Streamlit Cloud, headers podem ter o IP
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                ip = st.context.headers.get("x-forwarded-for", "N/A")
        except Exception:
            pass
        
        # Mensagem para o Telegram
        mensagem = (
            f"🔐 <b>Login no Monitor Zanatta</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"📅 <b>Data/Hora:</b> {data_hora_str}\n"
            f"🌐 <b>IP:</b> {ip}"
        )
        
        # Enviar notificação Telegram
        enviar_telegram(mensagem)
        
        # Registrar no Google Sheets
        registrar_gsheets(usuario, data_hora_str, ip)
        
    except Exception:
        # Silenciosamente ignora erros para não travar o login
        pass


# ============================================================



# ============================================================
# TELEGRAM — ENVIO DIRETO (BOT TOKEN)
# ============================================================

def telegram_enviar_mensagem(bot_token: str, chat_id: str, mensagem: str, parse_mode: str = "HTML") -> dict:
    """
    Envia mensagem via Telegram Bot API.
    
    Para configurar:
    1. Crie um bot com @BotFather no Telegram
    2. Copie o token do bot
    3. Inicie conversa com o bot e envie /start
    4. Obtenha seu chat_id em: https://api.telegram.org/bot<TOKEN>/getUpdates
    
    Returns:
        dict com 'ok' (bool) e 'message' ou 'error'
    """
    if not bot_token or not chat_id:
        return {"ok": False, "error": "Bot token ou chat_id não configurado"}
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get("ok"):
            return {"ok": True, "message": "Mensagem enviada com sucesso!"}
        else:
            return {"ok": False, "error": data.get("description", "Erro desconhecido")}
    except Exception as e:
        return {"ok": False, "error": str(e)}



