"""
Serviço de acesso à API do Senado Federal.

REGRAS:
- SEM Streamlit
- SEM cache (cache fica no DataProvider)
- Usa http_client para requisições
- Usa parsers para extração de dados
- Suporta respostas JSON e XML
"""

import datetime
from typing import Optional, Dict, List, Any

from .http_client import (
    safe_get,
    safe_get_raw,
    get_senado_session,
    SENADO_HEADERS,
    SSL_VERIFY,
    validar_resposta_api,
)
from .parsers import (
    parse_processo_senado,
    parse_processo_senado_com_identificacao,
    parse_relatoria_senado_json,
    parse_relatoria_senado_xml,
    selecionar_relatoria_ativa,
    parse_informes_senado_json,
    parse_informes_senado_xml,
    parse_status_senado_json,
    parse_status_senado_xml,
    parse_senadores_lista,
    parse_materias_senado,
    parse_datetime,
    format_datetime_br,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

SENADO_BASE_URL = "https://legis.senado.leg.br/dadosabertos"


class SenadoService:
    """
    Serviço para acesso à API do Senado Federal.
    
    Todos os métodos retornam dados brutos (dicts/lists).
    Não há cache nesta camada - cache fica no DataProvider.
    
    Nota: A API do Senado pode retornar JSON ou XML mesmo com Accept: application/json.
    Este serviço trata ambos os formatos.
    """
    
    def __init__(self):
        self._session = get_senado_session()
    
    # ============================================================
    # BUSCA DE PROCESSO POR TIPO/NÚMERO/ANO
    # ============================================================
    
    def buscar_tramitacao_por_numero(
        self,
        tipo: str,
        numero: str,
        ano: str,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Busca tramitação no Senado usando tipo/número/ano.
        
        REGRA: o número do projeto é IDÊNTICO na Câmara e no Senado.
        Exemplo: PLP 223/2023 na Câmara → PLP 223/2023 no Senado.
        
        Args:
            tipo: Sigla (PL, PLP, PEC, etc.)
            numero: Número
            ano: Ano (4 dígitos)
            debug: Modo debug (para logs, não UI)
            
        Returns:
            Dict com dados do Senado ou None
        """
        tipo_norm = (tipo or "").strip().upper()
        numero_norm = (numero or "").strip()
        ano_norm = (ano or "").strip()
        
        if not (tipo_norm and numero_norm and ano_norm):
            return None
        
        # Endpoint /processo com query params
        url = (
            f"{SENADO_BASE_URL}/processo"
            f"?sigla={tipo_norm}&numero={numero_norm}&ano={ano_norm}&v=1"
        )
        
        identificacao_alvo = f"{tipo_norm} {numero_norm}/{ano_norm}"
        
        if debug:
            print(f"[SENADO] Buscando (processo): {identificacao_alvo}")
            print(f"[SENADO] URL: {url}")
        
        resp = safe_get_raw(url, timeout=20)
        
        if resp is None:
            return None
        
        if resp.status_code == 404:
            if debug:
                print("[SENADO] Não encontrado (404)")
            return None
        
        if resp.status_code != 200:
            if debug:
                print(f"[SENADO] HTTP {resp.status_code}")
            return None
        
        # Tentar parsear JSON
        try:
            data = resp.json()
        except Exception:
            try:
                import json
                data = json.loads(resp.text)
            except Exception:
                return None
        
        if not data:
            return None
        
        # Parsear com identificação específica
        parsed = parse_processo_senado_com_identificacao(data, identificacao_alvo)
        
        if not parsed or not parsed.get("codigo_materia"):
            return None
        
        # Construir URL deep link
        codigo_materia = parsed["codigo_materia"]
        url_deep = f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo_materia}"
        
        return {
            "tipo_senado": tipo_norm,
            "numero_senado": numero_norm,
            "ano_senado": ano_norm,
            "codigo_senado": codigo_materia,
            "id_processo_senado": parsed.get("id_processo", ""),
            "situacao_senado": parsed.get("situacao", ""),
            "url_senado": url_deep,
        }
    
    # ============================================================
    # DETALHES (RELATOR E ÓRGÃO)
    # ============================================================
    
    def buscar_detalhes(
        self,
        codigo_materia: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Busca Relator e Órgão atuais no Senado pelo CodigoMateria.
        
        Endpoint: /dadosabertos/processo/relatoria?codigoMateria=...
        
        Args:
            codigo_materia: Código da matéria no Senado
            debug: Modo debug
            
        Returns:
            Dict com relator e órgão
        """
        resultado = {
            "relator_senado": "",
            "relator_nome": "",
            "relator_partido": "",
            "relator_uf": "",
            "orgao_senado_sigla": "",
            "orgao_senado_nome": "",
        }
        
        if not codigo_materia:
            return resultado
        
        data_ref = datetime.date.today().isoformat()
        url = (
            f"{SENADO_BASE_URL}/processo/relatoria"
            f"?codigoMateria={codigo_materia}&dataReferencia={data_ref}&v=1"
        )
        
        if debug:
            print(f"[SENADO-RELATORIA] URL: {url}")
        
        resp = safe_get_raw(url, timeout=20)
        
        if resp is None or resp.status_code != 200 or not resp.content:
            return resultado
        
        # Tentar JSON primeiro
        relatorias = []
        try:
            data = resp.json()
            relatorias = parse_relatoria_senado_json(data)
        except Exception:
            pass
        
        # Fallback: XML
        if not relatorias:
            relatorias = parse_relatoria_senado_xml(resp.content)
        
        if not relatorias:
            return resultado
        
        # Selecionar relatoria ativa
        atual = selecionar_relatoria_ativa(relatorias)
        if not atual:
            return resultado
        
        nome = (atual.get("nomeParlamentar") or "").strip()
        partido = (atual.get("siglaPartidoParlamentar") or "").strip()
        uf = (atual.get("ufParlamentar") or "").strip()
        sigla_col = (atual.get("siglaColegiado") or "").strip()
        nome_col = (atual.get("nomeColegiado") or "").strip()
        
        resultado["relator_nome"] = nome
        resultado["relator_partido"] = partido
        resultado["relator_uf"] = uf
        resultado["orgao_senado_sigla"] = sigla_col
        resultado["orgao_senado_nome"] = nome_col
        
        # Formatar nome completo do relator
        if nome:
            if partido and uf:
                resultado["relator_senado"] = f"{nome} ({partido}/{uf})"
            elif partido:
                resultado["relator_senado"] = f"{nome} ({partido})"
            else:
                resultado["relator_senado"] = nome
        
        return resultado
    
    # ============================================================
    # MOVIMENTAÇÕES
    # ============================================================
    
    def buscar_movimentacoes(
        self,
        id_processo_senado: str,
        limite: int = 10,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca as últimas movimentações (informes legislativos) do Senado.
        
        Endpoint: /dadosabertos/processo/{id}?v=1
        
        Args:
            id_processo_senado: ID do processo no Senado
            limite: Número máximo de movimentações
            debug: Modo debug
            
        Returns:
            Lista de movimentações formatadas
        """
        if not id_processo_senado:
            return []
        
        url = f"{SENADO_BASE_URL}/processo/{id_processo_senado}?v=1"
        
        if debug:
            print(f"[SENADO-PROCESSO] URL: {url}")
        
        resp = safe_get_raw(url, timeout=25)
        
        if resp is None or resp.status_code != 200 or not resp.content:
            return []
        
        # Tentar JSON primeiro
        informes = []
        try:
            proc = resp.json()
            informes = parse_informes_senado_json(proc)
        except Exception:
            pass
        
        # Fallback: XML
        if not informes:
            informes = parse_informes_senado_xml(resp.content)
        
        # Processar e formatar
        movs = []
        for it in informes:
            data_txt = (it.get("data") or "").strip()
            desc = (it.get("descricao") or "").strip()
            
            org_sigla = ""
            coleg = it.get("colegiado") or {}
            if isinstance(coleg, dict):
                org_sigla = (coleg.get("sigla") or "").strip()
            
            # Parsear data
            dt = parse_datetime(data_txt)
            data_br, hora = format_datetime_br(dt)
            
            movs.append({
                "data": data_br or data_txt,
                "hora": hora,
                "orgao": org_sigla,
                "descricao": desc,
                "_sort": dt or datetime.datetime.min
            })
        
        # Ordenar por data (mais recente primeiro)
        movs.sort(key=lambda x: x.get("_sort"), reverse=True)
        movs = movs[:limite]
        
        # Remover campo de ordenação
        for m in movs:
            m.pop("_sort", None)
        
        return movs
    
    # ============================================================
    # STATUS DO PROCESSO
    # ============================================================
    
    def buscar_status_por_processo(
        self,
        id_processo_senado: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Obtém SITUAÇÃO ATUAL e ÓRGÃO ATUAL no Senado.
        
        Endpoint: /dadosabertos/processo/{id}?v=1
        
        Args:
            id_processo_senado: ID do processo
            debug: Modo debug
            
        Returns:
            Dict com situacao e órgão
        """
        out = {
            "situacao_senado": "",
            "orgao_senado_sigla": "",
            "orgao_senado_nome": ""
        }
        
        if not id_processo_senado:
            return out
        
        url = f"{SENADO_BASE_URL}/processo/{id_processo_senado}?v=1"
        
        if debug:
            print(f"[SENADO-PROCESSO] URL status: {url}")
        
        resp = safe_get_raw(url, timeout=25)
        
        if resp is None or resp.status_code != 200 or not resp.content:
            return out
        
        # Tentar JSON primeiro
        try:
            proc = resp.json()
            parsed = parse_status_senado_json(proc)
            if parsed.get("situacao") or parsed.get("orgao_sigla"):
                out["situacao_senado"] = parsed.get("situacao", "")
                out["orgao_senado_sigla"] = parsed.get("orgao_sigla", "")
                out["orgao_senado_nome"] = parsed.get("orgao_nome", "")
                return out
        except Exception:
            pass
        
        # Fallback: XML
        parsed = parse_status_senado_xml(resp.content)
        out["situacao_senado"] = parsed.get("situacao", "")
        out["orgao_senado_sigla"] = parsed.get("orgao_sigla", "")
        out["orgao_senado_nome"] = parsed.get("orgao_nome", "")
        
        return out
    
    # ============================================================
    # SENADORES
    # ============================================================
    
    def buscar_codigo_senador_por_nome(self, nome_senador: str) -> Optional[str]:
        """
        Busca o código do senador pelo nome.
        
        Endpoint: /dadosabertos/senador/lista/atual
        
        Args:
            nome_senador: Nome do senador
            
        Returns:
            Código do senador ou None
        """
        if not nome_senador:
            return None
        
        # Normalizar nome
        nome_busca = nome_senador.lower().strip()
        for prefixo in ["senador ", "senadora "]:
            if nome_busca.startswith(prefixo):
                nome_busca = nome_busca[len(prefixo):]
        
        url = f"{SENADO_BASE_URL}/senador/lista/atual"
        
        resp = safe_get_raw(url, timeout=15)
        
        if resp is None or resp.status_code != 200:
            return None
        
        try:
            data = resp.json()
        except Exception:
            return None
        
        parlamentares = parse_senadores_lista(data)
        
        for p in parlamentares:
            nome_parl = p.get("nome_parlamentar", "")
            nome_completo = p.get("nome_completo", "")
            codigo = p.get("codigo")
            
            if (nome_busca in nome_parl or 
                nome_busca in nome_completo or 
                nome_parl in nome_busca):
                return str(codigo)
        
        return None
    
    def get_foto_senador(
        self,
        nome_senador: str,
        codigo_senador: Optional[str] = None
    ) -> Optional[str]:
        """
        Retorna a URL da foto do senador.
        
        Args:
            nome_senador: Nome do senador
            codigo_senador: Código (opcional, busca pelo nome se não fornecido)
            
        Returns:
            URL da foto ou None
        """
        if not codigo_senador and nome_senador:
            codigo_senador = self.buscar_codigo_senador_por_nome(nome_senador)
        
        if codigo_senador:
            return f"https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo_senador}.jpg"
        
        return None
    
    # ============================================================
    # PESQUISA DE MATÉRIAS
    # ============================================================
    
    def pesquisar_materias(
        self,
        termo_busca: str = "Julia Zanatta",
        tramitando: str = "S",
        limite: int = 50,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Pesquisa matérias no Senado por termo.
        
        Endpoint: /dadosabertos/materia/pesquisa/lista
        
        Args:
            termo_busca: Termo para buscar
            tramitando: "S" para apenas tramitando
            limite: Limite de resultados
            debug: Modo debug
            
        Returns:
            Lista de matérias
        """
        url = f"{SENADO_BASE_URL}/materia/pesquisa/lista"
        
        params = {
            "texto": termo_busca,
            "tramitando": tramitando,
            "formato": "json"
        }
        
        if debug:
            print(f"[SENADO-PESQUISA] URL: {url}")
            print(f"[SENADO-PESQUISA] Params: {params}")
        
        resp = safe_get_raw(url, params=params, timeout=30)
        
        if resp is None:
            return []
        
        # Validar resposta
        valida, msg_erro = validar_resposta_api(resp)
        if not valida:
            if debug:
                print(f"[SENADO-PESQUISA] Erro: {msg_erro}")
            return []
        
        try:
            data = resp.json()
        except Exception:
            return []
        
        materias = parse_materias_senado(data)
        return materias[:limite] if len(materias) > limite else materias
    
    def pesquisar_autoria(
        self,
        nome_autor: str = "Julia Zanatta",
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Pesquisa matérias de autoria específica no Senado.
        
        Args:
            nome_autor: Nome do autor
            debug: Modo debug
            
        Returns:
            Lista de matérias
        """
        return self.pesquisar_materias(
            termo_busca=nome_autor,
            tramitando="S",
            debug=debug
        )
    
    # ============================================================
    # AGREGAÇÃO
    # ============================================================
    
    def enriquecer_com_dados_senado(
        self,
        tipo: str,
        numero: str,
        ano: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Busca todos os dados do Senado para uma proposição.
        
        Agrega: tramitação, detalhes (relator/órgão), status.
        
        Args:
            tipo: Sigla (PL, PLP, etc.)
            numero: Número
            ano: Ano
            debug: Modo debug
            
        Returns:
            Dict completo com dados do Senado ou {}
        """
        resultado = {
            "no_senado": False,
            "codigo_materia_senado": "",
            "id_processo_senado": "",
            "situacao_senado": "",
            "url_senado": "",
            "tipo_numero_senado": "",
            "Relator_Senado": "",
            "Orgao_Senado_Sigla": "",
            "Orgao_Senado_Nome": "",
            "UltimasMov_Senado": "",
        }
        
        # 1. Buscar tramitação básica
        tram = self.buscar_tramitacao_por_numero(tipo, numero, ano, debug=debug)
        
        if not tram:
            return resultado
        
        resultado["no_senado"] = True
        resultado["codigo_materia_senado"] = tram.get("codigo_senado", "")
        resultado["id_processo_senado"] = tram.get("id_processo_senado", "")
        resultado["situacao_senado"] = tram.get("situacao_senado", "")
        resultado["url_senado"] = tram.get("url_senado", "")
        resultado["tipo_numero_senado"] = f"{tipo} {numero}/{ano}"
        
        codigo = tram.get("codigo_senado", "")
        id_processo = tram.get("id_processo_senado", "")
        
        # 2. Buscar detalhes (relator/órgão)
        if codigo:
            detalhes = self.buscar_detalhes(codigo, debug=debug)
            resultado["Relator_Senado"] = detalhes.get("relator_senado", "")
            resultado["Orgao_Senado_Sigla"] = detalhes.get("orgao_senado_sigla", "")
            resultado["Orgao_Senado_Nome"] = detalhes.get("orgao_senado_nome", "")
        
        # 3. Buscar status atualizado
        if id_processo:
            status = self.buscar_status_por_processo(id_processo, debug=debug)
            if status.get("situacao_senado"):
                resultado["situacao_senado"] = status["situacao_senado"]
            if status.get("orgao_senado_sigla"):
                resultado["Orgao_Senado_Sigla"] = status["orgao_senado_sigla"]
            if status.get("orgao_senado_nome"):
                resultado["Orgao_Senado_Nome"] = status["orgao_senado_nome"]
        
        # 4. Buscar movimentações
        if id_processo:
            movs = self.buscar_movimentacoes(id_processo, limite=5, debug=debug)
            if movs:
                linhas = []
                for m in movs:
                    data = m.get("data", "")
                    desc = m.get("descricao", "")[:100]
                    orgao = m.get("orgao", "")
                    if orgao:
                        linhas.append(f"• {data} [{orgao}]: {desc}")
                    else:
                        linhas.append(f"• {data}: {desc}")
                resultado["UltimasMov_Senado"] = "\n".join(linhas)
        
        return resultado
