"""
Utilitários de texto para o Monitor Parlamentar.
Funções de normalização, sanitização e formatação de strings.

REGRA: Este módulo NÃO pode importar streamlit.
"""
import unicodedata
import re
from typing import Optional


# ============================================================
# NORMALIZAÇÃO DE MINISTÉRIOS (nomes canônicos)
# ============================================================
# Mapeamento de variações textuais para nomes canônicos únicos

MINISTERIOS_CANONICOS = {
    # Ministério da Agricultura e Pecuária
    "Ministério da Agricultura e Pecuária": [
        "agricultura", "pecuária", "pecuaria", "agro", "agropecuária", "agropecuaria",
        "agricultura e pecuária", "agricultura e pecuaria", "mapa", "favaro",
        "ministro de estado da agricultura", "ministério da agricultura"
    ],
    
    # Ministério das Cidades
    "Ministério das Cidades": [
        "cidades", "ministério das cidades", "ministerio das cidades", "jader filho"
    ],
    
    # Ministério da Ciência, Tecnologia e Inovação
    "Ministério da Ciência, Tecnologia e Inovação": [
        "ciência", "ciencia", "tecnologia", "inovação", "inovacao", "mcti",
        "ciência e tecnologia", "ciencia e tecnologia", "luciana santos"
    ],
    
    # Ministério das Comunicações
    "Ministério das Comunicações": [
        "comunicações", "comunicacoes", "correios", "ect", "anatel", "juscelino",
        "ministério das comunicações", "ministerio das comunicacoes", "telecomunicações"
    ],
    
    # Ministério da Cultura
    "Ministério da Cultura": [
        "cultura", "ministério da cultura", "ministerio da cultura", "minc", "margareth menezes"
    ],
    
    # Ministério da Defesa
    "Ministério da Defesa": [
        "defesa", "ministério da defesa", "ministerio da defesa", "múcio", "mucio",
        "forças armadas", "forcas armadas"
    ],
    
    # Ministério do Desenvolvimento Agrário
    "Ministério do Desenvolvimento Agrário e Agricultura Familiar": [
        "desenvolvimento agrário", "desenvolvimento agrario", "agricultura familiar",
        "mda", "incra", "reforma agrária", "reforma agraria", "paulo teixeira"
    ],
    
    # Ministério do Desenvolvimento e Assistência Social
    "Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome": [
        "desenvolvimento social", "assistência social", "assistencia social",
        "combate à fome", "combate a fome", "mds", "bolsa família", "bolsa familia",
        "wellington dias"
    ],
    
    # Ministério do Desenvolvimento, Indústria, Comércio e Serviços
    "Ministério do Desenvolvimento, Indústria, Comércio e Serviços": [
        "desenvolvimento, indústria", "desenvolvimento, industria", "comércio e serviços",
        "comercio e servicos", "mdic", "indústria", "industria", "geraldo alckmin", "alckmin"
    ],
    
    # Ministério da Educação
    "Ministério da Educação": [
        "educação", "educacao", "mec", "ensino", "camilo santana", "universidade", "escolas"
    ],
    
    # Ministério do Empreendedorismo
    "Ministério do Empreendedorismo, da Microempresa e da Empresa de Pequeno Porte": [
        "empreendedorismo", "microempresa", "empresa de pequeno porte", "mpe",
        "márcio frança", "marcio franca"
    ],
    
    # Ministério do Esporte
    "Ministério do Esporte": [
        "esporte", "esportes", "ministério do esporte", "ministerio do esporte",
        "andré fufuca", "andre fufuca"
    ],
    
    # Ministério da Fazenda
    "Ministério da Fazenda": [
        "fazenda", "ministério da fazenda", "ministerio da fazenda", "mf",
        "fernando haddad", "haddad", "receita federal", "tesouro"
    ],
    
    # Ministério da Gestão e Inovação em Serviços Públicos
    "Ministério da Gestão e da Inovação em Serviços Públicos": [
        "gestão", "gestao", "inovação em serviços", "inovacao em servicos",
        "serviços públicos", "servicos publicos", "esther dweck", "dweck"
    ],
    
    # Ministério da Igualdade Racial
    "Ministério da Igualdade Racial": [
        "igualdade racial", "ministério da igualdade racial", "ministerio da igualdade racial",
        "anielle franco"
    ],
    
    # Ministério da Integração e do Desenvolvimento Regional
    "Ministério da Integração e do Desenvolvimento Regional": [
        "integração", "integracao", "desenvolvimento regional", "midr",
        "waldez góes", "waldez goes"
    ],
    
    # Ministério da Justiça e Segurança Pública
    "Ministério da Justiça e Segurança Pública": [
        "justiça", "justica", "segurança pública", "seguranca publica", "mjsp", "mj",
        "polícia federal", "policia federal", "pf", "flávio dino", "flavio dino", "ricardo lewandowski"
    ],
    
    # Ministério do Meio Ambiente
    "Ministério do Meio Ambiente e Mudança do Clima": [
        "meio ambiente", "mudança do clima", "mudanca do clima", "mma",
        "marina silva", "ibama", "icmbio"
    ],
    
    # Ministério de Minas e Energia
    "Ministério de Minas e Energia": [
        "minas e energia", "mme", "energia", "petróleo", "petroleo", "gás", "gas",
        "alexandre silveira"
    ],
    
    # Ministério das Mulheres
    "Ministério das Mulheres": [
        "mulheres", "ministério das mulheres", "ministerio das mulheres",
        "cida gonçalves", "cida goncalves"
    ],
    
    # Ministério dos Povos Indígenas
    "Ministério dos Povos Indígenas": [
        "povos indígenas", "povos indigenas", "indígenas", "indigenas", "funai",
        "sonia guajajara"
    ],
    
    # Ministério da Pesca e Aquicultura
    "Ministério da Pesca e Aquicultura": [
        "pesca", "aquicultura", "ministério da pesca", "ministerio da pesca",
        "andré de paula", "andre de paula"
    ],
    
    # Ministério do Planejamento e Orçamento
    "Ministério do Planejamento e Orçamento": [
        "planejamento", "orçamento", "orcamento", "mpo",
        "simone tebet", "tebet"
    ],
    
    # Ministério dos Portos e Aeroportos
    "Ministério de Portos e Aeroportos": [
        "portos", "aeroportos", "ministério de portos", "ministerio de portos",
        "silvio costa filho"
    ],
    
    # Ministério da Previdência Social
    "Ministério da Previdência Social": [
        "previdência", "previdencia", "inss", "aposentadoria",
        "carlos lupi", "lupi"
    ],
    
    # Ministério das Relações Exteriores
    "Ministério das Relações Exteriores": [
        "relações exteriores", "relacoes exteriores", "mre", "itamaraty",
        "mauro vieira"
    ],
    
    # Ministério da Saúde
    "Ministério da Saúde": [
        "saúde", "saude", "ministério da saúde", "ministerio da saude", "ms",
        "nísia trindade", "nisia trindade", "sus", "anvisa"
    ],
    
    # Ministério do Trabalho e Emprego
    "Ministério do Trabalho e Emprego": [
        "trabalho", "emprego", "ministério do trabalho", "ministerio do trabalho", "mte",
        "luiz marinho", "marinho"
    ],
    
    # Ministério dos Transportes
    "Ministério dos Transportes": [
        "transportes", "ministério dos transportes", "ministerio dos transportes",
        "renan filho"
    ],
    
    # Ministério do Turismo
    "Ministério do Turismo": [
        "turismo", "ministério do turismo", "ministerio do turismo", "mtur",
        "celso sabino"
    ],
    
    # Advocacia-Geral da União
    "Advocacia-Geral da União": [
        "agu", "advocacia-geral", "advocacia geral", "jorge messias"
    ],
    
    # Controladoria-Geral da União
    "Controladoria-Geral da União": [
        "cgu", "controladoria", "vinícius carvalho", "vinicius carvalho"
    ],
    
    # Gabinete de Segurança Institucional
    "Gabinete de Segurança Institucional": [
        "gsi", "segurança institucional", "seguranca institucional",
        "marcos antonio amaro"
    ],
    
    # Casa Civil
    "Casa Civil da Presidência da República": [
        "casa civil", "rui costa"
    ],
    
    # Secretaria-Geral da Presidência
    "Secretaria-Geral da Presidência da República": [
        "secretaria-geral", "secretaria geral", "márcio macêdo", "marcio macedo"
    ],
    
    # Secretaria de Relações Institucionais
    "Secretaria de Relações Institucionais": [
        "relações institucionais", "relacoes institucionais", "alexandre padilha", "padilha"
    ],
    
    # Secretaria de Comunicação Social
    "Secretaria de Comunicação Social": [
        "secom", "comunicação social", "comunicacao social", "paulo pimenta", "pimenta"
    ],
    
    # Banco Central (adicionado para completude)
    "Banco Central do Brasil": [
        "banco central", "bacen", "bcb", "galípolo", "galipolo", "campos neto"
    ],
}

# Mapeamento legado (mantido para compatibilidade)
MINISTERIOS_KEYWORDS = MINISTERIOS_CANONICOS


def normalize_ministerio(texto: str) -> str:
    """
    Normaliza o nome do ministério para uma nomenclatura canônica única.
    
    Regras:
    - Remove acentos e converte para minúsculas
    - Ignora nomes de ministros, cargos, artigos
    - Para keywords curtas (<6 chars), usa word boundary para evitar falsos positivos
    - Retorna o nome canônico ou "Não identificado"
    """
    if not texto:
        return "Não identificado"
    
    # Normalizar texto: remover acentos, lowercase
    texto_norm = texto.lower().strip()
    
    # Remover acentos
    texto_norm = unicodedata.normalize('NFD', texto_norm)
    texto_norm = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    
    # Remover termos genéricos
    termos_remover = [
        "ministro de estado", "ministra de estado", "ministro", "ministra",
        "sr.", "sra.", "senhor", "senhora", "exmo.", "exma.",
        "chefe da", "chefe do", "chefe", "ao ", "a ", "do ", "da ", "de ", "dos ", "das "
    ]
    
    for termo in termos_remover:
        texto_norm = texto_norm.replace(termo, " ")
    
    # Limpar espaços extras
    texto_norm = " ".join(texto_norm.split())
    
    # Procurar correspondência nos ministérios canônicos
    melhor_match = None
    melhor_score = 0
    
    for nome_canonico, keywords in MINISTERIOS_CANONICOS.items():
        for kw in keywords:
            # Normalizar keyword também
            kw_norm = unicodedata.normalize('NFD', kw.lower())
            kw_norm = ''.join(c for c in kw_norm if unicodedata.category(c) != 'Mn')
            
            # Para keywords curtas, usar word boundary para evitar falsos positivos
            if len(kw_norm) < 6:
                # Usar regex com word boundary
                pattern = r'\b' + re.escape(kw_norm) + r'\b'
                if re.search(pattern, texto_norm):
                    score = len(kw_norm) + 10  # Bonus por match exato
                    if score > melhor_score:
                        melhor_score = score
                        melhor_match = nome_canonico
            else:
                # Para keywords longas, substring match é ok
                if kw_norm in texto_norm:
                    # Priorizar matches mais longos (mais específicos)
                    score = len(kw_norm)
                    if score > melhor_score:
                        melhor_score = score
                        melhor_match = nome_canonico
    
    return melhor_match if melhor_match else "Não identificado"


def canonical_situacao(situacao: str) -> str:
    """
    Normaliza o texto da situação de uma proposição.
    Retorna o texto limpo e padronizado.
    """
    if not situacao:
        return ""
    
    # Limpar e normalizar
    texto = str(situacao).strip()
    
    # Remover múltiplos espaços
    texto = " ".join(texto.split())
    
    return texto


def normalize_text(text: str) -> str:
    """
    Normaliza texto removendo acentos e convertendo para minúsculas.
    Usado para buscas e comparações.
    """
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


def party_norm(sigla: str) -> str:
    """Normaliza sigla de partido político."""
    s = (sigla or "").strip().upper()
    if s in {"PC DO B", "PCDOB", "PCDOB ", "PCD0B"}:
        return "PCDOB"
    return s


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
