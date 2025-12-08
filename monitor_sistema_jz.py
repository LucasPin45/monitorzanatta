import datetime
import unicodedata
from functools import lru_cache

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÕES BÁSICAS
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559  # ID da Júlia na API da Câmara

HEADERS = {
    "User-Agent": "MonitorZanatta/1.0 (gabinete-julia-zanatta)"
}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina",
    "Armas",
    "Arma",
    "Aborto",
    "Conanda",
    "Violência",
    "PIX",
    "DREX",
    "Imposto de Renda",
    "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = [
    "CDC",      # Defesa do Consumidor
    "CCOM",     # Comunicação
    "CE",       # Educação
    "CREDN",    # Relações Exteriores e Defesa Nacional
    "CCJC",     # Constituição e Justiça e de Cidadania
]

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================


def normalize_text(text):
    """Remove acentos e coloca em minúsculas para comparação/busca."""
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


def matches_deputy(nome, alvo_nome, partido=None, alvo_partido=None, uf=None, alvo_uf=None):
    """
    Verifica se (nome, partido, uf) é a deputada alvo.
    Usa match 'frouxo' no nome e, se disponível, partido/UF.
    """
    if not nome:
        return False

    if normalize_text(alvo_nome) not in normalize_text(nome):
        return False

    if alvo_partido and partido:
        if normalize_text(alvo_partido) != normalize_text(partido):
            return False

    if alvo_uf and uf:
        if normalize_text(alvo_uf) != normalize_text(uf):
            return False

    return True


def safe_get(url, params=None):
    """Wrapper de requests.get com tratamento simples."""
    resp = requests.get(url, params=params or {}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_proposicao_id_from_uri(uri):
    if not uri:
        return None
    return uri.rstrip("/").split("/")[-1]


def get_proposicao_id_from_item(item):
    """
    Tenta extrair o ID da proposição com prioridade:

      1) proposicaoRelacionada*  (PL principal)
      2) proposicaoPrincipal*
      3) proposicao*             (parecer, PRL etc.)
      4) campos de URI diretos
    """

    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_", "proposicao_relacionada"],
        ["proposicaoPrincipal", "proposicao_principal"],
        ["proposicao", "proposicao_"],
    ]

    # 1) ID direto nos blocos
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                if prop.get("id"):
                    return str(prop["id"])
                if prop.get("idProposicao"):
                    return str(prop["idProposicao"])

    # 2) ID a partir de URIs nos blocos
    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                uri = (
                    prop.get("uri")
                    or prop.get("uriProposicao")
                    or prop.get("uriProposicaoPrincipal")
                )
                if uri:
                    return extract_proposicao_id_from_uri(uri)

    # 3) URIs diretas no item
    for chave_uri in ["uriProposicaoPrincipal", "uriProposicao", "uri"]:
        if item.get(chave_uri):
            return extract_proposicao_id_from_uri(item[chave_uri])

    return None


@lru_cache(maxsize=4096)
def fetch_proposicao_info(id_proposicao):
    """
    Busca detalhes básicos da proposição:
    siglaTipo, número, ano, ementa.
    """
    try:
        data = safe_get(f"{BASE_URL}/proposicoes/{id_proposicao}")
        dados = data.get("dados", {})
        return {
            "sigla": str(dados.get("siglaTipo") or "").strip(),
            "numero": str(dados.get("numero") or "").strip(),
            "ano": str(dados.get("ano") or "").strip(),
            "ementa": (dados.get("ementa") or "").strip(),
        }
    except Exception:
        return {
            "sigla": "",
            "numero": "",
            "ano": "",
            "ementa": "",
        }

# ============================================================
# ACESSO À API – EVENTOS, PAUTA, AUTORIA
# ============================================================


@st.cache_data(show_spinner=False)
def fetch_eventos(start_date, end_date):
    """Busca todos os eventos da Câmara no intervalo [start_date, end_date]."""
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
        dados = data.get("dados", [])
        if not dados:
            break

        eventos.extend(dados)

        links = data.get("links", [])
        has_next = any(link.get("rel") == "next" for link in links)
        if not has_next:
            break

        pagina += 1

    return eventos


@st.cache_data(show_spinner=False)
def fetch_pauta_evento(event_id):
    """Busca a pauta de um evento da Câmara."""
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    return data.get("dados", [])


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_proposicoes_autoria_deputada(id_deputada):
    """
    Busca TODOS os IDs de proposições de autoria da deputada na API,
    usando /proposicoes?idDeputadoAutor=... com paginação.

    Resultado: set de strings com IDs de proposição.
    """
    ids = set()
    url = f"{BASE_URL}/proposicoes"
    params = {
        "idDeputadoAutor": id_deputada,
        "itens": 100,
        "ordem": "ASC",
        "ordenarPor": "id",
    }

    while True:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for d in data.get("dados", []):
            if d.get("id"):
                ids.add(str(d["id"]))

        # paginação: procura link "next"
        links = data.get("links", [])
        next_link = None
        for link in links:
            if link.get("rel") == "next":
                next_link = link.get("href")
                break

        if not next_link:
            break

        # próxima página: usamos o href completo e zeramos params
        url = next_link
        params = {}

    return ids

# ============================================================
# REGRAS DE MONITORAMENTO
# ============================================================


def pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf):
    relator = item.get("relator") or {}
    nome = relator.get("nome") or ""
    partido = relator.get("siglaPartido") or ""
    uf = relator.get("siglaUf") or ""

    return matches_deputy(
        nome,
        alvo_nome,
        partido,
        alvo_partido,
        uf,
        alvo_uf,
    )


def pauta_item_palavras_chave(item, palavras_chave_normalizadas):
    """
    Verifica se algum termo de palavras-chave aparece em textos relevantes
    do item de pauta e de todas as proposições associadas.
    """

    textos = []

    # 1. Campos diretos do item
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        valor = item.get(chave)
        if valor:
            textos.append(str(valor))

    # 2. Proposição "normal": item["proposicao"]
    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        valor = prop.get(chave)
        if valor:
            textos.append(str(valor))

    # 3. Proposição RELACIONADA
    prop_rel = item.get("proposicaoRelacionada_") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        valor = prop_rel.get(chave)
        if valor:
            textos.append(str(valor))

    texto = " ".join(textos)
    texto_norm = normalize_text(texto)

    encontradas = set()
    for kw_norm, kw_original in palavras_chave_normalizadas:
        if kw_norm and kw_norm in texto_norm:
            encontradas.add(kw_original)

    return encontradas


def is_comissao_estrategica(sigla_orgao, lista_siglas):
    """Retorna True se a comissão estiver na lista estratégica."""
    if not sigla_orgao:
        return False
    return sigla_orgao.upper() in [s.upper() for s in lista_siglas]

# ============================================================
# VARREDURA GERAL (CORE)
# ============================================================


def escanear_eventos(
    eventos,
    alvo_nome,
    alvo_partido,
    alvo_uf,
    palavras_chave,
    comissoes_estrategicas,
    apenas_reuniao_deliberativa=False,
    buscar_autoria=True,
    ids_autoria_deputada=None,
):
    """
    Percorre todos os eventos e suas pautas, gerando um DataFrame com flags.

    - Palavras-chave: avaliadas na própria pauta.
    - Relatoria: lida na própria pauta (campo relator).
    - Autoria: se buscar_autoria=True, verifica se o ID da proposição está
      no set ids_autoria_deputada (obtido via /proposicoes?idDeputadoAutor=...).
    """
    registros = []

    palavras_chave_norm = [
        (normalize_text(p), p) for p in palavras_chave if p.strip()
    ]

    ids_autoria_deputada = ids_autoria_deputada or set()

    for ev in eventos:
        desc_tipo = (ev.get("descricaoTipo") or "").lower()
        if apenas_reuniao_deliberativa and "reunião deliberativa" not in desc_tipo:
            continue

        event_id = ev.get("id") or ev.get("codEvento")
        if event_id is None:
            continue

        data_hora_ini = ev.get("dataHoraInicio") or ""
        data_str = data_hora_ini[:10] if len(data_hora_ini) >= 10 else ""
        hora_str = data_hora_ini[11:16] if len(data_hora_ini) >= 16 else ""

        descricao_evento = ev.get("descricao") or ""
        tipo_evento = ev.get("descricaoTipo") or ""

        orgaos = ev.get("orgaos") or []
        if not orgaos:
            orgaos = [{"sigla": "", "nome": "", "id": None}]

        try:
            pauta = fetch_pauta_evento(event_id)
        except Exception:
            pauta = []

        proposicoes_relatoria = set()
        proposicoes_autoria = set()
        proposicoes_keywords = set()
        palavras_evento = set()
        pares_kw_proposicao = set()  # (palavra, PL) exato

        for item in pauta:
            # Palavras-chave deste item
            kws_item = pauta_item_palavras_chave(item, palavras_chave_norm)
            has_keywords = bool(kws_item)

            # RELATORIA
            relatoria_flag = pauta_item_tem_relatoria_deputada(
                item, alvo_nome, alvo_partido, alvo_uf
            )

            # AUTORIA – via set de IDs
            autoria_flag = False
            if buscar_autoria and ids_autoria_deputada:
                id_prop_tmp = get_proposicao_id_from_item(item)
                if id_prop_tmp and id_prop_tmp in ids_autoria_deputada:
                    autoria_flag = True

            # Se não há nada de interesse, pula
            if not (relatoria_flag or autoria_flag or has_keywords):
                continue

            # Identificar proposição
            id_prop = get_proposicao_id_from_item(item)

            identificacao = "(proposição não identificada)"
            ementa_prop = ""

            if id_prop:
                info = fetch_proposicao_info(id_prop)
                if info["sigla"] and info["numero"] and info["ano"]:
                    identificacao = f"{info['sigla']} {info['numero']}/{info['ano']}"
                ementa_prop = info["ementa"]
            else:
                # fallback: tenta usar o que vier no próprio item de pauta
                prop = item.get("proposicao") or {}
                sigla = prop.get("siglaTipo") or ""
                numero = prop.get("numero") or ""
                ano = prop.get("ano") or ""
                if sigla and numero and ano:
                    identificacao = f"{sigla} {numero}/{ano}"
                ementa_prop = prop.get("ementa") or ""

            texto_completo = identificacao
            if ementa_prop:
                texto_completo = f"{identificacao} — {ementa_prop}"

            if relatoria_flag:
                proposicoes_relatoria.add(texto_completo)
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
            if has_keywords:
                # este PL tem palavras-chave
                proposicoes_keywords.add(identificacao)
                for kw in kws_item:
                    palavras_evento.add(kw)
                    pares_kw_proposicao.add((kw, identificacao))

        tem_relatoria = len(proposicoes_relatoria) > 0
        tem_autoria = len(proposicoes_autoria) > 0
        tem_keywords = len(palavras_evento) > 0

        # mapeamento exato palavra -> PL
        if pares_kw_proposicao:
            pares_ordenados = sorted(pares_kw_proposicao)
            mapa_kw_prop = "; ".join([f"{kw}||{pl}" for kw, pl in pares_ordenados])
        else:
            mapa_kw_prop = ""

        for org in orgaos:
            sigla_org = org.get("siglaOrgao") or org.get("sigla") or ""
            nome_org = org.get("nomeOrgao") or org.get("nome") or ""
            orgao_id = org.get("id")

            registro = {
                "data": data_str,
                "hora": hora_str,
                "orgao_id": orgao_id,
                "orgao_sigla": sigla_org,
                "orgao_nome": nome_org,
                "id_evento": event_id,
                "tipo_evento": tipo_evento,
                "descricao_evento": descricao_evento,
                "tem_relatoria_deputada": tem_relatoria,
                "proposicoes_relatoria": "; ".join(sorted(proposicoes_relatoria)) if proposicoes_relatoria else "",
                "tem_autoria_deputada": tem_autoria,
                "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)) if proposicoes_autoria else "",
                "tem_palavras_chave": tem_keywords,
                "palavras_chave_encontradas": "; ".join(sorted(palavras_evento)) if palavras_evento else "",
                "proposicoes_palavras_chave": "; ".join(sorted(proposicoes_keywords)) if proposicoes_keywords else "",
                "mapeamento_kw_proposicao": mapa_kw_prop,  # NOVO: pares exatos
                "comissao_estrategica": is_comissao_estrategica(sigla_org, comissoes_estrategicas),
            }
            registros.append(registro)

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values(["data", "hora", "orgao_sigla", "id_evento"])
    return df

# ============================================================
# INTERFACE STREAMLIT
# ============================================================


def main():
    st.set_page_config(
        page_title="Sistema de Monitoramento – Dep. Júlia Zanatta",
        layout="wide",
    )

    st.title("📡 Sistema de Monitoramento Legislativo – Gab Julia Zanatta")
    st.markdown(
        """
        Este painel monitora:
        1. **Matérias de autoria ou relatoria da Dep. Júlia Zanatta**  
        2. **Matérias de todas as comissões com termos sensíveis**  
        3. **Matérias de comissões estratégicas selecionadas**  
        """
    )

    # ---------------- Sidebar ----------------
    with st.sidebar:
        st.header("⚙️ Configurações")

        hoje = datetime.date.today()
        default_inicio = hoje
        default_fim = hoje + datetime.timedelta(days=7)

        date_range = st.date_input(
            "Intervalo de datas",
            value=(default_inicio, default_fim),
            format="DD/MM/YYYY",
        )

        if isinstance(date_range, tuple):
            dt_inicio, dt_fim = date_range
        else:
            dt_inicio = date_range
            dt_fim = date_range

        if dt_inicio > dt_fim:
            st.error("Data inicial não pode ser maior que a data final.")
            return

        dias_intervalo = (dt_fim - dt_inicio).days + 1
        if dias_intervalo > 14:
            st.warning(
                f"Intervalo de {dias_intervalo} dias — isso pode deixar a consulta mais lenta. "
                "Se possível, reduza a janela para 1 semana."
            )

        st.markdown("---")
        st.subheader("Deputada monitorada")

        alvo_nome = st.text_input("Nome", value=DEPUTADA_NOME_PADRAO)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            alvo_partido = st.text_input("Partido", value=DEPUTADA_PARTIDO_PADRAO)
        with col2:
            alvo_uf = st.text_input("UF", value=DEPUTADA_UF_PADRAO)
        with col3:
            id_dep_str = st.text_input("ID (Dados Abertos)", value=str(DEPUTADA_ID_PADRAO))
        try:
            id_deputada = int(id_dep_str)
        except ValueError:
            st.error("ID da deputada inválido. Use apenas números.")
            return

        st.markdown("---")
        st.subheader("Palavras-chave (todas as comissões)")
        palavras_str = st.text_area(
            "Uma por linha",
            value="\n".join(PALAVRAS_CHAVE_PADRAO),
            height=150,
        )
        palavras_lista = [p.strip() for p in palavras_str.splitlines() if p.strip()]

        st.markdown("---")
        st.subheader("Comissões estratégicas")
        comissoes_str = st.text_area(
            "Siglas das comissões (uma por linha)",
            value="\n".join(COMISSOES_ESTRATEGICAS_PADRAO),
            height=120,
        )
        comissoes_lista = [c.strip().upper() for c in comissoes_str.splitlines() if c.strip()]

        st.markdown("---")
        apenas_delib = st.checkbox(
            "Considerar apenas **Reuniões Deliberativas**",
            value=False,
        )

        buscar_autoria = st.checkbox(
            "Verificar AUTORIA da deputada (recomendado)",
            value=True,
        )

        st.markdown("---")
        bt_rodar = st.button("🔍 Rodar monitoramento", type="primary")

    if not bt_rodar:
        st.info("Configure os filtros na barra lateral e clique em **🔍 Rodar monitoramento**.")
        return

    # ---------------- Execução ----------------
    with st.spinner("Consultando Dados Abertos da Câmara e analisando pautas..."):
        try:
            eventos = fetch_eventos(dt_inicio, dt_fim)
        except Exception as e:
            st.error(f"Erro ao buscar eventos na API da Câmara: {e}")
            return

        # Para AUTORIA: lista de proposições da deputada (uma vez, cacheada)
        ids_autoria = set()
        if buscar_autoria:
            try:
                with st.spinner("Buscando lista de proposições de AUTORIA da deputada..."):
                    ids_autoria = fetch_proposicoes_autoria_deputada(id_deputada)
            except Exception as e:
                st.warning(
                    "Não foi possível buscar lista de proposições de autoria. "
                    f"Autoria pode ficar incompleta.\n\nErro: {e}"
                )
                ids_autoria = set()

        df = escanear_eventos(
            eventos=eventos,
            alvo_nome=alvo_nome,
            alvo_partido=alvo_partido,
            alvo_uf=alvo_uf,
            palavras_chave=palavras_lista,
            comissoes_estrategicas=comissoes_lista,
            apenas_reuniao_deliberativa=apenas_delib,
            buscar_autoria=buscar_autoria,
            ids_autoria_deputada=ids_autoria,
        )

    if df.empty:
        st.warning("Nenhum evento encontrado no período com os critérios atuais.")
        return

    # ---------------- KPIs gerais ----------------
    total_eventos = len(df["id_evento"].unique())
    total_autoria = df["tem_autoria_deputada"].sum()
    total_relatoria = df["tem_relatoria_deputada"].sum()
    total_keywords = df["tem_palavras_chave"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Eventos de comissão (intervalo)", total_eventos)
    k2.metric("Eventos c/ AUTORIA da deputada", int(total_autoria))
    k3.metric("Eventos c/ RELATORIA da deputada", int(total_relatoria))
    k4.metric("Eventos com palavras-chave", int(total_keywords))

    # ---------------- Abas ----------------
    tab1, tab2, tab3 = st.tabs(
        [
            "1️⃣ Autoria/Relatoria da Deputada",
            "2️⃣ Palavras-chave em qualquer comissão",
            "3️⃣ Comissões estratégicas",
        ]
    )

    # --------- TAB 1: Autoria/Relatoria JZ ---------
    with tab1:
        st.subheader("Matérias de autoria ou relatoria da Deputada")

        df_jz = df[(df["tem_autoria_deputada"]) | (df["tem_relatoria_deputada"])].copy()
        if df_jz.empty:
            st.info("Nenhum evento com autoria ou relatoria da deputada no período.")
        else:
            st.caption(f"Total de linhas (evento x órgão): {len(df_jz)}")

            df_jz_show = df_jz[
                [
                    "data",
                    "hora",
                    "orgao_id",
                    "orgao_sigla",
                    "orgao_nome",
                    "id_evento",
                    "tipo_evento",
                    "tem_autoria_deputada",
                    "proposicoes_autoria",
                    "tem_relatoria_deputada",
                    "proposicoes_relatoria",
                    "descricao_evento",
                ]
            ].rename(
                columns={
                    "data": "Data",
                    "hora": "Hora",
                    "orgao_id": "ID órgão",
                    "orgao_sigla": "Órgão (sigla)",
                    "orgao_nome": "Órgão (nome)",
                    "id_evento": "ID evento",
                    "tipo_evento": "Tipo de evento",
                    "tem_autoria_deputada": "Tem AUTORIA da deputada?",
                    "proposicoes_autoria": "Proposições (autoria)",
                    "tem_relatoria_deputada": "Tem RELATORIA da deputada?",
                    "proposicoes_relatoria": "Proposições (relatoria)",
                    "descricao_evento": "Descrição evento",
                }
            )

            # formata data dd/mm/aaaa
            df_jz_show["Data"] = pd.to_datetime(
                df_jz_show["Data"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

            # 1 LINHA POR PROJETO NA RELATORIA
            df_jz_show["Proposições (relatoria)"] = df_jz_show["Proposições (relatoria)"].fillna("")
            df_jz_show["Proposições (relatoria)"] = df_jz_show["Proposições (relatoria)"].apply(
                lambda x: [s.strip() for s in str(x).split(";") if s.strip()] or [""]
            )
            df_jz_show = df_jz_show.explode("Proposições (relatoria)")

            st.dataframe(df_jz_show, use_container_width=True, hide_index=True)

            csv_jz = df_jz_show.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV – Autoria/Relatoria",
                data=csv_jz,
                file_name=f"monitor_autoria_relatoria_{dt_inicio}_{dt_fim}.csv",
                mime="text/csv",
            )

    # --------- TAB 2: Palavras-chave ---------
    with tab2:
        st.subheader("Matérias com palavras-chave sensíveis (todas as comissões)")

        df_kw = df[df["tem_palavras_chave"] == True].copy()

        if df_kw.empty:
            st.info("Nenhuma matéria com palavras-chave sensíveis encontrada no intervalo selecionado.")
        else:
            df_kw_show = df_kw[
                [
                    "data",
                    "hora",
                    "orgao_sigla",
                    "orgao_nome",
                    "id_evento",
                    "tipo_evento",
                    "mapeamento_kw_proposicao",
                    "tem_autoria_deputada",
                    "proposicoes_autoria",
                    "tem_relatoria_deputada",
                    "proposicoes_relatoria",
                    "descricao_evento",
                ]
            ].rename(
                columns={
                    "data": "Data",
                    "hora": "Hora",
                    "orgao_sigla": "Órgão (sigla)",
                    "orgao_nome": "Órgão (nome)",
                    "id_evento": "ID evento",
                    "tipo_evento": "Tipo de evento",
                    "mapeamento_kw_proposicao": "MapaKWPL",
                    "tem_autoria_deputada": "Tem AUTORIA da deputada?",
                    "proposicoes_autoria": "Proposições (autoria)",
                    "tem_relatoria_deputada": "Tem RELATORIA da deputada?",
                    "proposicoes_relatoria": "Proposições (relatoria)",
                    "descricao_evento": "Descrição evento",
                }
            )

            # formata data dd/mm/aaaa
            df_kw_show["Data"] = pd.to_datetime(
                df_kw_show["Data"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

            # MapaKWPL = "palavra||PL 1234/2024; outra||PL 5678/2025"
            df_kw_show["MapaKWPL"] = df_kw_show["MapaKWPL"].fillna("").apply(
                lambda x: [s.strip() for s in str(x).split(";") if s.strip()] or [""]
            )

            df_kw_show = df_kw_show.explode("MapaKWPL")

            def split_pair(s):
                parts = str(s).split("||", 1)
                if len(parts) == 2:
                    return parts[0], parts[1]
                return "", s

            df_kw_show[["Palavras-chave encontradas", "Proposições (palavras-chave)"]] = pd.DataFrame(
                df_kw_show["MapaKWPL"].apply(split_pair).tolist(),
                index=df_kw_show.index,
            )

            df_kw_show = df_kw_show.drop(columns=["MapaKWPL"])

            # reordena colunas: Data, Hora, Órgão (sigla), Palavra, PL, resto
            cols_order = [
                "Data",
                "Hora",
                "Órgão (sigla)",
                "Palavras-chave encontradas",
                "Proposições (palavras-chave)",
                "Órgão (nome)",
                "ID evento",
                "Tipo de evento",
                "Tem AUTORIA da deputada?",
                "Proposições (autoria)",
                "Tem RELATORIA da deputada?",
                "Proposições (relatoria)",
                "Descrição evento",
            ]
            df_kw_show = df_kw_show[cols_order]

            st.dataframe(df_kw_show, use_container_width=True, hide_index=True)

            csv_kw = df_kw_show.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV – Palavras-chave",
                data=csv_kw,
                file_name=f"monitor_palavras_chave_{dt_inicio}_{dt_fim}.csv",
                mime="text/csv",
            )

    # --------- TAB 3: Comissões estratégicas ---------
    with tab3:
        st.subheader("Matérias das comissões estratégicas")

        df_com = df[df["comissao_estrategica"]].copy()
        if df_com.empty:
            st.info("Nenhum evento de comissão estratégica no período.")
        else:
            st.caption(f"Total de linhas (evento x órgão): {len(df_com)}")

            df_com_show = df_com[
                [
                    "data",
                    "hora",
                    "orgao_sigla",
                    "orgao_nome",
                    "id_evento",
                    "tipo_evento",
                    "tem_autoria_deputada",
                    "proposicoes_autoria",
                    "tem_relatoria_deputada",
                    "proposicoes_relatoria",
                    "tem_palavras_chave",
                    "palavras_chave_encontradas",
                    "proposicoes_palavras_chave",
                    "descricao_evento",
                ]
            ].rename(
                columns={
                    "data": "Data",
                    "hora": "Hora",
                    "orgao_sigla": "Órgão (sigla)",
                    "orgao_nome": "Órgão (nome)",
                    "id_evento": "ID evento",
                    "tipo_evento": "Tipo de evento",
                    "tem_autoria_deputada": "Tem AUTORIA da deputada?",
                    "proposicoes_autoria": "Proposições (autoria)",
                    "tem_relatoria_deputada": "Tem RELATORIA da deputada?",
                    "proposicoes_relatoria": "Proposições (relatoria)",
                    "tem_palavras_chave": "Tem palavras-chave?",
                    "palavras_chave_encontradas": "Palavras-chave encontradas",
                    "proposicoes_palavras_chave": "Proposições (palavras-chave)",
                    "descricao_evento": "Descrição evento",
                }
            )

            # formata data dd/mm/aaaa
            df_com_show["Data"] = pd.to_datetime(
                df_com_show["Data"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

            st.dataframe(df_com_show, use_container_width=True, hide_index=True)

            csv_com = df_com_show.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV – Comissões estratégicas",
                data=csv_com,
                file_name=f"monitor_comissoes_estrategicas_{dt_inicio}_{dt_fim}.csv",
                mime="text/csv",
            )

    st.caption(
        "Dados: API de Dados Abertos da Câmara dos Deputados "
        "(/eventos, /eventos/{id}/pauta, /proposicoes, /proposicoes/{id})."
    )


if __name__ == "__main__":
    main()
