# modules/tabs/tab1_dashboard.py
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_tab1(provider) -> None:
    """
    Aba 1 — Dashboard Executivo.
    Esta função deve conter SOMENTE a UI da Aba 1 e chamadas ao provider.
    Não colocar requests aqui. Não colocar cache aqui.
    """

    # ✅ A PARTIR DO PRÓXIMO PASSO (3.2), vamos mover o conteúdo real da Aba 1
    st.title("📊 Dashboard Executivo")

    perfil: Dict[str, Any] = provider.get_perfil_deputada()
    nome = perfil.get("nome", "Júlia Zanatta")
    partido = perfil.get("partido", "PL")
    uf = perfil.get("uf", "SC")

    st.markdown(f"### {nome}")
    st.markdown(f"**Partido:** {partido} | **UF:** {uf}")

    st.info("Aba 1 (placeholder) criada. No próximo passo vamos mover o conteúdo completo do monólito para cá.")
