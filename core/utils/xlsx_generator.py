"""
Gerador de arquivos XLSX para o Monitor Parlamentar.
Funções de exportação de DataFrames para Excel.

REGRA: Este módulo NÃO pode importar streamlit.
"""
from io import BytesIO
from typing import Tuple
import pandas as pd



def to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> Tuple[bytes, str, str]:
    """
    Exporta DataFrame para XLSX.
    Sempre tenta exportar como XLSX, fallback para CSV apenas se necessário.
    
    Retorna: (bytes, mime_type, extension)
    """
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

    # Fallback para CSV
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return (csv_bytes, "text/csv", "csv")
