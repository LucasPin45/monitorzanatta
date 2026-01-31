"""
Utilitários de data e hora para o Monitor Parlamentar.
Funções de formatação, cálculo de prazos e manipulação de datas.

REGRA: Este módulo NÃO pode importar streamlit.
"""
import datetime
import unicodedata
import re
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
import pandas as pd


# Timezone de Brasília
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


def get_brasilia_now() -> datetime.datetime:
    """Retorna datetime atual no fuso de Brasília."""
    return datetime.datetime.now(TZ_BRASILIA)


def parse_dt(iso_str: str) -> Optional[pd.Timestamp]:
    """Converte string ISO para pandas Timestamp."""
    return pd.to_datetime(iso_str, errors="coerce", utc=False)


def days_since(dt: pd.Timestamp) -> Optional[int]:
    """Calcula dias desde uma data até hoje."""
    if dt is None or pd.isna(dt):
        return None
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    today = pd.Timestamp(datetime.date.today())
    return int((today - d.normalize()).days)


def fmt_dt_br(dt: pd.Timestamp) -> str:
    """Formata datetime para padrão brasileiro (DD/MM/YYYY HH:MM)."""
    if dt is None or pd.isna(dt):
        return "—"
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    return d.strftime("%d/%m/%Y %H:%M")


def proximo_dia_util(dt: datetime.date) -> Optional[datetime.date]:
    """
    Retorna o próximo dia útil após a data informada.
    Pula sábados (5) e domingos (6).
    """
    if dt is None:
        return None
    proximo = dt + datetime.timedelta(days=1)
    while proximo.weekday() in (5, 6):  # Sábado=5, Domingo=6
        proximo += datetime.timedelta(days=1)
    return proximo


def ajustar_para_dia_util(dt: datetime.date) -> Optional[datetime.date]:
    """
    Se a data cair em fim de semana, retorna o próximo dia útil.
    Caso contrário, retorna a própria data.
    """
    if dt is None:
        return None
    while dt.weekday() in (5, 6):
        dt += datetime.timedelta(days=1)
    return dt


def calcular_prazo_ric(data_remessa: datetime.date) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    """
    Calcula o prazo de 30 dias para resposta de RIC conforme regra constitucional.
    
    REGRA:
    - Dia 1 = 1º dia ÚTIL após a remessa
    - Dia 30 = 30º dia se for útil, ou próximo dia útil se não for
    
    Exemplo:
    - Remessa: 27/11/2025 (quinta)
    - Dia 1: 28/11/2025 (sexta) - primeiro dia útil após remessa
    - Dia 30 seria: 28/11 + 29 dias = 27/12/2025 (sábado)
    - Como 27/12 é sábado, prazo final = 29/12/2025 (segunda)
    
    Retorna: (inicio_contagem, prazo_fim)
    """
    if data_remessa is None:
        return None, None
    
    # Dia 1 = primeiro dia ÚTIL após a remessa
    inicio_contagem = proximo_dia_util(data_remessa)
    
    # Dia 30 = 29 dias após o Dia 1 (porque Dia 1 já conta)
    dia_30_bruto = inicio_contagem + datetime.timedelta(days=29)
    
    # Se o Dia 30 cair em fim de semana, estende para o próximo dia útil
    prazo_fim = ajustar_para_dia_util(dia_30_bruto)
    
    return inicio_contagem, prazo_fim


def contar_dias_uteis(data_inicio: datetime.date, data_fim: datetime.date) -> int:
    """Conta dias úteis entre duas datas (excluindo fins de semana)."""
    if data_inicio is None or data_fim is None:
        return 0
    if data_fim < data_inicio:
        return 0
    dias = 0
    atual = data_inicio
    while atual <= data_fim:
        if atual.weekday() < 5:  # Segunda a sexta
            dias += 1
        atual += datetime.timedelta(days=1)
    return dias


def _determinar_status_por_situacao(situacao_atual: str, respondido: bool, data_resposta, prazo_fim) -> str:
    """
    Determina o status do RIC baseado na situação atual e dados de prazo/resposta.
    
    REGRAS:
    1. "Aguardando Remessa ao Arquivo" → "Respondido"
    2. "Aguardando Providências Internas" → "Em tramitação na Câmara"
    3. "Aguardando Despacho do Presidente da Câmara..." → "Em tramitação na Câmara"
    4. "Aguardando Designação de Relator" → "Em tramitação na Câmara"
    5. "Aguardando Resposta" (situação da Câmara) → "Em tramitação na Câmara" SE não houver prazo
    6. Se respondido e data_resposta > prazo_fim → "Respondido fora do prazo"
    7. Se respondido e data_resposta <= prazo_fim → "Respondido"
    8. Se não respondido e hoje > prazo_fim → "Fora do prazo"
    9. Se não há prazo_fim (não encontrou remessa) → "Em tramitação na Câmara"
    10. Caso contrário → "Aguardando resposta"
    """
    situacao_norm = (situacao_atual or "").lower().strip()
    hoje = datetime.date.today()
    
    # REGRA 1: Aguardando Remessa ao Arquivo = JÁ FOI RESPONDIDO
    if "aguardando remessa ao arquivo" in situacao_norm or "remessa ao arquivo" in situacao_norm:
        if prazo_fim and data_resposta and data_resposta > prazo_fim:
            return "Respondido fora do prazo"
        return "Respondido"
    
    # REGRA 2, 3, 4 e 5: Situações que indicam tramitação interna na Câmara
    situacoes_tramitacao_camara = [
        "aguardando providências internas",
        "aguardando providencias internas",
        "aguardando despacho do presidente da câmara",
        "aguardando despacho do presidente da camara",
        "aguardando designação de relator",
        "aguardando designacao de relator",
        "aguardando recebimento",
        "retirado pelo(a) autor(a)",
        "retirado pelo autor",
    ]
    for sit in situacoes_tramitacao_camara:
        if sit in situacao_norm:
            return "Em tramitação na Câmara"
    
    # REGRA 6 e 7: Se foi respondido (detectado nas tramitações)
    if respondido:
        if prazo_fim and data_resposta:
            if data_resposta > prazo_fim:
                return "Respondido fora do prazo"
            else:
                return "Respondido"
        else:
            return "Respondido"
    
    # REGRA 8: Se não foi respondido e prazo venceu
    if prazo_fim and hoje > prazo_fim:
        return "Fora do prazo"
    
    # REGRA 9: Se não há prazo (não encontrou remessa) → Em tramitação na Câmara
    # Isso significa que o RIC ainda não foi remetido ao Executivo
    if not prazo_fim:
        return "Em tramitação na Câmara"
    
    # REGRA 10: Caso padrão - já foi remetido, aguardando resposta
    return "Aguardando resposta"


def parse_prazo_resposta_ric(tramitacoes: list, situacao_atual: str = "") -> dict:
    """
    Extrai informações de prazo de resposta de RIC a partir das tramitações.
    
    REGRA CONSTITUCIONAL DE PRAZO:
    ==============================
    O Poder Executivo tem 30 DIAS para responder, contados a partir da REMESSA.
    
    DETECÇÃO DE REMESSA:
    - Órgão: 1SECM (1ª Secretaria da Câmara dos Deputados)
    - Texto contém: "Remessa por meio do Ofício" (qualquer variação)
    
    DETECÇÃO DE RESPOSTA:
    - Órgão: 1SECM (1ª Secretaria da Câmara dos Deputados)
    - Texto contém: "Recebimento de resposta conforme Ofício"
    
    CÁLCULO DO PRAZO:
    - Se houver texto "Prazo para Resposta Externas (de DD/MM/AAAA a DD/MM/AAAA)": usar datas explícitas
    - Senão: prazo_fim = data_remessa + 30 dias
    """
    resultado = {
        "data_remessa": None,
        "inicio_contagem": None,
        "prazo_inicio": None,
        "prazo_fim": None,
        "prazo_str": "",
        "dias_restantes": None,
        "fonte_prazo": "",
        "status_resposta": "Aguardando resposta",
        "data_resposta": None,
        "respondido": False,
        "ministerio_destinatario": "",
        "tramitacao_remessa_texto": "",
    }
    
    if not tramitacoes:
        resultado["status_resposta"] = _determinar_status_por_situacao(situacao_atual, False, None, None)
        return resultado
    
    # Ordenar tramitações por data (cronológica)
    tramitacoes_ordenadas = sorted(
        tramitacoes,
        key=lambda x: x.get("dataHora") or x.get("data") or "",
        reverse=False
    )
    
    # Regex para prazo explícito (se existir no texto)
    regex_prazo = r"Prazo\s+para\s+Resposta\s+Externas?\s*\(de\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})\)"
    
    def normalizar_texto_busca(texto):
        """Normaliza texto removendo acentos e convertendo para minúsculas"""
        texto = texto.lower()
        # Substituir caracteres especiais
        texto = texto.replace('ª', 'a').replace('º', 'o')
        # Remover acentos usando unicodedata
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto
    
    # ============================================================
    # PASSO 1: Procurar tramitação de REMESSA
    # Critério: 1SECM + "Remessa por meio do Ofício 1ªSec/RI/E"
    # ============================================================
    tramitacao_remessa = None
    data_remessa = None
    
    for t in tramitacoes_ordenadas:
        sigla_orgao = (t.get("siglaOrgao") or "").upper().strip()
        despacho = t.get("despacho") or ""
        desc = t.get("descricaoTramitacao") or ""
        texto_completo = f"{despacho} {desc}"
        
        # Normalizar texto para busca
        texto_busca = normalizar_texto_busca(texto_completo)
        
        is_1secm = "1SEC" in sigla_orgao or sigla_orgao == "1SECM"
        
        # Critério de REMESSA: "Remessa por meio do Ofício 1ªSec/RI/E" ou variações
        # Aceita: "remessa por meio do oficio", "1asec/ri/e", "1sec/ri/e"
        has_remessa = "remessa por meio do oficio" in texto_busca
        has_1sec_ri = "1asec/ri/e" in texto_busca or "1sec/ri/e" in texto_busca
        
        # NÃO é remessa se for recebimento de resposta
        is_recebimento = "recebimento de resposta" in texto_busca
        
        if is_1secm and (has_remessa or has_1sec_ri) and not is_recebimento:
            tramitacao_remessa = t
            resultado["tramitacao_remessa_texto"] = texto_completo.strip()
            
            # Extrair data da tramitação de remessa
            data_str = t.get("dataHora") or t.get("data")
            if data_str:
                try:
                    dt = pd.to_datetime(data_str, errors="coerce")
                    if pd.notna(dt):
                        data_remessa = dt.date()
                        resultado["data_remessa"] = data_remessa
                except:
                    pass
            
            # Verificar se tem prazo EXPLÍCITO no texto
            match_prazo = re.search(regex_prazo, texto_completo, re.IGNORECASE)
            if match_prazo:
                try:
                    prazo_inicio_str = match_prazo.group(1)
                    prazo_fim_str = match_prazo.group(2)
                    resultado["prazo_inicio"] = datetime.datetime.strptime(prazo_inicio_str, "%d/%m/%Y").date()
                    resultado["prazo_fim"] = datetime.datetime.strptime(prazo_fim_str, "%d/%m/%Y").date()
                    resultado["prazo_str"] = f"{prazo_inicio_str} a {prazo_fim_str}"
                    resultado["fonte_prazo"] = "explicitado_na_tramitacao"
                    resultado["inicio_contagem"] = resultado["prazo_inicio"]
                except:
                    pass
            
            # Continua procurando para pegar a ÚLTIMA remessa (mais recente)
    
    # ============================================================
    # PASSO 2: Se não encontrou prazo explícito, CALCULAR
    # Regra: Dia 1 = 1º dia útil após remessa, Dia 30 = 30º dia (ou próximo útil)
    # ============================================================
    if tramitacao_remessa and not resultado["prazo_fim"] and data_remessa:
        # Usar função que calcula corretamente os dias úteis
        inicio_contagem, prazo_fim = calcular_prazo_ric(data_remessa)
        if inicio_contagem and prazo_fim:
            resultado["prazo_inicio"] = inicio_contagem
            resultado["inicio_contagem"] = inicio_contagem
            resultado["prazo_fim"] = prazo_fim
            resultado["prazo_str"] = f"até {prazo_fim.strftime('%d/%m/%Y')}"
            resultado["fonte_prazo"] = "calculado_30_dias"
    
    # ============================================================
    # PASSO 3: Calcular dias restantes
    # ============================================================
    if resultado["prazo_fim"]:
        hoje = datetime.date.today()
        delta = (resultado["prazo_fim"] - hoje).days
        resultado["dias_restantes"] = delta
    
    # ============================================================
    # PASSO 4: Verificar se foi RESPONDIDO
    # Critério: 1SECM + "Recebimento de resposta conforme Ofício"
    # A data da resposta é a data mencionada NO TEXTO do ofício, não a data da tramitação
    # ============================================================
    data_resposta = None
    respondido = False
    
    # Regex para extrair data do texto do ofício
    # Padrões: "de 24 de novembro de 2025" ou "de 27/12/2025"
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    regex_data_extenso = r"de\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"
    regex_data_num = r"de\s+(\d{1,2})/(\d{1,2})/(\d{4})"
    
    for t in tramitacoes_ordenadas:
        sigla_orgao = (t.get("siglaOrgao") or "").upper().strip()
        despacho = (t.get("despacho") or "")
        desc = (t.get("descricaoTramitacao") or "")
        texto = f"{despacho} {desc}"
        texto_busca = normalizar_texto_busca(texto)
        
        is_1secm = "1SEC" in sigla_orgao or sigla_orgao == "1SECM"
        
        # Critério PRINCIPAL: "Recebimento de resposta conforme Ofício"
        is_recebimento_resposta = "recebimento de resposta conforme of" in texto_busca
        
        if is_1secm and is_recebimento_resposta:
            respondido = True
            
            # Tentar extrair data do texto do ofício (ex: "de 24 de novembro de 2025")
            match_extenso = re.search(regex_data_extenso, texto, re.IGNORECASE)
            match_num = re.search(regex_data_num, texto)
            
            if match_extenso:
                try:
                    dia = int(match_extenso.group(1))
                    mes_nome = match_extenso.group(2).lower()
                    ano = int(match_extenso.group(3))
                    mes = meses_pt.get(mes_nome)
                    if mes:
                        data_resposta = datetime.date(ano, mes, dia)
                except:
                    pass
            elif match_num:
                try:
                    dia = int(match_num.group(1))
                    mes = int(match_num.group(2))
                    ano = int(match_num.group(3))
                    data_resposta = datetime.date(ano, mes, dia)
                except:
                    pass
            
            # Se não conseguiu extrair do texto, usar data da tramitação como fallback
            if not data_resposta:
                data_str = t.get("dataHora") or t.get("data")
                if data_str:
                    try:
                        dt_resp = pd.to_datetime(data_str, errors="coerce")
                        if pd.notna(dt_resp):
                            data_resposta = dt_resp.date()
                    except:
                        pass
    
    resultado["respondido"] = respondido
    resultado["data_resposta"] = data_resposta
    
    # ============================================================
    # PASSO 5: Determinar STATUS FINAL
    # ============================================================
    resultado["status_resposta"] = _determinar_status_por_situacao(
        situacao_atual, 
        respondido, 
        data_resposta, 
        resultado["prazo_fim"]
    )
    
    return resultado
