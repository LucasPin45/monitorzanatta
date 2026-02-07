# core/data_provider.py
"""
Camada central de dados do app.
- UI chama DataProvider
- DataProvider chama Services (CamaraService / SenadoService)
- Cache Streamlit fica aqui (centralizado)
"""
from __future__ import annotations

import concurrent.futures
import datetime
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import streamlit as st

from core.services.camara_service import CamaraService
from core.services.senado_service import SenadoService
from core.utils.formatters import format_sigla_num_ano
from core.utils.text_utils import canonical_situacao, normalize_ministerio
from core.utils.links import camara_link_tramitacao, camara_link_deputado
from core.utils.date_utils import (
    parse_dt,
    days_since,
    fmt_dt_br,
    parse_prazo_resposta_ric,
)

# Imports para Tab 2 - Pauta
from core.services.pauta_service import (
    escanear_eventos,
    fetch_proposicao_info_cached,
)


@dataclass(frozen=True)
class ProviderConfig:
    ttl_seconds: int = 900  # 15 min


class DataProvider:
    """
    Camada central de dados do app.
    """

    def __init__(self, cfg: Optional[ProviderConfig] = None):
        self.cfg = cfg or ProviderConfig()
        self.camara = CamaraService()
        self.senado = SenadoService()

    def _ttl(self) -> int:
        return int(self.cfg.ttl_seconds)

    # ---------------------------------------------------------------------
    # PERFIL
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_perfil_deputada(_self) -> Dict[str, Any]:
        return {
            "nome": "Júlia Zanatta",
            "partido": "PL",
            "uf": "SC",
        }

    def get_perfil_deputada(self) -> Dict[str, Any]:
        return self._cached_get_perfil_deputada()

    # ---------------------------------------------------------------------
    # AUTORIA / PROPOSIÇÕES
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_proposicoes_autoria(_self, id_deputada: int) -> List[Dict[str, Any]]:
        return _self.camara.get_proposicoes_autoria(id_deputada)

    def get_proposicoes_autoria(self, id_deputada: int) -> List[Dict[str, Any]]:
        return self._cached_get_proposicoes_autoria(id_deputada)

    # ---------------------------------------------------------------------
    # UTIL: contar tipos
    # ---------------------------------------------------------------------

    def contar_tipos(self, props_autoria: List[Dict[str, Any]]) -> Dict[str, int]:
        tipos_count: Dict[str, int] = {}
        if not props_autoria:
            return tipos_count

        for p in props_autoria:
            if not isinstance(p, dict):
                continue
            tipo = p.get("siglaTipo") or p.get("tipo") or p.get("sigla_tipo")
            if not tipo:
                continue
            tipos_count[str(tipo)] = tipos_count.get(str(tipo), 0) + 1

        return tipos_count

    # ---------------------------------------------------------------------
    # TRAMITAÇÕES
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_tramitacoes(_self, id_proposicao: str) -> List[Dict[str, Any]]:
        return _self.camara.get_tramitacoes(id_proposicao)

    def get_tramitacoes(self, id_proposicao: str) -> List[Dict[str, Any]]:
        return self._cached_get_tramitacoes(id_proposicao)

    # ---------------------------------------------------------------------
    # PROPOSIÇÃO COMPLETA
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_proposicao_completa(_self, id_proposicao: str) -> Dict[str, Any]:
        return _self.camara.get_proposicao_completa(id_proposicao)

    def get_proposicao_completa(self, id_proposicao: str) -> Dict[str, Any]:
        return self._cached_get_proposicao_completa(id_proposicao)

    # ---------------------------------------------------------------------
    # RICs - BUSCA BÁSICA
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_get_rics_autoria(_self, id_deputada: int) -> List[Dict[str, Any]]:
        return _self.camara.listar_rics_autoria(id_deputada)

    def get_rics_autoria(self, id_deputada: int) -> List[Dict[str, Any]]:
        return self._cached_get_rics_autoria(id_deputada)

    # ---------------------------------------------------------------------
    # RICs - FETCH COM DATAFRAME (para Aba 7)
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_fetch_rics_por_autor(_self, id_deputada: int) -> pd.DataFrame:
        """
        Busca RICs de autoria e retorna como DataFrame.
        """
        rics = _self.camara.listar_rics_autoria(id_deputada)
        
        if not rics:
            return pd.DataFrame()
        
        rows = []
        for d in rics:
            rows.append({
                "id": str(d.get("id") or ""),
                "siglaTipo": (d.get("siglaTipo") or "").strip(),
                "numero": str(d.get("numero") or "").strip(),
                "ano": str(d.get("ano") or "").strip(),
                "ementa": (d.get("ementa") or "").strip(),
                "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
            })
        
        return pd.DataFrame(rows)

    def fetch_rics_por_autor(self, id_deputada: int) -> pd.DataFrame:
        return self._cached_fetch_rics_por_autor(id_deputada)

    # ---------------------------------------------------------------------
    # RICs - BUILD STATUS MAP (com lógica específica de RIC)
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=900, show_spinner=False)
    def _cached_build_status_map_rics(_self, ids: tuple) -> Dict[str, Dict[str, Any]]:
        """
        Constrói mapa de status para RICs com informações de prazo.
        """
        out: Dict[str, Dict[str, Any]] = {}
        ids_list = [str(x) for x in (ids or []) if str(x).strip()]
        
        if not ids_list:
            return out

        def _one(pid: str):
            dados_completos = _self.camara.get_proposicao_completa(pid)
            
            situacao = canonical_situacao(dados_completos.get("status_descricaoSituacao", ""))
            andamento = dados_completos.get("status_descricaoTramitacao", "")
            relator_info = dados_completos.get("relator", {})
            tramitacoes = dados_completos.get("tramitacoes", [])
            sigla_tipo = dados_completos.get("sigla", "")
            ementa = dados_completos.get("ementa", "")
            
            # Formatar relator
            relator_txt = ""
            relator_id = ""
            if relator_info and relator_info.get("nome"):
                nome = relator_info.get("nome", "")
                partido = relator_info.get("partido", "")
                uf = relator_info.get("uf", "")
                relator_id = str(relator_info.get("id_deputado", ""))
                if partido or uf:
                    relator_txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
                else:
                    relator_txt = nome
            
            resultado = {
                "situacao": situacao,
                "andamento": andamento,
                "status_dataHora": dados_completos.get("status_dataHora", ""),
                "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
                "relator": relator_txt,
                "relator_id": relator_id,
                "sigla_tipo": sigla_tipo,
                "ementa": ementa,
            }
            
            # Lógica específica de RIC
            if sigla_tipo == "RIC":
                prazo_info = parse_prazo_resposta_ric(tramitacoes, situacao)
                resultado.update({
                    "ric_data_remessa": prazo_info.get("data_remessa"),
                    "ric_inicio_contagem": prazo_info.get("inicio_contagem"),
                    "ric_prazo_inicio": prazo_info.get("prazo_inicio"),
                    "ric_prazo_fim": prazo_info.get("prazo_fim"),
                    "ric_prazo_str": prazo_info.get("prazo_str", ""),
                    "ric_dias_restantes": prazo_info.get("dias_restantes"),
                    "ric_fonte_prazo": prazo_info.get("fonte_prazo", ""),
                    "ric_status_resposta": prazo_info.get("status_resposta"),
                    "ric_data_resposta": prazo_info.get("data_resposta"),
                    "ric_respondido": prazo_info.get("respondido", False),
                    "ric_ministerio": _self._extrair_ministerio_ric(ementa, tramitacoes),
                    "ric_assunto": _self._extrair_assunto_ric(ementa),
                })
            
            return pid, resultado

        max_workers = 10 if len(ids_list) >= 40 else 6
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for pid, payload in ex.map(_one, ids_list):
                out[str(pid)] = payload

        return out

    def build_status_map_rics(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        # Converter para tuple para ser hashable no cache
        return self._cached_build_status_map_rics(tuple(ids))

    # ---------------------------------------------------------------------
    # RICs - ENRIQUECER DATAFRAME COM STATUS
    # ---------------------------------------------------------------------

    def enrich_rics_with_status(self, df_base: pd.DataFrame, status_map: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        Enriquece DataFrame de RICs com informações de status.
        """
        df = df_base.copy()
        
        # Mapeamentos básicos
        df["Situação atual"] = df["id"].astype(str).map(lambda x: canonical_situacao(status_map.get(str(x), {}).get("situacao", "")))
        df["Andamento (status)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("andamento", ""))
        df["Data do status (raw)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("status_dataHora", ""))
        df["Órgão (sigla)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("siglaOrgao", ""))
        df["Relator(a)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("relator", "—"))
        df["Relator_ID"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("relator_id", ""))

        # Normalizações
        df["Situação atual"] = df["Situação atual"].replace({
            "Aguardando Parecer do Relator(a)": "Aguardando Parecer",
            "Aguardando Parecer do Relator(a).": "Aguardando Parecer",
        })
        
        def _is_blankish(v):
            if pd.isna(v):
                return True
            s = str(v).strip()
            return s in ("", "-", "—", "–")
        
        df.loc[df["Situação atual"].apply(_is_blankish), "Situação atual"] = "Em providência Interna"

        # Link do relator
        def _link_relator(row):
            relator_id = row.get("Relator_ID", "")
            if relator_id and str(relator_id).strip() not in ('', 'nan', 'None'):
                return camara_link_deputado(relator_id)
            return ""
        df["LinkRelator"] = df.apply(_link_relator, axis=1)

        # Datas
        dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
        df["DataStatus_dt"] = dt
        df["Data do status"] = dt.apply(fmt_dt_br)
        df["AnoStatus"] = dt.dt.year
        df["MesStatus"] = dt.dt.month
        df["Parado (dias)"] = df["DataStatus_dt"].apply(days_since)
        
        # Link tramitação
        df["LinkTramitacao"] = df["id"].astype(str).apply(camara_link_tramitacao)
        
        # Dados específicos de RIC
        df["RIC_DataRemessa"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_data_remessa"))
        df["RIC_InicioContagem"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_inicio_contagem"))
        df["RIC_PrazoInicio"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_inicio"))
        df["RIC_PrazoFim"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_fim"))
        df["RIC_PrazoStr"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_prazo_str", ""))
        df["RIC_DiasRestantes"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_dias_restantes"))
        df["RIC_FontePrazo"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_fonte_prazo", ""))
        df["RIC_StatusResposta"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_status_resposta", ""))
        df["RIC_DataResposta"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_data_resposta"))
        df["RIC_Respondido"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_respondido", False))
        df["RIC_Ministerio"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_ministerio", ""))
        df["RIC_Assunto"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("ric_assunto", ""))

        # Sinal de alerta
        def _sinal(d):
            try:
                if d is None or pd.isna(d):
                    return "—"
                d = int(d)
                if d >= 30:
                    return "🔴"
                if d >= 15:
                    return "🟠"
                if d >= 7:
                    return "🟡"
                return "🟢"
            except Exception:
                return "—"

        df["Sinal"] = df["Parado (dias)"].apply(_sinal)
        
        # Ordenar por data mais recente
        df = df.sort_values("DataStatus_dt", ascending=False)
        
        return df

    # ---------------------------------------------------------------------
    # FUNÇÕES AUXILIARES INTERNAS PARA RIC
    # ---------------------------------------------------------------------

    def _extrair_ministerio_ric(self, ementa: str, tramitacoes: list = None) -> str:
        """Extrai ministério destinatário de um RIC."""
        if not ementa:
            ementa = ""
        
        ementa_lower = ementa.lower()
        
        patterns = [
            r"ministr[oa]\s+(?:de\s+estado\s+)?(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre|acerca|a\s+respeito)",
            r"ministério\s+(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre|acerca|a\s+respeito)",
            r"sr[ªa]?\.\s+ministr[oa]\s+([^,\.;]+?)(?:,|\.|;|sobre)",
            r"senhor[a]?\s+ministr[oa]\s+(?:d[oa]s?\s+)?([^,\.;]+?)(?:,|\.|;|sobre)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ementa_lower)
            if match:
                ministerio = match.group(1).strip()
                normalizado = normalize_ministerio(ministerio)
                if normalizado and normalizado != "Não identificado":
                    return normalizado
        
        ministerio_direto = normalize_ministerio(ementa)
        if ministerio_direto and ministerio_direto != "Não identificado":
            return ministerio_direto
        
        if tramitacoes:
            for t in tramitacoes:
                sigla = (t.get("siglaOrgao") or "").upper()
                if "1SEC" in sigla:
                    despacho = t.get("despacho") or ""
                    desc = t.get("descricaoTramitacao") or ""
                    texto = f"{despacho} {desc}"
                    ministerio_tram = normalize_ministerio(texto)
                    if ministerio_tram and ministerio_tram != "Não identificado":
                        return ministerio_tram
        
        return "Não identificado"

    def _extrair_assunto_ric(self, ementa: str) -> str:
        """Extrai assunto/tema de um RIC."""
        if not ementa:
            return ""
        
        ementa_lower = ementa.lower()
        
        assuntos = {
            "Correios/ECT": ["correios", "ect", "empresa de correios"],
            "Agricultura/Agronegócio": ["arroz", "leite", "agro", "agricultura", "pecuária", "soja", "milho", "rural"],
            "Saúde/Vacinas": ["vacina", "vacinação", "imunizante", "sus", "saúde", "medicamento", "anvisa"],
            "Segurança Pública": ["polícia", "policia", "arma", "segurança", "crime", "prisão", "presídio"],
            "Educação": ["escola", "ensino", "educação", "universidade", "mec", "enem"],
            "Economia/Finanças": ["imposto", "pix", "drex", "banco", "receita", "tributo", "economia"],
            "Direitos Humanos": ["direitos humanos", "conanda", "criança", "adolescente", "indígena"],
            "Meio Ambiente": ["ambiente", "clima", "floresta", "ibama", "desmatamento"],
            "Comunicações/Tecnologia": ["internet", "tecnologia", "telecom", "comunicação", "digital"],
            "Relações Exteriores": ["exterior", "internacional", "embaixada", "diplomacia"],
            "Defesa/Militar": ["defesa", "militar", "exército", "forças armadas"],
            "Transportes": ["transporte", "rodovia", "ferrovia", "estrada", "aeroporto"],
            "Assistência Social": ["bolsa família", "assistência", "fome", "pobreza"],
        }
        
        for assunto, keywords in assuntos.items():
            for kw in keywords:
                if kw in ementa_lower:
                    return assunto
        
        return ""

    # ---------------------------------------------------------------------
    # TAB 2 - PAUTA (EVENTOS E AUTORIA/RELATORIA)
    # ---------------------------------------------------------------------

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached_get_eventos(_self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """
        Busca eventos da Câmara no período especificado.
        Cache: 1 hora (eventos podem mudar ao longo do dia).
        """
        import requests
        
        eventos = []
        pagina = 1
        base_url = "https://dadosabertos.camara.leg.br/api/v2"
        
        while True:
            params = {
                "dataInicio": start_date.strftime("%Y-%m-%d"),
                "dataFim": end_date.strftime("%Y-%m-%d"),
                "pagina": pagina,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "dataHoraInicio",
            }
            
            try:
                response = requests.get(f"{base_url}/eventos", params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[ERRO] get_eventos: {e}")
                break
            
            dados = data.get("dados", [])
            if not dados:
                break
            
            eventos.extend(dados)
            
            # Verificar se há próxima página
            links = data.get("links", [])
            if not any(link.get("rel") == "next" for link in links):
                break
            
            pagina += 1
        
        return eventos

    def get_eventos(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """
        Busca eventos da Câmara em um período.
        
        Args:
            start_date: Data inicial (inclusive)
            end_date: Data final (inclusive)
            
        Returns:
            Lista de eventos (cada evento é um dict)
        """
        return self._cached_get_eventos(start_date, end_date)

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached_get_ids_autoria_deputada(_self, id_deputada: int) -> Set[str]:
        """
        Busca IDs de todas as proposições de autoria da deputada.
        Cache: 1 hora.
        """
        import requests
        
        ids = set()
        base_url = "https://dadosabertos.camara.leg.br/api/v2"
        url = f"{base_url}/proposicoes"
        
        params = {
            "idDeputadoAutor": id_deputada,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "id"
        }
        
        while True:
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[ERRO] get_ids_autoria_deputada: {e}")
                break
            
            for d in data.get("dados", []):
                if d.get("id"):
                    ids.add(str(d["id"]))
            
            # Verificar próxima página
            next_link = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_link = link.get("href")
                    break
            
            if not next_link:
                break
            
            url = next_link
            params = {}  # Próxima URL já tem todos os parâmetros
        
        return ids

    def get_ids_autoria_deputada(self, id_deputada: int) -> Set[str]:
        """
        Retorna set de IDs de proposições de autoria da deputada.
        
        Args:
            id_deputada: ID da deputada na API da Câmara
            
        Returns:
            Set de IDs (strings)
        """
        return self._cached_get_ids_autoria_deputada(id_deputada)

    def escanear_eventos_pauta(
        self,
        eventos: List[Dict[str, Any]],
        nome_deputada: str,
        partido_deputada: str,
        uf_deputada: str,
        ids_autoria_deputada: Optional[Set[str]] = None,
    ) -> pd.DataFrame:
        """
        Escaneia eventos buscando proposições de autoria ou relatoria da deputada.
        
        Args:
            eventos: Lista de eventos (retorno de get_eventos)
            nome_deputada: Nome da deputada
            partido_deputada: Sigla do partido
            uf_deputada: UF
            ids_autoria_deputada: Set de IDs de proposições de autoria (opcional)
            
        Returns:
            DataFrame com eventos filtrados
        """
        # Importar aqui para evitar circular import
        from core.config import COMISSOES_ESTRATEGICAS_PADRAO
        
        return escanear_eventos(
            eventos=eventos,
            alvo_nome=nome_deputada,
            alvo_partido=partido_deputada,
            alvo_uf=uf_deputada,
            palavras_chave=[],  # Sem palavras-chave (Tab 2)
            comissoes_estrategicas=COMISSOES_ESTRATEGICAS_PADRAO,
            ids_autoria_deputada=ids_autoria_deputada or set(),
        )

    def escanear_eventos_palavras_chave(
        self,
        eventos: List[Dict[str, Any]],
        nome_deputada: str,
        partido_deputada: str,
        uf_deputada: str,
        palavras_chave: List[str],
        ids_autoria_deputada: Optional[Set[str]] = None,
    ) -> pd.DataFrame:
        """
        Escaneia eventos buscando proposições com palavras-chave específicas.
        
        Args:
            eventos: Lista de eventos (retorno de get_eventos)
            nome_deputada: Nome da deputada
            partido_deputada: Sigla do partido
            uf_deputada: UF
            palavras_chave: Lista de palavras-chave a buscar
            ids_autoria_deputada: Set de IDs de proposições de autoria (opcional)
            
        Returns:
            DataFrame com eventos contendo as palavras-chave
        """
        # Importar aqui para evitar circular import
        from core.config import COMISSOES_ESTRATEGICAS_PADRAO
        
        return escanear_eventos(
            eventos=eventos,
            alvo_nome=nome_deputada,
            alvo_partido=partido_deputada,
            alvo_uf=uf_deputada,
            palavras_chave=palavras_chave,
            comissoes_estrategicas=COMISSOES_ESTRATEGICAS_PADRAO,
            ids_autoria_deputada=ids_autoria_deputada or set(),
        )

    def escanear_eventos_comissoes(
        self,
        eventos: List[Dict[str, Any]],
        nome_deputada: str,
        partido_deputada: str,
        uf_deputada: str,
        comissoes_estrategicas: List[str],
        ids_autoria_deputada: Optional[Set[str]] = None,
    ) -> pd.DataFrame:
        """
        Escaneia eventos buscando eventos em comissões estratégicas específicas.
        
        Args:
            eventos: Lista de eventos (retorno de get_eventos)
            nome_deputada: Nome da deputada
            partido_deputada: Sigla do partido
            uf_deputada: UF
            comissoes_estrategicas: Lista de siglas de comissões estratégicas
            ids_autoria_deputada: Set de IDs de proposições de autoria (opcional)
            
        Returns:
            DataFrame com eventos das comissões estratégicas
        """
        return escanear_eventos(
            eventos=eventos,
            alvo_nome=nome_deputada,
            alvo_partido=partido_deputada,
            alvo_uf=uf_deputada,
            palavras_chave=[],  # Sem palavras-chave (Tab 4)
            comissoes_estrategicas=comissoes_estrategicas,
            ids_autoria_deputada=ids_autoria_deputada or set(),
        )

    def get_proposicao_info(self, id_proposicao: str) -> Dict[str, Any]:
        """
        Busca informações básicas de uma proposição.
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dict com: id, sigla, numero, ano, ementa
        """
        return fetch_proposicao_info_cached(id_proposicao)

    # ---------------------------------------------------------------------
    # TAB 5 - BUSCAR PROPOSIÇÕES
    # ---------------------------------------------------------------------

    def fetch_proposicoes_autoria(self, id_deputada: int) -> pd.DataFrame:
        """
        Busca proposições de autoria da deputada.
        
        Combina proposições gerais e RICs em um único DataFrame.
        
        Args:
            id_deputada: ID da deputada
            
        Returns:
            DataFrame com: id, Proposicao, siglaTipo, numero, ano, ementa
        """
        # Importar funções necessárias
        from monitor_sistema_jz import (
            fetch_lista_proposicoes_autoria_geral,
            fetch_rics_por_autor,
            format_sigla_num_ano
        )
        
        # Buscar proposições gerais
        df1 = fetch_lista_proposicoes_autoria_geral(id_deputada)
        # Buscar RICs
        df2 = fetch_rics_por_autor(id_deputada)
        
        if df1.empty and df2.empty:
            return pd.DataFrame(
                columns=["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"]
            )
        
        # Combinar
        df = pd.concat([df1, df2], ignore_index=True)
        
        # Garantir coluna Proposicao
        if "Proposicao" not in df.columns:
            df["Proposicao"] = ""
        
        # Preencher Proposicao vazia
        mask = df["Proposicao"].isna() | (df["Proposicao"].astype(str).str.strip() == "")
        if mask.any():
            df.loc[mask, "Proposicao"] = df.loc[mask].apply(
                lambda r: format_sigla_num_ano(
                    r.get("siglaTipo"),
                    r.get("numero"),
                    r.get("ano")
                ),
                axis=1
            )
        
        # Remover duplicatas
        df = df.drop_duplicates(subset=["id"], keep="first")
        
        # Garantir colunas
        cols = ["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"]
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        
        return df[cols]

    @st.cache_data(show_spinner=False, ttl=900)
    def build_proposicoes_status_map(_self, ids: List[str]) -> Dict:
        """
        Constrói mapa de status para proposições.
        
        Busca status, andamento, relator, órgão para cada proposição.
        Para RICs, busca também informações de prazo.
        
        Args:
            ids: Lista de IDs de proposições
            
        Returns:
            Dict mapeando ID → dados de status
        """
        # Importar funções necessárias
        from monitor_sistema_jz import (
            fetch_proposicao_completa,
            canonical_situacao,
            parse_prazo_resposta_ric,
            extrair_ministerio_ric,
            extrair_assunto_ric
        )
        import concurrent.futures
        
        out: Dict = {}
        ids = [str(x) for x in (ids or []) if str(x).strip()]
        if not ids:
            return out
        
        def _one(pid: str):
            dados_completos = fetch_proposicao_completa(pid)
            
            situacao = canonical_situacao(
                dados_completos.get("status_descricaoSituacao", "")
            )
            andamento = dados_completos.get("status_descricaoTramitacao", "")
            relator_info = dados_completos.get("relator", {})
            tramitacoes = dados_completos.get("tramitacoes", [])
            sigla_tipo = dados_completos.get("sigla", "")
            ementa = dados_completos.get("ementa", "")
            
            # Formatar relator
            relator_txt = ""
            relator_id = ""
            if relator_info and relator_info.get("nome"):
                nome = relator_info.get("nome", "")
                partido = relator_info.get("partido", "")
                uf = relator_info.get("uf", "")
                relator_id = str(relator_info.get("id_deputado", ""))
                if partido or uf:
                    relator_txt = f"{nome} ({partido}/{uf})".replace(
                        "//", "/"
                    ).replace("(/", "(").replace("/)", ")")
                else:
                    relator_txt = nome
            
            # Resultado base
            resultado = {
                "situacao": situacao,
                "andamento": andamento,
                "status_dataHora": dados_completos.get("status_dataHora", ""),
                "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
                "relator": relator_txt,
                "relator_id": relator_id,
                "sigla_tipo": sigla_tipo,
                "ementa": ementa,
            }
            
            # Se for RIC, extrair informações adicionais
            if sigla_tipo == "RIC":
                prazo_info = parse_prazo_resposta_ric(tramitacoes, situacao)
                resultado.update({
                    "ric_data_remessa": prazo_info.get("data_remessa"),
                    "ric_inicio_contagem": prazo_info.get("inicio_contagem"),
                    "ric_prazo_inicio": prazo_info.get("prazo_inicio"),
                    "ric_prazo_fim": prazo_info.get("prazo_fim"),
                    "ric_prazo_str": prazo_info.get("prazo_str", ""),
                    "ric_dias_restantes": prazo_info.get("dias_restantes"),
                    "ric_fonte_prazo": prazo_info.get("fonte_prazo", ""),
                    "ric_status_resposta": prazo_info.get("status_resposta"),
                    "ric_data_resposta": prazo_info.get("data_resposta"),
                    "ric_respondido": prazo_info.get("respondido", False),
                    "ric_ministerio": extrair_ministerio_ric(ementa, tramitacoes),
                    "ric_assunto": extrair_assunto_ric(ementa),
                })
            
            return pid, resultado
        
        max_workers = 10 if len(ids) >= 40 else 6
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for pid, payload in ex.map(_one, ids):
                out[str(pid)] = payload
        
        return out

    def enrich_proposicoes_with_status(
        self,
        df_base: pd.DataFrame,
        status_map: Dict
    ) -> pd.DataFrame:
        """
        Enriquece DataFrame de proposições com informações de status.
        
        Args:
            df_base: DataFrame base com proposições
            status_map: Mapa de status (retorno de build_proposicoes_status_map)
            
        Returns:
            DataFrame enriquecido com colunas de status
        """
        # Importar funções necessárias
        from monitor_sistema_jz import (
            canonical_situacao,
            camara_link_deputado,
            get_proposicao_principal_id,
            fetch_proposicao_completa,
            format_relator_text
        )
        import datetime
        
        df = df_base.copy()
        
        # Mapear campos básicos
        df["Situação atual"] = df["id"].astype(str).map(
            lambda x: canonical_situacao(status_map.get(str(x), {}).get("situacao", ""))
        )
        df["Andamento (status)"] = df["id"].astype(str).map(
            lambda x: status_map.get(str(x), {}).get("andamento", "")
        )
        df["Data do status (raw)"] = df["id"].astype(str).map(
            lambda x: status_map.get(str(x), {}).get("status_dataHora", "")
        )
        df["Órgão (sigla)"] = df["id"].astype(str).map(
            lambda x: status_map.get(str(x), {}).get("siglaOrgao", "")
        )
        df["Relator(a)"] = df["id"].astype(str).map(
            lambda x: status_map.get(str(x), {}).get("relator", "—")
        )
        df["Relator_ID"] = df["id"].astype(str).map(
            lambda x: status_map.get(str(x), {}).get("relator_id", "")
        )
        
        # Normalizações
        _SITUACOES_INTERNA = {
            "Despacho de Apensação",
            "Distribuição",
            "Publicação de Despacho",
            "Notificacao para Publicação Intermediária",
            "Notificações",
            "Ratificação de Parecer",
        }
        
        # Unificar variações
        df["Situação atual"] = df["Situação atual"].replace({
            "Aguardando Parecer do Relator(a)": "Aguardando Parecer",
            "Aguardando Parecer do Relator(a).": "Aguardando Parecer",
        })
        df.loc[
            df["Situação atual"].astype(str).str.startswith("Aguardando Parecer", na=False),
            "Situação atual"
        ] = "Aguardando Parecer"
        
        # Tratar vazios como "Em providência Interna"
        def _is_blankish(v):
            if pd.isna(v):
                return True
            s = str(v).strip()
            return s in ("", "-", "—", "–")
        
        df.loc[
            df["Situação atual"].apply(_is_blankish),
            "Situação atual"
        ] = "Em providência Interna"
        df.loc[
            df["Situação atual"].isin(_SITUACOES_INTERNA),
            "Situação atual"
        ] = "Em providência Interna"
        
        # Preencher relator quando aguardando designação
        mask_aguardando_relator = df["Situação atual"].isin([
            "Aguardando Designação de Relator(a)",
            "Aguardando Designacao de Relator(a)",
        ])
        df.loc[
            mask_aguardando_relator & df["Relator(a)"].apply(_is_blankish),
            "Relator(a)"
        ] = "Aguardando"
        
        # Preencher relator para "Tramitando em Conjunto"
        mask_conjunto = df["Situação atual"].eq("Tramitando em Conjunto")
        if mask_conjunto.any():
            def _fill_relator_conjunto(row):
                if not _is_blankish(row.get("Relator(a)", "")):
                    return row.get("Relator(a)", "—")
                pid = str(row.get("id", "") or "").strip()
                if not pid:
                    return row.get("Relator(a)", "—")
                principal_id = get_proposicao_principal_id(pid)
                if not principal_id or str(principal_id) == pid:
                    return row.get("Relator(a)", "—")
                dados_principal = fetch_proposicao_completa(str(principal_id))
                rel_txt, _ = format_relator_text(dados_principal.get("relator", {}) or {})
                return rel_txt if rel_txt else row.get("Relator(a)", "—")
            
            df.loc[mask_conjunto, "Relator(a)"] = df.loc[mask_conjunto].apply(
                _fill_relator_conjunto, axis=1
            )
        
        # Link do relator
        def _link_relator(row):
            relator_id = row.get("Relator_ID", "")
            if relator_id and str(relator_id).strip() not in ('', 'nan', 'None'):
                return camara_link_deputado(relator_id)
            return ""
        
        df["LinkRelator"] = df.apply(_link_relator, axis=1)
        
        # Processar data
        dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
        df["DataStatus_dt"] = dt
        df["Data do status"] = dt.dt.strftime("%d/%m/%Y %H:%M").where(dt.notna(), "")
        
        # Calcular dias parados
        now = datetime.datetime.now()
        df["Parado (dias)"] = (now - dt).dt.days
        
        return df

    def get_default_anos_filter(self, anos_disponiveis: List[int]) -> List[int]:
        """
        Retorna lista de anos padrão para filtro.
        
        Regra: últimos 2 anos.
        
        Args:
            anos_disponiveis: Lista de anos disponíveis
            
        Returns:
            Lista de anos padrão (até 2 anos mais recentes)
        """
        if not anos_disponiveis:
            return []
        
        # Últimos 2 anos
        anos_sorted = sorted(anos_disponiveis, reverse=True)
        return anos_sorted[:2]

    def clear_proposicoes_cache(self) -> None:
        """
        Limpa cache de proposições.
        
        Limpa os caches de:
        - fetch_proposicao_completa
        - fetch_lista_proposicoes_autoria_geral
        - fetch_rics_por_autor
        - fetch_lista_proposicoes_autoria
        - build_status_map
        """
        # Importar funções
        from monitor_sistema_jz import (
            fetch_proposicao_completa,
            fetch_lista_proposicoes_autoria_geral,
            fetch_rics_por_autor,
            fetch_lista_proposicoes_autoria,
            build_status_map
        )
        
        # Limpar caches
        fetch_proposicao_completa.clear()
        fetch_lista_proposicoes_autoria_geral.clear()
        fetch_rics_por_autor.clear()
        fetch_lista_proposicoes_autoria.clear()
        build_status_map.clear()

    def processar_proposicoes_com_senado(
        self,
        df_proposicoes: pd.DataFrame,
        debug: bool = False,
        mostrar_progresso: bool = True
    ) -> pd.DataFrame:
        """
        Processa lista de proposições e enriquece com dados do Senado.
        
        Wrapper para o serviço de integração do Senado.
        
        Args:
            df_proposicoes: DataFrame com proposições
            debug: Modo debug
            mostrar_progresso: Mostrar barra de progresso
            
        Returns:
            DataFrame enriquecido com dados do Senado
        """
        from core.services.senado_integration import processar_lista_com_senado
        
        return processar_lista_com_senado(
            df_proposicoes,
            debug=debug,
            mostrar_progresso=mostrar_progresso
        )

    def clear_all_proposicoes_cache(self) -> None:
        """
        Limpa TODOS os caches relacionados a proposições.
        
        Versão estendida de clear_proposicoes_cache que também
        limpa o cache do build_proposicoes_status_map.
        """
        self.clear_proposicoes_cache()
        
        # Limpar também o cache do status map
        if hasattr(self.build_proposicoes_status_map, 'clear'):
            self.build_proposicoes_status_map.clear()

    # ---------------------------------------------------------------------
    # SENADO (placeholder)
    # ---------------------------------------------------------------------

    def get_senado_sob_demanda(self, *_args, **_kwargs) -> Any:
        return []


# ---------------------------------------------------------------------
# SINGLETON / FACTORY
# ---------------------------------------------------------------------

@st.cache_resource
def get_provider() -> DataProvider:
    """
    Retorna instância singleton do DataProvider.
    Usar este getter em vez de instanciar diretamente.
    """
    return DataProvider()
