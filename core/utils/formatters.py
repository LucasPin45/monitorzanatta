"""
Utilitários de formatação para o Monitor Parlamentar.
Funções de formatação e ordenação de dados para exibição.

REGRA: Este módulo NÃO pode importar streamlit.
"""
from typing import Tuple, Optional
import pandas as pd


# Partidos considerados adversários (oposição)
PARTIDOS_RELATOR_ADVERSARIO = {"PT", "PV", "PSB", "PCDOB", "PSOL", "REDE"}

# Partidos da oposição (lista expandida)
PARTIDOS_OPOSICAO = {"PT", "PSOL", "PCDOB", "PC DO B", "REDE", "PV", "PSB", "PDT", "PSDB"}


def format_sigla_num_ano(sigla, numero, ano) -> str:
    """Formata uma proposição como 'SIGLA NUMERO/ANO'."""
    sigla = (sigla or "").strip()
    numero = (str(numero) or "").strip()
    ano = (str(ano) or "").strip()
    if sigla and numero and ano:
        return f"{sigla} {numero}/{ano}"
    return ""


def _verificar_relator_adversario(relator_str: str) -> Tuple[str, bool]:
    """
    Verifica se o relator é de partido adversário.
    Retorna: (texto_relator_formatado, is_adversario)
    """
    if not relator_str or not str(relator_str).strip() or str(relator_str).strip() in ('-', '—', 'nan'):
        return "Sem relator designado", False
    
    relator = str(relator_str).strip()
    relator_upper = relator.upper()
    
    for partido in PARTIDOS_RELATOR_ADVERSARIO:
        if f"({partido}/" in relator_upper or f"({partido}-" in relator_upper or f"/{partido})" in relator_upper:
            return relator, True
        if partido == "PCDOB" and ("(PC DO B" in relator_upper or "/PC DO B" in relator_upper):
            return relator, True
    
    return relator, False


def _obter_situacao_com_fallback(row: pd.Series) -> str:
    """
    Obtém a situação da proposição com fallback para andamento/tramitação.
    """
    situacao = ""
    for col in ['Situação atual', 'Situacao atual', 'situacao']:
        if col in row.index and pd.notna(row.get(col)) and str(row.get(col)).strip():
            situacao = str(row.get(col)).strip()
            break
    
    if not situacao or situacao in ('-', '—'):
        for col in ['Andamento (status)', 'Último andamento', 'Andamento', 'status_descricaoTramitacao']:
            if col in row.index and pd.notna(row.get(col)) and str(row.get(col)).strip():
                situacao = str(row.get(col)).strip()
                if len(situacao) > 60:
                    situacao = situacao[:57] + "..."
                break
    
    return situacao if situacao else "Situacao nao informada"


def _categorizar_situacao_para_ordenacao(situacao: str) -> Tuple[int, str, str]:
    """
    Categoriza a situação para ordenação personalizada dos blocos no PDF.
    Retorna: (ordem_prioridade, categoria_agrupada, situacao_original)
    
    Ordem de prioridade:
    1. Pronta para Pauta
    2. Aguardando Parecer de Relator(a)
    3. Aguardando Designação de Relator(a)
    4. Aguardando Apreciação pelo Senado Federal
    5. Aguardando Despacho do Presidente da Câmara
    6. Tramitando em Conjunto
    7. Aguardando Encaminhamentos/Procedimentos Administrativos
    8. Arquivadas/Aguardando Remessa ao Arquivo
    9. Outras situações
    """
    s = situacao.lower().strip()
    
    # 1. Pronta para Pauta
    if 'pronta' in s and 'pauta' in s:
        return (1, "Pronta para Pauta", situacao)
    # 2. Aguardando Parecer
    if 'aguardando parecer' in s:
        return (2, "Aguardando Parecer", situacao)
    # 3. Aguardando Designação de Relator(a) (incluindo devolução)
    if ('aguardando design' in s and 'relator' in s) or ('devolucao de relator' in s) or ('devolução de relator' in s):
        return (3, "Aguardando Designacao de Relator(a)", situacao)
    
    # 4. Aguardando Apreciação pelo Senado Federal
    if 'senado' in s or 'aguardando aprecia' in s:
        return (4, "Aguardando Apreciacao pelo Senado Federal", situacao)
    
    # 5. Aguardando Despacho do Presidente (todos os tipos)
    if ('despacho' in s and 'presidente' in s) or ('autorizacao do despacho' in s) or ('autorização do despacho' in s) or ('deliberacao de recurso' in s) or ('deliberação de recurso' in s):
        return (5, "Aguardando Despacho do Presidente da Camara", situacao)
    
    # 6. Tramitando em Conjunto (incluindo Aguardando Apensação)
    if 'tramitando em conjunto' in s or 'apensacao' in s or 'apensação' in s:
        return (6, "Tramitando em Conjunto", situacao)
    
    # 7. Aguardando Encaminhamentos/Procedimentos Administrativos
    if 'aguardando encaminhamento' in s or 'aguardando recebimento' in s or 'comissao temporaria' in s or 'comissão temporária' in s or 'criacao de comissao' in s or 'criação de comissão' in s:
        return (7, "Aguardando Procedimentos Administrativos da Casa", situacao)
    
    # 8. Arquivadas/Aguardando Remessa ao Arquivo
    if 'arquiv' in s or 'remessa ao arquivo' in s:
        return (8, "Arquivadas / Aguardando Remessa ao Arquivo", situacao)
    
    # 9. Outras situações (situacao nao informada, retirado pelo autor, etc.)
    return (9, "Outras Situacoes", situacao)


def is_comissao_estrategica(sigla_orgao: str, lista_siglas: list) -> bool:
    """Verifica se um órgão está na lista de comissões estratégicas."""
    if not sigla_orgao:
        return False
    return sigla_orgao.upper() in [s.upper() for s in lista_siglas]


def format_relator_text(relator_info: dict) -> Tuple[str, str]:
    """Formata relator para 'Nome (PART/UF)'. Retorna (texto, id)."""
    if not relator_info or not isinstance(relator_info, dict) or not relator_info.get("nome"):
        return ("", "")
    nome = str(relator_info.get("nome", "")).strip()
    partido = str(relator_info.get("partido", "") or "").strip()
    uf = str(relator_info.get("uf", "") or "").strip()
    relator_id = str(relator_info.get("id_deputado", "") or "")
    if partido or uf:
        txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
    else:
        txt = nome
    return (txt, relator_id)
