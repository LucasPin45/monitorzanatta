"""
Configurações e constantes globais do Monitor Parlamentar.
Este arquivo centraliza valores "hardcoded" e configurações do sistema.

REGRA: Este módulo NÃO pode importar streamlit.
NOTA: Constantes relacionadas a lógica de utils (MINISTERIOS_CANONICOS,
      TZ_BRASILIA, PARTIDOS_*) estão em core/utils/ para evitar duplicação.
"""

# ============================================================
# CONFIGURAÇÕES DE API
# ============================================================

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

HEADERS = {"User-Agent": "MonitorZanatta/22.0 (gabinete-julia-zanatta)"}


# ============================================================
# IDENTIDADE DA DEPUTADA
# ============================================================

DEPUTADA_NOME_PADRAO = "Júlia Zanatta"
DEPUTADA_PARTIDO_PADRAO = "PL"
DEPUTADA_UF_PADRAO = "SC"
DEPUTADA_ID_PADRAO = 220559


# ============================================================
# LISTAS PADRÃO PARA FILTROS
# ============================================================

PALAVRAS_CHAVE_PADRAO = [
    "Vacina", "Vacinas", "Armas", "Arma", "Armamento", "Aborto", "Conanda", 
    "Violência", "PIX", "DREX", "Imposto de Renda", "IRPF", "Logística"
]

COMISSOES_ESTRATEGICAS_PADRAO = ["CDC", "CCOM", "CE", "CREDN", "CCJC"]

TIPOS_CARTEIRA_PADRAO = ["PL", "PLP", "PDL", "PEC", "PRC", "PLV", "MPV", "RIC"]


# ============================================================
# STATUS E MESES
# ============================================================

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


# ============================================================
# PALAVRAS-CHAVE PARA DETECÇÃO DE RESPOSTA EM RICs
# ============================================================

RIC_RESPOSTA_KEYWORDS = [
    "resposta", "encaminha resposta", "recebimento de resposta", 
    "resposta do poder executivo", "resposta ao requerimento",
    "resposta do ministério", "resposta do ministerio", "atendimento ao requerimento"
]


# ============================================================
# TEMAS PARA CATEGORIZAÇÃO (palavras-chave por tema)
# ============================================================

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
# WORKAROUND: Proposições faltantes na API da Câmara
# ============================================================
# A API da Câmara (endpoint idDeputadoAutor) não retorna algumas
# proposições que são OFICIALMENTE de autoria da deputada.

PROPOSICOES_FALTANTES_API = {
    "220559": [  # Julia Zanatta - Projetos que a API não retorna corretamente
        # === PROJETOS APENSADOS (24 total) ===
        {"id": "2570510", "siglaTipo": "PL", "numero": "5072", "ano": "2025"},   # PL 5072/2025
        {"id": "2571359", "siglaTipo": "PL", "numero": "5128", "ano": "2025"},   # PL 5128/2025
        {"id": "2483453", "siglaTipo": "PLP", "numero": "19", "ano": "2025"},    # PLP 19/2025
        {"id": "2455568", "siglaTipo": "PL", "numero": "3341", "ano": "2024"},   # PL 3341/2024
        {"id": "2436763", "siglaTipo": "PL", "numero": "2098", "ano": "2024"},   # PL 2098/2024
        {"id": "2455562", "siglaTipo": "PL", "numero": "3338", "ano": "2024"},   # PL 3338/2024
        {"id": "2482260", "siglaTipo": "PDL", "numero": "24", "ano": "2025"},    # PDL 24/2025
        {"id": "2482169", "siglaTipo": "PDL", "numero": "16", "ano": "2025"},    # PDL 16/2025
        {"id": "2567301", "siglaTipo": "PL", "numero": "4954", "ano": "2025"},   # PL 4954/2025
        {"id": "2531615", "siglaTipo": "PL", "numero": "3222", "ano": "2025"},   # PL 3222/2025
        {"id": "2372482", "siglaTipo": "PLP", "numero": "141", "ano": "2023"},   # PLP 141/2023
        {"id": "2399426", "siglaTipo": "PL", "numero": "5198", "ano": "2023"},   # PL 5198/2023
        {"id": "2423254", "siglaTipo": "PL", "numero": "955", "ano": "2024"},    # PL 955/2024
        {"id": "2374405", "siglaTipo": "PDL", "numero": "194", "ano": "2023"},   # PDL 194/2023
        {"id": "2374340", "siglaTipo": "PDL", "numero": "189", "ano": "2023"},   # PDL 189/2023
        {"id": "2485135", "siglaTipo": "PL", "numero": "623", "ano": "2025"},    # PL 623/2025
        {"id": "2419264", "siglaTipo": "PDL", "numero": "30", "ano": "2024"},    # PDL 30/2024
        {"id": "2375447", "siglaTipo": "PDL", "numero": "209", "ano": "2023"},   # PDL 209/2023
        {"id": "2456691", "siglaTipo": "PDL", "numero": "348", "ano": "2024"},   # PDL 348/2024
        {"id": "2462038", "siglaTipo": "PL", "numero": "3887", "ano": "2024"},   # PL 3887/2024
        {"id": "2448732", "siglaTipo": "PEC", "numero": "28", "ano": "2024"},    # PEC 28/2024
        {"id": "2390075", "siglaTipo": "PDL", "numero": "337", "ano": "2023"},   # PDL 337/2023
        {"id": "2361454", "siglaTipo": "PL", "numero": "2472", "ano": "2023"},   # PL 2472/2023
        {"id": "2365600", "siglaTipo": "PL", "numero": "2815", "ano": "2023"},   # PL 2815/2023
        # === OUTROS PROJETOS FALTANTES ===
        {"id": "2347150", "siglaTipo": "PL", "numero": "321", "ano": "2023"},    # PL 321/2023 (no Senado)
        {"id": "2381193", "siglaTipo": "PL", "numero": "4045", "ano": "2023"},   # PL 4045/2023
    ]
}


# ============================================================
# PROJETOS APENSADOS - v35.1 (MAPEAMENTO COMPLETO)
# ============================================================
# Mapeamento DIRETO para o PL RAIZ (onde tramita de verdade)
# Inclui: PL principal imediato, PL raiz, e cadeia completa
# ============================================================

# Mapeamento principal: ID da proposição Zanatta → dados completos
# Formato: {id: {"principal": "PL X", "raiz": "PL Y", "cadeia": ["PL A", "PL B", ...]}}
MAPEAMENTO_APENSADOS_COMPLETO = {
    # === PLs ===
    "2361454": {  # PL 2472/2023 - TEA/Acompanhante escolas
        "principal": "PL 1620/2023",
        "raiz": "PL 1620/2023",
        "cadeia": ["PL 1620/2023"],
    },
    "2361794": {  # PL 2501/2023 - Crime de censura
        "principal": "PL 2782/2022",
        "raiz": "PL 2782/2022",
        "cadeia": ["PL 2782/2022"],
    },
    "2365600": {  # PL 2815/2023 - Bagagem de mão
        "principal": "PL 9417/2017",
        "raiz": "PL 9417/2017",
        "cadeia": ["PL 9417/2017"],
    },
    "2381193": {  # PL 4045/2023 - OAB/STF
        "principal": "PL 3593/2020",
        "raiz": "PL 3593/2020",
        "cadeia": ["PL 3593/2020"],
    },
    "2396351": {  # PL 5021/2023 - Organizações terroristas
        "principal": "PL 5065/2016",
        "raiz": "PL 5065/2016",
        "cadeia": ["PL 5065/2016"],
    },
    "2399426": {  # PL 5198/2023 - ONGs estrangeiras (CADEIA CORRIGIDA!)
        "principal": "PL 736/2022",
        "raiz": "PL 4953/2016",  # ← RAIZ REAL (não é o 736/2022!)
        "cadeia": ["PL 736/2022", "PL 4953/2016"],
    },
    "2423254": {  # PL 955/2024 - Vacinação
        "principal": "PL 776/2024",
        "raiz": "PL 776/2024",
        "cadeia": ["PL 776/2024"],
    },
    "2436763": {  # PL 2098/2024 - Produtos alimentícios (CADEIA LONGA!)
        "principal": "PL 5499/2020",
        "raiz": "PL 10556/2018",  # ← RAIZ REAL
        "cadeia": ["PL 5499/2020", "PL 5344/2020", "PL 10556/2018"],
    },
    "2455562": {  # PL 3338/2024 - Direito dos pais
        "principal": "PL 2829/2023",
        "raiz": "PL 2829/2023",
        "cadeia": ["PL 2829/2023"],
    },
    "2455568": {  # PL 3341/2024 - Moeda digital/DREX
        "principal": "PL 4068/2020",
        "raiz": "PL 4068/2020",
        "cadeia": ["PL 4068/2020"],
    },
    "2462038": {  # PL 3887/2024 - CLT/Contribuição sindical
        "principal": "PL 1036/2019",
        "raiz": "PL 1036/2019",
        "cadeia": ["PL 1036/2019"],
    },
    "2485135": {  # PL 623/2025 - CPC
        "principal": "PL 606/2022",
        "raiz": "PL 606/2022",
        "cadeia": ["PL 606/2022"],
    },
    "2531615": {  # PL 3222/2025 - Prisão preventiva
        "principal": "PL 2617/2025",
        "raiz": "PL 2617/2025",
        "cadeia": ["PL 2617/2025"],
    },
    "2567301": {  # PL 4954/2025 - Maria da Penha masculina
        "principal": "PL 1500/2025",
        "raiz": "PL 1500/2025",
        "cadeia": ["PL 1500/2025"],
    },
    "2570510": {  # PL 5072/2025 - Paternidade socioafetiva
        "principal": "PL 503/2025",
        "raiz": "PL 503/2025",
        "cadeia": ["PL 503/2025"],
    },
    "2571359": {  # PL 5128/2025 - Maria da Penha/Falsas denúncias
        "principal": "PL 6198/2023",
        "raiz": "PL 6198/2023",
        "cadeia": ["PL 6198/2023"],
    },
    # === PLPs ===
    "2372482": {  # PLP 141/2023 - Inelegibilidade
        "principal": "PLP 316/2016",
        "raiz": "PLP 316/2016",
        "cadeia": ["PLP 316/2016"],
    },
    "2390310": {  # PLP (coautoria)
        "principal": "PLP 156/2012",
        "raiz": "PLP 156/2012",
        "cadeia": ["PLP 156/2012"],
    },
    "2439451": {  # PL (coautoria)
        "principal": "PL 4019/2021",
        "raiz": "PL 4019/2021",
        "cadeia": ["PL 4019/2021"],
    },
    "2483453": {  # PLP 19/2025 - Sigilo financeiro
        "principal": "PLP 235/2024",
        "raiz": "PLP 235/2024",
        "cadeia": ["PLP 235/2024"],
    },
    # === PDLs ===
    "2482260": {  # PDL 24/2025 - Susta Decreto 12.341 (PIX)
        "principal": "PDL 3/2025",
        "raiz": "PDL 3/2025",
        "cadeia": ["PDL 3/2025"],
    },
    "2482169": {  # PDL 16/2025 - Susta Decreto 12.341 (PIX)
        "principal": "PDL 3/2025",
        "raiz": "PDL 3/2025",
        "cadeia": ["PDL 3/2025"],
    },
    "2374405": {  # PDL 194/2023 - Susta Decreto armas
        "principal": "PDL 174/2023",
        "raiz": "PDL 174/2023",
        "cadeia": ["PDL 174/2023"],
    },
    "2374340": {  # PDL 189/2023 - Susta Decreto armas
        "principal": "PDL 174/2023",
        "raiz": "PDL 174/2023",
        "cadeia": ["PDL 174/2023"],
    },
    "2419264": {  # PDL 30/2024 - Susta Resolução TSE
        "principal": "PDL 3/2024",
        "raiz": "PDL 3/2024",
        "cadeia": ["PDL 3/2024"],
    },
    "2375447": {  # PDL 209/2023 - Susta Resolução ANS
        "principal": "PDL 183/2023",
        "raiz": "PDL 183/2023",
        "cadeia": ["PDL 183/2023"],
    },
    "2456691": {  # PDL 348/2024 - Susta IN banheiros
        "principal": "PDL 285/2024",
        "raiz": "PDL 285/2024",
        "cadeia": ["PDL 285/2024"],
    },
    "2390075": {  # PDL 337/2023 - Susta Resolução CONAMA
        "principal": "PDL 302/2023",
        "raiz": "PDL 302/2023",
        "cadeia": ["PDL 302/2023"],
    },
    # === PECs ===
    "2448732": {  # PEC 28/2024 - Mandado de segurança coletivo
        "principal": "PEC 8/2021",
        "raiz": "PEC 8/2021",
        "cadeia": ["PEC 8/2021"],
    },
}

# Mapeamento simples (compatibilidade): ID → PL principal imediato
MAPEAMENTO_APENSADOS = {k: v["principal"] for k, v in MAPEAMENTO_APENSADOS_COMPLETO.items()}


# ============================================================
# __all__ - EXPORTS PÚBLICOS
# ============================================================

__all__ = [
    # API
    'BASE_URL',
    'HEADERS',
    # Identidade
    'DEPUTADA_NOME_PADRAO',
    'DEPUTADA_PARTIDO_PADRAO',
    'DEPUTADA_UF_PADRAO',
    'DEPUTADA_ID_PADRAO',
    # Listas padrão
    'PALAVRAS_CHAVE_PADRAO',
    'COMISSOES_ESTRATEGICAS_PADRAO',
    'TIPOS_CARTEIRA_PADRAO',
    # Status e meses
    'STATUS_PREDEFINIDOS',
    'MESES_PT',
    # RIC
    'RIC_RESPOSTA_KEYWORDS',
    # Temas
    'TEMAS_CATEGORIAS',
    # Workarounds API
    'PROPOSICOES_FALTANTES_API',
    # Apensados
    'MAPEAMENTO_APENSADOS_COMPLETO',
    'MAPEAMENTO_APENSADOS',
]
