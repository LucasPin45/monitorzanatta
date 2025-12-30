# monitor_sistema_jz.py - v19
# ============================================================
# Monitor Legislativo – Dep. Júlia Zanatta (Streamlit)
# VERSÃO 19: PDFs profissionais para Autoria/Relatoria e Comissões
# ============================================================

import datetime
import concurrent.futures
import time
import unicodedata
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
import re
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend não-interativo

# Timezone de Brasília
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")

def get_brasilia_now():
    """Retorna datetime atual no fuso de Brasília."""
    return datetime.datetime.now(TZ_BRASILIA)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559

HEADERS = {"User-Agent": "MonitorZanatta/19.0 (gabinete-julia-zanatta)"}

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Armas", "Arma", "Aborto", "Conanda", "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]

STATUS_PREDEFINIDOS = [
    "Arquivada",
    "Aguardando Despacho do Presidente da Câmara dos Deputados",
    "Aguardando Designação de Relator(a)",
    "Aguardando Parecer de Relator(a)",
    "Tramitando em Conjunto",
    "Pronta para Pauta",
    "Aguardando Deliberação",
    "Aguardando Apreciação",
    "Aguardando Distribuição",
    "Aguardando Designação",
    "Aguardando Votação",
]

MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

PARTIDOS_RELATOR_ADVERSARIO = {"PT", "PV", "PSB", "PCDOB", "PSOL", "REDE"}

# Temas para categorização (palavras-chave por tema)
TEMAS_CATEGORIAS = {
    "Saúde": [
        "vacina", "saude", "saúde", "hospital", "medicamento", "sus", "anvisa", 
        "medico", "médico", "enfermeiro", "farmacia", "farmácia", "tratamento",
        "doenca", "doença", "epidemia", "pandemia", "leito", "uti", "plano de saude"
    ],
    "Segurança Pública": [
        "arma", "armas", "seguranca", "segurança", "policia", "polícia", "violencia", 
        "violência", "crime", "criminal", "penal", "prisao", "prisão", "preso",
        "bandido", "trafic", "roubo", "furto", "homicidio", "homicídio", "legítima defesa",
        "porte", "posse de arma", "cac", "atirador", "caçador", "colecionador"
    ],
    "Economia e Tributos": [
        "pix", "drex", "imposto", "irpf", "tributo", "economia", "financeiro",
        "taxa", "contribuicao", "contribuição", "fiscal", "orcamento", "orçamento",
        "divida", "dívida", "inflacao", "inflação", "juros", "banco", "credito", "crédito",
        "renda", "salario", "salário", "aposentadoria", "previdencia", "previdência",
        "inss", "fgts", "trabalhista", "clt", "emprego", "desemprego"
    ],
    "Família e Costumes": [
        "aborto", "conanda", "crianca", "criança", "menor", "familia", "família",
        "genero", "gênero", "ideologia", "lgb", "trans", "casamento", "uniao", "união",
        "mae", "mãe", "pai", "filho", "maternidade", "paternidade", "nascituro",
        "vida", "pro-vida", "pró-vida", "adocao", "adoção", "tutela", "guarda"
    ],
    "Educação": [
        "educacao", "educação", "escola", "ensino", "universidade", "professor",
        "aluno", "estudante", "enem", "vestibular", "mec", "fundeb", "creche",
        "alfabetizacao", "alfabetização", "curriculo", "currículo", "didatico", "didático"
    ],
    "Agronegócio": [
        "agro", "rural", "fazenda", "produtor", "agricult", "pecuaria", "pecuária",
        "gado", "soja", "milho", "cafe", "café", "cana", "algodao", "algodão",
        "fertilizante", "agrotox", "defensivo", "irrigacao", "irrigação", "funrural",
        "terra", "propriedade rural", "mst", "invasao", "invasão", "demarcacao", "demarcação"
    ],
    "Meio Ambiente": [
        "ambiente", "ambiental", "clima", "floresta", "desmatamento", "ibama",
        "icmbio", "reserva", "unidade de conserv", "carbono", "emissao", "emissão",
        "poluicao", "poluição", "saneamento", "residuo", "resíduo", "lixo", "reciclagem"
    ],
    "Comunicação e Tecnologia": [
        "internet", "digital", "tecnologia", "telecom", "comunicacao", "comunicação",
        "imprensa", "midia", "mídia", "censura", "liberdade de expressao", "expressão",
        "rede social", "plataforma", "fake news", "desinformacao", "desinformação",
        "inteligencia artificial", "ia", "dados pessoais", "lgpd", "privacidade"
    ],
    "Administração Pública": [
        "servidor", "funcionalismo", "concurso", "licitacao", "licitação", "contrato",
        "administracao", "administração", "gestao", "gestão", "ministerio", "ministério",
        "autarquia", "estatal", "privatizacao", "privatização", "reforma administrativa"
    ],
    "Transporte e Infraestrutura": [
        "transporte", "rodovia", "ferrovia", "aeroporto", "porto", "infraestrutura",
        "mobilidade", "transito", "trânsito", "veiculo", "veículo", "combustivel", "combustível",
        "pedagio", "pedágio", "concessao", "concessão", "obra", "construcao", "construção"
    ],
    "Defesa e Soberania": [
        "defesa", "militar", "forcas armadas", "forças armadas", "exercito", "exército",
        "marinha", "aeronautica", "aeronáutica", "fronteira", "soberania", "nacional",
        "estrategico", "estratégico", "inteligencia", "inteligência", "espionagem"
    ],
    "Direito e Justiça": [
        "justica", "justiça", "judiciario", "judiciário", "tribunal", "stf", "stj",
        "magistrado", "juiz", "promotor", "advogado", "oab", "processo", "recurso",
        "habeas corpus", "prisao", "prisão", "inquerito", "inquérito", "investigacao", "investigação"
    ],
    "Relações Exteriores": [
        "internacional", "exterior", "diplomacia", "embaixada", "consulado",
        "mercosul", "brics", "onu", "tratado", "acordo internacional", "exportacao", "exportação",
        "importacao", "importação", "alfandega", "alfândega", "comercio exterior", "comércio exterior"
    ],
}

# ============================================================
# UTILITÁRIOS
# ============================================================

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


def format_sigla_num_ano(sigla, numero, ano) -> str:
    sigla = (sigla or "").strip()
    numero = (str(numero) or "").strip()
    ano = (str(ano) or "").strip()
    if sigla and numero and ano:
        return f"{sigla} {numero}/{ano}"
    return ""


def extract_id_from_uri(uri: str):
    if not uri:
        return None
    try:
        path = urlparse(uri).path.rstrip("/")
        return path.split("/")[-1]
    except Exception:
        return None


def is_comissao_estrategica(sigla_orgao, lista_siglas):
    if not sigla_orgao:
        return False
    return sigla_orgao.upper() in [s.upper() for s in lista_siglas]


def parse_dt(iso_str: str):
    return pd.to_datetime(iso_str, errors="coerce", utc=False)


def days_since(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return None
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    today = pd.Timestamp(datetime.date.today())
    return int((today - d.normalize()).days)


def fmt_dt_br(dt: pd.Timestamp):
    if dt is None or pd.isna(dt):
        return "—"
    d = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
    return d.strftime("%d/%m/%Y %H:%M")


def camara_link_tramitacao(id_proposicao: str) -> str:
    pid = str(id_proposicao).strip()
    return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}"


def to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> tuple[bytes, str, str]:
    """Sempre tenta exportar como XLSX, fallback para CSV apenas se necessário."""
    for engine in ["xlsxwriter", "openpyxl"]:
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine=engine) as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            return (
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            )
        except ModuleNotFoundError:
            continue
        except Exception:
            continue

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return (csv_bytes, "text/csv", "csv")


def sanitize_text_pdf(text: str) -> str:
    """Remove caracteres problemáticos para PDF."""
    if not text:
        return ""
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        '–': '-', '—': '-', '"': '"', '"': '"', ''': "'", ''': "'",
        '…': '...', '•': '*', '°': 'o', '²': '2', '³': '3',
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = result.encode('ascii', 'ignore').decode('ascii')
    return result


def to_pdf_bytes(df: pd.DataFrame, subtitulo: str = "Relatório") -> tuple[bytes, str, str]:
    """Exporta DataFrame para PDF em formato de relatório profissional."""
    
    # Colunas a excluir do relatório
    colunas_excluir = ['Tipo', 'Ano', 'Alerta', 'ID', 'id', 'LinkTramitacao', 'Link', 
                       'sinal', 'AnoStatus', 'MesStatus', 'ids_proposicoes_autoria',
                       'ids_proposicoes_relatoria', 'id_evento']
    
    try:
        from fpdf import FPDF
        
        class RelatorioPDF(FPDF):
            def header(self):
                # Logo/Título
                self.set_fill_color(0, 51, 102)  # Azul escuro
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
        
        # Linha divisória
        pdf.ln(5)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)
        
        # Resumo
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True)
        pdf.ln(5)
        
        # Filtrar colunas
        cols_mostrar = [c for c in df.columns if c not in colunas_excluir]
        
        # Identificar colunas principais para destaque
        col_proposicao = next((c for c in cols_mostrar if 'Proposi' in c or 'sigla' in c.lower()), None)
        col_ementa = next((c for c in cols_mostrar if 'Ementa' in c or 'ementa' in c), None)
        col_situacao = next((c for c in cols_mostrar if 'Situa' in c or 'situa' in c), None)
        col_orgao = next((c for c in cols_mostrar if 'Org' in c or 'org' in c.lower()), None)
        col_data = next((c for c in cols_mostrar if 'data' in c.lower() or 'Data' in c), None)
        col_relator = next((c for c in cols_mostrar if 'Relator' in c or 'relator' in c), None)
        col_tema = next((c for c in cols_mostrar if 'Tema' in c or 'tema' in c), None)
        
        # Renderizar cada registro como um card
        for idx, (_, row) in enumerate(df.head(300).iterrows()):
            # Verificar se precisa de nova página
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(30)
            
            # Card container
            y_start = pdf.get_y()
            pdf.set_fill_color(245, 247, 250)
            
            # Número do registro
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(0, 51, 102)
            pdf.cell(8, 6, str(idx + 1), fill=True, align='C')
            
            # Proposição (destaque)
            if col_proposicao and pd.notna(row.get(col_proposicao)):
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, f"  {sanitize_text_pdf(str(row[col_proposicao]))}", ln=True)
            else:
                pdf.ln(6)
            
            pdf.set_x(20)
            
            # Situação com destaque colorido
            if col_situacao and pd.notna(row.get(col_situacao)):
                situacao = sanitize_text_pdf(str(row[col_situacao]))
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
                pdf.cell(0, 5, situacao[:60], ln=True)
            
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
            
            # Data
            if col_data and pd.notna(row.get(col_data)):
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(20, 5, "Data: ", ln=False)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, sanitize_text_pdf(str(row[col_data]))[:20], ln=True)
            
            pdf.set_x(20)
            
            # Relator
            if col_relator and pd.notna(row.get(col_relator)):
                relator = str(row[col_relator])
                if relator and relator.strip() and relator.strip() != '-':
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(20, 5, "Relator: ", ln=False)
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 5, sanitize_text_pdf(relator)[:40], ln=True)
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
            
            # Ementa (texto maior)
            if col_ementa and pd.notna(row.get(col_ementa)):
                ementa = sanitize_text_pdf(str(row[col_ementa]))
                if ementa and ementa.strip():
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 5, "Ementa:", ln=True)
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(60, 60, 60)
                    # Multi-cell para texto longo
                    pdf.multi_cell(170, 4, ementa[:300] + ('...' if len(ementa) > 300 else ''))
            
            # Linha divisória entre cards
            pdf.ln(3)
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(5)
        
        # Nota de rodapé se houver mais registros
        if len(df) > 300:
            pdf.ln(5)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"* Exibindo 300 de {len(df)} registros. Exporte em XLSX para lista completa.", ln=True, align='C')
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except (ImportError, Exception) as e:
        # Fallback para CSV se der erro
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return (csv_bytes, "text/csv", "csv")


def to_pdf_autoria_relatoria(df: pd.DataFrame) -> tuple[bytes, str, str]:
    """PDF específico para Autoria e Relatoria na Pauta - formato de gabinete."""
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
        
        pdf.ln(5)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)
        
        # Ordenar por data (mais recente primeiro)
        df_sorted = df.copy()
        if 'data' in df_sorted.columns:
            df_sorted['_data_sort'] = pd.to_datetime(df_sorted['data'], errors='coerce', dayfirst=True)
            df_sorted = df_sorted.sort_values('_data_sort', ascending=False)
        
        # Separar AUTORIA e RELATORIA
        registros_autoria = []
        registros_relatoria = []
        
        for _, row in df_sorted.iterrows():
            data = str(row.get('data', '-'))
            hora = str(row.get('hora', '-')) if pd.notna(row.get('hora')) else '-'
            orgao_sigla = str(row.get('orgao_sigla', '-'))
            orgao_nome = str(row.get('orgao_nome', ''))
            local = f"{orgao_sigla}" + (f" - {orgao_nome}" if orgao_nome and orgao_nome != orgao_sigla else "")
            id_evento = str(row.get('id_evento', ''))
            link = f"https://www.camara.leg.br/evento-legislativo/{id_evento}" if id_evento and id_evento != 'nan' else ""
            
            props_autoria = str(row.get('proposicoes_autoria', ''))
            props_relatoria = str(row.get('proposicoes_relatoria', ''))
            
            if props_autoria and props_autoria.strip() and props_autoria != 'nan':
                registros_autoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'proposicoes': props_autoria, 'link': link
                })
            
            if props_relatoria and props_relatoria.strip() and props_relatoria != 'nan':
                registros_relatoria.append({
                    'data': data, 'hora': hora, 'local': local,
                    'proposicoes': props_relatoria, 'link': link
                })
        
        # === SEÇÃO AUTORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 100, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  AUTORIA DA DEPUTADA ({len(registros_autoria)} registro(s))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_autoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de autoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_autoria, 1):
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_y(30)
                
                # Card
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(0, 100, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(8, 6, str(idx), fill=True, align='C')
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 6, f"  {reg['data']} as {reg['hora']}", ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(15, 5, "Local: ", ln=False)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:60], ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "Materias:", ln=True)
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(170, 4, sanitize_text_pdf(reg['proposicoes'])[:500])
                
                if reg['link']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 4, f"Link: {reg['link']}", ln=True)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        pdf.ln(5)
        
        # === SEÇÃO RELATORIA ===
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  RELATORIA DA DEPUTADA ({len(registros_relatoria)} registro(s))", ln=True, fill=True)
        pdf.ln(3)
        
        if not registros_relatoria:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Nenhuma proposicao de relatoria na pauta neste periodo.", ln=True)
        else:
            for idx, reg in enumerate(registros_relatoria, 1):
                if pdf.get_y() > 250:
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
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(15, 5, "Local: ", ln=False)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, sanitize_text_pdf(reg['local'])[:60], ln=True)
                
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "Materias:", ln=True)
                pdf.set_x(20)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(170, 4, sanitize_text_pdf(reg['proposicoes'])[:500])
                
                if reg['link']:
                    pdf.set_x(20)
                    pdf.set_font('Helvetica', 'I', 7)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 4, f"Link: {reg['link']}", ln=True)
                
                pdf.ln(2)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return (csv_bytes, "text/csv", "csv")


def to_pdf_comissoes_estrategicas(df: pd.DataFrame) -> tuple[bytes, str, str]:
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
                self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
        pdf = RelatorioPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_y(30)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "Comissoes Estrategicas - Pautas", ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Gerado em: {get_brasilia_now().strftime('%d/%m/%Y as %H:%M')} (Brasilia)", ln=True, align='C')
        pdf.cell(0, 6, "Dep. Julia Zanatta (PL-SC)", ln=True, align='C')
        
        pdf.ln(5)
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"Total de reunioes: {len(df)}", ln=True)
        pdf.ln(3)
        
        # Ordenar por data (mais recente primeiro)
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
            descricao = str(row.get('descricao_evento', ''))
            
            # Determinar cor baseado se tem relatoria/autoria
            tem_relatoria = props_relatoria and props_relatoria.strip() and props_relatoria != 'nan'
            tem_autoria = props_autoria and props_autoria.strip() and props_autoria != 'nan'
            
            # Card header
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
            
            # Tipo e local
            pdf.set_x(20)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(100, 100, 100)
            if tipo_evento and tipo_evento != 'nan':
                pdf.cell(0, 4, sanitize_text_pdf(tipo_evento)[:80], ln=True)
            if orgao_nome and orgao_nome != orgao_sigla:
                pdf.set_x(20)
                pdf.cell(0, 4, sanitize_text_pdf(orgao_nome)[:80], ln=True)
            
            # Relatoria da deputada (destaque)
            if tem_relatoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 5, ">>> RELATORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_relatoria)[:400])
            
            # Autoria da deputada
            if tem_autoria:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 5, ">>> AUTORIA DA DEPUTADA:", ln=True)
                pdf.set_x(25)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(165, 4, sanitize_text_pdf(props_autoria)[:400])
            
            # Palavras-chave encontradas
            if palavras_chave and palavras_chave.strip() and palavras_chave != 'nan':
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_text_color(150, 100, 0)
                pdf.cell(30, 4, "Palavras-chave: ", ln=False)
                pdf.set_font('Helvetica', '', 8)
                pdf.cell(0, 4, sanitize_text_pdf(palavras_chave)[:60], ln=True)
            
            # Link
            if link:
                pdf.set_x(20)
                pdf.set_font('Helvetica', 'I', 7)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, f"Link pauta: {link}", ln=True)
            
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)
        
        output = BytesIO()
        pdf.output(output)
        return (output.getvalue(), "application/pdf", "pdf")
        
    except Exception as e:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return (csv_bytes, "text/csv", "csv")


def canonical_situacao(situacao: str) -> str:
    s_raw = (situacao or "").strip()
    s = normalize_text(s_raw)
    if "parecer" in s:
        return "Aguardando Parecer de Relator(a)"
    return s_raw


def merge_status_options(dynamic_opts: list[str]) -> list[str]:
    base = [s for s in STATUS_PREDEFINIDOS if s and str(s).strip()]
    dyn = [s for s in dynamic_opts if s and str(s).strip()]
    merged = []
    seen = set()
    for s in base + sorted(dyn):
        if s not in seen:
            merged.append(s)
            seen.add(s)
    return merged


def party_norm(sigla: str) -> str:
    s = (sigla or "").strip().upper()
    if s in {"PC DO B", "PCDOB", "PCDOB ", "PCD0B"}:
        return "PCDOB"
    return s


# Partidos da base/oposição para identificar relator adversário
PARTIDOS_OPOSICAO = {"PT", "PSOL", "PCDOB", "PC DO B", "REDE", "PV", "PSB", "PDT", "PSDB"}


def gerar_acao_sugerida(row: pd.Series) -> str:
    """Gera ação sugerida baseada na situação e contexto da proposição."""
    situacao = str(row.get("Situação atual", "") or "").lower()
    dias_parado = row.get("Parado há (dias)", 0)
    relator = str(row.get("Relator(a)", "") or "")
    
    acoes = []
    
    # Verificar relator adversário
    if relator and relator.strip() and relator != "-":
        for partido in PARTIDOS_OPOSICAO:
            if partido in relator.upper():
                acoes.append("⚠️ Relator adversario: atencao")
                break
    
    # Ações por situação
    if "aguardando designa" in situacao or "sem relator" in situacao:
        acoes.append("Cobrar designacao de relator")
    elif "pronta para pauta" in situacao:
        acoes.append("Articular inclusao em pauta")
    elif "aguardando delibera" in situacao:
        acoes.append("Preparar fala/destaque para votacao")
    elif "aguardando parecer" in situacao:
        acoes.append("Acompanhar elaboracao do parecer")
    elif "tramitando em conjunto" in situacao:
        acoes.append("Monitorar proposicao principal")
    
    # Ação por tempo parado
    try:
        dias = int(dias_parado) if pd.notna(dias_parado) else 0
    except:
        dias = 0
    
    if dias >= 30:
        acoes.append("DESTRAVAR: contato com comissao/lideranca")
    elif dias >= 15:
        acoes.append("Verificar andamento com secretaria")
    
    return " | ".join(acoes) if acoes else "Acompanhar tramitacao"


def calcular_prioridade(row: pd.Series) -> int:
    """Calcula score de prioridade (quanto maior, mais urgente)."""
    score = 0
    
    # Por sinal/dias parado
    dias = row.get("Parado há (dias)", 0)
    try:
        dias = int(dias) if pd.notna(dias) else 0
    except:
        dias = 0
    
    if dias >= 30:
        score += 100  # Crítico
    elif dias >= 15:
        score += 70   # Atenção
    elif dias >= 7:
        score += 40   # Monitoramento
    
    # Por situação crítica
    situacao = str(row.get("Situação atual", "") or "").lower()
    if "pronta para pauta" in situacao:
        score += 50
    elif "aguardando delibera" in situacao:
        score += 45
    elif "aguardando designa" in situacao:
        score += 30
    
    # Relator adversário
    relator = str(row.get("Relator(a)", "") or "")
    for partido in PARTIDOS_OPOSICAO:
        if partido in relator.upper():
            score += 20
            break
    
    return score


def render_resumo_executivo(df: pd.DataFrame):
    """Renderiza bloco de resumo executivo no topo."""
    if df.empty:
        return
    
    st.markdown("### 📊 Resumo Executivo")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(df)
    
    # Contagem por sinal (baseado em dias parado)
    def get_sinal_count(df, min_dias, max_dias=None):
        try:
            if "Parado há (dias)" in df.columns:
                if max_dias:
                    return len(df[(df["Parado há (dias)"] >= min_dias) & (df["Parado há (dias)"] < max_dias)])
                return len(df[df["Parado há (dias)"] >= min_dias])
        except:
            pass
        return 0
    
    criticos = get_sinal_count(df, 30)
    atencao = get_sinal_count(df, 15, 30)
    monitoramento = get_sinal_count(df, 7, 15)
    
    with col1:
        st.metric("📋 Total de Matérias", total)
    with col2:
        st.metric("🔴 Críticas (≥30 dias)", criticos)
    with col3:
        st.metric("🟠 Atenção (15-29 dias)", atencao)
    with col4:
        st.metric("🟡 Monitorar (7-14 dias)", monitoramento)
    
    # Contagem por situações-chave
    st.markdown("#### 📌 Por Situação-Chave")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    def count_situacao(df, termo):
        if "Situação atual" not in df.columns:
            return 0
        return len(df[df["Situação atual"].fillna("").str.lower().str.contains(termo.lower())])
    
    with col_s1:
        st.metric("🔍 Aguard. Relator", count_situacao(df, "aguardando designa"))
    with col_s2:
        st.metric("📝 Aguard. Parecer", count_situacao(df, "aguardando parecer"))
    with col_s3:
        st.metric("📅 Pronta p/ Pauta", count_situacao(df, "pronta para pauta"))
    with col_s4:
        st.metric("🗳️ Aguard. Deliberação", count_situacao(df, "aguardando delibera"))
    
    # Top 3 órgãos e situações
    st.markdown("#### 🏛️ Top 3 Órgãos e Situações")
    col_o, col_sit = st.columns(2)
    
    with col_o:
        if "Órgão (sigla)" in df.columns:
            top_orgaos = df["Órgão (sigla)"].value_counts().head(3)
            for orgao, qtd in top_orgaos.items():
                st.write(f"**{orgao}**: {qtd}")
    
    with col_sit:
        if "Situação atual" in df.columns:
            top_sit = df["Situação atual"].value_counts().head(3)
            for sit, qtd in top_sit.items():
                sit_short = sit[:40] + "..." if len(str(sit)) > 40 else sit
                st.write(f"**{sit_short}**: {qtd}")
    
    st.markdown("---")


def render_atencao_deputada(df: pd.DataFrame):
    """Renderiza bloco 'Atenção da Deputada' com Top 5 prioridades."""
    if df.empty:
        return
    
    st.markdown("### ⚠️ Atenção da Deputada (Top 5)")
    st.caption("Matérias que exigem decisão ou ação imediata")
    
    # Adicionar coluna de prioridade e ação
    df_pri = df.copy()
    df_pri["_prioridade"] = df_pri.apply(calcular_prioridade, axis=1)
    df_pri["Ação Sugerida"] = df_pri.apply(gerar_acao_sugerida, axis=1)
    
    # Ordenar por prioridade e pegar top 5
    df_top5 = df_pri.nlargest(5, "_prioridade")
    
    # Mostrar cards
    for idx, (_, row) in enumerate(df_top5.iterrows(), 1):
        prop = row.get("Proposição", row.get("siglaTipo", "")) 
        if "numero" in df.columns:
            prop = f"{row.get('siglaTipo', '')} {row.get('numero', '')}/{row.get('ano', '')}"
        
        orgao = row.get("Órgão (sigla)", "-")
        situacao = str(row.get("Situação atual", "-"))[:50]
        acao = row.get("Ação Sugerida", "-")
        dias = row.get("Parado há (dias)", "-")
        
        # Cor do sinal
        try:
            d = int(dias)
            if d >= 30:
                sinal = "🔴"
            elif d >= 15:
                sinal = "🟠"
            elif d >= 7:
                sinal = "🟡"
            else:
                sinal = "🟢"
        except:
            sinal = "⚪"
        
        st.markdown(f"""
        **{idx}. {sinal} {prop}** | {orgao} | {dias} dias  
        *Situação:* {situacao}  
        *→ Ação:* **{acao}**
        """)
    
    st.markdown("---")


def render_prioridades_gabinete(df: pd.DataFrame):
    """Renderiza tabela 'Top Prioridades do Gabinete' com Top 20."""
    if df.empty:
        return
    
    st.markdown("### 📋 Top Prioridades do Gabinete (Top 20)")
    st.caption("Para distribuição de tarefas e acompanhamento")
    
    # Adicionar colunas calculadas
    df_pri = df.copy()
    df_pri["_prioridade"] = df_pri.apply(calcular_prioridade, axis=1)
    df_pri["Ação Sugerida"] = df_pri.apply(gerar_acao_sugerida, axis=1)
    
    # Ordenar e pegar top 20
    df_top20 = df_pri.nlargest(20, "_prioridade")
    
    # Selecionar colunas para exibição
    colunas_exibir = []
    for col in ["Proposição", "Situação atual", "Órgão (sigla)", "Parado há (dias)", "Relator(a)", "Ação Sugerida"]:
        if col in df_top20.columns:
            colunas_exibir.append(col)
    
    if "Ação Sugerida" not in colunas_exibir:
        colunas_exibir.append("Ação Sugerida")
    
    if colunas_exibir:
        st.dataframe(
            df_top20[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ação Sugerida": st.column_config.TextColumn("Ação Sugerida", width="large"),
            }
        )
    
    st.markdown("---")


def categorizar_tema(ementa: str) -> str:
    """Categoriza uma proposição por tema baseado na ementa - REFINADO com scoring."""
    if not ementa:
        return "Não Classificado"
    ementa_norm = normalize_text(ementa)
    
    # Conta matches por tema para pegar o mais relevante
    scores = {}
    for tema, palavras in TEMAS_CATEGORIAS.items():
        score = 0
        for palavra in palavras:
            if palavra in ementa_norm:
                score += 1
        if score > 0:
            scores[tema] = score
    
    if scores:
        # Retorna o tema com mais matches
        return max(scores, key=scores.get)
    
    return "Não Classificado"


# ============================================================
# HTTP ROBUSTO
# ============================================================

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)

def _request_json(url: str, params=None, timeout=30, max_retries=3):
    params = params or {}
    backoffs = [0.5, 1.0, 2.0, 4.0]
    last_err = None

    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            if resp.status_code == 404:
                return None
            if resp.status_code in (429,) or (500 <= resp.status_code <= 599):
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
        except requests.exceptions.HTTPError as e:
            last_err = e
            break
        except Exception as e:
            last_err = e
            break

    return {"__error__": str(last_err) if last_err else "unknown_error"}


def safe_get(url, params=None):
    return _request_json(url, params=params, timeout=30, max_retries=3)


# ============================================================
# FUNÇÃO CENTRAL - BUSCA TUDO DE UMA VEZ
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)
def fetch_proposicao_completa(id_proposicao: str) -> dict:
    """
    FUNÇÃO CENTRAL: Busca TODAS as informações da proposição de uma vez.
    """
    pid = str(id_proposicao).strip()
    if not pid:
        return {}
    
    resultado = {
        "id": pid,
        "sigla": "",
        "numero": "",
        "ano": "",
        "ementa": "",
        "urlInteiroTeor": "",
        "status_dataHora": "",
        "status_siglaOrgao": "",
        "status_descricaoTramitacao": "",
        "status_descricaoSituacao": "",
        "status_despacho": "",
        "tramitacoes": [],
        "relator": {},
    }
    
    # 1. DADOS BÁSICOS + STATUS
    try:
        data = safe_get(f"{BASE_URL}/proposicoes/{pid}")
        if data and isinstance(data, dict) and data.get("dados"):
            d = data.get("dados", {}) or {}
            resultado.update({
                "sigla": (d.get("siglaTipo") or "").strip(),
                "numero": str(d.get("numero") or "").strip(),
                "ano": str(d.get("ano") or "").strip(),
                "ementa": (d.get("ementa") or "").strip(),
                "urlInteiroTeor": d.get("urlInteiroTeor") or "",
            })
            
            status = d.get("statusProposicao", {}) or {}
            resultado.update({
                "status_dataHora": status.get("dataHora") or "",
                "status_siglaOrgao": status.get("siglaOrgao") or "",
                "status_descricaoTramitacao": status.get("descricaoTramitacao") or "",
                "status_descricaoSituacao": canonical_situacao(status.get("descricaoSituacao") or ""),
                "status_despacho": status.get("despacho") or "",
            })
    except Exception:
        pass
    
    # 2. TRAMITAÇÕES
    try:
        tramitacoes = []
        tram_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/tramitacoes")
        
        if tram_data and isinstance(tram_data, dict) and tram_data.get("dados"):
            tramitacoes = tram_data.get("dados", [])
        
        if not tramitacoes:
            pagina = 1
            while pagina <= 10:
                params = {"itens": 100, "ordem": "DESC", "ordenarPor": "dataHora", "pagina": pagina}
                tram_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/tramitacoes", params=params)
                
                if not tram_data or "__error__" in tram_data:
                    break
                
                dados = tram_data.get("dados", [])
                if not dados:
                    break
                
                tramitacoes.extend(dados)
                
                has_next = any(link.get("rel") == "next" for link in tram_data.get("links", []))
                if not has_next:
                    break
                
                pagina += 1
        
        resultado["tramitacoes"] = tramitacoes
        
    except Exception:
        pass
    
    # 3. EXTRAI RELATOR DAS TRAMITAÇÕES
    try:
        relator_info = {}
        patterns = [
            r'Designad[oa]\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
            r'Relator[a]?:?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
            r'Parecer\s+(?:do|da)\s+Relator[a]?,?\s*Dep\.\s*([^(]+?)\s*\(([A-ZÀ-Ú][A-Za-zÀ-úà-ù]+)(?:-([A-Z]{2}))?\)',
        ]
        
        orgao_atual = resultado.get("status_siglaOrgao", "")
        relator_orgao_atual = None
        relator_qualquer = None
        
        tramitacoes_ordenadas = sorted(
            resultado["tramitacoes"],
            key=lambda x: x.get("dataHora") or x.get("data") or "",
            reverse=True
        )
        
        for t in tramitacoes_ordenadas:
            despacho = t.get("despacho") or ""
            desc = t.get("descricaoTramitacao") or ""
            orgao_tram = t.get("siglaOrgao") or ""
            texto = f"{despacho} {desc}"
            
            for pattern in patterns:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    nome = match.group(1).strip()
                    partido = party_norm(match.group(2).strip())
                    uf = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ""
                    
                    if nome and len(nome) > 3:
                        candidato = {"nome": nome, "partido": partido, "uf": uf}
                        
                        if orgao_tram and orgao_atual and orgao_tram.upper() == orgao_atual.upper():
                            if not relator_orgao_atual:
                                relator_orgao_atual = candidato
                                break
                        
                        if not relator_qualquer:
                            relator_qualquer = candidato
                        
                        break
            
            if relator_orgao_atual:
                break
        
        relator_info = relator_orgao_atual or relator_qualquer
        
        if not relator_info:
            rel_data = safe_get(f"{BASE_URL}/proposicoes/{pid}/relatores")
            if isinstance(rel_data, dict) and rel_data.get("dados"):
                candidatos = rel_data.get("dados", [])
                if candidatos:
                    r = candidatos[0]
                    nome = r.get("nome") or r.get("nomeRelator") or ""
                    partido = party_norm(r.get("siglaPartido") or r.get("partido") or "")
                    uf = r.get("siglaUf") or r.get("uf") or ""
                    id_dep = r.get("id") or r.get("idDeputado") or ""
                    
                    dep = r.get("deputado") or r.get("parlamentar") or {}
                    if isinstance(dep, dict):
                        nome = nome or dep.get("nome") or dep.get("nomeCivil") or ""
                        partido = partido or party_norm(dep.get("siglaPartido") or dep.get("partido") or "")
                        uf = uf or dep.get("siglaUf") or dep.get("uf") or ""
                        id_dep = id_dep or dep.get("id") or ""
                    
                    if nome:
                        relator_info = {"nome": nome, "partido": partido, "uf": uf, "id_deputado": str(id_dep)}
        
        if relator_info and not relator_info.get("id_deputado"):
            nome_relator = relator_info.get("nome", "")
            if nome_relator:
                dep_data = safe_get(f"{BASE_URL}/deputados", params={"nome": nome_relator, "itens": 5})
                if isinstance(dep_data, dict) and dep_data.get("dados"):
                    deps = dep_data.get("dados", [])
                    if deps:
                        relator_info["id_deputado"] = str(deps[0].get("id", ""))
        
        resultado["relator"] = relator_info
        
    except Exception:
        pass
    
    return resultado


@st.cache_data(show_spinner=False, ttl=1800)
def get_tramitacoes_ultimas10(id_prop):
    """Retorna as 10 últimas tramitações."""
    try:
        dados_completos = fetch_proposicao_completa(id_prop)
        tramitacoes = dados_completos.get("tramitacoes", [])
        
        if not tramitacoes:
            return pd.DataFrame()
        
        rows = []
        for t in tramitacoes:
            dh = t.get("dataHora") or ""
            if dh:
                rows.append({
                    "dataHora": dh,
                    "siglaOrgao": t.get("siglaOrgao") or "—",
                    "descricaoTramitacao": t.get("descricaoTramitacao") or "—",
                })
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df['dataHora_dt'] = pd.to_datetime(df['dataHora'], errors='coerce')
        df = df[df['dataHora_dt'].notna()].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        df['Data'] = df['dataHora_dt'].dt.strftime('%d/%m/%Y')
        df['Hora'] = df['dataHora_dt'].dt.strftime('%H:%M')
        df = df.sort_values('dataHora_dt', ascending=False)
        
        view = pd.DataFrame({
            "Data": df["Data"].values,
            "Hora": df["Hora"].values,
            "Órgão": df["siglaOrgao"].values,
            "Tramitação": df["descricaoTramitacao"].values,
        })
        
        resultado = view.head(10).reset_index(drop=True)
        
        return resultado
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_relator_atual(id_proposicao: str) -> dict:
    """Retorna relator usando a função centralizada."""
    try:
        dados_completos = fetch_proposicao_completa(id_proposicao)
        relator = dados_completos.get("relator", {})
        return relator
    except Exception:
        return {}


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_status_proposicao(id_proposicao):
    """Busca status usando a função centralizada."""
    dados_completos = fetch_proposicao_completa(id_proposicao)
    return {
        "id": dados_completos.get("id"),
        "sigla": dados_completos.get("sigla"),
        "numero": dados_completos.get("numero"),
        "ano": dados_completos.get("ano"),
        "ementa": dados_completos.get("ementa"),
        "urlInteiroTeor": dados_completos.get("urlInteiroTeor"),
        "status_dataHora": dados_completos.get("status_dataHora"),
        "status_siglaOrgao": dados_completos.get("status_siglaOrgao"),
        "status_descricaoTramitacao": dados_completos.get("status_descricaoTramitacao"),
        "status_descricaoSituacao": dados_completos.get("status_descricaoSituacao"),
        "status_despacho": dados_completos.get("status_despacho"),
    }


def relator_adversario_alert(relator_info: dict) -> str:
    if not relator_info:
        return ""
    p = party_norm(relator_info.get("partido") or "")
    if p and p in PARTIDOS_RELATOR_ADVERSARIO:
        return "⚠️ Relator adversário"
    return ""


def calc_ultima_mov(df_tram_ult10: pd.DataFrame, status_dataHora: str):
    last = None
    if df_tram_ult10 is not None and not df_tram_ult10.empty:
        try:
            first = df_tram_ult10.iloc[0]
            if str(first.get("Data", "")).strip() and str(first.get("Hora", "")).strip():
                dt_guess = pd.to_datetime(f"{first['Data']} {first['Hora']}", errors="coerce", dayfirst=True)
                if pd.notna(dt_guess):
                    last = dt_guess
        except Exception:
            last = None

    if (last is None or pd.isna(last)) and status_dataHora:
        last = parse_dt(status_dataHora)

    parado = days_since(last) if last is not None and not pd.isna(last) else None
    return last, parado


# ============================================================
# API: EVENTOS/PAUTA (MONITORAMENTO)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_eventos(start_date, end_date):
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
        if data is None or "__error__" in data:
            break

        dados = data.get("dados", [])
        if not dados:
            break
        eventos.extend(dados)

        links = data.get("links", [])
        if not any(link.get("rel") == "next" for link in links):
            break
        pagina += 1
    return eventos


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pauta_evento(event_id):
    data = safe_get(f"{BASE_URL}/eventos/{event_id}/pauta")
    if data is None or "__error__" in data:
        return []
    return data.get("dados", [])


def get_proposicao_id_from_item(item):
    grupos = [
        ["proposicaoRelacionada", "proposicaoRelacionada_", "proposicao_relacionada"],
        ["proposicaoPrincipal", "proposicao_principal"],
        ["proposicao", "proposicao_"],
    ]

    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                if prop.get("id"):
                    return str(prop["id"])
                if prop.get("idProposicao"):
                    return str(prop["idProposicao"])

    for grupo in grupos:
        for chave in grupo:
            prop = item.get(chave)
            if isinstance(prop, dict):
                uri = prop.get("uri") or prop.get("uriProposicao") or prop.get("uriProposicaoPrincipal")
                if uri:
                    return extract_id_from_uri(uri)

    for chave_uri in ["uriProposicaoPrincipal", "uriProposicao", "uri"]:
        if item.get(chave_uri):
            return extract_id_from_uri(item[chave_uri])

    return None


@lru_cache(maxsize=4096)
def fetch_proposicao_info(id_proposicao):
    data = safe_get(f"{BASE_URL}/proposicoes/{id_proposicao}")
    if data is None or "__error__" in data:
        return {"id": str(id_proposicao), "sigla": "", "numero": "", "ano": "", "ementa": ""}

    d = data.get("dados", {}) or {}
    return {
        "id": str(d.get("id") or id_proposicao),
        "sigla": (d.get("siglaTipo") or "").strip(),
        "numero": str(d.get("numero") or "").strip(),
        "ano": str(d.get("ano") or "").strip(),
        "ementa": (d.get("ementa") or "").strip(),
    }


def pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf):
    relator = item.get("relator") or {}
    nome = relator.get("nome") or ""
    partido = relator.get("siglaPartido") or ""
    uf = relator.get("siglaUf") or ""

    if normalize_text(alvo_nome) not in normalize_text(nome):
        return False
    if alvo_partido and partido and normalize_text(alvo_partido) != normalize_text(partido):
        return False
    if alvo_uf and uf and normalize_text(alvo_uf) != normalize_text(uf):
        return False
    return True


def pauta_item_palavras_chave(item, palavras_chave_normalizadas):
    textos = []
    for chave in ("ementa", "ementaDetalhada", "titulo", "descricao", "descricaoTipo"):
        v = item.get(chave)
        if v:
            textos.append(str(v))

    prop = item.get("proposicao") or {}
    for chave in ("ementa", "ementaDetalhada", "titulo"):
        v = prop.get(chave)
        if v:
            textos.append(str(v))

    texto_norm = normalize_text(" ".join(textos))
    encontradas = set()
    for kw_norm, kw_original in palavras_chave_normalizadas:
        if kw_norm and kw_norm in texto_norm:
            encontradas.add(kw_original)
    return encontradas


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ids_autoria_deputada(id_deputada):
    ids = set()
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "ASC", "ordenarPor": "id"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            if d.get("id"):
                ids.add(str(d["id"]))

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        if not next_link:
            break

        url = next_link
        params = {}

    return ids


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
    registros = []
    palavras_chave_norm = [(normalize_text(p), p) for p in palavras_chave if p.strip()]
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

        pauta = fetch_pauta_evento(event_id)

        proposicoes_relatoria = set()
        proposicoes_autoria = set()
        palavras_evento = set()
        ids_proposicoes_autoria = set()
        ids_proposicoes_relatoria = set()

        for item in pauta:
            kws_item = pauta_item_palavras_chave(item, palavras_chave_norm)
            has_keywords = bool(kws_item)
            relatoria_flag = pauta_item_tem_relatoria_deputada(item, alvo_nome, alvo_partido, alvo_uf)

            autoria_flag = False
            id_prop_tmp = None
            if buscar_autoria and ids_autoria_deputada:
                id_prop_tmp = get_proposicao_id_from_item(item)
                if id_prop_tmp and id_prop_tmp in ids_autoria_deputada:
                    autoria_flag = True

            if not (relatoria_flag or autoria_flag or has_keywords):
                continue

            id_prop = id_prop_tmp or get_proposicao_id_from_item(item)
            identificacao = "(proposição não identificada)"
            ementa_prop = ""

            if id_prop:
                info = fetch_proposicao_info(id_prop)
                identificacao = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or identificacao
                ementa_prop = info["ementa"]

            texto_completo = f"{identificacao} – {ementa_prop}" if ementa_prop else identificacao

            if relatoria_flag:
                proposicoes_relatoria.add(texto_completo)
                if id_prop:
                    ids_proposicoes_relatoria.add(str(id_prop))
            if autoria_flag:
                proposicoes_autoria.add(texto_completo)
                if id_prop:
                    ids_proposicoes_autoria.add(str(id_prop))
            if has_keywords:
                for kw in kws_item:
                    palavras_evento.add(kw)

        if not (proposicoes_relatoria or proposicoes_autoria or palavras_evento):
            continue

        for org in orgaos:
            sigla_org = org.get("siglaOrgao") or org.get("sigla") or ""
            nome_org = org.get("nomeOrgao") or org.get("nome") or ""
            orgao_id = org.get("id")

            registros.append(
                {
                    "data": data_str,
                    "hora": hora_str,
                    "orgao_id": orgao_id,
                    "orgao_sigla": sigla_org,
                    "orgao_nome": nome_org,
                    "id_evento": event_id,
                    "tipo_evento": tipo_evento,
                    "descricao_evento": descricao_evento,
                    "tem_relatoria_deputada": bool(proposicoes_relatoria),
                    "proposicoes_relatoria": "; ".join(sorted(proposicoes_relatoria)),
                    "ids_proposicoes_relatoria": ";".join(sorted(ids_proposicoes_relatoria)),
                    "tem_autoria_deputada": bool(proposicoes_autoria),
                    "proposicoes_autoria": "; ".join(sorted(proposicoes_autoria)),
                    "ids_proposicoes_autoria": ";".join(sorted(ids_proposicoes_autoria)),
                    "tem_palavras_chave": bool(palavras_evento),
                    "palavras_chave_encontradas": "; ".join(sorted(palavras_evento)),
                    "comissao_estrategica": is_comissao_estrategica(sigla_org, comissoes_estrategicas),
                }
            )

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values(["data", "hora", "orgao_sigla", "id_evento"])
    return df


# ============================================================
# API: RASTREADOR (INDEPENDENTE) + RIC Fallback
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_lista_proposicoes_autoria_geral(id_deputada):
    rows = []
    url = f"{BASE_URL}/proposicoes"
    params = {"idDeputadoAutor": id_deputada, "itens": 100, "ordem": "DESC", "ordenarPor": "ano"}

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            rows.append(
                {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                }
            )

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break

        if not next_link:
            break
        url = next_link
        params = {}

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Proposicao"] = df.apply(lambda r: format_sigla_num_ano(r["siglaTipo"], r["numero"], r["ano"]), axis=1)
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_rics_por_autor(id_deputada):
    rows = []
    url = f"{BASE_URL}/proposicoes"
    params = {
        "siglaTipo": "RIC",
        "idDeputadoAutor": id_deputada,
        "itens": 100,
        "ordem": "DESC",
        "ordenarPor": "ano",
    }

    while True:
        data = safe_get(url, params=params)
        if data is None or "__error__" in data:
            break

        for d in data.get("dados", []):
            rows.append(
                {
                    "id": str(d.get("id") or ""),
                    "siglaTipo": (d.get("siglaTipo") or "").strip(),
                    "numero": str(d.get("numero") or "").strip(),
                    "ano": str(d.get("ano") or "").strip(),
                    "ementa": (d.get("ementa") or "").strip(),
                    "Proposicao": format_sigla_num_ano(d.get("siglaTipo"), d.get("numero"), d.get("ano")),
                }
            )

        next_link = None
        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_link = link.get("href")
                break
        if not next_link:
            break

        url = next_link
        params = {}

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_lista_proposicoes_autoria(id_deputada):
    df1 = fetch_lista_proposicoes_autoria_geral(id_deputada)
    df2 = fetch_rics_por_autor(id_deputada)

    if df1.empty and df2.empty:
        return pd.DataFrame(columns=["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"])

    df = pd.concat([df1, df2], ignore_index=True)

    if "Proposicao" not in df.columns:
        df["Proposicao"] = ""
    mask = df["Proposicao"].isna() | (df["Proposicao"].astype(str).str.strip() == "")
    if mask.any():
        df.loc[mask, "Proposicao"] = df.loc[mask].apply(
            lambda r: format_sigla_num_ano(r.get("siglaTipo"), r.get("numero"), r.get("ano")),
            axis=1
        )

    df = df.drop_duplicates(subset=["id"], keep="first")

    cols = ["id", "Proposicao", "siglaTipo", "numero", "ano", "ementa"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    return df


# ============================================================
# STATUS MAP
# ============================================================

@st.cache_data(show_spinner=False, ttl=900)
def build_status_map(ids: list[str]) -> dict:
    out: dict = {}
    ids = [str(x) for x in (ids or []) if str(x).strip()]
    if not ids:
        return out

    def _one(pid: str):
        dados_completos = fetch_proposicao_completa(pid)
        
        situacao = canonical_situacao(dados_completos.get("status_descricaoSituacao", ""))
        andamento = dados_completos.get("status_descricaoTramitacao", "")
        relator_info = dados_completos.get("relator", {})
        
        relator_txt = ""
        if relator_info and relator_info.get("nome"):
            nome = relator_info.get("nome", "")
            partido = relator_info.get("partido", "")
            uf = relator_info.get("uf", "")
            if partido or uf:
                relator_txt = f"{nome} ({partido}/{uf})".replace("//", "/").replace("(/", "(").replace("/)", ")")
            else:
                relator_txt = nome
        
        return pid, {
            "situacao": situacao,
            "andamento": andamento,
            "status_dataHora": dados_completos.get("status_dataHora", ""),
            "siglaOrgao": dados_completos.get("status_siglaOrgao", ""),
            "relator": relator_txt,
        }

    max_workers = 10 if len(ids) >= 40 else 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for pid, payload in ex.map(_one, ids):
            out[str(pid)] = payload

    return out


def enrich_with_status(df_base: pd.DataFrame, status_map: dict) -> pd.DataFrame:
    df = df_base.copy()
    df["Situação atual"] = df["id"].astype(str).map(lambda x: canonical_situacao(status_map.get(str(x), {}).get("situacao", "")))
    df["Andamento (status)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("andamento", ""))
    df["Data do status (raw)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("status_dataHora", ""))
    df["Órgão (sigla)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("siglaOrgao", ""))
    df["Relator(a)"] = df["id"].astype(str).map(lambda x: status_map.get(str(x), {}).get("relator", "—"))

    dt = pd.to_datetime(df["Data do status (raw)"], errors="coerce")
    df["DataStatus_dt"] = dt
    df["Data do status"] = dt.apply(fmt_dt_br)
    df["AnoStatus"] = dt.dt.year
    df["MesStatus"] = dt.dt.month
    df["Parado (dias)"] = df["DataStatus_dt"].apply(days_since)
    
    # Adiciona tema
    df["Tema"] = df["ementa"].apply(categorizar_tema)

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
    df = df.sort_values("DataStatus_dt", ascending=True)
    
    return df


# ============================================================
# ESTRATÉGIAS
# ============================================================

def estrategia_por_situacao(situacao: str) -> list[str]:
    s = normalize_text(canonical_situacao(situacao or ""))

    if "aguardando designacao de relator" in s or "aguardando designação de relator" in s:
        return ["Pressionar Presidência da Comissão para evitar relator governista; buscar nome técnico ou neutro."]

    if "aguardando parecer" in s:
        return ["Cobrar celeridade e confrontar viés ideológico; preparar voto em separado ou emenda supressiva."]

    if "tramitando em conjunto" in s:
        return ["Identificar projeto principal e expor 'jabutis'; atuar para desmembrar ou travar avanço."]

    if "pronta para pauta" in s:
        return ["Atuar pela retirada de pauta; se não houver recuo, preparar obstrução e discurso crítico."]

    if "aguardando deliberacao" in s or "aguardando deliberação" in s:
        return ["Mapear ambiente político da comissão; usar requerimentos para ganhar tempo ou inviabilizar votação."]

    if "aguardando apreciacao" in s or "aguardando apreciação" in s:
        return ["Pressionar Presidência para não pautar; evitar avanço silencioso do governo."]

    if "aguardando distribuicao" in s or "aguardando distribuição" in s:
        return ["Atuar para impedir envio a comissão dominada pela esquerda; antecipar contenção política."]

    if "aguardando designacao" in s or "aguardando designação" in s:
        return ["Cobrar despacho e denunciar engavetamento seletivo; manter controle do rito."]

    if "aguardando votacao" in s or "aguardando votação" in s:
        return ["Fazer contagem voto a voto; acionar obstrução, destaques e narrativa contra aumento de poder do Estado."]

    if "arquivada" in s:
        return ["Mapear possibilidade de desarquivamento ou reapresentação; avaliar custo político e timing."]

    if "aguardando despacho" in s and "presidente" in s and "camara" in s:
        return ["Atuar junto à Mesa para evitar despacho desfavorável; antecipar reação conforme comissão designada."]

    return ["—"]


def exibir_detalhes_proposicao(selected_id: str, key_prefix: str = ""):
    """
    Função reutilizável para exibir detalhes completos de uma proposição.
    """
    with st.spinner("Carregando informações completas..."):
        dados_completos = fetch_proposicao_completa(selected_id)
        
        status = {
            "status_dataHora": dados_completos.get("status_dataHora"),
            "status_siglaOrgao": dados_completos.get("status_siglaOrgao"),
            "status_descricaoTramitacao": dados_completos.get("status_descricaoTramitacao"),
            "status_descricaoSituacao": dados_completos.get("status_descricaoSituacao"),
            "status_despacho": dados_completos.get("status_despacho"),
            "ementa": dados_completos.get("ementa"),
            "urlInteiroTeor": dados_completos.get("urlInteiroTeor"),
            "sigla": dados_completos.get("sigla"),
            "numero": dados_completos.get("numero"),
            "ano": dados_completos.get("ano"),
        }
        
        relator = dados_completos.get("relator", {})
        situacao = status.get("status_descricaoSituacao") or "—"
        
        situacao_norm = normalize_text(situacao)
        precisa_relator = (
            "pronta para pauta" in situacao_norm or 
            "pronto para pauta" in situacao_norm or
            "aguardando parecer" in situacao_norm
        )
        
        alerta_relator = relator_adversario_alert(relator) if relator else ""
        df_tram10 = get_tramitacoes_ultimas10(selected_id)
        
        status_dt = parse_dt(status.get("status_dataHora") or "")
        ultima_dt, parado_dias = calc_ultima_mov(df_tram10, status.get("status_dataHora") or "")

    proposicao_fmt = format_sigla_num_ano(status.get("sigla"), status.get("numero"), status.get("ano")) or ""
    org_sigla = status.get("status_siglaOrgao") or "—"
    andamento = status.get("status_descricaoTramitacao") or "—"
    despacho = status.get("status_despacho") or ""
    ementa = status.get("ementa") or ""

    st.markdown("#### 🧾 Contexto")
    
    if parado_dias is not None:
        if parado_dias <= 2:
            st.error("🚨 **URGENTÍSSIMO** - Tramitação há 2 dias ou menos!")
        elif parado_dias <= 5:
            st.warning("⚠️ **URGENTE** - Tramitação há 5 dias ou menos!")
        elif parado_dias <= 15:
            st.info("🔔 **TRAMITAÇÃO RECENTE** - Movimentação nos últimos 15 dias")
    
    st.markdown(f"**Proposição:** {proposicao_fmt or '—'}")
    st.markdown(f"**Órgão:** {org_sigla}")
    st.markdown(f"**Situação atual:** {situacao}")
    
    if relator and (relator.get("nome") or relator.get("partido") or relator.get("uf")):
        rel_nome = relator.get('nome','—')
        rel_partido = relator.get('partido','')
        rel_uf = relator.get('uf','')
        rel_id = relator.get('id_deputado','')
        
        rel_txt = f"{rel_nome}"
        if rel_partido or rel_uf:
            rel_txt += f" ({rel_partido}/{rel_uf})".replace("//", "/")
        
        col_foto, col_info = st.columns([1, 3])
        
        with col_foto:
            if rel_id:
                foto_url = f"https://www.camara.leg.br/internet/deputado/bandep/{rel_id}.jpg"
                try:
                    st.image(foto_url, width=120, caption=rel_nome)
                except:
                    st.markdown(f"**Relator(a):** {rel_txt}")
            else:
                st.markdown("📷")
        
        with col_info:
            st.markdown(f"**Relator(a):**")
            st.markdown(f"**{rel_txt}**")
            
            if alerta_relator:
                st.warning(alerta_relator)
                
    elif precisa_relator:
        st.markdown("**Relator(a):** Não identificado")
    
    c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
    c1.metric("Data do Status", fmt_dt_br(status_dt))
    c2.metric("Última mov.", fmt_dt_br(ultima_dt))
    c3.metric("Parado há", f"{parado_dias} dias" if isinstance(parado_dias, int) else "—")

    st.markdown("**Ementa**")
    st.write(ementa)

    st.markdown("**Último andamento**")
    st.write(andamento)

    if despacho:
        st.markdown("**Despacho (chave para onde foi)**")
        st.write(despacho)

    if status.get("urlInteiroTeor"):
        st.markdown("**Inteiro teor**")
        st.write(status["urlInteiroTeor"])

    st.markdown(f"[Tramitação]({camara_link_tramitacao(selected_id)})")

    st.markdown("---")
    st.markdown("### 🧠 Estratégia")
    
    df_estr = montar_estrategia_tabela(situacao, relator_alerta=alerta_relator)
    st.dataframe(df_estr, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🕒 Linha do Tempo (últimas 10 movimentações)")

    if df_tram10.empty:
        st.info("Sem tramitações retornadas.")
    else:
        st.dataframe(df_tram10, use_container_width=True, hide_index=True)

        col_xlsx, col_pdf = st.columns(2)
        with col_xlsx:
            bytes_out, mime, ext = to_xlsx_bytes(df_tram10, "LinhaDoTempo_10")
            st.download_button(
                f"⬇️ Baixar XLSX",
                data=bytes_out,
                file_name=f"linha_do_tempo_10_{selected_id}.{ext}",
                mime=mime,
                key=f"{key_prefix}_download_timeline_xlsx_{selected_id}"
            )
        with col_pdf:
            pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tram10, f"Linha do Tempo - ID {selected_id}")
            st.download_button(
                f"⬇️ Baixar PDF",
                data=pdf_bytes,
                file_name=f"linha_do_tempo_10_{selected_id}.{pdf_ext}",
                mime=pdf_mime,
                key=f"{key_prefix}_download_timeline_pdf_{selected_id}"
            )


def montar_estrategia_tabela(situacao: str, relator_alerta: str = "") -> pd.DataFrame:
    rows = []
    if relator_alerta:
        rows.append({"Estratégia sugerida": relator_alerta})
    for it in estrategia_por_situacao(situacao):
        rows.append({"Estratégia sugerida": it})
    if not rows:
        rows = [{"Estratégia sugerida": "—"}]
    return pd.DataFrame(rows)


# ============================================================
# GRÁFICOS - COM PLOTLY PARA MELHOR VISUALIZAÇÃO
# ============================================================

def render_grafico_barras_situacao(df: pd.DataFrame):
    """Renderiza gráfico de barras horizontal por situação - MATPLOTLIB ESTÁTICO."""
    if df.empty or "Situação atual" not in df.columns:
        st.info("Sem dados para gráfico de situação.")
        return
    
    df_counts = (
        df.assign(_s=df["Situação atual"].fillna("-").replace("", "-"))
        .groupby("_s", as_index=False)
        .size()
        .rename(columns={"_s": "Situação", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=True)
    )
    
    if df_counts.empty:
        st.info("Sem dados para gráfico.")
        return
    
    st.markdown("##### 📊 Distribuição por Situação Atual")
    
    fig, ax = plt.subplots(figsize=(10, max(4, len(df_counts) * 0.4)))
    bars = ax.barh(df_counts["Situação"], df_counts["Quantidade"], color='#1f77b4')
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Quantidade")
    ax.set_ylabel("")
    ax.tick_params(axis='y', labelsize=9)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_barras_tema(df: pd.DataFrame):
    """Renderiza gráfico de barras por tema - MATPLOTLIB ESTÁTICO."""
    if df.empty or "Tema" not in df.columns:
        st.info("Sem dados para gráfico de tema.")
        return
    
    df_counts = (
        df.groupby("Tema", as_index=False)
        .size()
        .rename(columns={"size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Tema")
    
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#2ca02c')
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Tema"], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_mensal(df: pd.DataFrame):
    """Renderiza gráfico de tendência mensal - MATPLOTLIB ESTÁTICO."""
    if df.empty or "AnoStatus" not in df.columns or "MesStatus" not in df.columns:
        st.info("Sem dados para gráfico mensal.")
        return

    df_valid = df.dropna(subset=["AnoStatus", "MesStatus"]).copy()
    if df_valid.empty:
        return

    df_valid["AnoMes_sort"] = df_valid.apply(
        lambda r: int(r["AnoStatus"]) * 100 + int(r["MesStatus"]), axis=1
    )

    df_mensal = (
        df_valid.groupby("AnoMes_sort", as_index=False)
        .size()
        .rename(columns={"size": "Movimentações"})
        .sort_values("AnoMes_sort")
        .reset_index(drop=True)
    )

    if df_mensal.empty or len(df_mensal) < 2:
        return

    df_mensal["Label"] = df_mensal["AnoMes_sort"].apply(
        lambda ym: f"{int(ym)%100:02d}/{int(ym)//100}"
    )

    st.markdown("##### 📈 Tendência de Movimentações por Mês")
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(range(len(df_mensal)), df_mensal["Movimentações"], marker='o', color='#ff7f0e', linewidth=2, markersize=6)
    
    for i, (x, y) in enumerate(zip(range(len(df_mensal)), df_mensal["Movimentações"])):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=8)
    
    ax.set_xticks(range(len(df_mensal)))
    ax.set_xticklabels(df_mensal["Label"], rotation=45, ha='right', fontsize=8)
    ax.set_xlabel("Mês/Ano")
    ax.set_ylabel("Movimentações")
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_tipo(df: pd.DataFrame):
    """Renderiza gráfico por tipo de proposição - MATPLOTLIB ESTÁTICO."""
    if df.empty or "siglaTipo" not in df.columns:
        return
    
    df_counts = (
        df.groupby("siglaTipo", as_index=False)
        .size()
        .rename(columns={"siglaTipo": "Tipo", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Tipo de Proposição")
    
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#1f77b4')
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Tipo"], fontsize=10)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grafico_orgao(df: pd.DataFrame):
    """Renderiza gráfico por órgão atual - MATPLOTLIB ESTÁTICO."""
    if df.empty or "Órgão (sigla)" not in df.columns:
        return
    
    df_valid = df[df["Órgão (sigla)"].notna() & (df["Órgão (sigla)"] != "")].copy()
    if df_valid.empty:
        return
    
    df_counts = (
        df_valid.groupby("Órgão (sigla)", as_index=False)
        .size()
        .rename(columns={"Órgão (sigla)": "Órgão", "size": "Quantidade"})
        .sort_values("Quantidade", ascending=False)
        .head(15)
    )
    
    if df_counts.empty:
        return
    
    st.markdown("##### 📊 Distribuição por Órgão (Top 15)")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(range(len(df_counts)), df_counts["Quantidade"], color='#d62728')
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xticks(range(len(df_counts)))
    ax.set_xticklabels(df_counts["Órgão"], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Quantidade")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ============================================================
# UI
# ============================================================

def main():
    st.set_page_config(
        page_title="Monitor Legislativo – Dep. Júlia Zanatta",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.markdown("""
    <style>
    .map-small iframe { height: 320px !important; }
    div[data-testid="stDataFrame"] * {
        white-space: normal !important;
        word-break: break-word !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ============================================================
    # TÍTULO DO SISTEMA (sem foto - foto fica no card abaixo)
    # ============================================================
    st.title("📡 Monitor Legislativo – Dep. Júlia Zanatta")
    st.caption("v19 – PDFs profissionais Autoria/Relatoria e Comissões")

    if "status_click_sel" not in st.session_state:
        st.session_state["status_click_sel"] = None

    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Dados abertos da deputada
        st.subheader("Deputada monitorada")
        nome_deputada = st.text_input("Nome completo", value=DEPUTADA_NOME_PADRAO)
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            partido_deputada = st.text_input("Partido", value=DEPUTADA_PARTIDO_PADRAO)
        with c2:
            uf_deputada = st.text_input("UF", value=DEPUTADA_UF_PADRAO)
        with c3:
            id_dep_str = st.text_input("ID (Dados Abertos)", value=str(DEPUTADA_ID_PADRAO))
        
        try:
            id_deputada = int(id_dep_str)
        except ValueError:
            st.error("ID da deputada inválido. Use apenas números.")
            return

        st.markdown("---")
        st.subheader("Período de busca (pauta)")
        hoje = datetime.date.today()
        date_range = st.date_input(
            "Intervalo de datas", 
            value=(hoje, hoje + datetime.timedelta(days=7)),
            format="DD/MM/YYYY"
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            dt_inicio, dt_fim = date_range
        else:
            dt_inicio = hoje
            dt_fim = hoje + datetime.timedelta(days=7)

        st.markdown("---")
        st.subheader("Palavras-chave")
        palavras_str = st.text_area("Uma por linha", value="\n".join(PALAVRAS_CHAVE_PADRAO), height=120)
        palavras_chave = [p.strip() for p in palavras_str.splitlines() if p.strip()]

        st.subheader("Comissões estratégicas")
        comissoes_str = st.text_input("Siglas (sep. vírgula)", value=", ".join(COMISSOES_ESTRATEGICAS_PADRAO))
        comissoes_estrategicas = [c.strip().upper() for c in comissoes_str.split(",") if c.strip()]

        st.markdown("---")
        run_scan = st.button("▶️ Rodar monitoramento (pauta)", type="primary")

    df = st.session_state.get("df_scan", pd.DataFrame())

    if run_scan:
        with st.spinner("Carregando eventos..."):
            eventos = fetch_eventos(dt_inicio, dt_fim)

        with st.spinner("Carregando autorias..."):
            ids_autoria = fetch_ids_autoria_deputada(int(id_deputada))

        with st.spinner("Escaneando pautas..."):
            df = escanear_eventos(
                eventos,
                nome_deputada,
                partido_deputada,
                uf_deputada,
                palavras_chave,
                comissoes_estrategicas,
                apenas_reuniao_deliberativa=False,
                buscar_autoria=True,
                ids_autoria_deputada=ids_autoria,
            )

        st.session_state["df_scan"] = df
        st.success(f"Monitoramento concluído – {len(df)} registros")

    # ============================================================
    # CARD FIXO DA DEPUTADA (aparece em todas as abas)
    # ============================================================
    with st.container():
        col_dep_foto, col_dep_info = st.columns([1, 5])
        with col_dep_foto:
            try:
                st.image(f"https://www.camara.leg.br/internet/deputado/bandep/{id_deputada}.jpg", width=100)
            except:
                st.markdown("👤")
        with col_dep_info:
            st.markdown(f"**{nome_deputada}**")
            st.markdown(f"**Partido:** {partido_deputada} | **UF:** {uf_deputada}")
            st.markdown(f"[🔗 Perfil na Câmara](https://www.camara.leg.br/deputados/{id_deputada})")
    
    with st.expander("📋 Minibiografia", expanded=False):
        st.markdown("""
**Júlia Pedroso Zanatta** é deputada federal por Santa Catarina, filiada ao Partido Liberal (PL). 
Natural de Criciúma (SC), nasceu em 20 de março de 1985 e é formada em **Jornalismo** e **Direito**. 
Antes de ingressar no Congresso Nacional, atuou como jornalista, advogada e assessora política, 
com forte presença na comunicação e no debate público.

Iniciou sua trajetória eleitoral em 2020, quando concorreu à Prefeitura de Criciúma. Em 2022, 
foi eleita deputada federal, assumindo o mandato na Câmara dos Deputados em fevereiro de 2023, 
para a legislatura 2023–2027. No Parlamento, integra a bancada conservadora e liberal, sendo **vice-líder do PL**.

Sua atuação legislativa é marcada pela defesa da **liberdade econômica**, da **redução da carga tributária**, 
da **segurança jurídica**, da **liberdade de expressão** e de pautas conservadoras nos campos social e institucional. 
Júlia Zanatta também se destaca pela postura crítica ao aumento de impostos, ao expansionismo do Estado 
e a políticas que, em sua visão, ampliam a intervenção governamental na economia e na vida dos cidadãos.
        """)
    
    st.markdown("---")

    # ============================================================
    # ABAS REORGANIZADAS (6 abas)
    # ============================================================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "1️⃣ Apresentação",
        "2️⃣ Autoria & Relatoria na pauta",
        "3️⃣ Palavras-chave na pauta",
        "4️⃣ Comissões estratégicas",
        "5️⃣ Buscar Proposição Específica",
        "6️⃣ Matérias por situação atual"
    ])

    # ============================================================
    # ABA 1 - APRESENTAÇÃO E GLOSSÁRIO
    # ============================================================
    with tab1:
        st.subheader("📖 Apresentação do Sistema")
        
        st.markdown("""
Este **Monitor Legislativo** foi desenvolvido para acompanhar em tempo real a atuação parlamentar 
da Deputada Federal **Júlia Zanatta (PL-SC)** na Câmara dos Deputados.

O sistema consulta a **API de Dados Abertos da Câmara dos Deputados** para fornecer informações 
atualizadas sobre proposições, tramitações, pautas e eventos legislativos.
        """)
        
        st.markdown("---")
        st.markdown("### 🎯 Funcionalidades por Aba")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
**2️⃣ Autoria & Relatoria na pauta**
- Proposições de **autoria** da deputada que estão na pauta
- Proposições onde a deputada é **relatora**
- Filtrado pelo período selecionado na barra lateral

**3️⃣ Palavras-chave na pauta**
- Busca por **palavras-chave** configuradas
- Identifica proposições de interesse temático
- Vacinas, armas, aborto, PIX, DREX, etc.

**4️⃣ Comissões estratégicas**
- Eventos nas comissões de interesse
- CDC, CCOM, CE, CREDN, CCJC
            """)
        
        with col2:
            st.markdown("""
**5️⃣ Buscar Proposição Específica**
- Busca livre por qualquer proposição
- Filtros por ano e tipo
- Detalhes completos com linha do tempo

**6️⃣ Matérias por situação atual**
- Visão geral da **carteira de proposições**
- Gráficos analíticos por situação, tema, órgão
- Filtros multi-nível avançados
            """)
        
        st.markdown("---")
        st.markdown("### 📚 Glossário de Termos")
        
        with st.expander("📋 Tipos de Proposições", expanded=False):
            st.markdown("""
| Sigla | Nome Completo | Descrição |
|-------|---------------|-----------|
| **PL** | Projeto de Lei | Proposta de lei ordinária |
| **PLP** | Projeto de Lei Complementar | Lei que complementa a Constituição |
| **PEC** | Proposta de Emenda à Constituição | Altera a Constituição Federal |
| **PDL** | Projeto de Decreto Legislativo | Matérias de competência exclusiva do Congresso |
| **PRC** | Projeto de Resolução da Câmara | Normas internas da Câmara |
| **PLV** | Projeto de Lei de Conversão | Conversão de Medida Provisória em lei |
| **MPV** | Medida Provisória | Ato do Presidente com força de lei |
| **RIC** | Requerimento de Informação | Pedido de informações a órgãos públicos |
            """)
        
        with st.expander("📊 Situações de Tramitação", expanded=False):
            st.markdown("""
| Situação | Significado |
|----------|-------------|
| **Aguardando Designação de Relator** | Proposição aguarda indicação de parlamentar para analisar |
| **Aguardando Parecer** | Relator designado, aguardando elaboração do parecer |
| **Pronta para Pauta** | Parecer aprovado, aguarda inclusão em pauta de votação |
| **Tramitando em Conjunto** | Apensada a outra proposição principal |
| **Aguardando Deliberação** | Na pauta, aguardando votação |
| **Arquivada** | Proposição arquivada (fim de legislatura ou rejeição) |
            """)
        
        with st.expander("🚦 Indicadores de Urgência", expanded=False):
            st.markdown("""
| Sinal | Tempo parado | Nível |
|-------|--------------|-------|
| 🚨 | ≤ 2 dias | **URGENTÍSSIMO** - Ação imediata necessária |
| ⚠️ | ≤ 5 dias | **URGENTE** - Requer atenção prioritária |
| 🔔 | ≤ 15 dias | **RECENTE** - Acompanhar de perto |
| 🟢 | < 7 dias | Normal - Em movimento |
| 🟡 | 7-14 dias | Atenção - Verificar |
| 🟠 | 15-29 dias | Alerta - Possível estagnação |
| 🔴 | ≥ 30 dias | Crítico - Parado há muito tempo |
            """)
        
        with st.expander("🏛️ Comissões Estratégicas Monitoradas", expanded=False):
            st.markdown("""
| Sigla | Nome Completo |
|-------|---------------|
| **CDC** | Comissão de Defesa do Consumidor |
| **CCOM** | Comissão de Comunicação |
| **CE** | Comissão de Educação |
| **CREDN** | Comissão de Relações Exteriores e Defesa Nacional |
| **CCJC** | Comissão de Constituição e Justiça e de Cidadania |
            """)
        
        with st.expander("🏷️ Categorias de Temas", expanded=False):
            st.markdown("""
O sistema categoriza automaticamente as proposições nos seguintes temas:

- **Saúde** - Vacinas, hospitais, medicamentos, SUS, ANVISA
- **Segurança Pública** - Armas, polícia, crimes, sistema penal
- **Economia e Tributos** - PIX, DREX, impostos, IRPF, previdência
- **Família e Costumes** - Aborto, CONANDA, crianças, gênero
- **Educação** - Escolas, universidades, MEC, FUNDEB
- **Agronegócio** - Produtores rurais, terra, MST, defensivos
- **Meio Ambiente** - IBAMA, florestas, clima, saneamento
- **Comunicação e Tecnologia** - Internet, redes sociais, LGPD, IA
- **Administração Pública** - Servidores, concursos, licitações
- **Transporte e Infraestrutura** - Rodovias, portos, mobilidade
- **Defesa e Soberania** - Forças Armadas, fronteiras, militar
- **Direito e Justiça** - STF, STJ, tribunais, processos
- **Relações Exteriores** - Diplomacia, tratados, comércio exterior
            """)
        
        st.markdown("---")
        st.markdown("### ⚙️ Como Usar")
        
        st.info("""
1. **Configure o período** na barra lateral (datas de início e fim)
2. **Clique em "Rodar monitoramento"** para buscar eventos da pauta
3. **Navegue pelas abas** para ver diferentes visões dos dados
4. **Use os filtros** para refinar os resultados
5. **Exporte para XLSX** os dados que precisar
        """)
        
        st.markdown("---")
        st.caption("Desenvolvido para o Gabinete da Dep. Júlia Zanatta | Dados: API Câmara dos Deputados")

    # ============================================================
    # ABA 2 - AUTORIA & RELATORIA NA PAUTA - OTIMIZADA
    # ============================================================
    with tab2:
        st.subheader("Autoria & Relatoria na pauta")
        
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_a = df[df["tem_autoria_deputada"] | df["tem_relatoria_deputada"]].copy()
            if df_a.empty:
                st.info("Sem autoria nem relatoria no período.")
            else:
                view = df_a[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "proposicoes_autoria", "ids_proposicoes_autoria", 
                     "proposicoes_relatoria", "ids_proposicoes_relatoria", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                col_x1, col_p1 = st.columns(2)
                with col_x1:
                    data_bytes, mime, ext = to_xlsx_bytes(view, "Autoria_Relatoria")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=data_bytes,
                        file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{ext}",
                        mime=mime,
                    )
                with col_p1:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_autoria_relatoria(view)
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"autoria_relatoria_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                        mime=pdf_mime,
                    )
                
                st.markdown("---")
                st.markdown("### 📋 Ver detalhes de proposição de autoria na pauta")
                
                # OTIMIZADO: Extrai IDs diretamente da coluna ids_proposicoes_autoria (já tem os IDs)
                ids_autoria_pauta = set()
                for _, row in df_a.iterrows():
                    val = row.get("ids_proposicoes_autoria", "")
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != "nan":
                            # IDs já estão separados por ;
                            for pid in val_str.split(";"):
                                pid = pid.strip()
                                if pid and pid.isdigit():
                                    ids_autoria_pauta.add(pid)
                
                if not ids_autoria_pauta:
                    st.info("Nenhuma proposição de autoria identificada na pauta.")
                else:
                    st.markdown(f"**{len(ids_autoria_pauta)} proposição(ões) de autoria encontrada(s)**")
                    
                    # Carrega info apenas quando usuário selecionar (lazy loading)
                    opcoes_props = {}
                    for pid in sorted(ids_autoria_pauta):
                        info = fetch_proposicao_info(pid)
                        label = format_sigla_num_ano(info["sigla"], info["numero"], info["ano"]) or f"ID {pid}"
                        opcoes_props[label] = pid
                    
                    if opcoes_props:
                        prop_selecionada = st.selectbox(
                            "Selecione uma proposição para ver detalhes:",
                            options=list(opcoes_props.keys()),
                            key="select_prop_autoria_tab2"
                        )
                        
                        if prop_selecionada:
                            selected_id_tab2 = opcoes_props[prop_selecionada]
                            exibir_detalhes_proposicao(selected_id_tab2, key_prefix="tab2")

    # ============================================================
    # ABA 3 - PALAVRAS-CHAVE
    # ============================================================
    with tab3:
        st.subheader("Palavras-chave na pauta")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_kw = df[df["tem_palavras_chave"]].copy()
            if df_kw.empty:
                st.info("Sem palavras-chave no período.")
            else:
                view = df_kw[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "palavras_chave_encontradas", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                col_x2, col_p2 = st.columns(2)
                with col_x2:
                    data_bytes, mime, ext = to_xlsx_bytes(view, "PalavrasChave_Pauta")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=data_bytes,
                        file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{ext}",
                        mime=mime,
                        key="download_kw_xlsx"
                    )
                with col_p2:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(view, "Palavras-chave na Pauta")
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"palavras_chave_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                        mime=pdf_mime,
                        key="download_kw_pdf"
                    )

    # ============================================================
    # ABA 4 - COMISSÕES ESTRATÉGICAS
    # ============================================================
    with tab4:
        st.subheader("Comissões estratégicas")
        if df.empty:
            st.info("Clique em **Rodar monitoramento (pauta)** na lateral para carregar.")
        else:
            df_com = df[df["comissao_estrategica"]].copy()
            if df_com.empty:
                st.info("Sem eventos em comissões estratégicas no período.")
            else:
                view = df_com[
                    ["data", "hora", "orgao_sigla", "orgao_nome", "id_evento", "tipo_evento",
                     "proposicoes_autoria", "proposicoes_relatoria", "palavras_chave_encontradas", "descricao_evento"]
                ].copy()
                view["data"] = pd.to_datetime(view["data"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.dataframe(view, use_container_width=True, hide_index=True)

                col_x3, col_p3 = st.columns(2)
                with col_x3:
                    data_bytes, mime, ext = to_xlsx_bytes(view, "ComissoesEstrategicas_Pauta")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=data_bytes,
                        file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{ext}",
                        mime=mime,
                        key="download_com_xlsx"
                    )
                with col_p3:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_comissoes_estrategicas(view)
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"comissoes_estrategicas_pauta_{dt_inicio}_{dt_fim}.{pdf_ext}",
                        mime=pdf_mime,
                        key="download_com_pdf"
                    )

    # ============================================================
    # ABA 5 - BUSCAR PROPOSIÇÃO ESPECÍFICA (LIMPA)
    # ============================================================
    with tab5:
        st.markdown("### 🔍 Buscar Proposição Específica")
        st.caption("Busque proposições de autoria da deputada e veja detalhes completos")

        # Botão de limpar cache
        col_cache, col_info = st.columns([1, 3])
        with col_cache:
            if st.button("🧹 Limpar cache", key="limpar_cache_tab5"):
                fetch_proposicao_completa.clear()
                fetch_lista_proposicoes_autoria_geral.clear()
                fetch_rics_por_autor.clear()
                fetch_lista_proposicoes_autoria.clear()
                build_status_map.clear()
                st.session_state.pop("df_status_last", None)
                st.success("✅ Cache limpo!")

        # Carrega proposições
        with st.spinner("Carregando proposições de autoria..."):
            df_aut = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
        else:
            df_aut = df_aut[df_aut["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

            # Filtros básicos
            st.markdown("#### 🗂️ Filtros de Proposições")
            col_ano, col_tipo = st.columns([1, 1])
            with col_ano:
                anos = sorted([a for a in df_aut["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
                anos_sel = st.multiselect("Ano", options=anos, default=anos[:3] if len(anos) >= 3 else anos, key="anos_tab5")
            with col_tipo:
                tipos = sorted([t for t in df_aut["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
                tipos_sel = st.multiselect("Tipo", options=tipos, default=tipos, key="tipos_tab5")

            df_base = df_aut.copy()
            if anos_sel:
                df_base = df_base[df_base["ano"].isin(anos_sel)].copy()
            if tipos_sel:
                df_base = df_base[df_base["siglaTipo"].isin(tipos_sel)].copy()

            st.markdown("---")

            # Campo de busca
            q = st.text_input(
                "Filtrar proposições",
                value="",
                placeholder="Ex.: PL 2030/2025 | 'pix' | 'conanda'",
                help="Busque por sigla/número/ano ou palavras na ementa",
                key="busca_tab5"
            )

            df_rast = df_base.copy()
            if q.strip():
                qn = normalize_text(q)
                df_rast["_search"] = (df_rast["Proposicao"].fillna("").astype(str) + " " + df_rast["ementa"].fillna("").astype(str)).apply(normalize_text)
                df_rast = df_rast[df_rast["_search"].str.contains(qn, na=False)].drop(columns=["_search"], errors="ignore")

            df_rast_lim = df_rast.head(400).copy()
            
            with st.spinner("Carregando status das proposições..."):
                ids_r = df_rast_lim["id"].astype(str).tolist()
                status_map_r = build_status_map(ids_r)
                df_rast_enriched = enrich_with_status(df_rast_lim, status_map_r)

            df_rast_enriched = df_rast_enriched.sort_values("DataStatus_dt", ascending=False)

            st.caption(f"Resultados: {len(df_rast_enriched)} proposições")

            df_tbl = df_rast_enriched.rename(
                columns={"Proposicao": "Proposição", "ementa": "Ementa", "id": "ID", "ano": "Ano", "siglaTipo": "Tipo"}
            ).copy()
            
            df_tbl["Último andamento"] = df_rast_enriched["Andamento (status)"]
            df_tbl["LinkTramitacao"] = df_tbl["ID"].astype(str).apply(camara_link_tramitacao)
            
            def get_alerta_emoji(dias):
                if pd.isna(dias):
                    return ""
                if dias <= 2:
                    return "🚨"
                if dias <= 5:
                    return "⚠️"
                if dias <= 15:
                    return "🔔"
                return ""
            
            df_tbl["Alerta"] = df_rast_enriched["Parado (dias)"].apply(get_alerta_emoji)

            show_cols_r = [
                "Alerta", "Proposição", "Ementa", "ID", "Ano", "Tipo", "Órgão (sigla)",
                "Situação atual", "Último andamento", "Data do status", "LinkTramitacao",
            ]

            for c in show_cols_r:
                if c not in df_tbl.columns:
                    df_tbl[c] = ""
            
            sel = st.dataframe(
                df_tbl[show_cols_r],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Alerta": st.column_config.TextColumn("", width="small", help="Urgência"),
                    "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                    "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                },
                key="df_busca_tab5"
            )
            
            st.caption("🚨 ≤2 dias (URGENTÍSSIMO) | ⚠️ ≤5 dias (URGENTE) | 🔔 ≤15 dias (Recente)")
            
            # Exportação
            col_x4, col_p4 = st.columns(2)
            with col_x4:
                bytes_rast, mime_rast, ext_rast = to_xlsx_bytes(df_tbl[show_cols_r], "Busca_Especifica")
                st.download_button(
                    f"⬇️ XLSX",
                    data=bytes_rast,
                    file_name=f"busca_especifica_proposicoes.{ext_rast}",
                    mime=mime_rast,
                    key="export_busca_xlsx_tab5"
                )
            with col_p4:
                pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tbl[show_cols_r], "Busca Específica")
                st.download_button(
                    f"⬇️ PDF",
                    data=pdf_bytes,
                    file_name=f"busca_especifica_proposicoes.{pdf_ext}",
                    mime=pdf_mime,
                    key="export_busca_pdf_tab5"
                )

            # Detalhes da proposição selecionada
            selected_id = None
            try:
                if sel and isinstance(sel, dict) and sel.get("selection") and sel["selection"].get("rows"):
                    row_idx = sel["selection"]["rows"][0]
                    selected_id = str(df_tbl.iloc[row_idx]["ID"])
            except Exception:
                selected_id = None

            st.markdown("---")
            st.markdown("#### 📋 Detalhes da Proposição Selecionada")

            if not selected_id:
                st.info("Clique em uma proposição acima para ver detalhes completos.")
            else:
                exibir_detalhes_proposicao(selected_id, key_prefix="tab5")

    # ============================================================
    # ABA 6 - MATÉRIAS POR SITUAÇÃO ATUAL (separada)
    # ============================================================
    with tab6:
        st.markdown("### 📊 Matérias por situação atual")
        st.caption("Análise da carteira de proposições por status de tramitação")

        with st.spinner("Carregando proposições de autoria..."):
            df_aut6 = fetch_lista_proposicoes_autoria(id_deputada)

        if df_aut6.empty:
            st.info("Nenhuma proposição de autoria encontrada.")
        else:
            df_aut6 = df_aut6[df_aut6["siglaTipo"].isin(TIPOS_CARTEIRA_PADRAO)].copy()

            st.markdown("#### 🗂️ Filtros de Proposições")
            
            col2, col3 = st.columns([1.1, 1.1])
            with col2:
                anos6 = sorted([a for a in df_aut6["ano"].dropna().unique().tolist() if str(a).strip().isdigit()], reverse=True)
                anos_sel6 = st.multiselect("Ano (da proposição)", options=anos6, default=anos6[:3] if len(anos6) >= 3 else anos6, key="anos_tab6")
            with col3:
                tipos6 = sorted([t for t in df_aut6["siglaTipo"].dropna().unique().tolist() if str(t).strip()])
                tipos_sel6 = st.multiselect("Tipo", options=tipos6, default=tipos6, key="tipos_tab6")

            df_base6 = df_aut6.copy()
            if anos_sel6:
                df_base6 = df_base6[df_base6["ano"].isin(anos_sel6)].copy()
            if tipos_sel6:
                df_base6 = df_base6[df_base6["siglaTipo"].isin(tipos_sel6)].copy()

            st.markdown("---")

            cS1, cS2, cS3, cS4 = st.columns([1.2, 1.2, 1.6, 1.0])
           
            with cS2:
                max_status = st.number_input(
                    "Limite (performance)",
                    min_value=20,
                    max_value=600,
                    value=min(200, len(df_base6)) if len(df_base6) else 20,
                    step=20,
                    key="max_status_tab6"
                )
            with cS3:
                st.caption("Aplique filtros acima (Ano/Tipo) e depois carregue o status.")
            with cS4:
                if st.button("✖ Limpar filtro por clique", key="limpar_click_tab6"):
                    st.session_state["status_click_sel"] = None

            df_status_view = st.session_state.get("df_status_last", pd.DataFrame()).copy()

            dynamic_status = []
            if not df_status_view.empty and "Situação atual" in df_status_view.columns:
                dynamic_status = [s for s in df_status_view["Situação atual"].dropna().unique().tolist() if str(s).strip()]
            status_opts = merge_status_options(dynamic_status)

            # Filtros Multi-nível
            st.markdown("##### 🔍 Filtros Multi-nível")
            
            f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.1, 1.1])

            default_status_sel = []
            if st.session_state.get("status_click_sel"):
                default_status_sel = [st.session_state["status_click_sel"]]

            org_opts = []
            ano_status_opts = []
            mes_status_opts = []
            tema_opts = []
            relator_opts = []

            if not df_status_view.empty:
                org_opts = sorted(
                    [o for o in df_status_view["Órgão (sigla)"].dropna().unique().tolist() if str(o).strip()]
                )

                ano_status_opts = sorted(
                    [int(a) for a in df_status_view["AnoStatus"].dropna().unique().tolist() if pd.notna(a)],
                    reverse=True
                )

                mes_status_opts = sorted(
                    [int(m) for m in df_status_view["MesStatus"].dropna().unique().tolist() if pd.notna(m)]
                )
                
                if "Tema" in df_status_view.columns:
                    tema_opts = sorted(
                        [t for t in df_status_view["Tema"].dropna().unique().tolist() if str(t).strip()]
                    )
                
                if "Relator(a)" in df_status_view.columns:
                    relator_opts = sorted(
                        [r for r in df_status_view["Relator(a)"].dropna().unique().tolist() 
                         if str(r).strip() and str(r).strip() != "—"]
                    )

            with f1:
                status_sel = st.multiselect("Situação Atual", options=status_opts, default=default_status_sel, key="status_sel_tab6")

            with f2:
                org_sel = st.multiselect("Órgão (sigla)", options=org_opts, default=[], key="org_sel_tab6")

            with f3:
                ano_status_sel = st.multiselect("Ano (do status)", options=ano_status_opts, default=[], key="ano_status_sel_tab6")

            with f4:
                mes_labels = [f"{m:02d}-{MESES_PT.get(m, '')}" for m in mes_status_opts]
                mes_map = {f"{m:02d}-{MESES_PT.get(m, '')}": m for m in mes_status_opts}
                mes_sel_labels = st.multiselect("Mês (do status)", options=mes_labels, default=[], key="mes_sel_tab6")
                mes_status_sel = [mes_map[x] for x in mes_sel_labels if x in mes_map]
            
            # Segunda linha de filtros multi-nível
            f5, f6, f7 = st.columns([1.2, 1.2, 1.6])
            
            with f5:
                tema_sel = st.multiselect("Tema", options=tema_opts, default=[], key="tema_sel_tab6")
            
            with f6:
                relator_sel = st.multiselect("Relator(a)", options=relator_opts, default=[], key="relator_sel_tab5")
            
            with f7:
                palavra_filtro = st.text_input(
                    "Palavra-chave na ementa",
                    placeholder="Digite para filtrar...",
                    help="Filtra proposições que contenham esta palavra na ementa",
                    key="palavra_filtro_tab5"
                )

            bt_status = st.button("Carregar/Atualizar status", type="primary", key="carregar_status_tab5")

            if bt_status:
                with st.spinner("Buscando status..."):
                    ids_list = df_base6["id"].astype(str).head(int(max_status)).tolist()
                    status_map = build_status_map(ids_list)
                    df_status_view = enrich_with_status(df_base6.head(int(max_status)), status_map)
                    st.session_state["df_status_last"] = df_status_view

            if df_status_view.empty:
                st.info(
                    "Clique em **Carregar/Atualizar status** para preencher "
                    "Situação/Órgão/Data e habilitar filtros por mês/ano."
                )
            else:
                df_fil = df_status_view.copy()

                # Aplicar filtros multi-nível
                if status_sel:
                    df_fil = df_fil[df_fil["Situação atual"].isin(status_sel)].copy()

                if org_sel:
                    df_fil = df_fil[df_fil["Órgão (sigla)"].isin(org_sel)].copy()

                if ano_status_sel:
                    df_fil = df_fil[df_fil["AnoStatus"].isin(ano_status_sel)].copy()

                if mes_status_sel:
                    df_fil = df_fil[df_fil["MesStatus"].isin(mes_status_sel)].copy()
                
                if tema_sel and "Tema" in df_fil.columns:
                    df_fil = df_fil[df_fil["Tema"].isin(tema_sel)].copy()
                
                if relator_sel and "Relator(a)" in df_fil.columns:
                    df_fil = df_fil[df_fil["Relator(a)"].isin(relator_sel)].copy()
                
                if palavra_filtro.strip():
                    palavra_norm = normalize_text(palavra_filtro)
                    df_fil = df_fil[df_fil["ementa"].apply(lambda x: palavra_norm in normalize_text(str(x)))].copy()

                # Garantir coluna de dias parado para cálculos
                if "Parado (dias)" in df_fil.columns and "Parado há (dias)" not in df_fil.columns:
                    df_fil["Parado há (dias)"] = df_fil["Parado (dias)"]

                st.markdown("---")
                
                # ============================================================
                # VISÃO EXECUTIVA - RESUMO, ATENÇÃO, PRIORIDADES
                # ============================================================
                with st.expander("🎯 Visão Executiva (Deputada / Chefia / Assessoria)", expanded=True):
                    render_resumo_executivo(df_fil)
                    render_atencao_deputada(df_fil)
                    render_prioridades_gabinete(df_fil)
                
                # ============================================================
                # GRÁFICOS - ORDENADOS DECRESCENTE
                # ============================================================
                st.markdown("#### 📈 Análise Visual")
                
                with st.expander("📊 Gráficos e Análises", expanded=True):
                    g1, g2 = st.columns(2)
                    
                    with g1:
                        render_grafico_barras_situacao(df_fil)
                    
                    with g2:
                        render_grafico_barras_tema(df_fil)
                    
                    g3, g4 = st.columns(2)
                    
                    with g3:
                        render_grafico_tipo(df_fil)
                    
                    with g4:
                        render_grafico_orgao(df_fil)
                    
                    render_grafico_mensal(df_fil)

                st.markdown("---")

                df_tbl_status = df_fil.copy()
                df_tbl_status["Parado há"] = df_tbl_status["Parado (dias)"].apply(
                    lambda x: f"{int(x)} dias" if isinstance(x, (int, float)) and pd.notna(x) else "—"
                )
                df_tbl_status["LinkTramitacao"] = df_tbl_status["id"].astype(str).apply(camara_link_tramitacao)

                df_tbl_status = df_tbl_status.rename(columns={
                    "Proposicao": "Proposição",
                    "siglaTipo": "Tipo",
                    "ano": "Ano",
                    "ementa": "Ementa",
                })

                show_cols = [
                    "Proposição", "Tipo", "Ano", "Situação atual", "Órgão (sigla)", "Relator(a)",
                    "Data do status", "Sinal", "Parado há", "Tema", "id", "LinkTramitacao", "Ementa"
                ]
                for c in show_cols:
                    if c not in df_tbl_status.columns:
                        df_tbl_status[c] = ""

                df_counts = (
                    df_fil.assign(
                        _s=df_fil["Situação atual"].fillna("-").replace("", "-")
                    )
                    .groupby("_s", as_index=False)
                    .size()
                    .rename(columns={"_s": "Situação atual", "size": "Qtde"})
                    .sort_values("Qtde", ascending=False)
                )

                cC1, cC2 = st.columns([1.0, 2.0])

                with cC1:
                    st.markdown("**Contagem por Situação atual**")
                    st.dataframe(df_counts, hide_index=True, use_container_width=True)

                with cC2:
                    st.markdown("**Lista filtrada (mais antigo no topo)**")
                    
                    st.dataframe(
                        df_tbl_status[show_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "LinkTramitacao": st.column_config.LinkColumn("Link", display_text="abrir"),
                            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
                            "Relator(a)": st.column_config.TextColumn("Relator(a)", width="medium"),
                        },
                    )

                col_x5, col_p5 = st.columns(2)
                with col_x5:
                    bytes_out, mime, ext = to_xlsx_bytes(df_tbl_status[show_cols], "Materias_Situacao")
                    st.download_button(
                        f"⬇️ XLSX",
                        data=bytes_out,
                        file_name=f"materias_por_situacao_atual.{ext}",
                        mime=mime,
                        key="download_materias_xlsx_tab6"
                    )
                with col_p5:
                    pdf_bytes, pdf_mime, pdf_ext = to_pdf_bytes(df_tbl_status[show_cols], "Matérias por Situação")
                    st.download_button(
                        f"⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"materias_por_situacao_atual.{pdf_ext}",
                        mime=pdf_mime,
                        key="download_materias_pdf_tab6"
                    )

    st.markdown("---")


if __name__ == "__main__":
    main()