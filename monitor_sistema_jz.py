import datetime
import concurrent.futures
import time
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559

HEADERS = {"User-Agent": "MonitorZanatta/4.2 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]
TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]

# ============================================================
# FUNÇÕES DE APOIO / API
# ============================================================

@lru_cache(maxsize=128)
def get_detalhes_proposicao(id_prop):
    """Retorna detalhes de uma proposição específica."""
    if not id_prop:
        return None
    url = f"{BASE_URL}/proposicoes/{id_prop}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get('dados')
        return None
    except:
        return None

def get_tramitacoes(id_prop):
    """Retorna o histórico de tramitações."""
    url = f"{BASE_URL}/proposicoes/{id_prop}/tramitacoes"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            df = pd.DataFrame(r.json().get('dados', []))
            if not df.empty:
                df['dataHora'] = pd.to_datetime(df['dataHora'], errors='coerce')
                df['Data'] = df['dataHora'].dt.strftime('%d/%m/%Y')
                df['Hora'] = df['dataHora'].dt.strftime('%H:%M')
                df = df.sort_values('dataHora', ascending=False)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def normalizar_texto(texto):
    if not texto: return ""
    return "".join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def calcular_dias_parado(df_tram):
    if df_tram.empty:
        return 0
    ultima_data = df_tram['dataHora'].max()
    if pd.isna(ultima_data):
        return 0
    delta = datetime.datetime.now() - ultima_data.to_pydatetime()
    return max(0, delta.days)

def to_xlsx_bytes(df, sheet_name="Dados"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"

# ============================================================
# LÓGICA DE NEGÓCIO (ESTRATÉGIA)
# ============================================================

def montar_estrategia_tabela(sigla_orgao, situacao, andamento, despacho, dias_parado):
    """Gera uma análise sugerida baseada no status atual."""
    # Lógica simplificada de estratégia
    alerta = "Normal"
    if dias_parado > 30: alerta = "Atenção (Parado)"
    if "CCJC" in sigla_orgao: acao = "Articular com Relator da CCJ"
    elif "Plenário" in sigla_orgao: acao = "Mobilizar Bancada"
    else: acao = "Acompanhar comissão"
    
    data = {
        "Métrica": ["Órgão Atual", "Dias Parado", "Gravidade", "Ação Sugerida"],
        "Valor": [sigla_orgao, f"{dias_parado} dias", alerta, acao]
    }
    return pd.DataFrame(data)

# ============================================================
# STREAMLIT UI
# ============================================================

def main():
    st.set_page_config(page_title="Monitor Legislativo - Júlia Zanatta", layout="wide")
    
    st.title("🏛️ Sistema de Monitoramento Legislativo")
    st.subheader(f"Foco: Dep. {DEPUTADA_NOME_PADRAO} ({DEPUTADA_PARTIDO_PADRAO}-{DEPUTADA_UF_PADRAO})")

    with st.sidebar:
        st.header("Filtros de Busca")
        ano = st.number_input("Ano das Proposições", min_value=2019, max_value=2025, value=2025)
        tipos = st.multiselect("Tipos de Proposição", TIPOS_CARTEIRA_PADRAO, default=["PL", "PEC"])
        palavras = st.text_area("Palavras-chave (separadas por vírgula)", value=", ".join(PALAVRAS_CHAVE_PADRAO))
        lista_keywords = [p.strip() for p in palavras.split(",") if p.strip()]

    # 1. BUSCA INICIAL
    @st.cache_data(ttl=3600)
    def buscar_proposicoes_base(ano, tipos_list):
        resultados = []
        for t in tipos_list:
            url = f"{BASE_URL}/proposicoes?siglaTipo={t}&ano={ano}&ordem=ASC&ordenarPor=id"
            r = requests.get(url, headers=HEADERS)
            if r.status_code == 200:
                resultados.extend(r.json().get('dados', []))
        return resultados

    with st.spinner("Buscando lista de proposições..."):
        dados_base = buscar_proposicoes_base(ano, tipos)

    if not dados_base:
        st.warning("Nenhuma proposição encontrada para os filtros selecionados.")
        return

    df_base = pd.DataFrame(dados_base)
    
    # 2. FILTRAGEM POR PALAVRA-CHAVE NA EMENTA
    def filtrar_keywords(df, keywords):
        if not keywords: return df
        regex = "|".join([normalizar_texto(k) for k in keywords])
        # Garante que a ementa não seja nula antes de normalizar
        mask = df['ementa'].fillna("").apply(normalizar_texto).str.contains(regex, na=False)
        return df[mask]

    df_filtrado = filtrar_keywords(df_base, lista_keywords)
    st.info(f"Encontradas {len(df_filtrado)} proposições com as palavras-chave selecionadas.")

    # 3. ENRIQUECIMENTO DE DADOS (Aqui estava o erro)
    # Usamos multithreading para agilizar a consulta de detalhes
    def processar_detalhes(row):
        # Correção crucial: Tratamento de NoneType
        detalhes = get_detalhes_proposicao(row['id'])
        
        if detalhes:
            status = detalhes.get('statusProposicao', {}) or {}
            return {
                "id": row['id'],
                "Sigla": f"{row['siglaTipo']} {row['numero']}/{row['ano']}",
                "Ementa": row['ementa'],
                "Órgão": status.get('siglaOrgao', 'N/A'),
                "Situação": status.get('descricaoSituacao', 'Desconhecida'),
                "Andamento": status.get('descricaoTramitacao', 'N/A'),
                "Despacho": status.get('despacho', 'N/A'),
                "URL": detalhes.get('urlInteiroTeor', '')
            }
        else:
            # Retorno fallback caso a API falhe para um ID específico
            return {
                "id": row['id'],
                "Sigla": f"{row['siglaTipo']} {row['numero']}/{row['ano']}",
                "Ementa": row['ementa'],
                "Órgão": "Erro API",
                "Situação": "Indisponível",
                "Andamento": "Indisponível",
                "Despacho": "Erro ao obter dados",
                "URL": ""
            }

    with st.spinner("Coletando detalhes técnicos..."):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            resultados_detalhes = list(executor.map(processar_detalhes, df_filtrado.to_dict('records')))
    
    df_exibicao = pd.DataFrame(resultados_detalhes)

    # 4. EXIBIÇÃO
    st.divider()
    
    if df_exibicao.empty:
        st.write("Sem dados para exibir.")
    else:
        # Tabela Principal
        st.dataframe(
            df_exibicao[["Sigla", "Órgão", "Situação", "Ementa"]],
            use_container_width=True,
            hide_index=True
        )

        # Seleção para Detalhamento
        st.subheader("🔍 Detalhamento e Estratégia")
        escolha = st.selectbox("Selecione uma proposição para analisar:", df_exibicao["Sigla"].tolist())
        
        if escolha:
            row_sel = df_exibicao[df_exibicao["Sigla"] == escolha].iloc[0]
            selected_id = row_sel['id']
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.write(f"**Ementa:** {row_sel['Ementa']}")
                st.write(f"**Último Despacho:** {row_sel['Despacho']}")
                if row_sel['URL']:
                    st.link_button("📄 Ver Texto Integral (PDF/HTML)", row_sel['URL'])

            # Tramitações e Dias Parado
            df_tram = get_tramitacoes(selected_id)
            parado_dias = calcular_dias_parado(df_tram)
            
            with col2:
                st.metric("Dias na mesma situação", f"{parado_dias} dias")
                st.markdown("### 🧠 Estratégia Sugerida")
                df_estr = montar_estrategia_tabela(
                    row_sel['Órgão'], 
                    row_sel['Situação'], 
                    row_sel['Andamento'], 
                    row_sel['Despacho'], 
                    parado_dias
                )
                st.table(df_estr)

            st.markdown("### 🧭 Linha do Tempo")
            if not df_tram.empty:
                st.dataframe(df_tram[['Data', 'siglaOrgao', 'descricaoTramitacao']].head(10), use_container_width=True)
            else:
                st.info("Nenhum histórico de tramitação encontrado.")

    # Botão de exportação geral
    st.sidebar.divider()
    if not df_exibicao.empty:
        csv = df_exibicao.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button("📥 Baixar Relatório CSV", csv, "relatorio_legislativo.csv", "text/csv")

if __name__ == "__main__":
    main()