# modules/tabs/tab9_notificacao.py
# v1 08/02/2025 17:45 (Brasília)
"""
Tab 9 – Receber Notificações por Email

Funcionalidades:
- Formulário de cadastro de email
- Informações sobre tipos de notificação
- Lista de emails cadastrados (admin)
- Links para Telegram e Painel Web

Desenvolvido por Lucas Pinheiro para o Gabinete da Dep. Júlia Zanatta
"""
from __future__ import annotations

import streamlit as st

# Funções de email — permanecem no monólito
from monitor_sistema_jz import (
    cadastrar_email_github,
    listar_emails_cadastrados,
)


def render_tab9() -> None:
    """Aba 9 – Receber Notificações por Email."""

    st.title("📧 Receber Notificações por Email")

    st.markdown("""
    ### 📬 Cadastre-se para receber alertas

    Receba notificações por email sempre que houver:
    - 📄 **Nova tramitação** em matérias da Dep. Júlia Zanatta
    - 📋 **Matéria na pauta** de comissões (autoria ou relatoria)
    - 🔑 **Palavras-chave** de interesse nas pautas
    - 🌙 **Resumo do dia** com todas as movimentações

    ---
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("✍️ Cadastrar Email")

        with st.form("form_cadastro_email", clear_on_submit=True):
            novo_email = st.text_input(
                "Seu email",
                placeholder="exemplo@email.com",
                help="Digite seu email para receber as notificações",
            )

            aceite = st.checkbox(
                "Concordo em receber notificações do Monitor Parlamentar",
                value=False,
            )

            submitted = st.form_submit_button("📩 Cadastrar", type="primary")

            if submitted:
                if not novo_email:
                    st.error("Por favor, digite seu email")
                elif not aceite:
                    st.warning("Por favor, marque a caixa de concordância")
                else:
                    with st.spinner("Cadastrando..."):
                        sucesso, mensagem = cadastrar_email_github(novo_email.strip())

                    if sucesso:
                        st.success(f"✅ {mensagem}")
                        st.balloons()
                    else:
                        st.error(f"❌ {mensagem}")

    with col2:
        st.subheader("ℹ️ Informações")

        st.info("""
        **O que você vai receber:**

        📌 Emails apenas quando houver movimentação relevante

        📌 Resumo diário às 20:30

        📌 Link para o painel em cada email
        """)

    st.markdown("---")

    # Emails cadastrados (apenas admin)
    if st.session_state.get("usuario_logado") == "admin":
        with st.expander("👑 Emails cadastrados (Admin)"):
            emails = listar_emails_cadastrados()
            if emails:
                for i, email in enumerate(emails, 1):
                    st.write(f"{i}. {email}")
                st.caption(f"Total: {len(emails)} emails cadastrados")
            else:
                st.write("Nenhum email cadastrado ainda")

    st.markdown("---")

    st.markdown("""
    ### 🔗 Outras formas de acompanhar

    <table style="width:100%">
    <tr>
        <td style="text-align:center; padding:20px;">
            <a href="https://t.me/+seu_grupo_telegram" target="_blank">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="50">
                <br><b>Grupo Telegram</b>
            </a>
        </td>
        <td style="text-align:center; padding:20px;">
            <a href="https://monitorzanatta.streamlit.app" target="_blank">
                <img src="https://streamlit.io/images/brand/streamlit-mark-color.png" width="50">
                <br><b>Painel Web</b>
            </a>
        </td>
    </tr>
    </table>
    """, unsafe_allow_html=True)
