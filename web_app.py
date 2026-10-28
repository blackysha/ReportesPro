
import os
import tempfile
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    LongTable,
    TableStyle
)

from main import (
    load_data,
    create_pdf,
    get_analysis_profiles,
    analyze_business_profile
)

from database.db import (
    crear_tablas,
    registrar_empresa,
    listar_empresas,
    guardar_reporte,
    listar_reportes,
    obtener_estadisticas_empresa
)


# =========================================
# CONFIGURACIÓN
# =========================================

st.set_page_config(
    page_title="ReportesPro",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }
    .hero {
        background: linear-gradient(110deg, #142b48, #225e9b);
        color: white;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }
    .hero h1 {
        color: white;
        margin: 0;
    }
    .hero p {
        color: #e0ebf8;
        margin-bottom: 0;
    }
    </style>
    <div class="hero">
        <h1>📊 ReportesPro</h1>
        <p>Análisis de datos y reportes empresariales</p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================
# FUNCIONES AUXILIARES
# =========================================

def generar_pdf_empresarial(
    ruta,
    empresa,
    archivo,
    perfil,
    indicadores,
    incidencias,
    validos
):
    """
    Genera un PDF para ventas, inventario o clientes.
    El perfil general conserva su PDF original.
    """

    documento = SimpleDocTemplate(
        ruta,
        pagesize=landscape(A4),
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    estilos = getSampleStyleSheet()
    elementos = []

    def parrafo(texto, estilo="Normal"):
        return Paragraph(
            escape(str(texto)),
            estilos[estilo]
        )

    elementos.append(
        parrafo("ReportesPro - Informe empresarial", "Title")
    )

    elementos.append(Spacer(1, 15))

    elementos.append(
        parrafo(f"Empresa: {empresa}")
    )
    elementos.append(
        parrafo(f"Archivo: {archivo}")
    )
    elementos.append(
        parrafo(f"Perfil: {perfil}")
    )
    elementos.append(
        parrafo(
            "Generado: "
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    elementos.append(Spacer(1, 18))
    elementos.append(
        parrafo("1. Indicadores", "Heading2")
    )

    filas = [["Indicador", "Resultado"]]

    for clave, valor in indicadores.items():

        nombre = clave.replace("_", " ").capitalize()

        if isinstance(valor, float):
            resultado = f"{valor:,.2f}"
        else:
            resultado = str(valor)

        filas.append([nombre, resultado])

    tabla = LongTable(
        filas,
        colWidths=[300, 160],
        repeatRows=1
    )

    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#174A7E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1),
             0.4, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.whitesmoke]),
            ("PADDING", (0, 0), (-1, -1), 7),
        ])
    )

    elementos.append(tabla)
    elementos.append(Spacer(1, 18))

    elementos.append(
        parrafo("2. Incidencias detectadas", "Heading2")
    )

    if incidencias.empty:

        elementos.append(
            parrafo("No se detectaron incidencias.")
        )

    else:

        filas_incidencias = [
            ["Fila", "Campo", "Problema"]
        ]

        for _, incidencia in incidencias.head(100).iterrows():

            filas_incidencias.append([
                str(incidencia["fila"]),
                parrafo(incidencia["campo"]),
                parrafo(incidencia["problema"])
            ])

        tabla_incidencias = LongTable(
            filas_incidencias,
            colWidths=[65, 150, 440],
            repeatRows=1
        )

        tabla_incidencias.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#8B2E2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0),
                 colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1),
                 0.4, colors.lightgrey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )

        elementos.append(tabla_incidencias)

        if len(incidencias) > 100:
            elementos.append(
                parrafo(
                    "Se muestran las primeras 100 incidencias."
                )
            )

    elementos.append(Spacer(1, 18))
    elementos.append(
        parrafo("3. Registros válidos", "Heading2")
    )

    elementos.append(
        parrafo(
            f"Total de registros válidos: {len(validos)}"
        )
    )

    documento.build(elementos)


def mostrar_indicadores(indicadores, perfil):
    """Muestra los indicadores del análisis actual."""

    columnas = st.columns(4)

    columnas[0].metric(
        "Registros procesados",
        indicadores["registros_totales"]
    )

    columnas[1].metric(
        "Registros válidos",
        indicadores["registros_validos"]
    )

    columnas[2].metric(
        "Con incidencias",
        indicadores["registros_con_incidencias"]
    )

    columnas[3].metric(
        "Porcentaje válido",
        f"{indicadores['porcentaje_validos']:.1f}%"
    )

    st.subheader("Indicadores del perfil")

    if perfil == "general":

        a, b = st.columns(2)

        a.metric(
            "Monto total válido",
            f"{indicadores['monto_total_valido']:,.2f}"
        )

        b.metric(
            "Monto promedio",
            f"{indicadores['monto_promedio']:,.2f}"
        )

    elif perfil == "ventas":

        a, b, c = st.columns(3)

        a.metric(
            "Ingresos totales",
            f"{indicadores['ingresos_totales']:,.2f}"
        )

        b.metric(
            "Unidades vendidas",
            f"{indicadores['unidades_vendidas']:,.0f}"
        )

        c.metric(
            "Ingreso promedio por registro",
            f"{indicadores['ingreso_promedio']:,.2f}"
        )

    elif perfil == "inventario":

        a, b, c = st.columns(3)

        a.metric(
            "Unidades disponibles",
            f"{indicadores['unidades_disponibles']:,.0f}"
        )

        b.metric(
            "Valor del inventario",
            f"{indicadores['valor_inventario']:,.2f}"
        )

        c.metric(
            "Productos agotados",
            indicadores["productos_agotados"]
        )

    elif perfil == "clientes":

        a, b = st.columns(2)

        a.metric(
            "Clientes válidos",
            indicadores["clientes_validos"]
        )

        b.metric(
            "Clientes con incidencias",
            indicadores["clientes_con_incidencias"]
        )


# =========================================
# BARRA LATERAL
# =========================================

with st.sidebar:

    st.header("ReportesPro")
    st.write("Sistema de análisis empresarial")
    st.divider()

    st.info("Base de datos: SQLite")
    st.write("Formatos: CSV, XLSX y XLS")


# =========================================
# BASE DE DATOS
# =========================================

crear_tablas()


# =========================================
# 1. GESTIÓN DE EMPRESAS
# =========================================

st.subheader("1. Gestión de empresas")

with st.expander("Registrar nueva empresa"):

    with st.form("formulario_empresa"):

        nombre_empresa = st.text_input(
            "Nombre de la empresa"
        )

        correo_empresa = st.text_input(
            "Correo electrónico"
        )

        guardar = st.form_submit_button(
            "Guardar empresa"
        )

        if guardar:

            if not nombre_empresa.strip():

                st.error(
                    "Debes escribir el nombre de la empresa."
                )

            else:

                try:

                    empresa_id = registrar_empresa(
                        nombre_empresa.strip(),
                        correo_empresa.strip()
                    )

                    st.success(
                        f"Empresa registrada con ID: {empresa_id}"
                    )

                except Exception as error:

                    st.error(
                        f"No se pudo registrar la empresa: {error}"
                    )


empresas = listar_empresas()

if empresas:

    opciones = {
        f"{empresa['nombre']} (ID: {empresa['id']})": empresa
        for empresa in empresas
    }

    seleccion = st.selectbox(
        "Selecciona una empresa",
        options=list(opciones.keys())
    )

    empresa_actual = opciones[seleccion]

    company = empresa_actual["nombre"]
    email = empresa_actual["correo"] or ""

    st.info(
        f"Empresa seleccionada: {company}"
    )

else:

    empresa_actual = None
    company = ""
    email = ""

    st.warning(
        "Todavía no hay empresas registradas."
    )


# =========================================
# 2. CARGAR Y ANALIZAR DATOS
# =========================================

st.divider()
st.subheader("2. Cargar datos")

perfiles = get_analysis_profiles()

perfil_seleccionado = st.selectbox(
    "Tipo de análisis empresarial",
    options=list(perfiles.keys()),
    format_func=lambda clave: perfiles[clave]["nombre"]
)

st.info(
    "Columnas requeridas: "
    + ", ".join(
        perfiles[perfil_seleccionado]["columnas"]
    )
)

with st.expander("Formato requerido"):

    st.write(
        f"Perfil: **{perfiles[perfil_seleccionado]['nombre']}**"
    )

    st.write(
        "Columnas obligatorias: "
        + ", ".join(
            perfiles[perfil_seleccionado]["columnas"]
        )
    )

    st.caption(
        "Los encabezados pueden contener mayúsculas "
        "y espacios adicionales."
    )


upload = st.file_uploader(
    "Selecciona un archivo CSV o Excel",
    type=["csv", "xlsx", "xls"]
)

example = Path(__file__).parent / "datos_ejemplo.csv"

if perfil_seleccionado == "general" and example.exists():

    usar_ejemplo = st.checkbox(
        "Usar archivo de demostración",
        value=False,
        disabled=upload is not None
    )

else:

    usar_ejemplo = False


if upload is not None or usar_ejemplo:

    if upload is not None:

        name = upload.name
        data = upload.getvalue()

    else:

        name = example.name
        data = example.read_bytes()

    procesar = st.button(
        "Procesar y generar PDF",
        type="primary",
        disabled=empresa_actual is None
    )

    if procesar:

        input_path = None
        pdf_path = None

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(name).suffix
            ) as temporal:

                temporal.write(data)
                input_path = temporal.name

            # Leer el archivo
            raw = load_data(input_path)

            # Analizar según el perfil
            valid, issues, metrics = analyze_business_profile(
                raw,
                perfil_seleccionado
            )

            # Crear PDF temporal
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            ) as temporal_pdf:

                pdf_path = temporal_pdf.name

            label = (
                f"{name} | Empresa: {company} | "
                f"Contacto: {email or 'No indicado'}"
            )

            if perfil_seleccionado == "general":

                create_pdf(
                    pdf_path,
                    label,
                    metrics,
                    issues,
                    valid
                )

            else:

                generar_pdf_empresarial(
                    pdf_path,
                    company,
                    name,
                    perfiles[perfil_seleccionado]["nombre"],
                    metrics,
                    issues,
                    valid
                )

            pdf = Path(pdf_path).read_bytes()

            # Guardar perfil e indicadores en SQLite
            reporte_id = guardar_reporte(
                empresa_actual["id"],
                name,
                metrics,
                perfil=perfil_seleccionado
            )

            st.session_state["ultimo_resultado"] = {
                "empresa_id": empresa_actual["id"],
                "perfil": perfil_seleccionado,
                "archivo": name,
                "reporte_id": reporte_id,
                "indicadores": metrics,
                "validos": valid,
                "incidencias": issues,
                "pdf": pdf
            }

            st.success(
                "Análisis completado. "
                f"Reporte registrado con ID: {reporte_id}"
            )

        except Exception as error:

            st.error(
                f"No se pudo procesar el archivo: {error}"
            )

        finally:

            for ruta in (input_path, pdf_path):

                if ruta:

                    try:
                        os.unlink(ruta)

                    except OSError:
                        pass


# =========================================
# MOSTRAR RESULTADO DEL ÚLTIMO ANÁLISIS
# =========================================

resultado = st.session_state.get(
    "ultimo_resultado"
)

if resultado is not None:

    if (
        resultado["empresa_id"] == (
            empresa_actual["id"]
            if empresa_actual is not None
            else None
        )
        and resultado["perfil"] == perfil_seleccionado
    ):

        st.divider()

        st.subheader(
            f"Resultado: {resultado['archivo']}"
        )

        mostrar_indicadores(
            resultado["indicadores"],
            resultado["perfil"]
        )

        datos_validos = resultado["validos"].drop(
            columns=["fila_origen"],
            errors="ignore"
        )

        st.subheader("Datos válidos")

        st.dataframe(
            datos_validos,
            use_container_width=True
        )

        st.subheader("Incidencias")

        st.dataframe(
            resultado["incidencias"],
            use_container_width=True
        )

        a, b, c = st.columns(3)

        a.download_button(
            "Descargar PDF",
            data=resultado["pdf"],
            file_name="reporte.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        b.download_button(
            "Descargar datos válidos",
            data=datos_validos.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="datos_validos.csv",
            mime="text/csv",
            use_container_width=True
        )

        c.download_button(
            "Descargar incidencias",
            data=resultado["incidencias"].to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="incidencias.csv",
            mime="text/csv",
            use_container_width=True
        )


# =========================================
# 3. HISTORIAL DE REPORTES
# =========================================

st.divider()
st.subheader("3. Historial de reportes")

if empresa_actual is not None:

    opciones_historial = {
        "Todos los perfiles": None,
        "Análisis general": "general",
        "Análisis de ventas": "ventas",
        "Análisis de inventario": "inventario",
        "Análisis de clientes": "clientes"
    }

    perfil_historial = st.selectbox(
        "Filtrar historial por tipo de análisis",
        options=list(opciones_historial.keys()),
        key="filtro_perfil_historial"
    )

    filtro_historial = opciones_historial[
        perfil_historial
    ]

    historial = listar_reportes(
        empresa_actual["id"],
        perfil=filtro_historial
    )

    if historial:

        df_historial = pd.DataFrame(historial)

        st.metric(
            "Reportes generados",
            len(df_historial)
        )

        busqueda = st.text_input(
            "Buscar por nombre de archivo",
            placeholder="Ejemplo: ventas.csv"
        )

        fechas = pd.to_datetime(
            df_historial["fecha_generacion"],
            utc=True
        ).dt.date

        fecha_min = fechas.min()
        fecha_max = fechas.max()

        rango = st.date_input(
            "Seleccionar período (fechas UTC)",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        filtrado = df_historial.copy()

        if busqueda.strip():

            filtrado = filtrado[
                filtrado["archivo"].str.contains(
                    busqueda.strip(),
                    case=False,
                    regex=False,
                    na=False
                )
            ]

        if (
            isinstance(rango, (tuple, list))
            and len(rango) == 2
        ):

            inicio, fin = rango

            fechas_filtradas = pd.to_datetime(
                filtrado["fecha_generacion"],
                utc=True
            ).dt.date

            filtrado = filtrado[
                (fechas_filtradas >= inicio)
                & (fechas_filtradas <= fin)
            ]

        st.write(
            f"Reportes encontrados: {len(filtrado)}"
        )

        columnas_visibles = [
            "id",
            "archivo",
            "perfil",
            "registros_totales",
            "registros_validos",
            "registros_invalidos",
            "fecha_generacion"
        ]

        st.dataframe(
            filtrado[columnas_visibles],
            use_container_width=True,
            hide_index=True
        )

        # Consultar indicadores de reportes anteriores
        if not filtrado.empty:

            ids_reportes = filtrado["id"].tolist()

            reporte_elegido = st.selectbox(
                "Consultar indicadores de un reporte anterior",
                options=ids_reportes,
                format_func=lambda rid: f"Reporte #{rid}",
                key="reporte_historico_elegido"
            )

            fila_reporte = filtrado.loc[
                filtrado["id"] == reporte_elegido
            ].iloc[0]

            indicadores_guardados = fila_reporte[
                "indicadores"
            ]

            if (
                isinstance(indicadores_guardados, dict)
                and indicadores_guardados
            ):

                tabla_indicadores = pd.DataFrame([
                    {
                        "Indicador": clave.replace(
                            "_", " "
                        ).capitalize(),
                        "Valor": valor
                    }
                    for clave, valor
                    in indicadores_guardados.items()
                ])

                st.dataframe(
                    tabla_indicadores,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Este reporte es anterior a la migración "
                    "y no tiene indicadores detallados guardados."
                )

        st.download_button(
            "Descargar historial CSV",
            data=filtrado.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="historial_reportes.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:

        st.info(
            "Esta empresa todavía no tiene reportes "
            "para el perfil seleccionado."
        )

else:

    st.warning(
        "Selecciona una empresa para consultar su historial."
    )


# =========================================
# 4. ESTADÍSTICAS HISTÓRICAS
# =========================================

st.divider()
st.subheader("4. Estadísticas históricas")

if empresa_actual is not None:

    empresa_id = empresa_actual["id"]

    estadisticas = obtener_estadisticas_empresa(
        empresa_id,
        perfil=filtro_historial
    )

    st.write(
        f"Estadísticas de: **{empresa_actual['nombre']}**"
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "Reportes generados",
        estadisticas["total_reportes"]
    )

    b.metric(
        "Registros procesados",
        estadisticas["total_registros"]
    )

    c.metric(
        "Registros válidos",
        estadisticas["total_validos"]
    )

    d.metric(
        "Con incidencias",
        estadisticas["total_incidencias"]
    )

    total = estadisticas["total_registros"]
    validos = estadisticas["total_validos"]

    porcentaje = (
        validos / total * 100
        if total
        else 0.0
    )

    st.metric(
        "Porcentaje histórico válido",
        f"{porcentaje:.1f}%"
    )

    historial_grafico = listar_reportes(
        empresa_id,
        perfil=filtro_historial
    )

    if historial_grafico:

        df_grafico = pd.DataFrame(
            historial_grafico
        )

        df_grafico = df_grafico.sort_values("id")

        df_grafico["ejecucion"] = (
            "Reporte #"
            + df_grafico["id"].astype(str)
        )

        df_grafico = df_grafico.set_index(
            "ejecucion"
        )

        st.subheader("Registros por ejecución")

        st.bar_chart(
            df_grafico[
                ["registros_totales", "registros_validos"]
            ],
            x_label="Reporte",
            y_label="Registros"
        )

        st.subheader("Incidencias por ejecución")

        st.bar_chart(
            df_grafico[
                ["registros_invalidos"]
            ],
            x_label="Reporte",
            y_label="Registros con incidencias"
        )

        st.caption(
            "Las estadísticas corresponden al perfil "
            "seleccionado, o a todos si se eligió esa "
            "opción. Procesar un archivo varias veces "
            "cuenta cada ejecución por separado."
        )

    else:

        st.info(
            "Todavía no hay reportes para mostrar gráficos."
        )

else:

    st.warning(
        "Selecciona una empresa para ver estadísticas."
    )


# =========================================
# PIE DE PÁGINA
# =========================================

st.divider()

st.caption(
    "ReportesPro · Sistema local en desarrollo. "
    "Sin autenticación, automatización ni conexión "
    "directa con MariaDB."
)
