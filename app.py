"""
Collections Knowledge Base ("Enciclopedia de Resoluciones")
=============================================================
App de autoservicio para que cualquier colaborador de Collections
resuelva dudas operativas del día a día sin depender de un
compañero o supervisor.

IMPORTANTE:
- Esta app NO es una herramienta de auditoría de usuarios.
- No maneja datos de clientes ni información personal.
- El contenido (cómo se resuelven disputas, procesos internos) se
  considera información interna sensible: el repo de GitHub y la
  app en Streamlit Community Cloud deben mantenerse PRIVADOS.
  Ver instrucciones de despliegue al final de este archivo.

Ejecutar localmente con:
    streamlit run app.py
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

# ============================================================
# 1. CONFIGURACIÓN GENERAL / GENERAL CONFIG
# ============================================================

CSV_PATH = "knowledge_base.csv"

# Columnas obligatorias que debe tener knowledge_base.csv
REQUIRED_COLUMNS = [
    "Categoria",
    "Subcategoria",
    "Problema_ES",
    "Solucion_ES",
    "Problema_EN",
    "Solucion_EN",
]

st.set_page_config(
    page_title="Collections Knowledge Base",
    page_icon="📚",
    layout="wide",
)

# Valores que consideramos "subcategoría vacía" y por lo tanto se
# deben ocultar del menú en cascada.
EMPTY_SUBCATEGORY_MARKERS = {"", "n/a", "na", "none", "null", "nan", "-"}


# ============================================================
# 2. TEXTOS / i18n (Español / English)
# ============================================================
# Todo el texto visible de la interfaz vive aquí para que sea fácil
# de mantener y para que el selector de idioma cambie todo de forma
# consistente.

TEXTS = {
    "ES": {
        "app_title": "📚 Enciclopedia de Resoluciones — Collections",
        "app_subtitle": (
            "Herramienta de autoservicio para resolver dudas operativas "
            "sin necesidad de preguntar a un compañero o supervisor."
        ),
        "lang_selector_label": "Idioma / Language",
        "search_header": "🔎 Buscar por palabra clave",
        "search_placeholder": "Ej: cargo duplicado, bloqueo de cuenta, plan de pagos...",
        "search_help": (
            "Escribe cualquier palabra relacionada con tu duda. Buscamos en "
            "categoría, subcategoría, problema y solución al mismo tiempo."
        ),
        "search_results_count": "Se encontraron {n} resultado(s) para '{query}'.",
        "search_no_results": (
            "No se encontraron resultados para '{query}'. Intenta con otra "
            "palabra clave o usa la navegación por categorías más abajo."
        ),
        "browse_header": "🗂️ O explora por categoría",
        "browse_help": (
            "¿No sabes qué buscar? Navega paso a paso: primero elige una "
            "categoría y, si aplica, una subcategoría."
        ),
        "category_label": "Categoría",
        "subcategory_label": "Subcategoría",
        "subcategory_general": "General (sin subcategoría)",
        "case_select_label": "Selecciona el caso específico",
        "problem_label": "🧩 Problema",
        "solution_label": "✅ Solución / Pasos a seguir",
        "no_cases_in_selection": "No hay casos disponibles para esta selección.",
        "download_section_header": "📊 Registrar esta consulta (opcional)",
        "download_help": (
            "Este botón es **opcional** y solo se usa durante la fase de "
            "prueba (beta testing) para confirmar que la herramienta se está "
            "usando, antes del lanzamiento oficial. **No es una auditoría "
            "continua ni un requisito para usar la app.**"
        ),
        "download_button_label": "⬇️ Descargar registro de esta consulta (.txt)",
        "missing_file_warning": (
            "⚠️ No se encontró el archivo **{path}** en el repositorio."
        ),
        "missing_file_instructions": (
            "Para que la app funcione, agrega un archivo `knowledge_base.csv` "
            "en la raíz del repositorio con las siguientes columnas:\n\n"
            "`Categoria, Subcategoria, Problema_ES, Solucion_ES, Problema_EN, "
            "Solucion_EN`\n\n"
            "Puedes generar este archivo con el script `prepare_kb.py` a "
            "partir de un export de Microsoft Forms."
        ),
        "load_dummy_button": "🧪 Cargar datos de prueba temporales",
        "dummy_data_notice": (
            "ℹ️ Estás viendo **datos de prueba (dummy)**, no el contenido "
            "real de Collections. Sustituye `knowledge_base.csv` en el repo "
            "para ver el contenido definitivo."
        ),
        "empty_kb_warning": (
            "El archivo de conocimiento está vacío o no tiene las columnas "
            "esperadas."
        ),
        "footer_note": (
            "¿Falta un caso o encontraste un error? Repórtalo a tu "
            "supervisor para actualizar la base de conocimiento."
        ),
    },
    "EN": {
        "app_title": "📚 Resolutions Encyclopedia — Collections",
        "app_subtitle": (
            "Self-service tool to resolve day-to-day operational questions "
            "without needing to ask a teammate or supervisor."
        ),
        "lang_selector_label": "Idioma / Language",
        "search_header": "🔎 Search by keyword",
        "search_placeholder": "E.g.: duplicate charge, account block, payment plan...",
        "search_help": (
            "Type any word related to your question. We search category, "
            "subcategory, problem and solution at the same time."
        ),
        "search_results_count": "Found {n} result(s) for '{query}'.",
        "search_no_results": (
            "No results found for '{query}'. Try another keyword or use the "
            "category browser below."
        ),
        "browse_header": "🗂️ Or browse by category",
        "browse_help": (
            "Not sure what to search for? Navigate step by step: pick a "
            "category and, if applicable, a subcategory."
        ),
        "category_label": "Category",
        "subcategory_label": "Subcategory",
        "subcategory_general": "General (no subcategory)",
        "case_select_label": "Select the specific case",
        "problem_label": "🧩 Problem",
        "solution_label": "✅ Solution / Steps to follow",
        "no_cases_in_selection": "No cases available for this selection.",
        "download_section_header": "📊 Log this lookup (optional)",
        "download_help": (
            "This button is **optional** and is only used during the beta "
            "testing phase to confirm the tool is being used, ahead of the "
            "official rollout. **It is not a continuous audit or a "
            "requirement to use the app.**"
        ),
        "download_button_label": "⬇️ Download log for this lookup (.txt)",
        "missing_file_warning": (
            "⚠️ File **{path}** was not found in the repository."
        ),
        "missing_file_instructions": (
            "For the app to work, add a `knowledge_base.csv` file at the "
            "repository root with the following columns:\n\n"
            "`Categoria, Subcategoria, Problema_ES, Solucion_ES, Problema_EN, "
            "Solucion_EN`\n\n"
            "You can generate this file with the `prepare_kb.py` script from "
            "a Microsoft Forms export."
        ),
        "load_dummy_button": "🧪 Load temporary test data",
        "dummy_data_notice": (
            "ℹ️ You are viewing **dummy test data**, not the real Collections "
            "content. Replace `knowledge_base.csv` in the repo to see the "
            "final content."
        ),
        "empty_kb_warning": (
            "The knowledge base file is empty or missing the expected "
            "columns."
        ),
        "footer_note": (
            "Missing a case or found an error? Report it to your supervisor "
            "to update the knowledge base."
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Atajo para obtener un texto traducido y formatearlo si aplica."""
    text = TEXTS[lang][key]
    return text.format(**kwargs) if kwargs else text


# ============================================================
# 3. CARGA DE DATOS / DATA LOADING
# ============================================================

@st.cache_data(show_spinner=False)
def load_kb_csv(path: str) -> pd.DataFrame:
    """
    Carga y cachea knowledge_base.csv.
    Lanza FileNotFoundError si el archivo no existe (se maneja arriba,
    en la capa de UI, para no romper la app).
    """
    df = pd.read_csv(path, dtype=str)
    df = df.fillna("")
    # Normaliza espacios en blanco sobrantes en todas las columnas texto.
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def get_dummy_data() -> pd.DataFrame:
    """Datos dummy (2-3 filas) usados como fallback si no existe el CSV."""
    data = [
        {
            "Categoria": "Disputas",
            "Subcategoria": "Cargo Duplicado",
            "Problema_ES": "[DEMO] El cliente reporta un cobro duplicado.",
            "Solucion_ES": "[DEMO] 1. Verificar ambos cargos. 2. Abrir disputa. 3. Reversar el cargo duplicado.",
            "Problema_EN": "[DEMO] The customer reports a duplicate charge.",
            "Solucion_EN": "[DEMO] 1. Verify both charges. 2. Open a dispute. 3. Reverse the duplicate charge.",
        },
        {
            "Categoria": "Pagos",
            "Subcategoria": "",
            "Problema_ES": "[DEMO] El cliente quiere un plan de pagos.",
            "Solucion_ES": "[DEMO] Revisar elegibilidad y ofrecer plazos de 3, 6 o 12 meses.",
            "Problema_EN": "[DEMO] The customer wants a payment plan.",
            "Solucion_EN": "[DEMO] Check eligibility and offer 3, 6 or 12-month terms.",
        },
        {
            "Categoria": "Cuenta",
            "Subcategoria": "Bloqueo de Cuenta",
            "Problema_ES": "[DEMO] El cliente no puede acceder a su cuenta.",
            "Solucion_ES": "[DEMO] Verificar el motivo del bloqueo en el log de seguridad y guiar al cliente según el caso.",
            "Problema_EN": "[DEMO] The customer cannot access their account.",
            "Solucion_EN": "[DEMO] Check the block reason in the security log and guide the customer accordingly.",
        },
    ]
    return pd.DataFrame(data)


def validate_columns(df: pd.DataFrame) -> bool:
    return all(col in df.columns for col in REQUIRED_COLUMNS) and len(df) > 0


def is_empty_subcategory(value: str) -> bool:
    return str(value).strip().lower() in EMPTY_SUBCATEGORY_MARKERS


# ============================================================
# 4. UTILIDADES DE NEGOCIO / BUSINESS HELPERS
# ============================================================

def search_kb(df: pd.DataFrame, query: str, lang: str) -> pd.DataFrame:
    """
    Filtra el DataFrame buscando `query` (case-insensitive) en
    Categoria, Subcategoria y en las columnas de Problema/Solucion
    del idioma seleccionado.
    """
    if not query.strip():
        return df.iloc[0:0]  # DataFrame vacío

    problem_col = f"Problema_{lang}"
    solution_col = f"Solucion_{lang}"
    search_cols = ["Categoria", "Subcategoria", problem_col, solution_col]

    query_lower = query.strip().lower()
    mask = pd.Series(False, index=df.index)
    for col in search_cols:
        mask = mask | df[col].str.lower().str.contains(query_lower, na=False, regex=False)
    return df[mask]


def build_log_txt(categoria: str, subcategoria: str, lang: str) -> bytes:
    """Genera el contenido del .txt de registro de consulta (opcional)."""
    now = datetime.now()
    subcategoria_display = subcategoria if subcategoria else "N/A"
    content = (
        "Registro de consulta - Collections Knowledge Base\n"
        "(Uso opcional durante fase de beta testing - NO es auditoría continua)\n"
        "-----------------------------------------------------------------\n"
        f"Fecha: {now.strftime('%Y-%m-%d')}\n"
        f"Hora: {now.strftime('%H:%M:%S')}\n"
        f"Categoria: {categoria}\n"
        f"Subcategoria: {subcategoria_display}\n"
        f"Idioma: {lang}\n"
    )
    return content.encode("utf-8")


def render_case(row: pd.Series, lang: str, texts: dict, log_key_suffix: str) -> None:
    """Muestra un caso (problema/solución) y su botón de registro opcional."""
    problem_col = f"Problema_{lang}"
    solution_col = f"Solucion_{lang}"

    st.markdown(f"**{texts['problem_label']}**")
    st.info(row[problem_col])

    st.markdown(f"**{texts['solution_label']}**")
    # Si la solución tiene varios pasos (saltos de línea), se muestra
    # como markdown para conservar el formato de lista/numeración.
    solucion = row[solution_col]
    if "\n" in solucion:
        with st.container(border=True):
            st.success("")  # separador visual con el color de "éxito"
            st.markdown(solucion.replace("\n", "\n\n"))
    else:
        st.success(solucion)

    with st.expander(texts["download_section_header"]):
        st.caption(texts["download_help"])
        log_bytes = build_log_txt(row["Categoria"], row["Subcategoria"], lang)
        st.download_button(
            label=texts["download_button_label"],
            data=log_bytes,
            file_name=f"consulta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key=f"download_{log_key_suffix}",
        )


# ============================================================
# 5. SIDEBAR: SELECTOR DE IDIOMA
# ============================================================

if "lang" not in st.session_state:
    st.session_state.lang = "ES"

lang_choice = st.sidebar.radio(
    "Idioma / Language",
    options=["ES", "EN"],
    format_func=lambda x: "Español" if x == "ES" else "English",
    index=0 if st.session_state.lang == "ES" else 1,
)
st.session_state.lang = lang_choice
lang = st.session_state.lang
texts = TEXTS[lang]

# ============================================================
# 6. ENCABEZADO
# ============================================================

st.title(texts["app_title"])
st.caption(texts["app_subtitle"])
st.divider()

# ============================================================
# 7. CARGA DEL CSV CON MANEJO DE ERRORES
# ============================================================

if "use_dummy" not in st.session_state:
    st.session_state.use_dummy = False

df = None

if st.session_state.use_dummy:
    df = get_dummy_data()
    st.info(texts["dummy_data_notice"])
else:
    try:
        df = load_kb_csv(CSV_PATH)
        if not validate_columns(df):
            st.warning(texts["empty_kb_warning"])
            df = None
    except FileNotFoundError:
        st.warning(t(lang, "missing_file_warning", path=CSV_PATH))
        st.markdown(texts["missing_file_instructions"])
        if st.button(texts["load_dummy_button"]):
            st.session_state.use_dummy = True
            st.rerun()
        df = None
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier error de parseo
        st.warning(t(lang, "missing_file_warning", path=CSV_PATH))
        st.caption(f"({exc})")
        st.markdown(texts["missing_file_instructions"])
        if st.button(texts["load_dummy_button"]):
            st.session_state.use_dummy = True
            st.rerun()
        df = None

# Si no hay datos disponibles (ni archivo real ni dummy activado), detener aquí.
if df is None:
    st.stop()

# ============================================================
# 8. BÚSQUEDA POR PALABRA CLAVE (MECANISMO PRINCIPAL)
# ============================================================

st.subheader(texts["search_header"])
st.caption(texts["search_help"])

query = st.text_input(
    label=texts["search_header"],
    placeholder=texts["search_placeholder"],
    label_visibility="collapsed",
)

search_results = pd.DataFrame()
if query.strip():
    search_results = search_kb(df, query, lang)

    if len(search_results) == 0:
        st.warning(t(lang, "search_no_results", query=query))
    else:
        st.success(t(lang, "search_results_count", n=len(search_results), query=query))
        for idx, (_, row) in enumerate(search_results.iterrows()):
            subtitle = row["Categoria"]
            if not is_empty_subcategory(row["Subcategoria"]):
                subtitle += f" › {row['Subcategoria']}"
            with st.expander(f"{subtitle} — {row[f'Problema_{lang}'][:90]}", expanded=(len(search_results) == 1)):
                render_case(row, lang, texts, log_key_suffix=f"search_{idx}")

st.divider()

# ============================================================
# 9. NAVEGACIÓN EN CASCADA (ALTERNATIVA A LA BÚSQUEDA)
# ============================================================

st.subheader(texts["browse_header"])
st.caption(texts["browse_help"])

col1, col2 = st.columns(2)

with col1:
    categorias = sorted(df["Categoria"].unique())
    selected_cat = st.selectbox(texts["category_label"], options=categorias, key="cat_select")

subset_cat = df[df["Categoria"] == selected_cat]

# Regla: si TODAS las subcategorías de esta categoría están vacías/N/A,
# ocultamos el menú de subcategoría y vamos directo al selector de caso.
subcats_no_vacias = sorted(
    {s for s in subset_cat["Subcategoria"] if not is_empty_subcategory(s)}
)
hay_filas_generales = any(is_empty_subcategory(s) for s in subset_cat["Subcategoria"])

subset_final = subset_cat
if subcats_no_vacias:
    options = subcats_no_vacias.copy()
    if hay_filas_generales:
        options.append(texts["subcategory_general"])
    with col2:
        selected_subcat = st.selectbox(texts["subcategory_label"], options=options, key="subcat_select")
    if selected_subcat == texts["subcategory_general"]:
        subset_final = subset_cat[subset_cat["Subcategoria"].apply(is_empty_subcategory)]
    else:
        subset_final = subset_cat[subset_cat["Subcategoria"] == selected_subcat]
# else: no se muestra el menú de subcategoría; subset_final ya es subset_cat.

if len(subset_final) == 0:
    st.info(texts["no_cases_in_selection"])
elif len(subset_final) == 1:
    row = subset_final.iloc[0]
    render_case(row, lang, texts, log_key_suffix="browse_single")
else:
    # Varios casos dentro de la misma categoría/subcategoría: se deja
    # elegir el caso puntual por el texto del problema.
    problem_col = f"Problema_{lang}"
    options = subset_final[problem_col].tolist()
    selected_problem = st.selectbox(texts["case_select_label"], options=options, key="case_select")
    row = subset_final[subset_final[problem_col] == selected_problem].iloc[0]
    render_case(row, lang, texts, log_key_suffix="browse_multi")

# ============================================================
# 10. PIE DE PÁGINA
# ============================================================

st.divider()
st.caption(texts["footer_note"])
