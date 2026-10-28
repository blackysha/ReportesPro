""""
Sistema de validación, indicadores y reportes PDF.
Lee archivos CSV, Excel (.xlsx/.xls) y tablas de bases de datos SQLite.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


REQUIRED_COLUMNS = ["nombre", "correo", "edad", "monto"]


# =========================================
# PERFILES DE ANÁLISIS EMPRESARIAL
# =========================================

ANALYSIS_PROFILES = {
    "general": {
        "nombre": "Análisis general",
        "columnas": ["nombre", "correo", "edad", "monto"],
    },
    "ventas": {
        "nombre": "Análisis de ventas",
        "columnas": ["fecha", "producto", "cantidad", "precio"],
    },
    "inventario": {
        "nombre": "Análisis de inventario",
        "columnas": ["producto", "stock", "costo"],
    },
    "clientes": {
        "nombre": "Análisis de clientes",
        "columnas": ["nombre", "correo", "fecha_registro"],
    },
}


def get_analysis_profiles():
    """Devuelve los perfiles disponibles."""
    return ANALYSIS_PROFILES


def validate_profile_columns(df, profile="general"):
    """
    Comprueba si el archivo contiene las columnas
    requeridas por el perfil seleccionado.
    """

    if profile not in ANALYSIS_PROFILES:
        raise ValueError(
            f"Perfil de análisis desconocido: {profile}"
        )

    normalized = normalize_columns(df)

    required = ANALYSIS_PROFILES[profile]["columnas"]

    missing = [
        column
        for column in required
        if column not in normalized.columns
    ]

    if missing:
        raise ValueError(
            "Faltan columnas para el análisis "
            f"'{profile}': {', '.join(missing)}"
        )

    return normalized


def load_data(source: str, table: str | None = None) -> pd.DataFrame:
    """Carga datos desde CSV, Excel o una tabla SQLite."""
    path = Path(source)

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {source}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suffix in (".db", ".sqlite", ".sqlite3"):
        if not table:
            raise ValueError(
                "Para una base de datos SQLite debes indicar la tabla con --table."
            )
        # El nombre de tabla no puede parametrizarse como un valor SQL.
        # Se valida que sea un identificador simple antes de usarlo.
        if not table.replace("_", "").isalnum():
            raise ValueError("Nombre de tabla no válido. Usa letras, números y guion bajo.")
        with sqlite3.connect(path) as connection:
            return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)

    raise ValueError("Formato no compatible. Usa CSV, XLSX, XLS o SQLite (.db).")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas para reducir problemas por espacios o mayúsculas."""
    result = df.copy()
    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]
    return result


def validate_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Valida campos básicos:
    - columnas requeridas presentes
    - nombre y correo no vacíos
    - correo con formato básico
    - edad numérica y no negativa
    - monto numérico y no negativo
    - filas duplicadas
    Devuelve (datos_limpios, incidencias).
    """
    df = normalize_columns(df)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas requeridas: "
            + ", ".join(missing)
            + ". Columnas esperadas: "
            + ", ".join(REQUIRED_COLUMNS)
        )

    work = df.copy()
    work.insert(0, "fila_origen", range(2, len(work) + 2))
    issues: list[dict] = []

    for idx, row in work.iterrows():
        row_number = int(row["fila_origen"])

        if pd.isna(row["nombre"]) or not str(row["nombre"]).strip():
            issues.append({"fila": row_number, "campo": "nombre", "problema": "Nombre vacío"})

        email = "" if pd.isna(row["correo"]) else str(row["correo"]).strip()
        if not email:
            issues.append({"fila": row_number, "campo": "correo", "problema": "Correo vacío"})
        elif "@" not in email or "." not in email.split("@")[-1]:
            issues.append({"fila": row_number, "campo": "correo", "problema": "Formato de correo no válido"})

    work["edad"] = pd.to_numeric(work["edad"], errors="coerce")
    work["monto"] = pd.to_numeric(work["monto"], errors="coerce")

    for idx, row in work.iterrows():
        row_number = int(row["fila_origen"])
        if pd.isna(row["edad"]):
            issues.append({"fila": row_number, "campo": "edad", "problema": "Edad no numérica o vacía"})
        elif row["edad"] < 0:
            issues.append({"fila": row_number, "campo": "edad", "problema": "Edad negativa"})
        if pd.isna(row["monto"]):
            issues.append({"fila": row_number, "campo": "monto", "problema": "Monto no numérico o vacío"})
        elif row["monto"] < 0:
            issues.append({"fila": row_number, "campo": "monto", "problema": "Monto negativo"})

    duplicate_mask = work.duplicated(subset=REQUIRED_COLUMNS, keep="first")
    for idx in work.index[duplicate_mask]:
        issues.append({
            "fila": int(work.loc[idx, "fila_origen"]),
            "campo": "registro",
            "problema": "Registro duplicado"
        })

    issues_df = pd.DataFrame(issues, columns=["fila", "campo", "problema"])

    # Se consideran válidas las filas que no tengan incidencias asociadas.
    bad_rows = set(issues_df["fila"].tolist()) if not issues_df.empty else set()
    clean = work[~work["fila_origen"].isin(bad_rows)].copy()
    return clean, issues_df


def calculate_indicators(original: pd.DataFrame, clean: pd.DataFrame,
                          issues: pd.DataFrame) -> dict:
    total = len(original)
    valid = len(clean)
    invalid = len(set(issues["fila"].tolist())) if not issues.empty else 0
    total_amount = float(clean["monto"].sum()) if valid else 0.0
    average_amount = float(clean["monto"].mean()) if valid else 0.0
    average_age = float(clean["edad"].mean()) if valid else 0.0

    return {
        "registros_totales": total,
        "registros_validos": valid,
        "registros_con_incidencias": invalid,
        "porcentaje_validos": (valid / total * 100) if total else 0.0,
        "monto_total_valido": total_amount,
        "monto_promedio": average_amount,
        "edad_promedio": average_age,
        "incidencias_detectadas": len(issues),
    }



# =========================================
# INDICADORES POR PERFIL EMPRESARIAL
# =========================================

def analyze_business_profile(df, profile="general"):
    """
    Analiza los datos según el perfil empresarial.

    Devuelve:
    - datos válidos
    - incidencias detectadas
    - indicadores calculados
    """

    if profile == "general":
        valid, issues = validate_data(df)

        indicators = calculate_indicators(
            df,
            valid,
            issues
        )

        return valid, issues, indicators

    work = validate_profile_columns(
        df,
        profile
    ).copy()

    work.insert(
        0,
        "fila_origen",
        range(2, len(work) + 2)
    )

    issues = []

    # =====================================
    # PERFIL DE VENTAS
    # =====================================

    if profile == "ventas":

        work["cantidad"] = pd.to_numeric(
            work["cantidad"],
            errors="coerce"
        )

        work["precio"] = pd.to_numeric(
            work["precio"],
            errors="coerce"
        )

        work["fecha"] = pd.to_datetime(
            work["fecha"],
            errors="coerce"
        )

        for _, row in work.iterrows():

            fila = int(row["fila_origen"])

            if pd.isna(row["fecha"]):
                issues.append({
                    "fila": fila,
                    "campo": "fecha",
                    "problema": "Fecha inválida"
                })

            if pd.isna(row["producto"]) or not str(
                row["producto"]
            ).strip():
                issues.append({
                    "fila": fila,
                    "campo": "producto",
                    "problema": "Producto vacío"
                })

            if pd.isna(row["cantidad"]) or row["cantidad"] <= 0:
                issues.append({
                    "fila": fila,
                    "campo": "cantidad",
                    "problema": "Cantidad inválida"
                })

            if pd.isna(row["precio"]) or row["precio"] < 0:
                issues.append({
                    "fila": fila,
                    "campo": "precio",
                    "problema": "Precio inválido"
                })

    # =====================================
    # PERFIL DE INVENTARIO
    # =====================================

    elif profile == "inventario":

        work["stock"] = pd.to_numeric(
            work["stock"],
            errors="coerce"
        )

        work["costo"] = pd.to_numeric(
            work["costo"],
            errors="coerce"
        )

        for _, row in work.iterrows():

            fila = int(row["fila_origen"])

            if pd.isna(row["producto"]) or not str(
                row["producto"]
            ).strip():
                issues.append({
                    "fila": fila,
                    "campo": "producto",
                    "problema": "Producto vacío"
                })

            if pd.isna(row["stock"]) or row["stock"] < 0:
                issues.append({
                    "fila": fila,
                    "campo": "stock",
                    "problema": "Stock inválido"
                })

            if pd.isna(row["costo"]) or row["costo"] < 0:
                issues.append({
                    "fila": fila,
                    "campo": "costo",
                    "problema": "Costo inválido"
                })

    # =====================================
    # PERFIL DE CLIENTES
    # =====================================

    elif profile == "clientes":

        work["fecha_registro"] = pd.to_datetime(
            work["fecha_registro"],
            errors="coerce"
        )

        for _, row in work.iterrows():

            fila = int(row["fila_origen"])

            if pd.isna(row["nombre"]) or not str(
                row["nombre"]
            ).strip():
                issues.append({
                    "fila": fila,
                    "campo": "nombre",
                    "problema": "Nombre vacío"
                })

            correo = (
                ""
                if pd.isna(row["correo"])
                else str(row["correo"]).strip()
            )

            if not correo or (
                "@" not in correo
                or "." not in correo.split("@")[-1]
            ):
                issues.append({
                    "fila": fila,
                    "campo": "correo",
                    "problema": "Correo inválido"
                })

            if pd.isna(row["fecha_registro"]):
                issues.append({
                    "fila": fila,
                    "campo": "fecha_registro",
                    "problema": "Fecha de registro inválida"
                })

    # =====================================
    # DETECTAR DUPLICADOS
    # =====================================

    columnas_duplicados = {
        "ventas": [
            "fecha", "producto", "cantidad", "precio"
        ],
        "inventario": [
            "producto"
        ],
        "clientes": [
            "correo"
        ]
    }

    duplicados = work.duplicated(
        subset=columnas_duplicados[profile],
        keep="first"
    )

    for _, row in work[duplicados].iterrows():

        issues.append({
            "fila": int(row["fila_origen"]),
            "campo": "registro",
            "problema": "Registro duplicado"
        })

    # =====================================
    # SEPARAR REGISTROS VÁLIDOS
    # =====================================

    issues_df = pd.DataFrame(
        issues,
        columns=["fila", "campo", "problema"]
    )

    filas_invalidas = set(
        issues_df["fila"].tolist()
    )

    valid = work[
        ~work["fila_origen"].isin(
            filas_invalidas
        )
    ].copy()

    # =====================================
    # INDICADORES GENERALES
    # =====================================

    total = len(work)
    total_validos = len(valid)

    indicators = {
        "registros_totales": total,
        "registros_validos": total_validos,
        "registros_con_incidencias": (
            total - total_validos
        ),
        "porcentaje_validos": (
            total_validos / total * 100
            if total
            else 0.0
        ),
        "incidencias_detectadas": len(
            issues_df
        )
    }

    # =====================================
    # INDICADORES DE VENTAS
    # =====================================

    if profile == "ventas":

        ingresos = (
            valid["cantidad"] * valid["precio"]
        ).sum()

        indicators.update({
            "ingresos_totales": float(ingresos),
            "unidades_vendidas": float(
                valid["cantidad"].sum()
            ),
            "ingreso_promedio": (
                float(ingresos / total_validos)
                if total_validos
                else 0.0
            )
        })

    # =====================================
    # INDICADORES DE INVENTARIO
    # =====================================

    elif profile == "inventario":

        valor = (
            valid["stock"] * valid["costo"]
        ).sum()

        indicadores_agotados = (
            valid["stock"] == 0
        ).sum()

        indicators.update({
            "unidades_disponibles": float(
                valid["stock"].sum()
            ),
            "valor_inventario": float(valor),
            "productos_agotados": int(
                indicadores_agotados
            )
        })

    # =====================================
    # INDICADORES DE CLIENTES
    # =====================================

    elif profile == "clientes":

        indicators.update({
            "clientes_validos": total_validos,
            "clientes_con_incidencias": (
                total - total_validos
            )
        })

    return valid, issues_df, indicators


def money(value: float) -> str:
    return f"{value:,.2f}"


def create_pdf(output: str, source: str, indicators: dict,
               issues: pd.DataFrame, clean: pd.DataFrame) -> None:
    """Genera un informe PDF con resumen, indicadores y detalle de incidencias."""
    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4),
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.4 * cm, bottomMargin=1.4 * cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#174A7E"), spaceAfter=12
    ))
    story = [
        Paragraph("Reporte de validación e indicadores", styles["ReportTitle"]),
        Paragraph(f"<b>Fuente:</b> {source}", styles["Normal"]),
        Paragraph(
            f"<b>Generado:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Normal"]
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("1. Resumen ejecutivo", styles["Heading2"]),
    ]

    summary_rows = [
        ["Indicador", "Resultado"],
        ["Registros analizados", str(indicators["registros_totales"])],
        ["Registros válidos", str(indicators["registros_validos"])],
        ["Registros con incidencias", str(indicators["registros_con_incidencias"])],
        ["Porcentaje válido", f'{indicators["porcentaje_validos"]:.2f}%'],
        ["Incidencias detectadas", str(indicators["incidencias_detectadas"])],
        ["Monto total válido", money(indicators["monto_total_valido"])],
        ["Monto promedio válido", money(indicators["monto_promedio"])],
        ["Edad promedio válida", f'{indicators["edad_promedio"]:.2f}'],
    ]
    summary = Table(summary_rows, colWidths=[8 * cm, 6 * cm], repeatRows=1)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174A7E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3DF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary, Spacer(1, 0.5 * cm), Paragraph("2. Incidencias detectadas", styles["Heading2"])])

    if issues.empty:
        story.append(Paragraph("No se detectaron incidencias.", styles["Normal"]))
    else:
        issue_rows = [["Fila de origen", "Campo", "Problema"]]
        for _, issue in issues.head(500).iterrows():
            issue_rows.append([
                str(issue["fila"]),
                str(issue["campo"]),
                str(issue["problema"])[:120],
            ])
        issue_table = Table(issue_rows, colWidths=[3 * cm, 4 * cm, 17 * cm], repeatRows=1)
        issue_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B2E2E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5D5D5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF4F4")]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(issue_table)
        if len(issues) > 500:
            story.append(Paragraph("Nota: se muestran las primeras 500 incidencias.", styles["Italic"]))

    story.extend([Spacer(1, 0.5 * cm), Paragraph("3. Muestra de registros válidos", styles["Heading2"])])
    display_columns = [col for col in ["nombre", "correo", "edad", "monto"] if col in clean.columns]
    sample_rows = [display_columns]
    for _, row in clean[display_columns].head(15).iterrows():
        sample_rows.append([
            str(row[col])[:45] if not pd.isna(row[col]) else ""
            for col in display_columns
        ])
    if len(sample_rows) == 1:
        sample_rows.append(["No hay registros válidos"] + [""] * (len(display_columns) - 1))
    sample_table = Table(sample_rows, repeatRows=1)
    sample_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#287A58")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5D5D5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F8F4")]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sample_table)

    doc.build(story)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida datos y genera indicadores y un reporte PDF."
    )
    parser.add_argument("source", help="Ruta del archivo CSV, Excel o base SQLite")
    parser.add_argument("--table", help="Nombre de la tabla SQLite (solo para .db/.sqlite)")
    parser.add_argument("--output", default="reporte.pdf", help="Ruta del PDF de salida")
    parser.add_argument("--clean-csv", default="datos_validos.csv",
                        help="Ruta del CSV con registros válidos")
    parser.add_argument("--issues-csv", default="incidencias.csv",
                        help="Ruta del CSV con incidencias")
    args = parser.parse_args()

    try:
        original = load_data(args.source, args.table)
        clean, issues = validate_data(original)
        indicators = calculate_indicators(original, clean, issues)
        create_pdf(args.output, args.source, indicators, issues, clean)

        clean.drop(columns=["fila_origen"], errors="ignore").to_csv(
            args.clean_csv, index=False, encoding="utf-8-sig"
        )
        issues.to_csv(args.issues_csv, index=False, encoding="utf-8-sig")

        print("\nProceso terminado correctamente.")
        print(f"PDF: {args.output}")
        print(f"Datos válidos: {args.clean_csv}")
        print(f"Incidencias: {args.issues_csv}")
        print(f"Registros analizados: {indicators['registros_totales']}")
        print(f"Registros válidos: {indicators['registros_validos']}")
        print(f"Registros con incidencias: {indicators['registros_con_incidencias']}")
        print(f"Porcentaje válido: {indicators['porcentaje_validos']:.2f}%")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
