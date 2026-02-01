"""
Módulo de utilitários para o Monitor Parlamentar.
Este pacote contém funções puras sem dependência de Streamlit.
"""

# text_utils
from .text_utils import (
    normalize_text,
    normalize_ministerio,
    canonical_situacao,
    party_norm,
    sanitize_text_pdf,
    MINISTERIOS_CANONICOS,
    MINISTERIOS_KEYWORDS,
)

# date_utils
from .date_utils import (
    TZ_BRASILIA,
    get_brasilia_now,
    parse_dt,
    days_since,
    fmt_dt_br,
    proximo_dia_util,
    ajustar_para_dia_util,
    calcular_prazo_ric,
    contar_dias_uteis,
    parse_prazo_resposta_ric,
)

# formatters
from .formatters import (
    PARTIDOS_RELATOR_ADVERSARIO,
    PARTIDOS_OPOSICAO,
    format_sigla_num_ano,
    format_relator_text,
    is_comissao_estrategica,
    _verificar_relator_adversario,
    _obter_situacao_com_fallback,
    _categorizar_situacao_para_ordenacao,
)

# links
from .links import (
    camara_link_tramitacao,
    camara_link_deputado,
    extract_id_from_uri,
)

# xlsx_generator
from .xlsx_generator import to_xlsx_bytes

# pdf_generator
from .pdf_generator import (
    to_pdf_bytes,
    to_pdf_linha_do_tempo,
    to_pdf_autoria_relatoria,
    to_pdf_comissoes_estrategicas,
    to_pdf_palavras_chave,
    to_pdf_rics_por_status,
)

__all__ = [
    # text_utils
    'normalize_text',
    'normalize_ministerio', 
    'canonical_situacao',
    'party_norm',
    'sanitize_text_pdf',
    'MINISTERIOS_CANONICOS',
    'MINISTERIOS_KEYWORDS',
    # date_utils
    'TZ_BRASILIA',
    'get_brasilia_now',
    'parse_dt',
    'days_since',
    'fmt_dt_br',
    'proximo_dia_util',
    'ajustar_para_dia_util',
    'calcular_prazo_ric',
    'contar_dias_uteis',
    'parse_prazo_resposta_ric',
    # formatters
    'PARTIDOS_RELATOR_ADVERSARIO',
    'PARTIDOS_OPOSICAO',
    'format_sigla_num_ano',
    'format_relator_text',
    'is_comissao_estrategica',
    '_verificar_relator_adversario',
    '_obter_situacao_com_fallback',
    '_categorizar_situacao_para_ordenacao',
    # links
    'camara_link_tramitacao',
    'camara_link_deputado',
    'extract_id_from_uri',
    # xlsx_generator
    'to_xlsx_bytes',
    # pdf_generator
    'to_pdf_bytes',
    'to_pdf_linha_do_tempo',
    'to_pdf_autoria_relatoria',
    'to_pdf_comissoes_estrategicas',
    'to_pdf_palavras_chave',
    'to_pdf_rics_por_status',
]
