"""
prepare_kb.py
=============
Utilidad de línea de comandos para transformar un export de Microsoft
Forms (Excel o CSV) al formato requerido por `knowledge_base.csv` de la
app "Collections Knowledge Base".

Objetivo: facilitar la actualización mensual del contenido sin que
alguien tenga que editar el CSV a mano fila por fila.

Qué hace:
    1. Lee el export de Microsoft Forms (.xlsx o .csv).
    2. Renombra las columnas del export a los nombres esperados por la
       app, usando el mapeo configurable COLUMN_MAPPING (ver abajo).
    3. Valida que existan todas las columnas requeridas.
    4. Separa las filas en:
         - "listas": tienen todos los campos obligatorios completos.
         - "por revisar": les falta algún campo obligatorio (ej. no
           tienen traducción a inglés). Estas filas NO se descartan
           silenciosamente ni rompen el script: se guardan en un
           archivo aparte para que alguien las complete a mano.
    5. Si ya existe un `knowledge_base.csv` previo y se usa --merge,
       agrega las filas nuevas y listas al archivo existente (evitando
       duplicados exactos) en vez de sobrescribirlo.

Uso típico (actualización mensual):
    python prepare_kb.py --input export_forms_septiembre.xlsx --merge

Esto genera/actualiza:
    - knowledge_base.csv                (filas completas, listas para la app)
    - knowledge_base_por_revisar.csv    (filas incompletas, para revisión manual)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# ============================================================
# 1. CONFIGURACIÓN: MAPEO DE COLUMNAS
# ============================================================
# Microsoft Forms exporta cada pregunta como una columna, con el texto
# literal de la pregunta como encabezado. Ajusta este diccionario para
# que coincida EXACTAMENTE con los encabezados de tu export
# (clave = encabezado en el export, valor = columna destino).
#
# Si cambias el formulario de Forms, solo necesitas actualizar este
# diccionario, no el resto del script.

COLUMN_MAPPING = {
    "Categoría del caso": "Categoria",
    "Subcategoría (opcional)": "Subcategoria",
    "Descripción del problema (Español)": "Problema_ES",
    "Solución / pasos a seguir (Español)": "Solucion_ES",
    "Descripción del problema (English)": "Problema_EN",
    "Solución / pasos a seguir (English)": "Solucion_EN",
}

# Columnas que debe tener el archivo final knowledge_base.csv.
TARGET_COLUMNS = [
    "Categoria",
    "Subcategoria",
    "Problema_ES",
    "Solucion_ES",
    "Problema_EN",
    "Solucion_EN",
]

# Columnas obligatorias para considerar una fila "completa". Subcategoria
# queda fuera a propósito: puede estar vacía legítimamente.
REQUIRED_NON_EMPTY = [
    "Categoria",
    "Problema_ES",
    "Solucion_ES",
    "Problema_EN",
    "Solucion_EN",
]


# ============================================================
# 2. LECTURA DEL EXPORT
# ============================================================

def read_forms_export(path: Path) -> pd.DataFrame:
    """Lee el export de Microsoft Forms (.xlsx o .csv) como texto plano."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {path}")

    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(
            f"Formato no soportado '{suffix}'. Usa un export .xlsx o .csv de Microsoft Forms."
        )

    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


# ============================================================
# 3. MAPEO Y VALIDACIÓN DE COLUMNAS
# ============================================================

def apply_column_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra las columnas del export según COLUMN_MAPPING."""
    missing_source_cols = [c for c in COLUMN_MAPPING if c not in df.columns]
    if missing_source_cols:
        print(
            "⚠️  Aviso: las siguientes columnas esperadas del export de "
            "Microsoft Forms no se encontraron y se ignorarán:\n  - "
            + "\n  - ".join(missing_source_cols),
            file=sys.stderr,
        )

    rename_map = {k: v for k, v in COLUMN_MAPPING.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Nos quedamos solo con las columnas destino que sí pudimos mapear.
    available_targets = [c for c in TARGET_COLUMNS if c in df.columns]
    df = df[available_targets].copy()

    # Aseguramos que TODAS las columnas destino existan, aunque queden vacías,
    # para que el CSV final siempre tenga el esquema completo.
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[TARGET_COLUMNS]


def validate_required_columns(df: pd.DataFrame) -> None:
    """
    Falla con un mensaje claro (no silenciosamente) si, después del
    mapeo, faltan columnas destino críticas que no se pudieron generar
    en absoluto (es decir, ninguna fila del export las trae).
    """
    completely_missing = [
        col for col in REQUIRED_NON_EMPTY
        if col not in df.columns or (df[col] == "").all()
    ]
    if completely_missing:
        raise ValueError(
            "No se pudo generar el archivo: las siguientes columnas "
            f"obligatorias vinieron completamente vacías o no se mapearon: "
            f"{completely_missing}.\n"
            "Revisa el diccionario COLUMN_MAPPING al inicio de prepare_kb.py "
            "y confirma que los encabezados coincidan con tu export de "
            "Microsoft Forms."
        )


# ============================================================
# 4. DETECCIÓN DE FILAS INCOMPLETAS (PARA REVISIÓN MANUAL)
# ============================================================

def flag_incomplete_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega la columna 'Motivo_Revision' indicando qué campos
    obligatorios faltan en cada fila. Fila con Motivo_Revision == ""
    se considera completa.
    """
    def motivo(row) -> str:
        faltantes = [col for col in REQUIRED_NON_EMPTY if row[col].strip() == ""]
        if not faltantes:
            return ""
        return "Faltan campos: " + ", ".join(faltantes)

    df = df.copy()
    df["Motivo_Revision"] = df.apply(motivo, axis=1)
    return df


# ============================================================
# 5. MERGE CON knowledge_base.csv EXISTENTE (OPCIONAL)
# ============================================================

def merge_with_existing(new_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """Combina las filas nuevas con el CSV existente, evitando duplicados exactos."""
    if not output_path.exists():
        return new_df

    existing_df = pd.read_csv(output_path, dtype=str).fillna("")
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(
        subset=["Categoria", "Subcategoria", "Problema_ES", "Problema_EN"],
        keep="last",
    )
    removed = before - len(combined)
    if removed:
        print(f"ℹ️  Se eliminaron {removed} fila(s) duplicada(s) al combinar con el archivo existente.")
    return combined


# ============================================================
# 6. PROGRAMA PRINCIPAL
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte un export de Microsoft Forms al formato knowledge_base.csv"
    )
    parser.add_argument("--input", required=True, help="Ruta al export de Microsoft Forms (.xlsx o .csv)")
    parser.add_argument("--output", default="knowledge_base.csv", help="Ruta de salida para el CSV final (default: knowledge_base.csv)")
    parser.add_argument(
        "--review-output",
        default="knowledge_base_por_revisar.csv",
        help="Ruta de salida para las filas incompletas (default: knowledge_base_por_revisar.csv)",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Combina las filas nuevas y completas con el knowledge_base.csv existente en vez de sobrescribirlo.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    review_path = Path(args.review_output)

    print(f"📥 Leyendo export: {input_path}")
    raw_df = read_forms_export(input_path)
    print(f"   {len(raw_df)} fila(s) encontradas en el export.")

    mapped_df = apply_column_mapping(raw_df)
    validate_required_columns(mapped_df)

    flagged_df = flag_incomplete_rows(mapped_df)
    complete_df = flagged_df[flagged_df["Motivo_Revision"] == ""].drop(columns=["Motivo_Revision"])
    incomplete_df = flagged_df[flagged_df["Motivo_Revision"] != ""]

    print(f"✅ Filas completas y listas: {len(complete_df)}")
    print(f"⚠️  Filas que necesitan revisión manual: {len(incomplete_df)}")

    if args.merge:
        final_df = merge_with_existing(complete_df, output_path)
    else:
        final_df = complete_df

    final_df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"💾 Archivo generado: {output_path} ({len(final_df)} fila(s) en total)")

    if len(incomplete_df) > 0:
        incomplete_df.to_csv(review_path, index=False, encoding="utf-8")
        print(f"📝 Filas por revisar guardadas en: {review_path}")
        print(
            "   Completa manualmente los campos faltantes (por ejemplo, la "
            "traducción a inglés) y vuelve a incluirlas en el CSV final, "
            "o corre este script de nuevo una vez corregido el export."
        )
    else:
        print("🎉 No hay filas pendientes de revisión.")


if __name__ == "__main__":
    main()
