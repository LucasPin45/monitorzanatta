"""
Gerador de arquivos PDF para o Monitor Parlamentar.
Funções de exportação de DataFrames para PDF profissional.

REGRA: Este módulo NÃO pode importar streamlit.
"""
import datetime
from io import BytesIO
from typing import Tuple, Optional
import pandas as pd

# Imports locais de utils (relativos)
from .text_utils import sanitize_text_pdf
from .date_utils import get_brasilia_now, days_since
from .links import camara_link_tramitacao
from .formatters import (
    PARTIDOS_RELATOR_ADVERSARIO,
    _verificar_relator_adversario,
    _obter_situacao_com_fallback,
    _categorizar_situacao_para_ordenacao,
)


def _padronizar_colunas_pdf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza colunas do DataFrame para geração de PDF.
    Garante colunas canônicas e evita heurísticas frágeis.
    """
    df_out = df.copy()
    
    # Mapeamento de nomes possíveis para nomes canônicos
    mapeamentos = {
        'Situação atual': ['Situação atual', 'Situacao atual', 'situacao_atual', 'status_descricaoSituacao', 'situacao', 'Situação (Raiz)'],
        'Data da última tramitação': ['Data do status', 'Data', 'DataStatus', 'data_status', 'status_dataHora', 'Data do status (raw)'],
        'Parado há (dias)': ['Parado (dias)', 'Parado há (dias)', 'dias_parado', 'parado_dias'],
        'Relator(a)': ['Relator(a)', 'Relator', 'relator'],
        'LinkTramitacao': ['LinkTramitacao', 'Link', 'link', 'url_tramitacao'],
        'LinkRelator': ['LinkRelator', 'link_relator'],
        'Órgão (sigla)': ['Órgão (sigla)', 'Orgao (sigla)', 'orgao_sigla', 'siglaOrgao'],
        'Proposição': ['Proposição', 'Proposicao', 'proposicao'],
        'Ementa': ['Ementa', 'ementa'],
        'Tema': ['Tema', 'tema'],
        'Andamento': ['Andamento (status)', 'Último andamento', 'Andamento', 'andamento', 'status_descricaoTramitacao'],
        # Colunas RIC
        'RIC_Ministerio': ['RIC_Ministerio', 'ric_ministerio', 'Ministerio'],
        'RIC_StatusResposta': ['RIC_StatusResposta', 'ric_status_resposta', 'StatusResposta'],
        'RIC_PrazoFim': ['RIC_PrazoFim', 'ric_prazo_fim', 'PrazoFim'],
        'RIC_DiasRestantes': ['RIC_DiasRestantes', 'ric_dias_restantes', 'DiasRestantes'],
    }
    
    for col_canonica, possiveis in mapeamentos.items():
        if col_canonica not in df_out.columns:
            for possivel in possiveis:
                if possivel in df_out.columns and possivel != col_canonica:
                    df_out[col_canonica] = df_out[possivel]
                    break
    
    # Garantir que LinkTramitacao existe
    if 'LinkTramitacao' not in df_out.columns:
        if 'id' in df_out.columns:
            df_out['LinkTramitacao'] = df_out['id'].astype(str).apply(camara_link_tramitacao)
        elif 'ID' in df_out.columns:
            df_out['LinkTramitacao'] = df_out['ID'].astype(str).apply(camara_link_tramitacao)
    
    # Garantir que Parado há (dias) existe
    if 'Parado há (dias)' not in df_out.columns:
        if 'DataStatus_dt' in df_out.columns:
            df_out['Parado há (dias)'] = df_out['DataStatus_dt'].apply(days_since)
        elif 'Data da última tramitação' in df_out.columns:
            dt = pd.to_datetime(df_out['Data da última tramitação'], errors='coerce', dayfirst=True)
            df_out['Parado há (dias)'] = dt.apply(days_since)
    
    return df_out


def _renderizar_card_proposicao(pdf, row, idx, col_proposicao, col_ementa, col_situacao, col_orgao,
                                 col_data, col_relator, col_tema, col_parado, col_link, mostrar_situacao=True):
    """Renderiza um card de proposição no PDF."""
    pdf.set_fill_color(245, 247, 250)
    
    # Número do registro
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(0, 51, 102)
    pdf.cell(8, 6, str(idx), fill=True, align='C')
    
    # Proposição (destaque)
    if col_proposicao and pd.notna(row.get(col_proposicao)):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 6, f"  {sanitize_text_pdf(str(row[col_proposicao]))}", ln=True)
    else:
        pdf.ln(6)
    
    pdf.set_x(20)
    
    # SITUAÇÃO COM FALLBACK
    if mostrar_situacao:
        situacao = _obter_situacao_com_fallback(row)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Situacao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        if 'Arquiv' in situacao:
            pdf.set_text_color(150, 50, 50)
        elif 'Pronta' in situacao or 'Sancion' in situacao:
            pdf.set_text_color(50, 150, 50)
        else:
            pdf.set_text_color(50, 50, 150)
        pdf.cell(0, 5, sanitize_text_pdf(situacao)[:60], ln=True)
        pdf.set_x(20)
    
    # Órgão
    if col_orgao and pd.notna(row.get(col_orgao)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Orgao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_orgao]))[:50], ln=True)
        pdf.set_x(20)
    
    # DATA DA ÚLTIMA TRAMITAÇÃO
    if col_data and pd.notna(row.get(col_data)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(35, 5, "Ultima tramitacao: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_data]))[:20], ln=True)
        pdf.set_x(20)
    
    # PARADO HÁ (DIAS)
    dias_parado = None
    if col_parado and pd.notna(row.get(col_parado)):
        try:
            dias_parado = int(row[col_parado])
        except (ValueError, TypeError):
            dias_parado = None
    
    if dias_parado is not None:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(28, 5, "Parado ha (dias): ", ln=False)
        pdf.set_font('Helvetica', 'B', 9)
        if dias_parado >= 30:
            pdf.set_text_color(180, 50, 50)
        elif dias_parado >= 15:
            pdf.set_text_color(200, 120, 0)
        elif dias_parado >= 7:
            pdf.set_text_color(180, 180, 0)
        else:
            pdf.set_text_color(50, 150, 50)
        pdf.cell(0, 5, str(dias_parado), ln=True)
        pdf.set_x(20)
    
    # RELATOR COM ALERTA DE ADVERSÁRIO
    relator_txt = row.get(col_relator, "") if col_relator else ""
    relator_formatado, is_adversario = _verificar_relator_adversario(relator_txt)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(20, 5, "Relator(a): ", ln=False)
    pdf.set_font('Helvetica', '', 9)
    
    # Obter link do relator se existir
    link_relator = None
    if 'LinkRelator' in row.index and pd.notna(row.get('LinkRelator')):
        link_relator = str(row.get('LinkRelator')).strip()
        if not link_relator.startswith('http'):
            link_relator = None
    
    if is_adversario:
        pdf.set_text_color(180, 50, 50)
        if link_relator:
            pdf.set_font('Helvetica', 'U', 9)
            pdf.write(5, sanitize_text_pdf(relator_formatado)[:50], link=link_relator)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 5, " [!] ADVERSARIO", ln=True)
        else:
            pdf.cell(0, 5, sanitize_text_pdf(f"{relator_formatado} [!] RELATOR ADVERSARIO")[:70], ln=True)
    elif relator_formatado == "Sem relator designado":
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, "Sem relator designado", ln=True)
    else:
        pdf.set_text_color(0, 0, 0)
        if link_relator:
            pdf.set_font('Helvetica', 'U', 9)
            pdf.write(5, sanitize_text_pdf(relator_formatado)[:50], link=link_relator)
            pdf.ln(5)
        else:
            pdf.cell(0, 5, sanitize_text_pdf(relator_formatado)[:50], ln=True)
    
    pdf.set_x(20)
    
    # INFORMAÇÕES DE RIC (se for RIC)
    sigla_tipo = row.get('siglaTipo', '') or row.get('sigla_tipo', '')
    if sigla_tipo == 'RIC':
        # Ministério
        ministerio = row.get('RIC_Ministerio', '') or ''
        if ministerio and str(ministerio).strip() and str(ministerio).strip() != 'nan':
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Ministerio: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 4, sanitize_text_pdf(str(ministerio))[:50], ln=True)
            pdf.set_x(20)
        
        # Status de resposta
        status_resp = row.get('RIC_StatusResposta', '') or ''
        if status_resp and str(status_resp).strip() and str(status_resp).strip() != 'nan':
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Status: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            if 'Respondido' in str(status_resp):
                pdf.set_text_color(50, 150, 50)
            else:
                pdf.set_text_color(200, 120, 0)
            pdf.cell(0, 4, sanitize_text_pdf(str(status_resp))[:30], ln=True)
            pdf.set_x(20)
        
        # Prazo e dias restantes
        dias_rest = row.get('RIC_DiasRestantes', None)
        prazo_fim = row.get('RIC_PrazoFim', None)
        if prazo_fim and pd.notna(prazo_fim):
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 4, "Prazo: ", ln=False)
            pdf.set_font('Helvetica', '', 8)
            try:
                if isinstance(prazo_fim, datetime.date):
                    prazo_str = prazo_fim.strftime("%d/%m/%Y")
                else:
                    prazo_str = str(prazo_fim)[:10]
            except:
                prazo_str = str(prazo_fim)[:10]
            
            if dias_rest is not None and pd.notna(dias_rest):
                try:
                    dias_int = int(dias_rest)
                    if dias_int < 0:
                        pdf.set_text_color(180, 50, 50)
                        pdf.cell(0, 4, f"{prazo_str} (VENCIDO ha {abs(dias_int)} dias)", ln=True)
                    elif dias_int <= 5:
                        pdf.set_text_color(200, 120, 0)
                        pdf.cell(0, 4, f"{prazo_str} ({dias_int} dias restantes - URGENTE)", ln=True)
                    else:
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 4, f"{prazo_str} ({dias_int} dias restantes)", ln=True)
                except:
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 4, prazo_str, ln=True)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 4, prazo_str, ln=True)
            pdf.set_x(20)
    
    # Tema
    if col_tema and pd.notna(row.get(col_tema)):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(20, 5, "Tema: ", ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, sanitize_text_pdf(str(row[col_tema]))[:40], ln=True)
        pdf.set_x(20)
    
    # Ementa
    if col_ementa and pd.notna(row.get(col_ementa)):
        ementa = sanitize_text_pdf(str(row[col_ementa]))
        if ementa and ementa.strip():
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "Ementa:", ln=True)
            pdf.set_x(20)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(170, 4, ementa[:300] + ('...' if len(ementa) > 300 else ''))
    
    # LINK CLICÁVEL
    link_url = None
    if col_link and pd.notna(row.get(col_link)):
        link_url = str(row[col_link]).strip()
    elif 'id' in row.index and pd.notna(row.get('id')):
        link_url = camara_link_tramitacao(str(row['id']))
    elif 'ID' in row.index and pd.notna(row.get('ID')):
        link_url = camara_link_tramitacao(str(row['ID']))
    
    if link_url and link_url.startswith('http'):
        pdf.set_x(20)
        pdf.set_font('Helvetica', 'I', 7)
        pdf.set_text_color(0, 0, 200)
        pdf.cell(10, 4, "Link: ", ln=False)
        pdf.set_font('Helvetica', 'U', 7)
        pdf.write(4, "Abrir tramitacao na Camara", link=link_url)
        pdf.ln(4)
    
    # Linha divisória
    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.2)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)


def to_pdf_bytes(df: pd.DataFrame, subtitulo: str = "Relatório") -> Tuple[bytes, str, str]:
    """
    Exporta DataFrame para PDF em formato de relatório profissional.
    VERSÃO 21 - PDFs otimizados para decisão política em gabinete.
    """
    colunas_excluir = ['Tipo', 'Ano', 'Alerta', 'ID', 'id', 'sinal', 'AnoStatus', 'MesStatus', 
                       'ids_proposicoes_autoria', 'ids_proposicoes_relatoria', 'id_evento',
                       'DataStatus_dt', 'Data do status (raw)', '_search', '_dt_sort',
                       '_situacao_group', '_categoria_info', '_ordem_prioridade', '_categoria_agrupada']
    
    try:
        from fpdf import FPDF
        
        df_proc = _padronizar_colunas_pdf(df)
        is_materias_por_situacao = "Situação" in subtitulo or "Situacao" in subtitulo
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df_proc.copy()
        col_data_sort = None
        for col in ['DataStatus_dt', 'Data da última tramitação', 'Data do status']:
            if col in df_sorted.columns:
                col_data_sort = col
                break
        
        if col_data_sort:
            if col_data_sort == 'DataStatus_dt':
                df_sorted = df_sorted.sort_values(col_data_sort, ascending=False, na_position='last')
            else:
                df_sorted['_dt_sort'] = pd.to_datetime(df_sorted[col_data_sort], errors='coerce', dayfirst=True)
                df_sorted = df_sorted.sort_values('_dt_sort', ascending=False, na_position='last')
        
        # Garantir remoção de colunas temporárias
        for col_temp in ['_dt_sort', '_search']:
            if col_temp in df_sorted.columns:
                df_sorted = df_sorted.drop(columns=[col_temp])
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 297, 25, 'F')
                self.set_font('Helvetica', 'B', 20)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Subtítulo e data
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, sanitize_text_pdf(subtitulo), ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # CABEÇALHO INFORMATIVO - FONTE E CRITÉRIO
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Ultima tramitacao (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de registros: {len(df_sorted)}", ln=True)
        pdf.ln(3)
        
        # Definir colunas para renderização (excluindo colunas temporárias)
        cols_mostrar = [c for c in df_sorted.columns if c not in colunas_excluir]
        
        col_proposicao = next((c for c in cols_mostrar if 'Proposi' in c or c == 'Proposição'), None)
        col_ementa = next((c for c in cols_mostrar if 'Ementa' in c or 'ementa' in c), None)
        col_situacao = next((c for c in cols_mostrar if 'Situa' in c), None)
        col_orgao = next((c for c in cols_mostrar if 'Org' in c and 'sigla' in c.lower()), None)
        col_data = next((c for c in cols_mostrar if 'Data' in c and 'última' in c.lower()), None)
        if not col_data:
            col_data = next((c for c in cols_mostrar if 'Data do status' in c or 'Data' in c), None)
        col_relator = next((c for c in cols_mostrar if 'Relator' in c), None)
        col_tema = next((c for c in cols_mostrar if 'Tema' in c), None)
        col_parado = next((c for c in cols_mostrar if 'Parado' in c and 'dias' in c.lower()), None)
        col_link = next((c for c in ['LinkTramitacao', 'Link'] if c in df_sorted.columns), None)
        
        # AGRUPAMENTO POR SITUAÇÃO COM ORDENAÇÃO PERSONALIZADA
        if is_materias_por_situacao and col_situacao:
            df_sorted['_situacao_group'] = df_sorted.apply(_obter_situacao_com_fallback, axis=1)
            
            # Aplicar categorização para ordenação
            df_sorted['_categoria_info'] = df_sorted['_situacao_group'].apply(_categorizar_situacao_para_ordenacao)
            df_sorted['_ordem_prioridade'] = df_sorted['_categoria_info'].apply(lambda x: x[0])
            df_sorted['_categoria_agrupada'] = df_sorted['_categoria_info'].apply(lambda x: x[1])
            
            # Ordenar por prioridade da categoria e depois por data dentro de cada categoria
            if '_dt_sort' not in df_sorted.columns and col_data_sort:
                df_sorted['_dt_sort'] = pd.to_datetime(df_sorted[col_data_sort], errors='coerce', dayfirst=True)
            
            # Ordenar - usar _dt_sort só se existir
            if '_dt_sort' in df_sorted.columns:
                df_sorted = df_sorted.sort_values(['_ordem_prioridade', '_dt_sort'], ascending=[True, False], na_position='last')
                # Remover _dt_sort após ordenação
                df_sorted = df_sorted.drop(columns=['_dt_sort'])
            else:
                df_sorted = df_sorted.sort_values('_ordem_prioridade', ascending=True, na_position='last')
            
            # Agrupar por categoria agrupada (não pela situação original)
            categorias_ordenadas = df_sorted.groupby('_categoria_agrupada', sort=False).agg({
                '_ordem_prioridade': 'first',
                '_situacao_group': 'count'
            }).reset_index()
            categorias_ordenadas = categorias_ordenadas.sort_values('_ordem_prioridade')
            
            registro_num = 0
            for _, cat_row in categorias_ordenadas.iterrows():
                categoria = cat_row['_categoria_agrupada']
                qtd_categoria = cat_row['_situacao_group']
                
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                # Cabeçalho da categoria principal
                pdf.ln(3)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(255, 255, 255)
                categoria_txt = sanitize_text_pdf(str(categoria))
                pdf.cell(0, 8, f"  {categoria_txt} ({qtd_categoria})", ln=True, fill=True)
                pdf.ln(2)
                
                df_categoria = df_sorted[df_sorted['_categoria_agrupada'] == categoria]
                
                # Subcategorias (situações originais dentro da categoria)
                situacoes_na_categoria = df_categoria.groupby('_situacao_group', sort=False).size()
                
                for situacao_original, qtd_sit in situacoes_na_categoria.items():
                    # Se a categoria tem múltiplas situações originais, mostrar subcabeçalho
                    if len(situacoes_na_categoria) > 1:
                        if pdf.get_y() > 245:
                            pdf.add_page()
                            pdf.set_y(30)
                        
                        pdf.set_fill_color(220, 230, 240)
                        pdf.set_font('Helvetica', 'B', 9)
                        pdf.set_text_color(0, 51, 102)
                        sit_txt = sanitize_text_pdf(str(situacao_original))[:65]
                        pdf.cell(0, 6, f"    {sit_txt} ({qtd_sit})", ln=True, fill=True)
                        pdf.ln(1)
                    
                    df_grupo = df_categoria[df_categoria['_situacao_group'] == situacao_original]
                    
                    for _, row in df_grupo.head(100).iterrows():
                        registro_num += 1
                        if registro_num > 300:
                            break
                        
                        if pdf.get_y() > 250:
                            pdf.add_page()
                            pdf.set_y(30)
                        
                        _renderizar_card_proposicao(
                            pdf, row, registro_num,
                            col_proposicao, col_ementa, col_situacao, col_orgao,
                            col_data, col_relator, col_tema, col_parado, col_link,
                            mostrar_situacao=False
                        )
                    
                    if registro_num > 300:
                        break
                
                if registro_num > 300:
                    break
        else:
            # Remover colunas temporárias antes de iterar
            for col_temp in ['_dt_sort', '_search']:
                if col_temp in df_sorted.columns:
                    df_sorted = df_sorted.drop(columns=[col_temp])
            
            for idx, (_, row) in enumerate(df_sorted.head(300).iterrows()):
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_y(30)
                
                _renderizar_card_proposicao(
                    pdf, row, idx + 1,
                    col_proposicao, col_ementa, col_situacao, col_orgao,
                    col_data, col_relator, col_tema, col_parado, col_link,
                    mostrar_situacao=True
                )
        
        if len(df) > 300:
            pdf.ln(5)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"* Exibindo 300 de {len(df)} registros. Exporte em XLSX para lista completa.", ln=True, align='C')
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except ImportError:
        # fpdf não instalado - gerar PDF simples de erro
        raise Exception("Biblioteca fpdf2 não disponível. Instale com: pip install fpdf2")
    except Exception as e:
        # Propagar o erro para debug - NÃO fazer fallback para CSV
        import traceback
        raise Exception(f"Erro ao gerar PDF: {str(e)} | Traceback: {traceback.format_exc()}")


def to_pdf_linha_do_tempo(df: pd.DataFrame, proposicao_info: dict) -> Tuple[bytes, str, str]:
    """
    Gera PDF de linha do tempo de tramitação de uma proposição.
    """
    try:
        from fpdf import FPDF
        
        proposicao = proposicao_info.get("proposicao", "—")
        situacao = proposicao_info.get("situacao", "—")
        orgao = proposicao_info.get("orgao", "—")
        regime = proposicao_info.get("regime", "")
        prop_id = proposicao_info.get("id", "")
        
        class RelatorioLinhaDoTempoPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioLinhaDoTempoPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Título: Linha do Tempo
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, f"Linha do Tempo - ID {prop_id}", ln=True, align='C')
        
        # Data de geração
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        # Fonte
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Ultima tramitacao (mais recente primeiro)", ln=True, align='C')
        
        # Linha separadora
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # ============================================================
        # BLOCO DE IDENTIFICAÇÃO DA MATÉRIA (EM DESTAQUE)
        # ============================================================
        
        # Proposição (destaque principal)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, sanitize_text_pdf(proposicao) if proposicao else "—", ln=True, align='C')
        
        # Situação atual (em destaque)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Situacao atual:", ln=True, align='C')
        
        # Cor da situação baseada no texto
        pdf.set_font('Helvetica', 'B', 11)
        if 'Arquiv' in situacao:
            pdf.set_text_color(150, 50, 50)  # Vermelho
        elif 'Pronta' in situacao or 'Sancion' in situacao:
            pdf.set_text_color(50, 150, 50)  # Verde
        elif 'Aguardando' in situacao:
            pdf.set_text_color(50, 50, 150)  # Azul
        else:
            pdf.set_text_color(80, 80, 80)  # Cinza
        pdf.cell(0, 7, sanitize_text_pdf(situacao)[:80], ln=True, align='C')
        
        # Órgão atual
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Orgao: {sanitize_text_pdf(orgao)}", ln=True, align='C')
        
        # Regime de tramitação (se disponível)
        if regime:
            pdf.cell(0, 6, f"Regime: {sanitize_text_pdf(regime)}", ln=True, align='C')
        
        pdf.ln(4)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        # ============================================================
        # TRAMITAÇÕES (SEM CAMPO "SITUAÇÃO" EM CADA BLOCO)
        # ============================================================
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True)
        pdf.ln(3)
        
        for idx, (_, row) in enumerate(df.iterrows()):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(30)
            
            # Número do registro (badge)
            pdf.set_fill_color(0, 51, 102)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(8, 6, str(idx + 1), fill=True, align='C')
            pdf.ln(8)
            
            pdf.set_x(20)
            
            # Última tramitação (data/hora)
            data_val = row.get("Data", "—")
            hora_val = row.get("Hora", "")
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(35, 5, "Ultima tramitacao: ", ln=False)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(0, 0, 0)
            data_hora_str = f"{data_val}"
            if hora_val:
                data_hora_str += f" {hora_val}"
            pdf.cell(0, 5, sanitize_text_pdf(data_hora_str)[:30], ln=True)
            pdf.set_x(20)
            
            # Calcular "Parado há (dias)" baseado na data
            dias_parado = None
            try:
                if data_val and data_val != "—":
                    dt_tram = datetime.datetime.strptime(data_val, "%d/%m/%Y")
                    hoje = datetime.datetime.now()
                    dias_parado = (hoje - dt_tram).days
            except:
                pass
            
            if dias_parado is not None:
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(28, 5, "Parado ha (dias): ", ln=False)
                pdf.set_font('Helvetica', 'B', 9)
                if dias_parado >= 30:
                    pdf.set_text_color(180, 50, 50)  # Vermelho
                elif dias_parado >= 15:
                    pdf.set_text_color(200, 120, 0)  # Laranja
                elif dias_parado >= 7:
                    pdf.set_text_color(180, 180, 0)  # Amarelo
                else:
                    pdf.set_text_color(50, 150, 50)  # Verde
                pdf.cell(0, 5, str(dias_parado), ln=True)
                pdf.set_x(20)
            
            # Órgão
            orgao_val = row.get("Órgão", "—")
            if orgao_val and orgao_val != "—":
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(15, 5, "Orgao: ", ln=False)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, sanitize_text_pdf(str(orgao_val))[:50], ln=True)
                pdf.set_x(20)
            
            # Relator - mantido como "Sem relator designado" por padrão na linha do tempo
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(20, 5, "Relator(a): ", ln=False)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, "Sem relator designado", ln=True)
            pdf.set_x(20)
            
            # Descrição da tramitação (se houver)
            tramitacao = row.get("Tramitação", "")
            if tramitacao and str(tramitacao).strip():
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(22, 5, "Tramitacao: ", ln=False)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(60, 60, 60)
                
                # Quebrar texto longo
                texto_tram = sanitize_text_pdf(str(tramitacao))[:200]
                pdf.multi_cell(160, 4, texto_tram)
            
            pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except ImportError:
        raise Exception("Biblioteca fpdf2 não disponível. Instale com: pip install fpdf2")
    except Exception as e:
        import traceback
        raise Exception(f"Erro ao gerar PDF da Linha do Tempo: {str(e)} | Traceback: {traceback.format_exc()}")


def to_pdf_autoria_relatoria(df: pd.DataFrame, fetch_proposicao_completa_func=None) -> Tuple[bytes, str, str]:
    """PDF específico para Autoria e Relatoria na Pauta - formato de gabinete com dados completos."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Autoria e Relatoria na Pauta", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Data do evento (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df.copy()
        if 'data' in df_sorted.columns:
            df_sorted['_data_sort'] = pd.to_datetime(df_sorted['data'], errors='coerce', dayfirst=True)
            df_sorted = df_sorted.sort_values('_data_sort', ascending=False)
        
        # Função auxiliar para extrair IDs
        def extrair_ids(texto_ids):
            ids = []
            if pd.isna(texto_ids) or str(texto_ids).strip() in ('', 'nan'):
                return ids
            for pid in str(texto_ids).split(';'):
                pid = pid.strip()
                if pid and pid.isdigit():
                    ids.append(pid)
            return ids
        
        def buscar_info_proposicao(pid):
            if fetch_proposicao_completa_func:
                try:
                    return fetch_proposicao_completa_func(str(pid))
                except:
                    return {}
            return {}
        
        registros_autoria = []
        registros_relatoria = []
        
        for _, row in df_sorted.iterrows():
            data = str(row.get('data', '-'))
            hora = str(row.get('hora', '-')) if pd.notna(row.get('hora')) else '-'
            orgao_sigla = str(row.get('orgao_sigla', '-'))
            orgao_nome = str(row.get('orgao_nome', ''))
            local = f"{orgao_sigla}" + (f" - {orgao_nome}" if orgao_nome and orgao_nome != orgao_sigla else "")
            id_evento = str(row.get('id_evento', ''))
            link_evento = f"https://www.camara.leg.br/evento-legislativo/{id_evento}" if id_evento and id_evento != 'nan' else ""
            
            ids_autoria = extrair_ids(row.get('ids_proposicoes_autoria', ''))
            ids_relatoria = extrair_ids(row.get('ids_proposicoes_relatoria', ''))
            
            if ids_autoria:
                materias_autoria = []
                for pid in ids_autoria:
                    info = buscar_info_proposicao(pid)
                    sigla = f"{info.get('sigla', '')} {info.get('numero', '')}/{info.get('ano', '')}"
                    ementa = info.get('ementa', '')
                    situacao = info.get('status_descricaoSituacao', '')
                    relator_info = info.get('relator', {}) or {}
                    relator_nome = relator_info.get('nome', '')
                    relator_partido = relator_info.get('partido', '')
                    relator_uf = relator_info.get('uf', '')
                    relator_str = f"{relator_nome} ({relator_partido}/{relator_uf})" if relator_nome else "Sem relator designado"
                    link_materia = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"
                    _, is_adversario = _verificar_relator_adversario(relator_str)
                    
                    materias_autoria.append({
                        'sigla': sigla.strip(),
                        'ementa': ementa,
                        'situacao': situacao if situacao else "Situacao nao informada",
                        'relator': relator_str,
                        'link': link_materia,
                        'is_adversario': is_adversario
                    })
                
                registros_autoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'link_evento': link_evento, 'materias': materias_autoria
                })
            
            if ids_relatoria:
                materias_relatoria = []
                for pid in ids_relatoria:
                    info = buscar_info_proposicao(pid)
                    sigla = f"{info.get('sigla', '')} {info.get('numero', '')}/{info.get('ano', '')}"
                    ementa = info.get('ementa', '')
                    situacao = info.get('status_descricaoSituacao', '')
                    url_teor = info.get('urlInteiroTeor', '')
                    link_materia = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"
                    
                    parecer_info = ""
                    tramitacoes = info.get('tramitacoes', [])
                    for tram in tramitacoes[:10]:
                        desc = tram.get('descricaoTramitacao', '') or ''
                        desp = tram.get('despacho', '') or ''
                        if 'parecer' in desc.lower() or 'parecer' in desp.lower():
                            parecer_info = f"{desc} - {desp}".strip(' -')
                            break
                    
                    materias_relatoria.append({
                        'sigla': sigla.strip(),
                        'ementa': ementa,
                        'situacao': situacao,
                        'parecer': parecer_info,
                        'link': link_materia,
                        'link_teor': url_teor
                    })
                
                registros_relatoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'link_evento': link_evento, 'materias': materias_relatoria
                })
        
        # === SEÇÃO AUTORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 100, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  AUTORIA DA DEPUTADA ({len(registros_autoria)} reuniao(oes))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_autoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de autoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_autoria, 1):
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(0, 100, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(8, 6, str(idx), fill=True, align='C')
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 6, f"  {reg['data']} as {reg['hora']}", ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:70], ln=True)
                
                for mat in reg['materias']:
                    if pdf.get_y() > 250:
                        pdf.add_page()
                        pdf.set_y(30)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 5, sanitize_text_pdf(mat['sigla']), ln=True)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Situacao: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    sit = mat['situacao'] or '-'
                    if 'Arquiv' in sit:
                        pdf.set_text_color(150, 50, 50)
                    elif 'Pronta' in sit:
                        pdf.set_text_color(50, 150, 50)
                    else:
                        pdf.set_text_color(50, 50, 150)
                    pdf.cell(0, 4, sanitize_text_pdf(sit)[:55], ln=True)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Relator: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    if mat.get('is_adversario'):
                        pdf.set_text_color(180, 50, 50)
                        pdf.cell(0, 4, sanitize_text_pdf(mat['relator'] + " [!] ADVERSARIO")[:60], ln=True)
                    elif mat['relator'] == "Sem relator designado":
                        pdf.set_text_color(150, 150, 150)
                        pdf.cell(0, 4, "Sem relator designado", ln=True)
                    else:
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 4, sanitize_text_pdf(mat['relator'])[:50], ln=True)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', '', 7)
                    pdf.set_text_color(60, 60, 60)
                    ementa = mat['ementa'][:250] + ('...' if len(mat['ementa']) > 250 else '')
                    pdf.multi_cell(160, 3.5, sanitize_text_pdf(ementa))
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'I', 6)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(3, "Abrir tramitacao", link=mat['link'])
                    pdf.ln(4)
                
                if reg['link_evento']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(4, "Ver pauta do evento", link=reg['link_evento'])
                    pdf.ln(4)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        pdf.ln(5)
        
        # === SEÇÃO RELATORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  RELATORIA DA DEPUTADA ({len(registros_relatoria)} reuniao(oes))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_relatoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de relatoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_relatoria, 1):
                if pdf.get_y() > 240:
                    pdf.add_page()
                    pdf.set_y(30)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(8, 6, str(idx), fill=True, align='C')
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, f"  {reg['data']} as {reg['hora']}", ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:70], ln=True)
                
                for mat in reg['materias']:
                    if pdf.get_y() > 250:
                        pdf.add_page()
                        pdf.set_y(30)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 5, sanitize_text_pdf(mat['sigla']), ln=True)
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(18, 4, "Situacao: ", ln=False)
                    pdf.set_font('Helvetica', '', 8)
                    sit = mat['situacao'] or '-'
                    if 'Arquiv' in sit:
                        pdf.set_text_color(150, 50, 50)
                    elif 'Pronta' in sit:
                        pdf.set_text_color(50, 150, 50)
                    else:
                        pdf.set_text_color(50, 50, 150)
                    pdf.cell(0, 4, sanitize_text_pdf(sit)[:55], ln=True)
                    
                    if mat['parecer']:
                        pdf.set_x(25)
                        pdf.set_font('Helvetica', 'B', 8)
                        pdf.set_text_color(150, 100, 0)
                        pdf.cell(18, 4, "Parecer: ", ln=False)
                        pdf.set_font('Helvetica', '', 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.multi_cell(145, 4, sanitize_text_pdf(mat['parecer'])[:150])
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', '', 7)
                    pdf.set_text_color(60, 60, 60)
                    ementa = mat['ementa'][:250] + ('...' if len(mat['ementa']) > 250 else '')
                    pdf.multi_cell(160, 3.5, sanitize_text_pdf(ementa))
                    
                    pdf.set_x(25)
                    pdf.set_font('Helvetica', 'I', 6)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(3, "Abrir tramitacao", link=mat['link'])
                    
                    if mat.get('link_teor'):
                        pdf.write(3, " | ")
                        pdf.write(3, "Inteiro teor", link=mat['link_teor'])
                    
                    pdf.ln(4)
                
                if reg['link_evento']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(0, 0, 200)
                    pdf.write(4, "Ver pauta do evento", link=reg['link_evento'])
                    pdf.ln(4)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de autoria/relatoria: {str(e)}")


def to_pdf_comissoes_estrategicas(df: pd.DataFrame) -> Tuple[bytes, str, str]:
    """PDF específico para Comissões Estratégicas - formato de gabinete."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Comissoes Estrategicas - Pautas", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Ordenado por: Data do evento (mais recente primeiro)", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de reunioes: {len(df)}", ln=True)
        pdf.ln(3)
        
        df_sorted = df.copy()
        if 'data' in df_sorted.columns:
            df_sorted['_data_sort'] = pd.to_datetime(df_sorted['data'], errors='coerce', dayfirst=True)
            df_sorted = df_sorted.sort_values('_data_sort', ascending=False)
        
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(30)
            
            data = str(row.get('data', '-'))
            hora = str(row.get('hora', '-')) if pd.notna(row.get('hora')) else '-'
            orgao_sigla = str(row.get('orgao_sigla', '-'))
            orgao_nome = str(row.get('orgao_nome', ''))
            tipo_evento = str(row.get('tipo_evento', ''))
            id_evento = str(row.get('id_evento', ''))
            link = f"https://www.camara.leg.br/evento-legislativo/{id_evento}" if id_evento and id_evento != 'nan' else ""
            
            props_autoria = str(row.get('proposicoes_autoria', ''))
            props_relatoria = str(row.get('proposicoes_relatoria', ''))
            palavras_chave = str(row.get('palavras_chave_encontradas', ''))
            
            tem_relatoria = props_relatoria and props_relatoria.strip() and props_relatoria != 'nan'
            tem_autoria = props_autoria and props_autoria.strip() and props_autoria != 'nan'
            
            pdf.set_font('Helvetica', 'B', 9)
            if tem_relatoria:
                pdf.set_fill_color(0, 51, 102)
            elif tem_autoria:
                pdf.set_fill_color(0, 100, 0)
            else:
                pdf.set_fill_color(100, 100, 100)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(8, 6, str(idx), fill=True, align='C')
            
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 6, f"  {orgao_sigla} - {data} as {hora}", ln=True)
            
            pdf.set_x(20)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(100, 100, 100)
            if tipo_evento and tipo_evento != 'nan':
                pdf.cell(0, 4, sanitize_text_pdf(tipo_evento)[:80], ln=True)
            if orgao_nome and orgao_nome != orgao_sigla:
                pdf.set_x(20)
                pdf.cell(0, 4, sanitize_text_pdf(orgao_nome)[:80], ln=True)
            
            if tem_relatoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 5, ">>> RELATORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_relatoria)[:400])
            
            if tem_autoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 5, ">>> AUTORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_autoria)[:400])
            
            if palavras_chave and palavras_chave.strip() and palavras_chave != 'nan':
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_text_color(150, 100, 0)
                pdf.cell(30, 4, "Palavras-chave: ", ln=False)
                pdf.set_font('Helvetica', '', 8)
                pdf.cell(0, 4, sanitize_text_pdf(palavras_chave)[:60], ln=True)
            
            if link:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'I', 7)
                pdf.set_text_color(0, 0, 200)
                pdf.write(4, "Ver pauta do evento", link=link)
                pdf.ln(4)
            
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de comissões estratégicas: {str(e)}")


def to_pdf_palavras_chave(df: pd.DataFrame) -> Tuple[bytes, str, str]:
    """Gera PDF de palavras-chave na pauta, organizado por Comissão."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 25, 'F')
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(255, 255, 255)
                self.set_y(8)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Palavras-chave na Pauta", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        proposicoes_por_comissao = {}
        todas_proposicoes = set()
        
        for _, row in df.iterrows():
            props_str = row.get("proposicoes_palavras_chave", "") or ""
            
            if not props_str or pd.isna(props_str):
                continue
            
            for prop_detail in str(props_str).split("; "):
                if "|||" not in prop_detail:
                    continue
                    
                partes = prop_detail.split("|||")
                
                materia = partes[0].strip() if len(partes) > 0 else ""
                palavras = partes[1].strip() if len(partes) > 1 else ""
                ementa = partes[2].strip() if len(partes) > 2 else ""
                link = partes[3].strip() if len(partes) > 3 else ""
                
                relator_raw = partes[4].strip() if len(partes) > 4 else ""
                if not relator_raw or len(relator_raw) < 5:
                    relator = "Sem relator designado"
                else:
                    relator = relator_raw
                
                comissao = partes[5].strip() if len(partes) > 5 else row.get("orgao_sigla", "Outras")
                nome_comissao = partes[6].strip() if len(partes) > 6 else ""
                data_evento = partes[7].strip() if len(partes) > 7 else ""
                
                data_formatada = ""
                if data_evento and len(data_evento) >= 10:
                    try:
                        dt = datetime.datetime.strptime(data_evento[:10], "%Y-%m-%d")
                        data_formatada = dt.strftime("%d/%m/%Y")
                    except:
                        data_formatada = data_evento
                
                if not materia:
                    continue
                
                chave_unica = f"{materia}_{comissao}"
                if chave_unica in todas_proposicoes:
                    continue
                todas_proposicoes.add(chave_unica)
                
                if comissao not in proposicoes_por_comissao:
                    proposicoes_por_comissao[comissao] = {
                        "nome": nome_comissao,
                        "proposicoes": []
                    }
                
                proposicoes_por_comissao[comissao]["proposicoes"].append({
                    "materia": materia,
                    "palavras": palavras,
                    "ementa": ementa,
                    "link": link,
                    "relator": relator,
                    "data": data_formatada
                })
        
        comissoes_ordenadas = sorted(proposicoes_por_comissao.keys())
        total_props = sum(len(c["proposicoes"]) for c in proposicoes_por_comissao.values())
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de materias encontradas: {total_props}", ln=True)
        pdf.cell(0, 6, f"Comissoes: {len(comissoes_ordenadas)}", ln=True)
        pdf.ln(4)
        
        for comissao in comissoes_ordenadas:
            dados = proposicoes_por_comissao[comissao]
            props = dados["proposicoes"]
            nome_comissao = dados["nome"]
            
            if not props:
                continue
            
            pdf.set_fill_color(0, 102, 153)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 11)
            titulo_comissao = f"  {sanitize_text_pdf(comissao)}"
            if nome_comissao:
                titulo_comissao += f" - {sanitize_text_pdf(nome_comissao)}"
            titulo_comissao += f" ({len(props)} materia{'s' if len(props) > 1 else ''})"
            pdf.cell(0, 8, titulo_comissao, ln=True, fill=True)
            pdf.ln(3)
            
            for idx, prop in enumerate(props, 1):
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(0, 51, 102)
                materia_text = sanitize_text_pdf(prop.get('materia', '') or '')
                data_text = (prop.get("data", "") or "").strip()
                if data_text:
                    pdf.cell(0, 6, f"{idx}. [{data_text}] {materia_text}", ln=True)
                else:
                    pdf.cell(0, 6, f"{idx}. {materia_text}", ln=True)
                
                palavras = (prop.get("palavras", "") or "").strip()
                if palavras:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(180, 0, 0)
                    pdf.cell(0, 5, f"   Palavras-chave: {sanitize_text_pdf(palavras)}", ln=True)
                
                ementa = (prop.get("ementa", "") or "").strip()
                if ementa:
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(60, 60, 60)
                    ementa_text = sanitize_text_pdf(ementa)
                    if len(ementa_text) > 250:
                        ementa_text = ementa_text[:250] + "..."
                    pdf.multi_cell(0, 4, f"   {ementa_text}")
                    pdf.ln(1)
                
                relator_raw = (prop.get("relator", "") or "").strip()
                relator_valido = (
                    relator_raw 
                    and len(relator_raw) > 5 
                    and "Sem relator" not in relator_raw 
                    and "(-)" not in relator_raw
                )
                
                pdf.set_font('Helvetica', 'B', 9)
                if relator_valido:
                    pdf.set_text_color(0, 100, 0)
                    texto_relator = "   Relator(a): " + sanitize_text_pdf(relator_raw)
                else:
                    pdf.set_text_color(128, 128, 128)
                    texto_relator = "   Relator(a): Sem relator designado"
                
                pdf.cell(0, 5, texto_relator, ln=True)
                
                link = (prop.get("link", "") or "").strip()
                if link:
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(0, 0, 180)
                    pdf.cell(0, 4, f"   {link}", ln=True)
                
                pdf.ln(3)
            
            pdf.ln(2)
        
        pdf_bytes = pdf.output()
        return (bytes(pdf_bytes), "application/pdf", "pdf")
        
    except Exception as e:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 10, f"Erro ao gerar PDF: {str(e)}", ln=True)
        pdf_bytes = pdf.output()
        return (bytes(pdf_bytes), "application/pdf", "pdf")


def to_pdf_rics_por_status(df: pd.DataFrame, titulo: str = "RICs - Requerimentos de Informação") -> Tuple[bytes, str, str]:
    """Gera PDF de RICs organizado por blocos de status."""
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                self.set_fill_color(0, 51, 102)
                self.rect(0, 0, 210, 22, 'F')
                self.set_font('Helvetica', 'B', 16)
                self.set_text_color(255, 255, 255)
                self.set_y(6)
                self.cell(0, 10, 'MONITOR PARLAMENTAR', align='C')
                self.ln(18)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.set_x(10)
                self.cell(60, 10, 'Desenvolvido por Lucas Pinheiro', align='L')
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        pdf.set_y(28)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, sanitize_text_pdf(titulo), ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Fonte: dadosabertos.camara.leg.br | Prazo constitucional: 30 dias apos remessa", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de RICs: {len(df)}", ln=True)
        pdf.ln(3)
        
        col_status = None
        for c in ['Status', 'RIC_StatusResposta']:
            if c in df.columns:
                col_status = c
                break
        
        if not col_status:
            col_status = 'Status'
            df[col_status] = 'Aguardando resposta'
        
        blocos = [
            {'titulo': 'AGUARDANDO RESPOSTA (No Prazo)', 'filtro': lambda x: x == 'Aguardando resposta', 'cor': (255, 193, 7)},
            {'titulo': 'FORA DO PRAZO (Sem Resposta)', 'filtro': lambda x: x == 'Fora do prazo', 'cor': (220, 53, 69)},
            {'titulo': 'EM TRAMITACAO NA CAMARA', 'filtro': lambda x: x == 'Em tramitação na Câmara', 'cor': (108, 117, 125)},
            {'titulo': 'RESPONDIDOS', 'filtro': lambda x: x in ['Respondido', 'Respondido fora do prazo'], 'cor': (40, 167, 69)},
        ]
        
        col_ric = next((c for c in ['RIC', 'Proposicao'] if c in df.columns), None)
        col_ministerio = next((c for c in ['Ministério', 'RIC_Ministerio'] if c in df.columns), None)
        col_prazo = next((c for c in ['Prazo', 'RIC_PrazoStr'] if c in df.columns), None)
        col_ementa = next((c for c in ['ementa', 'Ementa'] if c in df.columns), None)
        col_situacao = next((c for c in ['Situação atual', 'Situacao atual'] if c in df.columns), None)
        col_data = next((c for c in ['Última tramitação', 'Data do status'] if c in df.columns), None)
        
        for bloco in blocos:
            df_bloco = df[df[col_status].apply(bloco['filtro'])].copy()
            
            if df_bloco.empty:
                continue
            
            pdf.ln(4)
            pdf.set_fill_color(*bloco['cor'])
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, f"  {sanitize_text_pdf(bloco['titulo'])} ({len(df_bloco)})", ln=True, fill=True)
            pdf.ln(3)
            
            if col_data and col_data in df_bloco.columns:
                df_bloco['_sort_dt'] = pd.to_datetime(df_bloco[col_data], errors='coerce', dayfirst=True)
                df_bloco = df_bloco.sort_values('_sort_dt', ascending=False)
            
            for idx, (_, row) in enumerate(df_bloco.iterrows()):
                if pdf.get_y() > 250:
                    pdf.add_page()
                
                ric_nome = sanitize_text_pdf(str(row.get(col_ric, ''))) if col_ric else "RIC"
                
                pdf.set_fill_color(245, 245, 245)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, f"{idx+1}. {ric_nome}", ln=True)
                
                if col_ministerio:
                    ministerio = sanitize_text_pdf(str(row.get(col_ministerio, '') or 'Não identificado'))
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(60, 60, 60)
                    pdf.cell(0, 5, f"Ministerio: {ministerio}", ln=True)
                
                prazo_display = "-"
                if col_prazo:
                    prazo_val = row.get(col_prazo, '')
                    if prazo_val and str(prazo_val).strip() and str(prazo_val) != '-':
                        prazo_display = sanitize_text_pdf(str(prazo_val))
                    else:
                        prazo_fim = row.get('RIC_PrazoFim') or row.get('RIC_PrazoStr', '')
                        if prazo_fim and str(prazo_fim).strip():
                            try:
                                if hasattr(prazo_fim, 'strftime'):
                                    prazo_display = f"ate {prazo_fim.strftime('%d/%m/%Y')}"
                                else:
                                    prazo_display = sanitize_text_pdf(str(prazo_fim))
                            except:
                                pass
                        dias = row.get('RIC_DiasRestantes')
                        if dias is not None and pd.notna(dias) and prazo_display != "-":
                            try:
                                dias_int = int(dias)
                                if dias_int < 0:
                                    prazo_display += f" ({abs(dias_int)}d restantes)"
                                else:
                                    prazo_display += f" ({dias_int}d restantes)"
                            except:
                                pass
                pdf.cell(0, 5, f"Prazo: {prazo_display}", ln=True)
                
                if col_situacao:
                    sit = sanitize_text_pdf(str(row.get(col_situacao, '') or '-'))
                    pdf.cell(0, 5, f"Situacao: {sit}", ln=True)
                
                if col_data:
                    data = sanitize_text_pdf(str(row.get(col_data, '') or '-'))
                    pdf.cell(0, 5, f"Ultima tramitacao: {data}", ln=True)
                
                if col_ementa:
                    ementa = str(row.get(col_ementa, '') or '')
                    if ementa:
                        ementa_trunc = sanitize_text_pdf(ementa[:200] + "..." if len(ementa) > 200 else ementa)
                        pdf.set_font('Helvetica', 'I', 8)
                        pdf.set_text_color(80, 80, 80)
                        pdf.multi_cell(0, 4, f"Ementa: {ementa_trunc}")
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(3)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF de RICs: {str(e)}")
