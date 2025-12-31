# 🔔 Configuração de Notificações Automáticas

## Para o Administrador do Sistema

### 1. Configurar o Token do Bot no Streamlit Cloud

Vá em **Settings → Secrets** do seu app e adicione:

```toml
[telegram]
bot_token = "8204385840:AAEoOe3-wINFBHjnpqFTC_YFkxo_OA-6yCU"
```

> ⚠️ **Importante**: Gere um novo token pelo @BotFather usando `/revoke` pois o atual foi exposto.

---

### 2. Configurar Notificações Automáticas (GitHub Actions)

#### Passo 1: Criar repositório no GitHub (se ainda não existe)

1. Vá em github.com e crie um novo repositório
2. Faça upload dos arquivos:
   - `monitor_sistema_jz_v23.py`
   - `notificar_tramitacoes.py`

#### Passo 2: Criar pasta de workflows

Crie a estrutura:
```
seu-repositorio/
├── monitor_sistema_jz_v23.py
├── notificar_tramitacoes.py
└── .github/
    └── workflows/
        └── notificar-tramitacoes.yml
```

#### Passo 3: Configurar Secrets no GitHub

1. Vá no repositório → **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret**
3. Adicione:

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | `8204385840:AAEoOe3-wINFBHjnpqFTC_YFkxo_OA-6yCU` |
| `TELEGRAM_CHAT_ID` | `(ID do chat do gabinete)` |

#### Passo 4: Ativar GitHub Actions

1. Vá na aba **Actions** do repositório
2. Clique em **I understand my workflows, go ahead and enable them**
3. O workflow rodará automaticamente a cada 6 horas

#### Passo 5: Testar manualmente

1. Vá em **Actions** → **Notificar Tramitações**
2. Clique em **Run workflow**
3. Escolha quantas horas verificar
4. Clique em **Run workflow** (botão verde)

---

## Para o Usuário Final

### Como receber notificações no seu Telegram:

1. **Obtenha seu ID:**
   - Abra o Telegram
   - Procure por **@userinfobot**
   - Envie qualquer mensagem
   - Copie o número do "Id"

2. **Configure no sistema:**
   - Acesse a aba **🔔 Notificações**
   - Cole seu ID
   - Clique em **Enviar mensagem de teste**

3. **Pronto!**
   - Você receberá notificações quando houver movimentação nas proposições

---

## Frequência das Notificações Automáticas

| Horário (Brasília) | Horário (UTC) |
|--------------------|---------------|
| 21:00 | 00:00 |
| 03:00 | 06:00 |
| 09:00 | 12:00 |
| 15:00 | 18:00 |

O sistema verifica as últimas 8 horas de tramitações a cada execução.

---

## Problemas Comuns

### "Bot não responde"
- Verifique se você iniciou conversa com @MoniParBot
- Envie `/start` para o bot

### "ID inválido"
- O ID deve ser apenas números (ex: `123456789`)
- Obtenha pelo @userinfobot

### "Notificações não chegam automaticamente"
- Verifique se o GitHub Actions está ativado
- Veja os logs em Actions → Notificar Tramitações
